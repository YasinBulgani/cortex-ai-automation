"""
Örnek Test — Google Ana Sayfa
Playwright Page Object Model kullanımını gösterir.
AI entegrasyonu OLMADAN çalışır (API key gerektirmez).
"""
import pytest
from pages.base_page import BasePage


class TestGoogleHomepage:
    """Google ana sayfa testleri."""

    def test_page_title(self, page):
        """Sayfa başlığının 'Google' içerdiğini doğrula."""
        base = BasePage(page)
        base.navigate("https://www.google.com")
        assert "Google" in base.title, f"Beklenen 'Google' başlıkta yok: {base.title}"

    def test_search_input_visible(self, page):
        """Arama kutusunun görünür olduğunu doğrula."""
        base = BasePage(page)
        base.navigate("https://www.google.com")
        # Google arama kutusu
        assert base.is_visible("textarea[name='q']") or base.is_visible("input[name='q']"), \
            "Arama kutusu görünür değil!"

    def test_search_flow(self, page):
        """Arama yapma akışını test et."""
        base = BasePage(page)
        base.navigate("https://www.google.com")

        # Arama kutusunu bul ve doldur
        search_sel = "textarea[name='q'], input[name='q']"
        page.locator(search_sel).first.fill("Playwright Python otomasyon")
        page.locator(search_sel).first.press("Enter")

        # Sonuç sayfasını bekle
        page.wait_for_load_state("domcontentloaded")

        # URL'nin arama sonuçlarına gittiğini doğrula
        assert "search" in page.url, f"Arama sonuç sayfası URL'si beklenmiyor: {page.url}"

        # Screenshot al
        base.screenshot("google_search_result")


class TestWithAI:
    """AI destekli otomasyon testleri — API key gerektirir."""

    @pytest.mark.ai
    def test_ai_generated_actions(self, page, ai_engine):
        """
        AI ile aksiyonlar üretip çalıştırır.
        pytest -m ai komutuyla çalıştırılır.
        """
        url = "https://www.google.com"
        task = "Google ana sayfasına git, arama kutusuna 'Playwright Python' yaz ve Enter'a bas"

        # Sayfaya git (AI bağlamı için)
        page.goto(url, wait_until="domcontentloaded")

        # AI aksiyonları üret
        actions = ai_engine.generate_actions(task, page=page)
        assert actions, "AI hiç aksiyon üretmedi!"

        # Aksiyonları çalıştır
        results = ai_engine.execute_actions(actions, page)

        # En az bir başarılı adım olmalı
        passed = [r for r in results if r["status"] == "passed"]
        assert len(passed) > 0, "Hiç aksiyon başarılı olmadı!"
