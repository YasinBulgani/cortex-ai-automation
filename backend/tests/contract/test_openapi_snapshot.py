"""OpenAPI snapshot kontrat testi — breaking API değişikliklerini yakalar.

Nasıl çalışır?
  1. Bir commit'te kritik endpoint'lerin path + method + response schema'sı
     `OpenAPISnapshot` sabitine yazılır.
  2. CI'da her PR'da live FastAPI app'inden alınan OpenAPI şeması bu snapshot
     ile karşılaştırılır.
  3. Bir endpoint silinir, method değişir veya response schema'sından kritik
     alan çıkarılırsa test kırılır — katkıcı bilinçli olarak snapshot'ı
     güncellemek zorunda kalır (bu da code review gözüne sokulur).

Bu "poor man's contract testing": OpenAPI diff için Pact/Spectral gibi
dedicated araçları yüklemeden hızlı regresyon kapısı. Tam bir kontrat
kütüphanesi istendiğinde bu modülü Pact'e terfi ettirin.

Öncelik: otomasyonun kalbindeki endpoint'ler — execution lifecycle,
scheduler, approval, integration sync, automation üretimi.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ────────────────────────────────────────────────────────────────────────
# Snapshot: kritik otomasyon endpoint'leri için minimum sözleşme
# ────────────────────────────────────────────────────────────────────────
#
# Format: { path: { method: { "must_fields": [<response_body_fields>] } } }
# `must_fields` response şemasında mutlaka bulunmalı; ek alan eklenebilir.
# Path'ler OpenAPI'de templated (örn. {project_id}) görünür.

EXPECTED_ENDPOINTS: dict[str, dict[str, dict]] = {
    # ── Execution lifecycle ──────────────────────────────────────────────
    "/api/v1/tspm/projects/{project_id}/executions": {
        "post": {"must_fields": ["id", "name", "status", "simulated"]},
        "get": {"must_fields": []},  # list[ExecutionOut] — item kontratı aşağıda
    },
    # ── Scheduler: trigger ──────────────────────────────────────────────
    "/api/v1/tspm/projects/{project_id}/schedules": {
        "post": {"must_fields": ["id", "name", "cron_expression", "is_active"]},
        "get": {"must_fields": []},
    },
    "/api/v1/tspm/projects/{project_id}/schedules/{schedule_id}/trigger": {
        "post": {"must_fields": []},  # shape esnek, yalnızca path/method garantisi
    },
    # ── Approvals ───────────────────────────────────────────────────────
    "/api/v1/tspm/projects/{project_id}/approvals": {
        "get": {"must_fields": []},
        "post": {"must_fields": ["id"]},
    },
    "/api/v1/tspm/projects/{project_id}/approvals/{approval_id}/decide": {
        "post": {"must_fields": []},
    },
    # ── Integration sync (stub contract) ─────────────────────────────────
    "/api/v1/tspm/projects/{project_id}/integrations/{integration_id}/sync": {
        "post": {
            "must_fields": ["synced_count", "message", "stub", "provider"],
        },
    },
    # ── Scenarios + BDD ──────────────────────────────────────────────────
    "/api/v1/tspm/projects/{project_id}/scenarios": {
        "get": {"must_fields": []},
        "post": {"must_fields": ["id", "title", "status"]},
    },
    # ── Automation generation — Faz 5 ───────────────────────────────────
    "/api/v1/tspm/projects/{project_id}/automation/generate": {
        "post": {"must_fields": []},
    },
    # ── Health / Ready ───────────────────────────────────────────────────
    # NOT: /health ve /ready response_model olmadan dict dönüyor; FastAPI
    # OpenAPI'ye properties çıkarmaz. Yalnızca endpoint varlığını garanti
    # ediyoruz — field snapshot için Pydantic model eklemek gerekir.
    "/health": {"get": {"must_fields": []}},
    "/ready": {"get": {"must_fields": []}},
}


def _resolve_ref(schema: dict, components: dict) -> dict:
    """OpenAPI $ref'i component schema'sına çöz."""
    ref = schema.get("$ref", "")
    if not ref.startswith("#/components/schemas/"):
        return schema
    name = ref.rsplit("/", 1)[-1]
    return components.get(name, {})


def _response_fields(operation: dict, components: dict) -> set[str]:
    """Operation'ın 2xx response body'sinin top-level alanlarını çıkar.

    Liste (array) dönüşleri için item şemasının alanları kullanılır.
    $ref çözümlemesi bir seviye derin; nested ref zincirleri için
    özyineleme yapmayız (gereksiz karmaşa — snapshot yüzeyi sığ).
    """
    responses = operation.get("responses", {})
    for code in ("200", "201", "202"):
        resp = responses.get(code) or responses.get(int(code))
        if not resp:
            continue
        content = resp.get("content", {})
        schema = content.get("application/json", {}).get("schema")
        if not schema:
            continue
        if "$ref" in schema:
            schema = _resolve_ref(schema, components)
        if schema.get("type") == "array":
            item = schema.get("items", {})
            if "$ref" in item:
                item = _resolve_ref(item, components)
            return set(item.get("properties", {}).keys())
        return set(schema.get("properties", {}).keys())
    return set()


@pytest.fixture(scope="module")
def openapi_spec(client: TestClient) -> dict:
    r = client.get("/openapi.json")
    assert r.status_code == 200, "OpenAPI şeması alınamadı"
    return r.json()


class TestOpenAPIEndpointSnapshot:
    """Path + method seviyesinde endpoint'lerin var olmaya devam ettiğini doğrula."""

    @pytest.mark.parametrize("path", sorted(EXPECTED_ENDPOINTS.keys()))
    def test_endpoint_exists(self, openapi_spec: dict, path: str):
        assert path in openapi_spec.get("paths", {}), (
            f"Endpoint kayboldu: {path}. "
            "Bilerek sildiyseniz tests/contract/test_openapi_snapshot.py "
            "içinde EXPECTED_ENDPOINTS'ten kaydı çıkarın."
        )

    def test_all_expected_methods_present(self, openapi_spec: dict):
        paths = openapi_spec.get("paths", {})
        missing: list[str] = []
        for path, methods in EXPECTED_ENDPOINTS.items():
            p = paths.get(path, {})
            for method in methods:
                if method not in p:
                    missing.append(f"{method.upper()} {path}")
        assert not missing, (
            "Beklenen HTTP method'ları eksik: " + ", ".join(missing)
        )


class TestOpenAPIResponseFields:
    """Kritik response alanlarının şemadan silinmediğini garanti et."""

    @pytest.mark.parametrize(
        ("path", "method", "must_fields"),
        [
            (p, m, spec["must_fields"])
            for p, methods in EXPECTED_ENDPOINTS.items()
            for m, spec in methods.items()
            if spec["must_fields"]
        ],
    )
    def test_required_fields_present(
        self, openapi_spec: dict, path: str, method: str, must_fields: list[str]
    ):
        op = (
            openapi_spec.get("paths", {})
            .get(path, {})
            .get(method, {})
        )
        if not op:
            pytest.skip(f"{method.upper()} {path} — endpoint mevcut değil, ayrı test yakalıyor")
        components = openapi_spec.get("components", {}).get("schemas", {})
        fields = _response_fields(op, components)
        for f in must_fields:
            assert f in fields, (
                f"{method.upper()} {path} response'undan '{f}' alanı silinmiş. "
                "Breaking change — UI/istemciler kırılır. Kasıtlı silme ise "
                "EXPECTED_ENDPOINTS snapshot'ını güncelleyin."
            )


class TestOpenAPIRouteCount:
    """Route sayısı ani düşüşünü yakala — kitlesel endpoint silinmesini önler."""

    # Backend 440+ route ile geliyor (11'i FastAPI default + middleware);
    # 300 eşiği altına düşüş muhtemelen toplu refactor hatasıdır.
    MIN_ROUTES = 300

    def test_route_count_stable(self, openapi_spec: dict):
        paths = openapi_spec.get("paths", {})
        # Her path birden çok method barındırabilir; toplam operasyon sayısı.
        count = sum(
            1
            for methods in paths.values()
            for m in methods
            if m in ("get", "post", "put", "patch", "delete")
        )
        assert count >= self.MIN_ROUTES, (
            f"Toplam OpenAPI operasyon sayısı {count}, eşik {self.MIN_ROUTES}. "
            "Büyük bir endpoint kaybı var gibi. Snapshot eşiğini değiştirmeden "
            "silinenleri geri ekleyin."
        )
