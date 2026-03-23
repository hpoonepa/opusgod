"""Bankr LLM Gateway — multi-model routing with retry and cost tracking.

Routes to GPT-4o, Claude Sonnet, Gemini Pro based on task type.
Endpoint: https://llm.bankr.bot/v1/chat/completions (OpenAI-compatible).
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# Model routing by task type
MODEL_ROUTES: dict[str, str] = {
    "analysis": "gpt-4o",
    "risk": "gpt-4o",
    "score": "gpt-4o",
    "monitor": "gpt-4o-mini",
    "alert": "gpt-4o-mini",
    "simple": "gpt-4o-mini",
    "strategy": "claude-sonnet-4-20250514",
    "rebalance": "claude-sonnet-4-20250514",
    "portfolio": "claude-sonnet-4-20250514",
}

TEMP_ROUTES: dict[str, float] = {
    "risk": 0.0, "score": 0.0, "analysis": 0.1,
    "strategy": 0.7, "creative": 0.7,
}

# Cost per 1K tokens (approximate)
MODEL_COSTS: dict[str, float] = {
    "gpt-4o": 0.005, "gpt-4o-mini": 0.00015,
    "claude-sonnet-4-20250514": 0.003, "gemini-pro": 0.00025,
}


class BankrAPIError(Exception):
    """Raised on non-retryable Bankr API errors."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Bankr API {status_code}: {detail}")


@dataclass
class UsageStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0
    requests: int = 0


class BankrClient:
    """Multi-model LLM gateway client with retry and cost tracking."""

    def __init__(self, api_key: str,
                 endpoint: str = "https://llm.bankr.bot/v1/chat/completions",
                 model: str = "gpt-4o"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.default_model = model
        self._client = httpx.AsyncClient(timeout=60.0)
        self._usage = UsageStats()

    def _resolve_model(self, task_type: str | None, model: str | None) -> str:
        if model:
            return model
        if task_type and task_type in MODEL_ROUTES:
            return MODEL_ROUTES[task_type]
        return self.default_model

    def _resolve_temp(self, task_type: str | None, temperature: float | None) -> float:
        if temperature is not None:
            return temperature
        if task_type and task_type in TEMP_ROUTES:
            return TEMP_ROUTES[task_type]
        return 0.3

    async def _request_with_retry(self, payload: dict, max_retries: int = 3) -> dict:
        """Send request with exponential backoff on 429/5xx."""
        delays = [1, 2, 4]
        last_error = None

        for attempt in range(max_retries):
            try:
                resp = await self._client.post(
                    self.endpoint,
                    headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    await asyncio.sleep(delays[attempt])
                    continue
                raise BankrAPIError(resp.status_code, resp.text)
            except httpx.HTTPError as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(delays[attempt])
                    continue
                raise BankrAPIError(0, str(e)) from e

        raise BankrAPIError(0, str(last_error))

    def _track_usage(self, response: dict, model: str) -> None:
        usage = response.get("usage", {})
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        self._usage.prompt_tokens += prompt
        self._usage.completion_tokens += completion
        self._usage.requests += 1
        cost_rate = MODEL_COSTS.get(model, 0.005)
        self._usage.total_cost_usd += (prompt + completion) * cost_rate / 1000

    async def chat(self, prompt: str, system: str | None = None,
                   model: str | None = None, task_type: str | None = None,
                   temperature: float | None = None, json_mode: bool = False) -> str:
        """Send a chat request with model routing."""
        resolved_model = self._resolve_model(task_type, model)
        resolved_temp = self._resolve_temp(task_type, temperature)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict = {
            "model": resolved_model,
            "messages": messages,
            "temperature": resolved_temp,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = await self._request_with_retry(payload)
        self._track_usage(response, resolved_model)
        return response["choices"][0]["message"]["content"]

    async def analyze_defi(self, query: str, *, model: str | None = None) -> str:
        """DeFi analysis with structured JSON output."""
        system = (
            "You are an autonomous DeFi intelligence agent. Analyze the following and return "
            "structured JSON with keys: risk_level, yield_apy, recommendation, confidence."
        )
        return await self.chat(query, system=system, task_type="analysis",
                               model=model, json_mode=True)

    async def score_vault(self, vault_data: dict, *, model: str | None = None) -> str:
        """Score a DeFi vault."""
        system = "Score this DeFi vault on risk (1-10), yield attractiveness (1-10), and liquidity depth. Return JSON."
        return await self.chat(json.dumps(vault_data), system=system,
                               task_type="score", model=model, json_mode=True)

    def get_usage_stats(self) -> dict:
        """Get accumulated usage statistics."""
        return {
            "prompt_tokens": self._usage.prompt_tokens,
            "completion_tokens": self._usage.completion_tokens,
            "total_tokens": self._usage.prompt_tokens + self._usage.completion_tokens,
            "total_cost_usd": round(self._usage.total_cost_usd, 6),
            "requests": self._usage.requests,
        }

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
