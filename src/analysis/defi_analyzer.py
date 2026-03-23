"""DeFi analysis engine — combines real DeFiLlama data with Bankr LLM analysis.

Fetches live protocol data from DeFiLlama API, then uses Bankr for
intelligent analysis and recommendations.
"""
from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)

DEFILLAMA_BASE = "https://api.llama.fi"
DEFILLAMA_YIELDS = "https://yields.llama.fi"


class DeFiAnalyzer:
    """Core DeFi analysis engine powered by real data + Bankr LLM."""

    def __init__(self, bankr):
        self.bankr = bankr
        self._http = httpx.AsyncClient(timeout=30.0)
        self._cache: dict[str, tuple[float, any]] = {}  # key -> (timestamp, data)
        self._cache_ttl = 300  # 5 minutes

    def _cache_get(self, key: str):
        import time
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _cache_set(self, key: str, data):
        import time
        self._cache[key] = (time.time(), data)

    async def _fetch_protocol(self, protocol: str) -> dict | None:
        """Fetch protocol data from DeFiLlama (cached)."""
        cached = self._cache_get(f"protocol:{protocol}")
        if cached is not None:
            return cached
        try:
            resp = await self._http.get(f"{DEFILLAMA_BASE}/protocol/{protocol}")
            if resp.status_code == 200:
                data = resp.json()
                self._cache_set(f"protocol:{protocol}", data)
                return data
        except httpx.HTTPError as e:
            logger.warning(f"DeFiLlama fetch failed for {protocol}: {e}")
        return None

    async def _fetch_yields(self, chain: str | None = None, min_tvl: float = 0) -> list[dict]:
        """Fetch yield pool data from DeFiLlama (cached)."""
        cache_key = f"yields:{chain}:{min_tvl}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            resp = await self._http.get(f"{DEFILLAMA_YIELDS}/pools")
            if resp.status_code == 200:
                pools = resp.json().get("data", [])
                if chain:
                    pools = [p for p in pools if p.get("chain", "").lower() == chain.lower()]
                if min_tvl > 0:
                    pools = [p for p in pools if (p.get("tvlUsd") or 0) >= min_tvl]
                self._cache_set(cache_key, pools)
                return pools
        except httpx.HTTPError as e:
            logger.warning(f"DeFiLlama yields fetch failed: {e}")
        return []

    async def analyze_protocol(self, protocol: str) -> dict:
        """Fetch real DeFiLlama data + LLM analysis."""
        llama_data = await self._fetch_protocol(protocol)

        context = f"Protocol: {protocol}"
        if llama_data:
            tvl = llama_data.get("tvl", [{}])
            current_tvl = tvl[-1].get("totalLiquidityUSD", 0) if tvl else 0
            context += f"\nTVL: ${current_tvl:,.0f}"
            context += f"\nChains: {', '.join(llama_data.get('chains', []))}"
            context += f"\nCategory: {llama_data.get('category', 'Unknown')}"

        raw = await self.bankr.analyze_defi(f"Analyze DeFi protocol with real data:\n{context}")
        current_tvl_value = current_tvl if llama_data else None
        return {"protocol": protocol, "analysis": self._parse(raw),
                "live_data": {"tvl": current_tvl_value}}

    async def get_top_yields(self, chain: str | None = None, min_tvl: float = 1_000_000,
                              limit: int = 10) -> list[dict]:
        """Get top yield opportunities from DeFiLlama."""
        pools = await self._fetch_yields(chain=chain, min_tvl=min_tvl)
        # Sort by APY descending
        pools.sort(key=lambda p: p.get("apy", 0), reverse=True)
        return [
            {
                "pool": p.get("pool", ""),
                "project": p.get("project", ""),
                "chain": p.get("chain", ""),
                "apy": p.get("apy", 0),
                "tvl": p.get("tvlUsd", 0),
                "symbol": p.get("symbol", ""),
            }
            for p in pools[:limit]
        ]

    async def compare_yields(self, protocols: list[str]) -> dict:
        """Compare yields across protocols using real DeFiLlama data."""
        real_data = {}
        for protocol in protocols:
            llama = await self._fetch_protocol(protocol)
            if llama:
                tvl_list = llama.get("tvl", [])
                real_data[protocol] = {
                    "tvl": tvl_list[-1].get("totalLiquidityUSD", 0) if tvl_list else 0,
                    "chains": llama.get("chains", []),
                    "category": llama.get("category", "unknown"),
                }

        context = f"Compare yields across: {', '.join(protocols)}. Rank by risk-adjusted return."
        if real_data:
            context += f"\n\nReal DeFiLlama data:\n{json.dumps(real_data, indent=1)}"
        raw = await self.bankr.analyze_defi(context)
        return {"comparison": self._parse(raw), "protocols": protocols,
                "live_data": real_data}

    async def get_market_overview(self) -> dict:
        """Market overview with real DeFiLlama data."""
        top_yields = await self.get_top_yields(limit=5)
        context = f"Top 5 yield pools:\n{json.dumps(top_yields, indent=2)}"
        raw = await self.bankr.analyze_defi(
            f"Provide a DeFi market overview based on real data:\n{context}"
        )
        return {"overview": self._parse(raw), "source": "defillama+bankr",
                "top_yields": top_yields}

    def _parse(self, raw: str) -> dict | str:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def close(self) -> None:
        await self._http.aclose()
