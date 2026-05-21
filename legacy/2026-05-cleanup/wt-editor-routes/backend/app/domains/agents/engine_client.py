"""
EngineClient — Backend ↔ Engine (Flask 5001) iletişim katmanı.

Backend agent pipeline'ı engine servisine HTTP üzerinden bağlar:
  - Sayfa keşfi (crawl)
  - Selector discovery
  - Test koşumu (pytest / playwright)
  - Self-healing (kırık locator onarımı)
  - Feature dosya yönetimi
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Engine servisi zaman aşımı süreleri
_TIMEOUT_SHORT = 15.0      # health, basit sorgular
_TIMEOUT_MEDIUM = 60.0     # crawl, locator discovery
_TIMEOUT_LONG = 300.0      # test koşumu, tam pipeline
_TIMEOUT_EXTRA = 600.0     # büyük regression suites

_MAX_RETRIES = 2


class EngineClient:
    """Engine servisine HTTP client — tüm agent'lar bu sınıf üzerinden engine'e erişir."""

    def __init__(self, base_url: str | None = None):
        self._base = (base_url or settings.engine_base_url).rstrip("/")

    # ── Health ────────────────────────────────────────────────────────
    async def health(self) -> dict[str, Any]:
        """Engine sağlık kontrolü."""
        return await self._get("/api/health", timeout=_TIMEOUT_SHORT)

    async def is_alive(self) -> bool:
        """Engine erişilebilir mi?"""
        try:
            resp = await self.health()
            return resp.get("status") == "ok" or "status" in resp
        except Exception:
            return False

    # ── Crawl & Discovery ─────────────────────────────────────────────
    async def crawl(self, url: str, max_pages: int = 10, depth: int = 2) -> dict[str, Any]:
        """Hedef URL'yi crawl et — sayfalar, linkler, butonlar keşfet."""
        return await self._post("/api/wizard/crawl", {
            "url": url,
            "max_pages": max_pages,
            "depth": depth,
        }, timeout=_TIMEOUT_MEDIUM)

    async def discover_selectors(self, url: str) -> dict[str, Any]:
        """Sayfadaki tüm interaktif elementlerin selector'larını çıkar."""
        return await self._post("/api/wizard/discover-selectors", {
            "url": url,
        }, timeout=_TIMEOUT_MEDIUM)

    async def full_discovery(self, url: str, max_pages: int = 10) -> dict[str, Any]:
        """Tam keşif: crawl → selector → locator. Tek çağrıda."""
        return await self._post("/api/wizard/full-run", {
            "url": url,
            "max_pages": max_pages,
        }, timeout=_TIMEOUT_LONG)

    async def generate_locators(self, url: str, elements: list[dict] | None = None) -> dict[str, Any]:
        """AI destekli locator önerileri üret."""
        payload: dict[str, Any] = {"url": url}
        if elements:
            payload["elements"] = elements
        return await self._post("/api/ai/generate-locators", payload, timeout=_TIMEOUT_MEDIUM)

    # ── Test Execution ────────────────────────────────────────────────
    async def run_tests(
        self,
        markers: str | None = None,
        feature: str | None = None,
        features_list: list[str] | None = None,
        timeout: float = _TIMEOUT_LONG,
    ) -> dict[str, Any]:
        """Test koşumu başlat ve sonuç döndür."""
        payload: dict[str, Any] = {}
        if markers:
            payload["markers"] = markers
        if feature:
            payload["feature"] = feature
        if features_list:
            payload["features_list"] = features_list
        return await self._post("/api/run", payload, timeout=timeout)

    async def run_pipeline(
        self,
        test_id: str | None = None,
        test_content: str | None = None,
        auto_run: bool = True,
    ) -> dict[str, Any]:
        """Manuel test → Gherkin → Playwright tam pipeline."""
        payload: dict[str, Any] = {"auto_run": auto_run}
        if test_id:
            payload["test_id"] = test_id
        if test_content:
            payload["test_content"] = test_content
        return await self._post("/api/pipeline/manual-to-automation", payload, timeout=_TIMEOUT_LONG)

    # ── Feature Files ─────────────────────────────────────────────────
    async def list_features(self) -> dict[str, Any]:
        """Tüm .feature dosyalarını listele."""
        return await self._get("/api/features", timeout=_TIMEOUT_SHORT)

    async def save_feature(self, name: str, content: str) -> dict[str, Any]:
        """Feature dosyası kaydet (otomatik glue code oluşturur)."""
        return await self._put(f"/api/features/{name}", {
            "content": content,
        }, timeout=_TIMEOUT_MEDIUM)

    async def read_feature(self, name: str) -> dict[str, Any]:
        """Feature dosyası oku."""
        return await self._get(f"/api/features/{name}", timeout=_TIMEOUT_SHORT)

    # ── Self-Healing ──────────────────────────────────────────────────
    async def self_heal(
        self,
        locator: str,
        page_url: str,
        accessibility_tree: str | None = None,
    ) -> dict[str, Any]:
        """Kırık locator'ı onar — AI + accessibility tree."""
        payload: dict[str, Any] = {
            "locator": locator,
            "page_url": page_url,
        }
        if accessibility_tree:
            payload["accessibility_tree"] = accessibility_tree
        return await self._post("/api/ai/self-heal", payload, timeout=_TIMEOUT_MEDIUM)

    async def healing_log(self) -> dict[str, Any]:
        """Self-healing geçmişini getir."""
        return await self._get("/api/ai/healing-log", timeout=_TIMEOUT_SHORT)

    # ── AI Generation ─────────────────────────────────────────────────
    async def generate_test(self, description: str, test_type: str = "bdd") -> dict[str, Any]:
        """Doğal dilden test kodu üret."""
        return await self._post("/api/ai/generate-test", {
            "description": description,
            "type": test_type,
        }, timeout=_TIMEOUT_MEDIUM)

    async def generate_bdd(self, description: str) -> dict[str, Any]:
        """Doğal dilden Gherkin feature üret."""
        return await self._post("/api/ai/generate-bdd", {
            "description": description,
        }, timeout=_TIMEOUT_MEDIUM)

    async def extract_from_document(self, content: str) -> dict[str, Any]:
        """Döküman metninden test senaryoları çıkar."""
        return await self._post("/api/wizard/analyze-document", {
            "content": content,
        }, timeout=_TIMEOUT_MEDIUM)

    # ── Analytics ─────────────────────────────────────────────────────
    async def quality_score(self) -> dict[str, Any]:
        """Genel test kalite skoru."""
        return await self._get("/api/ai/quality-score", timeout=_TIMEOUT_SHORT)

    async def coverage_gaps(self, features: list[str] | None = None) -> dict[str, Any]:
        """Test kapsam boşluklarını tespit et."""
        payload: dict[str, Any] = {}
        if features:
            payload["features"] = features
        return await self._post("/api/ai/coverage-gaps", payload, timeout=_TIMEOUT_MEDIUM)

    async def feedback_insights(self) -> dict[str, Any]:
        """Feedback loop öğrenme sonuçları."""
        return await self._get("/api/ai/feedback-insights", timeout=_TIMEOUT_SHORT)

    # ── Banking Test Data ─────────────────────────────────────────────
    async def generate_banking_data(self, config: dict[str, Any]) -> dict[str, Any]:
        """Bankacılık test verisi üret (BDDK/KVKK uyumlu)."""
        return await self._post("/api/banking/generate", config, timeout=_TIMEOUT_MEDIUM)

    # ── Monkey Testing ────────────────────────────────────────────────
    async def monkey_test(self, url: str, duration: int = 60, actions: int = 100) -> dict[str, Any]:
        """Chaos/monkey testing başlat."""
        return await self._post("/api/monkey-testing/run", {
            "url": url,
            "duration": duration,
            "max_actions": actions,
        }, timeout=_TIMEOUT_LONG)

    # ── Internal HTTP helpers ─────────────────────────────────────────
    async def _get(self, path: str, timeout: float = _TIMEOUT_SHORT) -> dict[str, Any]:
        return await self._request("GET", path, timeout=timeout)

    async def _post(self, path: str, json: dict | None = None, timeout: float = _TIMEOUT_MEDIUM) -> dict[str, Any]:
        return await self._request("POST", path, json=json, timeout=timeout)

    async def _put(self, path: str, json: dict | None = None, timeout: float = _TIMEOUT_MEDIUM) -> dict[str, Any]:
        return await self._request("PUT", path, json=json, timeout=timeout)

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        timeout: float = _TIMEOUT_MEDIUM,
    ) -> dict[str, Any]:
        """HTTP isteği gönder — retry ve hata yönetimi ile."""
        url = f"{self._base}{path}"
        last_err: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.request(method, url, json=json)
                    resp.raise_for_status()
                    return resp.json()
            except httpx.TimeoutException as exc:
                last_err = exc
                logger.warning(
                    "Engine timeout (%s %s) deneme %d/%d",
                    method, path, attempt, _MAX_RETRIES,
                )
            except httpx.HTTPStatusError as exc:
                # 4xx hatalarında retry yapma
                if 400 <= exc.response.status_code < 500:
                    logger.error("Engine client hatası (%d): %s %s", exc.response.status_code, method, path)
                    return {"error": True, "status": exc.response.status_code, "detail": exc.response.text}
                last_err = exc
                logger.warning(
                    "Engine HTTP hatası (%d) deneme %d/%d",
                    exc.response.status_code, attempt, _MAX_RETRIES,
                )
            except httpx.ConnectError as exc:
                last_err = exc
                logger.warning(
                    "Engine bağlantı hatası (%s) deneme %d/%d",
                    self._base, attempt, _MAX_RETRIES,
                )
            except Exception as exc:
                last_err = exc
                logger.warning("Engine beklenmeyen hata: %s", exc)
                break  # beklenmeyen hatalarda retry yapma

        # Tüm denemeler başarısız
        logger.error("Engine erişilemez (%s %s): %s", method, path, last_err)
        return {
            "error": True,
            "detail": f"Engine erişilemez: {last_err}",
            "engine_url": self._base,
        }


# Singleton
_client: EngineClient | None = None


def get_engine_client() -> EngineClient:
    """Global EngineClient instance."""
    global _client
    if _client is None:
        _client = EngineClient()
    return _client
