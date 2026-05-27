"""Unit tests for agents.banking_team.circuit_breaker and .errors.

Tests are fully self-contained: no DB, no HTTP, no LLM.
Covers:
  - CircuitBreaker: initial state, failure threshold, state transitions,
    OPEN → HALF_OPEN → CLOSED cycle, reset
  - CLOSED / OPEN / HALF_OPEN constants
  - AgentError: base exception with fields
  - LLMConnectionError / LLMResponseError / JSONParseError
  - ContextBuildError / PipelinePhaseError
"""
from __future__ import annotations

import time

import pytest

try:
    from app.domains.agents.banking_team.circuit_breaker import (
        CircuitBreaker,
        CLOSED,
        OPEN,
        HALF_OPEN,
        ollama_breaker,
    )
    _CB_OK = True
except ImportError:
    _CB_OK = False

try:
    from app.domains.agents.banking_team.errors import (
        AgentError,
        LLMConnectionError,
        LLMResponseError,
        JSONParseError,
        ContextBuildError,
        PipelinePhaseError,
    )
    _ERR_OK = True
except ImportError:
    _ERR_OK = False


# ---------------------------------------------------------------------------
# State constants
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="circuit_breaker import failed")
class TestStateConstants:
    def test_closed_value(self):
        assert CLOSED == "closed"

    def test_open_value(self):
        assert OPEN == "open"

    def test_half_open_value(self):
        assert HALF_OPEN == "half_open"


# ---------------------------------------------------------------------------
# CircuitBreaker — initial state
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="circuit_breaker import failed")
class TestCircuitBreakerInit:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CLOSED

    def test_initial_failure_count_zero(self):
        cb = CircuitBreaker()
        assert cb.failure_count == 0

    def test_can_execute_when_closed(self):
        cb = CircuitBreaker()
        assert cb.can_execute() is True

    def test_custom_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        # Still closed initially
        assert cb.state == CLOSED

    def test_custom_recovery_timeout(self):
        cb = CircuitBreaker(recovery_timeout=60)
        assert cb.state == CLOSED


# ---------------------------------------------------------------------------
# CircuitBreaker — failure and OPEN state
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="circuit_breaker import failed")
class TestCircuitBreakerFailures:
    def test_single_failure_below_threshold_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        assert cb.state == CLOSED

    def test_two_failures_below_threshold_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CLOSED

    def test_failure_count_increments(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

    def test_threshold_reached_opens_circuit(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=999)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == OPEN

    def test_can_execute_false_when_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=999)
        cb.record_failure()
        cb.record_failure()
        assert cb.can_execute() is False

    def test_failure_threshold_one(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=999)
        cb.record_failure()
        assert cb.state == OPEN


# ---------------------------------------------------------------------------
# CircuitBreaker — success resets
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="circuit_breaker import failed")
class TestCircuitBreakerSuccess:
    def test_success_resets_failure_count(self):
        cb = CircuitBreaker()
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0

    def test_success_closes_circuit(self):
        cb = CircuitBreaker()
        cb.record_success()
        assert cb.state == CLOSED

    def test_success_after_failures_closes(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CLOSED
        assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# CircuitBreaker — OPEN → HALF_OPEN via recovery_timeout=0
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="circuit_breaker import failed")
class TestCircuitBreakerRecovery:
    def test_open_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        # timeout=0 → any call should see HALF_OPEN
        assert cb.state == HALF_OPEN

    def test_can_execute_true_when_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        # Give it a moment for time.time() to advance past recovery_timeout=0
        assert cb.can_execute() is True

    def test_success_in_half_open_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        cb.record_success()
        assert cb.state == CLOSED

    def test_failure_in_half_open_reopens_circuit(self):
        # With recovery_timeout=0, state property auto-transitions OPEN→HALF_OPEN.
        # Verify by checking _state directly right after record_failure() sets OPEN.
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        # Force HALF_OPEN: read state property triggers auto-transition
        assert cb.state == HALF_OPEN
        # Now call record_failure() while in HALF_OPEN → should set _state = OPEN
        cb.record_failure()
        # Access internal state to avoid the auto-transition in the property
        with cb._lock:
            internal_state = cb._state
        assert internal_state == OPEN


# ---------------------------------------------------------------------------
# CircuitBreaker — reset
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="circuit_breaker import failed")
class TestCircuitBreakerReset:
    def test_reset_clears_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=999)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.reset()
        assert cb.failure_count == 0

    def test_reset_closes_open_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=999)
        cb.record_failure()
        assert cb.state == OPEN
        cb.reset()
        assert cb.state == CLOSED

    def test_reset_allows_execution_again(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=999)
        cb.record_failure()
        cb.reset()
        assert cb.can_execute() is True


# ---------------------------------------------------------------------------
# Global ollama_breaker instance
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="circuit_breaker import failed")
class TestOllamaBreaker:
    def test_is_circuit_breaker(self):
        assert isinstance(ollama_breaker, CircuitBreaker)


# ---------------------------------------------------------------------------
# AgentError
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ERR_OK, reason="errors import failed")
class TestAgentError:
    def test_is_exception(self):
        err = AgentError("test_agent", "something went wrong")
        assert isinstance(err, Exception)

    def test_agent_name_stored(self):
        err = AgentError("my_agent", "msg")
        assert err.agent_name == "my_agent"

    def test_default_not_recoverable(self):
        err = AgentError("agent", "msg")
        assert err.recoverable is False

    def test_recoverable_true(self):
        err = AgentError("agent", "msg", recoverable=True)
        assert err.recoverable is True

    def test_str_contains_agent_name(self):
        err = AgentError("my_agent", "bad thing")
        assert "my_agent" in str(err)

    def test_str_contains_message(self):
        err = AgentError("agent", "specific error message")
        assert "specific error message" in str(err)

    def test_can_raise_and_catch(self):
        with pytest.raises(AgentError):
            raise AgentError("agent", "error")


# ---------------------------------------------------------------------------
# LLMConnectionError
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ERR_OK, reason="errors import failed")
class TestLLMConnectionError:
    def test_is_agent_error(self):
        err = LLMConnectionError("agent", "llama2", Exception("timeout"))
        assert isinstance(err, AgentError)

    def test_model_stored(self):
        err = LLMConnectionError("agent", "gpt-4", Exception("refused"))
        assert err.model == "gpt-4"

    def test_original_stored(self):
        cause = ConnectionRefusedError("no connection")
        err = LLMConnectionError("agent", "gpt-4", cause)
        assert err.original is cause

    def test_is_recoverable(self):
        err = LLMConnectionError("agent", "model", Exception("x"))
        assert err.recoverable is True

    def test_str_contains_model(self):
        err = LLMConnectionError("agent", "llama3", Exception("err"))
        assert "llama3" in str(err)


# ---------------------------------------------------------------------------
# LLMResponseError
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ERR_OK, reason="errors import failed")
class TestLLMResponseError:
    def test_is_agent_error(self):
        err = LLMResponseError("agent", "gpt-4")
        assert isinstance(err, AgentError)

    def test_is_recoverable(self):
        err = LLMResponseError("agent", "gpt-4")
        assert err.recoverable is True

    def test_raw_response_truncated_to_500(self):
        long_response = "x" * 1000
        err = LLMResponseError("agent", "gpt-4", raw_response=long_response)
        assert len(err.raw_response) == 500

    def test_empty_raw_response_default(self):
        err = LLMResponseError("agent", "gpt-4")
        assert err.raw_response == ""


# ---------------------------------------------------------------------------
# JSONParseError
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ERR_OK, reason="errors import failed")
class TestJSONParseError:
    def test_is_agent_error(self):
        err = JSONParseError("agent", "{invalid}")
        assert isinstance(err, AgentError)

    def test_is_recoverable(self):
        err = JSONParseError("agent", "bad json")
        assert err.recoverable is True

    def test_raw_truncated_to_500(self):
        err = JSONParseError("agent", "z" * 1000)
        assert len(err.raw) == 500


# ---------------------------------------------------------------------------
# ContextBuildError
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ERR_OK, reason="errors import failed")
class TestContextBuildError:
    def test_is_agent_error(self):
        err = ContextBuildError("agent", "gitlab", Exception("403"))
        assert isinstance(err, AgentError)

    def test_source_stored(self):
        err = ContextBuildError("agent", "github.com/repo", Exception("not found"))
        assert err.source == "github.com/repo"

    def test_is_recoverable(self):
        err = ContextBuildError("agent", "src", Exception("err"))
        assert err.recoverable is True

    def test_original_stored(self):
        cause = FileNotFoundError("no file")
        err = ContextBuildError("agent", "src", cause)
        assert err.original is cause


# ---------------------------------------------------------------------------
# PipelinePhaseError
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ERR_OK, reason="errors import failed")
class TestPipelinePhaseError:
    def test_is_agent_error(self):
        err = PipelinePhaseError("discovery", "agent", Exception("fail"))
        assert isinstance(err, AgentError)

    def test_phase_stored(self):
        err = PipelinePhaseError("analysis", "agent", Exception("x"))
        assert err.phase == "analysis"

    def test_is_recoverable(self):
        err = PipelinePhaseError("phase", "agent", Exception("x"))
        assert err.recoverable is True

    def test_partial_data_default_empty(self):
        err = PipelinePhaseError("phase", "agent", Exception("x"))
        assert err.partial_data == {}

    def test_partial_data_stored(self):
        data = {"discovered": 5}
        err = PipelinePhaseError("discovery", "agent", Exception("x"), partial_data=data)
        assert err.partial_data == {"discovered": 5}

    def test_str_contains_phase(self):
        err = PipelinePhaseError("discovery", "agent", Exception("x"))
        assert "discovery" in str(err)
