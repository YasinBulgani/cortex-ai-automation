"""
AutoHealerAgent — Kırılan Playwright testlerini otomatik tamir eder.

Strateji (4 katman):
  0. Playwright MCP Live Verification: Gerçek browser'da selector doğrulama
  1. Zero-cost: 10-tier selector hierarchy (LLM gerektirmez, <1 saniye)
  2. Ollama fallback: DOM + eski selector'ı LLM'e gönder (3-10 saniye)
  3. pgvector cache: Başarılı heal'ler embedding ile cache'lenir

Selector Öncelik Sırası:
  P5: data-testid, role (en stabil)
  P4: aria-label, label, id
  P3: placeholder, name
  P2: text, css
  P1: xpath (en kırılgan)

Entegrasyon:
  TestRunner fail verdiğinde → AutoHealer çağrılır → Kırık selector'lar düzeltilir →
  Test dosyası güncellenir → Tekrar çalıştırılır → KnowledgeStore'a heal kaydedilir
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from app.config import settings
from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]

# ── 10-Tier Selector Hierarchy ────────────────────────────────────────────────
SELECTOR_TIERS = [
    ("data-testid", 5, '[data-testid="{value}"]'),
    ("role",        5, 'role={value}'),
    ("aria-label",  4, '[aria-label="{value}"]'),
    ("label",       4, 'label={value}'),
    ("id",          4, '#{value}'),
    ("placeholder", 3, '[placeholder="{value}"]'),
    ("name",        3, '[name="{value}"]'),
    ("text",        2, 'text={value}'),
    ("css",         2, '{value}'),
    ("xpath",       1, 'xpath={value}'),
]

SYSTEM_HEAL = """\
Sen kıdemli bir Playwright Test Mühendisisin. Kırılan bir test selector'ını tamir etmen gerekiyor.

## Kritik Kurallar
- PROJE BAĞLAMI'ndaki mevcut E2E testlerin selector stilini takip et
- Projedeki kullanılan UI framework'ü (React, ShadCN, Tailwind vb.) dikkate al
- Geçmiş heal sonuçlarını (KnowledgeStore'daki error_pattern) referans al

## Selector Öncelik Sırası
data-testid > role > aria-label > label > id > placeholder > name > text > CSS > XPath

## Ekstra Kurallar
- Tailwind CSS class'larını KULLANMA (sık değişir)
- React auto-generated ID'leri (başında :r, :R, radix-, rc-) KULLANMA
- Stability skoru yüksek olanı tercih et
- En az 2 alternatif öner

## Çıktı Formatı
MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "healed_selectors": [
    {
      "strategy": "data-testid|role|aria-label|...",
      "selector": "page.getByTestId('...')" ,
      "confidence": 0.95,
      "stability": 5,
      "reason": "Neden bu selector'ı seçtin"
    }
  ],
  "root_cause": "Selector neden kırıldı (DOM değişikliği, yeniden adlandırma, vb.)"
}
"""


class AutoHealerAgent(BaseAgent):
    name = "Otomatik Tamirci"
    temperature = 0.1
    max_tokens = 512
    model_fallback = ["qwen2.5-coder:7b"]

    @property
    def model(self) -> str:  # type: ignore[override]
        return (
            settings.ollama_model_fast
            if settings.ai_provider == "ollama"
            else settings.openai_model
        )

    def run(self, context: dict) -> AgentResult:
        """
        context keys:
          failed_tests    — [{file, test_name, error, selector, dom_snippet}]
          test_files_dir  — Test dosyalarının dizini (default: e2e/banking)
        """
        failed = context.get("failed_tests", [])
        if not failed:
            return AgentResult(agent_name=self.name, success=True, data={"healed": 0, "message": "Kırık test yok"})

        healed_count = 0
        results = []

        for test_info in failed[:10]:  # Max 10 test tamir et
            heal_result = self._heal_single(test_info)
            results.append(heal_result)
            if heal_result.get("healed"):
                healed_count += 1

        # KnowledgeStore'a heal sonuçlarını kaydet
        if healed_count > 0:
            self.learn(
                f"Auto-Heal: {healed_count}/{len(failed)} kırık selector tamir edildi. "
                f"Stratejiler: {', '.join(r.get('strategy', '?') for r in results if r.get('healed'))}",
                metadata={"healed_count": healed_count, "total_broken": len(failed)},
            )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "healed": healed_count,
                "total_broken": len(failed),
                "details": results,
            },
        )

    def _heal_single(self, test_info: dict) -> dict:
        """Tek bir kırık selector'ı tamir et."""
        broken_selector = test_info.get("selector", "")
        dom_snippet = test_info.get("dom_snippet", "")
        error_msg = test_info.get("error", "")
        file_path = test_info.get("file", "")
        test_name = test_info.get("test_name", "")

        result = {
            "file": file_path,
            "test_name": test_name,
            "broken_selector": broken_selector,
            "healed": False,
            "strategy": "",
            "new_selector": "",
        }

        # ── Tier 1: Zero-cost DOM-based healing ──────────────────────
        if dom_snippet:
            zero_cost = self._zero_cost_heal(broken_selector, dom_snippet)
            if zero_cost:
                result.update({
                    "healed": True,
                    "strategy": zero_cost["strategy"],
                    "new_selector": zero_cost["selector"],
                    "tier": "zero-cost",
                    "confidence": zero_cost["confidence"],
                })
                self._cache_heal(broken_selector, zero_cost)
                return result

        # ── Tier 2: pgvector cache lookup ────────────────────────────
        cached = self._lookup_cache(broken_selector)
        if cached:
            result.update({
                "healed": True,
                "strategy": cached.get("strategy", "cached"),
                "new_selector": cached.get("selector", ""),
                "tier": "cached",
                "confidence": 0.85,
            })
            return result

        # ── Tier 3: LLM-based healing ────────────────────────────────
        if dom_snippet or error_msg:
            llm_result = self._llm_heal(broken_selector, dom_snippet, error_msg, test_name)
            if llm_result:
                result.update({
                    "healed": True,
                    "strategy": llm_result.get("strategy", "llm"),
                    "new_selector": llm_result.get("selector", ""),
                    "tier": "llm",
                    "confidence": llm_result.get("confidence", 0.7),
                    "root_cause": llm_result.get("root_cause", ""),
                })
                self._cache_heal(broken_selector, llm_result)
                return result

        return result

    # ── Zero-Cost Healing ────────────────────────────────────────────────────

    def _zero_cost_heal(self, broken: str, dom: str) -> dict | None:
        """DOM'dan 10-tier hierarchy ile yeni selector bul."""

        # data-testid kontrolü
        testids = re.findall(r'data-testid=["\']([^"\']+)["\']', dom)
        if testids:
            return {
                "strategy": "data-testid",
                "selector": f"page.getByTestId('{testids[0]}')",
                "confidence": 0.95,
                "stability": 5,
            }

        # role kontrolü
        roles = re.findall(r'role=["\']([^"\']+)["\']', dom)
        for role in roles:
            names = re.findall(r'(?:aria-label|name)=["\']([^"\']+)["\']', dom)
            if names:
                return {
                    "strategy": "role",
                    "selector": f"page.getByRole('{role}', {{ name: '{names[0]}' }})",
                    "confidence": 0.90,
                    "stability": 5,
                }

        # aria-label
        labels = re.findall(r'aria-label=["\']([^"\']+)["\']', dom)
        if labels:
            return {
                "strategy": "aria-label",
                "selector": f"page.getByLabel('{labels[0]}')",
                "confidence": 0.85,
                "stability": 4,
            }

        # placeholder
        placeholders = re.findall(r'placeholder=["\']([^"\']+)["\']', dom)
        if placeholders:
            return {
                "strategy": "placeholder",
                "selector": f"page.getByPlaceholder('{placeholders[0]}')",
                "confidence": 0.80,
                "stability": 3,
            }

        # id — React/MUI/Radix random ID'lerini filtrele
        ids = re.findall(r'\bid=["\']([^"\']+)["\']', dom)
        # :r ile baslayan (React), radix- prefixi, rc- prefixi,
        # tamamen rakam, veya cok kisa ID'ler unstable kabul edilir
        ids = [
            i for i in ids
            if not i.startswith((":r", ":R", "radix-", "rc-", "react-"))
            and not re.match(r"^\d+$", i)
            and not re.match(r"^[a-f0-9]{6,}$", i)  # hex-only hash ID'ler
            and len(i) > 2
        ]
        if ids:
            return {
                "strategy": "id",
                "selector": f"page.locator('#{ids[0]}')",
                "confidence": 0.75,
                "stability": 4,
            }

        # text content
        texts = re.findall(r'>([^<]{3,30})<', dom)
        texts = [t.strip() for t in texts if t.strip() and not t.strip().startswith('{')]
        if texts:
            return {
                "strategy": "text",
                "selector": f"page.getByText('{texts[0]}')",
                "confidence": 0.60,
                "stability": 2,
            }

        return None

    # ── LLM-Based Healing ────────────────────────────────────────────────────

    def _llm_heal(self, broken: str, dom: str, error: str, test_name: str) -> dict | None:
        """Ollama LLM ile kırık selector'ı analiz et ve yeni öner."""
        user_prompt = (
            f"Kırık Selector: {broken}\n"
            f"Test Adı: {test_name}\n"
            f"Hata: {error[:300]}\n"
            f"DOM Snippet:\n{dom[:1500]}"
        )
        try:
            result = self.call_json(SYSTEM_HEAL, user_prompt)
            healed = result.get("healed_selectors", [])
            if healed:
                best = max(healed, key=lambda x: x.get("confidence", 0))
                best["root_cause"] = result.get("root_cause", "")
                return best
        except Exception as e:
            logger.debug("LLM heal hatası: %s", e)
        return None

    # ── Cache (pgvector) ─────────────────────────────────────────────────────

    def _cache_heal(self, broken_selector: str, heal: dict) -> None:
        """Başarılı heal'i KnowledgeStore'a cache'le."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            project_id = getattr(self, "_project_id", None)
            store = KnowledgeStore(project_id=project_id)
            store.ingest(
                text=f"Selector Heal: '{broken_selector}' → '{heal.get('selector', '')}'",
                source="error_pattern",
                metadata={
                    "type": "selector_heal",
                    "broken": broken_selector,
                    "healed": heal.get("selector", ""),
                    "strategy": heal.get("strategy", ""),
                    "confidence": heal.get("confidence", 0),
                },
                project_id=project_id,
            )
        except Exception:
            pass

    def _lookup_cache(self, broken_selector: str) -> dict | None:
        """pgvector'dan benzer bir heal cache'i ara."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            project_id = getattr(self, "_project_id", None)
            store = KnowledgeStore(project_id=project_id)
            chunks = store.retrieve(
                f"Selector Heal: '{broken_selector}'",
                top_k=1,
                sources=["error_pattern"],
                min_similarity=0.80,
                project_id=project_id,
            )
            if chunks and chunks[0].metadata.get("type") == "selector_heal":
                return {
                    "selector": chunks[0].metadata.get("healed", ""),
                    "strategy": chunks[0].metadata.get("strategy", "cached"),
                }
        except Exception:
            pass
        return None

    # ── Tier 0: Playwright MCP Live Verification ────────────────────────────

    def _verify_with_playwright(self, healed_selector: str, page_url: str = "") -> bool:
        """Playwright MCP uzerinden healed selector'i gercek browser'da dogrula."""
        try:
            import asyncio
            from app.domains.playwright_mcp.browser_manager import BrowserManager

            manager = BrowserManager()

            # Playwright selector formatini duzelt — page.getByTestId('x') -> getByTestId('x')
            pw_selector = healed_selector
            if pw_selector.startswith("page."):
                pw_selector = pw_selector[5:]

            async def _check() -> bool:
                try:
                    page = await manager.get_or_create_page(page_url or "about:blank")
                    if page_url:
                        await page.goto(page_url, wait_until="domcontentloaded", timeout=10000)

                    # Selector'i Playwright API formatina donustur ve dene
                    if "getByTestId" in pw_selector:
                        tid = re.search(r"getByTestId\(['\"](.+?)['\"]\)", pw_selector)
                        if tid:
                            loc = page.get_by_test_id(tid.group(1))
                            count = await loc.count()
                            return count > 0
                    elif "getByRole" in pw_selector:
                        role_match = re.search(
                            r"getByRole\(['\"](.+?)['\"]",
                            pw_selector,
                        )
                        if role_match:
                            loc = page.get_by_role(role_match.group(1))
                            count = await loc.count()
                            return count > 0
                    elif "getByLabel" in pw_selector:
                        label_match = re.search(r"getByLabel\(['\"](.+?)['\"]\)", pw_selector)
                        if label_match:
                            loc = page.get_by_label(label_match.group(1))
                            count = await loc.count()
                            return count > 0
                    elif "getByPlaceholder" in pw_selector:
                        ph_match = re.search(r"getByPlaceholder\(['\"](.+?)['\"]\)", pw_selector)
                        if ph_match:
                            loc = page.get_by_placeholder(ph_match.group(1))
                            count = await loc.count()
                            return count > 0
                    elif "getByText" in pw_selector:
                        txt_match = re.search(r"getByText\(['\"](.+?)['\"]\)", pw_selector)
                        if txt_match:
                            loc = page.get_by_text(txt_match.group(1))
                            count = await loc.count()
                            return count > 0
                    elif "locator" in pw_selector:
                        css_match = re.search(r"locator\(['\"](.+?)['\"]\)", pw_selector)
                        if css_match:
                            loc = page.locator(css_match.group(1))
                            count = await loc.count()
                            return count > 0

                    return False
                except Exception:
                    return False

            # Mevcut event loop varsa kullan, yoksa yeni olustur
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = loop.run_in_executor(pool, lambda: asyncio.run(_check()))
                    # Fire-and-forget olmadigi icin sync bekle
                    return False  # Async context'te sync bekleyemeyiz — guvenli default
            except RuntimeError:
                return asyncio.run(_check())

        except (ImportError, Exception) as exc:
            logger.debug("Playwright MCP dogrulama atlandi: %s", exc)
            return False  # Playwright yok veya hata — dogrulama atla

    def _get_live_dom(self, page_url: str, session_id: str = "") -> str:
        """Playwright MCP'den canli DOM al."""
        try:
            import asyncio
            from app.domains.playwright_mcp.browser_manager import BrowserManager

            manager = BrowserManager()

            async def _fetch_dom() -> str:
                try:
                    page = await manager.get_or_create_page(session_id or page_url)
                    if page_url:
                        current_url = page.url
                        if current_url != page_url and page_url != "about:blank":
                            await page.goto(page_url, wait_until="domcontentloaded", timeout=10000)
                    content = await page.content()
                    return content
                except Exception:
                    return ""

            try:
                loop = asyncio.get_running_loop()
                # Zaten async context'teyiz — yeni thread'de calistir
                return ""  # Guvenli default — async context'te sync bekleyemeyiz
            except RuntimeError:
                return asyncio.run(_fetch_dom())

        except (ImportError, Exception) as exc:
            logger.debug("Canli DOM alinamadi: %s", exc)
            return ""

    def _take_screenshot(self, page_url: str, label: str = "screenshot") -> str:
        """Playwright MCP ile ekran goruntusu al, dosya yolunu dondur."""
        try:
            import asyncio
            from app.domains.playwright_mcp.browser_manager import BrowserManager

            manager = BrowserManager()
            ts = int(time.time())
            screenshot_dir = REPO_ROOT / "reports" / "heal-screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = screenshot_dir / f"{label}_{ts}.png"

            async def _capture() -> str:
                try:
                    page = await manager.get_or_create_page(page_url)
                    await page.screenshot(path=str(screenshot_path))
                    return str(screenshot_path)
                except Exception:
                    return ""

            try:
                asyncio.get_running_loop()
                return ""  # Async context — guvenli default
            except RuntimeError:
                return asyncio.run(_capture())

        except (ImportError, Exception):
            return ""

    def heal_with_live_dom(self, test_info: dict, session_id: str = "") -> dict:
        """Playwright MCP'den canli DOM alarak healing yap.

        Akis:
          1. Playwright MCP browser session'dan canli DOM alinir
          2. Canli DOM ile zero-cost healing yapilir (statik snippet'tan cok daha isabetli)
          3. Healed selector gercek browser'da dogrulanir
          4. Sonuc screenshot_before / screenshot_after ile zenginlestirilir
        """
        broken_selector = test_info.get("selector", "")
        page_url = test_info.get("page_url", test_info.get("url", ""))
        file_path = test_info.get("file", "")
        test_name = test_info.get("test_name", "")

        result: dict = {
            "file": file_path,
            "test_name": test_name,
            "broken_selector": broken_selector,
            "healed": False,
            "strategy": "",
            "new_selector": "",
            "tier": "",
            "live_dom_used": False,
            "verified_in_browser": False,
            "screenshot_before": "",
            "screenshot_after": "",
        }

        # Screenshot before (fire-and-forget, non-critical)
        if page_url:
            result["screenshot_before"] = self._take_screenshot(page_url, "before")

        # 1. Canli DOM al
        live_dom = ""
        if session_id or page_url:
            live_dom = self._get_live_dom(page_url, session_id)

        # 2. Canli DOM varsa zero-cost healing yap
        dom_for_healing = live_dom if live_dom else test_info.get("dom_snippet", "")
        if dom_for_healing:
            result["live_dom_used"] = bool(live_dom)
            enriched_info = {**test_info, "dom_snippet": dom_for_healing}
            heal_result = self._heal_single(enriched_info)
            result.update({
                "healed": heal_result.get("healed", False),
                "strategy": heal_result.get("strategy", ""),
                "new_selector": heal_result.get("new_selector", ""),
                "tier": heal_result.get("tier", ""),
                "confidence": heal_result.get("confidence", 0),
            })
        else:
            # DOM yok — standart heal_single ile devam et
            heal_result = self._heal_single(test_info)
            result.update({
                "healed": heal_result.get("healed", False),
                "strategy": heal_result.get("strategy", ""),
                "new_selector": heal_result.get("new_selector", ""),
                "tier": heal_result.get("tier", ""),
                "confidence": heal_result.get("confidence", 0),
            })

        # 3. Healed selector'i gercek browser'da dogrula
        if result["healed"] and page_url:
            verified = self._verify_with_playwright(result["new_selector"], page_url)
            result["verified_in_browser"] = verified
            if verified:
                result["tier"] = f"verified-{result.get('tier', 'unknown')}"
                result["confidence"] = min(
                    (result.get("confidence", 0.7) or 0.7) + 0.1, 1.0,
                )

        # Screenshot after (fire-and-forget, non-critical)
        if page_url and result["healed"]:
            result["screenshot_after"] = self._take_screenshot(page_url, "after")

        return result
