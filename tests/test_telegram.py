import pytest
from unittest.mock import AsyncMock, patch

from src.integrations.lido import AlertSeverity, VaultAlert
from src.integrations.telegram import TelegramNotifier


@pytest.fixture
def notifier():
    return TelegramNotifier(bot_token="test-token", chat_id="123456")


class TestTelegramNotifier:
    def test_format_alert(self, notifier):
        alert = VaultAlert(
            severity=AlertSeverity.HIGH,
            metric="apr",
            message="APR dropped 25%: 3.5% -> 2.6%",
            current_value=2.6,
            threshold=2.8,
        )
        text = notifier.format_alert(alert)
        assert "HIGH" in text
        assert "APR" in text.upper()

    def test_format_status(self, notifier):
        status = {
            "state": "IDLE",
            "requests_served": 42,
            "total_revenue_usd": 1.5,
        }
        text = notifier.format_status(status)
        assert "42" in text

    @pytest.mark.asyncio
    async def test_send_calls_bot(self, notifier):
        with patch.object(
            notifier, "_send_message", new_callable=AsyncMock
        ) as mock_send:
            await notifier.send_alert(
                VaultAlert(
                    severity=AlertSeverity.LOW,
                    metric="test",
                    message="test msg",
                    current_value=1.0,
                    threshold=2.0,
                )
            )
            mock_send.assert_called_once()
