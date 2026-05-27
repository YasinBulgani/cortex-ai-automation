"""Comprehensive tests for BaseAgent — the foundation of every banking agent.

Covers: AgentResult, _resolve_model, _get_model_chain, _get_context_budget,
        _enrich_system_prompt, call (retry + fallback), call_json (parse paths),
        _extract_json_object, _extract_json_array, safe_run, learn,
        get_project_context cache, reset_project_context.
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# We need to patch settings BEFORE importing the module under test so that the
# top-level `from app.config import settings` gets our fake.
_FAKE_SETTINGS = SimpleNamespace(
    ai_provider="ollama",
    ollama_base_url="http://localhost:11434/v1",
    ollama_api_key="ollama",
    ollama_model_analyst="qwen2.5:32b",
    ollama_model_fast="mistral:latest",
    ollama_model_coder="qwen2.5-coder:7b",
    openai_api_key="sk-test",
    openai_base_url="https://api.openai.com/v1",
    openai_model="gpt-4o",
    anthropic_api_key="",
)

# Patch settings at the module level so every import of base_agent sees it.
with patch("app.config.settings", _FAKE_SETTINGS):
    from app.domains.agents.banking_team.base_agent import (
        AgentResult,
        BaseAgent,
        MAX_LLM_RETRIES,
        RETRY_BACKOFF_BASE,
        _DEFAULT_CTX_LIMIT,
        _MODEL_CTX_LIMITS,
        _PROJECT_CTX_TTL,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_completion(content: str = '{"ok": true}'):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class _ConcreteAgent(BaseAgent):
    """Test double: BaseAgent'ı somutlaştırmak için minimal subclass.

    run() @abstractmethod olduğundan doğrudan BaseAgent() instantiate edilemez.
    Bu sınıf test için gerçek bir alt sınıf simüle eder.
    """
    def run(self, context: dict):
        return AgentResult(status="completed", output={"test": True})


def _new_agent(**overrides):
    """Create a fresh _ConcreteAgent with optional attribute overrides."""
    agent = _ConcreteAgent()
    for k, v in overrides.items():
        setattr(agent, k, v)
    return agent


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AgentResult dataclass
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentResult:
    def test_creation_with_required_fields(self):
        r = AgentResult(agent_name="test", success=True)
        assert r.agent_name == "test"
        assert r.success is True

    def test_default_values(self):
        r = AgentResult(agent_name="a", success=False)
        assert r.data == {}
        assert r.error == ""
        assert r.duration_ms == 0
        assert r.tokens_used == 0

    def test_custom_fields(self):
        r = AgentResult(
            agent_name="x",
            success=True,
            data={"key": "val"},
            error="err",
            duration_ms=123,
            tokens_used=456,
        )
        assert r.data == {"key": "val"}
        assert r.error == "err"
        assert r.duration_ms == 123
        assert r.tokens_used == 456

    def test_data_default_not_shared(self):
        """Each AgentResult should get its own dict (default_factory)."""
        r1 = AgentResult(agent_name="a", success=True)
        r2 = AgentResult(agent_name="b", success=True)
        r1.data["x"] = 1
        assert "x" not in r2.data


# ═══════════════════════════════════════════════════════════════════════════════
# 2. _resolve_model
# ═══════════════════════════════════════════════════════════════════════════════


class TestResolveModel:
    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_explicit_model_returned(self):
        agent = _new_agent(model="my-custom-model")
        assert agent._resolve_model() == "my-custom-model"

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_ollama_default(self):
        agent = _new_agent(model="")
        assert agent._resolve_model() == "mistral:latest"

    def test_openai_default(self):
        openai_settings = SimpleNamespace(**vars(_FAKE_SETTINGS))
        openai_settings.ai_provider = "openai"
        with patch("app.domains.agents.banking_team.base_agent.settings", openai_settings):
            agent = _new_agent(model="")
            assert agent._resolve_model() == "gpt-4o"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. _get_model_chain
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetModelChain:
    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_deduplication(self):
        agent = _new_agent(model="mistral:latest", model_fallback=["mistral:latest"])
        chain = agent._get_model_chain()
        # mistral:latest appears once as primary and is NOT duplicated
        assert chain.count("mistral:latest") == 1

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_chain_order_primary_then_fallback_then_global(self):
        agent = _new_agent(model="qwen2.5:14b", model_fallback=["mistral:7b"])
        chain = agent._get_model_chain()
        assert chain[0] == "qwen2.5:14b"
        assert "mistral:7b" in chain
        # Global fallback should be at the end
        assert "mistral:latest" in chain  # ollama_model_fast
        assert "qwen2.5:32b" in chain     # ollama_model_analyst

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_no_global_fallback_for_openai(self):
        openai_settings = SimpleNamespace(**vars(_FAKE_SETTINGS))
        openai_settings.ai_provider = "openai"
        with patch("app.domains.agents.banking_team.base_agent.settings", openai_settings):
            agent = _new_agent(model="gpt-4o", model_fallback=["gpt-4o-mini"])
            chain = agent._get_model_chain()
            # No Ollama models should leak in
            assert all("qwen" not in m and "mistral" not in m for m in chain)

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_empty_fallback(self):
        agent = _new_agent(model="qwen2.5:32b", model_fallback=[])
        chain = agent._get_model_chain()
        assert chain[0] == "qwen2.5:32b"
        # Still gets global ollama fallbacks
        assert len(chain) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# 4. _get_context_budget
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetContextBudget:
    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_known_model_budget(self):
        agent = _new_agent(model="gpt-4o")
        budget = agent._get_context_budget()
        assert budget == int(300000 * 0.40)

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_unknown_model_uses_default(self):
        agent = _new_agent(model="totally-unknown-model")
        budget = agent._get_context_budget()
        assert budget == int(_DEFAULT_CTX_LIMIT * 0.40)

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_budget_is_40_percent(self):
        for model_name, limit in _MODEL_CTX_LIMITS.items():
            agent = _new_agent(model=model_name)
            assert agent._get_context_budget() == int(limit * 0.40)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. _enrich_system_prompt
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnrichSystemPrompt:
    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_injection_disabled(self):
        agent = _new_agent(inject_project_context=False, model="gpt-4o")
        result = agent._enrich_system_prompt("Hello")
        assert result == "Hello"

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(BaseAgent, "get_project_context", return_value={})
    def test_empty_context_no_change(self, _mock_ctx):
        agent = _new_agent(model="gpt-4o")
        result = agent._enrich_system_prompt("Hello")
        assert result == "Hello"

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(
        BaseAgent,
        "get_project_context",
        return_value={"description": "Test Banking App"},
    )
    def test_context_block_appended(self, _mock_ctx):
        agent = _new_agent(model="gpt-4o")
        result = agent._enrich_system_prompt("Base prompt.")
        assert "PROJE BAĞLAMI" in result
        assert "Test Banking App" in result
        assert result.startswith("Base prompt.")

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(
        BaseAgent,
        "get_project_context",
        return_value={"description": "X" * 5000, "db_schema": "Y" * 5000},
    )
    def test_budget_truncation(self, _mock_ctx):
        """When the system prompt is already large, context is skipped."""
        # Use a small-context model: llama3.1:8b → 10000 chars, budget = 4000
        agent = _new_agent(model="llama3.1:8b")
        # Make the prompt so large that budget - len(prompt) < 500
        long_prompt = "Z" * 3501  # budget = 4000 - 3501 = 499 < 500 → skip
        result = agent._enrich_system_prompt(long_prompt)
        assert result == long_prompt

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(
        BaseAgent,
        "get_project_context",
        return_value={"description": "Desc", "knowledge": "K" * 3000},
    )
    def test_sections_respect_priority_order(self, _mock_ctx):
        agent = _new_agent(model="gpt-4o")
        result = agent._enrich_system_prompt("Start.")
        # description should appear before knowledge (priority order)
        desc_idx = result.find("Proje Tanımı")
        knowledge_idx = result.find("Geçmiş Öğrenimler")
        if desc_idx != -1 and knowledge_idx != -1:
            assert desc_idx < knowledge_idx


# ═══════════════════════════════════════════════════════════════════════════════
# 6. call() — retry + fallback + trace
# ═══════════════════════════════════════════════════════════════════════════════


class TestCall:
    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(BaseAgent, "_enrich_system_prompt", side_effect=lambda s: s)
    @patch("app.domains.ai.llm_trace.log_llm_call")
    def test_success_on_first_try(self, mock_trace, _mock_enrich):
        agent = _new_agent(model="mistral:latest")
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion("result text")
        agent._client = client

        out = agent.call("system", "user")
        assert out == "result text"
        assert client.chat.completions.create.call_count == 1

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(BaseAgent, "_enrich_system_prompt", side_effect=lambda s: s)
    @patch("app.domains.ai.llm_trace.log_llm_call")
    @patch("time.sleep")  # don't actually sleep
    def test_retry_then_success(self, mock_sleep, mock_trace, _mock_enrich):
        agent = _new_agent(model="mistral:latest", model_fallback=[])
        client = MagicMock()
        # First call fails, second succeeds
        client.chat.completions.create.side_effect = [
            RuntimeError("LLM down"),
            _make_completion("recovered"),
        ]
        agent._client = client

        out = agent.call("system", "user")
        assert out == "recovered"
        assert client.chat.completions.create.call_count == 2
        # Verify backoff sleep was called
        mock_sleep.assert_called_once()

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(BaseAgent, "_enrich_system_prompt", side_effect=lambda s: s)
    @patch("app.domains.ai.llm_trace.log_llm_call")
    @patch("time.sleep")
    def test_fallback_chain_model1_fails_model2_succeeds(
        self, mock_sleep, mock_trace, _mock_enrich
    ):
        # Use a 2-model chain where model 1 always fails
        openai_settings = SimpleNamespace(**vars(_FAKE_SETTINGS))
        openai_settings.ai_provider = "openai"
        with patch("app.domains.agents.banking_team.base_agent.settings", openai_settings):
            agent = _new_agent(model="gpt-4o", model_fallback=["gpt-4o-mini"])
            client = MagicMock()

            call_count = {"n": 0}
            def side_effect(**kwargs):
                call_count["n"] += 1
                if kwargs["model"] == "gpt-4o":
                    raise RuntimeError("gpt-4o is down")
                return _make_completion("fallback ok")

            client.chat.completions.create.side_effect = side_effect
            agent._client = client

            out = agent.call("sys", "usr")
            assert out == "fallback ok"
            # model1 tried MAX_LLM_RETRIES times, then model2 succeeded on first try
            assert call_count["n"] == MAX_LLM_RETRIES + 1

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(BaseAgent, "_enrich_system_prompt", side_effect=lambda s: s)
    @patch("app.domains.ai.llm_trace.log_llm_call")
    @patch("time.sleep")
    def test_all_models_fail_raises(self, mock_sleep, mock_trace, _mock_enrich):
        openai_settings = SimpleNamespace(**vars(_FAKE_SETTINGS))
        openai_settings.ai_provider = "openai"
        with patch("app.domains.agents.banking_team.base_agent.settings", openai_settings):
            agent = _new_agent(model="gpt-4o", model_fallback=["gpt-4o-mini"])
            client = MagicMock()
            client.chat.completions.create.side_effect = RuntimeError("all dead")
            agent._client = client

            with pytest.raises(RuntimeError, match="all dead"):
                agent.call("sys", "usr")

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(BaseAgent, "_enrich_system_prompt", side_effect=lambda s: s)
    @patch("app.domains.ai.llm_trace.log_llm_call")
    def test_json_mode_appends_instruction_for_ollama(self, mock_trace, _mock_enrich):
        agent = _new_agent(model="mistral:latest")
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion('{"a":1}')
        agent._client = client

        agent.call("sys", "usr", json_mode=True)
        call_kwargs = client.chat.completions.create.call_args
        user_msg = call_kwargs.kwargs["messages"][-1]["content"]
        assert "JSON" in user_msg

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    @patch.object(BaseAgent, "_enrich_system_prompt", side_effect=lambda s: s)
    @patch("app.domains.ai.llm_trace.log_llm_call")
    def test_extra_messages_included(self, mock_trace, _mock_enrich):
        agent = _new_agent(model="mistral:latest")
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion("ok")
        agent._client = client

        extra = [{"role": "assistant", "content": "prior response"}]
        agent.call("sys", "usr", extra_messages=extra)
        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        # system, extra[0], user
        assert len(messages) == 3
        assert messages[1]["role"] == "assistant"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. call_json() — JSON parse paths
# ═══════════════════════════════════════════════════════════════════════════════


class TestCallJson:
    def _agent_returning(self, raw_text: str):
        """Helper: build an agent whose call() returns raw_text."""
        agent = _new_agent(model="mistral:latest")
        agent.call = MagicMock(return_value=raw_text)
        agent._trace_json_parse = MagicMock()
        return agent

    def test_valid_json_direct_parse(self):
        agent = self._agent_returning('{"key": "value"}')
        result = agent.call_json("sys", "usr")
        assert result == {"key": "value"}

    def test_markdown_code_block_cleanup(self):
        raw = '```json\n{"key": "value"}\n```'
        agent = self._agent_returning(raw)
        result = agent.call_json("sys", "usr")
        assert result == {"key": "value"}

    def test_markdown_block_with_language_tag(self):
        raw = '```json\n{"a": 1, "b": 2}\n```\n'
        agent = self._agent_returning(raw)
        result = agent.call_json("sys", "usr")
        assert result == {"a": 1, "b": 2}

    def test_nested_json_extraction(self):
        raw = 'Some text before {"nested": {"inner": true}} and after'
        agent = self._agent_returning(raw)
        result = agent.call_json("sys", "usr")
        assert result == {"nested": {"inner": True}}

    def test_array_extraction_wrapped(self):
        # Use an array of primitives so _extract_json_object won't match first
        raw = 'prefix [1, 2, 3] suffix'
        agent = self._agent_returning(raw)
        result = agent.call_json("sys", "usr")
        assert result == {"items": [1, 2, 3]}

    def test_parse_error_fallback(self):
        raw = "This is not JSON at all"
        agent = self._agent_returning(raw)
        result = agent.call_json("sys", "usr")
        assert result["parse_error"] is True
        assert "raw" in result

    def test_empty_object(self):
        agent = self._agent_returning("{}")
        result = agent.call_json("sys", "usr")
        assert result == {}

    def test_complex_nested_with_escaped_quotes(self):
        obj = {"key": 'value with "escaped" quotes', "num": 42}
        raw = f"Here is the output: {json.dumps(obj)}"
        agent = self._agent_returning(raw)
        result = agent.call_json("sys", "usr")
        assert result["key"] == 'value with "escaped" quotes'
        assert result["num"] == 42

    def test_call_json_passes_extra_messages(self):
        agent = _new_agent(model="mistral:latest")
        agent.call = MagicMock(return_value='{"ok": true}')
        agent._trace_json_parse = MagicMock()

        extra = [{"role": "user", "content": "extra"}]
        agent.call_json("sys", "usr", extra_messages=extra)
        agent.call.assert_called_once_with(
            "sys", "usr", json_mode=True, extra_messages=extra
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. _extract_json_object
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractJsonObject:
    def test_simple_object(self):
        assert BaseAgent._extract_json_object('{"a": 1}') == {"a": 1}

    def test_nested_braces(self):
        text = '{"outer": {"inner": {"deep": true}}}'
        assert BaseAgent._extract_json_object(text) == {
            "outer": {"inner": {"deep": True}}
        }

    def test_escaped_quotes_in_value(self):
        text = r'{"msg": "He said \"hello\" to me"}'
        result = BaseAgent._extract_json_object(text)
        assert result is not None
        assert "hello" in result["msg"]

    def test_no_braces(self):
        assert BaseAgent._extract_json_object("no json here") is None

    def test_malformed_json(self):
        assert BaseAgent._extract_json_object("{not valid json}") is None

    def test_prefix_text(self):
        text = 'Explanation: {"result": 42}'
        assert BaseAgent._extract_json_object(text) == {"result": 42}

    def test_multiple_objects_takes_first(self):
        text = '{"first": 1} {"second": 2}'
        result = BaseAgent._extract_json_object(text)
        assert result == {"first": 1}

    def test_string_with_braces_inside(self):
        text = '{"code": "function() { return {}; }"}'
        result = BaseAgent._extract_json_object(text)
        assert result is not None
        assert "function" in result["code"]


# ═══════════════════════════════════════════════════════════════════════════════
# 9. _extract_json_array
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractJsonArray:
    def test_valid_array(self):
        assert BaseAgent._extract_json_array('[1, 2, 3]') == [1, 2, 3]

    def test_array_of_objects(self):
        text = '[{"a": 1}, {"b": 2}]'
        result = BaseAgent._extract_json_array(text)
        assert result == [{"a": 1}, {"b": 2}]

    def test_no_array(self):
        assert BaseAgent._extract_json_array("no array here") is None

    def test_malformed_array(self):
        assert BaseAgent._extract_json_array("[1, 2,") is None

    def test_embedded_array(self):
        text = 'Result: [{"x": 1}] done'
        result = BaseAgent._extract_json_array(text)
        assert result == [{"x": 1}]

    def test_non_list_json_returns_none(self):
        """If the text between [ ] parses as non-list, returns None."""
        # This case is unlikely, but the code checks isinstance(result, list)
        assert BaseAgent._extract_json_array("not [valid") is None


# ═══════════════════════════════════════════════════════════════════════════════
# 10. safe_run()
# ═══════════════════════════════════════════════════════════════════════════════


class TestSafeRun:
    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_catches_exception(self):
        agent = _new_agent()
        agent.run = MagicMock(side_effect=ValueError("boom"))
        result = agent.safe_run({})
        assert result.success is False
        assert "boom" in result.error
        assert result.agent_name == "BaseAgent"

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_returns_successful_result(self):
        agent = _new_agent()
        expected = AgentResult(agent_name="BaseAgent", success=True, data={"ok": True})
        agent.run = MagicMock(return_value=expected)
        result = agent.safe_run({})
        assert result.success is True
        assert result.data == {"ok": True}

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_duration_ms_is_set(self):
        agent = _new_agent()
        agent.run = MagicMock(
            return_value=AgentResult(agent_name="BaseAgent", success=True)
        )
        result = agent.safe_run({})
        assert result.duration_ms >= 0

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_duration_ms_on_failure(self):
        agent = _new_agent()
        agent.run = MagicMock(side_effect=RuntimeError("fail"))
        result = agent.safe_run({})
        assert result.duration_ms >= 0
        assert result.success is False


# ═══════════════════════════════════════════════════════════════════════════════
# 11. learn()
# ═══════════════════════════════════════════════════════════════════════════════


class TestLearn:
    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_learn_calls_knowledge_store(self):
        with patch("app.domains.ai.knowledge_store.KnowledgeStore") as MockKS:
            store = MockKS.return_value
            agent = _new_agent()
            agent.learn("some insight", metadata={"key": "val"})
            store.ingest.assert_called_once()
            call_kwargs = store.ingest.call_args.kwargs
            assert call_kwargs["text"] == "some insight"
            assert call_kwargs["source"] == "insight"
            assert call_kwargs["metadata"]["agent"] == "BaseAgent"
            assert call_kwargs["metadata"]["key"] == "val"

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_learn_suppresses_exceptions(self):
        with patch(
            "app.domains.ai.knowledge_store.KnowledgeStore",
            side_effect=RuntimeError("DB down"),
        ):
            agent = _new_agent()
            # Should not raise
            agent.learn("test")


# ═══════════════════════════════════════════════════════════════════════════════
# 12. get_project_context() — caching + TTL
# ═══════════════════════════════════════════════════════════════════════════════


class TestProjectContext:
    def _reset_cache(self):
        import app.domains.agents.banking_team.base_agent as mod
        mod._project_context_cache = None
        mod._project_context_ts = 0.0

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_caching_returns_same_object(self):
        self._reset_cache()
        # Mock both KnowledgeStore and ProjectScanner to avoid real deps
        with (
            patch("app.domains.ai.knowledge_store.KnowledgeStore") as MockKS,
            patch(
                "app.domains.agents.banking_team.project_scanner.ProjectScannerAgent"
            ) as MockScanner,
        ):
            MockKS.return_value.retrieve.return_value = []
            mock_scanner = MockScanner.return_value
            # Scanner must return non-empty data so cache dict is truthy
            mock_scanner.safe_run.return_value = AgentResult(
                agent_name="scanner",
                success=True,
                data={"description": "Test project", "db_schema": "users(id)"},
            )

            ctx1 = BaseAgent.get_project_context()
            ctx2 = BaseAgent.get_project_context()
            assert ctx1 is ctx2  # same object from cache

        self._reset_cache()

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_ttl_expiry_regenerates(self):
        self._reset_cache()
        import app.domains.agents.banking_team.base_agent as mod

        with (
            patch("app.domains.ai.knowledge_store.KnowledgeStore") as MockKS,
            patch(
                "app.domains.agents.banking_team.project_scanner.ProjectScannerAgent"
            ) as MockScanner,
        ):
            MockKS.return_value.retrieve.return_value = []
            mock_scanner = MockScanner.return_value
            mock_scanner.safe_run.return_value = AgentResult(
                agent_name="scanner",
                success=True,
                data={"description": "Test project", "db_schema": "users(id)"},
            )

            ctx1 = BaseAgent.get_project_context()
            # Simulate TTL expiry
            mod._project_context_ts = time.time() - _PROJECT_CTX_TTL - 10
            ctx2 = BaseAgent.get_project_context()
            # After TTL expiry, a fresh dict is built
            assert ctx2 is not ctx1

        self._reset_cache()

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_reset_clears_cache(self):
        import app.domains.agents.banking_team.base_agent as mod
        mod._project_context_cache = {"cached": True}
        mod._project_context_ts = time.time()
        BaseAgent.reset_project_context()
        assert mod._project_context_cache is None
        assert mod._project_context_ts == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Constants sanity checks
# ═══════════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_max_retries_value(self):
        assert MAX_LLM_RETRIES == 2

    def test_backoff_base(self):
        assert RETRY_BACKOFF_BASE == 1.5

    def test_ctx_ttl(self):
        assert _PROJECT_CTX_TTL == 600

    def test_default_ctx_limit(self):
        assert _DEFAULT_CTX_LIMIT == 10000

    def test_known_models_in_limits(self):
        assert "gpt-4o" in _MODEL_CTX_LIMITS
        assert "qwen2.5:32b" in _MODEL_CTX_LIMITS
        assert "mistral:latest" in _MODEL_CTX_LIMITS


# ═══════════════════════════════════════════════════════════════════════════════
# 14. _get_client
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetClient:
    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_ollama_client_uses_ollama_url(self):
        with patch("openai.OpenAI") as MockOpenAI:
            agent = _ConcreteAgent()
            agent._get_client()
            MockOpenAI.assert_called_once_with(
                api_key="ollama",
                base_url="http://localhost:11434/v1",
            )

    def test_openai_client_uses_openai_url(self):
        openai_settings = SimpleNamespace(**vars(_FAKE_SETTINGS))
        openai_settings.ai_provider = "openai"
        import app.domains.ai.service as _svc
        with (
            patch("app.domains.agents.banking_team.base_agent.settings", openai_settings),
            # service._get_openai_client() reads its own module-level settings
            patch("app.domains.ai.service.settings", openai_settings),
            # reset singleton so a fresh OpenAI() call is made inside the with block
            patch.object(_svc, "_openai_client", None),
            patch("openai.OpenAI") as MockOpenAI,
        ):
            agent = _ConcreteAgent()
            agent._get_client()
            MockOpenAI.assert_called_once_with(
                api_key="sk-test",
                base_url="https://api.openai.com/v1",
            )

    @patch("app.domains.agents.banking_team.base_agent.settings", _FAKE_SETTINGS)
    def test_client_cached(self):
        import app.domains.ai.service as _svc
        with patch("openai.OpenAI") as MockOpenAI, \
             patch.object(_svc, "_ollama_client", None):
            agent = _ConcreteAgent()
            c1 = agent._get_client()
            c2 = agent._get_client()
            assert c1 is c2
            MockOpenAI.assert_called_once()

    def test_base_agent_is_abstract(self):
        """BaseAgent doğrudan instantiate edilemez — @abstractmethod run() zorunlu."""
        import pytest
        with pytest.raises(TypeError, match="abstract"):
            BaseAgent()  # type: ignore[abstract]
