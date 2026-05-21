"""LLM Stepper birim testleri — heuristic fallback davranışı."""
from __future__ import annotations

import pytest

from app.domains.mobile.llm_stepper import (
    _heuristic_stepper,
    _parse_llm_json,
    generate_steps,
)


pytestmark = pytest.mark.P1


class TestHeuristicStepper:
    def test_always_starts_with_launch(self):
        steps = _heuristic_stepper("test", "android")
        assert steps[0].action == "launch"

    def test_login_flow_generates_find_and_tap(self):
        prompt = "Giriş yap butonuna bas, email alanına test@bgts.ai yaz, devam et"
        steps = _heuristic_stepper(prompt, "android")
        actions = [s.action for s in steps]
        assert "find" in actions
        assert "tap" in actions
        assert "sendKeys" in actions

    def test_email_extraction_from_prompt(self):
        steps = _heuristic_stepper("email alanına ali@example.com yaz", "android")
        send_keys = [s for s in steps if s.action == "sendKeys"]
        assert any(s.text == "ali@example.com" for s in send_keys)

    def test_fallback_email_when_no_match(self):
        steps = _heuristic_stepper("email alanını doldur", "android")
        send_keys = [s for s in steps if s.action == "sendKeys"]
        assert any("@" in (s.text or "") for s in send_keys)

    def test_password_extraction_from_quoted(self):
        steps = _heuristic_stepper("şifre alanına 'MySecret99' yaz", "android")
        send_keys = [s for s in steps if s.action == "sendKeys"]
        assert any(s.text == "MySecret99" for s in send_keys)

    def test_search_with_quoted_term(self):
        steps = _heuristic_stepper("arama kutusuna 'kahve' yaz", "android")
        send_keys = [s for s in steps if s.action == "sendKeys"]
        assert any(s.text == "kahve" for s in send_keys)

    def test_cart_flow_ends_with_verify(self):
        steps = _heuristic_stepper("ürünü sepete ekle", "android")
        assert any(s.action == "verifyVisible" for s in steps)
        assert any(s.value == "add_to_cart" for s in steps if s.by)

    def test_logout_flow_complete(self):
        steps = _heuristic_stepper("çıkış yap", "android")
        values = [s.value for s in steps if s.value]
        assert "logout_button" in values
        assert "confirm_yes" in values
        assert "login_screen" in values

    def test_home_assertion_when_dogrula(self):
        steps = _heuristic_stepper("ana sayfanın yüklendiğini doğrula", "android")
        verify = [s for s in steps if s.action == "verifyVisible"]
        assert any(s.value == "home_screen" for s in verify)

    def test_empty_prompt_has_sensible_fallback(self):
        steps = _heuristic_stepper("xyz random metin", "android")
        assert len(steps) >= 2  # launch + at least one fallback step
        assert any(s.action == "verifyVisible" for s in steps)

    def test_case_insensitive_matching(self):
        steps = _heuristic_stepper("GİRİŞ YAP butonuna bas", "android")
        assert any(s.value == "login_button" for s in steps if s.value)


class TestJsonParsing:
    def test_plain_json_array(self):
        raw = '[{"action":"launch"},{"action":"tap"}]'
        parsed = _parse_llm_json(raw)
        assert parsed is not None
        assert len(parsed) == 2

    def test_with_markdown_fence(self):
        raw = '```json\n[{"action":"launch"}]\n```'
        parsed = _parse_llm_json(raw)
        assert parsed == [{"action": "launch"}]

    def test_with_surrounding_text(self):
        raw = 'İşte adımlar:\n[{"action":"launch"}]\nUmarım yardımcı olur.'
        parsed = _parse_llm_json(raw)
        assert parsed == [{"action": "launch"}]

    def test_malformed_returns_none(self):
        assert _parse_llm_json("bu geçerli bir JSON değil") is None

    def test_object_instead_of_array_returns_none(self):
        assert _parse_llm_json('{"action":"launch"}') is None


class TestGenerateSteps:
    def test_returns_fallback_when_gateway_unavailable(self, monkeypatch):
        """AI Gateway kapalıyken heuristic fallback kullanılır."""
        # Gateway zaten çalışmıyor (dev ortamı), model='heuristic-tr' beklenir
        resp = generate_steps("Uygulamayı aç, giriş yap", "android")
        assert resp.fallback_used is True
        assert resp.model == "heuristic-tr"
        assert len(resp.steps) >= 2

    def test_response_has_steps(self):
        resp = generate_steps("Uygulamayı aç ve doğrula", "ios")
        assert len(resp.steps) > 0
        assert resp.steps[0].action == "launch"

    def test_gateway_success_is_used_when_available(self, monkeypatch):
        """Gateway başarılı olursa onun çıktısı kullanılır."""

        def fake_gateway_complete(**kwargs):  # type: ignore[no-untyped-def]
            return '[{"action":"launch"},{"action":"verifyVisible","by":"accessibilityId","value":"ok"}]'

        import app.domains.mobile.llm_stepper as stepper_mod
        from app.domains.ai import gateway_client

        monkeypatch.setattr(gateway_client, "gateway_complete", fake_gateway_complete)
        # Cached import in stepper: reload not needed because it imports lazily inside function

        resp = stepper_mod.generate_steps("test", "android")
        assert resp.fallback_used is False
        assert resp.model == "ai-gateway"
        assert len(resp.steps) == 2
