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
    def __init__(self):
        self.signals: list[Signal] = []

    def add(self, signal: Signal) -> None:
        self.signals.append(signal)

    def clear(self) -> None:
        self.signals.clear()

    def aggregate(self) -> dict:
        if not self.signals:
            return {"sentiment": "neutral", "score": 0.0, "signal_count": 0}
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
        return {
            "sentiment": sentiment,
            "score": round(score, 4),
            "signal_count": len(self.signals),
            "sources": list({s.source for s in self.signals}),
        }
