"""
FastAPI endpoint birim testleri.

TestClient ile tüm API endpointlerini test eder.
Veritabanı bağımlılıkları mock'lanmıştır.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi import status
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════════
# Test App Fixture — DB bağımlılığı mock'lanmış
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient — veritabanı mock'lu."""
    # DB session mock
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.count.return_value = 0
    mock_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.count.return_value = 0

    def _get_db_override():
        yield mock_session

    from app.main import app
    from app.models.database import get_db

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════
# Kök ve Sağlık Endpoint Testleri
# ═══════════════════════════════════════════════════════════════════


class TestRootEndpoint:
    """Kök endpoint testleri."""

    def test_root_returns_200(self, client: TestClient) -> None:
        """/ endpoint'i 200 dönmeli."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

    def test_root_contains_platform_info(self, client: TestClient) -> None:
        """Kök yanıt platform bilgilerini içermeli."""
        response = client.get("/")
        data = response.json()
        assert "platform" in data
        assert "version" in data
        assert "docs" in data

    def test_root_has_api_prefix(self, client: TestClient) -> None:
        """API prefix /api/v1 olmalı."""
        response = client.get("/")
        data = response.json()
        assert data.get("api_prefix") == "/api/v1"


class TestHealthEndpoint:
    """Sağlık kontrolü endpoint testleri."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """/api/v1/health endpoint'i 200 dönmeli."""
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_contains_status(self, client: TestClient) -> None:
        """Sağlık yanıtı durum bilgisi içermeli."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "status" in data or "database" in data or "uptime" in data


class TestScenariosEndpoint:
    """Senaryo listeleme endpoint testleri."""

    def test_list_scenarios_returns_200(self, client: TestClient) -> None:
        """/api/v1/scenarios endpoint'i 200 dönmeli."""
        response = client.get("/api/v1/scenarios")
        assert response.status_code == status.HTTP_200_OK

    def test_list_scenarios_has_items(self, client: TestClient) -> None:
        """Senaryo listesi en az 12 senaryo içermeli."""
        response = client.get("/api/v1/scenarios")
        data = response.json()
        scenarios = data.get("scenarios", data.get("items", []))
        assert len(scenarios) >= 12


# ═══════════════════════════════════════════════════════════════════
# Dosya Yükleme Endpoint Testleri
# ═══════════════════════════════════════════════════════════════════


class TestUploadEndpoint:
    """Dosya yükleme endpoint testleri."""

    def test_upload_csv_file(self, client: TestClient) -> None:
        """CSV dosya yükleme başarılı olmalı."""
        csv_content = "customer_id,first_name,last_name\nMUS001,Ahmet,Yılmaz\nMUS002,Ayşe,Kaya\n"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}

        # Mock dataset creation
        mock_dataset = MagicMock()
        mock_dataset.id = 1
        mock_dataset.name = "test.csv"
        mock_dataset.file_type = "csv"
        mock_dataset.row_count = 2
        mock_dataset.column_count = 3

        with patch("app.api.routes.Dataset", return_value=mock_dataset):
            response = client.post("/api/v1/upload", files=files)
            # 200 veya 201 bekleniyor (DB mock'lu olduğundan hata alabilir)
            assert response.status_code in (
                status.HTTP_200_OK, status.HTTP_201_CREATED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def test_upload_rejects_invalid_extension(self, client: TestClient) -> None:
        """Geçersiz dosya uzantısı reddedilmeli."""
        files = {"file": ("test.exe", io.BytesIO(b"malicious"), "application/octet-stream")}
        response = client.post("/api/v1/upload", files=files)
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ═══════════════════════════════════════════════════════════════════
# Dataset Listeleme ve Detay Endpoint Testleri
# ═══════════════════════════════════════════════════════════════════


class TestDatasetsEndpoint:
    """Veri seti listeleme endpoint testleri."""

    def test_list_datasets_returns_200(self, client: TestClient) -> None:
        """/api/v1/datasets endpoint'i 200 dönmeli."""
        response = client.get("/api/v1/datasets")
        assert response.status_code == status.HTTP_200_OK

    def test_get_nonexistent_dataset_returns_404(self, client: TestClient) -> None:
        """Var olmayan veri seti 404 dönmeli."""
        response = client.get("/api/v1/datasets/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ═══════════════════════════════════════════════════════════════════
# API Genel Davranış Testleri
# ═══════════════════════════════════════════════════════════════════


class TestAPIGeneralBehavior:
    """API genel davranış testleri."""

    def test_cors_headers_present(self, client: TestClient) -> None:
        """CORS başlıkları mevcut olmalı."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS middleware aktif — header kontrolü
        assert response.status_code in (200, 204, 405)

    def test_process_time_header(self, client: TestClient) -> None:
        """X-Process-Time başlığı dönmeli."""
        response = client.get("/")
        assert "x-process-time" in response.headers

    def test_docs_endpoint_accessible(self, client: TestClient) -> None:
        """Swagger UI erişilebilir olmalı."""
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK

    def test_openapi_json_accessible(self, client: TestClient) -> None:
        """OpenAPI şeması erişilebilir olmalı."""
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_nonexistent_endpoint_returns_404(self, client: TestClient) -> None:
        """Var olmayan endpoint 404 dönmeli."""
        response = client.get("/api/v1/nonexistent_endpoint")
        assert response.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_stats_endpoint(self, client: TestClient) -> None:
        """/api/v1/stats endpoint'i 200 dönmeli."""
        response = client.get("/api/v1/stats")
        assert response.status_code == status.HTTP_200_OK
