"""Job queue and artifact tests."""

import pytest

from config.constants import FastAPIPaths
from helpers.data_factory import random_uuid, random_dataset_name, snapshot_v1


@pytest.mark.critical
class TestJobEnqueue:

    @pytest.fixture(autouse=True)
    def setup_dataset_version(self, api):
        ds_resp = api.post(FastAPIPaths.DATASETS, json={"name": random_dataset_name()})
        self.dataset_id = ds_resp.json()["id"]
        ver_path = FastAPIPaths.DATASET_VERSIONS.format(dataset_id=self.dataset_id)
        ver_resp = api.post(ver_path, json={"snapshot": snapshot_v1()})
        self.version_id = ver_resp.json()["id"]

    def test_enqueue_job(self, api):
        resp = api.post(
            FastAPIPaths.JOBS,
            json={"dataset_version_id": self.version_id},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] in ("pending", "queued", "running")

    @pytest.mark.negative
    def test_enqueue_job_missing_version(self, api):
        resp = api.post(FastAPIPaths.JOBS, json={})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_enqueue_job_nonexistent_version(self, api):
        resp = api.post(
            FastAPIPaths.JOBS,
            json={"dataset_version_id": random_uuid()},
        )
        assert resp.status_code in (400, 404)


class TestJobList:

    def test_list_jobs_default(self, api):
        resp = api.get(FastAPIPaths.JOBS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.boundary
    def test_list_jobs_limit_200(self, api):
        resp = api.get(FastAPIPaths.JOBS, params={"limit": 200})
        assert resp.status_code == 200

    @pytest.mark.boundary
    def test_list_jobs_limit_0(self, api):
        resp = api.get(FastAPIPaths.JOBS, params={"limit": 0})
        assert resp.status_code in (200, 422)

    @pytest.mark.negative
    def test_list_jobs_negative_limit(self, api):
        resp = api.get(FastAPIPaths.JOBS, params={"limit": -1})
        assert resp.status_code in (200, 422)


class TestJobDetail:

    @pytest.mark.negative
    def test_get_nonexistent_job(self, api):
        path = FastAPIPaths.JOB_DETAIL.format(job_id=random_uuid())
        resp = api.get(path)
        assert resp.status_code == 404

    @pytest.mark.negative
    def test_get_job_events_nonexistent(self, api):
        path = FastAPIPaths.JOB_EVENTS.format(job_id=random_uuid())
        resp = api.get(path)
        assert resp.status_code == 404
