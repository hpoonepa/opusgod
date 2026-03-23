"""Telegram alert notifier using python-telegram-bot v20+ async API.

Sends formatted alerts for vault anomalies, status updates, and revenue milestones.
"""
from __future__ import annotations

import logging

from telegram import Bot
from telegram.error import TelegramError

from src.integrations.lido import AlertSeverity, VaultAlert

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    AlertSeverity.INFO: "\u2139\ufe0f",       # info
    AlertSeverity.WARNING: "\u26a0\ufe0f",     # warning
    AlertSeverity.CRITICAL: "\U0001f6a8",      # siren
}


class TelegramNotifier:
    """Sends alerts via Telegram using python-telegram-bot v20+."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._bot = Bot(token=bot_token)

    def format_alert(self, alert: VaultAlert) -> str:
        emoji = SEVERITY_EMOJI.get(alert.severity, "?")
        return (
            f"{emoji} <b>{alert.severity.name} ALERT</b>\n"
            f"Metric: <code>{alert.metric}</code>\n{alert.message}\n"
            f"Current: <code>{alert.current_value}</code> | Threshold: <code>{alert.threshold}</code>"
        )

    def format_status(self, status: dict) -> str:
        return (
            f"\U0001f916 <b>OpusGod Status</b>\n"
            f"State: <code>{status.get('state', 'UNKNOWN')}</code>\n"
            f"Requests served: <code>{status.get('requests_served', 0)}</code>\n"
            f"Revenue: <code>${status.get('total_revenue_usd', 0):.2f}</code>"
        )

    def format_anomaly_alert(self, anomalies: list[VaultAlert]) -> str:
        """Format multiple anomalies into a single message."""
        if not anomalies:
            return "\u2705 No anomalies detected"
        lines = [f"\U0001f6a8 <b>{len(anomalies)} Anomalies Detected</b>\n"]
        for a in anomalies:
            emoji = SEVERITY_EMOJI.get(a.severity, "?")
            lines.append(f"{emoji} [{a.metric.upper()}] {a.message}")
        return "\n".join(lines)

    async def _send_message(self, text: str, parse_mode: str = "HTML") -> None:
        try:
            await self._bot.send_message(
                chat_id=self.chat_id, text=text, parse_mode=parse_mode,
            )
        except TelegramError as e:
            logger.error(f"Telegram send failed: {e}")

    async def send_alert(self, alert: VaultAlert) -> None:
        await self._send_message(self.format_alert(alert))

    async def send_status(self, status: dict) -> None:
        await self._send_message(self.format_status(status))

    async def send_anomalies(self, anomalies: list[VaultAlert]) -> None:
        if anomalies:
            await self._send_message(self.format_anomaly_alert(anomalies))

    async def close(self) -> None:
        """Cleanup (Bot doesn't need explicit close)."""
        pass
