import pytest
from src.analysis.vault_scorer import VaultScorer, VaultScore


class TestVaultScorer:
    def test_score_high_yield_low_risk(self):
        score = VaultScorer.score(apy=8.0, tvl=5e9, age_days=365, audit_count=3)
        assert score.overall >= 7.0
        assert score.yield_score >= 7.0

    def test_score_low_yield_high_risk(self):
        score = VaultScorer.score(apy=0.5, tvl=1e6, age_days=7, audit_count=0)
        assert score.overall < 5.0
        assert score.risk_score >= 5.0

    def test_score_returns_vault_score(self):
        score = VaultScorer.score(apy=5.0, tvl=1e9, age_days=180, audit_count=2)
        assert isinstance(score, VaultScore)
        assert 0 <= score.overall <= 10

    def test_rank_vaults(self):
        vaults = [
            {"name": "A", "apy": 8.0, "tvl": 5e9, "age_days": 365, "audit_count": 3},
            {"name": "B", "apy": 0.5, "tvl": 1e6, "age_days": 7, "audit_count": 0},
            {"name": "C", "apy": 5.0, "tvl": 1e9, "age_days": 180, "audit_count": 2},
        ]
        ranked = VaultScorer.rank(vaults)
        assert ranked[0]["name"] == "A"
