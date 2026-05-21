"""
steps/api/step_executions.py — Test kosulari (TS-06) step tanimlari.

Feature: executions.feature
Kapsam: TC-0601 ~ TC-0606
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/executions.feature")


@when(parsers.parse('senaryo ID\'leri ile "{name}" adli kosu olusturulur'))
def create_execution(api: APIClient, project_id: str, context: dict, name: str):
    ids = context.get("scenario_ids", [])
    context["response"] = api.post(
        api.project_path(project_id, "executions"),
        json={"name": name, "scenario_ids": ids},
    )
    if context["response"].status_code == 201:
        context["execution_id"] = context["response"].json()["id"]


@given("bir test kosusu olusturulmus")
def execution_created(api: APIClient, project_id: str, context: dict):
    ids = context.get("scenario_ids", [])
    resp = api.post(
        api.project_path(project_id, "executions"),
        json={"name": "Test Kosusu", "scenario_ids": ids},
    )
    assert resp.status_code == 201
    body = resp.json()
    context["execution_id"] = body["id"]
    context["execution_name"] = body.get("name", "Test Kosusu")


@when("kosu detayi istenir")
def get_execution_detail(api: APIClient, project_id: str, context: dict):
    eid = context["execution_id"]
    context["response"] = api.get(api.project_path(project_id, f"executions/{eid}"))


@then('her senaryo icin "pending" statusunde sonuc kaydi bulunmalidir')
def assert_pending_results(context: dict):
    body = context["response"].json()
    results = body.get("results", [])
    for r in results:
        assert r.get("status") == "pending", f"Sonuc pending degil: {r}"


@then(parsers.parse('her sonuc kaydinda "{field}" alani dolu olmalidir'))
def assert_result_field(context: dict, field: str):
    body = context["response"].json()
    for r in body.get("results", []):
        assert r.get(field), f"'{field}' bos: {r}"


@when(parsers.parse('ilk sonuc kaydinin statusu "{status}" olarak guncellenir'))
def update_first_result(api: APIClient, project_id: str, context: dict, status: str):
    eid = context["execution_id"]
    detail = api.get(api.project_path(project_id, f"executions/{eid}")).json()
    result_id = detail["results"][0]["id"]
    context["updated_result_id"] = result_id
    context["response"] = api.patch(
        api.project_path(project_id, f"executions/{eid}/results/{result_id}"),
        json={"status": status},
    )


@then(parsers.parse('kosu detayindaki ilgili sonuc "{status}" olmalidir'))
def assert_result_status(api: APIClient, project_id: str, context: dict, status: str):
    eid = context["execution_id"]
    detail = api.get(api.project_path(project_id, f"executions/{eid}")).json()
    rid = context["updated_result_id"]
    result = next((r for r in detail["results"] if r["id"] == rid), None)
    assert result and result["status"] == status


@when("kosu re-run istegi gonderilir")
def rerun_execution(api: APIClient, project_id: str, context: dict):
    eid = context["execution_id"]
    context["response"] = api.post(api.project_path(project_id, f"executions/{eid}"))


@then('yeni kosunun adi "(re-run)" son eki icermelidir')
def assert_rerun_name(context: dict):
    body = context["response"].json()
    assert "(re-run)" in body.get("name", ""), f"Ad re-run icermiyor: {body.get('name')}"


@then("yeni kosunun senaryo sayisi orijinal ile ayni olmalidir")
def assert_same_scenario_count(context: dict):
    body = context["response"].json()
    orig_count = len(context.get("scenario_ids", []))
    assert body.get("scenario_total") == orig_count


@when("var olmayan kosu ID ile re-run istegi gonderilir")
def rerun_nonexistent(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, f"executions/{uuid.uuid4()}")
    )


@when("bos senaryo listesi ile kosu olusturulur")
def create_empty_execution(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "executions"),
        json={"name": "Bos Kosu", "scenario_ids": []},
    )
