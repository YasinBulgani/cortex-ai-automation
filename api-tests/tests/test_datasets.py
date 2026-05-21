"""Dataset CRUD and version management tests."""

import pytest

from config.constants import FastAPIPaths
from helpers.data_factory import random_dataset_name, long_string, snapshot_v1, random_uuid


@pytest.mark.datasets
class TestDatasetCreate:

    def test_create_dataset_valid(self, api):
        resp = api.post(FastAPIPaths.DATASETS, json={"name": random_dataset_name()})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "name" in data

    def test_create_dataset_with_description(self, api):
        resp = api.post(
            FastAPIPaths.DATASETS,
            json={"name": random_dataset_name(), "description": "Test açıklaması"},
        )
        assert resp.status_code == 201

    @pytest.mark.negative
    def test_create_dataset_empty_name(self, api):
        resp = api.post(FastAPIPaths.DATASETS, json={"name": ""})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_dataset_missing_name(self, api):
        resp = api.post(FastAPIPaths.DATASETS, json={"description": "no name"})
        assert resp.status_code == 422

    @pytest.mark.boundary
    def test_create_dataset_name_200_chars(self, api):
        resp = api.post(FastAPIPaths.DATASETS, json={"name": "A" * 200})
        assert resp.status_code == 201

    @pytest.mark.boundary
    def test_create_dataset_name_201_chars(self, api):
        resp = api.post(FastAPIPaths.DATASETS, json={"name": "A" * 201})
        assert resp.status_code == 422

    @pytest.mark.boundary
    def test_create_dataset_name_1_char(self, api):
        resp = api.post(FastAPIPaths.DATASETS, json={"name": "X"})
        assert resp.status_code == 201

    @pytest.mark.negative
    def test_create_dataset_no_auth(self, api_noauth):
        resp = api_noauth.post(FastAPIPaths.DATASETS, json={"name": "test"})
        assert resp.status_code in (401, 403)


@pytest.mark.datasets
class TestDatasetList:

    def test_list_datasets(self, api):
        resp = api.get(FastAPIPaths.DATASETS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.datasets
class TestDatasetDetail:

    def test_get_existing_dataset(self, api):
        create_resp = api.post(FastAPIPaths.DATASETS, json={"name": random_dataset_name()})
        dataset_id = create_resp.json()["id"]
        path = FastAPIPaths.DATASET_DETAIL.format(dataset_id=dataset_id)
        resp = api.get(path)
        assert resp.status_code == 200
        assert resp.json()["id"] == dataset_id

    @pytest.mark.negative
    def test_get_nonexistent_dataset(self, api):
        path = FastAPIPaths.DATASET_DETAIL.format(dataset_id=random_uuid())
        resp = api.get(path)
        assert resp.status_code == 404


@pytest.mark.datasets
class TestDatasetVersions:

    def test_create_version_valid_snapshot(self, api):
        ds_resp = api.post(FastAPIPaths.DATASETS, json={"name": random_dataset_name()})
        dataset_id = ds_resp.json()["id"]
        path = FastAPIPaths.DATASET_VERSIONS.format(dataset_id=dataset_id)
        resp = api.post(path, json={"snapshot": snapshot_v1()})
        assert resp.status_code == 201

    @pytest.mark.negative
    def test_create_version_empty_snapshot(self, api):
        ds_resp = api.post(FastAPIPaths.DATASETS, json={"name": random_dataset_name()})
        dataset_id = ds_resp.json()["id"]
        path = FastAPIPaths.DATASET_VERSIONS.format(dataset_id=dataset_id)
        resp = api.post(path, json={"snapshot": {}})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_version_wrong_schema_version(self, api):
        ds_resp = api.post(FastAPIPaths.DATASETS, json={"name": random_dataset_name()})
        dataset_id = ds_resp.json()["id"]
        path = FastAPIPaths.DATASET_VERSIONS.format(dataset_id=dataset_id)
        resp = api.post(
            path,
            json={"snapshot": {"version": 2, "fields": [{"name": "x", "type": "string"}]}},
        )
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_version_duplicate_field_names(self, api):
        ds_resp = api.post(FastAPIPaths.DATASETS, json={"name": random_dataset_name()})
        dataset_id = ds_resp.json()["id"]
        path = FastAPIPaths.DATASET_VERSIONS.format(dataset_id=dataset_id)
        resp = api.post(
            path,
            json={
                "snapshot": snapshot_v1([
                    {"name": "dup", "type": "string"},
                    {"name": "dup", "type": "integer"},
                ])
            },
        )
        assert resp.status_code == 422

    @pytest.mark.boundary
    def test_create_version_invalid_field_name_format(self, api):
        ds_resp = api.post(FastAPIPaths.DATASETS, json={"name": random_dataset_name()})
        dataset_id = ds_resp.json()["id"]
        path = FastAPIPaths.DATASET_VERSIONS.format(dataset_id=dataset_id)
        resp = api.post(
            path,
            json={"snapshot": snapshot_v1([{"name": "123invalid", "type": "string"}])},
        )
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_version_nonexistent_dataset(self, api):
        path = FastAPIPaths.DATASET_VERSIONS.format(dataset_id=random_uuid())
        resp = api.post(path, json={"snapshot": snapshot_v1()})
        assert resp.status_code == 404
