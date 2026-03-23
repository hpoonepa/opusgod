from __future__ import annotations
from typing import Any


async def yield_optimizer(query: str, *, bankr: Any) -> str:
    return await bankr.chat(query, system="You are a DeFi yield optimizer. Compare protocols and return JSON with: best_yield, protocol, risk_adjusted_score, recommendation.")


async def risk_assessor(query: str, *, bankr: Any) -> str:
    return await bankr.chat(query, system="You are a DeFi risk assessor. Analyze and return JSON with: risk_score (1-10), factors, mitigation, recommendation.")


async def vault_monitor(query: str, *, bankr: Any) -> str:
    return await bankr.chat(query, system="You are a DeFi vault monitor. Return JSON with: health_status, apy_current, tvl_trend, anomalies, alert_level.")


async def protocol_analyzer(query: str, *, bankr: Any) -> str:
    return await bankr.chat(query, system="You are a DeFi protocol analyst. Return JSON with: safety_score, audit_status, tvl, governance_risk, recommendation.")


async def portfolio_rebalancer(query: str, *, bankr: Any) -> str:
    return await bankr.chat(query, system="You are a DeFi portfolio rebalancer. Return JSON with: current_allocation, recommended_allocation, expected_improvement, actions.")


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "yield_optimizer": {"description": "Cross-protocol yield comparison and optimization", "handler": yield_optimizer},
    "risk_assessor": {"description": "Portfolio and vault risk scoring (1-10 scale)", "handler": risk_assessor},
    "vault_monitor": {"description": "Real-time vault health monitoring with anomaly detection", "handler": vault_monitor},
    "protocol_analyzer": {"description": "DeFi protocol health and safety analysis", "handler": protocol_analyzer},
    "portfolio_rebalancer": {"description": "AI-driven portfolio rebalancing recommendations", "handler": portfolio_rebalancer},
}
