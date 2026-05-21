"""Mobile DSL step tanımları — pytest-bdd tarafı.

Engine üzerinde Python'dan mobil Gherkin çalıştırmak için bir köprü.
Gerçek otomasyon motoru Playwright mobile emulation (TypeScript
`frameworks/playwright-cucumber-ts/steps/mobile-steps.ts`) tarafında
olduğu için burada basit bir **placeholder** katmanı tutuyoruz:

    * Adımlar senaryonun `scenario_context`'ine log düşer.
    * Gerçek cihaz koşumu Appium tabanlı ayrı bir PR'da ekleniyor.
    * TSPM `mobile-run` akışı şu anda zaten doğrudan Playwright runner
      çağırır; bu dosya adım eşleşmesi olduğunu DSL loader'a sinyallemek
      için var.

Bu dosya import edilmese bile `_dsl_catalog_bootstrap.py` YAML kataloğunu
loader'a aktarırken `source_file` referansını bu yola verir.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from pytest_bdd import given, parsers, then, when

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


def _log(ctx: str, msg: str) -> None:
    logger.info("[mobile:%s] %s", ctx, msg)


# ── Gesture ────────────────────────────────────────────────────────────────


@when(parsers.parse('kullanıcı "{selector}" üzerine dokunur'))
def tap_element(scenario_context, selector: str) -> None:
    _log("tap", selector)
    scenario_context.setdefault("_mobile_steps", []).append(("tap", selector))


@when(parsers.parse('kullanıcı "{direction}" yönünde kaydırır'))
def swipe_direction(scenario_context, direction: str) -> None:
    _log("swipe", direction)
    scenario_context.setdefault("_mobile_steps", []).append(("swipe", direction))


@when(parsers.parse('kullanıcı "{selector}" üzerine uzun basar'))
def long_press_element(scenario_context, selector: str) -> None:
    _log("long_press", selector)
    scenario_context.setdefault("_mobile_steps", []).append(("long_press", selector))


# ── App ────────────────────────────────────────────────────────────────────


@given(parsers.parse('"{package}" uygulaması açılır'))
def launch_app(scenario_context, package: str) -> None:
    _log("launch_app", package)
    scenario_context.setdefault("_mobile_steps", []).append(("launch_app", package))


# ── Nav ────────────────────────────────────────────────────────────────────


@when(parsers.parse("kullanıcı geri döner"))
def go_back(scenario_context) -> None:
    _log("go_back", "-")
    scenario_context.setdefault("_mobile_steps", []).append(("go_back", None))


# ── Assert ─────────────────────────────────────────────────────────────────


@then(parsers.parse('"{selector}" ekranda görünür'))
def assert_element_on_screen(scenario_context, selector: str) -> None:
    _log("assert_visible", selector)
    scenario_context.setdefault("_mobile_steps", []).append(
        ("assert_visible", selector)
    )
