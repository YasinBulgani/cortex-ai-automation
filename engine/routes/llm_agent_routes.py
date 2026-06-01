"""
LLM Agent Routes — ReAct-style browser agent oturumları.

Her oturum bir Playwright browser/context/page üçlüsünü saklar.
Endpoint'ler backend TSPM router tarafından iç key ile çağrılır.

Threading notu:
  Flask threaded=False kullanılıyor (Playwright threading fix için). Ama
  Playwright sync API, asyncio event loop'u olan bir thread'de çalışamaz.
  Önceki session'dan kalan asyncio state sonraki start() çağrısını bozuyordu.
  Çözüm: Her session için ayrı bir daemon thread (PlaywrightWorker). Flask
  thread'i hiç Playwright çağrısı yapmaz — sadece work item'ları kuyruğa
  ekler ve sonucu bekler.
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


# ─── Timeout configuration (env-overridable) ──────────────────────────────────
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default

# Browser launch + ilk page.goto'ya verilen toplam süre (warm pool ile düşürülebilir)
TIMEOUT_PW_INIT_SEC = _env_int("LLM_AGENT_PW_INIT_TIMEOUT_SEC", 25)
# Tek bir /act çağrısı için worker timeout
TIMEOUT_PW_ACT_SEC = _env_int("LLM_AGENT_PW_ACT_TIMEOUT_SEC", 15)
# DOM analizi için worker timeout
TIMEOUT_PW_DOM_SEC = _env_int("LLM_AGENT_PW_DOM_TIMEOUT_SEC", 15)
# Snapshot/screenshot için worker timeout
TIMEOUT_PW_SNAPSHOT_SEC = _env_int("LLM_AGENT_PW_SNAPSHOT_TIMEOUT_SEC", 10)
# /close cleanup için worker timeout
TIMEOUT_PW_CLOSE_SEC = _env_int("LLM_AGENT_PW_CLOSE_TIMEOUT_SEC", 10)
# Sayfa goto sonrası kısa bekleme (client-side hydration için)
WAIT_AFTER_GOTO_MS = _env_int("LLM_AGENT_WAIT_AFTER_GOTO_MS", 600)
# Login sonrası bekleme
WAIT_AFTER_LOGIN_MS = _env_int("LLM_AGENT_WAIT_AFTER_LOGIN_MS", 1500)
# Browser launch + page navigation page.goto timeout
GOTO_TIMEOUT_MS = _env_int("LLM_AGENT_GOTO_TIMEOUT_MS", 20000)

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

llm_agent_bp = Blueprint("llm_agent", __name__)

# ─── Thread-safe session store ────────────────────────────────────────────────
_SESSIONS: dict[str, dict] = {}
_SESSIONS_LOCK = threading.Lock()

# ─── Warm browser pool ────────────────────────────────────────────────────────
# Engine-wide singleton: ilk /start çağrısında Playwright + Chromium başlatılır
# ve _POOL'da tutulur. Sonraki /start çağrıları sadece yeni context+page açar
# (~1-3s), tam initialization gerekmez (~25-30s tasarruf).
#
# Tüm Playwright çağrıları aynı worker thread'inde çalışmalı (sync API +
# asyncio constraint), bu yüzden pool tek bir PlaywrightWorker paylaşır.
_POOL: dict = {"pw": None, "browser": None, "worker": None}
_POOL_LOCK = threading.Lock()

# ─── DOM cache ────────────────────────────────────────────────────────────────
# Aynı URL'i 5 dakika içinde tekrar test ederken DOM analizinin pahalı
# JS evaluate adımını atlamak için. Cache anahtarı: page.url'in fragment'sız
# hâli. Console/network listeleri session bazlı kaldığı için cache değil.
_DOM_CACHE: dict[str, tuple[float, dict]] = {}
_DOM_CACHE_LOCK = threading.Lock()
_DOM_CACHE_TTL_SEC = 300


def _dom_cache_key(url: str) -> str:
    # Fragment ve sondaki / atılır; aynı sayfanın varyantları tek key'e mapleniyor
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
        # Defensive copy: tüketici listeleri değiştirebilir
        return {**data}


def _dom_cache_set(url: str, data: dict) -> None:
    with _DOM_CACHE_LOCK:
        _DOM_CACHE[_dom_cache_key(url)] = (time.time(), {**data})
        # Cache boyutu kontrolü (cap: 50 farklı URL)
        if len(_DOM_CACHE) > 50:
            oldest = min(_DOM_CACHE.items(), key=lambda kv: kv[1][0])[0]
            _DOM_CACHE.pop(oldest, None)


# ─── Per-session Playwright worker thread ─────────────────────────────────────
# Her session, Playwright işlemlerini yürütmek için kendi daemon thread'ine
# sahiptir. Bu thread sıfırdan başlar, asyncio event loop'u yoktur ve
# Playwright sync API için her zaman güvenlidir.

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
                break  # poison pill — kapat
            fn, result_q = item
            try:
                result_q.put(("ok", fn()))
            except Exception as exc:  # noqa: BLE001
                result_q.put(("err", exc))

    def run(self, fn, timeout: float = 60):
        """fn'i Playwright thread'inde çalıştır; sonucu döndür veya hatayı yükselt."""
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
        """Worker thread'ini kapat (poison pill gönder)."""
        self._q.put(None)
        self._thread.join(timeout=10)


# ─── Pool init / health check ─────────────────────────────────────────────────

def _ensure_pool() -> dict:
    """Pool'da warm browser var mı kontrol et, yoksa başlat. Thread-safe.

    Browser ölmüşse otomatik yeniden başlatır (örn. crash sonrası).
    Returns: _POOL dict (pw, browser, worker hep dolu).
    """
    with _POOL_LOCK:
        worker = _POOL.get("worker")
        browser = _POOL.get("browser")

        # Browser yaşıyor mu kontrol et (worker üzerinden)
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

        # Yeniden başlat: önce eski worker'ı temizle
        if worker is not None:
            try:
                worker.stop()
            except Exception:
                pass

        new_worker = PlaywrightWorker()

        def _boot():
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            return {"pw": pw, "browser": browser}

        try:
            boot = new_worker.run(_boot, timeout=40)
        except Exception:
            new_worker.stop()
            raise

        _POOL["pw"] = boot["pw"]
        _POOL["browser"] = boot["browser"]
        _POOL["worker"] = new_worker
        return _POOL


# ─── Auth helper ──────────────────────────────────────────────────────────────

def _require_internal_auth():
    key = request.headers.get("X-Internal-Key", "")
    expected = os.environ.get("ENGINE_INTERNAL_KEY", "")
    if not key or key != expected:
        return True, (jsonify({"error": "Unauthorized"}), 401)
    return False, None


# ─── Screenshot helper ────────────────────────────────────────────────────────
# NOT: Bu fonksiyon Playwright thread'inden çağrılmalıdır.

def _take_screenshot(page) -> str:
    try:
        raw = page.screenshot(type="jpeg", quality=65, full_page=False)
        return base64.b64encode(raw).decode()
    except Exception as exc:
        logger.warning("Screenshot alınamadı: %s", exc)
        return ""


# ─── Page info helper (basic) ─────────────────────────────────────────────────
# NOT: Bu fonksiyon Playwright thread'inden çağrılmalıdır.

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


# ─── Deep DOM analysis ────────────────────────────────────────────────────────

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

    // Buttons
    const buttons = Array.from(document.querySelectorAll(
        'button, [role="button"], input[type="submit"], input[type="button"], a.btn, a.button'
    )).filter(isVisible).slice(0, 20).map(el => ({
        text: (el.textContent || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 80),
        selector: getSelector(el),
        tag: el.tagName.toLowerCase(),
        disabled: el.disabled || false,
    }));

    // Inputs
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

    // Navigation links
    const navLinks = Array.from(document.querySelectorAll(
        'nav a, header a, [role="navigation"] a, .nav a, .navbar a, .menu a'
    )).filter(isVisible).slice(0, 15).map(el => ({
        text: el.textContent.trim().slice(0, 60),
        href: el.href,
        selector: getSelector(el),
        active: el.classList.contains('active') || el.ariaCurrent === 'page',
    }));

    // Alerts / errors / notifications visible on page
    const alerts = Array.from(document.querySelectorAll(
        '[class*="error"], [class*="alert"], [class*="warning"], [class*="danger"], [role="alert"], .toast, .notification, .snackbar, [class*="message"]'
    )).filter(el => isVisible(el) && el.textContent.trim().length > 3).slice(0, 6).map(el => ({
        text: el.textContent.trim().slice(0, 200),
        type: el.getAttribute('role') || el.className.split(' ').find(c => ['error','alert','warning','danger','success','info'].some(k => c.includes(k))) || 'message',
    }));

    // Forms with their fields
    const forms = Array.from(document.querySelectorAll('form')).slice(0, 3).map(form => ({
        id: form.id || '',
        action: form.action || '',
        method: form.method || 'get',
        field_count: form.querySelectorAll('input:not([type="hidden"]), textarea, select').length,
        submit_text: safe(() => form.querySelector('[type="submit"], button[type="submit"]')?.textContent?.trim() || ''),
    }));

    // Detect page type
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

    // Page text excerpt (for context)
    const textExcerpt = document.body.innerText
        .replace(/\\s+/g, ' ').trim().slice(0, 2000);

    // Headings for structure understanding
    const headings = Array.from(document.querySelectorAll('h1, h2, h3')).slice(0, 8).map(h => ({
        level: parseInt(h.tagName[1]),
        text: h.textContent.trim().slice(0, 80),
    }));

    // Performance
    const perf = safe(() => {
        const nav = performance.getEntriesByType('navigation')[0] || {};
        return {
            load_ms: Math.round(nav.loadEventEnd - nav.startTime) || 0,
            dom_interactive_ms: Math.round(nav.domInteractive - nav.startTime) || 0,
            ttfb_ms: Math.round(nav.responseStart - nav.startTime) || 0,
        };
    }) || {};

    // Technology detection
    const tech = [];
    if (window.__NEXT_DATA__) tech.push({name:'Next.js',category:'framework'});
    if (window.React || document.querySelector('[data-reactroot],[data-react-helmet]')) tech.push({name:'React',category:'framework'});
    if (window.Vue || document.querySelector('[data-v-app]')) tech.push({name:'Vue',category:'framework'});
    if (window.angular || window.ng) tech.push({name:'Angular',category:'framework'});
    if (window.jQuery || window.$) tech.push({name:'jQuery',category:'library'});
    if (document.querySelector('meta[name="generator"]')) tech.push({name:document.querySelector('meta[name="generator"]').content,category:'cms'});
    // Security headers hint (can't check from JS, but check for common CSP nonce)
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


# ─── POST /api/llm-agent/warmup ───────────────────────────────────────────────
# Browser pool'unu manuel tetikler. Backend bunu app startup'ta çağırabilir
# (ya da ilk /start otomatik tetikleyecek).

@llm_agent_bp.route("/api/llm-agent/warmup", methods=["POST"])
def llm_agent_warmup():
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response
    try:
        t0 = time.time()
        _ensure_pool()
        return jsonify({"warmed": True, "duration_ms": round((time.time() - t0) * 1000)})
    except Exception as exc:
        logger.exception("Warmup hatası: %s", exc)
        return jsonify({"warmed": False, "error": str(exc)}), 500


# ─── POST /api/llm-agent/cache/clear ──────────────────────────────────────────
# DOM cache'i manuel temizle (test scenario'ları arası, cache invalidation için).

@llm_agent_bp.route("/api/llm-agent/cache/clear", methods=["POST"])
def llm_agent_cache_clear():
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response
    with _DOM_CACHE_LOCK:
        removed = len(_DOM_CACHE)
        _DOM_CACHE.clear()
    return jsonify({"cleared": True, "entries_removed": removed})


# ─── POST /api/llm-agent/sessions/cleanup ─────────────────────────────────────
# Yarım kalan (orphaned) tüm oturumları kapat. Backend yeniden başlarsa çağrılır.

@llm_agent_bp.route("/api/llm-agent/sessions/cleanup", methods=["POST"])
def llm_agent_sessions_cleanup():
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response

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
    return jsonify({"closed": closed, "errors": errors, "total": len(session_ids)})


# ─── GET /api/llm-agent/stats ─────────────────────────────────────────────────
# Pool/cache observability. Dashboard veya health probe için.

@llm_agent_bp.route("/api/llm-agent/stats", methods=["GET"])
def llm_agent_stats():
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response
    with _SESSIONS_LOCK:
        active_sessions = len(_SESSIONS)
    with _POOL_LOCK:
        pool_ready = _POOL.get("browser") is not None and _POOL.get("worker") is not None
        # Check browser is_connected (non-blocking; skip if worker busy)
        browser_alive = "unknown"
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
        # Age of each entry
        now = time.time()
        cache_ages_s = [round(now - ts, 1) for ts in cache_urls]
    return jsonify({
        "pool": {
            "ready": pool_ready,
            "browser_alive": browser_alive,
            "worker_thread_name": (_POOL.get("worker")._thread.name if _POOL.get("worker") else None),
        },
        "sessions": {
            "active": active_sessions,
        },
        "dom_cache": {
            "entries": cache_entries,
            "cap": 50,
            "ttl_sec": _DOM_CACHE_TTL_SEC,
            "ages_sec_sample": cache_ages_s[:10],
        },
        "uptime_ts": time.time(),
    })


# Engine import edildiğinde arka planda warmup başlat: ilk gerçek
# kullanıcı isteğine kadar pool hazır olur. Hata olursa sessizce geç —
# normal lazy init devreye girer.
def _background_warmup():
    try:
        time.sleep(2)  # engine'in app context'i tam ayağa kalksın
        _ensure_pool()
        logger.info("LLM Agent browser pool warmup tamamlandı")
    except Exception as exc:
        logger.warning("Background warmup başarısız (lazy init devreye girer): %s", exc)


threading.Thread(target=_background_warmup, daemon=True, name="llm-pool-warmup").start()


# ─── POST /api/llm-agent/start ────────────────────────────────────────────────

@llm_agent_bp.route("/api/llm-agent/start", methods=["POST"])
def llm_agent_start():
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response

    data = request.json or {}
    url = data.get("url", "").strip()
    credentials = data.get("credentials")
    # Hızlandırma: aynı URL'i ardışık test ederken navigate atla.
    # Caller backend tarafından gönderilir. Default False (güvenli).
    skip_initial_navigation = bool(data.get("skip_initial_navigation", False))
    # Session yeniden kullanımı: önceki bir session_id verilmişse browser/context
    # kapatılmaz, sadece event logları sıfırlanır ve URL gerekiyorsa navigate edilir.
    # ~1-3s tasarruf (context açma) + TLS handshake tasarrufu.
    reuse_session_id: str | None = data.get("reuse_session_id")

    if not url:
        return jsonify({"error": "URL gereklidir"}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # ── Mevcut session'ı yeniden kullan (warm re-run) ─────────────────────────
    if reuse_session_id:
        with _SESSIONS_LOCK:
            old_session = _SESSIONS.get(reuse_session_id)
        if old_session is not None:
            # Aynı worker ve page üzerinde: log listelerini temizle, navigate et, yeni ID ver
            worker = old_session["worker"]
            page = old_session["page"]
            old_console: list = old_session["console_errors"]
            old_network: list = old_session["network_calls"]
            old_net_err: list = old_session["network_errors"]
            reuse_result: dict = {}

            def _pw_reuse():
                # Logları .clear() ile sıfırla — event handler closure'ları hâlâ bu listeleri gösteriyor
                old_console.clear()
                old_network.clear()
                old_net_err.clear()
                # URL farklıysa navigate et
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
                # Hata durumunda normal yoldan devam et
            else:
                new_session_id = str(uuid.uuid4())
                # Yeni ID → aynı fiziksel session; eski ID'yi de canlı tut
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
                return jsonify({
                    "session_id": new_session_id,
                    "screenshot_b64": reuse_result["screenshot_b64"],
                    "page_info": reuse_result["page_info"],
                    "reused": True,
                })

    session_id = str(uuid.uuid4())

    # Paylaşılan listeler — Flask thread'inde oluşturulur, PW callback'leri tarafından doldurulur
    console_errors: list = []
    network_calls: list = []
    network_errors: list = []
    _request_start_times: dict = {}
    init_result: dict = {}

    # Warm pool'dan paylaşılan worker+browser al; ilk çağrıda ~30s, sonra ~1-3s
    try:
        pool = _ensure_pool()
    except Exception as exc:
        logger.exception("Browser pool init başarısız: %s", exc)
        return jsonify({"error": f"Browser pool başlatılamadı: {exc}"}), 500

    worker = pool["worker"]
    browser = pool["browser"]

    def _pw_init():
        # Pool'daki warm browser üzerinde yeni izole context aç
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

        # Optional login
        if credentials and credentials.get("login_url"):
            try:
                page.goto(credentials["login_url"], wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
                page.wait_for_timeout(WAIT_AFTER_GOTO_MS)
                if credentials.get("username_selector") and credentials.get("username"):
                    page.fill(credentials["username_selector"], credentials["username"])
                if credentials.get("password_selector") and credentials.get("password"):
                    page.fill(credentials["password_selector"], credentials["password"])
                if credentials.get("submit_selector"):
                    page.click(credentials["submit_selector"])
                    page.wait_for_timeout(WAIT_AFTER_LOGIN_MS)
            except Exception as login_exc:
                logger.warning("LLM Agent login atlandı: %s", login_exc)

        # Hızlandırma: skip_initial_navigation=True ise sayfa zaten doğru URL'de
        # olduğunu varsayıp goto'yu atla. Caller bunun garantisini vermelidir.
        if not skip_initial_navigation:
            page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            # WAIT_AFTER_GOTO_MS yeterli — domcontentloaded zaten yüklendi
            page.wait_for_timeout(WAIT_AFTER_GOTO_MS)

        # pw/browser pool'da; sadece session-spesifik objeleri sakla
        init_result["context"] = context
        init_result["page"] = page
        init_result["screenshot_b64"] = _take_screenshot(page)
        init_result["page_info"] = _get_page_info(page)

    try:
        # Warm pool sayesinde sadece context+navigation; TIMEOUT_PW_INIT_SEC yeterli (default 25)
        worker.run(_pw_init, timeout=TIMEOUT_PW_INIT_SEC)
    except Exception as exc:
        logger.exception("LLM Agent start hatası: %s", exc)
        # Pool worker'ı kapatma — başka session'lar kullanıyor olabilir
        return jsonify({"error": str(exc)}), 500

    session = {
        # playwright/browser pool'da paylaşılıyor; session bunlara sahip değil
        "context": init_result["context"],
        "page": init_result["page"],
        "worker": worker,  # shared pool worker
        "console_errors": console_errors,
        "network_calls": network_calls,
        "network_errors": network_errors,
        "start_time": time.time(),
    }
    with _SESSIONS_LOCK:
        _SESSIONS[session_id] = session

    return jsonify({
        "session_id": session_id,
        "screenshot_b64": init_result["screenshot_b64"],
        "page_info": init_result["page_info"],
    })


# ─── GET /api/llm-agent/<session_id>/dom ─────────────────────────────────────

@llm_agent_bp.route("/api/llm-agent/<session_id>/dom", methods=["GET"])
def llm_agent_dom(session_id: str):
    """Deep DOM analysis — returns structured page data for LLM context."""
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response

    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "Oturum bulunamadı"}), 404

    worker = session["worker"]
    page = session["page"]

    # 1) Cache hit kontrolü — URL aynıysa pahalı JS evaluate'i atla
    try:
        current_url = worker.run(lambda: page.url, timeout=3)
    except Exception:
        current_url = ""

    cached = _dom_cache_get(current_url) if current_url else None
    if cached is not None:
        # Console/network listeleri session bazlı — cache'den almıyoruz
        cached["console_errors"] = session["console_errors"][-5:]
        cached["network_errors"] = session["network_errors"][-5:]
        cached["_cache_hit"] = True
        return jsonify(cached)

    def _dom():
        data = _deep_dom_analysis(page)
        data["console_errors"] = session["console_errors"][-5:]
        data["network_errors"] = session["network_errors"][-5:]
        return data

    try:
        dom = worker.run(_dom, timeout=TIMEOUT_PW_DOM_SEC)
        # 2) Başarılı analiz → cache'e koy (console/network hariç)
        if current_url:
            cacheable = {k: v for k, v in dom.items() if k not in ("console_errors", "network_errors")}
            _dom_cache_set(current_url, cacheable)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(dom)


# ─── POST /api/llm-agent/<session_id>/act ────────────────────────────────────

@llm_agent_bp.route("/api/llm-agent/<session_id>/act", methods=["POST"])
def llm_agent_act(session_id: str):
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response

    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "Oturum bulunamadı"}), 404

    data = request.json or {}
    action_type = data.get("type", "")
    selector = data.get("selector", "")
    value = data.get("value", "")

    worker = session["worker"]
    page = session["page"]
    console_before = len(session["console_errors"])

    act_result: dict = {}

    def _act():
        prev_url = page.url
        error_msg = None
        extracted_text = ""
        links: list = []

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
                    # XSS varyantları — farklı encode biçimleri
                    "xss": "<script>alert('xss')</script>",
                    "xss2": '"><img src=x onerror=alert(1)>',
                    "xss3": "javascript:alert(1)",
                    # SQL Injection varyantları
                    "sqli": "' OR 1=1--",
                    "sqli2": '" OR "1"="1',
                    "sqli3": "'; DROP TABLE users--",
                    # Boyut saldırıları
                    "long": "A" * 10000,
                    "unicode": "ÜüİışĞğŞşÇçÖö" * 100,  # Türkçe karakter testi
                    # Özel karakterler
                    "special": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
                    "null": "\x00\x00\x00",  # Null byte injection
                    "crlf": "value\r\nX-Injected: header",  # CRLF injection
                    # Boş değer testi
                    "empty": "",
                    "whitespace": "   ",  # Sadece boşluk
                    # SSTI / template injection
                    "ssti": "{{7*7}}\${7*7}#{7*7}",
                }
                payload = fuzz_payloads.get(value, value)
                page.fill(selector, payload, timeout=6000)
                # Güvenlik testi: submit et ve yanıtı bekle
                page.wait_for_timeout(500)
            elif action_type == "screenshot_full":
                pass  # handled below
            elif action_type == "extract_links":
                pass  # handled below
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
                pass  # sentinel — caller should break
            else:
                error_msg = f"Bilinmeyen aksiyon türü: {action_type}"

            if not error_msg:
                page.wait_for_timeout(WAIT_AFTER_GOTO_MS)
        except Exception as exc:
            error_msg = str(exc)[:300]
            logger.debug("LLM Agent act [%s %s]: %s", action_type, selector, exc)

        # extract_links result
        nonlocal_links = []
        if action_type == "extract_links":
            try:
                nonlocal_links = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.textContent.trim().slice(0,60),
                    href: a.href,
                    internal: a.href.startsWith(window.location.origin),
                })).filter(l => l.href && !l.href.startsWith('javascript:')).slice(0,30)""")
            except Exception:
                nonlocal_links = []

        # screenshot_full uses full_page=True
        if action_type == "screenshot_full":
            try:
                raw = page.screenshot(type="jpeg", quality=65, full_page=True)
                screenshot_b64 = base64.b64encode(raw).decode()
            except Exception:
                screenshot_b64 = _take_screenshot(page)
        else:
            screenshot_b64 = _take_screenshot(page)

        # DOM changes count
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
        # _act içinde navigation+wait olabileceğinden ACT timeout'u biraz daha geniş tutulur
        worker.run(_act, timeout=TIMEOUT_PW_ACT_SEC + 20)
    except Exception as exc:
        return jsonify({"error": str(exc), "success": False}), 500

    return jsonify(act_result)


# ─── GET /api/llm-agent/<session_id>/snapshot ────────────────────────────────

@llm_agent_bp.route("/api/llm-agent/<session_id>/snapshot", methods=["GET"])
def llm_agent_snapshot(session_id: str):
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response

    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "Oturum bulunamadı"}), 404

    worker = session["worker"]
    page = session["page"]

    def _snap():
        return {
            "screenshot_b64": _take_screenshot(page),
            "url": page.url,
            "title": page.title(),
        }

    try:
        result = worker.run(_snap, timeout=TIMEOUT_PW_SNAPSHOT_SEC)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


# ─── GET /api/llm-agent/<session_id>/network ─────────────────────────────────

@llm_agent_bp.route("/api/llm-agent/<session_id>/network", methods=["GET"])
def llm_agent_network(session_id):
    denied, err = _require_internal_auth()
    if denied:
        return err
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Oturum bulunamadı"}), 404
    limit = int(request.args.get("limit", 50))
    calls = session["network_calls"][-limit:]
    errors = session["network_errors"][-20:]
    return jsonify({
        "calls": calls,
        "errors": errors,
        "total_calls": len(session["network_calls"]),
        "error_rate": round(len(errors) / max(len(session["network_calls"]), 1) * 100, 1),
        "unique_hosts": list(set(c["url"].split("/")[2] for c in calls if "/" in c.get("url", ""))),
    })


# ─── GET /api/llm-agent/<session_id>/console ─────────────────────────────────

@llm_agent_bp.route("/api/llm-agent/<session_id>/console", methods=["GET"])
def llm_agent_console(session_id):
    denied, err = _require_internal_auth()
    if denied:
        return err
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Oturum bulunamadı"}), 404
    messages = session["console_errors"]
    return jsonify({
        "messages": messages[-30:],
        "errors": [m for m in messages if m["type"] == "error"],
        "warnings": [m for m in messages if m["type"] == "warning"],
        "total": len(messages),
    })


# ─── GET /api/llm-agent/<session_id>/storage ─────────────────────────────────

@llm_agent_bp.route("/api/llm-agent/<session_id>/storage", methods=["GET"])
def llm_agent_storage(session_id):
    denied, err = _require_internal_auth()
    if denied:
        return err
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Oturum bulunamadı"}), 404

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
        result = worker.run(_storage, timeout=TIMEOUT_PW_DOM_SEC)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


# ─── DELETE /api/llm-agent/<session_id> ──────────────────────────────────────

@llm_agent_bp.route("/api/llm-agent/<session_id>", methods=["DELETE"])
def llm_agent_close(session_id: str):
    denied, err_response = _require_internal_auth()
    if denied:
        return err_response

    with _SESSIONS_LOCK:
        session = _SESSIONS.pop(session_id, None)

    if session is None:
        return jsonify({"error": "Oturum bulunamadı"}), 404

    errors: list = []
    worker = session.get("worker")

    def _cleanup():
        # Sadece context'i kapat — browser/pw pool'da warm kalmalı
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
        # Pool worker'ı STOP ETMİYORUZ — sonraki session'lar için açık tutuluyor

    return jsonify({"closed": True, "session_id": session_id, "cleanup_errors": errors})
