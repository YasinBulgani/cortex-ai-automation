from __future__ import annotations

from unittest.mock import patch

from app.domains.ai import llm_trace


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, list | tuple | None]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, sql: str, params=None) -> None:
        self.executed.append((sql, params))

    def fetchall(self):
        return []

    def fetchone(self):
        if self.executed:
            sql = self.executed[-1][0]
            if "RETURNING id" in sql:
                return (123,)
        return (3, 2, 1, 0, 125, 400, 2, 1)


class _FakeConn:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def close(self) -> None:
        return None


def test_get_recent_traces_requires_project_scope() -> None:
    assert llm_trace.get_recent_traces() == []


def test_get_recent_traces_applies_project_and_user_filters(monkeypatch) -> None:
    cursor = _FakeCursor()
    monkeypatch.setattr(llm_trace, "_get_conn", lambda: _FakeConn(cursor))

    llm_trace.get_recent_traces(
        project_id="proj-1",
        user_id="user-1",
        run_id="run-1",
        agent_name="agent-a",
        limit=25,
    )

    sql, params = cursor.executed[0]
    assert "project_id = %s" in sql
    assert "user_id = %s" in sql
    assert "run_id = %s" in sql
    assert "agent_name = %s" in sql
    assert params == ["proj-1", "user-1", "run-1", "agent-a", 25]


def test_get_trace_stats_scoped_requires_project_scope() -> None:
    stats = llm_trace.get_trace_stats_scoped(project_id=None)
    assert stats["total_calls"] == 0
    assert stats["total_traces"] == 0


def test_log_llm_call_writes_project_and_user_scope(monkeypatch) -> None:
    cursor = _FakeCursor()
    monkeypatch.setattr(llm_trace, "_get_conn", lambda: _FakeConn(cursor))

    trace_id = llm_trace.log_llm_call(
        agent_name="chat",
        model="gpt-4o",
        system_prompt="system",
        user_prompt="user",
        response="response",
        latency_ms=123,
        project_id="proj-1",
        user_id="user-1",
    )

    sql, params = cursor.executed[0]
    assert "project_id, user_id, run_id, agent_name, provider, model" in sql
    assert params[0] == "proj-1"
    assert params[1] == "user-1"
    assert trace_id == 123


def test_build_llm_trace_record_estimates_contract_fields() -> None:
    record = llm_trace.build_llm_trace_record(
        agent_name="chat_stream",
        model="gpt-4o",
        system_prompt="system prompt",
        user_prompt="user prompt",
        response="assistant response",
        latency_ms=321,
        is_streaming=True,
    )

    assert record.provider == "openai"
    assert record.total_tokens == record.prompt_tokens + record.completion_tokens
    assert record.metadata["streaming"] is True


def test_update_json_parse_status_targets_exact_trace_id(monkeypatch) -> None:
    cursor = _FakeCursor()
    monkeypatch.setattr(llm_trace, "_get_conn", lambda: _FakeConn(cursor))

    ok = llm_trace.update_json_parse_status(321, True)

    assert ok is True
    sql, params = cursor.executed[0]
    assert "WHERE id = %s" in sql
    assert params == (True, 321)


def test_base_agent_trace_json_parse_uses_last_trace_id() -> None:
    from app.domains.agents.banking_team.base_agent import BaseAgent

    agent = BaseAgent()
    agent._last_trace_id = 555

    with patch("app.domains.ai.llm_trace.update_json_parse_status") as mocked_update:
        agent._trace_json_parse(True)

    mocked_update.assert_called_once_with(555, True)
