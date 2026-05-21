"""
steps/api/step_api_tests.py — API testi (TS-14) step tanimlari.

Feature: api_tests.feature
Kapsam: TC-1401 ~ TC-1404
"""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/api_tests.feature")


@when(parsers.parse('"{name}" adli koleksiyon olusturulur'))
def create_collection(api: APIClient, project_id: str, context: dict, name: str):
    context["response"] = api.post(
        api.project_path(project_id, "api-tests/collections"),
        json={"name": name, "base_url": "http://localhost:8000"},
    )
    if context["response"].status_code == 201:
        context["collection_id"] = context["response"].json()["id"]


@given("projede bir API koleksiyonu olusturulmus")
def collection_created(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "api-tests/collections"),
        json={"name": "Test Collection", "base_url": "http://localhost:8000"},
    )
    assert resp.status_code == 201
    context["collection_id"] = resp.json()["id"]


@when(parsers.parse('koleksiyona "{name}" adli GET {path} request\'i eklenir'))
def add_request(api: APIClient, project_id: str, context: dict, name: str, path: str):
    col_id = context["collection_id"]
    context["response"] = api.post(
        api.project_path(project_id, f"api-tests/collections/{col_id}/requests"),
        json={"name": name, "method": "GET", "path": path},
    )


@given("koleksiyonda en az 1 request mevcut")
def collection_has_request(api: APIClient, project_id: str, context: dict):
    col_id = context["collection_id"]
    api.post(
        api.project_path(project_id, f"api-tests/collections/{col_id}/requests"),
        json={"name": "Health", "method": "GET", "path": "/health"},
    )


@when("koleksiyon calistirilir")
def run_collection(api: APIClient, project_id: str, context: dict):
    col_id = context["collection_id"]
    context["response"] = api.post(
        api.project_path(project_id, f"api-tests/collections/{col_id}/run"),
    )


@then('sonuc listesinde her request icin "status_code" ve "passed" alanlari donmelidir')
def assert_run_results(context: dict):
    body = context["response"].json()
    results = body.get("results", [])
    for r in results:
        assert "status_code" in r, f"status_code eksik: {r}"
        assert "passed" in r, f"passed eksik: {r}"


@given("koleksiyonda erisilemez base_url'li request mevcut")
def unreachable_collection(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "api-tests/collections"),
        json={"name": "Unreachable", "base_url": "http://unreachable:9999"},
    )
    col_id = resp.json()["id"]
    context["collection_id"] = col_id
    api.post(
        api.project_path(project_id, f"api-tests/collections/{col_id}/requests"),
        json={"name": "Fail", "method": "GET", "path": "/test"},
    )


@then('sonuc listesinde "passed" false ve "error" alani dolu olmalidir')
def assert_error_results(context: dict):
    body = context["response"].json()
    results = body.get("results", [])
    for r in results:
        assert r.get("passed") is False, f"passed True beklenmiyor: {r}"
        assert r.get("error"), f"error alani bos: {r}"
