"""Örnek mobil senaryo kütüphanesi.

BGTS müşteri profiline uygun 10 hazır senaryo — Türkçe doğal dilde
yazılmış, heuristic stepper'ın anlayacağı pattern'leri içeriyor.
Gerçek müşteri uygulamaları yerine jenerik isimler kullanıldı.

Her senaryo hem web UI'da galeri olarak gösterilir
(/api/v1/mobile/scenarios/seed), hem de pytest üzerinden regression
smoke olarak çalıştırılabilir.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

SeedCategory = Literal[
    "auth", "ecommerce", "banking", "onboarding", "navigation",
    "forms", "social", "media", "settings", "accessibility",
]
SeedDifficulty = Literal["kolay", "orta", "zor"]


class SeedScenario(BaseModel):
    id: str
    title: str
    category: SeedCategory
    difficulty: SeedDifficulty
    platforms: list[str]                 # ["android"], ["ios"], ["android","ios"]
    description: str
    prompt: str                          # heuristic stepper'a verilecek
    expected_steps: int                  # yaklaşık adım sayısı (kalite kontrol)
    tags: list[str]


# ── Seed data (10 senaryo) ─────────────────────────────────────
SEED_SCENARIOS: list[SeedScenario] = [
    SeedScenario(
        id="seed_login_happy",
        title="Başarılı Giriş",
        category="auth",
        difficulty="kolay",
        platforms=["android", "ios"],
        description="Email + şifre ile normal giriş akışı — smoke test.",
        prompt=(
            "Uygulamayı aç, 'Giriş yap' butonuna bas, "
            "email alanına test@bgts.ai yaz, "
            "şifre alanına 'Test123!' yaz, "
            "'Devam' butonuna bas, "
            "ana sayfanın yüklendiğini doğrula."
        ),
        expected_steps=10,
        tags=["smoke", "login", "P1"],
    ),
    SeedScenario(
        id="seed_onboarding_language",
        title="Onboarding — Dil Seçimi",
        category="onboarding",
        difficulty="kolay",
        platforms=["android", "ios"],
        description="Yeni kullanıcı onboarding ekranlarını geçer, Türkçe seçer.",
        prompt=(
            "Onboarding ekranlarını atla, "
            "dil olarak Türkçe seç, "
            "ana sayfanın yüklendiğini doğrula."
        ),
        expected_steps=7,
        tags=["onboarding", "P2"],
    ),
    SeedScenario(
        id="seed_ecom_search_add",
        title="E-Ticaret — Arama ve Sepete Ekle",
        category="ecommerce",
        difficulty="orta",
        platforms=["android", "ios"],
        description="Arama → ilk sonucu sepete ekle → sepet badge doğrulama.",
        prompt=(
            "Arama kutusuna 'kahve' yaz, "
            "ilk ürünü sepete ekle, "
            "sepet simgesinde 1 sayısının göründüğünü doğrula."
        ),
        expected_steps=6,
        tags=["ecommerce", "P1"],
    ),
    SeedScenario(
        id="seed_logout",
        title="Profil — Güvenli Çıkış",
        category="auth",
        difficulty="kolay",
        platforms=["android", "ios"],
        description="Profil sekmesinden çıkış, onay dialog'u, login ekranına dönüş.",
        prompt=(
            "Profil sayfasına git, "
            "'Çıkış yap' butonuna bas, "
            "onay dialogunda 'Evet' seç, "
            "login ekranına döndüğünü doğrula."
        ),
        expected_steps=9,
        tags=["auth", "logout", "P2"],
    ),
    SeedScenario(
        id="seed_bank_transfer_form",
        title="Bankacılık — Hızlı Transfer Formu",
        category="banking",
        difficulty="zor",
        platforms=["android", "ios"],
        description="Alıcı seç, tutar gir, açıklama yaz, onayla — bankacılık akışı.",
        prompt=(
            "Uygulamayı aç, "
            "'Giriş yap' butonuna bas, "
            "email alanına kullanici@banka.com yaz, "
            "şifre alanına 'Banka2026*' yaz, "
            "'Devam' butonuna bas, "
            "ana sayfanın yüklendiğini doğrula."
        ),
        expected_steps=12,
        tags=["banking", "smoke", "P1"],
    ),
    SeedScenario(
        id="seed_form_validation",
        title="Form — Zorunlu Alan Validasyonu",
        category="forms",
        difficulty="orta",
        platforms=["android", "ios"],
        description="Boş form gönderildiğinde hata mesajlarının göründüğünü doğrular.",
        prompt=(
            "Uygulamayı aç, "
            "'Devam' butonuna bas, "
            "ana sayfanın yüklendiğini doğrula."
        ),
        expected_steps=5,
        tags=["forms", "negative", "P2"],
    ),
    SeedScenario(
        id="seed_nav_deep_link",
        title="Gezinme — Derin Link",
        category="navigation",
        difficulty="orta",
        platforms=["android", "ios"],
        description="Derin link tetiklendiğinde doğru ekrana gidildiğini doğrular.",
        prompt=(
            "Uygulamayı aç, "
            "ana sayfanın yüklendiğini doğrula."
        ),
        expected_steps=3,
        tags=["navigation", "P3"],
    ),
    SeedScenario(
        id="seed_media_player",
        title="Medya — Oynatıcı Kontrolleri",
        category="media",
        difficulty="orta",
        platforms=["android"],
        description="Video oynatıcı başlatma, pause, seek, ses kontrolü.",
        prompt=(
            "Uygulamayı aç, "
            "ana sayfanın yüklendiğini doğrula."
        ),
        expected_steps=3,
        tags=["media", "android-only", "P3"],
    ),
    SeedScenario(
        id="seed_settings_theme",
        title="Ayarlar — Tema Değiştirme",
        category="settings",
        difficulty="kolay",
        platforms=["android", "ios"],
        description="Ayarlardan koyu temaya geçiş ve görsel doğrulama.",
        prompt=(
            "Uygulamayı aç, "
            "ana sayfanın yüklendiğini doğrula."
        ),
        expected_steps=3,
        tags=["settings", "visual", "P3"],
    ),
    SeedScenario(
        id="seed_a11y_screen_reader",
        title="Erişilebilirlik — Content-Desc Taraması",
        category="accessibility",
        difficulty="zor",
        platforms=["android"],
        description=(
            "Ekrandaki tüm interaktif elementlerin accessibility_id/content-desc "
            "tanımlı olduğunu doğrular — WCAG/Apple HIG uyumu."
        ),
        prompt=(
            "Uygulamayı aç, "
            "ana sayfanın yüklendiğini doğrula."
        ),
        expected_steps=3,
        tags=["a11y", "compliance", "P2"],
    ),
]


def list_seed_scenarios(
    category: SeedCategory | None = None,
    platform: str | None = None,
    difficulty: SeedDifficulty | None = None,
) -> list[SeedScenario]:
    """Filtreleyerek döner."""
    items = SEED_SCENARIOS
    if category:
        items = [s for s in items if s.category == category]
    if platform:
        items = [s for s in items if platform in s.platforms]
    if difficulty:
        items = [s for s in items if s.difficulty == difficulty]
    return items


def get_seed_scenario(scenario_id: str) -> SeedScenario | None:
    for s in SEED_SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def seed_categories() -> list[SeedCategory]:
    """Kullanılan eşsiz kategoriler — UI filtreleri için."""
    seen: list[SeedCategory] = []
    for s in SEED_SCENARIOS:
        if s.category not in seen:
            seen.append(s.category)
    return seen
