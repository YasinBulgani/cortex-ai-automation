"""Görev 5: Feature flags ve BulkCaseUpdate şema testleri.

DB/Redis/HTTP bağımlılığı yok — pure şema testleri.
"""
from __future__ import annotations


def test_flag_key_validation():
    """FlagUpdate şeması enabled alanını doğru parse eder."""
    from app.domains.feature_flags.schemas import FlagUpdate

    flag = FlagUpdate(enabled=True, description="test")
    assert flag.enabled is True
    assert flag.description == "test"


def test_flag_update_partial():
    """FlagUpdate kısmi güncellemeye izin verir (tüm alanlar opsiyonel)."""
    from app.domains.feature_flags.schemas import FlagUpdate

    flag = FlagUpdate(enabled=False)
    assert flag.enabled is False
    assert flag.description is None
    assert flag.percent is None


def test_bulk_case_update_schema():
    """BulkCaseUpdate şeması doğru alanları parse eder."""
    from app.domains.test_management.schemas import BulkCaseUpdate

    payload = BulkCaseUpdate(case_ids=["a", "b"], status="active")
    assert len(payload.case_ids) == 2
    assert payload.status == "active"
    assert payload.tags_add == []
    assert payload.tags_remove == []
    assert payload.priority is None


def test_bulk_case_update_with_tags():
    """BulkCaseUpdate tag ekleme/çıkarma alanlarını parse eder."""
    from app.domains.test_management.schemas import BulkCaseUpdate

    payload = BulkCaseUpdate(
        case_ids=["x", "y", "z"],
        priority="high",
        tags_add=["regression", "smoke"],
        tags_remove=["draft"],
    )
    assert len(payload.case_ids) == 3
    assert payload.priority == "high"
    assert "regression" in payload.tags_add
    assert "draft" in payload.tags_remove


def test_bulk_case_update_empty_tags_default():
    """BulkCaseUpdate tags_add/tags_remove varsayılan olarak boş liste."""
    from app.domains.test_management.schemas import BulkCaseUpdate

    payload = BulkCaseUpdate(case_ids=["a"])
    assert payload.tags_add == []
    assert payload.tags_remove == []


def test_flag_update_allow_tenants_deduplication():
    """FlagUpdate allow_tenants tekrarlı girişleri temizler."""
    from app.domains.feature_flags.schemas import FlagUpdate

    flag = FlagUpdate(allow_tenants=["t1", "t1", "t2", " t2 "])
    assert flag.allow_tenants is not None
    assert flag.allow_tenants.count("t1") == 1
    assert flag.allow_tenants.count("t2") == 1


def test_flag_update_percent_bounds():
    """FlagUpdate percent 0-100 arasında olmalı, dışında ValidationError fırlatır."""
    import pytest
    from pydantic import ValidationError

    from app.domains.feature_flags.schemas import FlagUpdate

    with pytest.raises(ValidationError):
        FlagUpdate(percent=101)

    with pytest.raises(ValidationError):
        FlagUpdate(percent=-1)

    # Sınır değerler geçerli
    flag_min = FlagUpdate(percent=0)
    assert flag_min.percent == 0

    flag_max = FlagUpdate(percent=100)
    assert flag_max.percent == 100
