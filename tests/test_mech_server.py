import pytest
from unittest.mock import AsyncMock
from src.mech.server import MechServer


@pytest.fixture
def server():
    mock_bankr = AsyncMock()
    mock_bankr.chat.return_value = '{"result": "test"}'
    return MechServer(bankr=mock_bankr, port=8080)


class TestMechServer:
    def test_init(self, server):
        assert server.port == 8080
        assert server.requests_served == 0

    @pytest.mark.asyncio
    async def test_handle_request(self, server):
        result = await server.handle_request("yield_optimizer", "Compare Aave vs Compound")
        assert isinstance(result, str)
        assert server.requests_served == 1

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, server):
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.handle_request("nonexistent_tool", "test")

    def test_list_tools(self, server):
        tools = server.list_tools()
        assert len(tools) == 5
        assert all("name" in t and "description" in t for t in tools)

    @pytest.mark.asyncio
    async def test_tracks_request_count(self, server):
        await server.handle_request("risk_assessor", "test query")
        await server.handle_request("vault_monitor", "test query 2")
        assert server.requests_served == 2
