import pytest
from unittest.mock import AsyncMock
from src.analysis.defi_analyzer import DeFiAnalyzer


@pytest.fixture
def analyzer():
    mock_bankr = AsyncMock()
    mock_bankr.analyze_defi.return_value = '{"risk_level": "medium", "yield_apy": 5.2}'
    return DeFiAnalyzer(bankr=mock_bankr)


class TestDeFiAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_protocol(self, analyzer):
        result = await analyzer.analyze_protocol("Aave v3")
        assert isinstance(result, dict)
        assert "protocol" in result

    @pytest.mark.asyncio
    async def test_compare_yields(self, analyzer):
        result = await analyzer.compare_yields(["Aave", "Compound", "Lido"])
        assert isinstance(result, dict)
        assert "comparison" in result

    @pytest.mark.asyncio
    async def test_get_market_overview(self, analyzer):
        result = await analyzer.get_market_overview()
        assert isinstance(result, dict)
