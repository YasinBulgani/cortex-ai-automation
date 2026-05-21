"""
steps/api/step_regression.py — Regresyon setleri (TS-09) step tanimlari.

Feature: regression.feature
Kapsam: TC-0901 ~ TC-0906
"""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/regression.feature")


@when(parsers.parse('"{name}" ismiyle regresyon seti olusturulur'))
def create_regression_set(api: APIClient, project_id: str, context: dict, name: str):
    context["response"] = api.post(
        api.project_path(project_id, "regression-sets"),
        json={"name": name},
    )
    if context["response"].status_code == 201:
        context["regression_set_id"] = context["response"].json()["id"]


@given("projede bir regresyon seti olusturulmus")
def regression_set_created(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "regression-sets"),
        json={"name": "Test Seti"},
    )
    assert resp.status_code == 201
    context["regression_set_id"] = resp.json()["id"]


@given(parsers.parse("projede {count:d} senaryo olusturulmus"))
def create_n_scenarios(api: APIClient, project_id: str, context: dict, count: int):
    ids = []
    for i in range(count):
        resp = api.post(
            api.project_path(project_id, "scenarios"),
            json={"title": f"Reg-Senaryo-{i + 1}", "steps": []},
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])
    context["scenario_ids"] = ids


@when(parsers.parse("{count:d} senaryonun ID'leri regresyon setine eklenir"))
def add_scenarios_to_set(api: APIClient, project_id: str, context: dict, count: int):
    set_id = context["regression_set_id"]
    ids = context["scenario_ids"][:count]
    context["response"] = api.post(
        api.project_path(project_id, f"regression-sets/{set_id}/add"),
        json={"scenario_ids": ids},
    )


@then(parsers.parse("set detayinda {count:d} senaryo bulunmalidir"))
def assert_set_count(api: APIClient, project_id: str, context: dict, count: int):
    set_id = context["regression_set_id"]
    resp = api.get(api.project_path(project_id, f"regression-sets/{set_id}"))
    body = resp.json()
    actual = body.get("scenario_count", len(body.get("scenario_ids", [])))
    assert actual == count, f"Beklenen: {count}, Gelen: {actual}"


@given(parsers.parse("regresyon setinde {count:d} senaryo mevcut"))
def set_has_scenarios(api: APIClient, project_id: str, context: dict, count: int):
    # Onceki adimlardan set ve senaryolar olusturulmus olmali
    pass


@when("ayni senaryo ID'leri tekrar eklenir")
def re_add_scenarios(api: APIClient, project_id: str, context: dict):
    set_id = context["regression_set_id"]
    ids = context["scenario_ids"]
    context["response"] = api.post(
        api.project_path(project_id, f"regression-sets/{set_id}/add"),
        json={"scenario_ids": ids},
    )


@then("set detayindaki senaryo sayisi degismemelidir")
def assert_count_unchanged(api: APIClient, project_id: str, context: dict):
    set_id = context["regression_set_id"]
    resp = api.get(api.project_path(project_id, f"regression-sets/{set_id}"))
    body = resp.json()
    actual = body.get("scenario_count", len(body.get("scenario_ids", [])))
    expected = len(context["scenario_ids"])
    assert actual == expected, f"Sayı degisti: {actual} != {expected}"


@when("AI regresyon seti oneri istegi gonderilir")
def request_ai_suggestion(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "regression-sets/suggest"),
        json={"extra_instructions": ""},
    )


@then(parsers.parse('yanit "sets" listesi en az {count:d} oneri icermelidir'))
def assert_suggestions(context: dict, count: int):
    body = context["response"].json()
    sets = body.get("sets", [])
    assert len(sets) >= count, f"Oneri sayisi yetersiz: {len(sets)}"


@given("AI regresyon seti onerileri alinmis")
def ai_suggestions_received(api: APIClient, project_id: str, scenario_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "regression-sets/suggest"),
        json={"extra_instructions": ""},
    )
    context["ai_suggestions"] = resp.json().get("sets", [])


@when("secilen oneriler kabul edilir")
def accept_suggestions(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "regression-sets/accept-suggestions"),
        json={"sets": context["ai_suggestions"]},
    )


@then("onerilen setler basariyla olusturulmus olmalidir")
def assert_sets_created(api: APIClient, project_id: str, context: dict):
    resp = api.get(api.project_path(project_id, "regression-sets"))
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", [])
    assert len(items) > 0, "Hic set olusturulmamis"
