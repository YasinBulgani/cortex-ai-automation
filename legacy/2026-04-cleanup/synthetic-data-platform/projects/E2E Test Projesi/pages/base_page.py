"""
Temel Sayfa Nesnesi sınıfı.

Tüm sayfa nesneleri tarafından kullanılan ortak metodları içerir.
"""

import logging
from pathlib import Path
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


logger = logging.getLogger(__name__)


class BasePage:
    """
    Tüm sayfa nesneleri için temel sınıf.

    Ortak sayfa etkileşimleri ve yardımcı metodları sağlar.
    """

    def __init__(self, page: Page):
        """
        BasePage nesnesini başlat.

        Parametreler:
            page (Page): Playwright page nesnesi
        """
        self.page = page
        self.logger = logging.getLogger(self.__class__.__name__)

    async def navigate(self, url: str) -> None:
        """
        Belirtilen URL'ye git.

        Parametreler:
            url (str): Gidilecek URL

        Yükseltir:
            Exception: Navigasyon başarısız olursa
        """
        try:
            await self.page.goto(url, wait_until='networkidle')
            self.logger.info(f"Navigasyon başarılı: {url}")
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Navigasyon zaman aşımı: {url}")
            raise

    async def click(self, selector: str) -> None:
        """
        Seçiciye tıkla.

        Parametreler:
            selector (str): CSS seçici

        Yükseltir:
            Exception: Tıklama başarısız olursa
        """
        try:
            await self.page.click(selector)
            self.logger.info(f"Tıklandı: {selector}")
        except Exception as e:
            self.logger.error(f"Tıklama hatası {selector}: {e}")
            raise

    async def fill(self, selector: str, value: str) -> None:
        """
        Giriş alanını doldur.

        Parametreler:
            selector (str): CSS seçici
            value (str): Doldurulacak değer

        Yükseltir:
            Exception: Doldurma başarısız olursa
        """
        try:
            await self.page.fill(selector, value)
            self.logger.info(f"Dolduruldu {selector}: {value}")
        except Exception as e:
            self.logger.error(f"Doldurma hatası {selector}: {e}")
            raise

    async def get_text(self, selector: str) -> str:
        """
        Seçicinin metin içeriğini al.

        Parametreler:
            selector (str): CSS seçici

        Dönüş:
            str: Metin içeriği

        Yükseltir:
            Exception: Metin alma başarısız olursa
        """
        try:
            text = await self.page.text_content(selector)
            self.logger.info(f"Metin alındı {selector}: {text}")
            return text or ""
        except Exception as e:
            self.logger.error(f"Metin alma hatası {selector}: {e}")
            raise

    async def wait_for(self, selector: str, timeout: int = 5000) -> None:
        """
        Seçicinin görünür olmasını bekle.

        Parametreler:
            selector (str): CSS seçici
            timeout (int): Timeout milisaniye cinsinden

        Yükseltir:
            PlaywrightTimeoutError: Timeout aşılırsa
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            self.logger.info(f"Beklenildi: {selector}")
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Bekleme zaman aşımı {selector}")
            raise

    async def screenshot(self, name: str) -> None:
        """
        Sayfanın screenshot'ını al.

        Parametreler:
            name (str): Screenshot dosya adı
        """
        try:
            screenshot_path = Path('screenshots') / f"{name}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await self.page.screenshot(path=str(screenshot_path))
            self.logger.info(f"Screenshot kaydedildi: {screenshot_path}")
        except Exception as e:
            self.logger.error(f"Screenshot alma hatası: {e}")
            raise

    async def is_visible(self, selector: str) -> bool:
        """
        Seçicinin görünür olup olmadığını kontrol et.

        Parametreler:
            selector (str): CSS seçici

        Dönüş:
            bool: Görünür ise True
        """
        try:
            return await self.page.is_visible(selector)
        except Exception as e:
            self.logger.warning(f"Görünürlük kontrolü hatası {selector}: {e}")
            return False

    async def get_elements(self, selector: str) -> list:
        """
        Seçiciye uygun tüm öğeleri al.

        Parametreler:
            selector (str): CSS seçici

        Dönüş:
            list: Öğelerin listesi
        """
        try:
            elements = await self.page.query_selector_all(selector)
            self.logger.info(f"Bulunan öğeler {selector}: {len(elements)}")
            return elements
        except Exception as e:
            self.logger.error(f"Öğe alma hatası {selector}: {e}")
            return []

    async def select_option(self, selector: str, value: str) -> None:
        """
        Select dropdown'dan seçenek seç.

        Parametreler:
            selector (str): CSS seçici
            value (str): Seçilecek değer

        Yükseltir:
            Exception: Seçim başarısız olursa
        """
        try:
            await self.page.select_option(selector, value)
            self.logger.info(f"Seçenek seçildi {selector}: {value}")
        except Exception as e:
            self.logger.error(f"Seçenek seçme hatası {selector}: {e}")
            raise

    async def hover(self, selector: str) -> None:
        """
        Seçicinin üzerine gel.

        Parametreler:
            selector (str): CSS seçici

        Yükseltir:
            Exception: Hover başarısız olursa
        """
        try:
            await self.page.hover(selector)
            self.logger.info(f"Hover yapıldı: {selector}")
        except Exception as e:
            self.logger.error(f"Hover hatası {selector}: {e}")
            raise

    async def double_click(self, selector: str) -> None:
        """
        Seçiciye çift tıkla.

        Parametreler:
            selector (str): CSS seçici

        Yükseltir:
            Exception: Çift tıklama başarısız olursa
        """
        try:
            await self.page.dblclick(selector)
            self.logger.info(f"Çift tıklandı: {selector}")
        except Exception as e:
            self.logger.error(f"Çift tıklama hatası {selector}: {e}")
            raise

    async def get_attribute(self, selector: str, attr: str) -> str:
        """
        Öğenin özniteliğini al.

        Parametreler:
            selector (str): CSS seçici
            attr (str): Öznitelik adı

        Dönüş:
            str: Öznitelik değeri

        Yükseltir:
            Exception: Öznitelik alma başarısız olursa
        """
        try:
            value = await self.page.get_attribute(selector, attr)
            self.logger.info(f"Öznitelik alındı {selector}.{attr}: {value}")
            return value or ""
        except Exception as e:
            self.logger.error(f"Öznitelik alma hatası {selector}: {e}")
            raise

    async def get_url(self) -> str:
        """
        Geçerli sayfa URL'sini al.

        Dönüş:
            str: Sayfa URL'si
        """
        url = self.page.url
        self.logger.info(f"URL alındı: {url}")
        return url

    async def wait_for_navigation(self) -> None:
        """
        Sayfa navigasyonunu bekle.

        Yükseltir:
            Exception: Navigasyon beklemesi başarısız olursa
        """
        try:
            await self.page.wait_for_load_state('networkidle')
            self.logger.info("Navigasyon tamamlandı")
        except Exception as e:
            self.logger.error(f"Navigasyon bekleme hatası: {e}")
            raise

    async def scroll_to(self, selector: str) -> None:
        """
        Seçiciye kaydır.

        Parametreler:
            selector (str): CSS seçici

        Yükseltir:
            Exception: Kaydırma başarısız olursa
        """
        try:
            await self.page.locator(selector).scroll_into_view_if_needed()
            self.logger.info(f"Kaydırma yapıldı: {selector}")
        except Exception as e:
            self.logger.error(f"Kaydırma hatası {selector}: {e}")
            raise
