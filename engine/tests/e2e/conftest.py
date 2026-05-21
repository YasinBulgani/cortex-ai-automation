"""
tests/e2e/conftest.py — E2E test master conftest.

Playwright tarayıcı, sayfa, POM ve test verisi fixture'ları sağlar.
Session-scoped tarayıcı, function-scoped sayfa ile her test izole çalışır.
Hata durumunda otomatik screenshot ve trace kaydeder.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Generator

import socket

import allure
import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# ── BDD Step Keşfi — Tüm step modüllerini yükle ─────────────────────────────
# pytest-bdd v7'de @given/@when/@then dekoratörleri, fixture'ları çağıran
# modülün yerel ad alanına (caller module locals) enjekte eder. Bu nedenle
# "import steps.xyz" yeterli DEĞİLDİR — fixture'ların conftest.py'nin
# namespace'ine taşınması için "from steps.xyz import *" kullanılmalıdır.
# Böylece pytest tüm step fixture'larını bu conftest üzerinden keşfeder ve
# tüm e2e testleri için Background adımları dahil tüm adımlar erişilebilir olur.
try:
    from steps.common_steps import *  # noqa: F401,F403
    from steps.bgts_login_steps import *  # noqa: F401,F403 — login step fixture'ları
    from steps.bgts_project_steps import *  # noqa: F401,F403
    from steps.bgts_scenario_steps import *  # noqa: F401,F403
    from steps.bgts_approval_steps import *  # noqa: F401,F403
    from steps.bgts_import_steps import *  # noqa: F401,F403
    from steps.bgts_regression_steps import *  # noqa: F401,F403
    from steps.bgts_synthetic_steps import *  # noqa: F401,F403
    from steps.bgts_smoke_steps import *  # noqa: F401,F403
except ImportError as _step_import_err:
    logger.debug("Step modülü yüklenemedi (opsiyonel): %s", _step_import_err)


def _is_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """TCP bağlantısı kurulabilirse True döner."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# Frontend (localhost:3000) ayakta mı? Değilse browser E2E testleri skip edilir.
_FRONTEND_UP = _is_reachable("localhost", 3000)

from config.settings import settings
from config.test_config import test_config
from core.locator_manager import LocatorManager as _CoreLocatorManager
from locators.locator_manager import LocatorManager
from pages.login_page import LoginPage
from pages.dashboard_page import DashboardPage
from pages.projects_page import ProjectsPage
from pages.scenarios_page import ScenariosListPage, ScenarioFormPage
from pages.approvals_page import ApprovalsPage
from pages.import_page import ImportPage
from pages.common_nav import CommonNav
from test_data.fixtures import (
    get_admin_user,
    get_test_projects,
    get_test_scenarios,
    load_test_data,
)


# ── Allure Ortam Bilgisi ─────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    """Marker kayıt, Allure ortam bilgisi ve locator yükleme."""
    config.addinivalue_line("markers", "e2e: Uçtan uca (E2E) testler")
    config.addinivalue_line("markers", "functional: Fonksiyonel testler")
    config.addinivalue_line("markers", "needs_frontend: Frontend (localhost:3000) gerektirir")


_API_ONLY_MODULES = {"test_api_bdd.py", "test_api_integration.py"}


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Frontend çalışmıyorsa browser E2E testlerini skip et."""
    if _FRONTEND_UP:
        return
    skip = pytest.mark.skip(reason="Frontend localhost:3000 erişilemez — browser E2E testleri atlandı")
    for item in items:
        if "page" in getattr(item, "fixturenames", []) or item.get_closest_marker("needs_frontend"):
            item.add_marker(skip)
            continue
        # pytest-bdd @scenario testleri page'i step tanımları üzerinden inject eder;
        # bu nedenle fixturenames'de görünmez. e2e dizinindeki API-dışı tüm BDD
        # testlerini frontend yokken skip et.
        if (
            hasattr(item, "fspath")
            and "tests/e2e" in str(item.fspath)
            and Path(str(item.fspath)).name not in _API_ONLY_MODULES
        ):
            item.add_marker(skip)

    allure_dir = Path(test_config.ALLURE_RESULTS_DIR)
    allure_dir.mkdir(parents=True, exist_ok=True)

    env_props = allure_dir / "environment.properties"
    env_props.write_text(
        f"BASE_URL={test_config.BASE_URL}\n"
        f"API_URL={test_config.API_URL}\n"
        f"BROWSER={test_config.BROWSER}\n"
        f"HEADLESS={test_config.HEADLESS}\n"
        f"ENVIRONMENT={os.getenv('TEST_ENV', 'test')}\n"
        f"TIMESTAMP={datetime.now().isoformat()}\n",
        encoding="utf-8",
    )

    _CoreLocatorManager.configure(settings.LOCATORS_DIR)
    _CoreLocatorManager.load_all()


# ── Playwright Tarayıcı (session-scoped) ─────────────────────────────────────

@pytest.fixture(scope="session")
def playwright_instance() -> Generator[Playwright, None, None]:
    """Tek bir Playwright süreci başlat."""
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Generator[Browser, None, None]:
    """Session-scoped tarayıcı. Tüm testler aynı tarayıcıyı paylaşır."""
    launcher = getattr(playwright_instance, test_config.BROWSER)
    _browser = launcher.launch(headless=test_config.HEADLESS)
    yield _browser
    _browser.close()


# ── Sayfa (function-scoped) ──────────────────────────────────────────────────

@pytest.fixture(scope="function")
def context(browser: Browser, request: pytest.FixtureRequest) -> Generator[BrowserContext, None, None]:
    """Her test için temiz browser context — trace desteği ile."""
    ctx = browser.new_context(
        viewport={
            "width": test_config.VIEWPORT_WIDTH,
            "height": test_config.VIEWPORT_HEIGHT,
        },
        base_url=test_config.BASE_URL,
    )
    ctx.set_default_timeout(test_config.DEFAULT_TIMEOUT)
    ctx.set_default_navigation_timeout(test_config.NAVIGATION_TIMEOUT)

    if test_config.TRACE_ON_FAILURE:
        ctx.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield ctx

    if test_config.TRACE_ON_FAILURE and request.node.rep_call and request.node.rep_call.failed:
        trace_path = (
            test_config.TRACES_DIR
            / f"{request.node.nodeid.replace('/', '_').replace('::', '__')}.zip"
        )
        try:
            ctx.tracing.stop(path=str(trace_path))
            allure.attach.file(
                str(trace_path),
                name="Playwright Trace",
                attachment_type=allure.attachment_type.TEXT,
            )
        except Exception as exc:
            logger.debug("Trace zip eklenemedi: %s", exc)
    else:
        try:
            ctx.tracing.stop()
        except Exception as exc:
            logger.debug("tracing.stop: %s", exc)

    ctx.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext, request: pytest.FixtureRequest) -> Generator[Page, None, None]:
    """Her test için yeni sayfa — hata durumunda screenshot alır."""
    _page = context.new_page()
    yield _page

    if (
        test_config.SCREENSHOT_ON_FAILURE
        and hasattr(request.node, "rep_call")
        and request.node.rep_call
        and request.node.rep_call.failed
    ):
        try:
            screenshot = _page.screenshot(full_page=True)
            allure.attach(
                screenshot,
                name="Hata Screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception as exc:
            logger.debug("Hata screenshot eklenemedi: %s", exc)

    _page.close()


# ── Pytest hook: test sonucu bilgisini fixture'a aktar ────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


# ── Giriş Yapılmış Oturum ───────────────────────────────────────────────────

@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Page:
    """
    API token injection ile kimlik doğrulanmış sayfa.

    global-setup.ts ile aynı yöntemi kullanır:
      1) httpx ile API'den access_token + refresh_token al
      2) Cookie'leri BrowserContext'e ekle (bgts_access_token, twai_session, bgts_refresh_token)
      3) /login sayfasına git ve localStorage'ı ayarla (tspm_access_token, onboarded …)
      4) /projects sayfasına yönlen ve URL'yi doğrula

    Login formuna dokunulmaz — Next.js hydration sorunlarını bypass eder.
    """
    import httpx
    from urllib.parse import urlparse

    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    # 1) API ile token al
    token = ""
    refresh_token = ""
    try:
        resp = httpx.post(
            f"{test_config.API_URL}/auth/login",
            json={"email": admin_email, "password": admin_password},
            timeout=10.0,
        )
        if resp.status_code == 429:
            pytest.skip("Rate limit — auth/login geçici olarak kilitli; test atlanıyor")
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token", "")
            refresh_token = data.get("refresh_token", "") or ""
    except Exception as exc:
        logger.debug("API token alınamadı: %s", exc)

    if not token:
        pytest.skip("Auth token alınamadı — authenticated_page fixture atlanıyor")

    # 2) Cookie'leri BrowserContext'e ekle
    parsed = urlparse(test_config.BASE_URL)
    domain = parsed.hostname or "localhost"
    secure = parsed.scheme == "https"
    cookie_base: dict = {
        "domain": domain,
        "path": "/",
        "sameSite": "Lax",
        "secure": secure,
    }
    cookies = [
        {**cookie_base, "name": "bgts_access_token", "value": token, "httpOnly": True},
        {**cookie_base, "name": "twai_session", "value": "1", "httpOnly": False},
    ]
    if refresh_token:
        cookies.append(
            {**cookie_base, "name": "bgts_refresh_token", "value": refresh_token, "httpOnly": True}
        )
    page.context.add_cookies(cookies)

    # 3) /login'e git (domcontentloaded) ve localStorage'ı ayarla
    try:
        page.goto(f"{test_config.BASE_URL}/login", wait_until="domcontentloaded", timeout=20_000)
    except Exception as exc:
        logger.debug("authenticated_page /login goto: %s", exc)
        page.goto(test_config.BASE_URL, wait_until="domcontentloaded", timeout=20_000)

    try:
        page.evaluate(
            """([accessToken, refreshToken]) => {
                localStorage.setItem('tspm_access_token', accessToken);
                localStorage.setItem('onboarded', 'true');
                localStorage.setItem('neurex_onboarding_done', String(Date.now()));
                if (refreshToken) {
                    localStorage.setItem('tspm_refresh_token', refreshToken);
                }
            }""",
            [token, refresh_token],
        )
    except Exception as exc:
        logger.debug("authenticated_page localStorage: %s", exc)

    # 4) /projects sayfasına git
    try:
        page.goto(f"{test_config.BASE_URL}/projects", wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_url("**/projects", timeout=15_000)
    except Exception as exc:
        logger.debug("authenticated_page /projects yönlendirme: %s", exc)

    return page


# ── LocatorManager ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def locator_manager() -> LocatorManager:
    """Merkezi locator yöneticisi."""
    return LocatorManager()


# ── POM Fixture'ları ─────────────────────────────────────────────────────────

@pytest.fixture()
def login_page(page: Page, locator_manager: LocatorManager) -> LoginPage:
    return LoginPage(page, locator_manager=locator_manager, base_url=test_config.BASE_URL)


@pytest.fixture(scope="session")
def e2e_project_id() -> str:
    """Test projesinin ID'si — env'den veya seeded değerden okunur."""
    return os.getenv("E2E_PROJECT_ID", "test-project")


@pytest.fixture(scope="session")
def seeded_project_id() -> str:
    """Gerçek proje ID'si — önce env'den okur, yoksa API'den alır.

    common_steps.navigate_to_project_sub ve navigate_to_project_dashboard
    için gerekli. 'test-project' gibi sahte ID'ler Next.js routing'de
    beklenmedik davranışlara yol açar; bu yüzden gerçek bir UUID kullanılır.
    """
    # 1. Ortam değişkeni varsa kullan (CI/CD için)
    env_id = os.getenv("E2E_PROJECT_ID", "")
    if env_id and env_id != "test-project":
        return env_id

    # 2. API'den ilk mevcut proje ID'sini çek
    try:
        import httpx as _httpx
        from config.test_config import test_config as _tc

        # Önce token al
        login_resp = _httpx.post(
            f"{_tc.API_URL}/auth/login",
            json={"email": os.getenv("ADMIN_EMAIL", "admin@example.com"),
                  "password": os.getenv("ADMIN_PASSWORD", "admin123")},
            timeout=8.0,
        )
        if login_resp.status_code == 200:
            token = login_resp.json().get("access_token", "")
            if token:
                proj_resp = _httpx.get(
                    f"{_tc.API_URL}/tspm/projects",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=8.0,
                )
                if proj_resp.status_code == 200:
                    projects = proj_resp.json()
                    if projects:
                        return projects[0]["id"]
    except Exception as exc:
        logger.debug("seeded_project_id API fetch failed: %s", exc)

    # 3. Fallback — CI ortamında proje oluşturulmuş olmalı
    return os.getenv("E2E_PROJECT_ID", "test-project")


@pytest.fixture()
def dashboard_page(
    authenticated_page: Page, locator_manager: LocatorManager, e2e_project_id: str
) -> DashboardPage:
    return DashboardPage(
        authenticated_page,
        project_id=e2e_project_id,
        locator_manager=locator_manager,
        base_url=test_config.BASE_URL,
    )


@pytest.fixture()
def projects_page(
    authenticated_page: Page, locator_manager: LocatorManager
) -> ProjectsPage:
    return ProjectsPage(
        authenticated_page,
        locator_manager=locator_manager,
        base_url=test_config.BASE_URL,
    )


@pytest.fixture()
def scenarios_page(
    authenticated_page: Page, locator_manager: LocatorManager, e2e_project_id: str
) -> ScenariosListPage:
    return ScenariosListPage(
        authenticated_page,
        project_id=e2e_project_id,
        locator_manager=locator_manager,
        base_url=test_config.BASE_URL,
    )


@pytest.fixture()
def scenario_form_page(
    authenticated_page: Page, locator_manager: LocatorManager, e2e_project_id: str
) -> ScenarioFormPage:
    return ScenarioFormPage(
        authenticated_page,
        project_id=e2e_project_id,
        locator_manager=locator_manager,
        base_url=test_config.BASE_URL,
    )


@pytest.fixture()
def approvals_page(
    authenticated_page: Page, locator_manager: LocatorManager, e2e_project_id: str
) -> ApprovalsPage:
    return ApprovalsPage(
        authenticated_page,
        project_id=e2e_project_id,
        locator_manager=locator_manager,
        base_url=test_config.BASE_URL,
    )


@pytest.fixture()
def import_page(
    authenticated_page: Page, locator_manager: LocatorManager, e2e_project_id: str
) -> ImportPage:
    return ImportPage(
        authenticated_page,
        project_id=e2e_project_id,
        locator_manager=locator_manager,
        base_url=test_config.BASE_URL,
    )


@pytest.fixture()
def common_nav(
    authenticated_page: Page, locator_manager: LocatorManager
) -> CommonNav:
    return CommonNav(
        authenticated_page,
        locator_manager=locator_manager,
        base_url=test_config.BASE_URL,
    )


# ── Test Verisi Fixture'ları ─────────────────────────────────────────────────

@pytest.fixture(scope="session")
def admin_user() -> dict:
    """Admin kullanıcı test verisi."""
    return get_admin_user()


@pytest.fixture(scope="session")
def test_projects() -> list[dict]:
    """Test projeleri listesi."""
    return get_test_projects()


@pytest.fixture(scope="session")
def test_scenarios() -> list[dict]:
    """Test senaryoları listesi."""
    return get_test_scenarios()


# ── Test Veri Tohumlama (session-scoped, autouse) ───────────────────────────

@pytest.fixture(scope="session", autouse=True)
def seed_test_data(seeded_project_id: str) -> None:
    """
    Her test oturumunun başında seeded_project_id'ye:
    - En az 5 test senaryosu
    - En az 10 onay kartı
    oluşturur. Zaten yeterli veri varsa işlem yapmaz.
    """
    import httpx as _httpx

    api_url = os.getenv("API_URL", "http://localhost:8000/api/v1")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    if seeded_project_id in ("test-project", ""):
        return  # Fallback değerle seed yapmaya çalışma

    try:
        login_resp = _httpx.post(
            f"{api_url}/auth/login",
            json={"email": admin_email, "password": admin_password},
            timeout=8.0,
        )
        if login_resp.status_code != 200:
            logger.debug("seed_test_data: auth başarısız — %s", login_resp.status_code)
            return
        token = login_resp.json().get("access_token", "")
        if not token:
            return
    except Exception as exc:
        logger.debug("seed_test_data: auth hatası — %s", exc)
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    pid = seeded_project_id

    # ── Senaryo tohumlama ──────────────────────────────────────────────────────
    try:
        scen_resp = _httpx.get(
            f"{api_url}/tspm/projects/{pid}/scenarios",
            headers=headers,
            timeout=8.0,
        )
        if scen_resp.status_code == 200:
            existing = scen_resp.json()
            count = len(existing) if isinstance(existing, list) else len(
                existing.get("items", existing.get("data", []))
            )
            needed = max(0, 5 - count)
            for i in range(needed):
                _httpx.post(
                    f"{api_url}/tspm/projects/{pid}/scenarios",
                    headers=headers,
                    json={"title": f"Seed Senaryo {i+1}", "description": f"Otomatik oluşturulmuş test senaryosu {i+1}"},
                    timeout=8.0,
                )
    except Exception as exc:
        logger.debug("seed_test_data: senaryo tohumlaması — %s", exc)

    # ── Onay kartı tohumlama ───────────────────────────────────────────────────
    try:
        apr_resp = _httpx.get(
            f"{api_url}/tspm/projects/{pid}/approvals",
            headers=headers,
            timeout=8.0,
        )
        if apr_resp.status_code == 200:
            existing_apr = apr_resp.json()
            count_apr = len(existing_apr) if isinstance(existing_apr, list) else len(
                existing_apr.get("items", existing_apr.get("data", []))
            )
            needed_apr = max(0, 10 - count_apr)
            for i in range(needed_apr):
                _httpx.post(
                    f"{api_url}/tspm/projects/{pid}/approvals",
                    headers=headers,
                    json={
                        "title": f"Seed Onay Kartı {i+1}",
                        "content": f"Test onay içeriği {i+1}",
                        "source_document": "Otomatik oluşturulmuş onay",
                        "status": "pending",
                    },
                    timeout=8.0,
                )
    except Exception as exc:
        logger.debug("seed_test_data: onay tohumlaması — %s", exc)


# ── AI Engine (opsiyonel — smoke testler için) ───────────────────────────────

@pytest.fixture(scope="session")
def ai_engine():
    """AI engine instance — OPENAI_API_KEY varsa yüklenir."""
    try:
        from core.ai_engine import AIEngine
        return AIEngine()
    except Exception as exc:
        logger.debug("AIEngine yüklenemedi (opsiyonel): %s", exc)
        return None


@pytest.fixture(scope="function")
def ai_results() -> dict:
    """AI aksiyon sonuçlarını adımlar arasında taşır."""
    return {"results": []}
