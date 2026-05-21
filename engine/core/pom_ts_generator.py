"""
TypeScript Page Object Generator
=================================
RecordingEvent veya RecordingSession'dan Playwright TypeScript POM dosyası üretir.

E2E pages/ yapısıyla uyumlu çıktı üretir:
- BasePage extend eden class
- data-testid bazlı locator property'leri
- Action metotları (click, fill, etc.)
- Assertion metotları

Kullanım:
    from core.pom_ts_generator import POMTypeScriptGenerator
    gen = POMTypeScriptGenerator()
    code = gen.from_session(session)
    gen.save(code, "e2e/pages/my.page.ts")
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class POMTypeScriptGenerator:
    """Recording session'dan TypeScript Playwright Page Object üretir."""

    def from_session(self, session: dict, class_name: str = "") -> str:
        """
        RecordingSession dict'ten TypeScript POM kodu üretir.

        Args:
            session: RecordingSession.to_dict() veya uyumlu dict
            class_name: POM class adı (boşsa session.name'den üretilir)
        """
        name = session.get("name", "recording")
        cls = class_name or self._to_class_name(name)
        url = self._extract_url(session)
        elements = self._extract_elements(session)
        actions_list = session.get("actions", [])

        return self._render(cls, url, elements, actions_list, name)

    def from_events(self, events: list[dict], class_name: str = "GeneratedPage") -> str:
        """RecordingEvent listesinden TypeScript POM kodu üretir."""
        elements = self._extract_elements_from_events(events)
        url = ""
        for e in events:
            if e.get("action", {}).get("type") == "navigate":
                url = e.get("action", {}).get("value", "")
                break
            ctx_url = e.get("context", {}).get("url", "")
            if ctx_url and not url:
                url = ctx_url

        return self._render(class_name, url, elements, events, "generated")

    def from_locator_json(self, locator_data: dict, class_name: str = "LocatorPage") -> str:
        """Locator registry JSON'dan TypeScript POM kodu üretir."""
        elements: dict[str, dict] = {}
        for name, entry in locator_data.items():
            chain = entry.get("chain", [])
            primary = chain[0] if chain else {}
            elements[name] = {
                "selector": primary.get("value", ""),
                "type": primary.get("type", "css"),
                "element_type": entry.get("element_type", ""),
                "screen": entry.get("screen", ""),
            }

        return self._render_from_locators(class_name, elements)

    # ── Private ──────────────────────────────────────────────────────

    def _render(self, cls: str, url: str, elements: dict, actions: list, name: str) -> str:
        lines = [
            f'import {{ type Locator, expect }} from "@playwright/test";',
            f'import {{ BasePage }} from "./base.page";',
            "",
            f"export class {cls} extends BasePage {{",
            f'  readonly url = "{url}";' if url else f"  readonly url: RegExp = /.*/;",
            "",
            "  // ── Locators ─────────────────────────────────────────────────",
        ]

        for el_name, el_info in elements.items():
            prop_name = self._to_prop_name(el_name)
            selector = el_info.get("selector", "")
            sel_type = el_info.get("type", "css")

            if sel_type == "testid":
                tid = selector.replace('[data-testid="', "").rstrip('"]')
                lines.append(f"  get {prop_name}(): Locator {{")
                lines.append(f'    return this.testId("{tid}");')
                lines.append("  }")
            elif sel_type == "text":
                text_val = selector.replace('text="', "").rstrip('"')
                lines.append(f"  get {prop_name}(): Locator {{")
                lines.append(f'    return this.text("{text_val}");')
                lines.append("  }")
            else:
                lines.append(f"  get {prop_name}(): Locator {{")
                lines.append(f'    return this.page.locator(\'{selector}\');')
                lines.append("  }")

        # Action methods
        click_elements = set()
        fill_elements = set()

        for action in actions:
            a_type = action.get("action_type", action.get("action", {}).get("type", ""))
            el_name = action.get("element_name", "")
            if not el_name:
                continue

            prop = self._to_prop_name(el_name)
            if a_type == "click" and prop not in click_elements:
                click_elements.add(prop)
            elif a_type in ("type", "fill") and prop not in fill_elements:
                fill_elements.add(prop)

        if click_elements or fill_elements:
            lines += [
                "",
                "  // ── Actions ──────────────────────────────────────────────────",
            ]

        for prop in sorted(click_elements):
            method = f"click{prop[0].upper()}{prop[1:]}"
            lines.append(f"  async {method}() {{")
            lines.append(f"    await this.{prop}.click();")
            lines.append("  }")
            lines.append("")

        for prop in sorted(fill_elements):
            method = f"fill{prop[0].upper()}{prop[1:]}"
            lines.append(f"  async {method}(value: string) {{")
            lines.append(f"    await this.{prop}.fill(value);")
            lines.append("  }")
            lines.append("")

        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    def _render_from_locators(self, cls: str, elements: dict) -> str:
        screens = set(e.get("screen", "") for e in elements.values())

        lines = [
            f'import {{ type Locator, expect }} from "@playwright/test";',
            f'import {{ BasePage }} from "./base.page";',
            "",
            f"export class {cls} extends BasePage {{",
            f"  readonly url: string | RegExp = /./;",
            "",
            "  // ── Locators ─────────────────────────────────────────────────",
        ]

        for el_name, el_info in elements.items():
            prop_name = self._to_prop_name(el_name)
            selector = el_info.get("selector", "")
            sel_type = el_info.get("type", "css")

            if sel_type == "testid":
                tid = selector.replace('[data-testid="', "").rstrip('"]')
                lines.append(f"  get {prop_name}(): Locator {{")
                lines.append(f'    return this.testId("{tid}");')
                lines.append("  }")
            else:
                lines.append(f"  get {prop_name}(): Locator {{")
                lines.append(f'    return this.page.locator(\'{selector}\');')
                lines.append("  }")

        lines.append("}")
        lines.append("")
        return "\n".join(lines)

    def _extract_elements(self, session: dict) -> dict[str, dict]:
        elements: dict[str, dict] = {}
        for action in session.get("actions", []):
            el_name = action.get("element_name", "")
            selector = action.get("selector", "")
            sel_type = action.get("selector_type", "css")
            if el_name and selector and action.get("action_type") != "navigate":
                if el_name not in elements:
                    elements[el_name] = {
                        "selector": selector,
                        "type": sel_type,
                    }
        return elements

    def _extract_elements_from_events(self, events: list[dict]) -> dict[str, dict]:
        elements: dict[str, dict] = {}
        for event in events:
            target = event.get("target", {})
            el_name = target.get("element_name", "")
            selector = target.get("selector", "")
            sel_type = target.get("selector_type", "css")
            chain = target.get("selector_chain", [])

            if not el_name or not selector:
                continue

            testid_candidate = next((c for c in chain if c.get("type") == "testid"), None)
            if testid_candidate:
                selector = testid_candidate["value"]
                sel_type = "testid"

            if el_name not in elements:
                elements[el_name] = {
                    "selector": selector,
                    "type": sel_type,
                }
        return elements

    def _extract_url(self, session: dict) -> str:
        for action in session.get("actions", []):
            if action.get("action_type") == "navigate":
                return action.get("value", "")
        return session.get("base_url", "")

    @staticmethod
    def _to_class_name(name: str) -> str:
        parts = re.split(r"[_\-\s]+", name)
        return "".join(p.capitalize() for p in parts if p) + "Page"

    @staticmethod
    def _to_prop_name(name: str) -> str:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name).strip("_")
        parts = name.split("_")
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

    def save(self, code: str, path: str | Path) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(code, encoding="utf-8")
        return str(p)
