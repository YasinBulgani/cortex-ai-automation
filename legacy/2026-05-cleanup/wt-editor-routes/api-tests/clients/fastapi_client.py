"""FastAPI backend client."""

from clients.base_client import BaseClient
from config.constants import FastAPIPaths
from config.settings import settings


class FastAPIClient(BaseClient):
    def __init__(self):
        super().__init__(settings.FASTAPI_BASE_URL)

    def login(self, email: str, password: str) -> dict:
        resp = self.post(FastAPIPaths.AUTH_LOGIN, json={"email": email, "password": password})
        if resp.status_code == 200:
            data = resp.json()
            self.set_token(data["access_token"])
        return {"status_code": resp.status_code, "data": resp.json()}

    def login_default_user(self) -> dict:
        return self.login(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)

    def get_me(self) -> dict:
        resp = self.get(FastAPIPaths.AUTH_ME)
        return {"status_code": resp.status_code, "data": resp.json()}

    def create_project(self, name: str, description: str = "") -> dict:
        resp = self.post(
            FastAPIPaths.TSPM_PROJECTS,
            json={"name": name, "description": description},
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    def list_projects(self) -> dict:
        resp = self.get(FastAPIPaths.TSPM_PROJECTS)
        return {"status_code": resp.status_code, "data": resp.json()}

    def create_scenario(self, project_id: str, title: str, **kwargs) -> dict:
        path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        payload = {"title": title, **kwargs}
        resp = self.post(path, json=payload)
        return {"status_code": resp.status_code, "data": resp.json()}

    def create_dataset(self, name: str, description: str | None = None) -> dict:
        payload = {"name": name}
        if description:
            payload["description"] = description
        resp = self.post(FastAPIPaths.DATASETS, json=payload)
        return {"status_code": resp.status_code, "data": resp.json()}

    def create_execution(self, project_id: str, **kwargs) -> dict:
        path = FastAPIPaths.TSPM_EXECUTIONS.format(project_id=project_id)
        resp = self.post(path, json=kwargs)
        return {"status_code": resp.status_code, "data": resp.json()}
