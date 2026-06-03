"""
LLM Agent routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/llm_agent_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/llm_agent.py — APIRouter, port 8000 (consolidated)

ReAct-style browser agent oturumları. Her oturum bir Playwright
browser context/page çiftini saklar. Tüm Playwright çağrıları ayrı
bir daemon worker thread'inde çalışır (sync API + asyncio uyumluluğu).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import queue as _queue_module
import threading
import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/llm-agent", tags=["engine", "llm-agent"])
logger = logging.getLogger(__name__)


# ─── Timeout configuration (env-overridable) ──────────────────────────────────

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default


TIMEOUT_PW_INIT_SEC     = _env_int("LLM_AGENT_PW_INIT_TIMEOUT_SEC", 25)
TIMEOUT_PW_ACT_SEC      = _env_int("LLM_AGENT_PW_ACT_TIMEOUT_SEC", 15)
TIMEOUT_PW_DOM_SEC      = _env_int("LLM_AGENT_PW_DOM_TIMEOUT_SEC", 15)
TIMEOUT_PW_SNAPSHOT_SEC = _env_int("LLM_AGENT_PW_SNAPSHOT_TIMEOUT_SEC", 10)
TIMEOUT_PW_CLOSE_SEC    = _env_int("LLM_AGENT_PW_CLOSE_TIMEOUT_SEC", 10)
WAIT_AFTER_GOTO_MS      = _env_int("LLM_AGENT_WAIT_AFTER_GOTO_MS", 600)
WAIT_AFTER_LOGIN_MS     = _env_int("LLM_AGENT_WAIT_AFTER_LOGIN_MS", 1500)
GOTO_TIMEOUT_MS         = _env_int("LLM_AGENT_GOTO_TIMEOUT_MS", 20000)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CredentialsSchema(BaseModel):
    login_url: str | None = None
    username_selector: str | None = None
    username: str | None = None
    password_selector: str | None = None
    password: str | None = None
    submit_selector: str | None = None


class StartRequest(BaseModel):
    url: str = Field(..., min_length=1)
    credentials: CredentialsSchema | None = None
    skip_initial_navigation: bool = False
    reuse_session_id: str | None = None


class ActRequest(BaseModel):
    type: str = Field(..., min_length=1)
    selector: str = ""
    value: str = ""


class ScreenshotRequest(BaseModel):
    full_page: bool = False
    quality: int = Field(default=65, ge=1, le=100)


class NavigateRequest(BaseModel):
    url: str = Field(..., min_length=1)
    wait_until: str = "domcontentloaded"


class FindElementRequest(BaseModel):
    selector: str = Field(..., min_length=1)
    all: bool = False  # False → first match, True → all matches


class EvaluateRequest(BaseModel):
    expression: str = Field(..., min_length=1)


class TypeRequest(BaseModel):
    selector: str = Field(..., min_length=1)
    text: str = ""
    delay_ms: int = Field(default=0, ge=0, le=500)
    clear_first: bool = False


class ClickRequest(BaseModel):
    selector: str = Field(..., min_length=1)
    button: str = "left"   # left | right | middle
    double: bool = False
    timeout_ms: int = Field(default=6000, ge=500, le=30000)


class WaitRequest(BaseModel):
    kind: str = "selector"  # selector | text | timeout | network_idle
    value: str = ""         # selector string, text snippet, or timeout ms
    timeout_ms: int = Field(default=6000, ge=100, le=30000)


# ─── Thread-safe session store ────────────────────────────────────────────────

_SESSIONS: dict[str, dict] = {}
_SESSIONS_LOCK = threading.Lock()


# ─── Warm browser pool ────────────────────────────────────────────────────────

_POOL: dict = {"pw": None, "browser": None, "worker": None}
_POOL_LOCK = threading.Lock()


# ─── DOM cache ────────────────────────────────────────────────────────────────

_DOM_CACHE: dict[str, tuple[float, dict]] = {}
_DOM_CACHE_LOCK = threading.Lock()
_DOM_CACHE_TTL_SEC = 300


def _dom_cache_key(url: str) -> str:
    return (url or "").split("#")[0].rstrip("/")


def _dom_cache_get(url: str) -> dict | None:
    with _DOM_CACHE_LOCK:
        entry = _DOM_CACHE.get(_dom_cache_key(url))
        if entry is None:
            return None
        ts, data = entry
        if time.time() - ts > _DOM_CACHE_TTL_SEC:
            _DOM_CACHE.pop(_dom_cache_key(url), None)
            return None
        return {**data}


def _dom_cache_set(url: str, data: dict) -> None:
    with _DOM_CACHE_LOCK:
        _DOM_CACHE[_dom_cache_key(url)] = (time.time(), {**data})
        if len(_DOM_CACHE) > 50:
            oldest = min(_DOM_CACHE.items(), key=lambda kv: kv[1][0])[0]
            _DOM_CACHE.pop(oldest, None)


# ─── Per-session Playwright worker thread ─────────────────────────────────────

class PlaywrightWorker:
    """Bir session'daki tüm Playwright çağrılarını ayrı bir thread'de yürütür."""

    def __init__(self) -> None:
        self._q: _queue_module.Queue = _queue_module.Queue()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="pw-worker"
        )
        self._thread.start()

    def _loop(self) -> None:
        while True:
            item = self._q.get()
            if item is None:
                break
            fn, result_q = item
            try:
                result_q.put(("ok", fn()))
            except Exception as exc:  # noqa: BLE001
                result_q.put(("err", exc))

    def run(self, fn, timeout: float = 60):
        rq: _queue_module.Queue = _queue_module.Queue()
        self._q.put((fn, rq))
        try:
            kind, val = rq.get(timeout=timeout)
        except _queue_module.Empty:
            raise TimeoutError(f"Playwright worker zaman aşımına uğradı ({timeout}s)")
        if kind == "err":
            raise val
        return val

    def stop(self) -> None:
        self._q.put(None)
        self._thread.join(timeout=10)


# ─── Pool init / health check ─────────────────────────────────────────────────

def _ensure_pool() -> dict:
    with _POOL_LOCK:
        worker = _POOL.get("worker")
        browser = _POOL.get("browser")

        browser_alive = False
        if worker is not None and browser is not None:
            try:
                browser_alive = bool(worker.run(
                    lambda: browser.is_connected(), timeout=3
                ))
            except Exception:
                browser_alive = False

        if browser_alive:
            return _POOL

        if worker is not None:
            try:
                worker.stop()
            except Exception:
                pass

        new_worker = PlaywrightWorker()

        def _boot():
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            b = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            return {"pw": pw, "browser": b}

        try:
            boot = new_worker.run(_boot, timeout=40)
        except Exception:
            new_worker.stop()
            raise

        _POOL["pw"] = boot["pw"]
        _POOL["browser"] = boot["browser"]
        _POOL["worker"] = new_worker
        return _POOL


# ─── Internal auth dependency ─────────────────────────────────────────────────

def _require_internal_auth(x_internal_key: Annotated[str | None, Header()] = None) -> None:
    expected = os.environ.get("ENGINE_INTERNAL_KEY", "")
    if not x_internal_key or x_internal_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# ─── Screenshot / page-info helpers ──────────────────────────────────────────
# NOT: Bu fonksiyonlar Playwright thread'inden çağrılmalıdır.

def _take_screenshot(page) -> str:
    try:
        raw = page.screenshot(type="jpeg", quality=65, full_page=False)
        return base64.b64encode(raw).decode()
    except Exception as exc:
        logger.warning("Screenshot alınamadı: %s", exc)
        return ""


def _get_page_info(page) -> dict:
    try:
        title = page.title()
    except Exception:
        title = ""
    try:
        url = page.url
    except Exception:
        url = ""
    try:
        counts = page.evaluate("""() => ({
            interactive: document.querySelectorAll('a, button, input, select, textarea').length,
            buttons: document.querySelectorAll('button, [role="button"], input[type="submit"]').length,
            inputs: document.querySelectorAll('input:not([type="hidden"]), textarea, select').length,
            links: document.querySelectorAll('a[href]').length,
            forms: document.querySelectorAll('form').length,
        })""")
    except Exception:
        counts = {"interactive": 0, "buttons": 0, "inputs": 0, "links": 0, "forms": 0}
    return {"title": title, "url": url, **counts}


# ─── Deep DOM analysis JS ─────────────────────────────────────────────────────

_DOM_JS = """() => {
    const safe = (fn) => { try { return fn(); } catch(e) { return null; } };

    const getSelector = (el) => {
        if (el.id) return '#' + el.id;
        if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
        if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
        const cls = (el.className || '').split(' ').filter(c => c && !c.includes(':')).slice(0, 2).join('.');
        return cls ? `${el.tagName.toLowerCase()}.${cls}` : el.tagName.toLowerCase();
    };

    const isVisible = (el) => {
        if (!el || el.offsetParent === null) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    };

    const buttons = Array.from(document.querySelectorAll(
        'button, [role="button"], input[type="submit"], input[type="button"], a.btn, a.button'
    )).filter(isVisible).slice(0, 20).map(el => ({
        text: (el.textContent || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 80),
        selector: getSelector(el),
        tag: el.tagName.toLowerCase(),
        disabled: el.disabled || false,
    }));

    const inputs = Array.from(document.querySelectorAll(
        'input:not([type="hidden"]), textarea, select'
    )).filter(isVisible).slice(0, 20).map(el => {
        const labelEl = el.id ? document.querySelector(`label[for="${el.id}"]`) : null;
        return {
            type: el.type || el.tagName.toLowerCase(),
            name: el.name || '',
            placeholder: el.placeholder || '',
            required: el.required || false,
            value: (el.value || '').slice(0, 50),
            label: labelEl ? labelEl.textContent.trim() : '',
            selector: getSelector(el),
        };
    });

    const navLinks = Array.from(document.querySelectorAll(
        'nav a, header a, [role="navigation"] a, .nav a, .navbar a, .menu a'
    )).filter(isVisible).slice(0, 15).map(el => ({
        text: el.textContent.trim().slice(0, 60),
        href: el.href,
        selector: getSelector(el),
        active: el.classList.contains('active') || el.ariaCurrent === 'page',
    }));

    const alerts = Array.from(document.querySelectorAll(
        '[class*="error"], [class*="alert"], [class*="warning"], [class*="danger"], [role="alert"], .toast, .notification, .snackbar, [class*="message"]'
    )).filter(el => isVisible(el) && el.textContent.trim().length > 3).slice(0, 6).map(el => ({
        text: el.textContent.trim().slice(0, 200),
        type: el.getAttribute('role') || el.className.split(' ').find(c => ['error','alert','warning','danger','success','info'].some(k => c.includes(k))) || 'message',
    }));

    const forms = Array.from(document.querySelectorAll('form')).slice(0, 3).map(form => ({
        id: form.id || '',
        action: form.action || '',
        method: form.method || 'get',
        field_count: form.querySelectorAll('input:not([type="hidden"]), textarea, select').length,
        submit_text: safe(() => form.querySelector('[type="submit"], button[type="submit"]')?.textContent?.trim() || ''),
    }));

    const bodyText = document.body.innerText.toLowerCase();
    const hasPassword = !!document.querySelector('input[type="password"]');
    const hasTable = !!document.querySelector('table, [role="grid"], [role="table"]');
    const hasSearch = !!document.querySelector('input[type="search"], [placeholder*="search" i], [placeholder*="ara" i]');
    const hasModal = !!document.querySelector('[role="dialog"], .modal, .dialog');
    const hasNav = !!document.querySelector('nav, [role="navigation"]');
    const formCount = document.querySelectorAll('form').length;

    let pageType = 'generic';
    if (hasModal) pageType = 'modal';
    else if (hasPassword) pageType = 'auth';
    else if (hasTable) pageType = 'list_table';
    else if (hasSearch && !formCount) pageType = 'search';
    else if (formCount > 0) pageType = 'form';
    else if (bodyText.includes('dashboard') || bodyText.includes('overview') || bodyText.includes('panel')) pageType = 'dashboard';
    else if (hasNav) pageType = 'navigation';

    const textExcerpt = document.body.innerText.replace(/\\s+/g, ' ').trim().slice(0, 2000);

    const headings = Array.from(document.querySelectorAll('h1, h2, h3')).slice(0, 8).map(h => ({
        level: parseInt(h.tagName[1]),
        text: h.textContent.trim().slice(0, 80),
    }));

    const perf = safe(() => {
        const nav = performance.getEntriesByType('navigation')[0] || {};
        return {
            load_ms: Math.round(nav.loadEventEnd - nav.startTime) || 0,
            dom_interactive_ms: Math.round(nav.domInteractive - nav.startTime) || 0,
            ttfb_ms: Math.round(nav.responseStart - nav.startTime) || 0,
        };
    }) || {};

    const tech = [];
    if (window.__NEXT_DATA__) tech.push({name:'Next.js',category:'framework'});
    if (window.React || document.querySelector('[data-reactroot],[data-react-helmet]')) tech.push({name:'React',category:'framework'});
    if (window.Vue || document.querySelector('[data-v-app]')) tech.push({name:'Vue',category:'framework'});
    if (window.angular || window.ng) tech.push({name:'Angular',category:'framework'});
    if (window.jQuery || window.$) tech.push({name:'jQuery',category:'library'});
    if (document.querySelector('meta[name="generator"]')) tech.push({name:document.querySelector('meta[name="generator"]').content,category:'cms'});
    const hasCSPNonce = !!document.querySelector('[nonce]');

    return {
        page_type: pageType,
        buttons,
        inputs,
        nav_links: navLinks,
        alerts,
        forms,
        headings,
        text_excerpt: textExcerpt,
        has_modal: hasModal,
        has_table: hasTable,
        has_search: hasSearch,
        perf,
        tech_stack: tech,
        has_csp_nonce: hasCSPNonce,
    };
}"""


def _deep_dom_analysis(page) -> dict:
    """Playwright thread'inden çağrılmalıdır."""
    try:
        data = page.evaluate(_DOM_JS)
        data["url"] = page.url
        data["title"] = page.title()
        return data
    except Exception as exc:
        logger.warning("DOM analizi başarısız: %s", exc)
        return {"error": str(exc), "url": page.url, "title": ""}


# ─── Background pool warmup ───────────────────────────────────────────────────

def _background_warmup():
    try:
        time.sleep(2)
        _ensure_pool()
        logger.info("LLM Agent browser pool warmup tamamlandı")
    except Exception as exc:
        logger.warning("Background warmup başarısız (lazy init devreye girer): %s", exc)


threading.Thread(target=_background_warmup, daemon=True, name="llm-pool-warmup").start()


# ─── POST /api/llm-agent/warmup ───────────────────────────────────────────────

@router.post("/warmup")
def llm_agent_warmup(
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Browser pool'unu manuel olarak ısıtır."""
    try:
        t0 = time.time()
        _ensure_pool()
        return {"warmed": True, "duration_ms": round((time.time() - t0) * 1000)}
    except Exception as exc:
        logger.exception("Warmup hatası: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ─── POST /api/llm-agent/cache/clear ──────────────────────────────────────────

@router.post("/cache/clear")
def llm_agent_cache_clear(
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """DOM cache'i temizler."""
    with _DOM_CACHE_LOCK:
        removed = len(_DOM_CACHE)
        _DOM_CACHE.clear()
    return {"cleared": True, "entries_removed": removed}


# ─── POST /api/llm-agent/sessions/cleanup ─────────────────────────────────────

@router.post("/sessions/cleanup")
def llm_agent_sessions_cleanup(
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Tüm orphaned session'ları kapatır."""
    with _SESSIONS_LOCK:
        session_ids = list(_SESSIONS.keys())

    closed = 0
    errors = 0
    for sid in session_ids:
        try:
            with _SESSIONS_LOCK:
                session = _SESSIONS.pop(sid, None)
            if session is None:
                continue
            worker: PlaywrightWorker = session.get("worker")
            if worker:
                def _close_page(page=session.get("page")):
                    if page:
                        try:
                            page.close()
                        except Exception:
                            pass
                worker.run(_close_page)
            closed += 1
        except Exception:
            errors += 1

    logger.info("Session cleanup: %d kapatıldı, %d hata", closed, errors)
    return {"closed": closed, "errors": errors, "total": len(session_ids)}


# ─── GET /api/llm-agent/stats ─────────────────────────────────────────────────

@router.get("/stats")
def llm_agent_stats(
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Pool/cache observability metrikleri."""
    with _SESSIONS_LOCK:
        active_sessions = len(_SESSIONS)
    with _POOL_LOCK:
        pool_ready = _POOL.get("browser") is not None and _POOL.get("worker") is not None
        browser_alive: Any = "unknown"
        try:
            w = _POOL.get("worker")
            b = _POOL.get("browser")
            if w and b:
                browser_alive = bool(w.run(lambda: b.is_connected(), timeout=2))
        except Exception:
            browser_alive = "check_failed"
    with _DOM_CACHE_LOCK:
        cache_entries = len(_DOM_CACHE)
        cache_urls = [_DOM_CACHE.get(k, (0, {}))[0] for k in list(_DOM_CACHE.keys())[:10]]
        now = time.time()
        cache_ages_s = [round(now - ts, 1) for ts in cache_urls]
    return {
        "pool": {
            "ready": pool_ready,
            "browser_alive": browser_alive,
            "worker_thread_name": (_POOL["worker"]._thread.name if _POOL.get("worker") else None),
        },
        "sessions": {"active": active_sessions},
        "dom_cache": {
            "entries": cache_entries,
            "cap": 50,
            "ttl_sec": _DOM_CACHE_TTL_SEC,
            "ages_sec_sample": cache_ages_s[:10],
        },
        "uptime_ts": time.time(),
    }


# ─── POST /api/llm-agent/start ────────────────────────────────────────────────

@router.post("/start", status_code=status.HTTP_200_OK)
def llm_agent_start(
    body: StartRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Yeni browser oturumu başlatır (veya mevcut birini yeniden kullanır)."""
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    credentials = body.credentials
    skip_initial_navigation = body.skip_initial_navigation
    reuse_session_id = body.reuse_session_id

    # ── Mevcut session'ı yeniden kullan ──────────────────────────────────────
    if reuse_session_id:
        with _SESSIONS_LOCK:
            old_session = _SESSIONS.get(reuse_session_id)
        if old_session is not None:
            worker = old_session["worker"]
            page = old_session["page"]
            old_console: list = old_session["console_errors"]
            old_network: list = old_session["network_calls"]
            old_net_err: list = old_session["network_errors"]
            reuse_result: dict = {}

            def _pw_reuse():
                old_console.clear()
                old_network.clear()
                old_net_err.clear()
                current = page.url
                if current.split("#")[0].rstrip("/") != url.split("#")[0].rstrip("/"):
                    page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
                    page.wait_for_timeout(WAIT_AFTER_GOTO_MS)
                reuse_result["screenshot_b64"] = _take_screenshot(page)
                reuse_result["page_info"] = _get_page_info(page)

            try:
                worker.run(_pw_reuse, timeout=TIMEOUT_PW_INIT_SEC)
            except Exception as exc:
                logger.warning("Session reuse navigasyon hatası: %s — yeni session açılıyor", exc)
            else:
                new_session_id = str(uuid.uuid4())
                new_session = {
                    "context": old_session["context"],
                    "page": page,
                    "worker": worker,
                    "console_errors": old_console,
                    "network_calls": old_network,
                    "network_errors": old_net_err,
                    "start_time": time.time(),
                    "reused_from": reuse_session_id,
                }
                with _SESSIONS_LOCK:
                    _SESSIONS[new_session_id] = new_session
                logger.info("LLM Agent session yeniden kullanıldı: %s → %s", reuse_session_id, new_session_id)
                return {
                    "session_id": new_session_id,
                    "screenshot_b64": reuse_result["screenshot_b64"],
                    "page_info": reuse_result["page_info"],
                    "reused": True,
                }

    session_id = str(uuid.uuid4())
    console_errors: list = []
    network_calls: list = []
    network_errors: list = []
    _request_start_times: dict = {}
    init_result: dict = {}

    try:
        pool = _ensure_pool()
    except Exception as exc:
        logger.exception("Browser pool init başarısız: %s", exc)
        raise HTTPException(status_code=500, detail=f"Browser pool başlatılamadı: {exc}")

    worker = pool["worker"]
    browser = pool["browser"]

    def _pw_init():
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="tr-TR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        def _on_console(msg):
            if msg.type in ("error", "warning"):
                console_errors.append({
                    "type": msg.type,
                    "text": msg.text[:500],
                    "url": page.url,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                })

        def _on_request(req):
            _request_start_times[req.url] = time.time()

        def _on_response(res):
            start = _request_start_times.pop(res.url, time.time())
            duration_ms = round((time.time() - start) * 1000)
            entry = {
                "url": res.url[:300],
                "method": res.request.method,
                "status": res.status,
                "duration_ms": duration_ms,
                "is_error": res.status >= 400,
                "page_url": page.url,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            network_calls.append(entry)
            if res.status >= 400:
                network_errors.append(entry)

        page.on("console", _on_console)
        page.on("request", _on_request)
        page.on("response", _on_response)

        if credentials and credentials.login_url:
            try:
                page.goto(credentials.login_url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
                page.wait_for_timeout(WAIT_AFTER_GOTO_MS)
                if credentials.username_selector and credentials.username:
                    page.fill(credentials.username_selector, credentials.username)
                if credentials.password_selector and credentials.password:
                    page.fill(credentials.password_selector, credentials.password)
                if credentials.submit_selector:
                    page.click(credentials.submit_selector)
                    page.wait_for_timeout(WAIT_AFTER_LOGIN_MS)
            except Exception as login_exc:
                logger.warning("LLM Agent login atlandı: %s", login_exc)

        if not skip_initial_navigation:
            page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            page.wait_for_timeout(WAIT_AFTER_GOTO_MS)

        init_result["context"] = context
        init_result["page"] = page
        init_result["screenshot_b64"] = _take_screenshot(page)
        init_result["page_info"] = _get_page_info(page)

    try:
        worker.run(_pw_init, timeout=TIMEOUT_PW_INIT_SEC)
    except Exception as exc:
        logger.exception("LLM Agent start hatası: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    session = {
        "context": init_result["context"],
        "page": init_result["page"],
        "worker": worker,
        "console_errors": console_errors,
        "network_calls": network_calls,
        "network_errors": network_errors,
        "start_time": time.time(),
    }
    with _SESSIONS_LOCK:
        _SESSIONS[session_id] = session

    return {
        "session_id": session_id,
        "screenshot_b64": init_result["screenshot_b64"],
        "page_info": init_result["page_info"],
    }


# ─── GET /api/llm-agent/{session_id}/dom ──────────────────────────────────────

@router.get("/{session_id}/dom")
def llm_agent_dom(
    session_id: str,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Deep DOM analizi — yapılandırılmış sayfa verisini döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]

    try:
        current_url = worker.run(lambda: page.url, timeout=3)
    except Exception:
        current_url = ""

    cached = _dom_cache_get(current_url) if current_url else None
    if cached is not None:
        cached["console_errors"] = session["console_errors"][-5:]
        cached["network_errors"] = session["network_errors"][-5:]
        cached["_cache_hit"] = True
        return cached

    def _dom():
        data = _deep_dom_analysis(page)
        data["console_errors"] = session["console_errors"][-5:]
        data["network_errors"] = session["network_errors"][-5:]
        return data

    try:
        dom = worker.run(_dom, timeout=TIMEOUT_PW_DOM_SEC)
        if current_url:
            cacheable = {k: v for k, v in dom.items() if k not in ("console_errors", "network_errors")}
            _dom_cache_set(current_url, cacheable)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return dom


# ─── POST /api/llm-agent/{session_id}/act ─────────────────────────────────────

@router.post("/{session_id}/act")
def llm_agent_act(
    session_id: str,
    body: ActRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Bir browser aksiyonu çalıştırır."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    action_type = body.type
    selector = body.selector
    value = body.value

    worker = session["worker"]
    page = session["page"]
    console_before = len(session["console_errors"])

    act_result: dict = {}

    def _act():
        prev_url = page.url
        error_msg = None
        extracted_text = ""
        nonlocal_links = []

        try:
            dom_count_before = page.evaluate("() => document.querySelectorAll('*').length")
        except Exception:
            dom_count_before = 0

        try:
            if action_type == "click":
                page.click(selector, timeout=6000)
            elif action_type in ("fill", "type_text"):
                if action_type == "type_text":
                    page.triple_click(selector, timeout=5000)
                page.fill(selector, value, timeout=6000)
            elif action_type == "clear_and_fill":
                page.click(selector, timeout=5000)
                page.keyboard.press("Control+A")
                page.keyboard.press("Delete")
                page.type(selector, value, delay=30)
            elif action_type == "navigate":
                page.goto(value, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            elif action_type == "navigate_back":
                page.go_back(wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            elif action_type == "scroll":
                amount = int(value) if value and str(value).lstrip("-").isdigit() else 400
                page.evaluate(f"window.scrollBy(0, {amount})")
            elif action_type == "scroll_to_top":
                page.evaluate("window.scrollTo(0, 0)")
            elif action_type == "hover":
                page.hover(selector, timeout=5000)
            elif action_type == "press_key":
                page.keyboard.press(value or "Tab")
            elif action_type == "select_option":
                page.select_option(selector, value, timeout=5000)
            elif action_type == "double_click":
                page.dblclick(selector, timeout=6000)
            elif action_type == "right_click":
                page.click(selector, button="right", timeout=5000)
            elif action_type == "get_text":
                el = page.query_selector(selector)
                extracted_text = el.inner_text().strip()[:500] if el else ""
            elif action_type == "fuzz_input":
                fuzz_payloads = {
                    "xss":       "<script>alert('xss')</script>",
                    "xss2":      '"><img src=x onerror=alert(1)>',
                    "xss3":      "javascript:alert(1)",
                    "sqli":      "' OR 1=1--",
                    "sqli2":     '" OR "1"="1',
                    "sqli3":     "'; DROP TABLE users--",
                    "long":      "A" * 10000,
                    "unicode":   "ÜüİışĞğŞşÇçÖö" * 100,
                    "special":   "!@#$%^&*()_+-=[]{}|;':\",./<>?",
                    "null":      "\x00\x00\x00",
                    "crlf":      "value\r\nX-Injected: header",
                    "empty":     "",
                    "whitespace": "   ",
                    "ssti":      "{{7*7}}\${7*7}#{7*7}",
                }
                payload = fuzz_payloads.get(value, value)
                page.fill(selector, payload, timeout=6000)
                page.wait_for_timeout(500)
            elif action_type == "screenshot_full":
                pass
            elif action_type == "extract_links":
                pass
            elif action_type == "assert_visible":
                el = page.query_selector(selector)
                if el is None or not el.is_visible():
                    error_msg = f"Element görünür değil: {selector}"
            elif action_type == "wait_for_text":
                page.wait_for_function(
                    f"() => document.body.innerText.includes({json.dumps(value)})",
                    timeout=5000,
                )
            elif action_type == "wait_for_selector":
                page.wait_for_selector(selector, timeout=6000)
            elif action_type == "done":
                pass
            else:
                error_msg = f"Bilinmeyen aksiyon türü: {action_type}"

            if not error_msg:
                page.wait_for_timeout(WAIT_AFTER_GOTO_MS)
        except Exception as exc:
            error_msg = str(exc)[:300]
            logger.debug("LLM Agent act [%s %s]: %s", action_type, selector, exc)

        if action_type == "extract_links":
            try:
                nonlocal_links = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.textContent.trim().slice(0,60),
                    href: a.href,
                    internal: a.href.startsWith(window.location.origin),
                })).filter(l => l.href && !l.href.startsWith('javascript:')).slice(0,30)""")
            except Exception:
                nonlocal_links = []

        if action_type == "screenshot_full":
            try:
                raw = page.screenshot(type="jpeg", quality=65, full_page=True)
                screenshot_b64 = base64.b64encode(raw).decode()
            except Exception:
                screenshot_b64 = _take_screenshot(page)
        else:
            screenshot_b64 = _take_screenshot(page)

        try:
            dom_count_after = page.evaluate("() => document.querySelectorAll('*').length")
            dom_changes = abs(dom_count_after - dom_count_before)
        except Exception:
            dom_changes = 0

        cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 3))
        act_result["success"] = error_msg is None
        act_result["screenshot_b64"] = screenshot_b64
        act_result["url"] = page.url
        act_result["url_changed"] = page.url != prev_url
        act_result["console_errors"] = session["console_errors"][console_before:]
        act_result["network_errors"] = [
            e for e in session["network_errors"]
            if e.get("timestamp", "") > cutoff
        ]
        act_result["dom_changes"] = dom_changes
        act_result["links"] = nonlocal_links if action_type == "extract_links" else []
        act_result["extracted_text"] = extracted_text if action_type == "get_text" else ""
        if error_msg:
            act_result["error"] = error_msg

    try:
        worker.run(_act, timeout=TIMEOUT_PW_ACT_SEC + 20)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return act_result


# ─── GET /api/llm-agent/{session_id}/snapshot ─────────────────────────────────

@router.get("/{session_id}/snapshot")
def llm_agent_snapshot(
    session_id: str,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Screenshot + url + title döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]

    def _snap():
        return {
            "screenshot_b64": _take_screenshot(page),
            "url": page.url,
            "title": page.title(),
        }

    try:
        return worker.run(_snap, timeout=TIMEOUT_PW_SNAPSHOT_SEC)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── GET /api/llm-agent/{session_id}/network ──────────────────────────────────

@router.get("/{session_id}/network")
def llm_agent_network(
    session_id: str,
    _auth: Annotated[None, Depends(_require_internal_auth)],
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    """Session'ın network çağrı loglarını döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    calls = session["network_calls"][-limit:]
    errors = session["network_errors"][-20:]
    return {
        "calls": calls,
        "errors": errors,
        "total_calls": len(session["network_calls"]),
        "error_rate": round(len(errors) / max(len(session["network_calls"]), 1) * 100, 1),
        "unique_hosts": list(set(c["url"].split("/")[2] for c in calls if "/" in c.get("url", ""))),
    }


# ─── GET /api/llm-agent/{session_id}/console ──────────────────────────────────

@router.get("/{session_id}/console")
def llm_agent_console(
    session_id: str,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Session'ın console mesajlarını döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    messages = session["console_errors"]
    return {
        "messages": messages[-30:],
        "errors": [m for m in messages if m["type"] == "error"],
        "warnings": [m for m in messages if m["type"] == "warning"],
        "total": len(messages),
    }


# ─── GET /api/llm-agent/{session_id}/storage ──────────────────────────────────

@router.get("/{session_id}/storage")
def llm_agent_storage(
    session_id: str,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """LocalStorage, sessionStorage ve cookie bilgilerini döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]

    def _storage():
        try:
            local_storage = page.evaluate("""() => {
                const items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const k = localStorage.key(i);
                    items[k] = localStorage.getItem(k)?.slice(0, 200);
                }
                return items;
            }""")
        except Exception:
            local_storage = {}
        try:
            session_storage = page.evaluate("""() => {
                const items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const k = sessionStorage.key(i);
                    items[k] = sessionStorage.getItem(k)?.slice(0, 200);
                }
                return items;
            }""")
        except Exception:
            session_storage = {}
        try:
            cookies = page.context.cookies()
        except Exception:
            cookies = []
        sensitive_keys = [
            k for k in list(local_storage.keys()) + list(session_storage.keys())
            if any(s in k.lower() for s in ["token", "auth", "password", "secret", "key", "jwt", "session"])
        ]
        return {
            "local_storage": local_storage,
            "session_storage": session_storage,
            "cookies": [
                {
                    "name": c["name"],
                    "httpOnly": c.get("httpOnly"),
                    "secure": c.get("secure"),
                    "sameSite": c.get("sameSite"),
                }
                for c in cookies
            ],
            "sensitive_keys_found": sensitive_keys,
        }

    try:
        return worker.run(_storage, timeout=TIMEOUT_PW_DOM_SEC)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── DELETE /api/llm-agent/{session_id} ───────────────────────────────────────

@router.delete("/{session_id}")
def llm_agent_close(
    session_id: str,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Browser context'i kapatır; pool worker'ı canlı tutar."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.pop(session_id, None)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    errors: list = []
    worker = session.get("worker")

    def _cleanup():
        ctx = session.get("context")
        if ctx is not None:
            try:
                ctx.close()
            except Exception as exc:
                errors.append(str(exc))

    if worker:
        try:
            worker.run(_cleanup, timeout=TIMEOUT_PW_CLOSE_SEC)
        except Exception as exc:
            errors.append(str(exc))
        # Pool worker'ı STOP ETMİYORUZ

    return {"closed": True, "session_id": session_id, "cleanup_errors": errors}


# ─── GET /api/llm-agent/sessions ──────────────────────────────────────────────

@router.get("/sessions")
def llm_agent_list_sessions(
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Tüm aktif session'ları ve temel meta verilerini döner."""
    with _SESSIONS_LOCK:
        sessions = {
            sid: {
                "session_id": sid,
                "start_time": s.get("start_time"),
                "reused_from": s.get("reused_from"),
                "console_error_count": len(s.get("console_errors", [])),
                "network_call_count": len(s.get("network_calls", [])),
                "network_error_count": len(s.get("network_errors", [])),
            }
            for sid, s in _SESSIONS.items()
        }
    return {"sessions": sessions, "total": len(sessions)}


# ─── GET /api/llm-agent/{session_id} ──────────────────────────────────────────

@router.get("/{session_id}")
def llm_agent_get_session(
    session_id: str,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Belirli bir session'ın durumunu ve anlık sayfa bilgisini döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]

    try:
        page_info = worker.run(lambda: _get_page_info(page), timeout=5)
    except Exception:
        page_info = {}

    return {
        "session_id": session_id,
        "start_time": session.get("start_time"),
        "reused_from": session.get("reused_from"),
        "page_info": page_info,
        "console_error_count": len(session.get("console_errors", [])),
        "network_call_count": len(session.get("network_calls", [])),
        "network_error_count": len(session.get("network_errors", [])),
    }


# ─── POST /api/llm-agent/{session_id}/screenshot ──────────────────────────────

@router.post("/{session_id}/screenshot")
def llm_agent_screenshot(
    session_id: str,
    body: ScreenshotRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Özelleştirilmiş screenshot alır (quality ve full_page parametreleri ile)."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]

    def _screenshot():
        try:
            raw = page.screenshot(
                type="jpeg",
                quality=body.quality,
                full_page=body.full_page,
            )
            return {
                "screenshot_b64": base64.b64encode(raw).decode(),
                "url": page.url,
                "title": page.title(),
                "full_page": body.full_page,
            }
        except Exception as exc:
            raise RuntimeError(f"Screenshot alınamadı: {exc}") from exc

    try:
        return worker.run(_screenshot, timeout=TIMEOUT_PW_SNAPSHOT_SEC)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── POST /api/llm-agent/{session_id}/navigate ────────────────────────────────

@router.post("/{session_id}/navigate")
def llm_agent_navigate(
    session_id: str,
    body: NavigateRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Sayfayı belirtilen URL'e yönlendirir ve screenshot döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    worker = session["worker"]
    page = session["page"]

    def _navigate():
        prev_url = page.url
        page.goto(url, wait_until=body.wait_until, timeout=GOTO_TIMEOUT_MS)
        page.wait_for_timeout(WAIT_AFTER_GOTO_MS)
        return {
            "success": True,
            "url": page.url,
            "prev_url": prev_url,
            "url_changed": page.url != prev_url,
            "title": page.title(),
            "screenshot_b64": _take_screenshot(page),
        }

    try:
        return worker.run(_navigate, timeout=TIMEOUT_PW_INIT_SEC)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── POST /api/llm-agent/{session_id}/find ────────────────────────────────────

@router.post("/{session_id}/find")
def llm_agent_find_element(
    session_id: str,
    body: FindElementRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """CSS selector ile element(leri) bulur; konum, görünürlük ve metin bilgisini döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]

    def _find():
        if body.all:
            elements = page.query_selector_all(body.selector)
            result = []
            for el in elements[:20]:
                try:
                    bbox = el.bounding_box()
                    result.append({
                        "tag": el.evaluate("el => el.tagName.toLowerCase()"),
                        "text": el.inner_text().strip()[:200],
                        "visible": el.is_visible(),
                        "enabled": el.is_enabled(),
                        "bounding_box": bbox,
                    })
                except Exception:
                    pass
            return {"found": len(result) > 0, "count": len(result), "elements": result}
        else:
            el = page.query_selector(body.selector)
            if el is None:
                return {"found": False, "element": None}
            try:
                bbox = el.bounding_box()
                return {
                    "found": True,
                    "element": {
                        "tag": el.evaluate("el => el.tagName.toLowerCase()"),
                        "text": el.inner_text().strip()[:200],
                        "visible": el.is_visible(),
                        "enabled": el.is_enabled(),
                        "bounding_box": bbox,
                    },
                }
            except Exception as exc:
                return {"found": True, "element": None, "error": str(exc)}

    try:
        return worker.run(_find, timeout=TIMEOUT_PW_DOM_SEC)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── POST /api/llm-agent/{session_id}/evaluate ────────────────────────────────

@router.post("/{session_id}/evaluate")
def llm_agent_evaluate(
    session_id: str,
    body: EvaluateRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Sayfada keyfi bir JavaScript ifadesi çalıştırır ve sonucu döner."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]

    def _evaluate():
        try:
            result = page.evaluate(body.expression)
            return {"success": True, "result": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)[:500]}

    try:
        return worker.run(_evaluate, timeout=TIMEOUT_PW_DOM_SEC)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── POST /api/llm-agent/{session_id}/type ────────────────────────────────────

@router.post("/{session_id}/type")
def llm_agent_type(
    session_id: str,
    body: TypeRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Bir input element'e metin girer; isteğe bağlı olarak önce içeriği temizler."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]
    console_before = len(session["console_errors"])

    def _type():
        try:
            if body.clear_first:
                page.click(body.selector, timeout=5000)
                page.keyboard.press("Control+A")
                page.keyboard.press("Delete")
            if body.delay_ms > 0:
                page.type(body.selector, body.text, delay=body.delay_ms)
            else:
                page.fill(body.selector, body.text, timeout=6000)
            page.wait_for_timeout(WAIT_AFTER_GOTO_MS)
            return {
                "success": True,
                "selector": body.selector,
                "text_length": len(body.text),
                "screenshot_b64": _take_screenshot(page),
                "url": page.url,
                "console_errors": session["console_errors"][console_before:],
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc)[:300],
                "screenshot_b64": _take_screenshot(page),
                "url": page.url,
            }

    try:
        return worker.run(_type, timeout=TIMEOUT_PW_ACT_SEC)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── POST /api/llm-agent/{session_id}/click ───────────────────────────────────

@router.post("/{session_id}/click")
def llm_agent_click(
    session_id: str,
    body: ClickRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Bir element'e tıklar; navigasyon gerçekleşip gerçekleşmediğini raporlar."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]
    console_before = len(session["console_errors"])

    def _click():
        prev_url = page.url
        try:
            if body.double:
                page.dblclick(body.selector, timeout=body.timeout_ms)
            else:
                page.click(
                    body.selector,
                    button=body.button,
                    timeout=body.timeout_ms,
                )
            page.wait_for_timeout(WAIT_AFTER_GOTO_MS)
            return {
                "success": True,
                "selector": body.selector,
                "url": page.url,
                "prev_url": prev_url,
                "url_changed": page.url != prev_url,
                "screenshot_b64": _take_screenshot(page),
                "console_errors": session["console_errors"][console_before:],
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc)[:300],
                "screenshot_b64": _take_screenshot(page),
                "url": page.url,
            }

    try:
        return worker.run(_click, timeout=TIMEOUT_PW_ACT_SEC)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── GET /api/llm-agent/{session_id}/page-info ────────────────────────────────

@router.get("/{session_id}/page-info")
def llm_agent_page_info(
    session_id: str,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Hızlı sayfa meta bilgisi döner: title, url, etkileşimli element sayıları."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]

    try:
        return worker.run(lambda: _get_page_info(page), timeout=5)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── POST /api/llm-agent/{session_id}/wait ────────────────────────────────────

@router.post("/{session_id}/wait")
def llm_agent_wait(
    session_id: str,
    body: WaitRequest,
    _auth: Annotated[None, Depends(_require_internal_auth)],
) -> dict:
    """Bir koşul gerçekleşene kadar bekler: selector, text, network_idle veya timeout."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")

    worker = session["worker"]
    page = session["page"]
    timeout_ms = body.timeout_ms

    def _wait():
        try:
            if body.kind == "selector":
                page.wait_for_selector(body.value, timeout=timeout_ms)
            elif body.kind == "text":
                page.wait_for_function(
                    f"() => document.body.innerText.includes({json.dumps(body.value)})",
                    timeout=timeout_ms,
                )
            elif body.kind == "network_idle":
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            elif body.kind == "timeout":
                ms = int(body.value) if body.value and body.value.isdigit() else timeout_ms
                page.wait_for_timeout(ms)
            else:
                return {"success": False, "error": f"Bilinmeyen wait kind: {body.kind}"}
            return {
                "success": True,
                "kind": body.kind,
                "url": page.url,
                "screenshot_b64": _take_screenshot(page),
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc)[:300],
                "kind": body.kind,
                "url": page.url,
            }

    try:
        return worker.run(_wait, timeout=timeout_ms / 1000 + 5)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
