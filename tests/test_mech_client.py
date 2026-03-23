import pytest
from unittest.mock import AsyncMock, patch
from src.mech.client import MechClient


@pytest.fixture
def client():
    return MechClient(private_key="0x" + "ab" * 32, target_mech="0x77af31De935740567Cf4fF1986D04B2c964A786a")


class TestMechClient:
    def test_init(self, client):
        assert client.target_mech.startswith("0x")
        assert client.requests_sent == 0

    @pytest.mark.asyncio
    async def test_send_request_tracks_count(self, client):
        with patch.object(client, "_send_onchain", new_callable=AsyncMock, return_value="0xhash"):
            result = await client.send_request("yield_optimizer", "Best yield on stETH?")
            assert result == "0xhash"
            assert client.requests_sent == 1

    @pytest.mark.asyncio
    async def test_send_multiple_requests(self, client):
        with patch.object(client, "_send_onchain", new_callable=AsyncMock, return_value="0xhash"):
            for i in range(5):
                await client.send_request("risk_assessor", f"Query {i}")
            assert client.requests_sent == 5

    def test_build_request_payload(self, client):
        payload = client.build_request_payload("vault_monitor", "Check Aave v3")
        assert payload["tool"] == "vault_monitor"
        assert payload["query"] == "Check Aave v3"
        assert "sender" in payload
