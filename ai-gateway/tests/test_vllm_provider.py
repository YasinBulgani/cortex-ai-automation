"""
VLLMProvider — Unit testler

httpx.MockTransport ile gerçek ağ çağrısı yapmadan OpenAI-uyumlu vLLM
sunucu davranışını simüle eder.

Çalıştırmak:
    cd ai-gateway && pytest tests/test_vllm_provider.py -v
"""
from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from app.core.config import settings
from app.core.models import AIRequest, Message, TaskType
from app.providers.vllm_provider import VLLMProvider


# ═══════════════════════════════════════════════════════════════════════════
# Yardımcılar
# ═══════════════════════════════════════════════════════════════════════════


def _make_request(
    content: str = "merhaba",
    *,
    task_type: TaskType = TaskType.CHAT,
    model_override: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> AIRequest:
    return AIRequest(
        task_type=task_type,
        messages=[Message(role="user", content=content)],
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode,
        model_override=model_override,
    )


def _install_mock_transport(monkeypatch, handler):
    """Tüm httpx.AsyncClient çağrılarını MockTransport üzerinden yönlendirir."""
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


# ═══════════════════════════════════════════════════════════════════════════
# is_available()
# ═══════════════════════════════════════════════════════════════════════════


class TestIsAvailable:
    """Flag davranışı ve /v1/models eşleşme mantığı."""

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(self, monkeypatch):
        """VLLM_ENABLED=False iken hiçbir ağ çağrısı yapılmaz ve False döner."""
        monkeypatch.setattr(settings, "VLLM_ENABLED", False)

        called = {"hit": False}

        def handler(req: httpx.Request) -> httpx.Response:
            called["hit"] = True
            return httpx.Response(200, json={"data": []})

        _install_mock_transport(monkeypatch, handler)

        provider = VLLMProvider()
        assert await provider.is_available() is False
        assert called["hit"] is False, "Flag kapalıyken ağ çağrısı yapılmamalı"

    @pytest.mark.asyncio
    async def test_returns_true_when_target_model_loaded(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)
        monkeypatch.setattr(
            settings, "VLLM_BASE_URL", "http://vllm-test.local:8000/v1"
        )
        monkeypatch.setattr(
            settings, "VLLM_MODEL", "Qwen/Qwen2.5-72B-Instruct"
        )

        def handler(req: httpx.Request) -> httpx.Response:
            assert req.url.path.endswith("/v1/models")
            assert req.method == "GET"
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "Qwen/Qwen2.5-72B-Instruct", "object": "model"},
                        {"id": "another-model", "object": "model"},
                    ]
                },
            )

        _install_mock_transport(monkeypatch, handler)

        provider = VLLMProvider()
        assert await provider.is_available() is True

    @pytest.mark.asyncio
    async def test_prefix_match_accepts_quantized_variant(self, monkeypatch):
        """Yüklü modeller AWQ / GPTQ son eki taşısa bile eşleşir."""
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)
        monkeypatch.setattr(settings, "VLLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"data": [{"id": "Qwen/Qwen2.5-72B-Instruct-AWQ"}]},
            )

        _install_mock_transport(monkeypatch, handler)

        assert await VLLMProvider().is_available() is True

    @pytest.mark.asyncio
    async def test_prefix_match_rejects_false_positive(self, monkeypatch):
        """Separator kontrolü: 'Qwen2' yüklüyken 'Qwen2.5-72B' eşleşmemeli."""
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)
        monkeypatch.setattr(settings, "VLLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

        def handler(req: httpx.Request) -> httpx.Response:
            # 'Qwen2' hedef 'Qwen2.5-72B-Instruct' ile eşleşmemeli —
            # nokta separator listesinde yok.
            return httpx.Response(
                200,
                json={"data": [{"id": "Qwen/Qwen2"}]},
            )

        _install_mock_transport(monkeypatch, handler)

        assert await VLLMProvider().is_available() is False

    @pytest.mark.asyncio
    async def test_returns_false_when_model_not_loaded(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)
        monkeypatch.setattr(settings, "VLLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"data": [{"id": "meta-llama/Llama-3.2-3B-Instruct"}]}
            )

        _install_mock_transport(monkeypatch, handler)

        assert await VLLMProvider().is_available() is False

    @pytest.mark.asyncio
    async def test_returns_false_on_http_error(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)

        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        _install_mock_transport(monkeypatch, handler)
        assert await VLLMProvider().is_available() is False

    @pytest.mark.asyncio
    async def test_returns_false_on_network_error(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)

        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        _install_mock_transport(monkeypatch, handler)
        assert await VLLMProvider().is_available() is False

    @pytest.mark.asyncio
    async def test_returns_false_when_data_list_empty(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)

        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": []})

        _install_mock_transport(monkeypatch, handler)
        assert await VLLMProvider().is_available() is False

    @pytest.mark.asyncio
    async def test_sends_api_key_header_when_set(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)
        monkeypatch.setattr(settings, "VLLM_API_KEY", "sk-vllm-test-token")
        monkeypatch.setattr(settings, "VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")

        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["auth"] = req.headers.get("Authorization")
            return httpx.Response(
                200, json={"data": [{"id": "Qwen/Qwen2.5-7B-Instruct"}]}
            )

        _install_mock_transport(monkeypatch, handler)
        await VLLMProvider().is_available()

        assert captured["auth"] == "Bearer sk-vllm-test-token"


# ═══════════════════════════════════════════════════════════════════════════
# complete()
# ═══════════════════════════════════════════════════════════════════════════


class TestComplete:
    """OpenAI-uyumlu /v1/chat/completions payload ve yanıt işleme."""

    @pytest.mark.asyncio
    async def test_happy_path_returns_content(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_ENABLED", True)
        monkeypatch.setattr(settings, "VLLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["method"] = req.method
            captured["body"] = json.loads(req.content.decode())
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"role": "assistant", "content": "yanıt-metni"}}
                    ]
                },
            )

        _install_mock_transport(monkeypatch, handler)

        provider = VLLMProvider()
        result = await provider.complete(_make_request("selam"))

        assert result == "yanıt-metni"
        assert captured["path"].endswith("/v1/chat/completions")
        assert captured["method"] == "POST"
        assert captured["body"]["model"] == "Qwen/Qwen2.5-72B-Instruct"
        assert captured["body"]["stream"] is False
        assert captured["body"]["temperature"] == 0.3
        assert captured["body"]["max_tokens"] == 500
        assert captured["body"]["messages"] == [
            {"role": "user", "content": "selam"}
        ]
        assert "response_format" not in captured["body"]

    @pytest.mark.asyncio
    async def test_honors_model_override(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(req.content.decode())
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )

        _install_mock_transport(monkeypatch, handler)

        provider = VLLMProvider()
        await provider.complete(
            _make_request(model_override="Qwen/Qwen2.5-Coder-32B-Instruct")
        )

        assert captured["body"]["model"] == "Qwen/Qwen2.5-Coder-32B-Instruct"

    @pytest.mark.asyncio
    async def test_json_mode_adds_response_format(self, monkeypatch):
        monkeypatch.setattr(settings, "VLLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(req.content.decode())
            return httpx.Response(
                200, json={"choices": [{"message": {"content": "{}"}}]}
            )

        _install_mock_transport(monkeypatch, handler)

        req = _make_request(json_mode=True, task_type=TaskType.ANALYZE_DOCUMENT)
        await VLLMProvider().complete(req)

        assert captured["body"]["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self, monkeypatch):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="overloaded")

        _install_mock_transport(monkeypatch, handler)

        with pytest.raises(httpx.HTTPStatusError):
            await VLLMProvider().complete(_make_request())

    @pytest.mark.asyncio
    async def test_raises_on_malformed_response(self, monkeypatch):
        """Yanıtta 'choices' yoksa ValueError fırlatmalı."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"unexpected": "shape"})

        _install_mock_transport(monkeypatch, handler)

        with pytest.raises(ValueError, match="beklenen formatta değil"):
            await VLLMProvider().complete(_make_request())

    @pytest.mark.asyncio
    async def test_raises_on_empty_content(self, monkeypatch):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"choices": [{"message": {"content": ""}}]}
            )

        _install_mock_transport(monkeypatch, handler)

        with pytest.raises(ValueError, match="boş içerik"):
            await VLLMProvider().complete(_make_request())


# ═══════════════════════════════════════════════════════════════════════════
# safe_complete() — base class entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════


class TestSafeComplete:
    @pytest.mark.asyncio
    async def test_success_path_wraps_content(self, monkeypatch):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"choices": [{"message": {"content": "ok"}}]}
            )

        _install_mock_transport(monkeypatch, handler)

        content, attempt = await VLLMProvider().safe_complete(_make_request())
        assert content == "ok"
        assert attempt.success is True
        assert attempt.provider == "vllm"
        assert attempt.error is None
        assert attempt.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_error_path_captures_message(self, monkeypatch):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        _install_mock_transport(monkeypatch, handler)

        content, attempt = await VLLMProvider().safe_complete(_make_request())
        assert content is None
        assert attempt.success is False
        assert attempt.provider == "vllm"
        assert attempt.error is not None
        assert len(attempt.error) <= 200


# ═══════════════════════════════════════════════════════════════════════════
# PROVIDER_ORDER — router entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════


class TestProviderOrder:
    """VLLM_ENABLED bayrağının zincir sırasına etkisi."""

    def test_vllm_disabled_by_default(self):
        """Varsayılan ayarlarla vLLM fallback zincirinde olmamalı."""
        # settings modülü singleton — gerçek config'i kontrol et.
        # Diğer testler monkeypatch ile değiştirebileceği için burada
        # geçici olarak default değerlere dön.
        with patch.multiple(
            settings,
            VLLM_ENABLED=False,
            GROQ_ENABLED=True,
            GEMINI_ENABLED=True,
            OLLAMA_ENABLED=True,
            AI_LOCAL_ONLY=False,
            AI_PROVIDER="auto",
        ):
            order = settings.PROVIDER_ORDER
        assert "vllm" not in order
        assert order[0] == "groq"  # bulut fallback zinciri

    def test_vllm_enabled_auto_mode_puts_vllm_first(self):
        with patch.multiple(
            settings,
            VLLM_ENABLED=True,
            GROQ_ENABLED=True,
            GEMINI_ENABLED=True,
            OLLAMA_ENABLED=True,
            AI_LOCAL_ONLY=False,
            AI_PROVIDER="auto",
        ):
            order = settings.PROVIDER_ORDER
        assert order[0] == "vllm"
        assert "groq" in order
        assert "g4f" not in order

    def test_ai_provider_vllm_forces_vllm_first(self):
        with patch.multiple(
            settings,
            VLLM_ENABLED=True,
            OLLAMA_ENABLED=True,
            GROQ_ENABLED=True,
            GEMINI_ENABLED=False,
            AI_LOCAL_ONLY=False,
            AI_PROVIDER="vllm",
        ):
            order = settings.PROVIDER_ORDER
        assert order[0] == "vllm"
        assert "gemini" not in order  # disabled

    def test_ai_provider_ollama_keeps_ollama_first_even_with_vllm(self):
        """AI_PROVIDER=ollama kullanıcının bilinçli seçimi — vLLM ikinci sıraya düşer."""
        with patch.multiple(
            settings,
            VLLM_ENABLED=True,
            OLLAMA_ENABLED=True,
            GROQ_ENABLED=False,
            GEMINI_ENABLED=False,
            AI_LOCAL_ONLY=True,
            AI_PROVIDER="ollama",
        ):
            order = settings.PROVIDER_ORDER
        assert order[0] == "ollama"
        assert order[1] == "vllm"

    def test_all_disabled_returns_empty(self):
        with patch.multiple(
            settings,
            VLLM_ENABLED=False,
            GROQ_ENABLED=False,
            GEMINI_ENABLED=False,
            OLLAMA_ENABLED=False,
            AI_LOCAL_ONLY=False,
            AI_PROVIDER="auto",
        ):
            assert settings.PROVIDER_ORDER == []


# ═══════════════════════════════════════════════════════════════════════════
# Router — VLLMProvider registry'de
# ═══════════════════════════════════════════════════════════════════════════


class TestRouterRegistration:
    def test_router_registers_vllm_provider(self):
        from app.core.router import ai_router

        assert "vllm" in ai_router._providers
        assert ai_router._providers["vllm"].name == "vllm"
        assert isinstance(ai_router._providers["vllm"], VLLMProvider)
