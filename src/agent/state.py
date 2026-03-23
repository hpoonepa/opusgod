from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class AgentState(Enum):
    STARTUP = auto()
    IDLE = auto()
    SERVING = auto()
    MONITORING = auto()
    ANALYZING = auto()
    HIRING = auto()
    SHUTDOWN = auto()


TRANSITIONS: dict[AgentState, list[AgentState]] = {
    AgentState.STARTUP: [AgentState.IDLE],
    AgentState.IDLE: [AgentState.SERVING, AgentState.MONITORING, AgentState.HIRING, AgentState.SHUTDOWN],
    AgentState.SERVING: [AgentState.ANALYZING, AgentState.IDLE],
    AgentState.MONITORING: [AgentState.ANALYZING, AgentState.IDLE],
    AgentState.ANALYZING: [AgentState.HIRING, AgentState.IDLE],
    AgentState.HIRING: [AgentState.IDLE],
    AgentState.SHUTDOWN: [],
}


@dataclass
class AgentContext:
    state: AgentState = AgentState.STARTUP
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    requests_served: int = 0
    requests_hired: int = 0
    vaults_monitored: int = 0
    total_revenue_usd: float = 0.0
    last_error: Optional[str] = None

    def can_transition(self, target: AgentState) -> bool:
        return target in TRANSITIONS.get(self.state, [])

    def transition(self, target: AgentState) -> None:
        if not self.can_transition(target):
            raise ValueError(f"Invalid transition: {self.state.name} -> {target.name}")
        self.state = target

    def to_dict(self) -> dict:
        return {
            "state": self.state.name,
            "uptime_seconds": (datetime.now(timezone.utc) - self.started_at).total_seconds(),
            "requests_served": self.requests_served,
            "requests_hired": self.requests_hired,
            "vaults_monitored": self.vaults_monitored,
            "total_revenue_usd": self.total_revenue_usd,
            "last_error": self.last_error,
        }
