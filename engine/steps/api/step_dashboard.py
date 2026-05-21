"""
steps/api/step_dashboard.py — Dashboard (TS-16) step tanimlari.

Feature: dashboard.feature
Kapsam: TC-1601 ~ TC-1602
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/dashboard.feature")


@given("projede senaryolar, onaylar, importlar ve kosular mevcut")
def populated_project(api: APIClient, context: dict):
    # Proje olustur
    resp = api.post(api.tspm("projects"), json={"name": f"Dashboard-{uuid.uuid4().hex[:6]}"})
    pid = resp.json()["id"]
    context["project_id"] = pid
    # Senaryo
    s = api.post(api.project_path(pid, "scenarios"), json={"title": "D-Senaryo", "steps": []})
    sid = s.json()["id"]
    # Kosu
    api.post(api.project_path(pid, "executions"), json={"name": "D-Kosu", "scenario_ids": [sid]})
    # Import (stub)
    api.post(api.project_path(pid, "imports"), json={"filename": "test.csv"})


@when("proje dashboard istegi gonderilir")
def get_dashboard(api: APIClient, context: dict):
    pid = context["project_id"]
    context["response"] = api.get(api.project_path(pid, "dashboard"))


@given("yeni olusturulmus bos bir proje mevcut")
def empty_project(api: APIClient, context: dict):
    resp = api.post(api.tspm("projects"), json={"name": f"Bos-{uuid.uuid4().hex[:6]}"})
    context["project_id"] = resp.json()["id"]
