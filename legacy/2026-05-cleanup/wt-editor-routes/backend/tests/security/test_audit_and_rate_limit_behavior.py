"""Behavioral security checks for middleware, audit, and rate limiting."""

import json
import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import has_rate_limit


def _extract_audit_events(caplog) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for record in caplog.records:
        if record.name != "bgts.audit":
            continue
        try:
            events.append(json.loads(record.getMessage()))
        except json.JSONDecodeError:
            continue
    return events


def test_audit_middleware_records_state_changing_request(client: TestClient, caplog) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert login.status_code == 200

    with caplog.at_level(logging.INFO, logger="bgts.audit"):
        response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    events = _extract_audit_events(caplog)
    assert events

    logout_event = next(
        (event for event in events if event.get("path") == "/api/v1/auth/logout"),
        None,
    )
    assert logout_event is not None
    assert logout_event["method"] == "POST"
    assert isinstance(logout_event.get("user_id"), str)


def test_audit_middleware_records_forwarded_client_ip(
    client: TestClient,
    caplog,
) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    with caplog.at_level(logging.INFO, logger="bgts.audit"):
        response = client.post(
            "/api/v1/auth/logout-all",
            headers={
                "Authorization": f"Bearer {token}",
                "x-forwarded-for": "198.51.100.77, 10.0.0.1",
            },
        )

    assert response.status_code == 200
    events = _extract_audit_events(caplog)
    assert events

    event = next(
        (item for item in events if item.get("path") == "/api/v1/auth/logout-all"),
        None,
    )
    assert event is not None
    assert event["ip"] == "198.51.100.77"
    assert event["method"] == "POST"


def test_rate_limit_enforced_for_login_when_enabled(
    client: TestClient,
) -> None:
    if not has_rate_limit:
        pytest.skip("Rate limiting not configured in this environment.")

    seen_status = set()
    payload = {"email": "admin@example.com", "password": "wrong-password"}
    for _ in range(12):
        response = client.post("/api/v1/auth/login", json=payload)
        seen_status.add(response.status_code)

    assert 429 in seen_status
