"""
steps/api/step_test_data.py — Test verisi yonetimi (TS-12) step tanimlari.

Feature: test_data.feature
Kapsam: TC-1201 ~ TC-1204
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/test_data.feature")


@when("asagidaki yapiyla test veri seti olusturulur:")
def create_test_data(api: APIClient, project_id: str, context: dict, datatable):
    row = datatable[0] if datatable else {}
    name = row.get("name", "Test Data")
    columns = [{"name": c.strip()} for c in row.get("columns", "").split(",")]
    raw_rows = row.get("rows", "").split(",")
    rows = []
    for rr in raw_rows:
        vals = rr.strip().split(":")
        row_data = {}
        for i, col in enumerate(columns):
            if i < len(vals):
                row_data[col["name"]] = vals[i]
        rows.append(row_data)
    context["response"] = api.post(
        api.project_path(project_id, "test-data"),
        json={"name": name, "columns": columns, "rows": rows},
    )
    if context["response"].status_code == 201:
        context["data_set_id"] = context["response"].json()["id"]


@given("projede bir senaryo ve veri seti olusturulmus")
def scenario_and_data(api: APIClient, project_id: str, scenario_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "test-data"),
        json={
            "name": "Login Verileri",
            "columns": [{"name": "username"}, {"name": "password"}],
            "rows": [{"username": "user1", "password": "pass1"}],
        },
    )
    assert resp.status_code == 201
    context["data_set_id"] = resp.json()["id"]
    context["scenario_id"] = scenario_id


@when("senaryo ile veri seti parametre eslesimiyle baglanir")
def bind_data(api: APIClient, project_id: str, context: dict):
    sid = context["scenario_id"]
    context["response"] = api.post(
        api.project_path(project_id, f"scenarios/{sid}/bind-data"),
        json={
            "data_set_id": context["data_set_id"],
            "parameter_mapping": {"kullanici": "username"},
        },
    )


@given('senaryo adimlari "{{kullanici}}" yer tutucusu icerir')
def scenario_with_placeholder(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "scenarios"),
        json={
            "title": "Parametrik Senaryo",
            "steps": [{"order": 1, "keyword": "When", "text": "{{kullanici}} ile giris yapilir"}],
        },
    )
    assert resp.status_code == 201
    context["scenario_id"] = resp.json()["id"]


@given("veri seti baglanmis")
def data_bound(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "test-data"),
        json={
            "name": "Bind Data",
            "columns": [{"name": "username"}],
            "rows": [{"username": "admin"}, {"username": "user"}],
        },
    )
    ds_id = resp.json()["id"]
    api.post(
        api.project_path(project_id, f"scenarios/{context['scenario_id']}/bind-data"),
        json={"data_set_id": ds_id, "parameter_mapping": {"kullanici": "username"}},
    )
    context["data_set_id"] = ds_id


@when("genisletilmis senaryo istenir")
def get_expanded(api: APIClient, project_id: str, context: dict):
    sid = context["scenario_id"]
    context["response"] = api.get(api.project_path(project_id, f"scenarios/{sid}/expanded"))


@then("her veri satiri icin adimlar genisletilmis donmelidir")
def assert_expanded(context: dict):
    body = context["response"].json()
    rows = body.get("expanded_rows", [])
    assert len(rows) > 0, "Genisletilmis satir bulunamadi"


@then('"{{kullanici}}" yerine gercek degerler yerlestirilmis olmalidir')
def assert_replaced(context: dict):
    body = context["response"].json()
    for row in body.get("expanded_rows", []):
        for step in row.get("steps", []):
            assert "{{kullanici}}" not in step.get("text", ""), "Yer tutucu degistirilmemis"


@given("projede bir senaryo mevcut")
def scenario_exists(api: APIClient, project_id: str, scenario_id: str, context: dict):
    context["scenario_id"] = scenario_id


@when("var olmayan veri seti ID ile baglama istegi gonderilir")
def bind_nonexistent(api: APIClient, project_id: str, context: dict):
    sid = context["scenario_id"]
    context["response"] = api.post(
        api.project_path(project_id, f"scenarios/{sid}/bind-data"),
        json={"data_set_id": str(uuid.uuid4()), "parameter_mapping": {}},
    )
