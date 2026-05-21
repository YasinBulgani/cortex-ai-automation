"""
steps/api/step_projects.py — Proje yonetimi (TS-02) step tanimlari.

Feature: projects.feature
Kapsam: TC-0201 ~ TC-0206
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/projects.feature")


@when(parsers.parse('"{name}" ismi ve "{desc}" ile proje olusturma istegi gonderilir'))
def create_project_with_desc(api: APIClient, context: dict, name: str, desc: str):
    context["response"] = api.post(
        api.tspm("projects"),
        json={"name": name, "description": desc},
    )


@when(parsers.parse('"{name}" ismi ile proje olusturma istegi gonderilir'))
def create_project(api: APIClient, context: dict, name: str):
    context["response"] = api.post(api.tspm("projects"), json={"name": name})


@when(parsers.parse("{length:d} karakter uzunlugunda isim ile proje olusturma istegi gonderilir"))
def create_project_long_name(api: APIClient, context: dict, length: int):
    name = "A" * length
    context["response"] = api.post(api.tspm("projects"), json={"name": name})


@when("proje listesi istenir")
def list_projects(api: APIClient, context: dict):
    context["response"] = api.get(api.tspm("projects"))


@then(parsers.parse('listenin ilk elemani "{name}" olmalidir'))
def assert_first_project(context: dict, name: str):
    items = context["response"].json()
    first = items[0] if isinstance(items, list) else items.get("items", items.get("data", []))[0]
    assert first["name"] == name, f"Ilk proje: '{first['name']}', beklenen: '{name}'"


@when("var olmayan proje ID ile dashboard istegi gonderilir")
def get_nonexistent_dashboard(api: APIClient, context: dict):
    fake_id = str(uuid.uuid4())
    context["response"] = api.get(api.project_path(fake_id, "dashboard"))
