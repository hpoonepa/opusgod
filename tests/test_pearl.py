import pytest
from src.pearl.compat import create_pearl_app, format_performance


class TestPearl:
    @pytest.mark.asyncio
    async def test_create_app(self):
        app = create_pearl_app(agent_status_fn=lambda: {"state": "IDLE"})
        assert app is not None

    def test_format_performance_json(self):
        perf = format_performance({"state": "IDLE", "requests_served": 42, "total_revenue_usd": 1.5})
        assert perf["status"] == "running"
        assert perf["requests_served"] == 42
