"""Unit tests for app.domains.ai_synthetic_data.service.

Tests are fully self-contained: generators are mocked so no heavy ML libs
are required at test time.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

try:
    from app.domains.ai_synthetic_data import service as synth_service
    from app.domains.ai_synthetic_data.service import (
        generate,
        list_datasets,
        get_dataset,
        _datasets,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="ai_synthetic_data service import failed")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_DATA = [
    {"name": "Alice", "age": 30, "salary": 70000},
    {"name": "Bob", "age": 25, "salary": 55000},
    {"name": "Carol", "age": 35, "salary": 90000},
]


def _mock_kde_generator():
    gen = MagicMock()
    gen.generate.return_value = [{"name": "Synthetic1", "age": 28, "salary": 60000}]
    gen.quality_metrics.return_value = {"similarity": 0.85}
    return gen


def _mock_ctgan_generator():
    gen = MagicMock()
    gen.generate.return_value = [{"name": "SyntheticC", "age": 32, "salary": 75000}]
    gen.quality_report.return_value = {"fidelity": 0.90}
    return gen


# ---------------------------------------------------------------------------
# generate — KDE
# ---------------------------------------------------------------------------

class TestGenerateKde:
    def test_returns_dict_with_required_keys(self):
        with patch.object(synth_service, "KDEGenerator", return_value=_mock_kde_generator()):
            result = generate({"sample_data": _SAMPLE_DATA, "generator_type": "kde", "count": 1})
        for key in ("dataset_id", "records", "quality_metrics", "duration_ms"):
            assert key in result

    def test_dataset_id_is_non_empty_string(self):
        with patch.object(synth_service, "KDEGenerator", return_value=_mock_kde_generator()):
            result = generate({"sample_data": _SAMPLE_DATA, "generator_type": "kde", "count": 1})
        assert isinstance(result["dataset_id"], str) and len(result["dataset_id"]) > 0

    def test_records_are_list(self):
        with patch.object(synth_service, "KDEGenerator", return_value=_mock_kde_generator()):
            result = generate({"sample_data": _SAMPLE_DATA, "generator_type": "kde", "count": 1})
        assert isinstance(result["records"], list)

    def test_duration_ms_is_non_negative(self):
        with patch.object(synth_service, "KDEGenerator", return_value=_mock_kde_generator()):
            result = generate({"sample_data": _SAMPLE_DATA, "generator_type": "kde", "count": 1})
        assert result["duration_ms"] >= 0

    def test_result_stored_in_datasets(self):
        with patch.object(synth_service, "KDEGenerator", return_value=_mock_kde_generator()):
            result = generate({"sample_data": _SAMPLE_DATA, "generator_type": "kde", "count": 1})
        assert result["dataset_id"] in synth_service._datasets


# ---------------------------------------------------------------------------
# generate — CTGAN
# ---------------------------------------------------------------------------

class TestGenerateCtgan:
    def test_ctgan_generator_called(self):
        mock_gen = _mock_ctgan_generator()
        with patch.object(synth_service, "CTGANGenerator", return_value=mock_gen):
            result = generate({"sample_data": _SAMPLE_DATA, "generator_type": "ctgan", "count": 1})
        mock_gen.fit.assert_called_once_with(_SAMPLE_DATA)
        assert "dataset_id" in result


# ---------------------------------------------------------------------------
# generate — validation errors
# ---------------------------------------------------------------------------

class TestGenerateValidation:
    def test_missing_sample_data_raises_value_error(self):
        with pytest.raises(ValueError, match="sample_data"):
            generate({"generator_type": "kde", "count": 5})

    def test_empty_sample_data_raises_value_error(self):
        with pytest.raises(ValueError):
            generate({"sample_data": [], "generator_type": "kde"})

    def test_unknown_generator_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Bilinmeyen generator_type"):
            generate({"sample_data": _SAMPLE_DATA, "generator_type": "unknown_gen"})

    def test_default_generator_type_is_kde(self):
        """Omitting generator_type should fall back to 'kde' without error."""
        with patch.object(synth_service, "KDEGenerator", return_value=_mock_kde_generator()):
            result = generate({"sample_data": _SAMPLE_DATA, "count": 1})
        assert result["generator_type"] == "kde"


# ---------------------------------------------------------------------------
# list_datasets / get_dataset
# ---------------------------------------------------------------------------

class TestListDatasets:
    def test_returns_list(self):
        result = list_datasets()
        assert isinstance(result, list)

    def test_summaries_do_not_include_records(self):
        with patch.object(synth_service, "KDEGenerator", return_value=_mock_kde_generator()):
            generate({"sample_data": _SAMPLE_DATA, "generator_type": "kde", "count": 1})
        for item in list_datasets():
            assert "records" not in item


class TestGetDataset:
    def test_get_existing_dataset_returns_data(self):
        with patch.object(synth_service, "KDEGenerator", return_value=_mock_kde_generator()):
            created = generate({"sample_data": _SAMPLE_DATA, "generator_type": "kde", "count": 1})
        fetched = get_dataset(created["dataset_id"])
        assert fetched["id"] == created["dataset_id"]

    def test_get_nonexistent_raises_key_error(self):
        with pytest.raises(KeyError):
            get_dataset("nonexistent-dataset-id-xyz")
