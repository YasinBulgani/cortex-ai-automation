"""
steps/api/step_requirements.py — Gereksinimler ve kapsam (TS-10) step tanimlari.

Feature: requirements_coverage.feature
Kapsam: TC-1001 ~ TC-1007
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/requirements_coverage.feature")


@when(parsers.parse('"{ext_id}" kimlikli "{title}" baslikli gereksinim olusturulur'))
def create_requirement(api: APIClient, project_id: str, context: dict, ext_id: str, title: str):
    context["response"] = api.post(
        api.project_path(project_id, "requirements"),
        json={"external_id": ext_id, "title": title, "priority": "high"},
    )
    if context["response"].status_code == 201:
        context["requirement_id"] = context["response"].json()["id"]


@when("senaryo ile gereksinim iliskilendirilir")
def link_scenario_requirement(api: APIClient, project_id: str, context: dict):
    sid = context["scenario_id"]
    rid = context["requirement_id"]
    context["response"] = api.post(
        api.project_path(project_id, f"scenarios/{sid}/requirements"),
        json={"requirement_ids": [rid]},
    )


@then(parsers.parse('gereksinim detayinda "scenario_count" {count:d} olmalidir'))
def assert_req_scenario_count(api: APIClient, project_id: str, context: dict, count: int):
    resp = api.get(api.project_path(project_id, "requirements"))
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
    rid = context["requirement_id"]
    req = next((r for r in items if r["id"] == rid), None)
    assert req and req.get("scenario_count") == count


@given("senaryo-gereksinim baglantisi mevcut")
def link_exists(api: APIClient, project_id: str, scenario_id: str, requirement_id: str, context: dict):
    api.post(
        api.project_path(project_id, f"scenarios/{scenario_id}/requirements"),
        json={"requirement_ids": [requirement_id]},
    )
    context["scenario_id"] = scenario_id
    context["requirement_id"] = requirement_id


@when("ayni baglanti tekrar gonderilir")
def re_link(api: APIClient, project_id: str, context: dict):
    sid = context["scenario_id"]
    rid = context["requirement_id"]
    context["response"] = api.post(
        api.project_path(project_id, f"scenarios/{sid}/requirements"),
        json={"requirement_ids": [rid]},
    )


@given(parsers.parse("projede {count:d} gereksinim olusturulmus"))
def create_requirements(api: APIClient, project_id: str, context: dict, count: int):
    ids = []
    for i in range(count):
        resp = api.post(
            api.project_path(project_id, "requirements"),
            json={"external_id": f"REQ-{i + 1}", "title": f"Gereksinim {i + 1}", "priority": "medium"},
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])
    context["requirement_ids"] = ids


@given(parsers.parse("{count:d} gereksinim senaryolara baglanmis"))
def link_requirements(api: APIClient, project_id: str, context: dict, count: int):
    # Oncelikle senaryo olustur
    resp = api.post(
        api.project_path(project_id, "scenarios"),
        json={"title": "Kapsam Senaryosu", "steps": []},
    )
    sid = resp.json()["id"]
    req_ids = context["requirement_ids"][:count]
    api.post(
        api.project_path(project_id, f"scenarios/{sid}/requirements"),
        json={"requirement_ids": req_ids},
    )


@when("kapsam matrisi istenir")
def get_coverage_matrix(api: APIClient, project_id: str, context: dict):
    context["response"] = api.get(api.project_path(project_id, "coverage-matrix"))


@then(parsers.parse('"{field}" {value:d} olmalidir'))
def assert_coverage_field_int(context: dict, field: str, value: int):
    body = context["response"].json()
    assert body.get(field) == value, f"'{field}': beklenen {value}, gelen {body.get(field)}"


@then(parsers.parse('"{field}" yaklasik {value:f} olmalidir'))
def assert_coverage_field_float(context: dict, field: str, value: float):
    body = context["response"].json()
    actual = body.get(field, 0)
    assert abs(actual - value) < 1.0, f"'{field}': beklenen ~{value}, gelen {actual}"


@given("projede baglanmamis gereksinimler mevcut")
def unlinked_requirements(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "requirements"),
        json={"external_id": "REQ-UNLINKED", "title": "Baglanmamis", "priority": "low"},
    )
    context["unlinked_req_id"] = resp.json()["id"]


@when("kapsam bosluklari istenir")
def get_coverage_gaps(api: APIClient, project_id: str, context: dict):
    context["response"] = api.get(api.project_path(project_id, "coverage-gaps"))


@then("baglanmamis gereksinimler listede gorulmalidir")
def assert_gaps(context: dict):
    body = context["response"].json()
    items = body if isinstance(body, list) else body.get("gaps", body.get("items", []))
    assert len(items) > 0, "Bosluk bulunamadi"


@when("gereksinim silinir")
def delete_requirement(api: APIClient, project_id: str, context: dict):
    rid = context["requirement_id"]
    context["response"] = api.delete(api.project_path(project_id, f"requirements/{rid}"))


@then("kapsam matrisinde ilgili gereksinim bulunmamalidir")
def assert_req_deleted_from_matrix(api: APIClient, project_id: str, context: dict):
    resp = api.get(api.project_path(project_id, "coverage-matrix"))
    body = resp.json()
    reqs = body.get("requirements", [])
    rid = context["requirement_id"]
    assert not any(r.get("id") == rid for r in reqs)


@when(parsers.parse('"" kimlikli gereksinim olusturma istegi gonderilir'))
def create_empty_req(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "requirements"),
        json={"external_id": "", "title": "Test"},
    )
