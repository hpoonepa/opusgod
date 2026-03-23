from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import httpx


class AlertSeverity(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class VaultAlert:
    severity: AlertSeverity
    metric: str
    message: str
    current_value: float
    threshold: float


class LidoMonitor:
    """Monitors Lido stETH vaults for anomalies and yield changes."""

    APR_DROP_THRESHOLD = 0.20
    TVL_DROP_THRESHOLD = 0.15
    APR_CRITICAL_FLOOR = 1.0

    def __init__(self, api_base: str = "https://eth-api.lido.fi/v1"):
        self.api_base = api_base
        self._client = httpx.AsyncClient(timeout=15.0)

    async def get_steth_stats(self) -> dict:
        resp = await self._client.get(f"{self.api_base}/protocol/steth/stats")
        resp.raise_for_status()
        return resp.json().get("data", resp.json())

    async def get_validators(self) -> dict:
        resp = await self._client.get(f"{self.api_base}/validators")
        resp.raise_for_status()
        return resp.json().get("data", resp.json())

    def check_anomalies(
        self,
        current_apr: float,
        historical_apr: float,
        tvl: float,
        prev_tvl: float,
    ) -> list[VaultAlert]:
        alerts: list[VaultAlert] = []

        if historical_apr > 0:
            apr_change = (historical_apr - current_apr) / historical_apr
            if apr_change >= self.APR_DROP_THRESHOLD:
                severity = (
                    AlertSeverity.CRITICAL
                    if current_apr < self.APR_CRITICAL_FLOOR
                    else AlertSeverity.HIGH
                )
                alerts.append(
                    VaultAlert(
                        severity=severity,
                        metric="apr",
                        message=f"APR dropped {apr_change:.1%}: {historical_apr:.2f}% \u2192 {current_apr:.2f}%",
                        current_value=current_apr,
                        threshold=historical_apr * (1 - self.APR_DROP_THRESHOLD),
                    )
                )

        if prev_tvl > 0:
            tvl_change = (prev_tvl - tvl) / prev_tvl
            if tvl_change >= self.TVL_DROP_THRESHOLD:
                severity = (
                    AlertSeverity.HIGH if tvl_change >= 0.30 else AlertSeverity.MEDIUM
                )
                alerts.append(
                    VaultAlert(
                        severity=severity,
                        metric="tvl",
                        message=f"TVL dropped {tvl_change:.1%}: ${prev_tvl / 1e9:.1f}B \u2192 ${tvl / 1e9:.1f}B",
                        current_value=tvl,
                        threshold=prev_tvl * (1 - self.TVL_DROP_THRESHOLD),
                    )
                )

        return alerts

    async def close(self) -> None:
        await self._client.aclose()
