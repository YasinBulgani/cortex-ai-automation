"""AI-powered endpoint'ler için kontrat/smoke testleri.

Kapsam:
  * `/api/v1/ai/nl-test/generate` — Doğal dil → test case üretim şekli
  * `/api/v1/ai/nl-test/validate` — Kod syntax doğrulama sözleşmesi
  * `/api/v1/automation-suite/health` — engine proxy sağlık kontrolü

Bu modül daha önce api-tests kapsamında HİÇ olmayan AI/otomasyon yüzeylerini
kısmen örter. AI anahtarı olmayan ortamlarda `ai` marker'ı ile bu testler
skip'lenir (marker'lar `pytest.ini`'de).
"""

from __future__ import annotations

import pytest


# ─── Yardımcı: yanıt "şekli" doğrula, içeriğe takılma ───
# AI tarafından üretilen metin deterministik değildir; bu yüzden
# kontrat testleri yalnızca response bize söz verilen alanları döndürdü mü
# bakar — içerik kalite değerlendirmesi ayrı eval suite'te yapılır.


@pytest.mark.ai
@pytest.mark.smoke
class TestNLTestGenerateContract:
    """`/api/v1/ai/nl-test/generate` sözleşmesi."""

    def test_minimum_payload_shape(self, api):
        """Kısa açıklama ile çağrıda 200 + beklenen top-level alanlar."""
        resp = api.post(
            "/api/v1/ai/nl-test/generate",
            json={
                "text": "Kullanıcı login olmalı, 200 dönmeli",
                "output_format": "api_test",
            },
        )
        # LLM anahtarı yok/geçersiz ise 5xx dönebilir — o zaman skip.
        if resp.status_code >= 500:
            pytest.skip(
                f"LLM gateway 5xx dönüyor ({resp.status_code}). "
                "OPENAI_API_KEY/ANTHROPIC_API_KEY eksik olabilir."
            )
        assert resp.status_code == 200, resp.text

        body = resp.json()
        # NLTestResponse şeması en az bu üst düzey alanları içermeli.
        # Spesifik alan isimleri şemayla uyumlu olmalı (backend/app/domains/ai/router.py).
        top_level = set(body.keys())
        # `test_cases` veya `code` alanı çıktı formatına göre mutlaka olmalı.
        assert any(
            k in top_level for k in ("test_cases", "code", "gherkin", "output", "generated")
        ), (
            f"NL-test response'u beklenen çıktı alanlarından hiçbirini "
            f"içermiyor: {top_level}"
        )

    @pytest.mark.negative
    def test_invalid_output_format_rejected(self, api):
        """Desteklenmeyen `output_format` için 422 veya 400."""
        resp = api.post(
            "/api/v1/ai/nl-test/generate",
            json={"text": "deneme", "output_format": "cobol"},
        )
        # 422 (Pydantic) veya 400 (router validation) — her ikisi de kabul.
        assert resp.status_code in (400, 422), resp.text

    @pytest.mark.negative
    def test_empty_text_rejected(self, api):
        """Min_length=3 kuralı Pydantic tarafında uygulanıyor mu?"""
        resp = api.post(
            "/api/v1/ai/nl-test/generate",
            json={"text": "", "output_format": "api_test"},
        )
        assert resp.status_code == 422


@pytest.mark.ai
@pytest.mark.smoke
class TestNLTestValidateContract:
    """`/api/v1/ai/nl-test/validate` — LLM-dışı syntax check."""

    def test_valid_python_passes(self, api):
        resp = api.post(
            "/api/v1/ai/nl-test/validate",
            json={
                "code": "def test_ok():\n    assert 1 == 1\n",
                "language": "python",
            },
        )
        if resp.status_code == 404:
            pytest.skip("/nl-test/validate endpoint'i bu sürümde yok")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Validation response'u en azından boolean "valid" veya benzeri bir
        # gösterge taşımalı.
        assert any(k in body for k in ("valid", "ok", "is_valid", "syntax_ok"))

    def test_invalid_python_fails_gracefully(self, api):
        """Bozuk syntax → 200 + valid:false. Endpoint crash'lememeli."""
        resp = api.post(
            "/api/v1/ai/nl-test/validate",
            json={
                "code": "def broken(\n    this is not python\n",
                "language": "python",
            },
        )
        if resp.status_code == 404:
            pytest.skip("/nl-test/validate endpoint'i bu sürümde yok")
        # Syntax hatası 200 ile (valid=false) ya da 400 ile dönebilir;
        # kabul edilen davranış aralığı bu ikisi.
        assert resp.status_code in (200, 400), resp.text


@pytest.mark.smoke
class TestAutomationSuiteHealth:
    """`/api/v1/automation-suite/health` — engine proxy layer."""

    def test_health_reachable(self, api):
        resp = api.get("/api/v1/automation-suite/health")
        if resp.status_code == 404:
            pytest.skip("automation-suite endpoint'i henüz route'lu değil")
        # Engine down ise 503 kabul; yüzey en azından cevap vermeli.
        assert resp.status_code in (200, 503), resp.text
        body = resp.json()
        # En az bir sağlık göstergesi alanı olmalı.
        assert any(k in body for k in ("status", "engine", "ok", "healthy"))
