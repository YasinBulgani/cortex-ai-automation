"""
steps/api/conftest.py — API BDD testleri icin pytest fixture'lari.

Tum feature dosyalari tarafindan paylasilan fixture'lar:
- api: Authenticated APIClient instance
- api_anon: Token'siz APIClient instance
- project_id: Test projesi ID'si
- scenario_id: Test senaryosu ID'si
- context: Adimlar arasi paylasilan dict

Calistirma:
  cd engine && python -m pytest steps/api/ -v
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

# Engine root'u sys.path'e ekle (helpers/ ve core/ import edilebilsin)
_ENGINE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from helpers.api_client import APIClient


BASE_URL = os.getenv("TWAI_API_URL", "http://127.0.0.1:8000")
ADMIN_EMAIL = os.getenv("TWAI_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("TWAI_ADMIN_PASSWORD", "admin123")


@pytest.fixture(scope="session")
def api() -> APIClient:
    """Oturum acmis admin kullanicisi ile API istemcisi."""
    client = APIClient(BASE_URL)
    resp = client.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    assert resp.status_code == 200, f"Admin login basarisiz: {resp.text}"
    yield client
    client.close()


@pytest.fixture(scope="function")
def api_anon() -> APIClient:
    """Token'siz (anonim) API istemcisi."""
    client = APIClient(BASE_URL)
    yield client
    client.close()


@pytest.fixture(scope="function")
def context() -> dict:
    """Adimlar arasi veri paylasimi icin dict."""
    return {}


@pytest.fixture(scope="function")
def project_id(api: APIClient, context: dict) -> str:
    """Her test icin temiz bir proje olusturur, ID'sini doner."""
    name = f"Test-{uuid.uuid4().hex[:8]}"
    resp = api.post(api.tspm("projects"), json={"name": name, "description": "BDD test projesi"})
    assert resp.status_code == 201
    pid = resp.json()["id"]
    context["project_id"] = pid
    context["project_name"] = name
    return pid


@pytest.fixture(scope="function")
def scenario_id(api: APIClient, project_id: str, context: dict) -> str:
    """Proje icinde bir test senaryosu olusturur, ID'sini doner."""
    resp = api.post(
        api.project_path(project_id, "scenarios"),
        json={
            "title": f"Senaryo-{uuid.uuid4().hex[:6]}",
            "description": "BDD test senaryosu",
            "steps": [{"order": 1, "keyword": "Given", "text": "Test adimi"}],
        },
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]
    context["scenario_id"] = sid
    return sid


@pytest.fixture(scope="function")
def requirement_id(api: APIClient, project_id: str, context: dict) -> str:
    """Proje icinde bir gereksinim olusturur, ID'sini doner."""
    resp = api.post(
        api.project_path(project_id, "requirements"),
        json={"external_id": f"REQ-{uuid.uuid4().hex[:6]}", "title": "Test gereksinimi", "priority": "high"},
    )
    assert resp.status_code == 201
    rid = resp.json()["id"]
    context["requirement_id"] = rid
    return rid
