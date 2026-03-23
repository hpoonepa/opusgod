from __future__ import annotations

import httpx

from src.integrations.lido import AlertSeverity, VaultAlert

SEVERITY_EMOJI = {
    AlertSeverity.LOW: "i",
    AlertSeverity.MEDIUM: "!",
    AlertSeverity.HIGH: "!!",
    AlertSeverity.CRITICAL: "!!!",
}


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._client = httpx.AsyncClient(timeout=10.0)

    def format_alert(self, alert: VaultAlert) -> str:
        emoji = SEVERITY_EMOJI.get(alert.severity, "?")
        return (
            f"{emoji} *{alert.severity.name} ALERT*\n"
            f"Metric: `{alert.metric}`\n{alert.message}\n"
            f"Current: `{alert.current_value}` | Threshold: `{alert.threshold}`"
        )

    def format_status(self, status: dict) -> str:
        return (
            f"OpusGod Status\n"
            f"State: `{status.get('state', 'UNKNOWN')}`\n"
            f"Requests served: `{status.get('requests_served', 0)}`\n"
            f"Revenue: `${status.get('total_revenue_usd', 0):.2f}`"
        )

    async def _send_message(
        self, text: str, parse_mode: str = "Markdown"
    ) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        await self._client.post(
            url,
            json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            },
        )

    async def send_alert(self, alert: VaultAlert) -> None:
        await self._send_message(self.format_alert(alert))

    async def send_status(self, status: dict) -> None:
        await self._send_message(self.format_status(status))

    async def close(self) -> None:
        await self._client.aclose()
