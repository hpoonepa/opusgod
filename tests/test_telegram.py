import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.integrations.lido import AlertSeverity, VaultAlert
from src.integrations.telegram import TelegramNotifier


@pytest.fixture
def notifier():
    with patch("src.integrations.telegram.Bot") as MockBot:
        MockBot.return_value = MagicMock()
        n = TelegramNotifier(bot_token="test-token", chat_id="123456")
        return n


class TestTelegramNotifier:
    def test_format_alert(self, notifier):
        alert = VaultAlert(
            severity=AlertSeverity.WARNING,
            metric="apr",
            message="APR dropped 25%: 3.5% -> 2.6%",
            current_value=2.6,
            threshold=2.8,
        )
        text = notifier.format_alert(alert)
        assert "WARNING" in text
        assert "apr" in text

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
                    severity=AlertSeverity.INFO,
                    metric="test",
                    message="test msg",
                    current_value=1.0,
                    threshold=2.0,
                )
            )
            mock_send.assert_called_once()

    def test_format_anomaly_alert(self, notifier):
        anomalies = [
            VaultAlert(severity=AlertSeverity.CRITICAL, metric="apr",
                        message="APR crashed", current_value=0.5, threshold=2.0),
            VaultAlert(severity=AlertSeverity.WARNING, metric="tvl",
                        message="TVL dropped", current_value=5e9, threshold=10e9),
        ]
        text = notifier.format_anomaly_alert(anomalies)
        assert "2 Anomalies" in text
        assert "APR" in text.upper()
