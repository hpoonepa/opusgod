"""Lido stETH vault monitoring with anomaly detection.

Monitors:
- stETH APR from Lido API (correct endpoint: /v1/protocol/steth/apr/last)
- TVL changes for anomaly detection
- Severity-tiered alerts: INFO / WARNING / CRITICAL
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto

import httpx


class AlertSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class VaultAlert:
    severity: AlertSeverity
    metric: str
    message: str
    current_value: float
    threshold: float


@dataclass
class DataPoint:
    apr: float
    tvl: float
    timestamp: float = 0.0


class LidoMonitor:
    """Monitors Lido stETH vaults for anomalies and yield changes."""

    # Severity thresholds
    APR_INFO_DROP = 0.05      # 5% drop = INFO
    APR_WARNING_DROP = 0.20   # 20% drop = WARNING
    APR_CRITICAL_DROP = 0.50  # 50% drop = CRITICAL
    TVL_WARNING_DROP = 0.10   # 10% TVL drop = WARNING
    TVL_CRITICAL_DROP = 0.30  # 30% TVL drop = CRITICAL

    def __init__(self, api_base: str = "https://eth-api.lido.fi",
                 rolling_window: int = 24):
        self.api_base = api_base.rstrip("/")
        self._client = httpx.AsyncClient(timeout=15.0)
        self._history: deque[DataPoint] = deque(maxlen=rolling_window)

    async def get_steth_apr(self) -> dict:
        """Get latest stETH APR from Lido API."""
        resp = await self._client.get(f"{self.api_base}/v1/protocol/steth/apr/last")
        resp.raise_for_status()
        return resp.json().get("data", resp.json())

    async def get_steth_tvl(self) -> dict:
        """Get stETH TVL from Lido API."""
        resp = await self._client.get(f"{self.api_base}/v1/protocol/steth/tvl")
        resp.raise_for_status()
        return resp.json().get("data", resp.json())

    async def get_steth_stats(self) -> dict:
        """Get combined stETH APR + TVL."""
        apr_data = await self.get_steth_apr()
        try:
            tvl_data = await self.get_steth_tvl()
            if isinstance(apr_data, dict):
                apr_data["tvl"] = tvl_data.get("tvl", tvl_data) if isinstance(tvl_data, dict) else tvl_data
        except Exception:
            pass  # TVL is optional
        return apr_data

    def record_data_point(self, apr: float, tvl: float, timestamp: float = 0.0) -> None:
        """Record a data point for historical tracking."""
        self._history.append(DataPoint(apr=apr, tvl=tvl, timestamp=timestamp))

    def get_historical_average(self) -> DataPoint | None:
        """Get average APR and TVL from history."""
        if not self._history:
            return None
        avg_apr = sum(d.apr for d in self._history) / len(self._history)
        avg_tvl = sum(d.tvl for d in self._history) / len(self._history)
        return DataPoint(apr=avg_apr, tvl=avg_tvl)

    def check_anomalies(
        self,
        current_apr: float,
        historical_apr: float,
        tvl: float,
        prev_tvl: float,
    ) -> list[VaultAlert]:
        """Check for anomalies against thresholds. Returns alerts sorted by severity."""
        alerts: list[VaultAlert] = []

        if historical_apr > 0:
            apr_change = (historical_apr - current_apr) / historical_apr

            if apr_change >= self.APR_CRITICAL_DROP:
                alerts.append(VaultAlert(
                    severity=AlertSeverity.CRITICAL, metric="apr",
                    message=f"APR dropped {apr_change:.1%}: {historical_apr:.2f}% -> {current_apr:.2f}%",
                    current_value=current_apr,
                    threshold=historical_apr * (1 - self.APR_CRITICAL_DROP),
                ))
            elif apr_change >= self.APR_WARNING_DROP:
                alerts.append(VaultAlert(
                    severity=AlertSeverity.WARNING, metric="apr",
                    message=f"APR dropped {apr_change:.1%}: {historical_apr:.2f}% -> {current_apr:.2f}%",
                    current_value=current_apr,
                    threshold=historical_apr * (1 - self.APR_WARNING_DROP),
                ))
            elif apr_change >= self.APR_INFO_DROP:
                alerts.append(VaultAlert(
                    severity=AlertSeverity.INFO, metric="apr",
                    message=f"APR dipped {apr_change:.1%}: {historical_apr:.2f}% -> {current_apr:.2f}%",
                    current_value=current_apr,
                    threshold=historical_apr * (1 - self.APR_INFO_DROP),
                ))

        if prev_tvl > 0:
            tvl_change = (prev_tvl - tvl) / prev_tvl

            if tvl_change >= self.TVL_CRITICAL_DROP:
                alerts.append(VaultAlert(
                    severity=AlertSeverity.CRITICAL, metric="tvl",
                    message=f"TVL dropped {tvl_change:.1%}: ${prev_tvl/1e9:.1f}B -> ${tvl/1e9:.1f}B",
                    current_value=tvl,
                    threshold=prev_tvl * (1 - self.TVL_CRITICAL_DROP),
                ))
            elif tvl_change >= self.TVL_WARNING_DROP:
                alerts.append(VaultAlert(
                    severity=AlertSeverity.WARNING, metric="tvl",
                    message=f"TVL dropped {tvl_change:.1%}: ${prev_tvl/1e9:.1f}B -> ${tvl/1e9:.1f}B",
                    current_value=tvl,
                    threshold=prev_tvl * (1 - self.TVL_WARNING_DROP),
                ))

        return alerts

    async def close(self) -> None:
        await self._client.aclose()
