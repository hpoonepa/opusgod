"""Olas mech tools — 5 DeFi analysis tools for the marketplace.

Each tool follows the Olas mech signature:
    async def run(**kwargs) -> Tuple[str, str, Optional[str], Optional[Dict], Any]
Returns: (result_text, prompt_used, error_or_none, metadata, raw_response)
"""
from __future__ import annotations

import json
from typing import Any, Optional


async def yield_optimizer(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """Cross-protocol yield comparison and optimization.

    Compares yields across protocols, ranks by risk-adjusted return (Sharpe-like),
    and recommends optimal allocation.
    """
    system = (
        "You are a DeFi yield optimizer. Analyze the query and return JSON with:\n"
        '{"best_yield": {"protocol": "name", "apy": 0.0, "chain": "chain"},\n'
        ' "rankings": [{"protocol": "name", "apy": 0.0, "risk": 1, "sharpe": 0.0}],\n'
        ' "recommendation": "text", "confidence": 0.0}'
    )
    try:
        raw = await bankr.chat(query, system=system, task_type="analysis")
        return (raw, query, None, {"tool": "yield_optimizer", "model": "gpt-4o"}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "yield_optimizer"}, None)


async def risk_assessor(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """Portfolio and vault risk scoring on a 1-10 scale.

    Evaluates protocol risks: smart contract risk, oracle risk, liquidity risk,
    governance risk, and audit status.
    """
    system = (
        "You are a DeFi risk assessor. Analyze and return JSON with:\n"
        '{"risk_score": 5, "risk_breakdown": {"smart_contract": 3, "oracle": 4, '
        '"liquidity": 5, "governance": 3}, "factors": ["factor1"], '
        '"mitigation": ["action1"], "recommendation": "text"}'
    )
    try:
        raw = await bankr.chat(query, system=system, task_type="risk")
        return (raw, query, None, {"tool": "risk_assessor", "model": "gpt-4o"}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "risk_assessor"}, None)


async def vault_monitor(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """Real-time vault health monitoring with anomaly detection.

    Checks vault TVL trends, APY stability, utilization ratio,
    and flags anomalies.
    """
    system = (
        "You are a DeFi vault monitor. Analyze vault health and return JSON with:\n"
        '{"health_status": "healthy|warning|critical", "metrics": '
        '{"apy_current": 0.0, "apy_7d_avg": 0.0, "tvl": 0, "utilization": 0.0}, '
        '"anomalies": [{"type": "type", "severity": "low|medium|high", "detail": "text"}], '
        '"alert_level": "none|info|warning|critical"}'
    )
    try:
        raw = await bankr.chat(query, system=system, task_type="monitor")
        return (raw, query, None, {"tool": "vault_monitor", "model": "gpt-4o-mini"}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "vault_monitor"}, None)


async def protocol_analyzer(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """DeFi protocol health and safety analysis.

    Analyzes protocol fundamentals: TVL, governance, audit history,
    team, and economic model.
    """
    system = (
        "You are a DeFi protocol analyst. Analyze the protocol and return JSON with:\n"
        '{"safety_score": 8, "audit_status": "audited|unaudited|partial", '
        '"tvl_usd": 0, "governance": {"type": "dao|multisig|single", "risk": "low|medium|high"}, '
        '"age_days": 0, "recommendation": "text", "red_flags": []}'
    )
    try:
        raw = await bankr.chat(query, system=system, task_type="analysis")
        return (raw, query, None, {"tool": "protocol_analyzer", "model": "gpt-4o"}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "protocol_analyzer"}, None)


async def portfolio_rebalancer(query: str, *, bankr: Any) -> tuple[str, str, Optional[str], Optional[dict], Any]:
    """AI-driven portfolio rebalancing recommendations.

    Suggests rebalancing based on risk/yield targets, current allocation,
    and market conditions.
    """
    system = (
        "You are a DeFi portfolio rebalancer. Analyze and return JSON with:\n"
        '{"current_allocation": [{"protocol": "name", "weight": 0.0}], '
        '"recommended_allocation": [{"protocol": "name", "weight": 0.0, "reason": "text"}], '
        '"expected_improvement": {"apy_delta": 0.0, "risk_delta": 0}, '
        '"actions": [{"action": "deposit|withdraw|swap", "protocol": "name", "amount_pct": 0.0}]}'
    )
    try:
        raw = await bankr.chat(query, system=system, task_type="strategy")
        return (raw, query, None, {"tool": "portfolio_rebalancer", "model": "claude-sonnet-4-20250514"}, raw)
    except Exception as e:
        return ("", query, str(e), {"tool": "portfolio_rebalancer"}, None)


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "yield_optimizer": {"description": "Cross-protocol yield comparison and optimization", "handler": yield_optimizer},
    "risk_assessor": {"description": "Portfolio and vault risk scoring (1-10 scale)", "handler": risk_assessor},
    "vault_monitor": {"description": "Real-time vault health monitoring with anomaly detection", "handler": vault_monitor},
    "protocol_analyzer": {"description": "DeFi protocol health and safety analysis", "handler": protocol_analyzer},
    "portfolio_rebalancer": {"description": "AI-driven portfolio rebalancing recommendations", "handler": portfolio_rebalancer},
}
