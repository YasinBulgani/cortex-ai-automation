"""
steps/api/step_flows.py — Akis editoru (TS-08) step tanimlari.

Feature: flows.feature
Kapsam: TC-0801 ~ TC-0803
"""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/flows.feature")


@when(parsers.parse('"{name}" ismiyle yeni akis olusturulur'))
def create_flow(api: APIClient, project_id: str, context: dict, name: str):
    context["response"] = api.post(
        api.project_path(project_id, "flows"),
        json={"name": name, "description": "BDD test akisi"},
    )
    if context["response"].status_code == 201:
        context["flow_id"] = context["response"].json()["id"]


@given("projede bir akis olusturulmus")
def flow_created(api: APIClient, project_id: str, context: dict):
    resp = api.post(
        api.project_path(project_id, "flows"),
        json={"name": "Test Akisi", "description": ""},
    )
    assert resp.status_code == 201
    context["flow_id"] = resp.json()["id"]


@when("akisin nodes ve edges verisi guncellenir")
def update_flow_graph(api: APIClient, project_id: str, context: dict):
    fid = context["flow_id"]
    nodes = [{"id": "n1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}}]
    edges = []
    context["response"] = api.put(
        api.project_path(project_id, f"flows/{fid}/graph"),
        json={"nodes": nodes, "edges": edges},
    )
    context["expected_nodes"] = nodes


@then("akis detayinda guncel nodes ve edges donmelidir")
def assert_flow_graph(api: APIClient, project_id: str, context: dict):
    fid = context["flow_id"]
    resp = api.get(api.project_path(project_id, f"flows/{fid}"))
    body = resp.json()
    assert body.get("nodes"), "Nodes bos"
