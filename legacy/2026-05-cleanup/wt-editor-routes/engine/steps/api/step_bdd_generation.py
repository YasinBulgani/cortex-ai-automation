"""
steps/api/step_bdd_generation.py — BDD senaryo uretimi (TS-04) step tanimlari.

Feature: bdd_generation.feature
Kapsam: TC-0401 ~ TC-0404
"""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/bdd_generation.feature")


@when("asagidaki analiz metni ile BDD uretim istegi gonderilir:")
def generate_bdd_from_text(api: APIClient, project_id: str, context: dict, docstring: str):
    context["response"] = api.post(
        api.project_path(project_id, "scenarios/generate-bdd"),
        json={"analysis_text": docstring.strip()},
    )


@when(parsers.parse('"{text}" analiz metni ile BDD uretim istegi gonderilir'))
def generate_bdd_short(api: APIClient, project_id: str, context: dict, text: str):
    context["response"] = api.post(
        api.project_path(project_id, "scenarios/generate-bdd"),
        json={"analysis_text": text},
    )


@given("BDD senaryolari basariyla uretilmis")
def bdd_scenarios_generated(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "scenarios/generate-bdd"),
        json={"analysis_text": "Kullanici giris yapar, profil sayfasini goruntuler ve cikis yapar."},
    )
    assert resp.status_code == 200
    context["generated_scenarios"] = resp.json().get("scenarios", [])


@when("uretilen senaryolar kaydetme istegi ile gonderilir")
def save_bdd_scenarios(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "scenarios/save-bdd"),
        json={"scenarios": context["generated_scenarios"]},
    )


@then('kaydedilen tum senaryolar "draft" statusunde olmalidir')
def assert_all_draft(api: APIClient, project_id: str, context: dict):
    resp = api.get(api.project_path(project_id, "scenarios"))
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
    for s in items:
        assert s.get("status") == "draft", f"Status 'draft' degil: {s}"
