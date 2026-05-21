"""
Test dizini konfigürasyon dosyası.

Test-spesifik fixture'larını tanımlar.
"""

import pytest


@pytest.fixture
async def authenticated_page(page, base_url):
    """
    Kimlik doğrulanmış sayfa fixture'ı.

    Parametreler:
        page: Sayfa nesnesi
        base_url: Temel URL

    Dönüş:
        Page: Kimlik doğrulanmış sayfa
    """
    await page.goto(base_url)

    # Kimlik doğrulama işlemi simülasyonu
    await page.fill('input[name="username"]', 'test_user')
    await page.fill('input[name="password"]', 'test_password')
    await page.click('button[type="submit"]')

    await page.wait_for_load_state('networkidle')

    return page
