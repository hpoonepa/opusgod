from __future__ import annotations

import json
import httpx


class BankrClient:
    """Client for Bankr LLM Gateway — routes to GPT/Claude/Gemini."""

    def __init__(self, api_key: str, endpoint: str = "https://llm.bankr.bot/v1/chat/completions", model: str = "gpt-4o"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self._client = httpx.AsyncClient(timeout=30.0)

    async def chat(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = await self._client.post(
            self.endpoint,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json={"model": model or self.model, "messages": messages},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def analyze_defi(self, query: str) -> str:
        system = (
            "You are an autonomous DeFi intelligence agent. Analyze the following and return "
            "structured JSON with keys: risk_level, yield_apy, recommendation, confidence."
        )
        return await self.chat(query, system=system)

    async def score_vault(self, vault_data: dict) -> str:
        system = "Score this DeFi vault on risk (1-10), yield attractiveness (1-10), and liquidity depth. Return JSON."
        return await self.chat(json.dumps(vault_data), system=system)

    async def close(self) -> None:
        await self._client.aclose()
