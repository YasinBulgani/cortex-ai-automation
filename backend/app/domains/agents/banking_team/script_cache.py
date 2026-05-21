"""
ScriptCache — Başarılı AI Koşularını Deterministik Script'lere Dönüştür (P2)

Skyvern Paterni:
  1. AI bir test senaryosunu başarıyla çalıştırdı
  2. Çalıştırma adımlarını kaydet (action log)
  3. libcst/AST ile Python kodu üret → deterministik script
  4. Sonraki koşularda AI yerine cached script çalıştır
  5. Cache hit → 10-100x hızlanma (AI call yok)

Neden Script Cache?
  - AI çağrıları pahalı ve yavaş (2-15 saniye per call)
  - Aynı sayfa yapısı için aynı aksiyon dizisi tekrarlanır
  - Deterministik scriptler %100 tekrarlanabilir
  - Mutation test, regression test için ideal

Kullanım:
  cache = ScriptCache()

  # AI koşusu sonrası kaydet
  cache.save(scenario_id="SCN-001", actions=[...], url="...", domain="...")

  # Sonraki koşularda
  script = cache.get(scenario_id="SCN-001", url="...")
  if script:
      run_script_in_isolated_worker(script)  # İzole yürütme zorunlu
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[5] / "engine" / "cache" / "scripts"


class ScriptCache:
    """Başarılı AI koşularını Playwright Python scriptlerine dönüştürür."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._stats = {"hits": 0, "misses": 0, "saves": 0}

    # ── Cache Get ──────────────────────────────────────────────────────────

    def get(self, scenario_id: str, url: str, dom_hash: str = "") -> str | None:
        """
        Cache'den deterministik script al.

        Returns: Python script string veya None (cache miss)
        """
        cache_key = self._make_key(scenario_id, url)
        script_path = self.cache_dir / f"{cache_key}.py"

        if not script_path.exists():
            self._stats["misses"] += 1
            return None

        script = script_path.read_text(encoding="utf-8")

        # DOM hash kontrolü (opsiyonel — DOM değiştiyse invalidate)
        if dom_hash:
            meta_path = self.cache_dir / f"{cache_key}.meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                if meta.get("dom_hash") != dom_hash:
                    logger.info("ScriptCache: DOM hash mismatch, invalidating %s", cache_key)
                    self._stats["misses"] += 1
                    return None

        self._stats["hits"] += 1
        logger.info("ScriptCache HIT: %s (scenario=%s)", cache_key[:12], scenario_id)
        return script

    # ── Cache Save ─────────────────────────────────────────────────────────

    def save(
        self,
        scenario_id: str,
        url: str,
        actions: list[dict],
        locators: list[dict] | None = None,
        dom_hash: str = "",
        test_data: dict | None = None,
    ) -> str:
        """
        Başarılı action log'unu deterministik Playwright script'e dönüştür ve kaydet.

        Args:
            scenario_id: Test senaryosu ID'si
            url: Hedef URL
            actions: Aksiyon listesi [{type, target, value, ...}]
            locators: NexusQA lokator haritası
            dom_hash: Sayfa DOM hash'i (invalidation için)
            test_data: Test verisi haritası

        Returns: Cache key
        """
        cache_key = self._make_key(scenario_id, url)

        # ── Actions → Python Script ───────────────────────────────────
        script = self._actions_to_script(actions, url, locators or [], test_data or {})

        # ── Save script ──────────────────────────────────────────────
        script_path = self.cache_dir / f"{cache_key}.py"
        script_path.write_text(script, encoding="utf-8")

        # ── Save metadata ────────────────────────────────────────────
        meta = {
            "scenario_id": scenario_id,
            "url": url,
            "action_count": len(actions),
            "dom_hash": dom_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "locator_count": len(locators or []),
        }
        meta_path = self.cache_dir / f"{cache_key}.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        self._stats["saves"] += 1
        logger.info("ScriptCache SAVE: %s (%d actions → script)", cache_key[:12], len(actions))

        return cache_key

    # ── Invalidate ─────────────────────────────────────────────────────────

    def invalidate(self, scenario_id: str, url: str) -> bool:
        """Cache entry'yi sil."""
        cache_key = self._make_key(scenario_id, url)
        script_path = self.cache_dir / f"{cache_key}.py"
        meta_path = self.cache_dir / f"{cache_key}.meta.json"

        deleted = False
        if script_path.exists():
            script_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()

        return deleted

    def invalidate_all(self) -> int:
        """Tüm cache'i temizle."""
        count = 0
        for f in self.cache_dir.glob("*.py"):
            f.unlink()
            count += 1
        for f in self.cache_dir.glob("*.meta.json"):
            f.unlink()
        return count

    @property
    def stats(self) -> dict:
        """Cache istatistikleri."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        return {
            **self._stats,
            "hit_rate": round(hit_rate, 1),
            "cached_scripts": len(list(self.cache_dir.glob("*.py"))),
        }

    # ── Private ────────────────────────────────────────────────────────────

    def _make_key(self, scenario_id: str, url: str) -> str:
        """Cache key oluştur."""
        raw = f"{scenario_id}:{url}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _actions_to_script(
        self,
        actions: list[dict],
        url: str,
        locators: list[dict],
        test_data: dict,
    ) -> str:
        """Action log'unu Playwright Python script'e çevir."""
        # Lokator haritası oluştur
        locator_map = {}
        for loc in locators:
            key = loc.get("key", "")
            ltype = loc.get("type", "css")
            val = loc.get("value", "")
            locator_map[key] = (ltype, val)

        # Script header
        lines = [
            '"""Auto-generated deterministic script — ScriptCache"""',
            '',
            'from playwright.sync_api import sync_playwright, expect',
            '',
            '',
            'def run(playwright):',
            '    browser = playwright.chromium.launch(headless=True)',
            '    context = browser.new_context(',
            '        viewport={"width": 1280, "height": 800},',
            '        locale="tr-TR",',
            '    )',
            '    page = context.new_page()',
            f'    page.goto("{url}")',
            '    page.wait_for_load_state("networkidle")',
            '',
        ]

        # Actions → Playwright commands
        for i, action in enumerate(actions):
            atype = action.get("type", "")
            target = action.get("target", "")
            value = action.get("value", "")

            # Test data interpolation
            if value in test_data:
                value = test_data[value]

            # Locator resolution
            pw_locator = self._resolve_locator(target, locator_map)

            comment = f'    # Step {i+1}: {atype} → {target[:40]}'
            lines.append(comment)

            if atype == "click":
                lines.append(f'    {pw_locator}.click()')
            elif atype == "fill":
                lines.append(f'    {pw_locator}.fill("{self._escape(value)}")')
            elif atype == "select":
                lines.append(f'    {pw_locator}.select_option(value="{self._escape(value)}")')
            elif atype == "navigate":
                lines.append(f'    page.goto("{self._escape(value or target)}")')
            elif atype == "wait":
                timeout = action.get("timeout", 2000)
                lines.append(f'    page.wait_for_timeout({timeout})')
            elif atype == "assert_visible":
                lines.append(f'    expect({pw_locator}).to_be_visible(timeout=10000)')
            elif atype == "assert_text":
                lines.append(f'    expect({pw_locator}).to_contain_text("{self._escape(value)}", timeout=10000)')
            elif atype == "assert_url":
                lines.append(f'    expect(page).to_have_url(re.compile("{self._escape(value)}"), timeout=10000)')
            elif atype == "scroll":
                direction = action.get("direction", "down")
                pixels = action.get("pixels", 300)
                if direction == "down":
                    lines.append(f'    page.mouse.wheel(0, {pixels})')
                else:
                    lines.append(f'    page.mouse.wheel(0, -{pixels})')
            elif atype == "press":
                lines.append(f'    page.keyboard.press("{self._escape(value)}")')
            elif atype == "hover":
                lines.append(f'    {pw_locator}.hover()')
            elif atype == "screenshot":
                lines.append(f'    page.screenshot(path="step_{i+1}.png")')
            else:
                lines.append(f'    # Unknown action: {atype}')

            lines.append('')

        # Script footer
        lines.extend([
            '    # Cleanup',
            '    context.close()',
            '    browser.close()',
            '',
            '',
            'if __name__ == "__main__":',
            '    with sync_playwright() as playwright:',
            '        run(playwright)',
        ])

        return '\n'.join(lines)

    def _resolve_locator(self, target: str, locator_map: dict) -> str:
        """Target key'den Playwright locator oluştur."""
        if target in locator_map:
            ltype, val = locator_map[target]
            if ltype == "testid":
                return f'page.get_by_test_id("{val}")'
            elif ltype == "role":
                return f'page.get_by_role("{val}")'
            elif ltype in ("aria-label", "label"):
                return f'page.get_by_label("{val}")'
            elif ltype == "placeholder":
                return f'page.get_by_placeholder("{val}")'
            elif ltype == "text":
                return f'page.get_by_text("{val}")'
            elif ltype == "id":
                return f'page.locator("#{val}")'
            elif ltype == "name":
                return f'page.locator("[name=\\"{val}\\"]")'
            elif ltype == "css":
                return f'page.locator("{val}")'
            elif ltype == "xpath":
                return f'page.locator("xpath={val}")'

        # Fallback: target'ı CSS selector olarak kullan
        if target.startswith(("#", ".", "[")):
            return f'page.locator("{target}")'
        elif target.startswith("//"):
            return f'page.locator("xpath={target}")'
        else:
            return f'page.get_by_test_id("{target}")'

    def _escape(self, s: str) -> str:
        """String'i Python string literal'e escape et."""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
