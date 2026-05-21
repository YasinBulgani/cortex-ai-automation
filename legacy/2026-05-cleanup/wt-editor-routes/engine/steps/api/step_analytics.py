"""
steps/api/step_analytics.py — Kosu analitikleri (TS-07) step tanimlari.

Feature: analytics.feature
Kapsam: TC-0701 ~ TC-0703
"""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/analytics.feature")


@given("projede kosu verileri mevcut")
def execution_data_exists(api: APIClient, project_id: str, context: dict):
    # Kosu olustur ve sonuc kaydet
    resp = api.post(
        api.project_path(project_id, "scenarios"),
        json={"title": "Analitik Senaryo", "steps": []},
    )
    sid = resp.json()["id"]
    resp2 = api.post(
        api.project_path(project_id, "executions"),
        json={"name": "Analitik Kosu", "scenario_ids": [sid]},
    )
    context["analytics_execution_id"] = resp2.json()["id"]


@when(parsers.parse("{days:d} gunluk execution trend istegi gonderilir"))
def get_trends(api: APIClient, project_id: str, context: dict, days: int):
    context["response"] = api.get(
        api.project_path(project_id, "execution-trends"),
        params={"days": days},
    )


@then('yanit "data_points" listesi doner')
def assert_data_points(context: dict):
    body = context["response"].json()
    assert "data_points" in body


@then(parsers.parse('her veri noktasinda "{fields}" alanlari bulunmalidir'))
def assert_point_fields(context: dict, fields: str):
    body = context["response"].json()
    field_list = [f.strip().strip('"') for f in fields.split(",")]
    for point in body.get("data_points", []):
        for f in field_list:
            assert f in point, f"'{f}' eksik: {point}"


@given("ayni senaryo farkli kosularda passed ve failed olmus")
def flaky_scenario_setup(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "scenarios"),
        json={"title": "Flaky Senaryo", "steps": []},
    )
    sid = resp.json()["id"]
    context["flaky_scenario_id"] = sid
    # Kosu 1: passed
    r1 = api.post(
        api.project_path(project_id, "executions"),
        json={"name": "Kosu-1", "scenario_ids": [sid]},
    )
    eid1 = r1.json()["id"]
    detail1 = api.get(api.project_path(project_id, f"executions/{eid1}")).json()
    if detail1.get("results"):
        api.patch(
            api.project_path(project_id, f"executions/{eid1}/results/{detail1['results'][0]['id']}"),
            json={"status": "passed"},
        )
    # Kosu 2: failed
    r2 = api.post(
        api.project_path(project_id, "executions"),
        json={"name": "Kosu-2", "scenario_ids": [sid]},
    )
    eid2 = r2.json()["id"]
    detail2 = api.get(api.project_path(project_id, f"executions/{eid2}")).json()
    if detail2.get("results"):
        api.patch(
            api.project_path(project_id, f"executions/{eid2}/results/{detail2['results'][0]['id']}"),
            json={"status": "failed"},
        )


@when("flaky test listesi istenir")
def get_flaky_tests(api: APIClient, project_id: str, context: dict):
    context["response"] = api.get(api.project_path(project_id, "flaky-tests"))


@then(parsers.parse('sonuc listesinde ilgili senaryo "flip_count >= 1" ile gorunmelidir'))
def assert_flaky(context: dict):
    body = context["response"].json()
    items = body if isinstance(body, list) else body.get("items", [])
    assert any(item.get("flip_count", 0) >= 1 for item in items), f"Flaky senaryo bulunamadi: {body}"


@when("kosu istatistikleri istenir")
def get_stats(api: APIClient, project_id: str, context: dict):
    context["response"] = api.get(api.project_path(project_id, "execution-stats"))
