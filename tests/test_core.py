import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.agent.core import OpusGodAgent
from src.agent.state import AgentState


class TestOpusGodAgent:
    @pytest.fixture
    def agent(self):
        with patch("src.agent.core.get_settings") as mock_settings:
            s = MagicMock()
            s.bankr_api_key = "test"
            s.bankr_endpoint = "https://test.com"
            s.bankr_model = "gpt-4o"
            s.telegram_bot_token = "test"
            s.telegram_chat_id = "123"
            s.private_key = "0x" + "ab" * 32
            s.gnosis_rpc = "https://rpc.gnosischain.com"
            s.base_rpc = "https://mainnet.base.org"
            s.mech_server_port = 8080
            s.mech_target_address = "0x" + "00" * 20
            s.ampersend_api_key = "test"
            s.zyfai_safe_address = "0x" + "00" * 20
            s.poll_interval_seconds = 30
            s.vault_check_interval_seconds = 300
            s.pearl_port = 8716
            mock_settings.return_value = s
            return OpusGodAgent()

    def test_init_state_is_startup(self, agent):
        assert agent.ctx.state == AgentState.STARTUP

    @pytest.mark.asyncio
    async def test_startup_transitions_to_idle(self, agent):
        await agent.startup()
        assert agent.ctx.state == AgentState.IDLE

    def test_status_returns_dict(self, agent):
        status = agent.status()
        assert "state" in status
        assert status["state"] == "STARTUP"

    @pytest.mark.asyncio
    async def test_handle_mech_request(self, agent):
        agent.ctx.transition(AgentState.IDLE)
        agent.ctx.transition(AgentState.SERVING)
        with patch.object(agent.bankr, "chat", new_callable=AsyncMock, return_value='{"result": "test"}'):
            result = await agent.handle_mech_request("yield_optimizer", "test query")
            assert isinstance(result, str)
            assert agent.ctx.requests_served == 1
