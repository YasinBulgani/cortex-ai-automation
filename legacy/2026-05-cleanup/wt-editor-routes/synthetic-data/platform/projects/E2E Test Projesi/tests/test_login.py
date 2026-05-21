"""
Giriş fonksiyonalitesi testleri.

Giriş sayfası etkileşimlerini test eder.
"""

import pytest
from pages.login_page import LoginPage
from utils.test_data import TestData


pytestmark = pytest.mark.asyncio


class TestLogin:
    """
    Giriş işlemleri test sınıfı.
    """

    @pytest.fixture
    async def login_page(self, page, base_url):
        """
        Giriş sayfası fixture'ı.

        Parametreler:
            page: Sayfa nesnesi
            base_url: Temel URL

        Dönüş:
            LoginPage: Giriş sayfası nesnesi
        """
        login_page = LoginPage(page)
        await login_page.navigate(f"{base_url}/login")
        return login_page

    async def test_successful_login(self, login_page):
        """
        Başarılı giriş testini çalıştır.

        Parametreler:
            login_page: Giriş sayfası nesnesi
        """
        test_data = TestData()
        user = test_data.valid_users[0]

        await login_page.login(user['username'], user['password'])

        assert await login_page.is_logged_in(), "Giriş başarısız oldu"

    async def test_invalid_password(self, login_page):
        """
        Geçersiz şifre testini çalıştır.

        Parametreler:
            login_page: Giriş sayfası nesnesi
        """
        test_data = TestData()
        user = test_data.valid_users[0]

        await login_page.login(user['username'], 'wrong_password')

        error_message = await login_page.get_error_message()
        assert error_message, "Hata mesajı görüntülenmedi"

    async def test_empty_credentials(self, login_page):
        """
        Boş kimlik bilgileri testini çalıştır.

        Parametreler:
            login_page: Giriş sayfası nesnesi
        """
        await login_page.click(login_page.LOGIN_BUTTON)

        error_message = await login_page.get_error_message()
        assert error_message, "Hata mesajı görüntülenmedi"

    async def test_logout(self, authenticated_page):
        """
        Çıkış işlemini testini çalıştır.

        Parametreler:
            authenticated_page: Kimlik doğrulanmış sayfa
        """
        await authenticated_page.click('button[class="logout"]')
        await authenticated_page.wait_for_load_state('networkidle')

        current_url = authenticated_page.url
        assert 'login' in current_url, "Çıkış işlemi başarısız oldu"
