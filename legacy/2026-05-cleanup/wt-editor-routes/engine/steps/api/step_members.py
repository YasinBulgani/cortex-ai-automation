"""
steps/api/step_members.py — Proje uyeleri (TS-15) step tanimlari.

Feature: members.feature
Kapsam: TC-1501 ~ TC-1503
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/members.feature")


@given("baska bir kullanici mevcut")
def other_user_exists(context: dict):
    # Gercek ortamda 2. kullanici seed edilmis olmali
    context["other_user_id"] = str(uuid.uuid4())


@when(parsers.parse('kullanici "{role}" roluyle projeye eklenir'))
def add_member(api: APIClient, project_id: str, context: dict, role: str):
    context["response"] = api.post(
        api.project_path(project_id, "members"),
        json={"user_id": context["other_user_id"], "role": role},
    )
    if context["response"].status_code == 201:
        context["member_id"] = context["response"].json().get("id")


@given("projede bir uye mevcut")
def member_exists(api: APIClient, project_id: str, context: dict):
    uid = str(uuid.uuid4())
    resp = api.post(
        api.project_path(project_id, "members"),
        json={"user_id": uid, "role": "operator"},
    )
    if resp.status_code == 201:
        context["member_id"] = resp.json().get("id")
    context["other_user_id"] = uid


@when("uye projeden cikarilir")
def remove_member(api: APIClient, project_id: str, context: dict):
    mid = context["member_id"]
    context["response"] = api.delete(api.project_path(project_id, f"members/{mid}"))


@then("uye listesinde gorulmemelidir")
def assert_member_removed(api: APIClient, project_id: str, context: dict):
    resp = api.get(api.project_path(project_id, "members"))
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
    mid = context["member_id"]
    assert not any(m.get("id") == mid for m in items)


@when("kullanici rol belirtilmeden projeye eklenir")
def add_member_no_role(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "members"),
        json={"user_id": context["other_user_id"]},
    )
