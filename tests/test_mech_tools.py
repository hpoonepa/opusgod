import pytest
from unittest.mock import AsyncMock
from src.mech.tools import TOOL_REGISTRY, yield_optimizer, risk_assessor


class TestToolRegistry:
    def test_all_five_tools_registered(self):
        assert len(TOOL_REGISTRY) == 5
        expected = {"yield_optimizer", "risk_assessor", "vault_monitor", "protocol_analyzer", "portfolio_rebalancer"}
        assert set(TOOL_REGISTRY.keys()) == expected

    def test_tools_have_descriptions(self):
        for name, tool in TOOL_REGISTRY.items():
            assert tool.get("description"), f"{name} missing description"
            assert tool.get("handler"), f"{name} missing handler"

    @pytest.mark.asyncio
    async def test_yield_optimizer_returns_tuple(self):
        mock_bankr = AsyncMock()
        mock_bankr.chat.return_value = '{"best_yield": "5.2%"}'
        result = await yield_optimizer("Compare Aave vs Compound", bankr=mock_bankr)
        assert isinstance(result, tuple)
        assert len(result) == 5
        assert result[0] == '{"best_yield": "5.2%"}'  # result text
        assert result[2] is None  # no error
        assert result[3]["tool"] == "yield_optimizer"  # metadata

    @pytest.mark.asyncio
    async def test_risk_assessor_returns_tuple(self):
        mock_bankr = AsyncMock()
        mock_bankr.chat.return_value = '{"risk_score": 3}'
        result = await risk_assessor("Assess vault 0x123", bankr=mock_bankr)
        assert isinstance(result, tuple)
        assert result[0] == '{"risk_score": 3}'
        assert result[3]["tool"] == "risk_assessor"

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        mock_bankr = AsyncMock()
        mock_bankr.chat.side_effect = Exception("API error")
        result = await yield_optimizer("test", bankr=mock_bankr)
        assert isinstance(result, tuple)
        assert result[0] == ""  # empty result
        assert result[2] == "API error"  # error message
