import pytest
from src.integrations.zyfai import ZyfaiClient

@pytest.fixture
def client():
    return ZyfaiClient(safe_address="0x" + "00" * 20)

class TestZyfai:
    def test_init(self, client):
        assert client.safe_address.startswith("0x")

    def test_get_yield_status(self, client):
        status = client.get_yield_status()
        assert "earned" in status
        assert "deployed" in status

    def test_record_yield(self, client):
        client.record_yield(0.05)
        client.record_yield(0.03)
        assert client.total_earned == pytest.approx(0.08)

    def test_can_fund_operation(self, client):
        client.record_yield(1.0)
        assert client.can_fund(0.5)
        assert not client.can_fund(1.5)
