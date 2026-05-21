"""
steps/api/step_scenarios.py — Senaryo yonetimi (TS-03) step tanimlari.

Feature: scenarios.feature
Kapsam: TC-0301 ~ TC-0309
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/scenarios.feature")


@when(parsers.parse('"{title}" baslikli yeni senaryo olusturulur'))
def create_scenario(api: APIClient, project_id: str, context: dict, title: str):
    context["response"] = api.post(
        api.project_path(project_id, "scenarios"),
        json={
            "title": title,
            "description": "BDD test",
            "steps": [{"order": 1, "keyword": "Given", "text": "Test adimi"}],
        },
    )
    if context["response"].status_code == 201:
        context["last_scenario_id"] = context["response"].json()["id"]


@when(parsers.parse('senaryonun basligi "{title}" olarak guncellenir'))
def update_scenario_title(api: APIClient, project_id: str, context: dict, title: str):
    sid = context["scenario_id"]
    context["response"] = api.put(
        api.project_path(project_id, f"scenarios/{sid}"),
        json={"title": title},
    )


@then("versiyon listesinde eski baslik versiyon 1 olarak saklanmalidir")
def assert_version_history(api: APIClient, project_id: str, context: dict):
    sid = context["scenario_id"]
    resp = api.get(api.project_path(project_id, f"scenarios/{sid}/versions"))
    assert resp.status_code == 200
    versions = resp.json()
    assert any(v.get("version_number") == 1 for v in versions), "Versiyon 1 bulunamadi"


@given("baska bir projede bir senaryo olusturulmus")
def scenario_in_other_project(api: APIClient, context: dict):
    resp = api.post(api.tspm("projects"), json={"name": f"Diger-{uuid.uuid4().hex[:6]}"})
    other_pid = resp.json()["id"]
    resp2 = api.post(
        api.project_path(other_pid, "scenarios"),
        json={"title": "Diger proje senaryosu", "steps": []},
    )
    context["other_project_id"] = other_pid
    context["other_scenario_id"] = resp2.json()["id"]


@when("bu senaryoya mevcut proje uzerinden erisim denenir")
def access_cross_project_scenario(api: APIClient, project_id: str, context: dict):
    sid = context["other_scenario_id"]
    context["response"] = api.get(api.project_path(project_id, f"scenarios/{sid}"))


@when(parsers.parse('senaryolar "{term}" arama terimiyle filtrelenir'))
def search_scenarios(api: APIClient, project_id: str, context: dict, term: str):
    context["response"] = api.get(
        api.project_path(project_id, "scenarios"),
        params={"q": term},
    )


@then(parsers.parse('sonuc listesinde yalnizca "{term}" iceren senaryolar bulunmalidir'))
def assert_search_results(context: dict, term: str):
    items = context["response"].json()
    if isinstance(items, dict):
        items = items.get("items", items.get("data", []))
    for item in items:
        assert term.lower() in item["title"].lower(), f"'{term}' icermiyor: {item['title']}"


@when("ilk 2 senaryonun ID'leri ile toplu silme istegi gonderilir")
def bulk_delete(api: APIClient, project_id: str, context: dict):
    ids = context["scenario_ids"][:2]
    context["deleted_ids"] = ids
    context["response"] = api.post(
        api.project_path(project_id, "scenarios/bulk-delete"),
        json={"ids": ids},
    )


@then("senaryo listesinde yalnizca silinmeyen senaryo kalmalidir")
def assert_remaining_scenario(api: APIClient, project_id: str, context: dict):
    resp = api.get(api.project_path(project_id, "scenarios"))
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
    remaining_ids = {s["id"] for s in items}
    for did in context["deleted_ids"]:
        assert did not in remaining_ids, f"Silinen senaryo hala mevcut: {did}"


@when("o senaryonun ID'si ile mevcut projede toplu silme denenir")
def bulk_delete_cross_project(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "scenarios/bulk-delete"),
        json={"ids": [context["other_scenario_id"]]},
    )


@then("diger projenin senaryosu silinmemis olmalidir")
def assert_other_scenario_exists(api: APIClient, context: dict):
    resp = api.get(
        api.project_path(context["other_project_id"], f"scenarios/{context['other_scenario_id']}")
    )
    assert resp.status_code == 200


@given("senaryo basligi guncellenmis")
def scenario_title_updated(api: APIClient, project_id: str, context: dict):
    sid = context["scenario_id"]
    api.put(api.project_path(project_id, f"scenarios/{sid}"), json={"title": "V2 Baslik"})


@when(parsers.parse("versiyon {v1:d} ve versiyon {v2:d} karsilastirilir"))
def compare_versions(api: APIClient, project_id: str, context: dict, v1: int, v2: int):
    sid = context["scenario_id"]
    context["response"] = api.get(
        api.project_path(project_id, f"scenarios/{sid}/versions/{v1}/diff/{v2}")
    )


@then(parsers.parse('diff sonucunda "{field}" true olmalidir'))
def assert_diff_field_true(context: dict, field: str):
    body = context["response"].json()
    assert body.get(field) is True, f"'{field}' true degil: {body}"
