"""Pure-function tests for Kiwi TCMS → Neurex mappers (no DB/IO). Phase 1+2."""

from __future__ import annotations

from app.domains.kiwi_tcms import mappers


def test_map_priority_known_and_default():
    assert mappers.map_priority("P1") == "critical"
    assert mappers.map_priority("p2") == "high"
    assert mappers.map_priority("P3") == "medium"
    assert mappers.map_priority("P5") == "low"
    assert mappers.map_priority(None) == "medium"
    assert mappers.map_priority("weird") == "medium"


def test_map_case_status():
    assert mappers.map_case_status("CONFIRMED") == "ready"
    assert mappers.map_case_status("PROPOSED") == "draft"
    assert mappers.map_case_status("DISABLED") == "deprecated"
    assert mappers.map_case_status(None) == "draft"


def test_map_execution_status():
    assert mappers.map_execution_status("PASSED") == "passed"
    assert mappers.map_execution_status("FAILED") == "failed"
    assert mappers.map_execution_status("ERROR") == "failed"
    assert mappers.map_execution_status("IDLE") == "not_run"
    assert mappers.map_execution_status("mystery") == "not_run"


def test_map_category_to_suite():
    out = mappers.map_category_to_suite({"id": 7, "name": "  Login  ", "description": "auth"})
    assert out == {"external_id": "7", "name": "Login", "description": "auth"}


def test_map_category_to_suite_blank_name_falls_back():
    out = mappers.map_category_to_suite({"id": 9, "name": "", "description": None})
    assert out["name"] == "Kategori 9"
    assert out["description"] == ""


def test_map_case_full():
    raw = {
        "id": 42,
        "summary": "Kullanıcı giriş yapar",
        "notes": "ön koşul yok",
        "setup": "tarayıcı açık",
        "priority__value": "P1",
        "case_status__name": "CONFIRMED",
        "is_automated": False,
        "category": 7,
        "tag": ["smoke", "auth"],
        "text": "1. Sayfayı aç\n2. Giriş yap",
    }
    out = mappers.map_case_to_neurex(raw)
    assert out["external_id"] == "42"
    assert out["category_external_id"] == "7"
    assert out["title"] == "Kullanıcı giriş yapar"
    assert out["objective"] == "ön koşul yok"
    assert out["preconditions"] == "tarayıcı açık"
    assert out["priority"] == "critical"
    assert out["status"] == "ready"
    assert out["automation_status"] == "manual"
    assert out["tags"] == ["smoke", "auth"]
    assert out["source_ref"] == "kiwi:case:42"
    assert len(out["steps"]) == 1
    assert out["steps"][0]["step_no"] == 1
    assert "Giriş yap" in out["steps"][0]["action"]


def test_map_case_automated_and_no_steps():
    raw = {"id": 1, "summary": "x", "is_automated": True, "text": "   "}
    out = mappers.map_case_to_neurex(raw)
    assert out["automation_status"] == "automated"
    assert out["steps"] == []
    assert out["category_external_id"] is None


def test_case_fingerprint_is_stable_and_sensitive():
    raw = {"id": 1, "summary": "x", "priority__value": "P3", "text": "do thing"}
    a = mappers.map_case_to_neurex(raw)
    fp1 = mappers.case_fingerprint(a)
    fp2 = mappers.case_fingerprint(mappers.map_case_to_neurex(dict(raw)))
    assert fp1 == fp2  # deterministic

    changed = dict(raw, summary="y")
    fp3 = mappers.case_fingerprint(mappers.map_case_to_neurex(changed))
    assert fp3 != fp1  # title change → different fingerprint

    # tag order must not matter
    t1 = mappers.case_fingerprint(mappers.map_case_to_neurex(dict(raw, tag=["a", "b"])))
    t2 = mappers.case_fingerprint(mappers.map_case_to_neurex(dict(raw, tag=["b", "a"])))
    assert t1 == t2

# ── Phase 2 mapper tests ──────────────────────────────────────────────

def test_map_plan_to_neurex():
    raw = {"id": 10, "name": "Sprint 1 Plan", "type__name": "release", "text": "scope"}
    out = mappers.map_plan_to_neurex(raw)
    assert out["external_id"] == "10"
    assert out["name"] == "Sprint 1 Plan"
    assert out["plan_type"] == "regression"
    assert out["scope_summary"] == "scope"

def test_map_plan_type_default():
    out = mappers.map_plan_to_neurex({"id": 1, "name": "x"})
    assert out["plan_type"] == "regression"

def test_plan_fingerprint_sensitive():
    a = mappers.map_plan_to_neurex({"id": 1, "name": "A"})
    b = mappers.map_plan_to_neurex({"id": 1, "name": "B"})
    assert mappers.plan_fingerprint(a) != mappers.plan_fingerprint(b)
    assert mappers.plan_fingerprint(a) == mappers.plan_fingerprint(a)

def test_map_run_to_neurex():
    raw = {
        "id": 50, "summary": "Release run", "plan": 10,
        "build__name": "v1.2.3", "environment__name": "staging",
        "status__name": "FINISHED",
    }
    out = mappers.map_run_to_neurex(raw)
    assert out["external_id"] == "50"
    assert out["plan_external_id"] == "10"
    assert out["name"] == "Release run"
    assert out["build_version"] == "v1.2.3"
    assert out["environment"] == "staging"
    assert out["status"] == "completed"

def test_map_run_status():
    assert mappers.map_run_status("RUNNING") == "in_progress"
    assert mappers.map_run_status("FINISHED") == "completed"
    assert mappers.map_run_status(None) == "planned"

def test_map_execution_to_neurex():
    raw = {"id": 200, "run": 50, "case": 500, "status__name": "PASSED", "notes": "ok"}
    out = mappers.map_execution_to_neurex(raw)
    assert out["external_id"] == "200"
    assert out["run_external_id"] == "50"
    assert out["case_external_id"] == "500"
    assert out["status"] == "passed"
    assert out["execution_notes"] == "ok"

def test_map_bug_to_neurex():
    raw = {"id": 99, "execution": 200, "bug_id": "GH-42", "summary": "crash", "url": "https://github.com/x/y/issues/42"}
    out = mappers.map_bug_to_neurex(raw)
    assert out["external_id"] == "99"
    assert out["execution_external_id"] == "200"
    assert out["external_key"] == "GH-42"
    assert out["title"] == "crash"
    assert "github.com" in out["url"]
