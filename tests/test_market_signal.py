import pytest
from src.analysis.market_signal import SignalAggregator, Signal, SignalType


class TestSignalAggregator:
    def test_add_signal(self):
        agg = SignalAggregator()
        agg.add(Signal(type=SignalType.APR_CHANGE, source="lido", value=-0.5, confidence=0.9))
        assert len(agg.signals) == 1

    def test_aggregate_empty(self):
        agg = SignalAggregator()
        result = agg.aggregate()
        assert result["sentiment"] == "neutral"

    def test_aggregate_bearish(self):
        agg = SignalAggregator()
        agg.add(Signal(type=SignalType.APR_CHANGE, source="lido", value=-2.0, confidence=0.9))
        agg.add(Signal(type=SignalType.TVL_CHANGE, source="aave", value=-0.3, confidence=0.8))
        result = agg.aggregate()
        assert result["sentiment"] in ("bearish", "very_bearish")

    def test_aggregate_bullish(self):
        agg = SignalAggregator()
        agg.add(Signal(type=SignalType.APR_CHANGE, source="lido", value=1.5, confidence=0.9))
        agg.add(Signal(type=SignalType.TVL_CHANGE, source="aave", value=0.2, confidence=0.8))
        result = agg.aggregate()
        assert result["sentiment"] in ("bullish", "very_bullish")
