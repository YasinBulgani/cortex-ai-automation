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
def authenticated_page(page: Page, locator_manager: LocatorManager) -> Page:
    """Önceden giriş yapılmış sayfa. Credential'lar env'den okunur."""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    lm = locator_manager
    email_loc = lm.get_locator_with_fallback("login", "email_input")
    password_loc = lm.get_locator_with_fallback("login", "password_input")
    submit_loc = lm.get_locator_with_fallback("login", "submit_button")

    page.goto(f"{test_config.BASE_URL}/login", wait_until="domcontentloaded")
    page.locator(email_loc).fill(admin_email)
    page.locator(password_loc).fill(admin_password)
    page.locator(submit_loc).click()
    try:
        page.wait_for_url("**/projects", timeout=10_000)
    except Exception as exc:
        logger.debug("authenticated_page URL bekleme: %s", exc)
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
