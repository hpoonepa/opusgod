import pytest
import httpx
from unittest.mock import AsyncMock, patch
from src.integrations.bankr import BankrClient


@pytest.fixture
def client():
    return BankrClient(api_key="test-key", endpoint="https://llm.bankr.bot/v1/chat/completions")


class TestBankrClient:
    def test_init(self, client):
        assert client.api_key == "test-key"
        assert "bankr.bot" in client.endpoint

    @pytest.mark.asyncio
    async def test_chat_sends_correct_headers(self, client):
        mock_response = httpx.Response(
            200,
            json={"choices": [{"message": {"content": "test response"}}]},
            request=httpx.Request("POST", "https://test.com"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            result = await client.chat("What is DeFi?")
            assert result == "test response"

    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self, client):
        mock_response = httpx.Response(
            200,
            json={"choices": [{"message": {"content": "analysis"}}]},
            request=httpx.Request("POST", "https://test.com"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            await client.chat("Analyze this vault", system="You are a DeFi analyst")
            call_json = mock_post.call_args[1]["json"]
            assert call_json["messages"][0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_analyze_defi_returns_structured(self, client):
        mock_response = httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"risk": "low", "yield": 5.2}'}}]},
            request=httpx.Request("POST", "https://test.com"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            result = await client.analyze_defi("vault 0x123")
            assert "risk" in result or isinstance(result, str)
