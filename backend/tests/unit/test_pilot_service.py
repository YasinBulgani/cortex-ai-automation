"""Unit tests for the Pilot orchestrator service.

All tests are fully in-memory — no DB, no real event bus.
The service uses an in-memory dict store and the event bus import
is guarded with try/except inside the module itself.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.pilot import service as svc
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="pilot domain not importable")


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_sessions():
    """Isolate each test by clearing the in-memory session store."""
    svc.clear()
    yield
    svc.clear()


# ── create_session ─────────────────────────────────────────────────────────────

class TestCreateSession:
    def test_session_stored_and_returned(self):
        s = svc.create_session(project_id="p1", user_id="u1")

        assert s.id.startswith("ps-")
        assert s.project_id == "p1"
        assert s.user_id == "u1"

    def test_initial_intent_is_unknown(self):
        s = svc.create_session(project_id="p1", user_id="u1")

        assert s.intent == "unknown"

    def test_welcome_turn_added(self):
        s = svc.create_session(project_id="p1", user_id="u1")

        assert len(s.turns) == 1
        assert s.turns[0].role == "system"

    def test_session_retrievable_via_get(self):
        s = svc.create_session(project_id="p1", user_id="u1")
        fetched = svc.get_session(s.id)

        assert fetched is s


# ── detect_intent ──────────────────────────────────────────────────────────────

class TestDetectIntent:
    def test_url_pattern_matches_explore(self):
        intent = svc.detect_intent("https://app.example.com'yi tara ve test et")
        assert intent == "explore_url_and_generate_tests"

    def test_prd_keyword_matches_scenarios(self):
        intent = svc.detect_intent("Bu PRD'yi test et, senaryo üret")
        assert intent == "create_scenarios_from_requirements"

    def test_run_keyword_matches_run_suite(self):
        intent = svc.detect_intent("smoke setini çalıştır")
        assert intent == "run_test_suite"

    def test_failure_keyword_matches_analyze(self):
        intent = svc.detect_intent("neden düştü, debug et kök neden analizi yap")
        assert intent == "analyze_failures"

    def test_unknown_text_returns_unknown(self):
        intent = svc.detect_intent("merhaba dünya")
        assert intent == "unknown"


# ── converse — intent detection ────────────────────────────────────────────────

class TestConverseIntentDetection:
    def test_converse_detects_intent_from_first_message(self):
        s = svc.create_session(project_id="p1", user_id="u1")
        s = svc.converse(s.id, "https://my-app.com'yi tara")

        assert s.intent == "explore_url_and_generate_tests"

    def test_stages_populated_after_intent_known(self):
        s = svc.create_session(project_id="p1", user_id="u1")
        s = svc.converse(s.id, "regression testleri çalıştır")

        assert len(s.stages) > 0

    def test_clarification_question_raised_when_input_missing(self):
        s = svc.create_session(project_id="p1", user_id="u1")
        s = svc.converse(s.id, "test verisi üret")

        assert s.pending_clarification is not None
        assert s.pending_clarification.field_name in ("entity", "goal", "source", "scope")


# ── answer_clarification ───────────────────────────────────────────────────────

class TestAnswerClarification:
    def _session_with_pending_question(self) -> "svc.PilotSession":
        s = svc.create_session(project_id="p1", user_id="u1")
        # Trigger a known intent that has required inputs
        s = svc.converse(s.id, "https://example.com tara")
        assert s.pending_clarification is not None, "Expected a pending clarification"
        return s

    def test_answer_stored_in_inputs(self):
        s = self._session_with_pending_question()
        field = s.pending_clarification.field_name

        s = svc.answer_clarification(s.id, "https://example.com")

        assert s.inputs.get(field) == "https://example.com"

    def test_answering_all_clears_pending(self):
        s = self._session_with_pending_question()

        # Provide answers for all required questions in a loop
        for _ in range(10):  # max iterations safety
            if s.pending_clarification is None:
                break
            s = svc.answer_clarification(s.id, "dummy-answer")

        assert s.pending_clarification is None

    def test_error_when_no_pending_question(self):
        s = svc.create_session(project_id="p1", user_id="u1")

        with pytest.raises(ValueError, match="Cevap bekleyen soru yok"):
            svc.answer_clarification(s.id, "anything")


# ── execute_next_stage ─────────────────────────────────────────────────────────

class TestExecuteNextStage:
    def _ready_session(self, intent_text: str = "test verisi üret") -> "svc.PilotSession":
        """Create a session, detect intent, answer all clarifications."""
        s = svc.create_session(project_id="p1", user_id="u1")
        s = svc.converse(s.id, intent_text)
        # Drain all clarification questions
        for _ in range(15):
            if s.pending_clarification is None:
                break
            s = svc.answer_clarification(s.id, "dummy")
        return s

    def test_first_pending_stage_becomes_complete(self):
        s = self._ready_session()
        first_pending = next((st for st in s.stages if st.status == "pending"), None)
        assert first_pending is not None, "Need at least one pending stage"

        s = svc.execute_next_stage(s.id)

        completed = next((st for st in s.stages if st.id == first_pending.id), None)
        assert completed.status == "complete"

    def test_system_turn_added_on_execute(self):
        s = self._ready_session()
        turn_count_before = len(s.turns)

        s = svc.execute_next_stage(s.id)

        assert len(s.turns) > turn_count_before

    def test_error_when_pending_clarification_exists(self):
        s = svc.create_session(project_id="p1", user_id="u1")
        # Trigger intent to get clarification pending
        s = svc.converse(s.id, "https://example.com tara")
        assert s.pending_clarification is not None

        with pytest.raises(ValueError, match="Önce bekleyen soruyu cevaplayın"):
            svc.execute_next_stage(s.id)

    def test_error_when_session_not_found(self):
        with pytest.raises(ValueError, match="bulunamadı"):
            svc.execute_next_stage("nonexistent-session-id")


# ── list_sessions ──────────────────────────────────────────────────────────────

class TestListSessions:
    def test_filter_by_project_id(self):
        svc.create_session(project_id="proj-A", user_id="u1")
        svc.create_session(project_id="proj-B", user_id="u2")

        result = svc.list_sessions(project_id="proj-A")

        assert len(result) == 1
        assert result[0].project_id == "proj-A"

    def test_filter_by_user_id(self):
        svc.create_session(project_id="proj-A", user_id="alice")
        svc.create_session(project_id="proj-A", user_id="bob")

        result = svc.list_sessions(user_id="alice")

        assert all(s.user_id == "alice" for s in result)

    def test_returns_all_when_no_filter(self):
        svc.create_session(project_id="p1", user_id="u1")
        svc.create_session(project_id="p2", user_id="u2")

        result = svc.list_sessions()

        assert len(result) == 2
