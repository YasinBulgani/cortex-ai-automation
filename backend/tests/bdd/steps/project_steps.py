"""Step definitions for project_management.feature (Turkce Gherkin)."""

from __future__ import annotations

import time

from pytest_bdd import given, parsers, scenarios, then, when
from fastapi.testclient import TestClient

from ..conftest import unique


# ── Background ───────────────────────────────────────────────────────


@given("kullanıcı oturum açmış ve geçerli JWT token'a sahip")
def user_authenticated(admin_auth: dict, ctx: dict):
    ctx["headers"] = admin_auth
    # Bearer token'ı auth_steps ile uyumlu tutmak için ayrıca "token" da saklıyoruz
    auth_val = admin_auth.get("Authorization", "")
    if auth_val.startswith("Bearer "):
        ctx["token"] = auth_val[len("Bearer "):]


# ── Proje oluşturma ──────────────────────────────────────────────────


@given("proje oluşturma verisi hazırlanıyor")
def prepare_project(ctx: dict):
    ctx["body"] = {}


@given(parsers.re(r'proje adı "(?P<name>.*)" olarak belirleniyor'))
def set_project_name(ctx: dict, name: str):
    ctx.setdefault("body", {})["name"] = name


@given(parsers.re(r'proje açıklaması "(?P<desc>.*)" olarak belirleniyor'))
def set_project_desc(ctx: dict, desc: str):
    ctx.setdefault("body", {})["description"] = desc


# ── Zaman sıralı proje seed ──────────────────────────────────────────


@given(parsers.parse('"{name}" adıyla proje oluşturulmuş'))
def project_created(api: TestClient, ctx: dict, name: str):
    unique_name = f"{name} {unique()}"
    r = api.post(
        "/api/v1/tspm/projects",
        json={"name": unique_name},
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 201, r.text
    ctx.setdefault("created_projects", []).append({"name": unique_name, "id": r.json()["id"]})


@given(parsers.parse('{seconds:d} saniye sonra "{name}" adıyla proje oluşturulmuş'))
def project_created_delayed(api: TestClient, ctx: dict, seconds: int, name: str):
    time.sleep(seconds)
    unique_name = f"{name} {unique()}"
    r = api.post(
        "/api/v1/tspm/projects",
        json={"name": unique_name},
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 201, r.text
    ctx.setdefault("created_projects", []).append({"name": unique_name, "id": r.json()["id"]})


@then(parsers.parse('yanıt listesinde ilk öğe "{name}" olmalı'))
def check_first_item(ctx: dict, name: str):
    items = ctx["response"].json()
    assert isinstance(items, list) and items, "Boş liste döndü"
    # İlk kayıt, "name" ile başlamalı (unique suffix nedeniyle prefix kontrolü)
    first_name = items[0].get("name", "")
    assert first_name.startswith(name), f"İlk öğe: {first_name!r}, beklenen prefix: {name!r}"


# ── Boş proje dashboard ──────────────────────────────────────────────


@given("yeni boş bir proje oluşturulmuş")
def create_empty_project(api: TestClient, ctx: dict):
    r = api.post(
        "/api/v1/tspm/projects",
        json={"name": f"Empty-{unique()}"},
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 201
    ctx["empty_project_id"] = r.json()["id"]


@then("bu projenin dashboard endpoint'i çağrılır")
@when("bu projenin dashboard endpoint'i çağrılır")
def call_empty_dashboard(api: TestClient, ctx: dict):
    pid = ctx["empty_project_id"]
    ctx["response"] = api.get(
        f"/api/v1/tspm/projects/{pid}/dashboard",
        headers=ctx.get("headers", {}),
    )
    assert ctx["response"].status_code == 200
