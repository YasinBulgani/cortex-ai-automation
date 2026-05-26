"""Unit tests for app.domains.ingestion.service (in-memory store)."""
from __future__ import annotations

import pytest

try:
    import app.domains.ingestion.service as svc
except ImportError as _e:  # pragma: no cover
    svc = None  # type: ignore

pytestmark = pytest.mark.skipif(svc is None, reason=f"ingestion service unavailable: {svc}")


@pytest.fixture(autouse=True)
def _clear_store():
    """Ensure a clean in-memory store for every test."""
    if svc is not None:
        svc.clear()
    yield
    if svc is not None:
        svc.clear()


# ── ingest_text ───────────────────────────────────────────────────────────


def test_ingest_text_missing_body_raises_value_error():
    with pytest.raises(ValueError, match="body boş olamaz"):
        svc.ingest_text(project_id="proj-1", title="Empty", body="   ")


def test_ingest_text_success_stores_requirement():
    req = svc.ingest_text(
        project_id="proj-1",
        title="User login",
        body="The user must be able to log in with email and password.",
    )
    assert req.id.startswith("req-")
    assert req.project_id == "proj-1"
    assert req.title == "User login"
    assert req.source == "text"
    stored = svc.get_ingested(req.id)
    assert stored is not None
    assert stored.id == req.id


def test_ingest_text_empty_title_becomes_untitled():
    req = svc.ingest_text(
        project_id="proj-1",
        title="   ",
        body="Some requirement body with enough content.",
    )
    assert req.title == "Untitled"


def test_ingest_text_extracts_ac_from_bullet_list():
    body = (
        "Login requirements:\n"
        "- User should enter a valid email address\n"
        "- Password must be at least 8 characters\n"
        "- Error message shown on invalid credentials\n"
    )
    req = svc.ingest_text(project_id="proj-1", title="Login", body=body)
    assert len(req.acceptance_criteria) >= 1
    ac_texts = [ac.text for ac in req.acceptance_criteria]
    assert any("email" in t.lower() for t in ac_texts)


def test_ingest_text_with_source_ref_and_extra():
    req = svc.ingest_text(
        project_id="proj-2",
        title="Payment flow",
        body="The payment gateway must process cards within 3 seconds.",
        source="confluence",
        source_ref="CONF-42",
        extra={"space": "Engineering"},
    )
    assert req.source == "confluence"
    assert req.source_ref == "CONF-42"
    assert req.extra["space"] == "Engineering"


# ── get_ingested (KeyError when not found) ────────────────────────────────


def test_get_ingested_returns_none_when_not_found():
    """get_ingested returns None (not KeyError) for unknown IDs."""
    result = svc.get_ingested("req-doesnotexist")
    assert result is None


# ── list_ingested (project filter) ───────────────────────────────────────


def test_list_ingested_project_filter():
    svc.ingest_text(project_id="proj-alpha", title="Alpha req", body="Alpha requirement body text.")
    svc.ingest_text(project_id="proj-beta", title="Beta req", body="Beta requirement body text.")
    alpha = svc.list_ingested(project_id="proj-alpha")
    assert len(alpha) == 1
    assert alpha[0].project_id == "proj-alpha"


def test_list_ingested_no_filter_returns_all():
    svc.ingest_text(project_id="proj-1", title="R1", body="Requirement one body content here.")
    svc.ingest_text(project_id="proj-2", title="R2", body="Requirement two body content here.")
    all_reqs = svc.list_ingested()
    assert len(all_reqs) == 2


def test_list_ingested_sorted_by_created_at_descending():
    r1 = svc.ingest_text(project_id="proj-1", title="First", body="First requirement content.")
    r2 = svc.ingest_text(project_id="proj-1", title="Second", body="Second requirement content.")
    results = svc.list_ingested(project_id="proj-1")
    # Most recently created comes first
    assert results[0].id == r2.id
    assert results[1].id == r1.id


# ── jira_webhook_ingest ───────────────────────────────────────────────────


def test_ingest_jira_payload_basic():
    payload = {
        "issue": {
            "key": "NEUREX-101",
            "fields": {
                "summary": "Login button broken",
                "description": "Steps to reproduce: click login button.",
            },
        }
    }
    req = svc.ingest_jira_payload("proj-1", payload)
    assert req.source == "jira"
    assert req.source_ref == "NEUREX-101"
    assert req.title == "Login button broken"
    assert req.extra.get("jira_key") == "NEUREX-101"


def test_ingest_jira_payload_adf_description():
    """ADF-style dict description is flattened to plain text."""
    payload = {
        "issue": {
            "key": "NEUREX-202",
            "fields": {
                "summary": "ADF test",
                "description": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "The user must see an error"}],
                        }
                    ],
                },
            },
        }
    }
    req = svc.ingest_jira_payload("proj-1", payload)
    assert "error" in req.body.lower() or "user" in req.body.lower()
