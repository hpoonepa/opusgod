import pytest
from src.agent.state import AgentState, AgentContext, TRANSITIONS


class TestAgentState:
    def test_all_states_in_transitions(self):
        for state in AgentState:
            assert state in TRANSITIONS

    def test_startup_can_only_go_to_idle(self):
        ctx = AgentContext()
        assert ctx.state == AgentState.STARTUP
        assert ctx.can_transition(AgentState.IDLE)
        assert not ctx.can_transition(AgentState.SERVING)

    def test_idle_can_go_to_serving_monitoring_hiring(self):
        ctx = AgentContext(state=AgentState.IDLE)
        assert ctx.can_transition(AgentState.SERVING)
        assert ctx.can_transition(AgentState.MONITORING)
        assert ctx.can_transition(AgentState.HIRING)
        assert ctx.can_transition(AgentState.SHUTDOWN)

    def test_transition_updates_state(self):
        ctx = AgentContext()
        ctx.transition(AgentState.IDLE)
        assert ctx.state == AgentState.IDLE

    def test_invalid_transition_raises(self):
        ctx = AgentContext()
        with pytest.raises(ValueError, match="Invalid transition"):
            ctx.transition(AgentState.ANALYZING)

    def test_context_tracks_metrics(self):
        ctx = AgentContext()
        ctx.requests_served = 5
        ctx.total_revenue_usd = 1.25
        assert ctx.requests_served == 5
        assert ctx.total_revenue_usd == 1.25
