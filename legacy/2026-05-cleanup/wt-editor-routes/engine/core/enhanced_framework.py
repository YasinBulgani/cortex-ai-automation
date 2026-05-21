"""
Enhanced Playwright/Pytest Framework
=====================================
Mavi Yaka test altyapısı için geliştirilmiş temel sınıflar:
- PageObjectBase: tüm POM'lar için base class
- PlaywrightTestRunner: paralel çalıştırma, retry
- TestDataManager: JSON tabanlı test verisi yönetimi
- ScreenshotManager: otomatik screenshot
- VideoRecorder: test video kaydı (Playwright trace)
- ReportIntegrator: Allure + HTML rapor
"""
from __future__ import annotations

import json
import os
import time
import threading
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# ── Opsiyonel bağımlılıklar ────────────────────────────────────────────────
try:
    from playwright.sync_api import (
        sync_playwright, Page, BrowserContext, Browser, Playwright,
        TimeoutError as PlaywrightTimeoutError,
    )
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from config.settings import settings

logger = logging.getLogger(__name__)

# Desteklenen Mavi Yaka domain'leri ve base URL şablonu
NEXUSQA_DOMAINS = {
    "ark":         "https://ark.example.com",
    "ghz":         "https://ghz.example.com",
    "girit":       "https://girit.example.com",
    "hrnexusqa":  "https://hr.nexusqa.com",
    "pex":         "https://pex.example.com",
    "plus":        "https://plus.example.com",
}


# ──────────────────────────────────────────────────────────────────────────────
# Veri Sınıfları
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class TestResult:
    """Tek bir test çalıştırmasının sonucu."""
    test_name: str
    status: str = "pending"     # pending | running | passed | failed | error | skipped
    duration_ms: float = 0.0
    error: str = ""
    screenshots: list[str] = field(default_factory=list)
    trace_path: str = ""
    steps: list[dict] = field(default_factory=list)
    retry_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
            "screenshots": self.screenshots,
            "trace_path": self.trace_path,
            "steps": self.steps,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class TestSuiteResult:
    """Bir test suite çalıştırmasının toplu sonucu."""
    suite_name: str
    results: list[TestResult] = field(default_factory=list)
    started_at: str = ""
    ended_at: str = ""
    report_path: str = ""

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status in ("failed", "error"))

    @property
    def pass_rate(self) -> float:
        return round(self.passed / self.total * 100, 2) if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "suite_name": self.suite_name,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "report_path": self.report_path,
            "results": [r.to_dict() for r in self.results],
        }


# ──────────────────────────────────────────────────────────────────────────────
# Screenshot Yöneticisi
# ──────────────────────────────────────────────────────────────────────────────
class ScreenshotManager:
    """
    Test adımlarında otomatik screenshot alma ve yönetimi.
    Her screenshot zaman damgalı ve test adına göre organize edilir.
    """

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else settings.SCREENSHOTS_DIR / "test_steps"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}

    def take(
        self,
        page: "Page",
        test_name: str,
        step_name: str = "",
        full_page: bool = False,
    ) -> str:
        """
        Screenshot alır ve dosyaya kaydeder.

        Returns:
            Screenshot dosyasının yolu
        """
        if not HAS_PLAYWRIGHT:
            return ""
        with self._lock:
            idx = self._counters.get(test_name, 0) + 1
            self._counters[test_name] = idx

        safe_test = re.sub(r"[^a-z0-9_]", "_", test_name.lower())
        safe_step = re.sub(r"[^a-z0-9_]", "_", step_name.lower()) if step_name else f"step_{idx:03d}"
        ts = datetime.now().strftime("%H%M%S")

        test_dir = self.base_dir / safe_test
        test_dir.mkdir(exist_ok=True)

        path = test_dir / f"{idx:03d}_{safe_step}_{ts}.png"
        try:
            page.screenshot(path=str(path), full_page=full_page)
            return str(path)
        except Exception as exc:
            logger.warning("Screenshot alınamadı: %s", exc)
            return ""

    def on_failure(self, page: "Page", test_name: str) -> str:
        """Hata anında tam sayfa screenshot alır."""
        return self.take(page, test_name, "FAILURE", full_page=True)

    def cleanup_test(self, test_name: str) -> None:
        """Test'e ait geçici screenshot'ları temizler."""
        safe = re.sub(r"[^a-z0-9_]", "_", test_name.lower())
        test_dir = self.base_dir / safe
        if test_dir.exists():
            import shutil
            shutil.rmtree(str(test_dir))
        self._counters.pop(test_name, None)


import re  # ScreenshotManager içinde kullanılan re burada da gerekli


# ──────────────────────────────────────────────────────────────────────────────
# Video/Trace Kaydedici
# ──────────────────────────────────────────────────────────────────────────────
class VideoRecorder:
    """
    Playwright trace ile test video kaydı.
    Context oluşturulurken trace başlatılır, test sonunda kaydedilir.
    """

    def __init__(self, traces_dir: Path | str | None = None):
        self.traces_dir = Path(traces_dir) if traces_dir else (
            settings.BASE_DIR / "traces"
        )
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def start_trace(self, context: "BrowserContext", test_name: str) -> None:
        """Trace kaydını başlatır."""
        if not HAS_PLAYWRIGHT:
            return
        try:
            context.tracing.start(
                screenshots=True,
                snapshots=True,
                sources=True,
                title=test_name,
            )
            logger.debug("Trace başlatıldı: %s", test_name)
        except Exception as exc:
            logger.warning("Trace başlatılamadı: %s", exc)

    def stop_trace(self, context: "BrowserContext", test_name: str) -> str:
        """Trace kaydını durdurur ve dosyaya kaydeder."""
        if not HAS_PLAYWRIGHT:
            return ""
        safe = re.sub(r"[^a-z0-9_]", "_", test_name.lower())
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.traces_dir / f"{safe}_{ts}.zip"
        try:
            context.tracing.stop(path=str(path))
            logger.info("Trace kaydedildi: %s", path)
            return str(path)
        except Exception as exc:
            logger.warning("Trace kaydedilemedi: %s", exc)
            return ""


# ──────────────────────────────────────────────────────────────────────────────
# Page Object Base Sınıfı
# ──────────────────────────────────────────────────────────────────────────────
class PageObjectBase:
    """
    Tüm Mavi Yaka POM sınıfları için temel sınıf.
    Ortak yardımcı metodları ve screenshot entegrasyonunu sağlar.
    """

    URL: str = ""

    def __init__(self, page: "Page", screenshot_manager: ScreenshotManager | None = None):
        """
        Args:
            page:               Playwright Page nesnesi
            screenshot_manager: Adım başına screenshot için (opsiyonel)
        """
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright yüklü değil: pip install playwright && playwright install")
        self.page      = page
        self._ss_mgr   = screenshot_manager
        self._test_name = self.__class__.__name__

    # ── Navigasyon ───────────────────────────────────────────────────────────
    def navigate(self, url: str | None = None) -> "PageObjectBase":
        """Sayfaya gider."""
        target = url or self.URL
        self.page.goto(target)
        self._screenshot(f"navigate_{re.sub(r'[^a-z0-9]', '_', target.lower())[:30]}")
        return self

    def reload(self) -> "PageObjectBase":
        """Sayfayı yeniler."""
        self.page.reload()
        return self

    # ── Bekleme ───────────────────────────────────────────────────────────────
    def wait_for(self, selector: str, state: str = "visible", timeout: int = 10_000) -> "PageObjectBase":
        """Elementi bekler."""
        self.page.wait_for_selector(selector, state=state, timeout=timeout)
        return self

    def wait_for_url(self, url_pattern: str, timeout: int = 10_000) -> "PageObjectBase":
        """URL değişimini bekler."""
        self.page.wait_for_url(url_pattern, timeout=timeout)
        return self

    def sleep(self, ms: int) -> "PageObjectBase":
        """Belirtilen süre bekler (tercihen wait_for kullanın)."""
        self.page.wait_for_timeout(ms)
        return self

    # ── Etkileşim ─────────────────────────────────────────────────────────────
    def click(self, selector: str, step_name: str = "") -> "PageObjectBase":
        """Elemente tıklar."""
        self.page.click(selector)
        self._screenshot(step_name or f"click_{selector[:20]}")
        return self

    def fill(self, selector: str, value: str, step_name: str = "") -> "PageObjectBase":
        """Input alanını doldurur."""
        self.page.fill(selector, value)
        self._screenshot(step_name or f"fill_{selector[:20]}")
        return self

    def select(self, selector: str, value: str) -> "PageObjectBase":
        """Select kutusundan seçer."""
        self.page.select_option(selector, value)
        return self

    def press(self, selector: str, key: str) -> "PageObjectBase":
        """Tuşa basar."""
        self.page.press(selector, key)
        return self

    def hover(self, selector: str) -> "PageObjectBase":
        """Elementin üzerine gelir."""
        self.page.hover(selector)
        return self

    # ── Doğrulama ─────────────────────────────────────────────────────────────
    def assert_text(self, selector: str, expected: str) -> "PageObjectBase":
        """Metin içeriğini doğrular."""
        actual = self.page.inner_text(selector)
        assert expected in actual, f"Metin beklentisi hatası: '{expected}' ≠ '{actual}'"
        return self

    def assert_visible(self, selector: str) -> "PageObjectBase":
        """Elementin görünür olduğunu doğrular."""
        assert self.page.is_visible(selector), f"Element görünür değil: {selector}"
        return self

    def assert_url_contains(self, fragment: str) -> "PageObjectBase":
        """URL'nin belirtilen metni içerdiğini doğrular."""
        current = self.page.url
        assert fragment in current, f"URL '{fragment}' içermiyor: {current}"
        return self

    # ── Screenshot ────────────────────────────────────────────────────────────
    def screenshot(self, step_name: str = "", full_page: bool = False) -> str:
        """Manuel screenshot alır."""
        return self._screenshot(step_name, full_page)

    def _screenshot(self, step_name: str = "", full_page: bool = False) -> str:
        if self._ss_mgr:
            return self._ss_mgr.take(self.page, self._test_name, step_name, full_page)
        return ""

    # ── Yardımcılar ──────────────────────────────────────────────────────────
    def get_text(self, selector: str) -> str:
        """Element metin içeriğini döner."""
        return self.page.inner_text(selector)

    def is_visible(self, selector: str) -> bool:
        """Element görünür mü?"""
        return self.page.is_visible(selector)

    def get_url(self) -> str:
        """Güncel URL'yi döner."""
        return self.page.url


# ──────────────────────────────────────────────────────────────────────────────
# Test Verisi Yöneticisi
# ──────────────────────────────────────────────────────────────────────────────
class TestDataManager:
    """
    JSON tabanlı test verisi yönetimi.
    Mavi Yaka domain yapısıyla uyumlu hiyerarşik veri depolama.

    Veri yapısı::

        test_data/
        ├── common.json          # Tüm domainlerde kullanılan veriler
        ├── ark/
        │   ├── users.json
        │   └── test_cases.json
        └── ghz/
            └── users.json
    """

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else settings.BASE_DIR / "test_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict] = {}

    # ── Okuma ─────────────────────────────────────────────────────────────────
    def get(self, key: str, domain: str = "common", default: Any = None) -> Any:
        """
        Test verisini döner.

        Args:
            key:    Veri anahtarı (nokta notasyonu: "users.admin.password")
            domain: Domain adı veya "common"
            default: Veri yoksa döndürülecek değer

        Returns:
            İstenen veri veya default değer
        """
        data = self._load_domain(domain)
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    def get_all(self, domain: str) -> dict:
        """Domain'e ait tüm test verisini döner."""
        return self._load_domain(domain)

    def get_user(self, role: str = "admin", domain: str = "common") -> dict | None:
        """Kullanıcı verisi döner."""
        return self.get(f"users.{role}", domain)

    def get_domain_config(self, domain: str) -> dict:
        """Domain konfigürasyonunu döner."""
        base_url = NEXUSQA_DOMAINS.get(domain, "")
        cfg = self.get("config", domain) or {}
        return {"domain": domain, "base_url": base_url, **cfg}

    # ── Yazma ─────────────────────────────────────────────────────────────────
    def set(self, key: str, value: Any, domain: str = "common") -> None:
        """Test verisini kaydeder."""
        data = self._load_domain(domain)
        parts = key.split(".")
        current = data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
        self._save_domain(domain, data)
        logger.debug("Test verisi güncellendi: %s.%s", domain, key)

    # ── Dosya I/O ─────────────────────────────────────────────────────────────
    def _domain_path(self, domain: str) -> Path:
        if domain == "common":
            return self.data_dir / "common.json"
        return self.data_dir / domain / "data.json"

    def _load_domain(self, domain: str) -> dict:
        cache_key = domain
        if cache_key in self._cache:
            return self._cache[cache_key]
        path = self._domain_path(domain)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._cache[cache_key] = data
                return data
            except Exception as exc:
                logger.warning("Test verisi okunamadı [%s]: %s", path, exc)
        return {}

    def _save_domain(self, domain: str, data: dict) -> None:
        path = self._domain_path(domain)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self._cache[domain] = data

    def initialize_domain(self, domain: str, template: dict | None = None) -> None:
        """Domain için temel veri şablonu oluşturur."""
        if template is None:
            base_url = NEXUSQA_DOMAINS.get(domain, "")
            template = {
                "config": {
                    "base_url": base_url,
                    "timeout": 30000,
                    "retry_count": 2,
                },
                "users": {
                    "admin": {"username": "admin", "password": "Admin123!", "role": "admin"},
                    "user":  {"username": "user1", "password": "User123!",  "role": "user"},
                },
                "test_data": {},
            }
        self._save_domain(domain, template)
        logger.info("Domain veri şablonu oluşturuldu: %s", domain)


# ──────────────────────────────────────────────────────────────────────────────
# Playwright Test Runner
# ──────────────────────────────────────────────────────────────────────────────
class PlaywrightTestRunner:
    """
    Playwright testlerini paralel çalıştırma ve retry mekanizması.
    ThreadPoolExecutor ile paralel test yürütme destekler.
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        max_workers: int = 4,
        retry_count: int = 2,
        timeout: int = 30_000,
        screenshot_manager: ScreenshotManager | None = None,
        video_recorder: VideoRecorder | None = None,
    ):
        """
        Args:
            browser_type:       Playwright tarayıcı tipi
            headless:           Headless mod
            max_workers:        Paralel thread sayısı
            retry_count:        Başarısız testler için tekrar sayısı
            timeout:            Default timeout (ms)
            screenshot_manager: Adım screenshot'ları için
            video_recorder:     Trace/video kaydı için
        """
        self.browser_type       = browser_type
        self.headless           = headless
        self.max_workers        = max_workers
        self.retry_count        = retry_count
        self.timeout            = timeout
        self.screenshot_manager = screenshot_manager or ScreenshotManager()
        self.video_recorder     = video_recorder or VideoRecorder()

    # ── Tek Test Çalıştır ─────────────────────────────────────────────────────
    def run_single(
        self,
        test_fn: Callable[["Page"], None],
        test_name: str,
        base_url: str = "",
        record_trace: bool = False,
    ) -> TestResult:
        """
        Tek bir testi çalıştırır, retry mekanizmasıyla.

        Args:
            test_fn:      (page) → None şeklinde test fonksiyonu
            test_name:    Test adı
            base_url:     Başlangıç URL (opsiyonel)
            record_trace: Trace kaydı aktif mi

        Returns:
            TestResult nesnesi
        """
        if not HAS_PLAYWRIGHT:
            return TestResult(
                test_name=test_name,
                status="error",
                error="Playwright yüklü değil",
            )

        result = TestResult(test_name=test_name)
        last_error = ""

        for attempt in range(self.retry_count + 1):
            result.retry_count = attempt
            result.status = "running"
            start_time = time.time()

            with sync_playwright() as pw:
                launcher = getattr(pw, self.browser_type)
                browser: "Browser" = launcher.launch(headless=self.headless)
                ctx: "BrowserContext" = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    locale="tr-TR",
                )
                ctx.set_default_timeout(self.timeout)

                if record_trace:
                    self.video_recorder.start_trace(ctx, test_name)

                page = ctx.new_page()
                if base_url:
                    page.goto(base_url)

                try:
                    test_fn(page)
                    result.status = "passed"
                    last_error = ""
                    break  # Başarılı → döngüden çık

                except Exception as exc:
                    last_error = str(exc)
                    logger.warning(
                        "Test başarısız [%s] (deneme %d/%d): %s",
                        test_name, attempt + 1, self.retry_count + 1, exc,
                    )
                    # Hata screenshot'u al
                    ss_path = self.screenshot_manager.on_failure(page, test_name)
                    if ss_path:
                        result.screenshots.append(ss_path)

                    if attempt == self.retry_count:
                        result.status = "failed"

                finally:
                    if record_trace:
                        trace_path = self.video_recorder.stop_trace(ctx, test_name)
                        if trace_path:
                            result.trace_path = trace_path
                    elapsed = (time.time() - start_time) * 1000
                    result.duration_ms = elapsed
                    ctx.close()
                    browser.close()

            if result.status == "passed":
                break
            if attempt < self.retry_count:
                time.sleep(1)  # Retry öncesi kısa bekleme

        result.error = last_error
        return result

    # ── Paralel Suite Çalıştır ────────────────────────────────────────────────
    def run_suite(
        self,
        test_cases: list[dict],
        suite_name: str = "Test Suite",
        parallel: bool = True,
        record_trace: bool = False,
    ) -> TestSuiteResult:
        """
        Birden fazla testi çalıştırır (paralel veya sıralı).

        Args:
            test_cases: Her biri {test_fn, test_name, base_url?, ...} içeren liste
            suite_name: Suite adı
            parallel:   True ise paralel çalıştır
            record_trace: Trace kaydı

        Returns:
            TestSuiteResult nesnesi
        """
        suite = TestSuiteResult(
            suite_name=suite_name,
            started_at=datetime.now().isoformat(),
        )

        if parallel and len(test_cases) > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self.run_single,
                        case["test_fn"],
                        case["test_name"],
                        case.get("base_url", ""),
                        record_trace,
                    ): case
                    for case in test_cases
                }
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    except Exception as exc:
                        case = futures[future]
                        result = TestResult(
                            test_name=case.get("test_name", "unknown"),
                            status="error",
                            error=str(exc),
                        )
                    suite.results.append(result)
        else:
            for case in test_cases:
                result = self.run_single(
                    case["test_fn"],
                    case["test_name"],
                    case.get("base_url", ""),
                    record_trace,
                )
                suite.results.append(result)

        suite.ended_at = datetime.now().isoformat()
        return suite

    # ── pytest entegrasyonu ───────────────────────────────────────────────────
    def run_pytest(
        self,
        test_path: str,
        allure_results_dir: str | None = None,
        extra_args: list[str] | None = None,
    ) -> dict:
        """
        pytest komutunu subprocess olarak çalıştırır.

        Args:
            test_path:          Pytest dosyası/dizini yolu
            allure_results_dir: Allure sonuç dizini
            extra_args:         Ekstra pytest argümanları

        Returns:
            {returncode, stdout, stderr}
        """
        cmd = ["python", "-m", "pytest", test_path, "-v", "--tb=short"]
        if allure_results_dir:
            cmd += ["--alluredir", allure_results_dir]
        if extra_args:
            cmd += extra_args

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "passed": proc.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": "Timeout", "passed": False}
        except Exception as exc:
            return {"returncode": -1, "stdout": "", "stderr": str(exc), "passed": False}


# ──────────────────────────────────────────────────────────────────────────────
# Rapor Entegratörü
# ──────────────────────────────────────────────────────────────────────────────
class ReportIntegrator:
    """
    TestSuiteResult'tan Allure JSON + HTML rapor üretir.
    """

    def __init__(self, reports_dir: Path | str | None = None):
        self.reports_dir = Path(reports_dir) if reports_dir else settings.REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    # ── HTML Rapor ────────────────────────────────────────────────────────────
    def generate_html(
        self,
        suite: TestSuiteResult,
        output_path: Path | str | None = None,
    ) -> str:
        """TestSuiteResult'tan HTML rapor üretir."""
        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.reports_dir / f"suite_report_{ts}.html"
        output_path = Path(output_path)

        rows = ""
        for r in suite.results:
            status_cls = "pass" if r.status == "passed" else "fail"
            status_lbl = {"passed": "GEÇTİ", "failed": "KALDI", "error": "HATA",
                          "skipped": "ATLANDI"}.get(r.status, r.status.upper())
            duration = f"{r.duration_ms:.0f}ms"
            error_cell = f'<span title="{r.error}">{r.error[:80]}...</span>' if len(r.error) > 80 else r.error
            retry_cell = f"×{r.retry_count}" if r.retry_count else ""
            trace_cell = (
                f'<a href="{r.trace_path}" target="_blank">Trace</a>'
                if r.trace_path else ""
            )
            rows += f"""
            <tr>
              <td>{r.test_name}</td>
              <td><span class="badge {status_cls}">{status_lbl}</span></td>
              <td>{duration}</td>
              <td style="color:#f87171">{error_cell}</td>
              <td style="color:#94a3b8">{retry_cell}</td>
              <td>{trace_cell}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Test Suite Raporu — {suite.suite_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }}
  header {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 24px 32px; }}
  header h1 {{ font-size: 1.4rem; color: #f8fafc; }}
  header p  {{ color: #94a3b8; font-size: 0.85rem; margin-top: 4px; }}
  .stats {{ display: flex; gap: 14px; padding: 20px 32px; }}
  .stat {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px;
           padding: 14px 22px; flex: 1; text-align: center; }}
  .stat .num {{ font-size: 1.8rem; font-weight: 700; }}
  .stat .lbl {{ color: #94a3b8; font-size: 0.72rem; margin-top: 4px; }}
  .passed-s .num {{ color: #22c55e; }}
  .failed-s .num {{ color: #ef4444; }}
  .total-s  .num {{ color: #60a5fa; }}
  .pct-s    .num {{ color: #a78bfa; }}
  table {{ width: calc(100% - 64px); margin: 0 32px 32px; border-collapse: collapse; }}
  th, td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid #1e293b; font-size: 0.84rem; }}
  th {{ background: #1e293b; color: #94a3b8; font-weight: 600; }}
  tr:hover td {{ background: #182030; }}
  .badge {{ padding: 2px 9px; border-radius: 99px; font-size: 0.72rem; font-weight: 600; }}
  .badge.pass {{ background: #14532d; color: #86efac; }}
  .badge.fail {{ background: #450a0a; color: #fca5a5; }}
  a {{ color: #7dd3fc; text-decoration: none; }}
  footer {{ text-align: center; padding: 20px; color: #475569; font-size: 0.8rem; }}
</style>
</head>
<body>
<header>
  <h1>🤖 Test Suite Raporu — {suite.suite_name}</h1>
  <p>Başlangıç: {suite.started_at} &nbsp;|&nbsp; Bitiş: {suite.ended_at}</p>
</header>
<div class="stats">
  <div class="stat total-s"><div class="num">{suite.total}</div><div class="lbl">TOPLAM</div></div>
  <div class="stat passed-s"><div class="num">{suite.passed}</div><div class="lbl">GEÇTİ</div></div>
  <div class="stat failed-s"><div class="num">{suite.failed}</div><div class="lbl">KALDI</div></div>
  <div class="stat pct-s"><div class="num">{suite.pass_rate}%</div><div class="lbl">BAŞARI</div></div>
</div>
<table>
  <thead>
    <tr><th>Test Adı</th><th>Durum</th><th>Süre</th><th>Hata</th><th>Retry</th><th>Trace</th></tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<footer>Mavi Yaka Enhanced Framework &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')}</footer>
</body>
</html>"""

        output_path.write_text(html, encoding="utf-8")
        logger.info("Suite raporu üretildi: %s", output_path)
        return str(output_path)

    # ── Allure JSON ───────────────────────────────────────────────────────────
    def write_allure_results(
        self,
        suite: TestSuiteResult,
        allure_dir: Path | str | None = None,
    ) -> list[str]:
        """
        Her test sonucu için Allure uyumlu JSON dosyası üretir.

        Returns:
            Üretilen dosya yolları listesi
        """
        allure_dir = Path(allure_dir) if allure_dir else settings.ALLURE_RESULTS_DIR
        allure_dir.mkdir(parents=True, exist_ok=True)
        files = []

        for r in suite.results:
            ts_ms = int(datetime.fromisoformat(r.timestamp).timestamp() * 1000)
            status = {"passed": "passed", "failed": "failed",
                      "error": "broken", "skipped": "skipped"}.get(r.status, "unknown")
            allure_data = {
                "uuid": f"{r.test_name}_{r.timestamp}".replace(":", "-"),
                "name": r.test_name,
                "status": status,
                "start": ts_ms,
                "stop": ts_ms + int(r.duration_ms),
                "labels": [
                    {"name": "suite", "value": suite.suite_name},
                    {"name": "framework", "value": "NexusQA Enhanced"},
                ],
                "attachments": [
                    {"name": Path(ss).name, "source": ss, "type": "image/png"}
                    for ss in r.screenshots
                ],
            }
            if r.error:
                allure_data["statusDetails"] = {"message": r.error, "trace": ""}

            fname = f"{r.test_name.replace(' ', '_')}_{r.timestamp}.json".replace(":", "-")
            fpath = allure_dir / fname
            fpath.write_text(json.dumps(allure_data, indent=2, ensure_ascii=False), encoding="utf-8")
            files.append(str(fpath))

        logger.info("%d Allure sonucu yazıldı: %s", len(files), allure_dir)
        return files
