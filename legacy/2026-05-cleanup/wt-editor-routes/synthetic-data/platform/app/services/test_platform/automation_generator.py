"""
AutomationGenerator — Playwright / Selenium / Appium Kod Üretimi

Test case nesnelerinden framework'e özgü otomasyon kodu üretir.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List


class Framework(str, Enum):
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    APPIUM = "appium"
    REQUESTS = "requests"


@dataclass
class AutomationScript:
    test_case_id: str
    framework: Framework
    language: str          # python / javascript / java
    filename: str
    code: str
    dependencies: List[str]


class AutomationGenerator:
    """Test case'lerden otomasyon kodu üretir."""

    def generate(self, test_case, framework: Framework = Framework.PLAYWRIGHT, language: str = "python") -> AutomationScript:
        tc_id = getattr(test_case, "id", "TC-001")
        title = getattr(test_case, "title", "Test")
        steps = getattr(test_case, "steps", [])

        generators = {
            (Framework.PLAYWRIGHT, "python"): self._playwright_python,
            (Framework.SELENIUM, "python"): self._selenium_python,
            (Framework.APPIUM, "python"): self._appium_python,
            (Framework.REQUESTS, "python"): self._requests_python,
        }
        gen_fn = generators.get((framework, language), self._playwright_python)
        code, deps = gen_fn(tc_id, title, steps)

        return AutomationScript(
            test_case_id=tc_id,
            framework=framework,
            language=language,
            filename=f"test_{tc_id.lower().replace('-', '_')}.py",
            code=code,
            dependencies=deps,
        )

    def _playwright_python(self, tc_id, title, steps) -> tuple:
        step_code = "\n".join(
            f"    # Adım {s.step_number}: {s.action}\n    page.wait_for_timeout(500)"
            for s in steps
        ) or "    page.wait_for_timeout(1000)"

        code = f'''"""
{tc_id} — {title}
Playwright Python otomatik testi.
"""
import pytest
from playwright.sync_api import Page, expect


def test_{tc_id.lower().replace("-", "_")}(page: Page):
    """
    {title}
    """
    page.goto("http://localhost:3000")

{step_code}

    # Son doğrulama
    expect(page).to_have_title(lambda t: len(t) > 0)
'''
        return code, ["playwright", "pytest"]

    def _selenium_python(self, tc_id, title, steps) -> tuple:
        step_code = "\n".join(
            f"    # Adım {s.step_number}: {s.action}\n    time.sleep(0.5)"
            for s in steps
        ) or "    time.sleep(1)"

        code = f'''"""
{tc_id} — {title}
Selenium Python otomatik testi.
"""
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By


@pytest.fixture
def driver():
    d = webdriver.Chrome()
    yield d
    d.quit()


def test_{tc_id.lower().replace("-", "_")}(driver):
    driver.get("http://localhost:3000")

{step_code}

    assert driver.title != ""
'''
        return code, ["selenium", "pytest"]

    def _appium_python(self, tc_id, title, steps) -> tuple:
        code = f'''"""
{tc_id} — {title}
Appium Python mobil testi.
"""
import pytest
from appium import webdriver as appium_driver


DESIRED_CAPS = {{
    "platformName": "Android",
    "deviceName": "emulator-5554",
    "app": "/path/to/app.apk",
}}


@pytest.fixture
def driver():
    d = appium_driver.Remote("http://localhost:4723/wd/hub", DESIRED_CAPS)
    yield d
    d.quit()


def test_{tc_id.lower().replace("-", "_")}(driver):
    # {title}
    driver.implicitly_wait(5)
    # Adımlar buraya eklenecek
    assert driver.current_activity is not None
'''
        return code, ["Appium-Python-Client", "pytest"]

    def _requests_python(self, tc_id, title, steps) -> tuple:
        code = f'''"""
{tc_id} — {title}
Requests ile API testi.
"""
import requests
import pytest

BASE_URL = "http://localhost:8000"


def test_{tc_id.lower().replace("-", "_")}():
    # {title}
    response = requests.get(f"{{BASE_URL}}/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data is not None
'''
        return code, ["requests", "pytest"]

    # ── Public API (dict-based wrappers) ──────────────────────────────────

    def generate_playwright(self, test_case: dict) -> str:
        """
        Test case dict'inden Playwright (Python) kodu üret.

        Args:
            test_case: title, description, steps, expected_result içeren dict.

        Returns:
            Playwright test kodu string olarak.
        """
        class _TC:
            pass
        tc = _TC()
        tc.id = test_case.get("id", "TC-001")
        tc.title = test_case.get("title", "Test")
        steps_raw = test_case.get("steps", [])

        class _Step:
            pass

        steps = []
        for i, s in enumerate(steps_raw, start=1):
            step = _Step()
            step.step_number = i
            step.action = str(s)
            steps.append(step)
        tc.steps = steps

        script = self.generate(tc, Framework.PLAYWRIGHT, "python")
        return script.code

    def generate_selenium(self, test_case: dict) -> str:
        """
        Test case dict'inden Selenium (Python) kodu üret.

        Args:
            test_case: title, description, steps, expected_result içeren dict.

        Returns:
            Selenium test kodu string olarak.
        """
        class _TC:
            pass
        tc = _TC()
        tc.id = test_case.get("id", "TC-001")
        tc.title = test_case.get("title", "Test")
        steps_raw = test_case.get("steps", [])

        class _Step:
            pass

        steps = []
        for i, s in enumerate(steps_raw, start=1):
            step = _Step()
            step.step_number = i
            step.action = str(s)
            steps.append(step)
        tc.steps = steps

        script = self.generate(tc, Framework.SELENIUM, "python")
        return script.code
