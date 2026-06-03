"""
Locator routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/locators_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/locators.py — APIRouter, port 8000 (consolidated)

Object Repository ve locator yönetimi endpoint'leri.
Geçici in-memory store yeterli — gerçek DB sonra.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/locators", tags=["engine", "locators"])

discover_router = APIRouter(prefix="/api", tags=["engine", "locators"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class LocatorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    locator_value: str = Field(..., min_length=1)
    page_url: str = ""


class LoadFeatureRequest(BaseModel):
    feature: str = Field(..., min_length=1)
    directory: str | None = None


class LoadAllRequest(BaseModel):
    directory: str | None = None


class ResolveKeyRequest(BaseModel):
    key: str = Field(..., min_length=1)


class BridgeResolveRequest(BaseModel):
    key: str = ""
    page: str | None = None
    element: str | None = None


class DiscoverRequest(BaseModel):
    url: str = Field(..., min_length=1)


# ─── In-memory store ─────────────────────────────────────────────────────────

class LocatorStore:
    """Geçici in-memory store. Migration tamamlanınca SQLAlchemy repository kullanılacak."""

    def __init__(self) -> None:
        self._records: dict[int, dict] = {}
        self._next_id = 1

    def list_all(self) -> list[dict]:
        return list(self._records.values())

    def save(self, name: str, locator_value: str, page_url: str = "") -> int:
        loc_id = self._next_id
        self._records[loc_id] = {"id": loc_id, "name": name, "locator_value": locator_value, "page_url": page_url}
        self._next_id += 1
        return loc_id

    def delete(self, loc_id: int) -> None:
        self._records.pop(loc_id, None)


_store = LocatorStore()


def get_store() -> LocatorStore:
    return _store


# ─── DB Locator Endpoints ─────────────────────────────────────────────────────

@router.get("")
def api_get_locators(source: str = "db", store: LocatorStore = Depends(get_store)):
    """DB veya JSON kaynaklı locator'ları listeler."""
    if source == "json":
        from core.locator_manager import LocatorManager  # type: ignore[import]
        return {"locators": LocatorManager.as_dict(), "source": "json"}
    return store.list_all()


@router.post("", status_code=status.HTTP_201_CREATED)
def api_save_locator(body: LocatorCreate, store: LocatorStore = Depends(get_store)):
    """Yeni locator kaydeder."""
    loc_id = store.save(body.name, body.locator_value, body.page_url)
    return {"status": "ok", "id": loc_id}


@router.delete("/{loc_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_locator(loc_id: int, store: LocatorStore = Depends(get_store)):
    """Locator siler."""
    store.delete(loc_id)


# ─── JSON Locator Management ──────────────────────────────────────────────────

@router.get("/json")
def api_get_json_locators():
    """Tüm JSON locator'ları döner."""
    from core.locator_manager import LocatorManager  # type: ignore[import]

    return {
        "locators": LocatorManager.as_dict(),
        "keys": LocatorManager.keys(),
        "count": len(LocatorManager.keys()),
    }


@router.post("/json/load", status_code=status.HTTP_200_OK)
def api_load_json_locators(body: LoadFeatureRequest):
    """Belirtilen feature için locator JSON dosyasını yükler."""
    try:
        from core.locator_manager import LocatorManager  # type: ignore[import]

        LocatorManager.load(body.feature, body.directory)
        return {
            "status": "ok",
            "feature": body.feature,
            "total_count": len(LocatorManager.keys()),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/json/load-all", status_code=status.HTTP_200_OK)
def api_load_all_json_locators(body: LoadAllRequest):
    """Tüm JSON locator dosyalarını yükler."""
    try:
        from core.locator_manager import LocatorManager  # type: ignore[import]

        LocatorManager.load_all(body.directory)
        return {
            "status": "ok",
            "total_count": len(LocatorManager.keys()),
            "keys": LocatorManager.keys(),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/json/resolve")
def api_resolve_json_locator(body: ResolveKeyRequest):
    """Verilen key'i Playwright selector'a çözümler."""
    from core.locator_manager import LocatorManager  # type: ignore[import]

    resolved = LocatorManager.resolve(body.key)
    return {"key": body.key, "selector": resolved, "from_json": resolved != body.key}


# ─── Locator Bridge ───────────────────────────────────────────────────────────

@router.post("/bridge/resolve")
def api_bridge_resolve(body: BridgeResolveRequest):
    """Tüm locator kaynaklarından birleşik çözümleme yapar."""
    if not body.key and not (body.page and body.element):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="key veya page+element gerekli",
        )
    try:
        from core.locator_bridge import get_bridge  # type: ignore[import]

        bridge = get_bridge()
        if body.page and body.element:
            selector = bridge.resolve(body.page, body.element)
        else:
            selector = bridge.resolve(body.key)
        return {"key": body.key or f"{body.page}.{body.element}", "selector": selector}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/bridge/health")
def api_bridge_health():
    """Tüm locator kaynaklarının sağlık raporunu döner."""
    try:
        from core.locator_bridge import get_bridge  # type: ignore[import]

        return get_bridge().health_report()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─── Discover Endpoint (ayrı prefix: /api/discover) ─────────────────────────

@discover_router.post("/discover")
def api_discover_page(body: DiscoverRequest, store: LocatorStore = Depends(get_store)):
    """
    Playwright ile sayfadaki interaktif elementleri keşfeder ve AI ile sınıflandırır.
    """
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        import json as _json

        from playwright.sync_api import sync_playwright  # type: ignore[import]
        from core.ai_engine import get_ai_engine  # type: ignore[import]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(2000)

            js_script = r"""
            () => {
                const getBestSelector = (el) => {
                    if (el.id) return "#" + el.id;
                    if (el.getAttribute('data-test-id')) return `[data-test-id="${el.getAttribute('data-test-id')}"]`;
                    if (el.name) return `[name="${el.name}"]`;
                    if (el.placeholder) return `[placeholder="${el.placeholder}"]`;
                    let sel = el.tagName.toLowerCase();
                    if (el.className && typeof el.className === 'string') {
                        let cls = el.className.trim().split(/\s+/)[0];
                        if (cls && !cls.includes(':')) sel += "." + cls;
                    }
                    return sel;
                };

                let results = [];
                let seen = new Set();
                let query = "button, a, input, select, textarea, [role='button'], [onclick]";
                let elements = document.querySelectorAll(query);

                elements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return;
                    let text = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || "").trim();
                    if (!text && el.tagName === 'A') text = el.getAttribute('href');
                    if (!text || text.length < 2) return;
                    let selector = getBestSelector(el);
                    if (seen.has(selector)) return;
                    seen.add(selector);
                    results.push({ text: text.substring(0, 60).replace(/\n/g, ' '), selector: selector });
                });
                return results;
            }
            """

            raw_elements = page.evaluate(js_script)
            browser.close()

        if not raw_elements:
            return {"status": "ok", "saved_count": 0}

        engine = get_ai_engine()
        prompt = (
            f"Scraped elements: {_json.dumps(raw_elements[:20])}. "
            "Classify into snake_case names for Object Repository. "
            "Return JSON Array with 'name', 'locator_value' keys. ONLY JSON."
        )
        msg = engine.client.chat.completions.create(
            model=engine.execute_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        response_text = msg.choices[0].message.content.strip()
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        ai_locators = _json.loads(response_text)
        saved_count = 0
        for loc in ai_locators:
            store.save(loc["name"], loc["locator_value"], url)
            saved_count += 1

        return {"status": "ok", "saved_count": saved_count}

    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
