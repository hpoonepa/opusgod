import pytest
from unittest.mock import AsyncMock, patch
import httpx
from src.integrations.lido import LidoMonitor, VaultAlert, AlertSeverity


@pytest.fixture
def monitor():
    return LidoMonitor(api_base="https://eth-api.lido.fi")


class TestLidoMonitor:
    def test_init(self, monitor):
        assert "lido.fi" in monitor.api_base

    @pytest.mark.asyncio
    async def test_get_steth_stats(self, monitor):
        mock_resp = httpx.Response(
            200,
            json={"data": {"apr": 3.5, "tvl": 15000000000}},
            request=httpx.Request("GET", "https://test.com"),
        )
        with patch.object(monitor._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            stats = await monitor.get_steth_stats()
            assert stats["apr"] == 3.5

    def test_check_anomaly_normal(self, monitor):
        alerts = monitor.check_anomalies(current_apr=3.5, historical_apr=3.4, tvl=15e9, prev_tvl=14.9e9)
        assert len(alerts) == 0

    def test_check_anomaly_apr_drop_warning(self, monitor):
        # 43% drop → WARNING (between 20% and 50%)
        alerts = monitor.check_anomalies(current_apr=2.0, historical_apr=3.5, tvl=15e9, prev_tvl=15e9)
        assert len(alerts) > 0
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_check_anomaly_apr_drop_critical(self, monitor):
        # 80% drop → CRITICAL (>50%)
        alerts = monitor.check_anomalies(current_apr=0.7, historical_apr=3.5, tvl=15e9, prev_tvl=15e9)
        assert len(alerts) > 0
        assert alerts[0].severity == AlertSeverity.CRITICAL

    def test_check_anomaly_apr_drop_info(self, monitor):
        # 8.5% drop → INFO (between 5% and 20%)
        alerts = monitor.check_anomalies(current_apr=3.2, historical_apr=3.5, tvl=15e9, prev_tvl=15e9)
        assert len(alerts) > 0
        assert alerts[0].severity == AlertSeverity.INFO

    def test_check_anomaly_tvl_drop(self, monitor):
        alerts = monitor.check_anomalies(current_apr=3.5, historical_apr=3.5, tvl=10e9, prev_tvl=15e9)
        assert len(alerts) > 0

    def test_record_data_point(self, monitor):
        monitor.record_data_point(3.5, 15e9)
        monitor.record_data_point(3.4, 14.8e9)
        avg = monitor.get_historical_average()
        assert avg is not None
        assert avg.apr == pytest.approx(3.45)
