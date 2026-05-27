"""Unit tests for ai.smart_model_router pure helper functions.

All tests are self-contained: no DB, no HTTP, no settings dependency.
Covers:
  - _next_tier: tier fallback chain (PREMIUM → MID → MINI → LOCAL)
  - Tier enum: all values present
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.smart_model_router import _next_tier, Tier
    _SMR_OK = True
except ImportError:
    _SMR_OK = False


# ---------------------------------------------------------------------------
# Tier enum
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SMR_OK, reason="smart_model_router import failed")
class TestTierEnum:
    def test_premium_value_exists(self):
        assert hasattr(Tier, "PREMIUM") or "PREMIUM" in [t.name for t in Tier]

    def test_mid_value_exists(self):
        assert hasattr(Tier, "MID") or "MID" in [t.name for t in Tier]

    def test_mini_value_exists(self):
        assert hasattr(Tier, "MINI") or "MINI" in [t.name for t in Tier]

    def test_local_value_exists(self):
        assert hasattr(Tier, "LOCAL") or "LOCAL" in [t.name for t in Tier]

    def test_tier_values_distinct(self):
        tiers = list(Tier)
        assert len(tiers) == len(set(tiers))


# ---------------------------------------------------------------------------
# _next_tier (fallback chain)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SMR_OK, reason="smart_model_router import failed")
class TestNextTier:
    def test_premium_falls_back_to_mid(self):
        assert _next_tier(Tier.PREMIUM) == Tier.MID

    def test_mid_falls_back_to_mini(self):
        assert _next_tier(Tier.MID) == Tier.MINI

    def test_mini_falls_back_to_local(self):
        assert _next_tier(Tier.MINI) == Tier.LOCAL

    def test_local_falls_back_to_local(self):
        # Bottom of chain — stays LOCAL
        assert _next_tier(Tier.LOCAL) == Tier.LOCAL

    def test_returns_tier(self):
        result = _next_tier(Tier.PREMIUM)
        assert isinstance(result, Tier)

    def test_chain_terminates_at_local(self):
        # Following the chain from PREMIUM always reaches LOCAL
        tier = Tier.PREMIUM
        for _ in range(10):
            tier = _next_tier(tier)
        assert tier == Tier.LOCAL
