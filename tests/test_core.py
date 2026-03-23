import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.agent.core import OpusGodAgent
from src.agent.state import AgentState
from src.integrations.lido import VaultAlert, AlertSeverity


class TestOpusGodAgent:
    @pytest.fixture
    def agent(self):
        with patch("src.agent.core.get_settings") as mock_settings, \
             patch("src.integrations.telegram.Bot"):
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
            s.mech_target_address = "0x77af31De935740567Cf4fF1986D04B2c964A786a"
            s.ampersend_api_key = "test"
            s.ampersend_max_payment = 1.0
            s.zyfai_api_key = "test"
            s.zyfai_safe_address = "0x" + "00" * 20
            s.poll_interval_seconds = 30
            s.vault_check_interval_seconds = 300
            s.pearl_port = 8716
            s.lido_api_base = "https://eth-api.lido.fi"
            s.slice_contract_address = ""
            s.demo_mode = False
            mock_settings.return_value = s
            return OpusGodAgent()

    def test_init_state_is_startup(self, agent):
        assert agent.ctx.state == AgentState.STARTUP

    def test_has_state_lock(self, agent):
        """Verify asyncio.Lock exists for thread-safe state transitions."""
        import asyncio
        assert isinstance(agent._state_lock, asyncio.Lock)

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
        with patch.object(agent.bankr, "chat", new_callable=AsyncMock, return_value='{"result": "test"}'):
            result = await agent.handle_mech_request("yield_optimizer", "test query")
            # handle_mech_request now returns a tuple from the tool
            assert isinstance(result, tuple)
            assert agent.ctx.requests_served == 1
            assert agent.ctx.state == AgentState.IDLE  # returns to IDLE after serving

    @pytest.mark.asyncio
    async def test_handle_mech_request_error_recovery(self, agent):
        """Verify agent recovers to IDLE on mech request failure."""
        agent.ctx.transition(AgentState.IDLE)
        with patch.object(agent.mech_server, "handle_request",
                          new_callable=AsyncMock, side_effect=Exception("Tool failed")):
            with pytest.raises(Exception, match="Tool failed"):
                await agent.handle_mech_request("yield_optimizer", "test query")
            assert agent.ctx.state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_hire_agent_error_recovery(self, agent):
        """Verify agent recovers to IDLE on hire failure."""
        agent.ctx.transition(AgentState.IDLE)
        with patch.object(agent.mech_client, "send_request",
                          new_callable=AsyncMock, side_effect=Exception("On-chain failed")):
            with pytest.raises(Exception, match="On-chain failed"):
                await agent.hire_agent("risk_assessor", "test query")
            assert agent.ctx.state == AgentState.IDLE

    def test_sign_request_returns_headers(self, agent):
        headers = agent.sign_request("GET", "https://example.com/api")
        assert "Signature-Input" in headers
        assert "Signature" in headers

    def test_sign_request_with_body(self, agent):
        headers = agent.sign_request("POST", "https://example.com/api", '{"data":1}')
        assert "Signature-Input" in headers
        assert "Content-Digest" in headers

    def test_slice_hook_initialized(self, agent):
        assert agent.slice_hook is not None
        config = agent.slice_hook.get_pricing_config()
        assert "hook_address" in config
        assert "base_price" in config

    def test_get_revenue_report_initial(self, agent):
        report = agent.get_revenue_report()
        assert report["mech_fees"] == 0.0
        assert report["zyfai_yield"] == 0.0
        assert report["slice_commerce"] == 0.0
        assert report["total_revenue_usd"] == 0.0
        assert "ampersend_treasury" in report
        assert "zyfai_pnl" in report
        assert "expenses" in report
        assert "net_pnl" in report
        assert "gas_costs" in report["expenses"]
        assert "mech_hiring" in report["expenses"]

    def test_get_revenue_report_self_sustaining_requires_revenue(self, agent):
        """self_sustaining should be False when both revenue and expenses are 0."""
        report = agent.get_revenue_report()
        assert report["self_sustaining"] is False

    def test_get_revenue_report_self_sustaining_positive(self, agent):
        """self_sustaining should be True when net P&L is positive."""
        agent._mech_revenue = 10.0
        agent._update_total_revenue()
        report = agent.get_revenue_report()
        assert report["self_sustaining"] is True
        assert report["net_pnl"] > 0

    def test_record_zyfai_yield(self, agent):
        agent.record_zyfai_yield(5.0)
        report = agent.get_revenue_report()
        assert report["zyfai_yield"] == 5.0
        assert report["total_revenue_usd"] == 5.0
        assert agent.ctx.total_revenue_usd == 5.0

    def test_record_slice_revenue(self, agent):
        agent.record_slice_revenue(3.0)
        report = agent.get_revenue_report()
        assert report["slice_commerce"] == 3.0
        assert report["total_revenue_usd"] == 3.0

    def test_revenue_aggregation(self, agent):
        agent.record_zyfai_yield(2.0)
        agent.record_slice_revenue(3.0)
        agent._mech_revenue = 1.5
        agent._update_total_revenue()
        report = agent.get_revenue_report()
        assert report["total_revenue_usd"] == 6.5
        assert report["mech_fees"] == 1.5
        assert report["zyfai_yield"] == 2.0
        assert report["slice_commerce"] == 3.0

    @pytest.mark.asyncio
    async def test_handle_mech_request_tracks_revenue(self, agent):
        agent.ctx.transition(AgentState.IDLE)
        with patch.object(agent.bankr, "chat", new_callable=AsyncMock, return_value='{"result": "ok"}'):
            await agent.handle_mech_request("yield_optimizer", "query")
            assert agent._mech_revenue > 0
            assert agent._slice_revenue > 0  # Slice revenue now wired in
            assert agent.ctx.total_revenue_usd > 0
            assert agent.ctx.state == AgentState.IDLE  # returns to IDLE after serving
            treasury = agent.ampersend.get_treasury_status()
            assert treasury["total_payments"] >= 0
            assert treasury["scheme"] == "eip712"

    @pytest.mark.asyncio
    async def test_check_vaults_transitions_monitoring_idle(self, agent):
        agent.ctx.transition(AgentState.IDLE)
        with patch.object(
            agent.lido, "get_steth_stats", new_callable=AsyncMock,
            return_value={"apr": 3.5, "tvl": 1e10},
        ):
            await agent.check_vaults()
            assert agent.ctx.state == AgentState.IDLE
            assert agent.ctx.vaults_monitored == 1

    @pytest.mark.asyncio
    async def test_check_vaults_error_returns_idle(self, agent):
        agent.ctx.transition(AgentState.IDLE)
        with patch.object(
            agent.lido, "get_steth_stats", new_callable=AsyncMock,
            side_effect=Exception("API down"),
        ):
            await agent.check_vaults()
            assert agent.ctx.state == AgentState.IDLE
            assert agent.ctx.last_error == "API down"

    @pytest.mark.asyncio
    async def test_check_vaults_anomaly_triggers_analysis(self, agent):
        agent.ctx.transition(AgentState.IDLE)
        agent._prev_apr = 5.0
        agent._prev_tvl = 1e10

        with patch.object(
            agent.lido, "get_steth_stats", new_callable=AsyncMock,
            return_value={"apr": 2.0, "tvl": 5e9},
        ), patch.object(
            agent.telegram, "send_alert", new_callable=AsyncMock,
        ) as mock_alert, patch.object(
            agent.analyzer, "analyze_protocol", new_callable=AsyncMock,
            return_value={"protocol": "lido", "analysis": "risk elevated"},
        ):
            await agent.check_vaults()
            assert mock_alert.call_count > 0
            assert agent.ctx.state == AgentState.IDLE
            assert agent.signals.aggregate()["signal_count"] > 0

    @pytest.mark.asyncio
    async def test_hire_agent_transitions(self, agent):
        agent.ctx.transition(AgentState.IDLE)

        async def mock_send(tool, query):
            agent.mech_client.requests_sent += 1
            return "0xhash"

        with patch.object(agent.mech_client, "send_request", side_effect=mock_send):
            tx = await agent.hire_agent("yield_optimizer", "test query")
            assert isinstance(tx, str)
            assert agent.ctx.requests_hired == 1
            assert agent.ctx.state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_startup_signs_erc8128(self, agent):
        with patch.object(agent.signer, "sign_request", return_value={
            "Signature-Input": "sig1=...",
            "Signature": "sig1=:abc:",
        }) as mock_sign:
            await agent.startup()
            mock_sign.assert_called_once()
            assert agent.ctx.state == AgentState.IDLE
