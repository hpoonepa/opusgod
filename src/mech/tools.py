"""Olas mech tools — 5 DeFi analysis tools for the marketplace.

Each tool follows the Olas mech signature:
    async def run(**kwargs) -> Tuple[str, str, Optional[str], Optional[Dict], Any]
Returns: (result_text, prompt_used, error_or_none, metadata, raw_response)

All tools fetch real data from DeFiLlama before sending to Bankr LLM.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import httpx

DEFILLAMA_BASE = "https://api.llama.fi"
DEFILLAMA_YIELDS = "https://yields.llama.fi"

async def _fetch_defillama(path: str, base: str = DEFILLAMA_BASE) -> dict | list | None:
    """Fetch data from DeFiLlama API. Returns None on any failure."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}{path}")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


async def yield_optimizer(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """Cross-protocol yield comparison and optimization.

    Fetches real yield pools from DeFiLlama, then uses Bankr LLM to rank
    by risk-adjusted return (Sharpe-like) and recommend optimal allocation.
    """
    # Fetch real yield data
    pools_data = await _fetch_defillama("/pools", base=DEFILLAMA_YIELDS)
    top_pools = []
    if pools_data and isinstance(pools_data, dict):
        pools = pools_data.get("data", [])
        pools.sort(key=lambda p: p.get("apy", 0), reverse=True)
        top_pools = [
            {"project": p.get("project"), "chain": p.get("chain"),
             "apy": round(p.get("apy", 0), 2), "tvl": p.get("tvlUsd", 0),
             "symbol": p.get("symbol")}
            for p in pools[:20] if (p.get("tvlUsd") or 0) > 1_000_000
        ]

    context = f"Real DeFiLlama yield data (top pools by APY):\n{json.dumps(top_pools[:10], indent=1)}\n\nUser query: {query}"
    system = (
        "You are a DeFi yield optimizer. You have real yield data above. Return JSON with:\n"
        '{"best_yield": {"protocol": "name", "apy": 0.0, "chain": "chain"},\n'
        ' "rankings": [{"protocol": "name", "apy": 0.0, "risk": 1, "sharpe": 0.0}],\n'
        ' "recommendation": "text", "confidence": 0.0, "data_source": "defillama"}'
    )
    try:
        raw = await bankr.chat(context, system=system, task_type="analysis")
        return (raw, query, None, {"tool": "yield_optimizer", "model": "gpt-4o", "pools_fetched": len(top_pools)}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "yield_optimizer"}, None)


async def risk_assessor(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """Portfolio and vault risk scoring on a 1-10 scale.

    Fetches protocol TVL and audit data from DeFiLlama for risk context.
    """
    # Try to extract protocol name from query for real data
    protocol_data = None
    for word in query.lower().split():
        data = await _fetch_defillama(f"/protocol/{word}")
        if data and isinstance(data, dict) and "tvl" in data:
            protocol_data = {
                "name": data.get("name", word),
                "tvl": data.get("tvl", [{}])[-1].get("totalLiquidityUSD", 0) if data.get("tvl") else 0,
                "chains": data.get("chains", []),
                "category": data.get("category", "unknown"),
                "audits": data.get("audits", "unknown"),
            }
            break

    context = query
    if protocol_data:
        context = f"Real protocol data:\n{json.dumps(protocol_data, indent=1)}\n\nQuery: {query}"

    system = (
        "You are a DeFi risk assessor with real protocol data. Analyze and return JSON with:\n"
        '{"risk_score": 5, "risk_breakdown": {"smart_contract": 3, "oracle": 4, '
        '"liquidity": 5, "governance": 3}, "factors": ["factor1"], '
        '"mitigation": ["action1"], "recommendation": "text", "data_source": "defillama"}'
    )
    try:
        raw = await bankr.chat(context, system=system, task_type="risk")
        return (raw, query, None, {"tool": "risk_assessor", "model": "gpt-4o", "has_live_data": protocol_data is not None}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "risk_assessor"}, None)


async def vault_monitor(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """Real-time vault health monitoring with anomaly detection.

    Fetches real TVL/APY data from DeFiLlama pools endpoint.
    """
    # Fetch real yield pool data for vault context
    pools_data = await _fetch_defillama("/pools", base=DEFILLAMA_YIELDS)
    relevant_pools = []
    if pools_data and isinstance(pools_data, dict):
        pools = pools_data.get("data", [])
        query_lower = query.lower()
        for p in pools:
            if any(term in (p.get("project", "") + p.get("symbol", "")).lower()
                   for term in query_lower.split() if len(term) > 2):
                relevant_pools.append({
                    "project": p.get("project"), "symbol": p.get("symbol"),
                    "apy": round(p.get("apy", 0), 2), "tvl": p.get("tvlUsd", 0),
                    "apy_7d": p.get("apyMean7d"), "chain": p.get("chain"),
                })
                if len(relevant_pools) >= 5:
                    break

    context = query
    if relevant_pools:
        context = f"Real vault data from DeFiLlama:\n{json.dumps(relevant_pools, indent=1)}\n\nQuery: {query}"

    system = (
        "You are a DeFi vault monitor with real data. Analyze vault health and return JSON with:\n"
        '{"health_status": "healthy|warning|critical", "metrics": '
        '{"apy_current": 0.0, "apy_7d_avg": 0.0, "tvl": 0, "utilization": 0.0}, '
        '"anomalies": [{"type": "type", "severity": "low|medium|high", "detail": "text"}], '
        '"alert_level": "none|info|warning|critical", "data_source": "defillama"}'
    )
    try:
        raw = await bankr.chat(context, system=system, task_type="monitor")
        return (raw, query, None, {"tool": "vault_monitor", "model": "gpt-4o-mini", "vaults_found": len(relevant_pools)}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "vault_monitor"}, None)


async def protocol_analyzer(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """DeFi protocol health and safety analysis.

    Fetches real protocol data from DeFiLlama including TVL, chains, and category.
    """
    # Fetch protocol data
    protocol_data = None
    for word in query.lower().split():
        data = await _fetch_defillama(f"/protocol/{word}")
        if data and isinstance(data, dict) and "tvl" in data:
            tvl_history = data.get("tvl", [])
            current_tvl = tvl_history[-1].get("totalLiquidityUSD", 0) if tvl_history else 0
            protocol_data = {
                "name": data.get("name", word),
                "current_tvl": current_tvl,
                "chains": data.get("chains", []),
                "category": data.get("category", "unknown"),
                "url": data.get("url", ""),
                "tvl_30d_ago": tvl_history[-30].get("totalLiquidityUSD", 0) if len(tvl_history) > 30 else 0,
            }
            break

    context = query
    if protocol_data:
        context = f"Real DeFiLlama protocol data:\n{json.dumps(protocol_data, indent=1)}\n\nQuery: {query}"

    system = (
        "You are a DeFi protocol analyst with real data. Analyze and return JSON with:\n"
        '{"safety_score": 8, "audit_status": "audited|unaudited|partial", '
        '"tvl_usd": 0, "governance": {"type": "dao|multisig|single", "risk": "low|medium|high"}, '
        '"age_days": 0, "recommendation": "text", "red_flags": [], "data_source": "defillama"}'
    )
    try:
        raw = await bankr.chat(context, system=system, task_type="analysis")
        return (raw, query, None, {"tool": "protocol_analyzer", "model": "gpt-4o", "has_live_data": protocol_data is not None}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "protocol_analyzer"}, None)


async def portfolio_rebalancer(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """AI-driven portfolio rebalancing recommendations.

    Fetches top yields from DeFiLlama to inform rebalancing strategy.
    """
    # Fetch current top yields for context
    pools_data = await _fetch_defillama("/pools", base=DEFILLAMA_YIELDS)
    top_opportunities = []
    if pools_data and isinstance(pools_data, dict):
        pools = pools_data.get("data", [])
        # Filter for high-TVL, reasonable-APY pools
        stable_pools = [p for p in pools if (p.get("tvlUsd") or 0) > 10_000_000]
        stable_pools.sort(key=lambda p: p.get("apy", 0), reverse=True)
        top_opportunities = [
            {"project": p.get("project"), "chain": p.get("chain"),
             "apy": round(p.get("apy", 0), 2), "tvl": p.get("tvlUsd", 0),
             "symbol": p.get("symbol")}
            for p in stable_pools[:10]
        ]

    context = f"Top rebalancing opportunities (real DeFiLlama data):\n{json.dumps(top_opportunities, indent=1)}\n\nQuery: {query}"
    system = (
        "You are a DeFi portfolio rebalancer with real market data. Analyze and return JSON with:\n"
        '{"current_allocation": [{"protocol": "name", "weight": 0.0}], '
        '"recommended_allocation": [{"protocol": "name", "weight": 0.0, "reason": "text"}], '
        '"expected_improvement": {"apy_delta": 0.0, "risk_delta": 0}, '
        '"actions": [{"action": "deposit|withdraw|swap", "protocol": "name", "amount_pct": 0.0}], '
        '"data_source": "defillama"}'
    )
    try:
        raw = await bankr.chat(context, system=system, task_type="strategy")
        return (raw, query, None, {"tool": "portfolio_rebalancer", "model": "claude-sonnet-4-20250514", "opportunities": len(top_opportunities)}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "portfolio_rebalancer"}, None)


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "yield_optimizer": {"description": "Cross-protocol yield comparison and optimization (DeFiLlama-powered)", "handler": yield_optimizer},
    "risk_assessor": {"description": "Portfolio and vault risk scoring with real protocol data", "handler": risk_assessor},
    "vault_monitor": {"description": "Real-time vault health monitoring with DeFiLlama data", "handler": vault_monitor},
    "protocol_analyzer": {"description": "DeFi protocol health and safety analysis with live TVL", "handler": protocol_analyzer},
    "portfolio_rebalancer": {"description": "AI-driven portfolio rebalancing with real yield data", "handler": portfolio_rebalancer},
}
