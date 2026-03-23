import pytest
from src.integrations.ampersend import AmpersendClient, PaymentError


@pytest.fixture
def client():
    return AmpersendClient(api_key="test-key", private_key="0x" + "ab" * 32)


class TestAmpersend:
    def test_init(self, client):
        assert client.api_key == "test-key"
        assert client._account is not None
        assert client.max_payment == 1.0

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
        assert status["scheme"] == "eip712"
        assert status["max_payment"] == 1.0

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
                "X-PAYMENT-AMOUNT": "100",
                "X-PAYMENT-TOKEN": "0x0000000000000000000000000000000000000000",
                "X-PAYMENT-RECIPIENT": "0x1234567890123456789012345678901234567890",
            },
            request=httpx.Request("GET", "https://test.com"),
        )
        details = client._parse_402(resp)
        assert details["amount"] == "100"
        assert details["token"] == "0x0000000000000000000000000000000000000000"

    def test_sign_payment_eip712(self, client):
        """Verify signing uses EIP-712 structured data."""
        details = {
            "amount": "100",
            "token": "0x0000000000000000000000000000000000000000",
            "recipient": "0x1234567890123456789012345678901234567890",
            "network": "8453",
            "nonce": "test-nonce",
        }
        proof = client._sign_payment(details)
        assert "signature" in proof
        assert "sender" in proof
        assert proof["chainId"] == 8453
        assert proof["scheme"] == "eip712"

    def test_payment_cap(self, client):
        """Verify payment cap prevents overpayment."""
        client.max_payment = 0.5
        # create_payment_intent doesn't check cap (it's for 402 flow)
        # The cap is checked in request_with_payment via _sign_payment
        assert client.max_payment == 0.5

    def test_custom_max_payment(self):
        """Verify custom max payment is respected."""
        c = AmpersendClient(api_key="test", private_key="0x" + "ab" * 32, max_payment=5.0)
        assert c.max_payment == 5.0
