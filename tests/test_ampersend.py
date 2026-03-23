import pytest
from src.integrations.ampersend import AmpersendClient

@pytest.fixture
def client():
    return AmpersendClient(api_key="test-key")

class TestAmpersend:
    def test_init(self, client):
        assert client.api_key == "test-key"

    def test_create_payment_intent(self, client):
        result = client.create_payment_intent(amount_usd=1.50, description="DeFi analysis")
        assert result["amount"] == 1.50
        assert result["currency"] == "USD"

    def test_verify_payment(self, client):
        intent = client.create_payment_intent(amount_usd=0.50, description="test")
        assert "id" in intent

    def test_get_treasury_status(self, client):
        status = client.get_treasury_status()
        assert "balance" in status
