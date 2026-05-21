"""Türkçe hata mesajı kataloğu — UX-F2-203 implementation'ı.

Amaç:
    Backend'den dönen HTTP hataları kullanıcıya 3 parça bilgiyle ulaşsın:
    ``title``   — kısa, insan-okur başlık
    ``message`` — ne olduğu (bağlam parametreleri desteklenir: ``{user_id}``)
    ``suggestion`` — kullanıcı ne yapabilir? (net aksiyon)

    Opsiyonel ``doc_url`` ileride eklenecek ``docs/errors/``'a işaret eder.

Kullanım:
    1. Yeni kod (önerilir):
        ``raise AppError("auth.invalid_credentials")``
        ``raise AppError("dsl.catalog_missing", project_id=pid)``

    2. Eski kod (backward compat):
        ``raise HTTPException(400, "Mevcut şifre hatalı")``
        Hâlâ çalışır, global exception handler bunu da yapılandırır — ancak
        ``code`` alanı olmaz, frontend varsayılan template gösterir.

Frontend sözleşmesi (JSON response shape):
    {
      "error": {
        "code": "auth.invalid_credentials",
        "title": "Geçersiz kimlik bilgileri",
        "message": "E-posta veya şifre hatalı.",
        "suggestion": "E-posta adresinizi ve şifrenizi kontrol edin...",
        "doc_url": null
      },
      "request_id": "abc123def456"
    }

Frontend herhangi bir client (apps/web + diğer tüketiciler) bu şemayı
toast/dialog/sayfa olarak render edebilir.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ErrorEntry(TypedDict, total=False):
    """Hata kataloğunda tek bir kayıt."""

    http_status: int
    title: str
    message: str         # "{var}" placeholder'ları ctx ile doldurulur
    suggestion: str
    doc_url: Optional[str]


# ═══════════════════════════════════════════════════════════════════════════════
# Katalog — kategori.alt_kod formatında. Yeni eklerken grupta tut, alfabetik kal.
# ═══════════════════════════════════════════════════════════════════════════════

ERROR_CATALOG: dict[str, ErrorEntry] = {
    # ── Auth / Session ────────────────────────────────────────────────────────
    "auth.invalid_credentials": {
        "http_status": 401,
        "title": "Geçersiz kimlik bilgileri",
        "message": "E-posta veya şifre hatalı.",
        "suggestion": (
            "E-posta adresinizi ve şifrenizi kontrol edin. Şifrenizi "
            "unuttuysanız 'Şifremi unuttum' bağlantısını kullanın."
        ),
    },
    "auth.session_expired": {
        "http_status": 401,
        "title": "Oturum süresi doldu",
        "message": "Oturumunuz güvenlik nedeniyle sonlandırıldı.",
        "suggestion": "Sayfayı yenileyin ve yeniden giriş yapın.",
    },
    "auth.admin_required": {
        "http_status": 403,
        "title": "Yönetici yetkisi gerekli",
        "message": "Bu işlemi yapmak için admin rolü gerekiyor.",
        "suggestion": (
            "Admin yetkisine sahip bir hesapla giriş yapın veya sistem "
            "yöneticinize başvurun."
        ),
    },
    "auth.email_already_exists": {
        "http_status": 409,
        "title": "E-posta zaten kayıtlı",
        "message": "Bu e-posta adresiyle başka bir hesap bulunuyor.",
        "suggestion": (
            "Farklı bir e-posta ile kaydolun veya mevcut hesaba giriş yapın."
        ),
    },
    "auth.password_incorrect": {
        "http_status": 400,
        "title": "Mevcut şifre hatalı",
        "message": "Girdiğiniz mevcut şifre doğrulanamadı.",
        "suggestion": (
            "Mevcut şifrenizi tekrar girin. Şifrenizi hatırlamıyorsanız "
            "önce şifre sıfırlama yapın."
        ),
    },
    "auth.reset_token_invalid": {
        "http_status": 400,
        "title": "Şifre sıfırlama bağlantısı geçersiz",
        "message": "Bağlantının süresi dolmuş ya da daha önce kullanılmış olabilir.",
        "suggestion": "Yeni bir şifre sıfırlama e-postası talep edin.",
    },
    "auth.rate_limited": {
        "http_status": 429,
        "title": "Çok hızlı deneme yaptınız",
        "message": "Güvenlik nedeniyle istek hızınız sınırlandı.",
        "suggestion": "Birkaç dakika bekleyip tekrar deneyin.",
    },
    # ── AI / LLM / Gateway ────────────────────────────────────────────────────
    "ai.gateway_unreachable": {
        "http_status": 503,
        "title": "AI servisi şu anda yanıt vermiyor",
        "message": "AI Gateway'e bağlanılamadı ({detail}).",
        "suggestion": (
            "Docker ortamında `docker compose up ai-gateway` ile servisi "
            "başlatın. Lokalde çalışıyorsanız 8080 portunun açık olduğunu "
            "kontrol edin: `make ports-check`."
        ),
    },
    "ai.all_providers_failed": {
        "http_status": 503,
        "title": "Hiçbir AI sağlayıcı yanıt veremedi",
        "message": "vLLM, Ollama, Groq ve Gemini zincirinin tamamı başarısız oldu.",
        "suggestion": (
            "Sağlayıcı durumunu kontrol edin (Gateway loglarına bakın). "
            "Lokal Ollama kullanıyorsanız `ollama list` ile modellerin "
            "yüklü olduğundan emin olun."
        ),
    },
    "ai.model_not_found": {
        "http_status": 400,
        "title": "AI modeli bulunamadı",
        "message": "İstenen model ({model}) aktif sağlayıcıda kayıtlı değil.",
        "suggestion": (
            "`AI_MODEL_*` env değişkenlerinde geçerli bir model adı kullanın. "
            "Ollama için: `ollama pull <model>` ile indirin."
        ),
    },
    "ai.token_budget_exceeded": {
        "http_status": 402,
        "title": "Token bütçesi aşıldı",
        "message": "Bu proje için belirlenen aylık LLM bütçesi tükendi.",
        "suggestion": (
            "Proje ayarlarından bütçe limitini artırın veya lokal Ollama "
            "sağlayıcısına geçin (ücretsiz)."
        ),
    },
    "ai.json_parse_failed": {
        "http_status": 502,
        "title": "AI cevabı işlenemedi",
        "message": "LLM beklenen JSON şemasına uymayan yanıt döndürdü.",
        "suggestion": (
            "Genellikle geçici bir sorundur, tekrar deneyin. Sorun devam "
            "ederse farklı bir AI sağlayıcı seçin."
        ),
    },
    # ── DSL / Test Generation ─────────────────────────────────────────────────
    "dsl.catalog_not_loaded": {
        "http_status": 500,
        "title": "DSL katalogu yüklenemedi",
        "message": "Aksiyon katalogu okunurken hata oluştu.",
        "suggestion": (
            "`packages/dsl/catalog/` klasörünün erişilebilir olduğundan emin "
            "olun. Düzenli olarak `make dsl-ai-warm` ile indeksi yeniden "
            "oluşturmayı deneyin."
        ),
    },
    "dsl.grounding_unknown": {
        "http_status": 422,
        "title": "Manuel adım DSL'e eşlenemedi",
        "message": "\"{step}\" adımı için yeterli benzerlikte bir aksiyon bulunamadı.",
        "suggestion": (
            "Adımı daha açık yazın veya DSL kataloğuna benzer bir aksiyon "
            "ekleyin. Eşik: AI_MODEL_RERANKER varsa %92, yoksa %85 hedef."
        ),
    },
    "dsl.validation_failed": {
        "http_status": 422,
        "title": "DSL doğrulaması başarısız",
        "message": "Üretilen Gherkin/YAML şemaya uymuyor: {detail}",
        "suggestion": (
            "Hata ayrıntılarını inceleyin. Sık hata: eksik 'Feature:' başlığı, "
            "bilinmeyen step, `# language: tr` eksikliği."
        ),
    },
    # ── Engine ────────────────────────────────────────────────────────────────
    "engine.unreachable": {
        "http_status": 503,
        "title": "Test motoruna erişilemiyor",
        "message": "Engine servisi (Flask) yanıt vermiyor.",
        "suggestion": (
            "Engine'in 5001 portunda çalıştığından emin olun: `make ports-check`. "
            "Yeniden başlatmak için: `docker compose restart engine`."
        ),
    },
    "engine.execution_timeout": {
        "http_status": 504,
        "title": "Test koşumu zaman aşımına uğradı",
        "message": "Koşum {elapsed}s içinde bitmedi.",
        "suggestion": (
            "`DEFAULT_TIMEOUT` env değerini artırın veya testi daha küçük "
            "parçalara bölün."
        ),
    },
    # ── Veri / Database ───────────────────────────────────────────────────────
    "db.unavailable": {
        "http_status": 503,
        "title": "Veritabanına erişilemiyor",
        "message": "PostgreSQL bağlantısı kurulamadı.",
        "suggestion": (
            "Postgres'in 5432 portunda çalıştığından emin olun "
            "(`make ports-check`). Docker: `docker compose up -d postgres`."
        ),
    },
    "db.unique_violation": {
        "http_status": 409,
        "title": "Kayıt zaten var",
        "message": "Girdiğiniz değer benzersiz olmalı: {field}",
        "suggestion": "Farklı bir değer deneyin veya mevcut kaydı düzenleyin.",
    },
    # ── Dosya / Upload ────────────────────────────────────────────────────────
    "file.too_large": {
        "http_status": 413,
        "title": "Dosya çok büyük",
        "message": "Yüklenen dosya {size_mb} MB, limit {limit_mb} MB.",
        "suggestion": (
            "Dosyayı sıkıştırın veya parçalara bölün. Yönetici olarak "
            "`max_body_size` limitini artırabilirsiniz."
        ),
    },
    "file.invalid_format": {
        "http_status": 415,
        "title": "Desteklenmeyen dosya türü",
        "message": "\".{ext}\" uzantısı kabul edilmiyor.",
        "suggestion": (
            "Desteklenen formatlar: {allowed}. Dosyayı dönüştürüp yeniden "
            "yükleyin."
        ),
    },
    # ── Kaynak / Resource ─────────────────────────────────────────────────────
    "resource.not_found": {
        "http_status": 404,
        "title": "Kayıt bulunamadı",
        "message": "İstenen {resource} bulunamadı.",
        "suggestion": (
            "Link'i kontrol edin veya listeden seçim yapın. Silinmiş olma "
            "ihtimali varsa audit log'a bakın."
        ),
    },
    "resource.forbidden_project": {
        "http_status": 403,
        "title": "Bu projeye erişiminiz yok",
        "message": "Hesabınız bu projenin üyesi değil.",
        "suggestion": (
            "Proje yöneticisinden sizi üye olarak eklemesini isteyin veya "
            "kendi projelerinizin listesine dönün."
        ),
    },
    # ── Genel ─────────────────────────────────────────────────────────────────
    "internal.unexpected": {
        "http_status": 500,
        "title": "Beklenmeyen bir hata oluştu",
        "message": "İşlem sırasında beklenmedik bir sorun yaşandı.",
        "suggestion": (
            "Birkaç saniye sonra tekrar deneyin. Sorun devam ederse "
            "request_id'yi destek ekibine iletin."
        ),
    },
    "validation.invalid_input": {
        "http_status": 422,
        "title": "Girdi doğrulaması başarısız",
        "message": "Gönderilen veriler şemaya uymuyor: {detail}",
        "suggestion": (
            "Form alanlarını tekrar kontrol edin. Zorunlu alanların dolu ve "
            "format'ların doğru olduğundan emin olun."
        ),
    },
}


def _format_message(raw: str, ctx: dict[str, Any]) -> str:
    """Katalog mesajındaki ``{var}`` placeholder'larını doldur.

    Eksik anahtar varsa placeholder'ı olduğu gibi bırakır (format_map).
    """

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:  # noqa: D401
            return "{" + key + "}"

    try:
        return raw.format_map(_SafeDict(**ctx))
    except Exception:  # pragma: no cover - defansif
        return raw


def get_error_entry(code: str) -> ErrorEntry:
    """Kataloğa bakar, yoksa genel ``internal.unexpected`` kaydını döner."""
    entry = ERROR_CATALOG.get(code)
    if entry is None:
        logger.warning("Bilinmeyen hata kodu: %s — fallback kullanılıyor", code)
        return ERROR_CATALOG["internal.unexpected"]
    return entry


class AppError(HTTPException):
    """Kataloga bağlı, zenginleştirilmiş HTTPException.

    HTTPException'dan türer — mevcut FastAPI exception handler'ları otomatik
    yakalar. Detail alanı dict formatında olduğundan istemciler ``error.code``,
    ``error.title``, vb. alanlara erişebilir.
    """

    def __init__(
        self,
        code: str,
        *,
        http_status: int | None = None,
        headers: dict[str, str] | None = None,
        **ctx: Any,
    ) -> None:
        entry = get_error_entry(code)
        status_code = http_status or int(entry.get("http_status", 500))
        detail = {
            "code": code,
            "title": entry.get("title", "Hata"),
            "message": _format_message(entry.get("message", ""), ctx),
            "suggestion": entry.get("suggestion", ""),
            "doc_url": entry.get("doc_url"),
        }
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code
        self.context = ctx


def enrich_legacy_detail(detail: Any, status_code: int) -> dict[str, Any]:
    """Eski tarz HTTPException'ların detail'ini zenginleştirilmiş şemaya çevir.

    Global exception handler tarafından kullanılır. AppError zaten yapılandırılmış
    detail döndürdüğü için dokunulmaz.
    """
    if isinstance(detail, dict) and "code" in detail and "title" in detail:
        # Zaten AppError formatında — olduğu gibi dön
        return detail

    # Mevcut Türkçe kısa mesajları koru, ama şema sağlasın
    text = detail if isinstance(detail, str) else str(detail)
    return {
        "code": f"legacy.http_{status_code}",
        "title": text[:80] if text else "Hata",
        "message": text,
        "suggestion": None,
        "doc_url": None,
    }
