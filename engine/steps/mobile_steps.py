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


# ── Scroll ─────────────────────────────────────────────────────────────────


@when(parsers.parse('"{selector}" görünür olana kadar aşağı kaydırılır'))
def scroll_until_visible(scenario_context, selector: str) -> None:
    _log("scroll_until_visible", selector)
    scenario_context.setdefault("_mobile_steps", []).append(("scroll_until_visible", selector))


# ── Zoom ───────────────────────────────────────────────────────────────────


@when(parsers.parse('"{selector}" üzerinde yakınlaştırma yapılır'))
def pinch_zoom_in(scenario_context, selector: str) -> None:
    _log("pinch_zoom", selector)
    scenario_context.setdefault("_mobile_steps", []).append(("pinch_zoom", selector))


# ── Rotate ─────────────────────────────────────────────────────────────────


@when(parsers.parse('cihaz "{orientation}" konumuna döndürülür'))
def rotate_device(scenario_context, orientation: str) -> None:
    _log("rotate_device", orientation)
    scenario_context.setdefault("_mobile_steps", []).append(("rotate_device", orientation))


# ── Hardware key ───────────────────────────────────────────────────────────


@when(parsers.parse('"{key}" donanım tuşuna basılır'))
def press_hardware_key(scenario_context, key: str) -> None:
    _log("press_hardware_key", key)
    scenario_context.setdefault("_mobile_steps", []).append(("press_hardware_key", key))


# ── App install ────────────────────────────────────────────────────────────


@given(parsers.parse('"{app_path}" uygulaması cihaza yüklenir'))
def install_app(scenario_context, app_path: str) -> None:
    _log("install_app", app_path)
    scenario_context.setdefault("_mobile_steps", []).append(("install_app", app_path))


# ── Network ────────────────────────────────────────────────────────────────


@when(parsers.parse('ağ modu "{mode}" olarak ayarlanır'))
def set_network_mode(scenario_context, mode: str) -> None:
    _log("set_network_mode", mode)
    scenario_context.setdefault("_mobile_steps", []).append(("set_network_mode", mode))


# ── Permissions ────────────────────────────────────────────────────────────


@when(parsers.parse('"{permission}" izni verilir'))
def grant_permission(scenario_context, permission: str) -> None:
    _log("grant_permission", permission)
    scenario_context.setdefault("_mobile_steps", []).append(("grant_permission", permission))


# ── WebView ────────────────────────────────────────────────────────────────


@when(parsers.parse('"{context_name}" web görünümüne geçilir'))
def switch_to_webview(scenario_context, context_name: str) -> None:
    _log("switch_to_webview", context_name)
    scenario_context.setdefault("_mobile_steps", []).append(("switch_to_webview", context_name))


# ── Screenshot ─────────────────────────────────────────────────────────────


@then(parsers.parse('"{label}" ismiyle ekran görüntüsü alınır'))
def take_mobile_screenshot(scenario_context, label: str) -> None:
    _log("take_mobile_screenshot", label)
    scenario_context.setdefault("_mobile_steps", []).append(("take_mobile_screenshot", label))
