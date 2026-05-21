"""
steps/api/step_integrations.py — Entegrasyonlar (TS-13) step tanimlari.

Feature: integrations.feature
Kapsam: TC-1301 ~ TC-1303
"""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/integrations.feature")


@when(parsers.parse('"{provider}" provider\'i ile entegrasyon olusturulur'))
def create_integration(api: APIClient, project_id: str, context: dict, provider: str):
    context["response"] = api.post(
        api.project_path(project_id, "integrations"),
        json={"provider": provider, "config": {"url": "https://example.com"}},
    )
    if context["response"].status_code == 201:
        context["integration_id"] = context["response"].json()["id"]


@given("projede bir entegrasyon olusturulmus")
def integration_created(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "integrations"),
        json={"provider": "jira", "config": {"url": "https://jira.test.com"}},
    )
    assert resp.status_code == 201
    context["integration_id"] = resp.json()["id"]


@when("entegrasyon sync istegi gonderilir")
def sync_integration(api: APIClient, project_id: str, context: dict):
    iid = context["integration_id"]
    context["response"] = api.post(
        api.project_path(project_id, f"integrations/{iid}/sync"),
    )


@when(parsers.parse('"" provider\'i ile entegrasyon olusturma istegi gonderilir'))
def create_empty_provider(api: APIClient, project_id: str, context: dict):
    context["response"] = api.post(
        api.project_path(project_id, "integrations"),
        json={"provider": ""},
    )
