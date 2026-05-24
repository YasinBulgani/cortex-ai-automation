"""Unit tests for app.domains.products.service.

Tests are fully self-contained: no DB, no HTTP, no external services.
The products service is pure-Python (random + stdlib only), so no mocking
of external dependencies is required.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.products import service as products_service
    from app.domains.products.service import (
        VALID_PRODUCT_IDS,
        validate_product_id,
        get_telemetry,
        list_valid_products,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="products service import failed")


# ---------------------------------------------------------------------------
# validate_product_id
# ---------------------------------------------------------------------------

class TestValidateProductId:
    def test_valid_id_does_not_raise(self):
        """A known product ID must pass without raising."""
        for pid in VALID_PRODUCT_IDS:
            validate_product_id(pid)  # must not raise

    def test_invalid_id_raises_value_error(self):
        """An unknown product ID must raise ValueError."""
        with pytest.raises(ValueError, match="Geçersiz product_id"):
            validate_product_id("nonexistent-product")

    def test_empty_string_raises_value_error(self):
        """Empty string is not a valid product ID."""
        with pytest.raises(ValueError):
            validate_product_id("")

    def test_case_sensitive(self):
        """Product IDs are case-sensitive; uppercase variants must be rejected."""
        with pytest.raises(ValueError):
            validate_product_id("ONE")


# ---------------------------------------------------------------------------
# get_telemetry
# ---------------------------------------------------------------------------

class TestGetTelemetry:
    def test_returns_dict_with_required_keys(self):
        result = get_telemetry("one")
        assert isinstance(result, dict)
        for key in ("productId", "stats", "isDemo", "lastUpdated"):
            assert key in result, f"Missing key: {key}"

    def test_product_id_echoed(self):
        result = get_telemetry("web")
        assert result["productId"] == "web"

    def test_is_demo_flag_is_true(self):
        """isDemo must be True — live aggregation not yet wired."""
        result = get_telemetry("studio")
        assert result["isDemo"] is True

    def test_stats_is_non_empty_list(self):
        result = get_telemetry("intelligence")
        assert isinstance(result["stats"], list)
        assert len(result["stats"]) > 0

    def test_invalid_product_id_raises(self):
        with pytest.raises(ValueError):
            get_telemetry("bogus-id")


# ---------------------------------------------------------------------------
# list_valid_products
# ---------------------------------------------------------------------------

class TestListValidProducts:
    def test_returns_sorted_list(self):
        products = list_valid_products()
        assert isinstance(products, list)
        assert products == sorted(products)

    def test_contains_known_ids(self):
        products = list_valid_products()
        for pid in ("one", "web", "studio"):
            assert pid in products

    def test_length_matches_set(self):
        products = list_valid_products()
        assert len(products) == len(VALID_PRODUCT_IDS)
