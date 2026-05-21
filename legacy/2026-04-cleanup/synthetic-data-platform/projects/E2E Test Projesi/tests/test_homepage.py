"""
Ana sayfa fonksiyonalitesi testleri.

Ana sayfa etkileşimlerini test eder.
"""

import pytest
from pages.home_page import HomePage
from utils.test_data import TestData


pytestmark = pytest.mark.asyncio


class TestHomePage:
    """
    Ana sayfa test sınıfı.
    """

    @pytest.fixture
    async def home_page(self, authenticated_page, base_url):
        """
        Ana sayfa fixture'ı.

        Parametreler:
            authenticated_page: Kimlik doğrulanmış sayfa
            base_url: Temel URL

        Dönüş:
            HomePage: Ana sayfa nesnesi
        """
        home_page = HomePage(authenticated_page)
        await home_page.navigate(base_url)
        return home_page

    async def test_homepage_loads(self, home_page):
        """
        Ana sayfanın yüklenip yüklenmediğini testini çalıştır.

        Parametreler:
            home_page: Ana sayfa nesnesi
        """
        assert await home_page.is_visible(home_page.HEADER), "Header görüntülenmedi"
        assert await home_page.is_visible(home_page.NAVIGATION), "Navigasyon görüntülenmedi"

    async def test_navigation_works(self, home_page):
        """
        Navigasyon çalışıp çalışmadığını testini çalıştır.

        Parametreler:
            home_page: Ana sayfa nesnesi
        """
        await home_page.navigate_to('Hakkımızda')

        page_title = await home_page.get_page_title()
        assert 'Hakkımızda' in page_title, "Navigasyon başarısız oldu"

    async def test_search_functionality(self, home_page):
        """
        Arama fonksiyonalitesini testini çalıştır.

        Parametreler:
            home_page: Ana sayfa nesnesi
        """
        test_data = TestData()
        search_query = test_data.search_queries[0]

        await home_page.search(search_query)

        # Arama sonuçlarının yüklenmesini bekle
        await home_page.page.wait_for_selector('.search-results', timeout=5000)

        assert await home_page.is_visible('.search-results'), "Arama sonuçları görüntülenmedi"
