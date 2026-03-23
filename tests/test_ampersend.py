import pytest
from src.integrations.ampersend import AmpersendClient


@pytest.fixture
def client():
    return AmpersendClient(api_key="test-key", private_key="0x" + "ab" * 32)


class TestAmpersend:
    def test_init(self, client):
        assert client.api_key == "test-key"
        assert client._account is not None

    def test_create_payment_intent(self, client):
        result = client.create_payment_intent(amount_usd=1.50, description="DeFi analysis")
        assert result["amount"] == 1.50
        assert result["currency"] == "USD"
        assert "id" in result

    def test_complete_payment(self, client):
        intent = client.create_payment_intent(amount_usd=0.50, description="test")
        assert client.complete_payment(intent["id"])
        assert not client.complete_payment("nonexistent")

    def test_get_treasury_status(self, client):
        status = client.get_treasury_status()
        assert "total_spent" in status
        assert "total_payments" in status
        assert "address" in status

    def test_treasury_tracks_completed(self, client):
        intent = client.create_payment_intent(amount_usd=2.0, description="test")
        client.complete_payment(intent["id"])
        status = client.get_treasury_status()
        assert status["total_payments"] == 1
        assert status["total_spent"] == 2.0

    def test_parse_402(self, client):
        import httpx
        resp = httpx.Response(
            402,
            headers={
                "X-PAYMENT-AMOUNT": "0.01",
                "X-PAYMENT-TOKEN": "ETH",
                "X-PAYMENT-RECIPIENT": "0x123",
            },
            request=httpx.Request("GET", "https://test.com"),
        )
        details = client._parse_402(resp)
        assert details["amount"] == "0.01"
        assert details["token"] == "ETH"

    def test_sign_payment(self, client):
        details = {"amount": "0.01", "token": "ETH", "recipient": "0x123",
                    "network": "8453", "nonce": "test-nonce"}
        proof = client._sign_payment(details)
        assert "signature" in proof
        assert "sender" in proof
        assert proof["chainId"] == 8453
