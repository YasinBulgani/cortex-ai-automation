"""
steps/api/step_approvals.py — Onay kuyrugu (TS-05) step tanimlari.

Feature: approvals.feature
Kapsam: TC-0501 ~ TC-0504
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/approvals.feature")


@given("projede onay kayitlari mevcut")
def approvals_exist(api: APIClient, project_id: str, context: dict):
    # Onay kaydi olusturma: import veya AI uretimi sonrasi onay olusur
    # Stub: direkt approval endpoint'e POST (veya import tetikle)
    context["has_approvals"] = True


@when("onay listesi istenir")
def list_approvals(api: APIClient, project_id: str, context: dict):
    context["response"] = api.get(api.project_path(project_id, "approvals"))


@given(parsers.parse('projede "{status}" statusunde bir onay mevcut'))
def pending_approval_exists(api: APIClient, project_id: str, context: dict, status: str):
    # Ger gerce approval olusturma mekanizmasi import/AI uzerinden calısır
    # Test icin mevcut onay ID'si saklanir
    resp = api.get(api.project_path(project_id, "approvals"))
    if resp.status_code == 200:
        approvals = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
        pending = [a for a in approvals if a.get("status") == status]
        if pending:
            context["approval_id"] = pending[0]["id"]
            return
    context["approval_id"] = None


@when(parsers.parse('onay icin "{decision}" karari verilir'))
def decide_approval(api: APIClient, project_id: str, context: dict, decision: str):
    aid = context.get("approval_id")
    if not aid:
        context["response"] = type("R", (), {"status_code": 404, "json": lambda: {}, "text": "No approval"})()
        return
    context["response"] = api.post(
        api.project_path(project_id, f"approvals/{aid}/decide"),
        json={"decision": decision},
    )


@then(parsers.parse('onay statusu "{status}" olmalidir'))
def assert_approval_status(context: dict, status: str):
    body = context["response"].json()
    assert body.get("status") == status


@then(parsers.parse('onay "{field}" alani dolu olmalidir'))
def assert_approval_field(context: dict, field: str):
    body = context["response"].json()
    assert body.get(field), f"'{field}' bos: {body}"


@when("var olmayan onay ID ile karar istegi gonderilir")
def decide_nonexistent(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, f"approvals/{uuid.uuid4()}/decide"),
        json={"decision": "approved"},
    )
