import pytest
from src.integrations.zyfai import ZyfaiClient


@pytest.fixture
def client():
    return ZyfaiClient(api_key="test-key", safe_address="0x" + "00" * 20)


class TestZyfai:
    def test_init(self, client):
        assert client.safe_address.startswith("0x")
        assert client.api_key == "test-key"

    def test_get_yield_status_sync_fallback(self, client):
        """Test that yield status works via the sync P&L path."""
        client.record_yield(1.0)
        client.record_spend(0.3)
        pnl = client.get_pnl()
        assert pnl["revenue"] == 1.0
        assert pnl["expenses"] == 0.3
        assert pnl["net"] == pytest.approx(0.7)

    def test_record_yield(self, client):
        client.record_yield(0.05)
        client.record_yield(0.03)
        assert client.total_earned == pytest.approx(0.08)

    def test_can_fund_operation(self, client):
        client.record_yield(1.0)
        assert client.can_fund(0.5)
        assert not client.can_fund(1.5)

    def test_record_spend(self, client):
        client.record_yield(2.0)
        client.record_spend(0.5)
        assert client.total_spent == 0.5
        assert client.can_fund(1.0)

    def test_operations_tracked(self, client):
        client.record_yield(1.0)
        client.record_spend(0.5)
        pnl = client.get_pnl()
        assert pnl["operations"] == 2
