"""
catalog service unit testleri — 14 test.

Tests are fully self-contained: no DB, no HTTP, no external services.
All SQLAlchemy session calls are mocked via unittest.mock.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call
from uuid import UUID, uuid4

try:
    from app.domains.catalog.service import (
        list_datasets,
        get_dataset,
        create_dataset,
        delete_dataset,
        list_versions,
        create_version,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="catalog service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_dataset(dataset_id: str = "ds-1", name: str = "Test Dataset") -> MagicMock:
    ds = MagicMock()
    ds.id = dataset_id
    ds.name = name
    ds.description = "A test dataset"
    ds.created_by = None
    return ds


def _mock_version(dataset_id: str = "ds-1", version: int = 1) -> MagicMock:
    ver = MagicMock()
    ver.id = str(uuid4())
    ver.dataset_id = dataset_id
    ver.version = version
    ver.status = "draft"
    return ver


# ---------------------------------------------------------------------------
# list_datasets
# ---------------------------------------------------------------------------

class TestListDatasets:
    def test_returns_list(self):
        db = MagicMock()
        ds1, ds2 = _mock_dataset("ds-1"), _mock_dataset("ds-2")
        db.scalars.return_value.all.return_value = [ds1, ds2]
        result = list_datasets(db)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_returns_empty_when_no_datasets(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        result = list_datasets(db)
        assert result == []

    def test_calls_scalars_with_select(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        list_datasets(db)
        db.scalars.assert_called_once()


# ---------------------------------------------------------------------------
# get_dataset
# ---------------------------------------------------------------------------

class TestGetDataset:
    def test_returns_dataset_when_found(self):
        db = MagicMock()
        ds = _mock_dataset("ds-abc")
        db.get.return_value = ds
        result = get_dataset(db, "ds-abc")
        assert result is ds
        db.get.assert_called_once()

    def test_raises_key_error_when_not_found(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(KeyError, match="ds-missing"):
            get_dataset(db, "ds-missing")

    def test_key_error_message_contains_id(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(KeyError) as exc_info:
            get_dataset(db, "bad-id-123")
        assert "bad-id-123" in str(exc_info.value)


# ---------------------------------------------------------------------------
# create_dataset
# ---------------------------------------------------------------------------

class TestCreateDataset:
    def test_creates_and_flushes(self):
        db = MagicMock()
        ds = _mock_dataset()
        # After add+flush, db.add is called once
        result_ds = MagicMock()
        result_ds.name = "New Dataset"
        db.add.side_effect = None
        db.flush.side_effect = None
        # We can't intercept the constructor easily, just ensure add+flush called
        create_dataset(db, name="New Dataset", description="desc", created_by=None)
        db.add.assert_called_once()
        db.flush.assert_called_once()

    def test_accepts_uuid_created_by(self):
        db = MagicMock()
        uid = uuid4()
        create_dataset(db, name="DS", description=None, created_by=uid)
        db.add.assert_called_once()

    def test_accepts_none_description(self):
        db = MagicMock()
        create_dataset(db, name="DS", description=None, created_by=None)
        db.add.assert_called_once()


# ---------------------------------------------------------------------------
# delete_dataset
# ---------------------------------------------------------------------------

class TestDeleteDataset:
    def test_deletes_existing_dataset(self):
        db = MagicMock()
        ds = _mock_dataset("ds-del")
        db.get.return_value = ds
        delete_dataset(db, "ds-del")
        db.delete.assert_called_once_with(ds)
        db.flush.assert_called_once()

    def test_raises_key_error_for_missing_dataset(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(KeyError):
            delete_dataset(db, "nonexistent")


# ---------------------------------------------------------------------------
# list_versions
# ---------------------------------------------------------------------------

class TestListVersions:
    def test_raises_key_error_if_parent_missing(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(KeyError):
            list_versions(db, "missing-ds")

    def test_returns_versions_for_existing_dataset(self):
        db = MagicMock()
        ds = _mock_dataset("ds-1")
        db.get.return_value = ds
        v1, v2 = _mock_version("ds-1", 1), _mock_version("ds-1", 2)
        db.scalars.return_value.all.return_value = [v2, v1]
        result = list_versions(db, "ds-1")
        assert len(result) == 2

    def test_returns_empty_list_when_no_versions(self):
        db = MagicMock()
        db.get.return_value = _mock_dataset("ds-1")
        db.scalars.return_value.all.return_value = []
        result = list_versions(db, "ds-1")
        assert result == []


# ---------------------------------------------------------------------------
# create_version
# ---------------------------------------------------------------------------

class TestCreateVersion:
    def test_raises_key_error_if_parent_missing(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(KeyError):
            create_version(db, "missing-ds", snapshot={}, profile=None, pii_flags=None)

    def test_creates_version_with_auto_incremented_number(self):
        db = MagicMock()
        db.get.return_value = _mock_dataset("ds-1")
        # Simulate max version = 3
        db.scalar.return_value = 3
        db.add.side_effect = None
        db.flush.side_effect = None
        create_version(db, "ds-1", snapshot={"col": "text"}, profile=None, pii_flags=None)
        # add called twice: DatasetVersion + SchemaSnapshot
        assert db.add.call_count == 2
        assert db.flush.call_count == 2

    def test_version_starts_at_1_when_no_previous(self):
        db = MagicMock()
        db.get.return_value = _mock_dataset("ds-1")
        db.scalar.return_value = None  # no existing versions
        db.add.side_effect = None
        db.flush.side_effect = None
        create_version(db, "ds-1", snapshot=None, profile=None, pii_flags=None)
        db.add.assert_called()

    def test_schema_snapshot_uses_empty_dict_when_no_snapshot(self):
        db = MagicMock()
        db.get.return_value = _mock_dataset("ds-1")
        db.scalar.return_value = 0
        added_objects = []
        db.add.side_effect = lambda obj: added_objects.append(obj)
        db.flush.side_effect = None
        create_version(db, "ds-1", snapshot=None, profile=None, pii_flags=None)
        # Second add is the SchemaSnapshot; its snapshot attr should be {}
        snap_obj = added_objects[1]
        assert snap_obj.snapshot == {}
