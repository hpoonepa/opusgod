from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


class DeFiAnalyzer:
    """Core DeFi analysis engine powered by Bankr LLM."""

    def __init__(self, bankr):
        self.bankr = bankr

    async def analyze_protocol(self, protocol: str) -> dict:
        raw = await self.bankr.analyze_defi(f"Analyze DeFi protocol: {protocol}")
        return {"protocol": protocol, "analysis": self._parse(raw)}

    async def compare_yields(self, protocols: list[str]) -> dict:
        query = f"Compare yields across: {', '.join(protocols)}. Rank by risk-adjusted return."
        raw = await self.bankr.analyze_defi(query)
        return {"comparison": self._parse(raw), "protocols": protocols}

    async def get_market_overview(self) -> dict:
        raw = await self.bankr.analyze_defi(
            "Provide a DeFi market overview: top TVL protocols, average yields, major risks."
        )
        return {"overview": self._parse(raw), "source": "bankr-llm"}

    def _parse(self, raw: str) -> dict | str:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
