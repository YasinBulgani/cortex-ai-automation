"""
Giriş Sayfası nesnesi.

Giriş sayfası etkileşimlerini ve doğrulamalarını yönetir.
"""

from pages.base_page import BasePage
from playwright.async_api import Page


class LoginPage(BasePage):
    """
    Giriş sayfası için sayfa nesnesi.
    """

    # Seçiciler
    USERNAME_INPUT = 'input[name="username"]'
    PASSWORD_INPUT = 'input[name="password"]'
    LOGIN_BUTTON = 'button[type="submit"]'
    ERROR_MESSAGE = '.error-message'
    SUCCESS_INDICATOR = '.success-message'

    def __init__(self, page: Page):
        """
        LoginPage nesnesini başlat.

        Parametreler:
            page (Page): Playwright page nesnesi
        """
        super().__init__(page)

    async def login(self, username: str, password: str) -> None:
        """
        Kullanıcı adı ve şifre ile giriş yap.

        Parametreler:
            username (str): Kullanıcı adı
            password (str): Şifre

        Yükseltir:
            Exception: Giriş işlemi başarısız olursa
        """
        self.logger.info(f"Giriş yapılıyor: {username}")

        await self.fill(self.USERNAME_INPUT, username)
        await self.fill(self.PASSWORD_INPUT, password)
        await self.click(self.LOGIN_BUTTON)

        await self.wait_for_navigation()
        self.logger.info("Giriş başarılı")

    async def get_error_message(self) -> str:
        """
        Hata mesajını al.

        Dönüş:
            str: Hata mesajı
        """
        if await self.is_visible(self.ERROR_MESSAGE):
            return await self.get_text(self.ERROR_MESSAGE)
        return ""

    async def is_logged_in(self) -> bool:
        """
        Giriş yapılıp yapılmadığını kontrol et.

        Dönüş:
            bool: Giriş yapılmışsa True
        """
        return await self.is_visible(self.SUCCESS_INDICATOR)
