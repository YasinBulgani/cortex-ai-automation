"""
Proje iskele oluşturma modülü.

Bu modül, sıfırdan tam bir test otomasyon projesi yapısı oluşturmak için kullanılır.
Playwright ile async testler için hazır şablonlar ve konfigürasyon dosyaları üretir.
"""

import os
import io
import zipfile
from pathlib import Path
from typing import Dict, List


class ProjectScaffolder:
    """
    Test otomasyon projesi için İskele Oluşturucu sınıfı.

    Proje yapısını, test dosyalarını ve konfigürasyon dosyalarını
    otomatik olarak oluşturur.
    """

    def __init__(self, config: dict):
        """
        ProjectScaffolder nesnesini başlat.

        Parametreler:
            config (dict): Proje konfigürasyonu içeren sözlük
                - project_name (str): Proje adı
                - base_url (str): Temel URL
                - browser (str): Tarayıcı türü (chromium, firefox, webkit)
                - headless (bool): Başsız mod aktif
                - output_dir (str): Çıktı dizini
                - environments (list): Ortam listesi (dev, staging, prod)
        """
        self.project_name = config.get('project_name', 'test_project')
        self.base_url = config.get('base_url', 'http://localhost:3000')
        self.browser = config.get('browser', 'chromium')
        self.headless = config.get('headless', True)
        self.output_dir = config.get('output_dir', './projects')
        self.environments = config.get('environments', ['dev', 'staging', 'prod'])

        self.project_path = Path(self.output_dir) / self.project_name
        self.files_created = []

    def scaffold(self) -> dict:
        """
        Ana iskele oluşturma metodu.

        Tüm proje dosyalarını oluşturur ve yapıyı kurar.

        Dönüş:
            dict: Oluşturulan dosya listesi ve proje yolunu içeren sözlük
                {
                    'project_path': str,
                    'files_created': List[str],
                    'file_contents': Dict[str, str]
                }
        """
        # Dosya içerikleri sözlüğü
        file_contents = {}

        # Test dizini dosyaları
        test_files = {
            'tests/__init__.py': self._generate_init_file(),
            'tests/conftest.py': self._generate_test_conftest(),
            'tests/test_login.py': self._generate_test_login(),
            'tests/test_homepage.py': self._generate_test_homepage(),
        }

        # Sayfa nesneleri dizini
        page_files = {
            'pages/__init__.py': self._generate_init_file(),
            'pages/base_page.py': self._generate_base_page(),
            'pages/login_page.py': self._generate_login_page(),
            'pages/home_page.py': self._generate_home_page(),
        }

        # Yardımcılar dizini
        utils_files = {
            'utils/__init__.py': self._generate_init_file(),
            'utils/helpers.py': self._generate_helpers(),
            'utils/test_data.py': self._generate_test_data(),
        }

        # Konfigürasyon dizini
        config_files = {
            'config/__init__.py': self._generate_init_file(),
            'config/settings.py': self._generate_settings(),
        }

        # Fixture'lar dizini
        fixtures_files = {
            'fixtures/__init__.py': self._generate_init_file(),
            'fixtures/test_fixtures.py': self._generate_fixtures(),
        }

        # Kök dizin dosyaları
        root_files = {
            'conftest.py': self._generate_conftest(),
            'pytest.ini': self._generate_pytest_ini(),
            'pyproject.toml': self._generate_pyproject_toml(),
            'requirements.txt': self._generate_requirements(),
            '.env.example': self._generate_env_example(),
            '.gitignore': self._generate_gitignore(),
            'README.md': self._generate_readme(),
        }

        # .gitkeep dosyaları
        gitkeep_files = {
            'reports/.gitkeep': '',
            'screenshots/.gitkeep': '',
        }

        # Tüm dosyaları birleştir
        file_contents.update(test_files)
        file_contents.update(page_files)
        file_contents.update(utils_files)
        file_contents.update(config_files)
        file_contents.update(fixtures_files)
        file_contents.update(root_files)
        file_contents.update(gitkeep_files)

        # Dosyaları diske yaz
        self._write_files(file_contents)

        return {
            'project_path': str(self.project_path),
            'files_created': self.files_created,
            'file_contents': file_contents
        }

    def _generate_init_file(self) -> str:
        """
        Python paket başlatma dosyası içeriği.

        Dönüş:
            str: Boş __init__.py dosyası içeriği
        """
        return """# Paket başlatma dosyası\n"""

    def _generate_conftest(self) -> str:
        """
        Kök seviye conftest.py dosyası içeriği.

        Playwright fixture'larını ve browser konfigürasyonunu içerir.

        Dönüş:
            str: conftest.py dosyası içeriği
        """
        return '''"""
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
        browser = await p.''' + self.browser + '''.launch(
            headless=''' + str(self.headless) + '''
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
    return os.getenv('BASE_URL', '''' + self.base_url + '''')


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
'''

    def _generate_test_conftest(self) -> str:
        """
        Test dizini için conftest.py içeriği.

        Dönüş:
            str: Test conftest.py dosyası içeriği
        """
        return '''"""
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
'''

    def _generate_base_page(self) -> str:
        """
        BasePage sınıfı içeriği.

        Tüm sayfa nesnelerinin kalıtım aldığı temel sınıf.

        Dönüş:
            str: base_page.py dosyası içeriği
        """
        return '''"""
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
'''

    def _generate_login_page(self) -> str:
        """
        LoginPage sınıfı içeriği.

        Giriş sayfası spesifik işlemlerini içerir.

        Dönüş:
            str: login_page.py dosyası içeriği
        """
        return '''"""
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
'''

    def _generate_home_page(self) -> str:
        """
        HomePage sınıfı içeriği.

        Ana sayfa spesifik işlemlerini içerir.

        Dönüş:
            str: home_page.py dosyası içeriği
        """
        return '''"""
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
'''

    def _generate_test_login(self) -> str:
        """
        Test giriş dosyası içeriği.

        Giriş işlemleri için örnek testler.

        Dönüş:
            str: test_login.py dosyası içeriği
        """
        return '''"""
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
'''

    def _generate_test_homepage(self) -> str:
        """
        Test ana sayfa dosyası içeriği.

        Ana sayfa etkileşimleri için örnek testler.

        Dönüş:
            str: test_homepage.py dosyası içeriği
        """
        return '''"""
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
'''

    def _generate_settings(self) -> str:
        """
        Ayarlar konfigürasyon modülü içeriği.

        Ortam-spesifik ayarları ve konfigürasyonları içerir.

        Dönüş:
            str: settings.py dosyası içeriği
        """
        return '''"""
Proje ayarları ve konfigürasyon modülü.

Ortam-spesifik ayarları ve temel konfigürasyonları yönetir.
"""

import os
from dotenv import load_dotenv


# .env dosyasını yükle
load_dotenv()


class Settings:
    """
    Uygulama ayarlarını yönetir.
    """

    # Ortam seçimi
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')

    # Temel URL'ler
    BASE_URLS = {
        'dev': os.getenv('BASE_URL_DEV', 'http://localhost:3000'),
        'staging': os.getenv('BASE_URL_STAGING', 'https://staging.example.com'),
        'prod': os.getenv('BASE_URL_PROD', 'https://example.com')
    }

    BASE_URL = BASE_URLS.get(ENVIRONMENT, BASE_URLS['dev'])
    API_URL = os.getenv('API_URL', 'http://localhost:5000/api')

    # Browser ayarları
    BROWSER = os.getenv('BROWSER', 'chromium')
    HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'

    # Timeout ayarları (milisaniye cinsinden)
    DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', '5000'))
    NAVIGATION_TIMEOUT = int(os.getenv('NAVIGATION_TIMEOUT', '30000'))

    # Tekrar deneme ayarları
    RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '1'))

    # Kullanıcı kimlik bilgileri
    TEST_USERNAME = os.getenv('USERNAME', 'test_user')
    TEST_PASSWORD = os.getenv('PASSWORD', 'test_password')

    # Logging ayarları
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/test_execution.log')

    # Viewport ayarları
    VIEWPORT_WIDTH = int(os.getenv('VIEWPORT_WIDTH', '1920'))
    VIEWPORT_HEIGHT = int(os.getenv('VIEWPORT_HEIGHT', '1080'))

    # Locale ayarı
    LOCALE = os.getenv('LOCALE', 'tr-TR')


def get_base_url() -> str:
    """
    Geçerli ortam için temel URL'yi al.

    Dönüş:
        str: Temel URL
    """
    return Settings.BASE_URL


def get_api_url() -> str:
    """
    API URL'sini al.

    Dönüş:
        str: API URL
    """
    return Settings.API_URL
'''

    def _generate_helpers(self) -> str:
        """
        Yardımcı fonksiyonlar modülü içeriği.

        Yaygın olarak kullanılan yardımcı fonksiyonları içerir.

        Dönüş:
            str: helpers.py dosyası içeriği
        """
        return '''"""
Yardımcı fonksiyonlar modülü.

Testlerde kullanılan yaygın yardımcı fonksiyonları içerir.
"""

import random
import string
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Any
from faker import Faker


logger = logging.getLogger(__name__)


def generate_random_string(length: int = 10) -> str:
    """
    Rastgele karakter dizesi oluştur.

    Parametreler:
        length (int): Oluşturulacak dizinin uzunluğu

    Dönüş:
        str: Rastgele karakter dizisi
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_email() -> str:
    """
    Rastgele e-posta adresi oluştur.

    Dönüş:
        str: Rastgele e-posta adresi
    """
    fake = Faker('tr_TR')
    return fake.email()


def generate_random_phone() -> str:
    """
    Rastgele telefon numarası oluştur.

    Dönüş:
        str: Rastgele telefon numarası
    """
    fake = Faker('tr_TR')
    return fake.phone_number()


async def wait_and_retry(
    func: Callable,
    retries: int = 3,
    delay: float = 1.0,
    *args,
    **kwargs
) -> Any:
    """
    Fonksiyonu belirtilen sayıda tekrar dene.

    Parametreler:
        func (Callable): Çalıştırılacak fonksiyon
        retries (int): Deneme sayısı
        delay (float): Denemeler arasındaki gecikme (saniye)
        *args: Fonksiyon için pozisyonel argümanlar
        **kwargs: Fonksiyon için anahtar sözcük argümanları

    Dönüş:
        Any: Fonksiyonun dönüş değeri

    Yükseltir:
        Exception: Tüm denemeler başarısız olursa
    """
    for attempt in range(retries):
        try:
            logger.info(f"Deneme {attempt + 1}/{retries}: {func.__name__}")
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"Tüm denemeler başarısız oldu: {func.__name__}")
                raise
            logger.warning(f"Deneme başarısız oldu, {delay} saniye bekle ve yeniden dene")
            await asyncio.sleep(delay)


async def take_screenshot(page, name: str) -> None:
    """
    Sayfanın screenshot'ını al.

    Parametreler:
        page: Sayfa nesnesi
        name (str): Screenshot adı
    """
    try:
        screenshot_path = Path('screenshots') / f"{name}.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        logger.info(f"Screenshot kaydedildi: {screenshot_path}")
    except Exception as e:
        logger.error(f"Screenshot alma hatası: {e}")


def read_test_data(file_path: str) -> dict:
    """
    Test verilerini dosyadan oku.

    Parametreler:
        file_path (str): Test veri dosyasının yolu

    Dönüş:
        dict: Test verileri
    """
    import json

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Test veri okuma hatası: {e}")
        return {}


def format_datetime(dt: datetime = None, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Tarih-saati formatlı string'e dönüştür.

    Parametreler:
        dt (datetime): Dönüştürülecek tarih-saat
        fmt (str): Tarih-saat formatı

    Dönüş:
        str: Formatlı tarih-saat string'i
    """
    if dt is None:
        dt = datetime.now()

    return dt.strftime(fmt)


def get_current_timestamp() -> str:
    """
    Geçerli zaman damgasını al.

    Dönüş:
        str: Zaman damgası (ISO 8601 formatında)
    """
    return datetime.now().isoformat()
'''

    def _generate_test_data(self) -> str:
        """
        Test veri modülü içeriği.

        Testlerde kullanılan örnek veri setlerini içerir.

        Dönüş:
            str: test_data.py dosyası içeriği
        """
        return '''"""
Test veri modülü.

Testlerde kullanılan örnek veri setlerini içerir.
"""


class TestData:
    """
    Test verileri sınıfı.
    """

    # Geçerli kullanıcı verisi
    valid_users = [
        {
            'username': 'test_user',
            'password': 'Test@123456',
            'email': 'test@example.com'
        },
        {
            'username': 'admin',
            'password': 'Admin@123456',
            'email': 'admin@example.com'
        }
    ]

    # Geçersiz kullanıcı verisi
    invalid_users = [
        {
            'username': '',
            'password': ''
        },
        {
            'username': 'invalid_user',
            'password': 'wrong_password'
        },
        {
            'username': 'test_user',
            'password': ''
        }
    ]

    # Form test verisi
    form_data = [
        {
            'firstname': 'Ahmet',
            'lastname': 'Yılmaz',
            'email': 'ahmet@example.com',
            'phone': '+90 555 123 45 67',
            'message': 'Bu bir test mesajıdır.'
        },
        {
            'firstname': 'Fatma',
            'lastname': 'Kara',
            'email': 'fatma@example.com',
            'phone': '+90 555 987 65 43',
            'message': 'Test mesajı - 2'
        }
    ]

    # Arama sorguları
    search_queries = [
        'Test arama sorgusu 1',
        'Test arama sorgusu 2',
        'Ürün arama',
        'Hizmet arama',
        'Bilgi arama'
    ]

    # Sayfa başlıkları
    page_titles = {
        'home': 'Ana Sayfa',
        'login': 'Giriş',
        'about': 'Hakkımızda',
        'contact': 'İletişim'
    }

    # Error mesajları
    error_messages = {
        'invalid_credentials': 'Geçersiz kullanıcı adı veya şifre',
        'required_field': 'Bu alan gereklidir',
        'invalid_email': 'Geçersiz e-posta adresi',
        'network_error': 'Ağ hatası oluştu'
    }
'''

    def _generate_fixtures(self) -> str:
        """
        Test fixture'ları modülü içeriği.

        Özel test fixture'larını içerir.

        Dönüş:
            str: test_fixtures.py dosyası içeriği
        """
        return '''"""
Test fixture'ları modülü.

Özel test fixture'larını tanımlar.
"""

import pytest
import logging
from utils.test_data import TestData


logger = logging.getLogger(__name__)


@pytest.fixture
def test_user():
    """
    Test kullanıcı fixture'ı.

    Dönüş:
        dict: Test kullanıcı verisi
    """
    return TestData.valid_users[0]


@pytest.fixture
def invalid_credentials():
    """
    Geçersiz kimlik bilgileri fixture'ı.

    Dönüş:
        dict: Geçersiz kimlik bilgileri
    """
    return TestData.invalid_users[1]


@pytest.fixture
def form_test_data():
    """
    Form test veri fixture'ı.

    Dönüş:
        list: Form test verileri
    """
    return TestData.form_data


@pytest.fixture
def api_client():
    """
    API istemci fixture'ı.

    Dönüş:
        object: API istemci nesnesi
    """
    import requests

    class APIClient:
        def __init__(self, base_url='http://localhost:5000/api'):
            self.base_url = base_url
            self.session = requests.Session()

        def get(self, endpoint):
            return self.session.get(f"{self.base_url}/{endpoint}")

        def post(self, endpoint, data):
            return self.session.post(f"{self.base_url}/{endpoint}", json=data)

        def put(self, endpoint, data):
            return self.session.put(f"{self.base_url}/{endpoint}", json=data)

        def delete(self, endpoint):
            return self.session.delete(f"{self.base_url}/{endpoint}")

        def close(self):
            self.session.close()

    return APIClient()
'''

    def _generate_pytest_ini(self) -> str:
        """
        pytest.ini konfigürasyon dosyası içeriği.

        Dönüş:
            str: pytest.ini dosyası içeriği
        """
        return '''[pytest]
# Minimum Python sürümü
minversion = 7.0

# Test dosyası desenleri
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Async modu
asyncio_mode = auto

# İşaretler
markers =
    asyncio: async testler işareti
    slow: yavaş testler işareti
    integration: entegrasyon testleri işareti
    smoke: smoke testleri işareti
    critical: kritik testler işareti

# Logging ayarları
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(name)s - %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

log_file = logs/pytest.log
log_file_level = DEBUG
log_file_format = %(asctime)s [%(levelname)8s] %(name)s - %(message)s
log_file_date_format = %Y-%m-%d %H:%M:%S

# Hata ayıklama ayarları
addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings

# Timeout
timeout = 300

# Coverage
testpaths = tests
'''

    def _generate_pyproject_toml(self) -> str:
        """
        pyproject.toml konfigürasyon dosyası içeriği.

        Dönüş:
            str: pyproject.toml dosyası içeriği
        """
        return '''[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "''' + self.project_name + '''"
version = "0.1.0"
description = "Test Otomasyon Projesi"
readme = "README.md"
requires-python = ">=3.9"
authors = [
    {name = "Test Takımı", email = "test@example.com"}
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "pytest-playwright>=0.3.0",
    "pytest-html>=3.2.0",
    "pytest-xdist>=3.0.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
markers = [
    "asyncio: async testler",
    "slow: yavaş testler",
    "integration: entegrasyon testleri",
    "smoke: smoke testleri",
    "critical: kritik testler",
]
addopts = "-v --strict-markers --tb=short"

[tool.black]
line-length = 100
target-version = ["py39", "py310", "py311"]

[tool.isort]
profile = "black"
line_length = 100
'''

    def _generate_requirements(self) -> str:
        """
        requirements.txt dosyası içeriği.

        Proje bağımlılıklarını tanımlar.

        Dönüş:
            str: requirements.txt dosyası içeriği
        """
        return '''# Test çerçeveleri
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-playwright==0.4.3
pytest-html==4.1.1
pytest-xdist==3.5.0

# Browser otomasyon
playwright==1.41.0

# Konfigürasyon
python-dotenv==1.0.0

# Raporlama
allure-pytest==2.13.2

# HTTP istemci
requests==2.31.0

# Fake verisi oluşturma
faker==22.0.0

# Linting ve formatlama
black==24.1.1
isort==5.13.2
flake8==7.0.0

# Type checking
mypy==1.8.0
'''

    def _generate_env_example(self) -> str:
        """
        .env.example dosyası içeriği.

        Ortam değişkenleri şablonunu sağlar.

        Dönüş:
            str: .env.example dosyası içeriği
        """
        return '''# Uygulama ayarları
ENVIRONMENT=dev

# Temel URL'ler
BASE_URL_DEV=http://localhost:3000
BASE_URL_STAGING=https://staging.example.com
BASE_URL_PROD=https://example.com

# API ayarları
API_URL=http://localhost:5000/api

# Browser ayarları
BROWSER=chromium
HEADLESS=True

# Timeout ayarları (milisaniye)
DEFAULT_TIMEOUT=5000
NAVIGATION_TIMEOUT=30000

# Tekrar deneme ayarları
RETRY_ATTEMPTS=3
RETRY_DELAY=1

# Kimlik bilgileri
USERNAME=test_user
PASSWORD=test_password

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/test_execution.log

# Viewport
VIEWPORT_WIDTH=1920
VIEWPORT_HEIGHT=1080

# Locale
LOCALE=tr-TR
'''

    def _generate_gitignore(self) -> str:
        """
        .gitignore dosyası içeriği.

        Sürüm kontrolünden hariç tutulacak dosyaları tanımlar.

        Dönüş:
            str: .gitignore dosyası içeriği
        """
        return '''# Ortam değişkenleri
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Test sonuçları
.pytest_cache/
.coverage
htmlcov/
.tox/
.hypothesis/

# Test raporları
reports/
screenshots/
logs/
*.log

# Playwright
.auth/
pw-debug.log

# Allure
allure-results/
allure-report/

# Node
node_modules/
npm-debug.log

# Misc
.cache
.mypy_cache/
.dmypy.json
dmypy.json
'''

    def _generate_readme(self) -> str:
        """
        README.md dosyası içeriği.

        Proje belgelendirmesi sağlar.

        Dönüş:
            str: README.md dosyası içeriği
        """
        return '''# ''' + self.project_name + '''

Test Otomasyon Projesi - Playwright ile Async Testler

## Proje Hakkında

Bu proje, Playwright kullanarak web uygulamalarının test otomasyon için tam bir yapı sağlar.
Async/await desenini kullanarak hızlı ve güvenilir testler yazmanıza olanak tanır.

## Gereksinimler

- Python 3.9+
- pip
- Git

## Kurulum

1. Projeyi klonla:
```bash
git clone <repository-url>
cd ''' + self.project_name + '''
```

2. Virtual ortam oluştur:
```bash
python -m venv venv
```

3. Virtual ortamı aktifleştir:
```bash
# Windows
venv\\Scripts\\activate

# macOS / Linux
source venv/bin/activate
```

4. Bağımlılıkları yükle:
```bash
pip install -r requirements.txt
```

5. Playwright tarayıcılarını yükle:
```bash
playwright install
```

6. Ortam değişkenlerini yapılandır:
```bash
cp .env.example .env
# .env dosyasını düzenle
```

## Test Çalıştırma

### Tüm testleri çalıştır:
```bash
pytest
```

### Belirli bir test dosyasını çalıştır:
```bash
pytest tests/test_login.py
```

### Belirli bir test sınıfını çalıştır:
```bash
pytest tests/test_login.py::TestLogin
```

### Belirli bir test metodunu çalıştır:
```bash
pytest tests/test_login.py::TestLogin::test_successful_login
```

### İşaretlere göre testleri çalıştır:
```bash
pytest -m smoke
pytest -m critical
```

### Paralel testleri çalıştır:
```bash
pytest -n 4
```

### HTML raporu ile çalıştır:
```bash
pytest --html=report.html --self-contained-html
```

### Allure raporu ile çalıştır:
```bash
pytest --alluredir=allure-results
allure serve allure-results
```

### Verbose çıkış ile çalıştır:
```bash
pytest -v
```

### Yavaş testleri hariç tut:
```bash
pytest -m "not slow"
```

## Proje Yapısı

```
''' + self.project_name + '''/
├── tests/                 # Test dosyaları
│   ├── __init__.py
│   ├── conftest.py       # Test-spesifik fixture'lar
│   ├── test_login.py     # Giriş testleri
│   └── test_homepage.py  # Ana sayfa testleri
├── pages/                 # Sayfa Nesneleri (POM)
│   ├── __init__.py
│   ├── base_page.py      # Temel sayfa sınıfı
│   ├── login_page.py     # Giriş sayfası
│   └── home_page.py      # Ana sayfa
├── utils/                 # Yardımcı modüller
│   ├── __init__.py
│   ├── helpers.py        # Yardımcı fonksiyonlar
│   └── test_data.py      # Test verileri
├── config/                # Konfigürasyon
│   ├── __init__.py
│   └── settings.py       # Ayarlar
├── fixtures/              # Özel fixture'lar
│   ├── __init__.py
│   └── test_fixtures.py  # Fixture tanımları
├── reports/              # Test raporları
├── screenshots/          # Hata screenshot'ları
├── conftest.py          # Kök seviye konfigürasyon
├── pytest.ini           # Pytest konfigürasyonu
├── pyproject.toml       # Proje konfigürasyonu
├── requirements.txt     # Python bağımlılıkları
├── .env.example         # Ortam değişkenleri şablonu
├── .gitignore          # Git hariç tutma
└── README.md           # Bu dosya
```

## Sayfa Nesneleri Modeli (POM)

Proje, Sayfa Nesneleri Modeli desenini kullanır. Her sayfa, bir sayfa nesnesi sınıfı tarafından
temsil edilir ve sayfaya özgü etkileşimleri kapsüller.

### Örnek Kullanım:

```python
from pages.login_page import LoginPage

async def test_login(page):
    login_page = LoginPage(page)
    await login_page.navigate('http://localhost:3000/login')
    await login_page.login('username', 'password')
    assert await login_page.is_logged_in()
```

## Fixture'lar

Projede şu fixture'lar mevcuttur:

- `browser`: Browser instance'ı
- `context`: Browser context'i
- `page`: Sayfa nesnesi
- `base_url`: Temel URL
- `authenticated_page`: Kimlik doğrulanmış sayfa
- `test_user`: Test kullanıcı verisi
- `api_client`: API istemci

## Logging

Testler otomatik olarak loglanır. Log dosyaları `logs/` dizininde saklanır.

## Raporlama

### Pytest HTML Raporu:
```bash
pytest --html=report.html --self-contained-html
```

### Allure Raporu:
```bash
pytest --alluredir=allure-results
allure serve allure-results
```

## Katkı

Bu projede katkıda bulunmak için:

1. Fork yapın
2. Feature branch'i oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikleri commit edin (`git commit -m 'Add AmazingFeature'`)
4. Push yapın (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır.

## İletişim

Test Takımı - test@example.com

---

Son güncelleme: ''' + (self.environments[0] if self.environments else 'dev') + '''
'''

    def _write_files(self, file_contents: Dict[str, str]) -> None:
        """
        Dosyaları diske yaz.

        Parametreler:
            file_contents (Dict[str, str]): Dosya yolu ve içeriğini içeren sözlük
        """
        for file_path, content in file_contents.items():
            full_path = self.project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.files_created.append(str(full_path))

    def create_project_archive(self) -> bytes:
        """
        Proje yapısının ZIP dosyasını oluştur.

        Tüm dosyaları bellekteki bir ZIP dosyasında paketler.

        Dönüş:
            bytes: ZIP dosyası içeriği (bytes)

        Yükseltir:
            Exception: Arşiv oluşturma başarısız olursa
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in self.files_created:
                file_path_obj = Path(file_path)

                if file_path_obj.exists() and file_path_obj.is_file():
                    # Proje yoluna göre dosyanın relative yolunu al
                    arcname = file_path_obj.relative_to(self.project_path.parent)
                    zip_file.write(file_path_obj, arcname=arcname)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
