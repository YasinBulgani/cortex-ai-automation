"""
Monkey Testing Modülü - QA Engine İçin Rastgele Test Modülü

Bu modül, web uygulamalarının dayanıklılığını ve stabiliteyi test etmek için
rastgele ve stress testleri yürütür.
"""

import asyncio
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
import re

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    async_playwright = None
    Page = None
    Browser = None
    BrowserContext = None

# Logger yapılandırması
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@dataclass
class MonkeyTestResult:
    """
    Monkey test sonuçlarını tutan veri sınıfı
    """
    test_type: str
    status: str
    duration: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ClickResult:
    """
    Rastgele tıklama sonucu
    """
    success: bool
    element_tag: Optional[str]
    element_class: Optional[str]
    element_id: Optional[str]
    error: Optional[str] = None


@dataclass
class FuzzResult:
    """
    Form fuzzing sonucu
    """
    form_id: Optional[str]
    form_name: Optional[str]
    inputs_fuzzed: int
    selects_fuzzed: int
    submit_attempted: bool
    errors: List[str] = field(default_factory=list)
    payloads_used: List[str] = field(default_factory=list)


@dataclass
class LinkCheckResult:
    """
    Link kontrol sonucu
    """
    url: str
    status_code: Optional[int]
    is_internal: bool
    is_broken: bool
    error: Optional[str] = None
    response_time: Optional[float] = None


class RandomClicker:
    """
    Sayfadaki rastgele elementlere tıklayan test modülü.
    Tıklanabilir elementleri otomatik olarak bulur ve rastgele seçer.
    """

    def __init__(self):
        """RandomClicker'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.click_count = 0

    async def click_random_element(self, page: Page) -> ClickResult:
        """
        Sayfadaki tıklanabilir elementlerden rastgele birini bulur ve tıklar.

        Args:
            page: Playwright Page nesnesi

        Returns:
            ClickResult: Tıklama işleminin sonucu
        """
        try:
            # Tıklanabilir element seçicileri
            selectors = [
                'a',
                'button',
                'input[type=submit]',
                'input[type=button]',
                '[role=button]',
                '[onclick]'
            ]

            # Tüm tıklanabilir elementleri bul
            clickable_elements = []
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    clickable_elements.extend(elements)
                except Exception as e:
                    self.logger.debug(f"Selector '{selector}' işlenirken hata: {e}")

            if not clickable_elements:
                self.logger.warning("Hiç tıklanabilir element bulunamadı")
                return ClickResult(success=False, element_tag=None, element_class=None,
                                 element_id=None, error="Tıklanabilir element bulunamadı")

            # Rastgele bir element seç
            import random
            element = random.choice(clickable_elements)

            # Element görünürlüğünü kontrol et
            is_visible = await element.is_visible()
            if not is_visible:
                self.logger.debug("Seçilen element görünür değil, başka bir element seçiliyor")
                return ClickResult(success=False, element_tag=None, element_class=None,
                                 element_id=None, error="Element görünür değil")

            # Element bilgilerini al
            tag_name = await element.evaluate('el => el.tagName')
            class_name = await element.evaluate('el => el.className')
            element_id = await element.evaluate('el => el.id')

            # Elementte tıkla
            await element.click(timeout=5000)
            self.click_count += 1
            self.logger.info(f"Element tıklandı: {tag_name} (ID: {element_id}, Class: {class_name})")

            return ClickResult(success=True, element_tag=tag_name, element_class=class_name,
                             element_id=element_id)

        except Exception as e:
            self.logger.error(f"Rastgele tıklama işleminde hata: {e}")
            return ClickResult(success=False, element_tag=None, element_class=None,
                             element_id=None, error=str(e))


class FormFuzzer:
    """
    Sayfadaki formları rastgele veri ile dolduran fuzzing modülü.
    XSS, SQL injection ve diğer zararlı payloadları test eder.
    """

    # Önceden tanımlanmış zararlı payload'lar
    XSS_PAYLOADS = [
        '<script>alert(1)</script>',
        '"><img src=x onerror=alert(1)>',
        '<img src=x onerror="alert(\'xss\')">',
        '<svg onload=alert(1)>',
        'javascript:alert(1)',
        '<iframe src="javascript:alert(1)"></iframe>',
        '<body onload=alert(1)>',
        '<img src= onerror=alert(1)>',
        '<marquee onstart=alert(1)>',
        'data:text/html,<script>alert(1)</script>'
    ]

    SQL_PAYLOADS = [
        "' OR 1=1 --",
        "'; DROP TABLE users; --",
        "' UNION SELECT NULL, NULL --",
        "1' AND '1'='1",
        "admin' --",
        "' OR 'a'='a",
        "1; DELETE FROM users;",
        "' OR 1=1 /*",
        "' UNION ALL SELECT NULL,NULL,NULL --",
        "' AND 1=0 UNION ALL SELECT 'a','b','c' --"
    ]

    SPECIAL_CHARS = [
        '!@#$%^&*()',
        '\x00\x01\x02\x03',
        '<%>',
        '${7*7}',
        '#{7*7}',
        '*;|`&><',
        '../../etc/passwd',
        '....\\\\....\\\\',
    ]

    LONG_TEXT = 'A' * 10000
    UNICODE_PAYLOADS = [
        '😀💀🔥',
        '\u0000\u0001\u0002',
        '你好世界',
        '🚀<script>alert(1)</script>',
        '\uFEFF<script>alert(1)</script>',
    ]

    EMPTY_STRINGS = ['', ' ', '\t', '\n', '\r\n']

    def __init__(self):
        """FormFuzzer'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.fuzz_results: List[FuzzResult] = []

    async def fuzz_forms(self, page: Page, max_forms: int = 10) -> List[FuzzResult]:
        """
        Sayfadaki tüm formları bulur ve rastgele veri ile doldurur.

        Args:
            page: Playwright Page nesnesi
            max_forms: En fazla kaç form test edilecek

        Returns:
            List[FuzzResult]: Form fuzzing sonuçlarının listesi
        """
        self.fuzz_results = []

        try:
            # Tüm formları bul
            forms = await page.query_selector_all('form')
            forms = forms[:max_forms]  # Maksimum form sayısını sınırla

            self.logger.info(f"{len(forms)} form bulundu, fuzzing başlıyor")

            for form_idx, form in enumerate(forms):
                result = await self._fuzz_single_form(page, form, form_idx)
                self.fuzz_results.append(result)

            return self.fuzz_results

        except Exception as e:
            self.logger.error(f"Form fuzzing işleminde hata: {e}")
            return self.fuzz_results

    async def _fuzz_single_form(self, page: Page, form, form_idx: int) -> FuzzResult:
        """
        Tek bir formu fuzz eder.

        Args:
            page: Playwright Page nesnesi
            form: Form elemanı
            form_idx: Form indeksi

        Returns:
            FuzzResult: İşlem sonucu
        """
        form_id = await form.get_attribute('id') or f'form_{form_idx}'
        form_name = await form.get_attribute('name')

        result = FuzzResult(
            form_id=form_id,
            form_name=form_name,
            inputs_fuzzed=0,
            selects_fuzzed=0,
            submit_attempted=False
        )

        try:
            # Form içindeki input elementlerini bul
            inputs = await form.query_selector_all('input')
            selects = await form.query_selector_all('select')
            textareas = await form.query_selector_all('textarea')

            import random

            # Input'ları fuzz et
            for input_elem in inputs:
                try:
                    input_type = await input_elem.get_attribute('type') or 'text'
                    input_id = await input_elem.get_attribute('id') or 'unknown'

                    # Input tiplerine göre uygun payload seç
                    payload = self._select_payload(input_type)
                    result.payloads_used.append(payload)

                    # Input'a değer gir
                    await input_elem.fill(payload, timeout=2000)
                    result.inputs_fuzzed += 1

                except Exception as e:
                    result.errors.append(f"Input #{input_id} doldurulurken hata: {e}")
                    self.logger.debug(f"Input doldurulurken hata: {e}")

            # Select elementlerini fuzz et
            for select_elem in selects:
                try:
                    options = await select_elem.query_selector_all('option')
                    if options:
                        random_option = random.choice(options)
                        option_value = await random_option.get_attribute('value')
                        if option_value:
                            await select_elem.select_option(option_value, timeout=2000)
                        result.selects_fuzzed += 1
                except Exception as e:
                    result.errors.append(f"Select işleminde hata: {e}")

            # Textarea'ları fuzz et
            for textarea in textareas:
                try:
                    payload = random.choice(self.XSS_PAYLOADS + self.SQL_PAYLOADS)
                    await textarea.fill(payload, timeout=2000)
                    result.inputs_fuzzed += 1
                except Exception as e:
                    result.errors.append(f"Textarea doldurulurken hata: {e}")

            # Form'u submit et
            try:
                submit_button = await form.query_selector('button[type=submit], input[type=submit]')
                if submit_button:
                    await submit_button.click(timeout=5000)
                    result.submit_attempted = True
                    self.logger.info(f"Form #{form_id} submit edildi")
                else:
                    # Alternatif olarak form'u JavaScript ile submit et
                    await form.evaluate('form => form.submit()', form)
                    result.submit_attempted = True
            except Exception as e:
                result.errors.append(f"Form submit işleminde hata: {e}")
                self.logger.debug(f"Form submit hatası: {e}")

        except Exception as e:
            result.errors.append(f"Form işleme hatası: {e}")
            self.logger.error(f"Form #{form_id} işleminde genel hata: {e}")

        return result

    def _select_payload(self, input_type: str) -> str:
        """
        Input tipi temelinde uygun payload seçer.

        Args:
            input_type: Input elemanının tipi

        Returns:
            str: Seçilen payload
        """
        import random

        type_map = {
            'email': lambda: random.choice(['test@example.com"', 'test@example.com\' OR 1=1']),
            'password': lambda: random.choice(self.SQL_PAYLOADS),
            'number': lambda: '999999999999999999999',
            'tel': lambda: '1234567890' * 10,
            'url': lambda: 'javascript:alert(1)',
            'search': lambda: random.choice(self.XSS_PAYLOADS),
            'text': lambda: self.LONG_TEXT,
            'hidden': lambda: random.choice(self.SPECIAL_CHARS),
        }

        payload_generator = type_map.get(input_type, lambda: random.choice(self.XSS_PAYLOADS))
        return payload_generator()


class ScrollStresser:
    """
    Sayfayı hızlıca scroll ederek stress testi yapan modül.
    Dinamik içerik yükleme ve console hatalarını kontrol eder.
    """

    def __init__(self):
        """ScrollStresser'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.scroll_count = 0

    async def stress_scroll(self, page: Page, iterations: int = 50) -> Dict[str, Any]:
        """
        Sayfayı hızlıca yukarı ve aşağı scroll eder.

        Args:
            page: Playwright Page nesnesi
            iterations: Kaç kez scroll yapılacak

        Returns:
            Dict[str, Any]: Scroll test sonuçları
        """
        result = {
            'iterations': iterations,
            'successful_scrolls': 0,
            'errors': [],
            'console_errors': [],
            'duration': 0
        }

        start_time = time.time()

        try:
            import random

            for i in range(iterations):
                try:
                    # Rastgele aşağı scroll
                    scroll_amount = random.randint(100, 1000)
                    await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                    await asyncio.sleep(0.01)  # Kısa bekleme

                    # Rastgele yukarı scroll
                    scroll_amount = random.randint(100, 1000)
                    await page.evaluate(f'window.scrollBy(0, -{scroll_amount})')
                    await asyncio.sleep(0.01)

                    result['successful_scrolls'] += 1
                    self.scroll_count += 1

                except Exception as e:
                    result['errors'].append(f"Scroll #{i}: {str(e)}")
                    self.logger.debug(f"Scroll hatası (#{i}): {e}")

            # Console hatalarını kontrol et
            console_result = await self._check_console_errors(page)
            result['console_errors'] = console_result

            result['duration'] = time.time() - start_time
            self.logger.info(f"Scroll stress testi tamamlandı: {result['successful_scrolls']}/{iterations} başarılı")

        except Exception as e:
            result['errors'].append(f"Genel scroll hatası: {str(e)}")
            self.logger.error(f"Scroll stress testi hatası: {e}")

        return result

    async def _check_console_errors(self, page: Page) -> List[str]:
        """
        Sayfada console hatalarını kontrol eder.

        Args:
            page: Playwright Page nesnesi

        Returns:
            List[str]: Konsol hataları
        """
        errors = []
        try:
            # JavaScript ile console hataları kontrol et
            errors = await page.evaluate('''
                () => {
                    if (window.__errors) {
                        return window.__errors;
                    }
                    return [];
                }
            ''')
        except Exception as e:
            self.logger.debug(f"Console hataları kontrol edilemedi: {e}")

        return errors


class ResizeStresser:
    """
    Pencere boyutunu değiştirerek responsive tasarım ve layout bozulmalarını
    test eden modül.
    """

    # Önceden tanımlanmış viewport boyutları
    MOBILE_SIZES = [
        (375, 667),    # iPhone SE
        (390, 844),    # iPhone 12
        (414, 896),    # iPhone XR
    ]

    TABLET_SIZES = [
        (768, 1024),   # iPad
        (820, 1180),   # iPad Pro
    ]

    DESKTOP_SIZES = [
        (1280, 720),   # HD
        (1920, 1080),  # Full HD
        (2560, 1440),  # 2K
    ]

    def __init__(self):
        """ResizeStresser'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.resize_count = 0

    async def stress_resize(self, page: Page, sizes: Optional[List[Tuple[int, int]]] = None) -> Dict[str, Any]:
        """
        Farklı viewport boyutlarında sayfayı test eder.

        Args:
            page: Playwright Page nesnesi
            sizes: Test edilecek viewport boyutları. None ise tüm önceden tanımlanmış boyutlar kullanılır.

        Returns:
            Dict[str, Any]: Resize test sonuçları
        """
        if sizes is None:
            sizes = self.MOBILE_SIZES + self.TABLET_SIZES + self.DESKTOP_SIZES

        result = {
            'tested_sizes': len(sizes),
            'successful_resizes': 0,
            'layout_issues': [],
            'overflow_issues': [],
            'errors': [],
            'duration': 0,
            'details': {}
        }

        start_time = time.time()

        try:
            for width, height in sizes:
                try:
                    # Viewport boyutunu değiştir
                    await page.set_viewport_size({"width": width, "height": height})
                    await page.wait_for_load_state('networkidle', timeout=5000)

                    # Layout sorunlarını kontrol et
                    layout_check = await self._check_layout_issues(page, width, height)

                    result['successful_resizes'] += 1
                    self.resize_count += 1
                    result['details'][f'{width}x{height}'] = layout_check

                    if layout_check['has_overflow']:
                        result['overflow_issues'].append(f"{width}x{height}: Overflow tespit edildi")

                    if layout_check['has_issues']:
                        result['layout_issues'].append(f"{width}x{height}: Layout sorunu tespit edildi")

                    self.logger.info(f"Viewport {width}x{height} test edildi")

                except Exception as e:
                    error_msg = f"Resize {width}x{height}: {str(e)}"
                    result['errors'].append(error_msg)
                    self.logger.debug(error_msg)

            result['duration'] = time.time() - start_time
            self.logger.info(f"Resize stress testi tamamlandı: {result['successful_resizes']}/{len(sizes)} başarılı")

        except Exception as e:
            result['errors'].append(f"Genel resize hatası: {str(e)}")
            self.logger.error(f"Resize stress testi hatası: {e}")

        return result

    async def _check_layout_issues(self, page: Page, width: int, height: int) -> Dict[str, Any]:
        """
        Layout sorunlarını kontrol eder.

        Args:
            page: Playwright Page nesnesi
            width: Pencere genişliği
            height: Pencere yüksekliği

        Returns:
            Dict[str, Any]: Layout kontrol sonuçları
        """
        result = {
            'has_overflow': False,
            'has_issues': False,
            'body_width': 0,
            'body_height': 0,
            'viewport_width': width,
            'viewport_height': height
        }

        try:
            overflow_info = await page.evaluate('''
                () => {
                    const body = document.body;
                    const html = document.documentElement;
                    return {
                        bodyWidth: body.scrollWidth,
                        bodyHeight: body.scrollHeight,
                        htmlWidth: html.scrollWidth,
                        htmlHeight: html.scrollHeight,
                        hasHorizontalScroll: body.scrollWidth > window.innerWidth,
                        hasVerticalScroll: body.scrollHeight > window.innerHeight,
                        brokenElements: document.querySelectorAll('[style*="overflow:hidden"]').length
                    };
                }
            ''')

            result['body_width'] = overflow_info.get('bodyWidth', 0)
            result['body_height'] = overflow_info.get('bodyHeight', 0)
            result['has_overflow'] = overflow_info.get('hasHorizontalScroll', False)

            if overflow_info.get('brokenElements', 0) > 0:
                result['has_issues'] = True

        except Exception as e:
            self.logger.debug(f"Layout kontrol hatası: {e}")

        return result


class NavigationFuzzer:
    """
    Sayfadaki linkleri rastgele takip ederek navigasyon ve hata sayfalarını
    test eden modül.
    """

    def __init__(self):
        """NavigationFuzzer'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.visited_pages: set = set()
        self.error_pages: List[str] = []
        self.navigation_depth = 0

    async def fuzz_navigation(self, page: Page, max_pages: int = 20, depth_limit: int = 5) -> Dict[str, Any]:
        """
        Sayfadaki linkleri rastgele takip eder ve navigasyon hatalarını kontrol eder.

        Args:
            page: Playwright Page nesnesi
            max_pages: En fazla kaç sayfa ziyaret edilecek
            depth_limit: Maksimum navigasyon derinliği

        Returns:
            Dict[str, Any]: Navigasyon test sonuçları
        """
        result = {
            'pages_visited': 0,
            'links_followed': 0,
            'error_pages': [],
            'broken_links': [],
            'errors': [],
            'duration': 0,
            'navigation_map': {}
        }

        start_time = time.time()
        self.visited_pages = set()
        self.error_pages = []

        try:
            initial_url = page.url
            self.visited_pages.add(initial_url)

            await self._fuzz_navigate_recursive(page, initial_url, max_pages, depth_limit, result)

            result['pages_visited'] = len(self.visited_pages)
            result['error_pages'] = self.error_pages
            result['duration'] = time.time() - start_time

            self.logger.info(f"Navigasyon fuzzing tamamlandı: {result['pages_visited']} sayfa ziyaret edildi")

        except Exception as e:
            result['errors'].append(f"Genel navigasyon hatası: {str(e)}")
            self.logger.error(f"Navigasyon fuzzing hatası: {e}")

        return result

    async def _fuzz_navigate_recursive(self, page: Page, current_url: str, max_pages: int,
                                      depth_limit: int, result: Dict) -> None:
        """
        Recursive olarak linkleri takip eder.

        Args:
            page: Playwright Page nesnesi
            current_url: Şu anki sayfa URL'si
            max_pages: Maksimum sayfa sayısı
            depth_limit: Maksimum derinlik
            result: Sonuç dictionary'si
        """
        if len(self.visited_pages) >= max_pages or self.navigation_depth >= depth_limit:
            return

        try:
            # Status kodunu kontrol et
            try:
                status_check = await page.evaluate('() => performance.navigation.type')
            except:
                pass

            # Sayfadaki linkleri bul
            links = await page.query_selector_all('a[href]')

            if not links:
                return

            import random
            if links:
                # Rastgele bir link seç
                link = random.choice(links)
                href = await link.get_attribute('href')

                if not href or href.startswith('#') or href.startswith('javascript:'):
                    return

                # URL'yi normalize et
                try:
                    if href.startswith('http'):
                        new_url = href
                    else:
                        new_url = page.url.rstrip('/') + '/' + href.lstrip('/')
                except:
                    new_url = href

                # Zaten ziyaret edilen sayfa mı kontrol et
                if new_url in self.visited_pages:
                    return

                self.visited_pages.add(new_url)
                self.navigation_depth += 1

                try:
                    # Link'e git
                    await page.goto(new_url, wait_until='domcontentloaded', timeout=10000)
                    result['links_followed'] += 1

                    # Hata sayfası mı kontrol et
                    status = await page.evaluate('() => window.location.href')
                    if '404' in status or '500' in status or 'error' in status.lower():
                        self.error_pages.append(new_url)
                        result['error_pages'].append(new_url)

                    # Recursive call
                    await self._fuzz_navigate_recursive(page, new_url, max_pages, depth_limit, result)

                except Exception as e:
                    result['broken_links'].append({'url': new_url, 'error': str(e)})
                    self.logger.debug(f"Link navigasyon hatası: {new_url} - {e}")

                finally:
                    self.navigation_depth -= 1

        except Exception as e:
            self.logger.error(f"Recursive navigasyon hatası: {e}")


class ConsoleErrorCollector:
    """
    Sayfada çıkan console hata, uyarı ve log mesajlarını toplayan modül.
    """

    def __init__(self):
        """ConsoleErrorCollector'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.console_messages: List[Dict[str, Any]] = []
        self.page_errors: List[Dict[str, Any]] = []

    async def setup_collector(self, page: Page) -> None:
        """
        Console message listener'ını sayfaya ekler.

        Args:
            page: Playwright Page nesnesi
        """
        try:
            async def on_console_message(msg):
                """Console mesajı handler"""
                severity = self._map_console_type(msg.type)
                self.console_messages.append({
                    'type': msg.type,
                    'severity': severity,
                    'message': msg.text,
                    'location': msg.location,
                    'timestamp': datetime.now().isoformat()
                })
                if severity == 'error':
                    self.logger.error(f"Console Error: {msg.text}")
                elif severity == 'warning':
                    self.logger.warning(f"Console Warning: {msg.text}")

            page.on('console', on_console_message)
            self.logger.info("Console error collector setup tamamlandı")

        except Exception as e:
            self.logger.error(f"Console collector setup hatası: {e}")

    async def setup_page_error_collector(self, page: Page) -> None:
        """
        Page error listener'ını sayfaya ekler.

        Args:
            page: Playwright Page nesnesi
        """
        try:
            async def on_page_error(error):
                """Sayfa hata handler"""
                self.page_errors.append({
                    'error': str(error),
                    'type': type(error).__name__,
                    'timestamp': datetime.now().isoformat()
                })
                self.logger.error(f"Page Error: {error}")

            page.on('pageerror', on_page_error)
            self.logger.info("Page error collector setup tamamlandı")

        except Exception as e:
            self.logger.error(f"Page error collector setup hatası: {e}")

    def _map_console_type(self, msg_type: str) -> str:
        """
        Console mesaj tipini severity seviyesine mapping yapır.

        Args:
            msg_type: Console mesaj tipi

        Returns:
            str: Severity seviyesi
        """
        type_map = {
            'log': 'info',
            'info': 'info',
            'warning': 'warning',
            'warn': 'warning',
            'error': 'error',
            'debug': 'debug'
        }
        return type_map.get(msg_type.lower(), 'info')

    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Tüm hataları döndürür.

        Returns:
            List[Dict[str, Any]]: Hata mesajları
        """
        errors = [m for m in self.console_messages if m['severity'] == 'error']
        errors.extend(self.page_errors)
        return errors

    def get_warnings(self) -> List[Dict[str, Any]]:
        """
        Tüm uyarıları döndürür.

        Returns:
            List[Dict[str, Any]]: Uyarı mesajları
        """
        return [m for m in self.console_messages if m['severity'] == 'warning']

    def get_all(self) -> Dict[str, Any]:
        """
        Tüm toplanan mesajları döndürür.

        Returns:
            Dict[str, Any]: Tüm mesajlar
        """
        return {
            'console_messages': self.console_messages,
            'page_errors': self.page_errors,
            'total_errors': len(self.get_errors()),
            'total_warnings': len(self.get_warnings())
        }

    def clear(self) -> None:
        """Tüm toplanan mesajları temizler"""
        self.console_messages = []
        self.page_errors = []
        self.logger.info("Error collector verisi temizlendi")


class BrokenLinkChecker:
    """
    Sayfadaki linkleri kontrol ederek broken link'leri bulan modül.
    HTTP status kodlarını ve yanıt sürelerini analiz eder.
    """

    def __init__(self):
        """BrokenLinkChecker'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.checked_links: List[LinkCheckResult] = []

    async def check_links(self, page: Page, timeout: int = 10000) -> Dict[str, Any]:
        """
        Sayfadaki tüm linkleri kontrol eder.

        Args:
            page: Playwright Page nesnesi
            timeout: İstek timeout süresi (ms)

        Returns:
            Dict[str, Any]: Link kontrol sonuçları
        """
        result = {
            'total_links': 0,
            'internal_links': 0,
            'external_links': 0,
            'broken_links': [],
            'working_links': [],
            'slow_links': [],
            'errors': [],
            'duration': 0
        }

        start_time = time.time()
        self.checked_links = []

        try:
            # Sayfadaki tüm linkleri bul
            links = await page.query_selector_all('a[href]')
            result['total_links'] = len(links)

            base_domain = self._extract_domain(page.url)
            link_urls = set()

            # Link URL'lerini topla
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    if href and not href.startswith('#') and not href.startswith('javascript:'):
                        link_urls.add(href)
                except Exception as e:
                    self.logger.debug(f"Link attribute okuma hatası: {e}")

            # Her link'i kontrol et
            for url in link_urls:
                try:
                    check_result = await self._check_single_link(page, url, base_domain, timeout)
                    self.checked_links.append(check_result)

                    if check_result.is_broken:
                        result['broken_links'].append({
                            'url': url,
                            'status_code': check_result.status_code,
                            'error': check_result.error
                        })
                    else:
                        result['working_links'].append(url)

                    if check_result.is_internal:
                        result['internal_links'] += 1
                    else:
                        result['external_links'] += 1

                    if check_result.response_time and check_result.response_time > 3:
                        result['slow_links'].append({
                            'url': url,
                            'response_time': check_result.response_time
                        })

                except Exception as e:
                    result['errors'].append(f"Link kontrol hatası: {url} - {str(e)}")

            result['duration'] = time.time() - start_time
            self.logger.info(f"Link kontrol tamamlandı: {len(result['working_links'])} çalışan, "
                           f"{len(result['broken_links'])} broken link bulundu")

        except Exception as e:
            result['errors'].append(f"Genel link kontrol hatası: {str(e)}")
            self.logger.error(f"Link kontrol hatası: {e}")

        return result

    async def _check_single_link(self, page: Page, url: str, base_domain: str,
                                timeout: int) -> LinkCheckResult:
        """
        Tek bir link'i kontrol eder.

        Args:
            page: Playwright Page nesnesi
            url: Kontrol edilecek URL
            base_domain: Temel domain
            timeout: Timeout süresi

        Returns:
            LinkCheckResult: Link kontrol sonucu
        """
        try:
            # URL'yi normalize et
            if url.startswith('http'):
                full_url = url
            elif url.startswith('/'):
                full_url = f"{base_domain}{url}"
            else:
                full_url = f"{base_domain}/{url}"

            # Link'in internal/external olduğunu belirle
            is_internal = self._extract_domain(full_url) == base_domain

            start_time = time.time()

            try:
                # Sayfada navigate et ve status kodunu kontrol et
                response = await page.goto(full_url, wait_until='networkidle', timeout=timeout)
                response_time = time.time() - start_time

                status_code = response.status if response else None
                is_broken = status_code and status_code >= 400

                return LinkCheckResult(
                    url=url,
                    status_code=status_code,
                    is_internal=is_internal,
                    is_broken=is_broken,
                    response_time=response_time
                )

            except asyncio.TimeoutError:
                return LinkCheckResult(
                    url=url,
                    status_code=None,
                    is_internal=is_internal,
                    is_broken=True,
                    error="Timeout"
                )

        except Exception as e:
            return LinkCheckResult(
                url=url,
                status_code=None,
                is_internal=True,
                is_broken=True,
                error=str(e)
            )

    def _extract_domain(self, url: str) -> str:
        """
        URL'den domain'i çıkartır.

        Args:
            url: Tam URL

        Returns:
            str: Domain URL'si
        """
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except:
            return url


class NetworkAnalyzer:
    """
    Sayfa yükleme sırasında network request'lerini analiz eden modül.
    Failed request'ler, yavaş request'ler ve büyük response'ları tespit eder.
    """

    def __init__(self):
        """NetworkAnalyzer'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.requests: List[Dict[str, Any]] = []
        self.responses: List[Dict[str, Any]] = []
        self.failed_requests: List[Dict[str, Any]] = []

    async def setup_network_monitor(self, page: Page) -> None:
        """
        Network monitoring listener'larını kurar.

        Args:
            page: Playwright Page nesnesi
        """
        try:
            async def on_request(request):
                """Request handler"""
                self.requests.append({
                    'url': request.url,
                    'method': request.method,
                    'timestamp': datetime.now().isoformat(),
                    'resource_type': request.resource_type
                })

            async def on_response(response):
                """Response handler"""
                response_info = {
                    'url': response.url,
                    'status': response.status,
                    'timestamp': datetime.now().isoformat()
                }

                try:
                    response_info['size'] = len(await response.body())
                except:
                    response_info['size'] = None

                self.responses.append(response_info)

            async def on_request_failed(request):
                """Failed request handler"""
                self.failed_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'failure': str(request.failure) if request.failure else 'Unknown',
                    'timestamp': datetime.now().isoformat()
                })

            page.on('request', on_request)
            page.on('response', on_response)
            page.on('requestfailed', on_request_failed)

            self.logger.info("Network monitoring kuruludu")

        except Exception as e:
            self.logger.error(f"Network monitoring setup hatası: {e}")

    def get_failed_requests(self) -> List[Dict[str, Any]]:
        """
        Failed request'leri döndürür.

        Returns:
            List[Dict[str, Any]]: Failed request'ler
        """
        return self.failed_requests

    def get_slow_requests(self, threshold: float = 3.0) -> List[Dict[str, Any]]:
        """
        Yavaş request'leri döndürür.

        Args:
            threshold: Threshold süresi (saniye)

        Returns:
            List[Dict[str, Any]]: Yavaş request'ler
        """
        # Bu basit bir implementasyon, timestamps kullanarak hesaplanabilir
        return []

    def get_summary(self) -> Dict[str, Any]:
        """
        Network analiz özetini döndürür.

        Returns:
            Dict[str, Any]: Özet istatistikler
        """
        total_size = sum(r.get('size', 0) or 0 for r in self.responses)
        large_responses = [r for r in self.responses if r.get('size', 0) and r['size'] > 1_000_000]

        return {
            'total_requests': len(self.requests),
            'total_responses': len(self.responses),
            'failed_requests': len(self.failed_requests),
            'total_response_size_bytes': total_size,
            'large_responses': len(large_responses),
            'request_types': self._count_request_types(),
            'status_codes': self._count_status_codes()
        }

    def _count_request_types(self) -> Dict[str, int]:
        """Request tiplerini sayar"""
        types = {}
        for req in self.requests:
            rtype = req.get('resource_type', 'unknown')
            types[rtype] = types.get(rtype, 0) + 1
        return types

    def _count_status_codes(self) -> Dict[int, int]:
        """Status kodlarını sayar"""
        codes = {}
        for resp in self.responses:
            status = resp.get('status', 0)
            codes[status] = codes.get(status, 0) + 1
        return codes


class MemoryLeakDetector:
    """
    Sayfada bellek sızıntısını tespit eden modül.
    Tekrarlı aksiyonlar yaparak heap size değişikliğini izler.
    """

    def __init__(self):
        """MemoryLeakDetector'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.snapshots: List[Dict[str, Any]] = []

    async def take_snapshot(self, page: Page, label: str) -> Dict[str, Any]:
        """
        Anında JavaScript heap size'ını ölçer.

        Args:
            page: Playwright Page nesnesi
            label: Snapshot etiketi

        Returns:
            Dict[str, Any]: Memory snapshot verileri
        """
        try:
            memory_info = await page.evaluate('''
                () => {
                    if (performance.memory) {
                        return {
                            jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
                            totalJSHeapSize: performance.memory.totalJSHeapSize,
                            usedJSHeapSize: performance.memory.usedJSHeapSize,
                            timestamp: new Date().toISOString()
                        };
                    }
                    return null;
                }
            ''')

            if memory_info:
                snapshot = {
                    'label': label,
                    'timestamp': datetime.now().isoformat(),
                    'js_heap_size_limit': memory_info['jsHeapSizeLimit'],
                    'total_js_heap_size': memory_info['totalJSHeapSize'],
                    'used_js_heap_size': memory_info['usedJSHeapSize']
                }
                self.snapshots.append(snapshot)
                self.logger.info(f"Memory snapshot alındı ({label}): "
                               f"{memory_info['usedJSHeapSize'] / 1_000_000:.2f} MB")
                return snapshot

            return {}

        except Exception as e:
            self.logger.warning(f"Memory snapshot hatası: {e}")
            return {}

    async def detect_leaks(self, page: Page, action_count: int = 50,
                          threshold_mb: float = 10.0) -> Dict[str, Any]:
        """
        Tekrarlı aksiyonlar yaparak bellek sızıntısını tespit eder.

        Args:
            page: Playwright Page nesnesi
            action_count: Kaç kez aksiyons yapılacak
            threshold_mb: Bellek büyüme threshold'u (MB)

        Returns:
            Dict[str, Any]: Leak detection sonuçları
        """
        result = {
            'action_count': action_count,
            'memory_growth_mb': 0,
            'potential_leak': False,
            'snapshots': []
        }

        try:
            # İlk snapshot
            await self.take_snapshot(page, 'Initial')
            initial_snapshot = self.snapshots[-1]

            # Tekrarlı aksiyonlar
            for i in range(action_count):
                try:
                    # Scroll aksiyonu
                    await page.evaluate('window.scrollBy(0, 1000)')
                    await asyncio.sleep(0.1)
                    await page.evaluate('window.scrollBy(0, -1000)')

                except Exception as e:
                    self.logger.debug(f"Aksiyonlar sırasında hata: {e}")

            # Son snapshot
            await self.take_snapshot(page, 'Final')
            final_snapshot = self.snapshots[-1]

            # Bellek büyümesini hesapla
            memory_growth = (final_snapshot['used_js_heap_size'] -
                           initial_snapshot['used_js_heap_size']) / 1_000_000

            result['memory_growth_mb'] = memory_growth
            result['snapshots'] = [initial_snapshot, final_snapshot]

            if memory_growth > threshold_mb:
                result['potential_leak'] = True
                self.logger.warning(f"Potansiyel bellek sızıntısı: {memory_growth:.2f} MB büyüme")
            else:
                self.logger.info(f"Bellek büyümesi normal: {memory_growth:.2f} MB")

        except Exception as e:
            result['errors'] = [str(e)]
            self.logger.error(f"Leak detection hatası: {e}")

        return result


class ScreenshotOnError:
    """
    Hata meydana geldiğinde otomatik olarak screenshot alan modül.
    """

    def __init__(self):
        """ScreenshotOnError'ı başlat"""
        self.logger = logging.getLogger(__name__)
        self.captured_screenshots: List[str] = []

    async def capture(self, page: Page, error_type: str, error_message: str,
                     output_dir: str) -> Dict[str, Any]:
        """
        Hata anında screenshot alır ve kaydeder.

        Args:
            page: Playwright Page nesnesi
            error_type: Hata tipi
            error_message: Hata mesajı
            output_dir: Çıktı dizini

        Returns:
            Dict[str, Any]: Screenshot bilgileri
        """
        result = {
            'success': False,
            'file_path': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Output dizinini oluştur
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Dosya adını oluştur
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"error_{error_type}_{timestamp}.png"
            file_path = output_path / filename

            # Full page screenshot al
            await page.screenshot(path=str(file_path), full_page=True)

            self.captured_screenshots.append(str(file_path))
            result['success'] = True
            result['file_path'] = str(file_path)

            self.logger.info(f"Screenshot alındı: {file_path} ({error_type}: {error_message})")

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Screenshot alma hatası: {e}")

        return result


class MonkeyTester:
    """
    Tüm monkey testing modüllerini koordine eden ana orkestratör sınıfı.
    Belirlenen konfigürasyona göre test'leri çalıştırır ve sonuçları toplar.
    """

    def __init__(self):
        """MonkeyTester'ı başlat"""
        self.logger = logging.getLogger(__name__)

        # Alt modülleri başlat
        self.random_clicker = RandomClicker()
        self.form_fuzzer = FormFuzzer()
        self.scroll_stresser = ScrollStresser()
        self.resize_stresser = ResizeStresser()
        self.navigation_fuzzer = NavigationFuzzer()
        self.console_collector = ConsoleErrorCollector()
        self.link_checker = BrokenLinkChecker()
        self.network_analyzer = NetworkAnalyzer()
        self.memory_detector = MemoryLeakDetector()
        self.screenshot_on_error = ScreenshotOnError()

        self.results: List[MonkeyTestResult] = []
        self.start_time = None
        self.end_time = None

    async def run_full_test(self, url: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Tüm monkey test'lerini tam konfigürasyon ile çalıştırır.

        Args:
            url: Test edilecek URL
            config: Test konfigürasyonu (opsiyonel)

        Returns:
            Dict[str, Any]: Tüm test sonuçları
        """
        if config is None:
            config = self._get_default_config()

        self.start_time = time.time()
        self.results = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=config.get('headless', True))
                context = await browser.new_context()
                page = await context.new_page()

                try:
                    # Sayfaya git
                    self.logger.info(f"Sayfaya navigating: {url}")
                    await page.goto(url, wait_until='networkidle', timeout=30000)

                    # Collector'ları setup et
                    await self.console_collector.setup_collector(page)
                    await self.console_collector.setup_page_error_collector(page)
                    await self.network_analyzer.setup_network_monitor(page)

                    # Test'leri çalıştır
                    if config.get('run_random_clicker', True):
                        await self._run_random_clicker_test(page, config)

                    if config.get('run_form_fuzzer', True):
                        await self._run_form_fuzzer_test(page, config)

                    if config.get('run_scroll_stresser', True):
                        await self._run_scroll_stresser_test(page, config)

                    if config.get('run_resize_stresser', True):
                        await self._run_resize_stresser_test(page, config)

                    if config.get('run_navigation_fuzzer', True):
                        await self._run_navigation_fuzzer_test(page, config)

                    if config.get('run_link_checker', True):
                        await self._run_link_checker_test(page, config)

                    if config.get('run_memory_detector', True):
                        await self._run_memory_detector_test(page, config)

                    # Final results'ı topla
                    final_result = self._aggregate_results(url, config)

                except Exception as e:
                    self.logger.error(f"Test çalıştırma hatası: {e}")
                    await self.screenshot_on_error.capture(page, 'test_error', str(e),
                                                          config.get('output_dir', '/tmp'))

                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            self.logger.error(f"Browser setup hatası: {e}")
            raise

        self.end_time = time.time()
        return self._aggregate_results(url, config)

    async def _run_random_clicker_test(self, page: Page, config: Dict) -> None:
        """Random clicker test'ini çalıştırır"""
        test_start = time.time()
        errors = []

        try:
            iterations = config.get('clicker_iterations', 10)
            for i in range(iterations):
                try:
                    result = await self.random_clicker.click_random_element(page)
                    if not result.success and result.error:
                        errors.append(result.error)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    errors.append(str(e))

            self.results.append(MonkeyTestResult(
                test_type='RandomClicker',
                status='completed',
                duration=time.time() - test_start,
                errors=errors,
                details={'clicks_made': self.random_clicker.click_count}
            ))

        except Exception as e:
            self.results.append(MonkeyTestResult(
                test_type='RandomClicker',
                status='failed',
                duration=time.time() - test_start,
                errors=[str(e)]
            ))

    async def _run_form_fuzzer_test(self, page: Page, config: Dict) -> None:
        """Form fuzzer test'ini çalıştırır"""
        test_start = time.time()

        try:
            results = await self.form_fuzzer.fuzz_forms(page)

            self.results.append(MonkeyTestResult(
                test_type='FormFuzzer',
                status='completed',
                duration=time.time() - test_start,
                details={
                    'forms_fuzzed': len(results),
                    'total_inputs_fuzzed': sum(r.inputs_fuzzed for r in results),
                    'selects_fuzzed': sum(r.selects_fuzzed for r in results)
                }
            ))

        except Exception as e:
            self.results.append(MonkeyTestResult(
                test_type='FormFuzzer',
                status='failed',
                duration=time.time() - test_start,
                errors=[str(e)]
            ))

    async def _run_scroll_stresser_test(self, page: Page, config: Dict) -> None:
        """Scroll stresser test'ini çalıştırır"""
        test_start = time.time()

        try:
            iterations = config.get('scroll_iterations', 50)
            result = await self.scroll_stresser.stress_scroll(page, iterations)

            self.results.append(MonkeyTestResult(
                test_type='ScrollStresser',
                status='completed',
                duration=time.time() - test_start,
                warnings=result.get('console_errors', []),
                details=result
            ))

        except Exception as e:
            self.results.append(MonkeyTestResult(
                test_type='ScrollStresser',
                status='failed',
                duration=time.time() - test_start,
                errors=[str(e)]
            ))

    async def _run_resize_stresser_test(self, page: Page, config: Dict) -> None:
        """Resize stresser test'ini çalıştırır"""
        test_start = time.time()

        try:
            result = await self.resize_stresser.stress_resize(page)

            self.results.append(MonkeyTestResult(
                test_type='ResizeStresser',
                status='completed',
                duration=time.time() - test_start,
                warnings=result.get('layout_issues', []),
                errors=result.get('overflow_issues', []),
                details=result
            ))

        except Exception as e:
            self.results.append(MonkeyTestResult(
                test_type='ResizeStresser',
                status='failed',
                duration=time.time() - test_start,
                errors=[str(e)]
            ))

    async def _run_navigation_fuzzer_test(self, page: Page, config: Dict) -> None:
        """Navigation fuzzer test'ini çalıştırır"""
        test_start = time.time()

        try:
            result = await self.navigation_fuzzer.fuzz_navigation(page)

            self.results.append(MonkeyTestResult(
                test_type='NavigationFuzzer',
                status='completed',
                duration=time.time() - test_start,
                errors=result.get('broken_links', []),
                details=result
            ))

        except Exception as e:
            self.results.append(MonkeyTestResult(
                test_type='NavigationFuzzer',
                status='failed',
                duration=time.time() - test_start,
                errors=[str(e)]
            ))

    async def _run_link_checker_test(self, page: Page, config: Dict) -> None:
        """Link checker test'ini çalıştırır"""
        test_start = time.time()

        try:
            result = await self.link_checker.check_links(page)

            self.results.append(MonkeyTestResult(
                test_type='BrokenLinkChecker',
                status='completed',
                duration=time.time() - test_start,
                errors=result.get('broken_links', []),
                details=result
            ))

        except Exception as e:
            self.results.append(MonkeyTestResult(
                test_type='BrokenLinkChecker',
                status='failed',
                duration=time.time() - test_start,
                errors=[str(e)]
            ))

    async def _run_memory_detector_test(self, page: Page, config: Dict) -> None:
        """Memory detector test'ini çalıştırır"""
        test_start = time.time()

        try:
            result = await self.memory_detector.detect_leaks(page)

            status_msg = 'failed' if result.get('potential_leak') else 'completed'
            errors = ['Potansiyel bellek sızıntısı tespit edildi'] if result.get('potential_leak') else []

            self.results.append(MonkeyTestResult(
                test_type='MemoryLeakDetector',
                status=status_msg,
                duration=time.time() - test_start,
                errors=errors,
                details=result
            ))

        except Exception as e:
            self.results.append(MonkeyTestResult(
                test_type='MemoryLeakDetector',
                status='failed',
                duration=time.time() - test_start,
                errors=[str(e)]
            ))

    def _aggregate_results(self, url: str, config: Dict) -> Dict[str, Any]:
        """
        Tüm sonuçları bir araya getirir.

        Args:
            url: Test edilen URL
            config: Test konfigürasyonu

        Returns:
            Dict[str, Any]: Aggregated results
        """
        total_duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        console_errors = self.console_collector.get_errors()
        network_summary = self.network_analyzer.get_summary()

        return {
            'test_url': url,
            'timestamp': datetime.now().isoformat(),
            'total_duration_seconds': total_duration,
            'test_results': [asdict(r) for r in self.results],
            'console_errors': console_errors,
            'network_summary': network_summary,
            'failed_tests': [r for r in self.results if r.status == 'failed'],
            'completed_tests': [r for r in self.results if r.status == 'completed'],
            'total_errors': sum(len(r.errors) for r in self.results),
            'total_warnings': sum(len(r.warnings) for r in self.results)
        }

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Varsayılan test konfigürasyonunu döndürür.

        Returns:
            Dict[str, Any]: Varsayılan konfigürasyon
        """
        return {
            'headless': True,
            'output_dir': '/tmp/monkey_test_results',
            'run_random_clicker': True,
            'run_form_fuzzer': True,
            'run_scroll_stresser': True,
            'run_resize_stresser': True,
            'run_navigation_fuzzer': True,
            'run_link_checker': True,
            'run_memory_detector': True,
            'clicker_iterations': 10,
            'scroll_iterations': 50,
            'form_max_forms': 10,
            'navigation_max_pages': 20
        }
