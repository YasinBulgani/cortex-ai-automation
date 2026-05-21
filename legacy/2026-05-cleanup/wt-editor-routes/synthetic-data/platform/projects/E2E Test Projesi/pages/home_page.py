"""
Ana Sayfa nesnesi.

Ana sayfa etkileşimlerini ve doğrulamalarını yönetir.
"""

from pages.base_page import BasePage
from playwright.async_api import Page


class HomePage(BasePage):
    """
    Ana sayfa için sayfa nesnesi.
    """

    # Seçiciler
    HEADER = 'header'
    NAVIGATION = 'nav'
    SEARCH_INPUT = 'input[name="search"]'
    USER_MENU = '.user-menu'

    def __init__(self, page: Page):
        """
        HomePage nesnesini başlat.

        Parametreler:
            page (Page): Playwright page nesnesi
        """
        super().__init__(page)

    async def search(self, query: str) -> None:
        """
        Sayfada arama yap.

        Parametreler:
            query (str): Arama sorgusu

        Yükseltir:
            Exception: Arama başarısız olursa
        """
        self.logger.info(f"Arama yapılıyor: {query}")

        await self.fill(self.SEARCH_INPUT, query)
        await self.page.press(self.SEARCH_INPUT, 'Enter')

        await self.wait_for_navigation()
        self.logger.info("Arama tamamlandı")

    async def navigate_to(self, menu_item: str) -> None:
        """
        Menü öğesine git.

        Parametreler:
            menu_item (str): Menü öğesi adı

        Yükseltir:
            Exception: Navigasyon başarısız olursa
        """
        self.logger.info(f"Menüye git: {menu_item}")

        selector = f'a:has-text("{menu_item}")'
        await self.click(selector)

        await self.wait_for_navigation()
        self.logger.info(f"Menü öğesine gidildi: {menu_item}")

    async def get_page_title(self) -> str:
        """
        Sayfa başlığını al.

        Dönüş:
            str: Sayfa başlığı
        """
        title = await self.page.title()
        self.logger.info(f"Sayfa başlığı: {title}")
        return title
