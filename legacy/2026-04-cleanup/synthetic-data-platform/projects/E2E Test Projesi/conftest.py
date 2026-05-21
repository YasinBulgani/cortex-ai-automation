"""
Kök seviye pytest konfigürasyon dosyası.

Playwright fixture'larını, browser ayarlarını ve screenshot
özelliklerini tanımlar.
"""

import pytest
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_execution.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
async def browser():
    """
    Browser instance fixture'ı.

    Playwright async session başlatır ve browser oluşturur.

    Dönüş:
        Browser: Playwright Browser nesnesi
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )
        yield browser
        await browser.close()


@pytest.fixture(scope="function")
async def context(browser: Browser):
    """
    Browser context fixture'ı.

    Her test için yeni bir context oluşturur.

    Parametreler:
        browser (Browser): Browser instance'ı

    Dönüş:
        BrowserContext: Yeni context nesnesi
    """
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="tr-TR"
    )
    yield context
    await context.close()


@pytest.fixture(scope="function")
async def page(context: BrowserContext):
    """
    Sayfa fixture'ı.

    Her test için context'ten bir sayfa oluşturur.

    Parametreler:
        context (BrowserContext): Browser context'i

    Dönüş:
        Page: Yeni page nesnesi
    """
    page = await context.new_page()

    # Başarısız request'ler için logging
    def log_response(response):
        logger.info(f"Response: {response.status} - {response.url}")

    page.on("response", log_response)

    yield page
    await page.close()


@pytest.fixture(scope="function")
async def screenshot_on_failure(page: Page, request):
    """
    Hata durumunda otomatik screenshot alma fixture'ı.

    Parametreler:
        page (Page): Sayfa nesnesi
        request: Pytest request nesnesi
    """
    yield

    if request.node.rep_call.failed if hasattr(request.node, 'rep_call') else False:
        screenshot_path = Path('screenshots') / f"{request.node.name}.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        logger.info(f"Hata screenshot'ı kaydedildi: {screenshot_path}")


@pytest.fixture(scope="function")
def base_url():
    """
    Temel URL fixture'ı.

    Dönüş:
        str: Temel URL
    """
    import os
    return os.getenv('BASE_URL',  + self.base_url + )


def pytest_runtest_makereport(item, call):
    """
    Test sonucunu döndür.

    Parametreler:
        item: Test öğesi
        call: Test çağrısı
    """
    if call.when == "call":
        setattr(item, "rep_call", call)


@pytest.fixture(autouse=True)
async def reset_browser_state(page: Page):
    """
    Her testten sonra browser durumunu sıfırla.

    Parametreler:
        page (Page): Sayfa nesnesi
    """
    yield
    try:
        await page.context.clear_cookies()
    except Exception as e:
        logger.warning(f"Browser durumu sıfırlama hatası: {e}")
