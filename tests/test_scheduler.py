import pytest
from unittest.mock import AsyncMock
from src.agent.scheduler import AgentScheduler


class TestAgentScheduler:
    def test_register_task(self):
        scheduler = AgentScheduler()
        task = AsyncMock()
        scheduler.register("vault_check", task, interval_seconds=300)
        assert "vault_check" in scheduler.tasks

    def test_register_duplicate_raises(self):
        scheduler = AgentScheduler()
        scheduler.register("test", AsyncMock(), interval_seconds=60)
        with pytest.raises(ValueError, match="already registered"):
            scheduler.register("test", AsyncMock(), interval_seconds=60)

    def test_list_tasks(self):
        scheduler = AgentScheduler()
        scheduler.register("a", AsyncMock(), interval_seconds=60)
        scheduler.register("b", AsyncMock(), interval_seconds=300)
        tasks = scheduler.list_tasks()
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_run_once(self):
        scheduler = AgentScheduler()
        mock_fn = AsyncMock()
        scheduler.register("test_task", mock_fn, interval_seconds=60)
        await scheduler.run_once("test_task")
        mock_fn.assert_called_once()
