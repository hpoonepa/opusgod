from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto


class SignalType(Enum):
    APR_CHANGE = auto()
    TVL_CHANGE = auto()
    PRICE_MOVE = auto()
    VOLUME_SPIKE = auto()
    LIQUIDATION = auto()


@dataclass
class Signal:
    type: SignalType
    source: str
    value: float
    confidence: float


class SignalAggregator:
    MAX_SIGNALS = 1000

    def __init__(self):
        self.signals: list[Signal] = []

    def add(self, signal: Signal) -> None:
        if len(self.signals) >= self.MAX_SIGNALS:
            self.signals = self.signals[-self.MAX_SIGNALS // 2:]
        self.signals.append(signal)

    def clear(self) -> None:
        self.signals.clear()

    def aggregate(self) -> dict:
        if not self.signals:
            return {"sentiment": "neutral", "score": 0.0, "signal_count": 0, "risk_flags": []}
        weighted_sum = sum(s.value * s.confidence for s in self.signals)
        total_confidence = sum(s.confidence for s in self.signals)
        score = weighted_sum / total_confidence if total_confidence > 0 else 0.0
        if score > 1.0:
            sentiment = "very_bullish"
        elif score > 0.3:
            sentiment = "bullish"
        elif score > -0.3:
            sentiment = "neutral"
        elif score > -1.0:
            sentiment = "bearish"
        else:
            sentiment = "very_bearish"

        # Risk flags based on signal patterns
        risk_flags: list[str] = []
        critical_signals = [s for s in self.signals if s.value <= -0.8]
        if critical_signals:
            risk_flags.append(f"CRITICAL: {len(critical_signals)} severe negative signals")
        tvl_drops = [s for s in self.signals if s.type == SignalType.TVL_CHANGE and s.value < 0]
        if len(tvl_drops) >= 2:
            risk_flags.append("SUSTAINED_TVL_DECLINE: multiple TVL drop signals")
        if score < -0.5 and len(self.signals) >= 3:
            risk_flags.append("BEARISH_CONVERGENCE: multiple sources agree on negative outlook")

        return {
            "sentiment": sentiment,
            "score": round(score, 4),
            "signal_count": len(self.signals),
            "sources": list({s.source for s in self.signals}),
            "risk_flags": risk_flags,
        }
