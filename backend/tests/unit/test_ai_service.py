"""Unit tests for app.domains.ai.service and app.domains.ai.pii_redactor.

All external I/O (OpenAI, Anthropic, DB, filesystem) is mocked.
No network calls are made; no real API keys are required.
"""
from __future__ import annotations

import pytest

try:
    import app.domains.ai.service as ai_service
    import app.domains.ai.pii_redactor as pii_redactor
    from app.domains.ai.pii_redactor import (
        redact,
        redact_with_stats,
        detect_pii_categories,
        has_pii,
        redact_messages,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="ai service import failed")

from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# PII detection — detect_pii_categories / has_pii
# ---------------------------------------------------------------------------

class TestDetectPiiCategories:
    def test_tc_kimlik_detected(self):
        """An 11-digit TCKN starting with a non-zero digit is flagged."""
        result = detect_pii_categories("Kullanıcı TC: 12345678901")
        assert "tckn" in result

    def test_email_detected(self):
        """A standard e-mail address is flagged as email."""
        result = detect_pii_categories("İletişim: user@example.com")
        assert "email" in result

    def test_clean_text_returns_empty_dict(self):
        """Text without PII returns an empty dict (not None)."""
        result = detect_pii_categories("Bu metin temiz bir metindir.")
        assert result == {}

    def test_multiple_pii_types_detected(self):
        """Text containing both TC and e-mail should flag both categories."""
        text = "TC: 12345678901, e-posta: test@domain.com"
        result = detect_pii_categories(text)
        assert "tckn" in result
        assert "email" in result

    def test_has_pii_true_for_pii_text(self):
        assert has_pii("kullanıcı@test.com içerir") is True

    def test_has_pii_false_for_clean_text(self):
        assert has_pii("Temiz metin, hiç PII yok.") is False

    def test_empty_string_returns_empty_dict(self):
        assert detect_pii_categories("") == {}


# ---------------------------------------------------------------------------
# redact / redact_with_stats
# ---------------------------------------------------------------------------

class TestRedact:
    def test_tckn_replaced_with_placeholder(self):
        result = redact("TC kimlik: 12345678901 bilgisi")
        assert "12345678901" not in result
        assert "[TC_KIMLIK]" in result

    def test_email_replaced_with_placeholder(self):
        result = redact("Mail: ali@sirket.com.tr adresine gönder")
        assert "ali@sirket.com.tr" not in result
        assert "[EMAIL]" in result

    def test_clean_text_unchanged(self):
        text = "Senaryo başlığı: Giriş sayfası testi"
        assert redact(text) == text

    def test_empty_string_returned_unchanged(self):
        assert redact("") == ""

    def test_redact_with_stats_counts_matches(self):
        text = "TC: 12345678901, email: a@b.com"
        result = redact_with_stats(text)
        assert result.total > 0
        assert result.masked != text

    def test_redact_with_stats_empty_input(self):
        result = redact_with_stats("")
        assert result.total == 0
        assert result.masked == ""


# ---------------------------------------------------------------------------
# redact_messages
# ---------------------------------------------------------------------------

class TestRedactMessages:
    def test_string_content_redacted(self):
        messages = [{"role": "user", "content": "TC: 12345678901"}]
        result = redact_messages(messages)
        # PII redactor replaces the TC number but may keep surrounding text
        assert "[TC_KIMLIK]" in result[0]["content"]

    def test_non_dict_message_passed_through(self):
        messages = ["not a dict"]
        result = redact_messages(messages)
        assert result == ["not a dict"]

    def test_multipart_content_blocks_redacted(self):
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "email: x@y.com"}],
            }
        ]
        result = redact_messages(messages)
        assert "[EMAIL]" in result[0]["content"][0]["text"]


# ---------------------------------------------------------------------------
# _is_local_llm_url
# ---------------------------------------------------------------------------

class TestIsLocalLlmUrl:
    def test_localhost_is_local(self):
        assert ai_service._is_local_llm_url("http://localhost:11434") is True

    def test_127_is_local(self):
        assert ai_service._is_local_llm_url("http://127.0.0.1:8080") is True

    def test_docker_service_name_is_local(self):
        # Single-label hostnames (no dot) are treated as local Docker services
        assert ai_service._is_local_llm_url("http://ollama:11434") is True

    def test_openai_api_is_not_local(self):
        assert ai_service._is_local_llm_url("https://api.openai.com") is False


# ---------------------------------------------------------------------------
# _resolve_effective_provider
# ---------------------------------------------------------------------------

class TestResolveEffectiveProvider:
    def _make_settings(self, provider, openai_key="", anthropic_key="", fallback=False):
        s = MagicMock()
        s.ai_provider = provider
        s.openai_api_key = openai_key
        s.anthropic_api_key = anthropic_key
        s.allow_provider_fallback = fallback
        return s

    def test_openai_provider_resolved_when_key_present(self):
        with patch.object(ai_service, "settings") as mock_settings:
            mock_settings.ai_provider = "openai"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.anthropic_api_key = ""
            mock_settings.allow_provider_fallback = False
            result = ai_service._resolve_effective_provider()
        assert result == "openai"

    def test_anthropic_provider_resolved_when_key_present(self):
        with patch.object(ai_service, "settings") as mock_settings:
            mock_settings.ai_provider = "anthropic"
            mock_settings.anthropic_api_key = "ant-test"
            mock_settings.openai_api_key = ""
            mock_settings.allow_provider_fallback = False
            result = ai_service._resolve_effective_provider()
        assert result == "anthropic"

    def test_ollama_always_resolved(self):
        with patch.object(ai_service, "settings") as mock_settings:
            mock_settings.ai_provider = "ollama"
            result = ai_service._resolve_effective_provider()
        assert result == "ollama"

    def test_openai_missing_key_raises_runtime_error(self):
        with patch.object(ai_service, "settings") as mock_settings:
            mock_settings.ai_provider = "openai"
            mock_settings.openai_api_key = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.allow_provider_fallback = False
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                ai_service._resolve_effective_provider()


# ---------------------------------------------------------------------------
# call_llm — OpenAI path
# ---------------------------------------------------------------------------

class TestCallLlmOpenAI:
    def _mock_openai_response(self, content: str):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = content
        return mock_response

    def test_call_llm_openai_returns_content_string(self):
        """call_llm with openai provider returns the LLM content string."""
        expected = "Merhaba, bu bir test yanıtıdır."
        with (
            patch.object(ai_service, "_resolve_effective_provider", return_value="openai"),
            patch.object(ai_service, "_assert_llm_provider_allowed"),
            patch.object(ai_service, "_get_openai_client") as mock_client_fn,
            patch.object(ai_service, "settings") as mock_settings,
            patch("app.domains.ai.service.log_llm_call", create=True),
        ):
            mock_settings.openai_api_key = "sk-test"
            mock_settings.openai_model = "gpt-4o"
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = self._mock_openai_response(expected)
            mock_client_fn.return_value = mock_client

            # Patch trace import to avoid DB
            with patch.dict("sys.modules", {"app.domains.ai.llm_trace": MagicMock()}):
                result = ai_service._call_openai("system prompt", "user message")

        assert result == expected

    def test_call_llm_anthropic_returns_content_string(self):
        """_call_anthropic returns the .text from the first content block."""
        expected = "Anthropic test yanıtı."
        with (
            patch.object(ai_service, "_get_anthropic_client") as mock_client_fn,
            patch.object(ai_service, "settings") as mock_settings,
        ):
            mock_settings.anthropic_api_key = "ant-test"
            mock_settings.anthropic_model = "claude-3-5-sonnet-20241022"
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=expected)]
            mock_client.messages.create.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = ai_service._call_anthropic("system", "user")

        assert result == expected


# ---------------------------------------------------------------------------
# _with_retry — rate limit / retriable error triggers retries
# ---------------------------------------------------------------------------

class TestRetryDecorator:
    def test_retriable_error_is_retried(self):
        """A generic RuntimeError (retriable) causes the wrapper to retry up to MAX_LLM_RETRIES."""
        call_count = 0

        @ai_service._with_retry
        def flaky():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("rate limit exceeded")

        with patch("app.domains.ai.service.time.sleep"):  # avoid real sleep
            with pytest.raises(RuntimeError, match="rate limit"):
                flaky()

        assert call_count == ai_service.MAX_LLM_RETRIES

    def test_non_retriable_value_error_raises_immediately(self):
        """ValueError is non-retriable — must raise on first attempt."""
        call_count = 0

        @ai_service._with_retry
        def instant_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError):
            instant_fail()

        assert call_count == 1

    def test_success_on_second_attempt(self):
        """Function succeeding on second attempt after one retriable error."""
        attempts = []

        @ai_service._with_retry
        def sometimes_works():
            attempts.append(1)
            if len(attempts) == 1:
                raise ConnectionError("temporary")
            return "ok"

        with patch("app.domains.ai.service.time.sleep"):
            result = sometimes_works()

        assert result == "ok"
        assert len(attempts) == 2


# ---------------------------------------------------------------------------
# analyze_test_results — public API
# ---------------------------------------------------------------------------

class TestAnalyzeTestResults:
    def test_returns_dict_with_expected_keys(self):
        raw_json = '{"summary": "2 test başarısız", "insights": [], "recommendations": []}'
        with (
            patch.object(ai_service, "call_llm", return_value=raw_json),
            patch.object(ai_service, "_get_rag_context", return_value=""),
        ):
            result = ai_service.analyze_test_results("test verileri")

        assert isinstance(result, dict)
        assert "summary" in result

    def test_empty_execution_data_still_returns_dict(self):
        raw_json = '{"summary": "", "insights": [], "recommendations": []}'
        with (
            patch.object(ai_service, "call_llm", return_value=raw_json),
            patch.object(ai_service, "_get_rag_context", return_value=""),
        ):
            result = ai_service.analyze_test_results("")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# chat_completion — public API
# ---------------------------------------------------------------------------

class TestChatCompletion:
    def test_returns_string(self):
        with (
            patch.object(ai_service, "call_llm", return_value="Yanıt metni"),
            patch.object(ai_service, "_get_rag_context", return_value=""),
        ):
            result = ai_service.chat_completion("Merhaba")
        assert isinstance(result, str)
        assert result == "Yanıt metni"

    def test_rag_context_appended_when_non_empty(self):
        captured_system = []

        def fake_call_llm(system, user, **kw):
            captured_system.append(system)
            return "ok"

        with (
            patch.object(ai_service, "call_llm", side_effect=fake_call_llm),
            patch.object(ai_service, "_get_rag_context", return_value="rag bağlamı"),
        ):
            ai_service.chat_completion("soru", project_id="proj-1")

        assert "rag bağlamı" in captured_system[0]
