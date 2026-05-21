"""
steps/conftest.py — BDD fixtures
pytest-bdd icin browser, page, AI engine, locator, data reader ve
multi-domain fixture'lari.
"""
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

import allure
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import base64
from config.settings import settings
from core.browser import BrowserEngine
from core.ai_engine import AIEngine
from core.locator_manager import LocatorManager
from core.data_reader import DataReader
from core.context import GlobalContext
from core.actions import Actions
from core.locator_bridge import get_bridge


# ── Allure Ortam Bilgisi + Locator/Data Yuklemesi ────────────────────────────
def pytest_configure(config):
    settings.REPORTS_DIR.mkdir(exist_ok=True)
    settings.SCREENSHOTS_DIR.mkdir(exist_ok=True)
    allure_dir = ROOT / "allure-results"
    allure_dir.mkdir(exist_ok=True)

    # Ortam yukleme (--env CLI parametresi veya TEST_ENV env var)
    env_name = os.getenv("TEST_ENV", "test")
    settings.load_environment(env_name)

    # Locator'lari toplu yukle
    LocatorManager.configure(settings.LOCATORS_DIR)
    LocatorManager.load_all()

    # Test verisini yukle
    domain = os.getenv("TEST_DOMAIN", settings.DOMAIN)
    DataReader.configure(settings.TESTDATA_DIR)
    DataReader.load(domain, env_name)


# ── BrowserEngine ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="function")
def browser_engine():
    # Mobil cihaz emülasyonu desteği: MOBILE_DEVICE_NAME env var ile aktifleşir
    device_profile = None
    device_name = os.getenv("MOBILE_DEVICE_NAME", "").strip()
    if device_name:
        try:
            from core.device_profiles import DEVICE_MAP, DEVICE_MAP_BY_NAME
            device_profile = DEVICE_MAP.get(device_name) or DEVICE_MAP_BY_NAME.get(device_name)
            if device_profile is None:
                logger.warning("MOBILE_DEVICE_NAME=%r tanımsız; masaüstü modunda devam ediliyor", device_name)
        except Exception as exc:
            logger.warning("device_profiles yüklenemedi: %s", exc)

    engine = BrowserEngine(device_profile=device_profile)
    engine.start()
    yield engine
    engine.stop()


@pytest.fixture(scope="function")
def page(browser_engine):
    """Hazir Playwright page — tum feature/step dosyalarinda kullanilabilir."""
    return browser_engine.page


# ── Actions ───────────────────────────────────────────────────────────────────
@pytest.fixture(scope="function")
def actions(page) -> Actions:
    """Playwright aksiyon sarmalayicisi."""
    return Actions(page)


# ── Locator Bridge ────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def locator_bridge():
    """Birlesik locator cozumleme koprusu (JSON + POM + DB)."""
    return get_bridge()


# ── Seeded Project (sabit proje ID yerine dinamik) ───────────────────────────
_seeded_project_cache: dict = {}


@pytest.fixture(scope="session")
def seeded_project_id():
    """
    Ilk cagrildiginda backend API uzerinden test projesi olusturur.
    Sonraki cagrilarda cache'lenmis ID'yi doner.
    Hard-coded 'test-project' yerine bunu kullanin.
    """
    if "id" in _seeded_project_cache:
        return _seeded_project_cache["id"]

    import httpx
    api_url = os.getenv("TWAI_API_URL", "http://127.0.0.1:8000")
    admin_email = os.getenv("TWAI_ADMIN_EMAIL", "admin@example.com")
    admin_pass = os.getenv("TWAI_ADMIN_PASSWORD", "admin123")

    try:
        with httpx.Client(base_url=api_url, timeout=15.0) as client:
            login_resp = client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_pass})
            if login_resp.status_code != 200:
                _seeded_project_cache["id"] = "test-project"
                return "test-project"

            token = login_resp.json().get("access_token", "")
            headers = {"Authorization": f"Bearer {token}"}

            create_resp = client.post(
                "/api/v1/tspm/projects",
                json={"name": "BDD Test Project", "description": "Otomatik olusturulan BDD test projesi"},
                headers=headers,
            )
            if create_resp.status_code == 201:
                pid = create_resp.json()["id"]
                _seeded_project_cache["id"] = pid
                return pid

            list_resp = client.get("/api/v1/tspm/projects", headers=headers)
            if list_resp.status_code == 200:
                projects = list_resp.json()
                if isinstance(projects, list) and projects:
                    pid = projects[0]["id"]
                    _seeded_project_cache["id"] = pid
                    return pid
    except Exception as exc:
        logger.debug("seeded_project_id API oluşturma atlandı, test-project kullanılacak: %s", exc)

    _seeded_project_cache["id"] = "test-project"
    return "test-project"


# ── Page Objects ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="function")
def login_page(page):
    from pages.login_page import LoginPage
    return LoginPage(page, base_url=settings.BASE_URL)

@pytest.fixture(scope="function")
def projects_page(page):
    from pages.projects_page import ProjectsPage
    return ProjectsPage(page, base_url=settings.BASE_URL)

@pytest.fixture(scope="function")
def locator_registry():
    from core.locator_registry import LocatorRegistry
    reg = LocatorRegistry()
    default_path = settings.BASE_DIR / "locators" / "default" / "bgts_locators.json"
    if default_path.exists():
        reg.load(default_path)
    reg.sync_from_db()
    return reg


# ── AI Engine ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def ai_engine():
    return AIEngine()


# ── AI aksiyon sonuclari — adimlar arasi paylasim ────────────────────────────
@pytest.fixture(scope="function")
def ai_results():
    """AI aksiyonlarinin sonuclarini adimlar arasinda tasir."""
    return {"results": []}


# ── Locator Yukleyici (Feature Bazli) ────────────────────────────────────────
@pytest.fixture(autouse=True)
def load_feature_locators(request):
    """
    Her feature calistirilmadan once ilgili locator JSON'unu yukler.
    Feature adi dosya adindan cikarilir (NexusQA Hooks.java pattern'i).
    """
    if hasattr(request, "node") and hasattr(request.node, "get_closest_marker"):
        fspath = getattr(request.node, "fspath", None)
        if fspath:
            feature_name = Path(str(fspath)).stem
            LocatorManager.load(feature_name)


# ── Data Reader Fixture ──────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def test_data() -> DataReader:
    """DataReader'a erismek icin fixture."""
    return DataReader


# ── GlobalContext Her Senaryo Sonrasi Temizle ────────────────────────────────
@pytest.fixture(autouse=True)
def clear_context_after_scenario():
    """NexusQA Hooks.tearDown pattern'i: her senaryo sonrasi context temizlenir."""
    yield
    GlobalContext.clear()


# ── Multi-domain Runner (NexusQA MultiDomainCucumberRunner port'u) ──────────
def pytest_generate_tests(metafunc):
    """
    Birden fazla domain varsa her testi her domain icin parametrize eder.
    TEST_DOMAINS env var'i virgullu liste kabul eder.

    Kullanim:
      TEST_DOMAINS=default,staging python -m pytest steps/ -v
    """
    domains = settings.DOMAINS
    if len(domains) > 1 and "domain" in metafunc.fixturenames:
        metafunc.parametrize("domain", domains, scope="session")


@pytest.fixture(scope="session")
def domain() -> str:
    """Aktif domain adi. Tek domain varsa settings'ten, birden fazlaysa parametrize'dan gelir."""
    return settings.DOMAIN


@pytest.fixture(autouse=True)
def reload_data_for_domain():
    """
    Multi-domain kosularinda her domain icin test verisini yeniden yukler.
    Domain degisikliginde DataReader otomatik reload eder.

    Allure raporunda domain bilgisi etiket olarak eklenir.
    """
    current_domain = os.getenv("TEST_DOMAIN", settings.DOMAIN)
    current_env = os.getenv("TEST_ENV", settings.ENVIRONMENT)

    if DataReader.current_domain() != current_domain:
        DataReader.reload(current_domain, current_env)
        settings.set_domain(current_domain)

    yield


# ── Allure: Her basarisiz test sonrasi screenshot ekle ───────────────────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        page_fixture = item.funcargs.get("page")
        if page_fixture is not None:
            try:
                screenshot = page_fixture.screenshot()
                allure.attach(
                    screenshot,
                    name="Basarisiz Test Screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception as exc:
                logger.debug("Allure ekran görüntüsü eklenemedi: %s", exc)

    # Allure'a domain etiketi ekle (NexusQA Hooks.setAllureDomainLabels port'u)
    if report.when == "call":
        domain_val = settings.DOMAIN
        if domain_val and domain_val != "default":
            allure.dynamic.label("domain", domain_val)
            allure.dynamic.label("parentSuite", domain_val)


# ── Canli Ekran (Virtual Device) Akisi ────────────────────────────────────────
def _send_live_screenshot(request):
    try:
        page = request.getfixturevalue("page")
        if page and not page.is_closed():
            screenshot_bytes = page.screenshot(type="jpeg", quality=50, scale="css")
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            print(f"__SCREENSHOT__:{b64}", flush=True)
    except Exception as exc:
        logger.debug("Canlı ekran görüntüsü atlandı: %s", exc)

def pytest_bdd_before_step(request, feature, scenario, step, step_func):
    _send_live_screenshot(request)

def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    _send_live_screenshot(request)


# ── Excel Rapor Entegrasyonu (NexusQA ExcelReportGenerator port'u) ──────────

_excel_reporter = None


def pytest_sessionstart(session):
    """Test oturumu basinda ExcelReporter baslatir."""
    global _excel_reporter
    try:
        from core.excel_reporter import ExcelReporter
        _excel_reporter = ExcelReporter(
            report_name=f"TestwrightAI_Test_{settings.DOMAIN}",
            domain=settings.DOMAIN,
        )
    except ImportError:
        logger.debug("ExcelReporter modülü yüklü değil, oturum raporu devre dışı")


def pytest_runtest_logreport(report):
    """Her test sonucunu ExcelReporter'a ekler."""
    if _excel_reporter is None:
        return
    if report.when != "call":
        return

    status = "passed" if report.passed else ("failed" if report.failed else "skipped")
    duration_ms = int(report.duration * 1000)
    error_msg = ""
    if report.failed and report.longreprtext:
        error_msg = report.longreprtext[:500]

    _excel_reporter.add_result(
        test_name=report.nodeid,
        status=status,
        duration_ms=duration_ms,
        error_message=error_msg,
        domain=settings.DOMAIN,
    )


def pytest_sessionfinish(session, exitstatus):
    """Test oturumu bitiminde Excel raporunu kaydeder."""
    if _excel_reporter is None:
        return
    if not _excel_reporter._results:
        return
    try:
        path = _excel_reporter.save()
        print(f"\n  Excel rapor olusturuldu: {path}")
    except Exception as exc:
        print(f"\n  Excel rapor olusturulamadi: {exc}")

