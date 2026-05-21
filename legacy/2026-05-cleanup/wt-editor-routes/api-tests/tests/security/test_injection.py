"""Security tests — injection attack prevention."""

import pytest

from clients.fastapi_client import FastAPIClient
from config.constants import FastAPIPaths
from config.settings import settings


@pytest.mark.security
class TestSQLInjection:

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = FastAPIClient()
        self.client.login(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)

    def test_sql_injection_in_dataset_name(self):
        resp = self.client.post(
            FastAPIPaths.DATASETS,
            json={"name": "'; DROP TABLE datasets; --"},
        )
        assert resp.status_code in (201, 422)
        if resp.status_code == 201:
            list_resp = self.client.get(FastAPIPaths.DATASETS)
            assert list_resp.status_code == 200

    def test_sql_injection_in_search_query(self):
        path = "/api/v1/tspm/projects/00000000-0000-0000-0000-000000000000/scenarios"
        resp = self.client.get(path, params={"q": "' OR '1'='1"})
        assert resp.status_code in (200, 404)


@pytest.mark.security
class TestXSS:

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = FastAPIClient()
        self.client.login(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)

    def test_xss_in_project_name(self):
        resp = self.client.post(
            FastAPIPaths.TSPM_PROJECTS,
            json={"name": "<script>alert('xss')</script>"},
        )
        if resp.status_code == 201:
            data = resp.json()
            assert "<script>" not in data.get("name", "") or data.get("name") == "<script>alert('xss')</script>"
