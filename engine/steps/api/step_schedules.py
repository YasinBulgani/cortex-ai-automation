"""
steps/api/step_schedules.py — Zamanlamalar (TS-11) step tanimlari.

Feature: schedules.feature
Kapsam: TC-1101 ~ TC-1105
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/schedules.feature")


@when(parsers.parse('"{name}" adli "{cron}" cron ile zamanlama olusturulur'))
def create_schedule(api: APIClient, project_id: str, context: dict, name: str, cron: str):
    ids = context.get("scenario_ids", [context.get("scenario_id", "")])
    context["response"] = api.post(
        api.project_path(project_id, "schedules"),
        json={
            "name": name,
            "cron_expression": cron,
            "scenario_ids": ids,
            "is_active": True,
        },
    )
    if context["response"].status_code == 201:
        context["schedule_id"] = context["response"].json()["id"]


@given("aktif bir zamanlama ve senaryolari mevcut")
def active_schedule(api: APIClient, project_id: str, scenario_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "schedules"),
        json={
            "name": "Aktif Zamanlama",
            "cron_expression": "0 3 * * *",
            "scenario_ids": [scenario_id],
            "is_active": True,
        },
    )
    assert resp.status_code == 201
    context["schedule_id"] = resp.json()["id"]


@when("zamanlama tetiklenir")
def trigger_schedule(api: APIClient, project_id: str, context: dict):
    sid = context["schedule_id"]
    context["response"] = api.post(api.project_path(project_id, f"schedules/{sid}/trigger"))


@then(parsers.parse('yeni kosunun adi "Scheduled:" on eki icermelidir'))
def assert_scheduled_name(context: dict):
    body = context["response"].json()
    name = body.get("name", "")
    assert "Scheduled:" in name, f"Ad 'Scheduled:' icermiyor: {name}"


@then('zamanlamanin "last_run_at" alani guncellenmis olmalidir')
def assert_last_run_updated(api: APIClient, project_id: str, context: dict):
    sid = context["schedule_id"]
    resp = api.get(api.project_path(project_id, f"schedules"))
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
    sched = next((s for s in items if s["id"] == sid), None)
    assert sched and sched.get("last_run_at"), "last_run_at guncellenmemis"


@given("senaryo atamasi olmayan bir zamanlama mevcut")
def empty_schedule(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "schedules"),
        json={
            "name": "Bos Zamanlama",
            "cron_expression": "0 4 * * *",
            "scenario_ids": [],
            "is_active": True,
        },
    )
    assert resp.status_code == 201
    context["schedule_id"] = resp.json()["id"]


@given('zamanlama "scenario_ids" bos ve "regression_set_id" dolu')
def schedule_with_regression(api: APIClient, project_id: str, scenario_id: str, context: dict):
    # Regression set olustur ve senaryo ekle
    set_resp = api.post(
        api.project_path(project_id, "regression-sets"),
        json={"name": "Schedule Seti"},
    )
    set_id = set_resp.json()["id"]
    api.post(
        api.project_path(project_id, f"regression-sets/{set_id}/add"),
        json={"scenario_ids": [scenario_id]},
    )
    # Zamanlamayi regression set ile olustur
    resp = api.post(
        api.project_path(project_id, "schedules"),
        json={
            "name": "Regression Zamanlama",
            "cron_expression": "0 5 * * *",
            "scenario_ids": [],
            "regression_set_id": set_id,
            "is_active": True,
        },
    )
    assert resp.status_code == 201
    context["schedule_id"] = resp.json()["id"]


@given("regression set'te senaryolar mevcut")
def regression_has_scenarios():
    pass  # Onceki adimda eklendi


@then("kosu regression set'teki senaryolarla olusturulmalidir")
def assert_regression_execution(context: dict):
    body = context["response"].json()
    assert body.get("scenario_total", 0) > 0


@when("zamanlama bos cron ifadesi ile olusturma istegi gonderilir")
def create_empty_cron_schedule(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "schedules"),
        json={"name": "Bos Cron", "cron_expression": "", "scenario_ids": []},
    )
