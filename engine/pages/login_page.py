"""
LoginPage — TestwrightAI Giriş ekranı Page Object.
LocatorManager üzerinden merkezi seçici yönetimi kullanır.
"""
from __future__ import annotations

import logging
from typing import Optional

from playwright.sync_api import Page, TimeoutError, expect

from pages.base_page import BasePage
from locators.locator_manager import LocatorManager

logger = logging.getLogger(__name__)

_PAGE = "login"


class LoginPage(BasePage):
    """TestwrightAI Giriş sayfası Page Object."""

    URL = "/login"

    def __init__(
        self,
        page: Page,
        locator_manager: Optional[LocatorManager] = None,
        base_url: str = "",
    ) -> None:
        super().__init__(page)
        self.lm = locator_manager or LocatorManager()
        self._base_url = base_url

    # ── Yardımcı — locator kısayolu ──────────────────────────────────────────

    def _loc(self, element: str) -> str:
        """Sayfa elemanı için test_id-first fallback locator döner."""
        return self.lm.get_locator_with_fallback(_PAGE, element)

    # ── Navigasyon ────────────────────────────────────────────────────────────

    def navigate_to_login(self) -> "LoginPage":
        """
        Giriş sayfasına git ve AuthBootstrap otomatik girişini devre dışı bırak.

        AuthBootstrap (root layout) dev modunda otomatik olarak giriş yaparak
        /login'i terk eder. `domcontentloaded` anında React hydration öncesi
        window.__bgtsAuthBootstrapped = true ayarlanarak bu davranış engellenir.
        """
        url = f"{self._base_url}{self.URL}" if self._base_url else self.URL
        logger.info("Giriş sayfasına gidiliyor: %s", url)
        self.navigate(url)  # wait_until="domcontentloaded"

        # React hydration öncesi AuthBootstrap dev auto-login'ini engelle.
        # AuthBootstrap flag'i görünce useEffect'ten erken çıkar.
        try:
            self.page.evaluate(
                "() => {"
                "  const w = window;"
                "  w.__bgtsAuthBootstrapped = true;"
                "  w.__bgtsAuthBootstrapping = true;"
                "}"
            )
        except Exception as exc:
            logger.debug("AuthBootstrap disable: %s", exc)

        return self

    def goto(self) -> "LoginPage":
        """``navigate_to_login`` ile aynı — geriye uyumluluk."""
        return self.navigate_to_login()

    # ── Element erişimi ───────────────────────────────────────────────────────

    @property
    def email_input(self):
        return self.page.locator(self._loc("email_input"))

    @property
    def password_input(self):
        return self.page.locator(self._loc("password_input"))

    @property
    def submit_button(self):
        return self.page.locator(self._loc("submit_button"))

    @property
    def error_alert(self):
        return self.page.locator(self._loc("error_alert"))

    @property
    def logo(self):
        return self.page.locator(self._loc("logo"))

    # ── Aksiyonlar ────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> "LoginPage":
        """E-posta ve şifre ile giriş yap."""
        logger.info("Giriş yapılıyor: %s", email)
        # ?next=/projects ile giriş yap — başarılı girişten sonra /projects'e yönlendirme.
        # Login sayfası nextPath = searchParams.get("next") || "/" kullandığından,
        # ?next param'ı olmadan giriş yapılırsa router.replace("/") ile root'a gider.
        login_url = (
            f"{self._base_url}/login?next=%2Fprojects"
            if self._base_url
            else "/login?next=%2Fprojects"
        )
        self.navigate(login_url)
        # React hydration öncesi AuthBootstrap dev auto-login'ini engelle.
        try:
            self.page.evaluate(
                "() => {"
                "  const w = window;"
                "  w.__bgtsAuthBootstrapped = true;"
                "  w.__bgtsAuthBootstrapping = true;"
                "}"
            )
        except Exception as exc:
            logger.debug("AuthBootstrap disable (login): %s", exc)
        self.fill(self._loc("email_input"), email)
        self.fill(self._loc("password_input"), password)
        self.click(self._loc("submit_button"))
        return self

    def login_as_admin(self) -> "LoginPage":
        """Varsayılan admin bilgileri ile giriş yap."""
        import os

        admin_email = os.getenv("ADMIN_EMAIL", "admin@bgtest.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        logger.info("Admin olarak giriş yapılıyor: %s", admin_email)
        return self.login(admin_email, admin_password)

    def get_error_message(self) -> str:
        """Hata mesajı metnini döner. Element yoksa boş string."""
        try:
            self.wait_for(self._loc("error_alert"), state="visible", timeout=5000)
            return self.get_text(self._loc("error_alert"))
        except TimeoutError:
            return ""

    def is_logged_in(self) -> bool:
        """Giriş yapılmış mı kontrol eder (URL /projects'e yönlendi mi)."""
        try:
            self.page.wait_for_url("**/projects", timeout=8000)
            return True
        except TimeoutError:
            return False

    def logout(self) -> "LoginPage":
        """Çıkış yap — sidebar'daki Çıkış butonuna tıkla."""
        logger.info("Çıkış yapılıyor")
        # Sidebar logout button (data-testid='sidebar-btn-logout')
        try:
            self.page.locator("[data-testid='sidebar-btn-logout']").click(timeout=10_000)
        except Exception:
            # Fallback: user menu dropdown approach
            try:
                nav_lm = LocatorManager()
                self.click(nav_lm.get_locator("common_navigation", "user_menu_button", "test_id"))
                # Try both "Çıkış" and "Çıkış Yap" text
                for logout_text in ["Çıkış", "Çıkış Yap", "Logout"]:
                    try:
                        self.page.get_by_text(logout_text, exact=True).first.click(timeout=5_000)
                        break
                    except Exception:
                        continue
            except Exception:
                pass
        return self

    # ── Assertion ─────────────────────────────────────────────────────────────

    def assert_page_loaded(self) -> "LoginPage":
        """Giriş sayfasının yüklendiğini doğrula (React hydration dahil)."""
        # 20s timeout: React hydration + SSR→CSR geçişini beklemek için yeterli
        expect(self.email_input).to_be_visible(timeout=20_000)
        expect(self.password_input).to_be_visible(timeout=20_000)
        expect(self.submit_button).to_be_visible(timeout=20_000)
        return self

    def assert_error_visible(self) -> "LoginPage":
        """Hata mesajının görünür olduğunu doğrula."""
        expect(self.error_alert).to_be_visible(timeout=10_000)
        return self

    def assert_redirect_to_projects(self) -> "LoginPage":
        """Projeler sayfasına yönlendirildiğini doğrula."""
        self.page.wait_for_url("**/projects", timeout=10_000)
        return self
