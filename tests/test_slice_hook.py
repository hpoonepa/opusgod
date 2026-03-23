import pytest
from src.integrations.slice_hook import SliceHookManager

@pytest.fixture
def manager():
    return SliceHookManager(hook_address="0x" + "00" * 20)

class TestSliceHook:
    def test_init(self, manager):
        assert manager.hook_address.startswith("0x")

    def test_calculate_dynamic_price(self, manager):
        price = manager.calculate_dynamic_price(base_price_usd=1.0, demand_factor=1.5, market_volatility=0.2)
        assert price > 0
        assert price != 1.0

    def test_price_increases_with_demand(self, manager):
        low = manager.calculate_dynamic_price(1.0, demand_factor=1.0, market_volatility=0.1)
        high = manager.calculate_dynamic_price(1.0, demand_factor=2.0, market_volatility=0.1)
        assert high > low

    def test_get_pricing_config(self, manager):
        config = manager.get_pricing_config()
        assert "base_price" in config
