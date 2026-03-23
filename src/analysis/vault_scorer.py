from __future__ import annotations
from dataclasses import dataclass


@dataclass
class VaultScore:
    yield_score: float
    risk_score: float
    liquidity_score: float
    overall: float


class VaultScorer:
    @staticmethod
    def score(apy: float, tvl: float, age_days: int, audit_count: int) -> VaultScore:
        yield_score = min(apy, 10.0)
        tvl_factor = min(tvl / 1e9, 1.0)
        audit_factor = min(audit_count / 3.0, 1.0)
        age_factor = min(age_days / 365.0, 1.0)
        safety = (tvl_factor * 0.4 + audit_factor * 0.35 + age_factor * 0.25)
        risk_score = (1.0 - safety) * 10.0
        liquidity_score = min(tvl / 5e8, 10.0)
        overall = (yield_score * 0.35 + (10 - risk_score) * 0.40 + liquidity_score * 0.25)
        return VaultScore(
            yield_score=round(yield_score, 2),
            risk_score=round(risk_score, 2),
            liquidity_score=round(liquidity_score, 2),
            overall=round(overall, 2),
        )

    @staticmethod
    def rank(vaults: list[dict]) -> list[dict]:
        scored = []
        for v in vaults:
            s = VaultScorer.score(v["apy"], v["tvl"], v["age_days"], v["audit_count"])
            scored.append({**v, "score": s.overall, "details": s})
        return sorted(scored, key=lambda x: x["score"], reverse=True)
