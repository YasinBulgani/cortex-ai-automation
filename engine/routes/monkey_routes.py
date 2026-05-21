"""
Monkey Testing Analist Routes — Super Version
- SSE streaming (real-time ilerleme)
- Video recording (WebM)
- Axe-core WCAG 2.0 A+AA erişilebilirlik denetimi
- JS Heap bellek sızıntısı tespiti
- Visual diff scoring
- Gelişmiş rastgele etkileşim testi
- Performans metrikleri toplama
- Hata kategorilendirme
- AI destekli analiz ve senaryo üretimi
"""
import base64
import json
import logging
import os
import random
import tempfile
import time
import traceback
import uuid
from datetime import datetime

from flask import Blueprint, Response, request, jsonify, send_file, stream_with_context

logger = logging.getLogger(__name__)

monkey_bp = Blueprint("monkey", __name__)

_VIDEO_STORE: dict = {}
_VIDEO_DIR = tempfile.mkdtemp(prefix="monkey_video_")

ACTION_WEIGHTS = {
    "click": 25,
    "fill": 15,
    "scroll": 10,
    "navigate": 10,
    "hover": 8,
    "double_click": 5,
    "right_click": 3,
    "keyboard": 5,
    "tab_navigation": 4,
    "select_change": 5,
    "checkbox_toggle": 5,
    "resize_viewport": 3,
    "back_forward": 2,
}

FUZZ_STRINGS = [
    "test", "a" * 500, "", " ", "null", "undefined", "-1", "0", "99999999",
    "' OR 1=1 --", "\" OR 1=1 --", "'; DROP TABLE users; --",
    "<script>alert('XSS')</script>", "<img src=x onerror=alert(1)>",
    "javascript:alert(1)", "<svg onload=alert(1)>",
    "!@#$%^&*()", "test@test.com", "admin@admin.com",
    "../../../etc/passwd", "..\\..\\..\\windows\\system32",
    "${7*7}", "{{7*7}}", "{{constructor.constructor('return this')()}}",
    "\x00\x01\x02", "\r\n\r\n", "\t\t\t",
    "SELECT * FROM users", "UNION SELECT 1,2,3",
    "true", "false", "[]", "{}", "NaN", "Infinity",
    "<h1>Heading Injection</h1>",
    "https://evil.com/phishing",
    "1; ls -la", "| cat /etc/passwd",
]

VIEWPORT_SIZES = [
    {"width": 320, "height": 568, "label": "iPhone SE"},
    {"width": 375, "height": 667, "label": "iPhone 8"},
    {"width": 414, "height": 896, "label": "iPhone XR"},
    {"width": 768, "height": 1024, "label": "iPad"},
    {"width": 1024, "height": 768, "label": "iPad Landscape"},
    {"width": 1280, "height": 800, "label": "Laptop"},
    {"width": 1920, "height": 1080, "label": "Desktop Full HD"},
]

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"


# ─── SSE Helper ───────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ─── Utilities ────────────────────────────────────────────────────────────────

def _weighted_choice(weights: dict) -> str:
    items = list(weights.keys())
    w = list(weights.values())
    return random.choices(items, weights=w, k=1)[0]


def _safe_visible(el) -> bool:
    try:
        return el.is_visible()
    except Exception:
        return False


def _categorize_error(error_text: str) -> str:
    text = error_text.lower()
    if any(k in text for k in ["typeerror", "referenceerror", "syntaxerror"]):
        return "JavaScript Hatası"
    if any(k in text for k in ["failed to fetch", "networkerror", "cors"]):
        return "Ağ / CORS Hatası"
    if any(k in text for k in ["undefined", "null", "cannot read"]):
        return "Null/Undefined Referans"
    if any(k in text for k in ["react", "component", "render", "hook"]):
        return "React / UI Framework Hatası"
    if any(k in text for k in ["security", "csp", "content-security"]):
        return "Güvenlik (CSP) Hatası"
    if any(k in text for k in ["deprecated", "warning"]):
        return "Uyarı / Deprecated"
    if any(k in text for k in ["memory", "heap", "stack overflow"]):
        return "Bellek / Performans"
    return "Diğer"


def _categorize_network_error(status: int) -> str:
    if status == 400: return "Bad Request (400)"
    if status == 401: return "Unauthorized (401)"
    if status == 403: return "Forbidden (403)"
    if status == 404: return "Not Found (404)"
    if status == 405: return "Method Not Allowed (405)"
    if status == 408: return "Request Timeout (408)"
    if status == 429: return "Rate Limited (429)"
    if 400 <= status < 500: return f"Client Error ({status})"
    if status == 500: return "Internal Server Error (500)"
    if status == 502: return "Bad Gateway (502)"
    if status == 503: return "Service Unavailable (503)"
    if 500 <= status < 600: return f"Server Error ({status})"
    return f"HTTP {status}"


# ─── Advanced Engine Features ─────────────────────────────────────────────────

def _run_accessibility_audit(page) -> dict:
    try:
        page.add_script_tag(url=AXE_CDN)
        page.wait_for_timeout(1200)
        result = page.evaluate("""
            async () => {
                try {
                    const r = await axe.run(document, {
                        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] }
                    });
                    return {
                        violations: r.violations.map(v => ({
                            id: v.id, impact: v.impact,
                            description: v.description, help: v.help,
                            helpUrl: v.helpUrl, nodes: v.nodes.length,
                        })),
                        passes: r.passes.length,
                        incomplete: r.incomplete.length,
                    };
                } catch(e) {
                    return { error: e.message, violations: [], passes: 0, incomplete: 0 };
                }
            }
        """)
        violations = result.get("violations", [])
        return {
            "violations": violations,
            "passes": result.get("passes", 0),
            "incomplete": result.get("incomplete", 0),
            "summary": {
                "total": len(violations),
                "critical": sum(1 for v in violations if v.get("impact") == "critical"),
                "serious":  sum(1 for v in violations if v.get("impact") == "serious"),
                "moderate": sum(1 for v in violations if v.get("impact") == "moderate"),
                "minor":    sum(1 for v in violations if v.get("impact") == "minor"),
            },
        }
    except Exception as e:
        return {
            "violations": [], "passes": 0, "incomplete": 0,
            "summary": {"total": 0, "critical": 0, "serious": 0, "moderate": 0, "minor": 0},
            "error": str(e),
        }


def _sample_memory(page) -> dict:
    try:
        data = page.evaluate("""
            () => {
                if (!performance.memory) return null;
                return {
                    usedJSHeapSize: performance.memory.usedJSHeapSize,
                    totalJSHeapSize: performance.memory.totalJSHeapSize,
                    jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
                };
            }
        """)
        if data:
            data["timestamp"] = datetime.now().isoformat()
        return data
    except Exception:
        return None


def _detect_memory_leak(samples: list) -> bool:
    valid = [s for s in samples if s and "usedJSHeapSize" in s]
    if len(valid) < 3:
        return False
    first = valid[0]["usedJSHeapSize"]
    last = valid[-1]["usedJSHeapSize"]
    if first == 0:
        return False
    growth = (last - first) / first
    monotonic = all(
        valid[i]["usedJSHeapSize"] <= valid[i + 1]["usedJSHeapSize"]
        for i in range(len(valid) - 1)
    )
    return growth > 0.5 and monotonic


def _visual_diff_score(before: bytes, after: bytes) -> float:
    if not before or not after:
        return 0.0
    max_size = max(len(before), len(after), 1)
    return round(min(abs(len(before) - len(after)) / max_size * 5.0, 1.0), 3)


def _compute_stability_score(error_count, action_errors, a11y_summary, memory_leak) -> int:
    score = 100
    score -= error_count * 3
    score -= action_errors * 2
    score -= a11y_summary.get("critical", 0) * 5
    score -= a11y_summary.get("serious", 0) * 2
    if memory_leak:
        score -= 20
    return max(0, score)


# ─── Analysis ─────────────────────────────────────────────────────────────────

def _generate_analysis(actions_log, console_errors, network_errors,
                       pages_visited, perf_metrics, stability_score,
                       a11y_data=None, memory_leak=False):
    scenarios, bugs, recommendations = [], [], []

    error_pages = set()
    for err in console_errors:
        error_pages.add(err.get("url", ""))
    for err in network_errors:
        error_pages.add(err.get("page_url", ""))

    error_categories = {}
    for err in console_errors:
        cat = _categorize_error(err.get("text", ""))
        error_categories.setdefault(cat, []).append(err)

    network_categories = {}
    for err in network_errors:
        cat = _categorize_network_error(err.get("status", 0))
        network_categories.setdefault(cat, []).append(err)

    for cat, errs in error_categories.items():
        bugs.append({
            "category": cat,
            "severity": "critical" if "Hatası" in cat and "Uyarı" not in cat else "warning",
            "count": len(errs),
            "sample": errs[0].get("text", "")[:200],
            "affected_pages": list(set(e.get("url", "") for e in errs))[:5],
        })

    for cat, errs in network_categories.items():
        sev = "critical" if any(s in cat for s in ["500", "502", "503"]) else "warning"
        bugs.append({
            "category": cat, "severity": sev, "count": len(errs),
            "sample": errs[0].get("url", "")[:200],
            "affected_pages": list(set(e.get("page_url", "") for e in errs))[:5],
        })

    if a11y_data and a11y_data.get("summary", {}).get("total", 0) > 0:
        s = a11y_data["summary"]
        bugs.append({
            "category": "Accessibility (WCAG 2.0 A+AA)",
            "severity": "critical" if s.get("critical", 0) > 0 else "warning",
            "count": s["total"],
            "sample": (a11y_data["violations"][0].get("help", "") if a11y_data.get("violations") else ""),
            "affected_pages": [],
        })

    if memory_leak:
        bugs.append({
            "category": "Bellek Sızıntısı (Memory Leak)",
            "severity": "critical", "count": 1,
            "sample": "JS Heap monoton artış tespit edildi (>%50 büyüme)",
            "affected_pages": [],
        })

    click_errors = [a for a in actions_log if (a.get("result") or "").startswith("click_error")]
    fill_errors  = [a for a in actions_log if (a.get("result") or "").startswith("fill_error")]
    nav_errors   = [a for a in actions_log if (a.get("result") or "").startswith("nav_error")]

    if click_errors:
        scenarios.append({
            "title": "Tıklanamayan Element Testi", "type": "functional",
            "description": f"{len(click_errors)} element tıklanamadı.",
            "steps": [
                {"action": "Sayfadaki tüm butonları ve linkleri kontrol et", "expected": "Tüm aktif elementler tıklanabilir olmalı"},
                {"action": "Overlapping elementleri CSS ile kontrol et", "expected": "z-index ve position doğru olmalı"},
                {"action": "JavaScript hatalarını console'da kontrol et", "expected": "Hata olmamalı"},
            ],
            "priority": "high",
        })

    if fill_errors:
        scenarios.append({
            "title": "Form Alanı Güvenlik Testi", "type": "security",
            "description": f"{len(fill_errors)} input alanında sorun tespit edildi.",
            "steps": [
                {"action": "Tüm input alanlarına uzun metin gir (500+ karakter)", "expected": "Karakter limiti olmalı"},
                {"action": "XSS payloadları dene", "expected": "Input sanitize edilmeli"},
                {"action": "SQL injection payloadları dene", "expected": "Parametrize query kullanılmalı"},
            ],
            "priority": "critical",
        })

    if nav_errors:
        scenarios.append({
            "title": "Navigasyon ve Routing Testi", "type": "functional",
            "description": f"{len(nav_errors)} sayfada navigasyon hatası.",
            "steps": [
                {"action": "Tüm menü linklerini sırayla tıkla", "expected": "Her sayfa doğru yüklenmeli"},
                {"action": "Doğrudan URL ile sayfalara git", "expected": "404 yerine doğru sayfa açılmalı"},
                {"action": "Tarayıcı geri/ileri butonlarını test et", "expected": "Sayfa durumu korunmalı"},
            ],
            "priority": "high",
        })

    if any(e.get("status") == 401 for e in network_errors):
        scenarios.append({
            "title": "Oturum ve Yetkilendirme Testi", "type": "security",
            "description": "401 Unauthorized hataları tespit edildi.",
            "steps": [
                {"action": "Oturum süresi dolduğunda davranışı test et", "expected": "Kullanıcı login sayfasına yönlendirilmeli"},
                {"action": "Yetkisiz endpoint'lere erişim dene", "expected": "Uygun hata mesajı gösterilmeli"},
                {"action": "Token geçerliliğini kontrol et", "expected": "Geçersiz token ile istek reddedilmeli"},
            ],
            "priority": "critical",
        })

    if any(e.get("status") == 404 for e in network_errors):
        scenarios.append({
            "title": "Kırık Link ve 404 Testi", "type": "functional",
            "description": "404 Not Found hataları tespit edildi.",
            "steps": [
                {"action": "Tüm navigasyon linklerini kontrol et", "expected": "Kırık link olmamalı"},
                {"action": "API endpoint'lerini doğrula", "expected": "Tüm endpoint'ler erişilebilir olmalı"},
                {"action": "Statik asset'leri kontrol et", "expected": "CSS, JS, image dosyaları yüklenmeli"},
            ],
            "priority": "medium",
        })

    js_errors = [e for e in console_errors if e.get("type") == "error"]
    if js_errors:
        scenarios.append({
            "title": "JavaScript Hata Regresyon Testi", "type": "regression",
            "description": f"{len(js_errors)} JavaScript hatası tespit edildi.",
            "steps": [
                {"action": "Console'u izleyerek sayfaları gez", "expected": "Hiç JavaScript hatası olmamalı"},
                {"action": "Farklı tarayıcılarda test et", "expected": "Tüm tarayıcılarda hatasız çalışmalı"},
                {"action": "Sayfa yüklenme sırasını kontrol et", "expected": "Bağımlılıklar doğru sırada yüklenmeli"},
            ],
            "priority": "high",
        })

    if a11y_data and a11y_data.get("summary", {}).get("total", 0) > 0:
        s = a11y_data["summary"]
        scenarios.append({
            "title": "WCAG 2.0 Erişilebilirlik Regresyon Testi", "type": "accessibility",
            "description": f"{s['total']} WCAG ihlali tespit edildi ({s.get('critical',0)} kritik, {s.get('serious',0)} ciddi).",
            "steps": [
                {"action": "axe-core ile tüm sayfaları tara", "expected": "Sıfır WCAG A+AA ihlali olmalı"},
                {"action": "Klavye navigasyonunu test et", "expected": "Tüm etkileşimler klavye ile erişilebilir olmalı"},
                {"action": "Screen reader uyumluluğunu kontrol et", "expected": "ARIA etiketleri doğru olmalı"},
            ],
            "priority": "critical" if s.get("critical", 0) > 0 else "high",
        })

    if memory_leak:
        scenarios.append({
            "title": "Bellek Sızıntısı Regresyon Testi", "type": "performance",
            "description": "Uzun kullanım boyunca JS Heap monoton artış tespit edildi.",
            "steps": [
                {"action": "Uygulamayı 15 dakika boyunca gezin ve bellek kullanımını izle", "expected": "Heap boyutu kararlı kalmalı"},
                {"action": "Olay dinleyicilerini kaldıran bileşen temizlemesini kontrol et", "expected": "Component unmount'ta cleanup çalışmalı"},
                {"action": "Chrome DevTools Memory profiler ile analiz et", "expected": "Detached DOM node olmamalı"},
            ],
            "priority": "high",
        })

    scenarios.append({
        "title": "Responsive Tasarım Testi", "type": "compatibility",
        "description": "Farklı ekran boyutlarında uygulamanın doğru görüntülenmesi kontrol edilmeli.",
        "steps": [
            {"action": "320x568 (iPhone SE) boyutunda test et", "expected": "Tüm elementler erişilebilir olmalı"},
            {"action": "768x1024 (iPad) boyutunda test et", "expected": "Layout kırılmamalı"},
            {"action": "1920x1080 (Desktop) boyutunda test et", "expected": "Boşluklar ve hizalama doğru olmalı"},
        ],
        "priority": "medium",
    })

    scenarios.append({
        "title": "Stres Altında Stabilite Testi", "type": "performance",
        "description": "Hızlı ve yoğun etkileşim altında uygulama davranışı test edilmeli.",
        "steps": [
            {"action": "Aynı butona 50 kez hızlıca tıkla", "expected": "Uygulama çökmemeli, duplicate işlem olmamalı"},
            {"action": "Form'u çok hızlı submit et", "expected": "Rate limiting veya debounce olmalı"},
            {"action": "Çok sayıda tab/pencere aç", "expected": "Bellek sızıntısı olmamalı"},
        ],
        "priority": "medium",
    })

    critical_count = sum(1 for b in bugs if b["severity"] == "critical")
    warning_count  = sum(1 for b in bugs if b["severity"] == "warning")

    if critical_count > 0:
        recommendations.append({"priority": "critical", "text": f"{critical_count} kritik hata öncelikle düzeltilmeli."})
    if warning_count > 3:
        recommendations.append({"priority": "high", "text": f"{warning_count} uyarı seviyesinde sorun var."})
    if stability_score < 50:
        recommendations.append({"priority": "critical", "text": f"Stabilite skoru %{stability_score} — uygulama kararsız."})
    elif stability_score < 80:
        recommendations.append({"priority": "high", "text": f"Stabilite skoru %{stability_score} — iyileştirme gerekli."})
    else:
        recommendations.append({"priority": "info", "text": f"Stabilite skoru %{stability_score} — uygulama genel olarak kararlı."})

    if any("Güvenlik" in b["category"] or b["category"] == "Accessibility (WCAG 2.0 A+AA)" for b in bugs):
        recommendations.append({"priority": "critical", "text": "Güvenlik ve/veya erişilebilirlik bulgular var. Penetrasyon testi ve WCAG denetimi önerilir."})
    if memory_leak:
        recommendations.append({"priority": "high", "text": "Bellek sızıntısı tespit edildi. React bileşenlerinde useEffect cleanup ve event listener yönetimini gözden geçirin."})

    if perf_metrics:
        avg_load = sum(m.get("load_time_ms", 0) for m in perf_metrics) / max(len(perf_metrics), 1)
        if avg_load > 3000:
            recommendations.append({"priority": "high", "text": f"Ortalama sayfa yükleme süresi {avg_load:.0f}ms — performans optimizasyonu gerekli."})

    risk_level = "low"
    if critical_count > 0 or stability_score < 50:
        risk_level = "critical"
    elif warning_count > 3 or stability_score < 80:
        risk_level = "high"
    elif warning_count > 0:
        risk_level = "medium"

    return {
        "scenarios": scenarios,
        "bugs": bugs,
        "recommendations": recommendations,
        "risk_level": risk_level,
        "summary": {
            "total_bugs": len(bugs),
            "critical_bugs": critical_count,
            "warning_bugs": warning_count,
            "scenarios_generated": len(scenarios),
            "pages_with_errors": len(error_pages),
            "error_categories": list(error_categories.keys()),
            "network_categories": list(network_categories.keys()),
        },
    }


# ─── SSE Streaming Route ──────────────────────────────────────────────────────

@monkey_bp.route("/api/monkey-testing/run/stream", methods=["POST"])
def api_monkey_run_stream():
    data = request.json or {}
    url = data.get("url", "").strip()
    max_actions = min(data.get("max_actions", 50), 200)
    credentials = data.get("credentials")
    test_config = data.get("config", {})
    record_video = data.get("record_video", False)

    if not url:
        return jsonify({"error": "URL gereklidir"}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    enabled_actions = test_config.get("enabled_actions", list(ACTION_WEIGHTS.keys()))
    weights = {k: v for k, v in ACTION_WEIGHTS.items() if k in enabled_actions} or ACTION_WEIGHTS
    run_id = str(uuid.uuid4())

    def generate():
        from playwright.sync_api import sync_playwright

        console_errors = []
        network_errors = []
        actions_log = []
        screenshots = {}
        pages_visited = set()
        perf_metrics = []
        memory_samples = []
        visual_diffs = []
        start_time = time.time()

        yield _sse("start", {
            "run_id": run_id, "url": url,
            "max_actions": max_actions, "record_video": record_video,
            "timestamp": datetime.now().isoformat(),
        })

        try:
            with sync_playwright() as p:
                ctx_kwargs = {"viewport": {"width": 1280, "height": 800}, "locale": "tr-TR"}
                if record_video:
                    video_run_dir = os.path.join(_VIDEO_DIR, run_id)
                    os.makedirs(video_run_dir, exist_ok=True)
                    ctx_kwargs["record_video_dir"] = video_run_dir
                    ctx_kwargs["record_video_size"] = {"width": 1280, "height": 800}

                browser = p.chromium.launch(headless=True)
                context = browser.new_context(**ctx_kwargs)
                page = context.new_page()

                def on_console(msg):
                    if msg.type in ("error", "warning"):
                        console_errors.append({
                            "type": msg.type, "text": msg.text[:500],
                            "url": page.url, "timestamp": datetime.now().isoformat(),
                            "category": _categorize_error(msg.text),
                        })

                def on_response(res):
                    if res.status >= 400:
                        network_errors.append({
                            "url": res.url[:300], "status": res.status,
                            "page_url": page.url, "timestamp": datetime.now().isoformat(),
                            "category": _categorize_network_error(res.status),
                        })

                page.on("console", on_console)
                page.on("response", on_response)

                # Login
                if credentials and credentials.get("login_url"):
                    try:
                        page.goto(credentials["login_url"], wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(1000)
                        if credentials.get("username_selector") and credentials.get("username"):
                            page.fill(credentials["username_selector"], credentials["username"])
                        if credentials.get("password_selector") and credentials.get("password"):
                            page.fill(credentials["password_selector"], credentials["password"])
                        if credentials.get("submit_selector"):
                            page.click(credentials["submit_selector"])
                            page.wait_for_timeout(2000)
                        yield _sse("login", {"status": "ok", "url": page.url})
                    except Exception as exc:
                        yield _sse("login", {"status": "skipped", "reason": str(exc)[:120]})

                # Initial navigation
                nav_start = time.time()
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1500)
                initial_load_ms = (time.time() - nav_start) * 1000
                pages_visited.add(url)
                perf_metrics.append({"url": url, "load_time_ms": round(initial_load_ms), "timestamp": datetime.now().isoformat()})

                yield _sse("nav", {"url": url, "load_time_ms": round(initial_load_ms), "timestamp": datetime.now().isoformat()})

                prev_ss_bytes = b""
                try:
                    ss_bytes = page.screenshot(full_page=False)
                    prev_ss_bytes = ss_bytes
                    yield _sse("frame", {"step": 0, "url": page.url, "image": base64.b64encode(ss_bytes).decode(), "timestamp": datetime.now().isoformat()})
                except Exception:
                    pass

                # Axe-core a11y audit
                a11y_data = _run_accessibility_audit(page)
                yield _sse("a11y", {
                    "summary": a11y_data.get("summary", {}),
                    "violations": a11y_data.get("violations", [])[:10],
                    "passes": a11y_data.get("passes", 0),
                    "timestamp": datetime.now().isoformat(),
                })

                dispatch = {
                    "click":           lambda r: _do_click(page, r),
                    "fill":            lambda r: _do_fill(page, r),
                    "scroll":          lambda r: _do_scroll(page, r),
                    "navigate":        lambda r: _do_navigate(page, r, pages_visited, perf_metrics, url),
                    "hover":           lambda r: _do_hover(page, r),
                    "double_click":    lambda r: _do_double_click(page, r),
                    "right_click":     lambda r: _do_right_click(page, r),
                    "keyboard":        lambda r: _do_keyboard(page, r),
                    "tab_navigation":  lambda r: _do_tab_navigation(page, r),
                    "select_change":   lambda r: _do_select_change(page, r),
                    "checkbox_toggle": lambda r: _do_checkbox_toggle(page, r),
                    "resize_viewport": lambda r: _do_resize(page, context, r),
                    "back_forward":    lambda r: _do_back_forward(page, r),
                }

                for i in range(max_actions):
                    action_type = _weighted_choice(weights)
                    record = {
                        "step": i + 1, "type": action_type,
                        "url": page.url, "timestamp": datetime.now().isoformat(),
                    }
                    console_before = len(console_errors)
                    network_before = len(network_errors)

                    try:
                        handler = dispatch.get(action_type)
                        if handler:
                            handler(record)
                    except Exception as e:
                        record["result"] = f"exception: {str(e)[:120]}"

                    new_console = console_errors[console_before:]
                    new_network = network_errors[network_before:]
                    triggered_error = bool(new_console or new_network)
                    record["triggered_error"] = triggered_error

                    for ce in new_console:
                        yield _sse("console_error", ce)
                    for ne in new_network:
                        yield _sse("network_error", ne)

                    try:
                        cur_ss = page.screenshot(full_page=False)
                        cur_b64 = base64.b64encode(cur_ss).decode()
                        vd = _visual_diff_score(prev_ss_bytes, cur_ss)
                        visual_diffs.append({"step": i + 1, "score": vd})
                        prev_ss_bytes = cur_ss

                        if triggered_error:
                            screenshots[f"error_step_{i+1}"] = cur_b64
                            yield _sse("error_shot", {"step": i + 1, "image": cur_b64, "url": page.url, "visual_diff": vd, "timestamp": datetime.now().isoformat()})
                        elif i % 10 == 0:
                            yield _sse("frame", {"step": i + 1, "url": page.url, "image": cur_b64, "visual_diff": vd, "timestamp": datetime.now().isoformat()})
                    except Exception:
                        pass

                    if (i + 1) % 15 == 0:
                        mem = _sample_memory(page)
                        if mem:
                            memory_samples.append(mem)
                            yield _sse("memory", {"step": i + 1, "sample": mem, "timestamp": datetime.now().isoformat()})

                    yield _sse("action", {**record, "progress": round((i + 1) / max_actions * 100)})
                    actions_log.append(record)

                # Final screenshot
                try:
                    final_ss = page.screenshot(full_page=True)
                    screenshots["final"] = base64.b64encode(final_ss).decode()
                except Exception:
                    pass

                # Video save
                video_url = None
                if record_video:
                    try:
                        video_path = page.video.path() if page.video else None
                        context.close()
                        if video_path and os.path.exists(video_path):
                            dest = os.path.join(_VIDEO_DIR, f"{run_id}.webm")
                            os.rename(video_path, dest)
                            _VIDEO_STORE[run_id] = dest
                            video_url = f"/api/monkey-testing/video/{run_id}"
                    except Exception as ve:
                        logger.warning("Video kaydetme hatası: %s", ve)
                else:
                    context.close()

                browser.close()

                total_time_s = time.time() - start_time
                error_count = len(console_errors) + len(network_errors)
                action_errors = len([a for a in actions_log if "error" in (a.get("result") or "")])
                a11y_summary = a11y_data.get("summary", {})
                memory_leak = _detect_memory_leak(memory_samples)
                stability_score = _compute_stability_score(error_count, action_errors, a11y_summary, memory_leak)
                analysis = _generate_analysis(
                    actions_log, console_errors, network_errors,
                    pages_visited, perf_metrics, stability_score,
                    a11y_data=a11y_data, memory_leak=memory_leak,
                )

                action_stats = {}
                for a in actions_log:
                    t = a["type"]
                    action_stats.setdefault(t, {"total": 0, "success": 0, "error": 0})
                    action_stats[t]["total"] += 1
                    if "error" in (a.get("result") or ""):
                        action_stats[t]["error"] += 1
                    else:
                        action_stats[t]["success"] += 1

                avg_vd = sum(d["score"] for d in visual_diffs) / len(visual_diffs) if visual_diffs else 0.0

                yield _sse("done", {
                    "run_id": run_id, "status": "ok", "test_url": url,
                    "actions_performed": len(actions_log),
                    "actions_log": actions_log, "action_stats": action_stats,
                    "console_errors": console_errors, "network_errors": network_errors,
                    "error_count": error_count, "stability_score": stability_score,
                    "pages_visited": list(pages_visited), "pages_visited_count": len(pages_visited),
                    "performance_metrics": perf_metrics, "screenshots": screenshots,
                    "total_time_seconds": round(total_time_s, 1), "analysis": analysis,
                    "accessibility": a11y_data, "memory_leak": memory_leak,
                    "memory_samples": memory_samples, "visual_diffs": visual_diffs,
                    "avg_visual_diff": round(avg_vd, 3), "video_url": video_url,
                    "started_at": datetime.now().isoformat(),
                })

        except Exception as e:
            yield _sse("fail", {"run_id": run_id, "error": str(e), "trace": traceback.format_exc()[-2000:]})

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Access-Control-Allow-Origin": "*",
    }
    return Response(stream_with_context(generate()), headers=headers)


# ─── Sync Route ────────────────────────────────────────────────────────────────

@monkey_bp.route("/api/monkey-testing/run", methods=["POST"])
def api_monkey_run():
    data = request.json or {}
    url = data.get("url", "").strip()
    max_actions = min(data.get("max_actions", 50), 200)
    credentials = data.get("credentials")
    test_config = data.get("config", {})

    if not url:
        return jsonify({"error": "URL gereklidir"}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    enabled_actions = test_config.get("enabled_actions", list(ACTION_WEIGHTS.keys()))
    weights = {k: v for k, v in ACTION_WEIGHTS.items() if k in enabled_actions} or ACTION_WEIGHTS

    try:
        from playwright.sync_api import sync_playwright

        console_errors, network_errors, actions_log = [], [], []
        screenshots, pages_visited, perf_metrics = {}, set(), []
        memory_samples, visual_diffs = [], []
        start_time = time.time()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="tr-TR")
            page = context.new_page()

            def on_console(msg):
                if msg.type in ("error", "warning"):
                    console_errors.append({
                        "type": msg.type, "text": msg.text[:500],
                        "url": page.url, "timestamp": datetime.now().isoformat(),
                        "category": _categorize_error(msg.text),
                    })

            def on_response(res):
                if res.status >= 400:
                    network_errors.append({
                        "url": res.url[:300], "status": res.status,
                        "page_url": page.url, "timestamp": datetime.now().isoformat(),
                        "category": _categorize_network_error(res.status),
                    })

            page.on("console", on_console)
            page.on("response", on_response)

            if credentials and credentials.get("login_url"):
                try:
                    page.goto(credentials["login_url"], wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1000)
                    if credentials.get("username_selector") and credentials.get("username"):
                        page.fill(credentials["username_selector"], credentials["username"])
                    if credentials.get("password_selector") and credentials.get("password"):
                        page.fill(credentials["password_selector"], credentials["password"])
                    if credentials.get("submit_selector"):
                        page.click(credentials["submit_selector"])
                        page.wait_for_timeout(2000)
                except Exception as exc:
                    logger.debug("Monkey login atlandı: %s", exc)

            nav_start = time.time()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)
            pages_visited.add(url)
            perf_metrics.append({"url": url, "load_time_ms": round((time.time() - nav_start) * 1000), "timestamp": datetime.now().isoformat()})

            prev_ss_bytes = b""
            try:
                ss = page.screenshot(full_page=False)
                screenshots["initial"] = base64.b64encode(ss).decode()
                prev_ss_bytes = ss
            except Exception:
                pass

            a11y_data = _run_accessibility_audit(page)

            dispatch = {
                "click":           lambda r: _do_click(page, r),
                "fill":            lambda r: _do_fill(page, r),
                "scroll":          lambda r: _do_scroll(page, r),
                "navigate":        lambda r: _do_navigate(page, r, pages_visited, perf_metrics, url),
                "hover":           lambda r: _do_hover(page, r),
                "double_click":    lambda r: _do_double_click(page, r),
                "right_click":     lambda r: _do_right_click(page, r),
                "keyboard":        lambda r: _do_keyboard(page, r),
                "tab_navigation":  lambda r: _do_tab_navigation(page, r),
                "select_change":   lambda r: _do_select_change(page, r),
                "checkbox_toggle": lambda r: _do_checkbox_toggle(page, r),
                "resize_viewport": lambda r: _do_resize(page, context, r),
                "back_forward":    lambda r: _do_back_forward(page, r),
            }

            for i in range(max_actions):
                action_type = _weighted_choice(weights)
                record = {"step": i + 1, "type": action_type, "url": page.url, "timestamp": datetime.now().isoformat()}
                console_before = len(console_errors)
                network_before = len(network_errors)

                try:
                    handler = dispatch.get(action_type)
                    if handler:
                        handler(record)
                except Exception as e:
                    record["result"] = f"exception: {str(e)[:120]}"

                triggered_error = len(console_errors) > console_before or len(network_errors) > network_before
                record["triggered_error"] = triggered_error

                if triggered_error:
                    try:
                        cur_ss = page.screenshot(full_page=False)
                        screenshots[f"error_step_{i+1}"] = base64.b64encode(cur_ss).decode()
                        visual_diffs.append({"step": i + 1, "score": _visual_diff_score(prev_ss_bytes, cur_ss)})
                        prev_ss_bytes = cur_ss
                    except Exception:
                        pass

                if (i + 1) % 15 == 0:
                    mem = _sample_memory(page)
                    if mem:
                        memory_samples.append(mem)

                actions_log.append(record)

            try:
                final_ss = page.screenshot(full_page=True)
                screenshots["final"] = base64.b64encode(final_ss).decode()
            except Exception:
                pass

            context.close()
            browser.close()

        total_time_s = time.time() - start_time
        error_count = len(console_errors) + len(network_errors)
        action_errors = len([a for a in actions_log if "error" in (a.get("result") or "")])
        a11y_summary = a11y_data.get("summary", {})
        memory_leak = _detect_memory_leak(memory_samples)
        stability_score = _compute_stability_score(error_count, action_errors, a11y_summary, memory_leak)
        analysis = _generate_analysis(
            actions_log, console_errors, network_errors,
            pages_visited, perf_metrics, stability_score,
            a11y_data=a11y_data, memory_leak=memory_leak,
        )

        action_stats = {}
        for a in actions_log:
            t = a["type"]
            action_stats.setdefault(t, {"total": 0, "success": 0, "error": 0})
            action_stats[t]["total"] += 1
            if "error" in (a.get("result") or ""):
                action_stats[t]["error"] += 1
            else:
                action_stats[t]["success"] += 1

        avg_vd = sum(d["score"] for d in visual_diffs) / len(visual_diffs) if visual_diffs else 0.0

        return jsonify({
            "status": "ok", "test_url": url,
            "actions_performed": len(actions_log),
            "actions_log": actions_log, "action_stats": action_stats,
            "console_errors": console_errors, "network_errors": network_errors,
            "error_count": error_count, "stability_score": stability_score,
            "pages_visited": list(pages_visited), "pages_visited_count": len(pages_visited),
            "performance_metrics": perf_metrics, "screenshots": screenshots,
            "total_time_seconds": round(total_time_s, 1), "analysis": analysis,
            "accessibility": a11y_data, "memory_leak": memory_leak,
            "memory_samples": memory_samples, "visual_diffs": visual_diffs,
            "avg_visual_diff": round(avg_vd, 3), "started_at": datetime.now().isoformat(),
        })

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ─── Video Serve Route ────────────────────────────────────────────────────────

@monkey_bp.route("/api/monkey-testing/video/<run_id>", methods=["GET"])
def api_monkey_video(run_id: str):
    path = _VIDEO_STORE.get(run_id)
    if not path or not os.path.exists(path):
        return jsonify({"error": "Video bulunamadı"}), 404
    return send_file(path, mimetype="video/webm", as_attachment=False)


# ─── Action Helpers ───────────────────────────────────────────────────────────

def _do_click(page, record):
    clickables = page.query_selector_all("button, a[href], [role='button'], [onclick], input[type='submit']")
    visible = [e for e in clickables if _safe_visible(e)]
    if visible:
        chosen = random.choice(visible)
        text = ""
        try:
            text = (chosen.inner_text() or "")[:60]
        except Exception:
            pass
        record["target"] = text or chosen.evaluate("e => e.tagName.toLowerCase()")
        chosen.click(timeout=3000)
        record["result"] = "clicked"
        page.wait_for_timeout(random.randint(300, 800))
    else:
        record["result"] = "no_visible_elements"


def _do_fill(page, record):
    inputs = page.query_selector_all(
        "input:not([type='hidden']):not([type='submit']):not([type='checkbox'])"
        ":not([type='radio']):not([type='file']), textarea"
    )
    visible = [inp for inp in inputs if _safe_visible(inp)]
    if visible:
        target = random.choice(visible)
        val = random.choice(FUZZ_STRINGS)
        record["value"] = val[:60]
        try:
            target.fill(val)
            record["result"] = "filled"
        except Exception as e:
            record["result"] = f"fill_error: {str(e)[:80]}"
    else:
        record["result"] = "no_visible_inputs"


def _do_scroll(page, record):
    direction = random.choice(["down", "up", "left", "right"])
    pixels = random.randint(100, 800)
    dx = pixels if direction == "right" else (-pixels if direction == "left" else 0)
    dy = pixels if direction == "down" else (-pixels if direction == "up" else 0)
    page.evaluate(f"window.scrollBy({dx}, {dy})")
    record["direction"] = direction
    record["pixels"] = pixels
    record["result"] = "scrolled"


def _do_navigate(page, record, pages_visited, perf_metrics, base_url):
    links = page.evaluate("""
    () => [...document.querySelectorAll('a[href]')]
        .map(a => a.href)
        .filter(h => h.startsWith('http') &&
                !h.includes('logout') && !h.includes('signout') &&
                !h.includes('delete') && !h.includes('remove'))
    """)
    if links:
        link = random.choice(links[:30])
        record["target"] = link[:120]
        nav_start = time.time()
        try:
            page.goto(link, wait_until="domcontentloaded", timeout=10000)
            load_ms = (time.time() - nav_start) * 1000
            record["result"] = "navigated"
            record["load_time_ms"] = round(load_ms)
            pages_visited.add(link)
            perf_metrics.append({"url": link, "load_time_ms": round(load_ms), "timestamp": datetime.now().isoformat()})
            page.wait_for_timeout(random.randint(500, 1200))
        except Exception as e:
            record["result"] = f"nav_error: {str(e)[:80]}"
    else:
        record["result"] = "no_links"


def _do_hover(page, record):
    els = page.query_selector_all("button, a, [role='button'], [role='menuitem'], [role='tab']")
    visible = [e for e in els if _safe_visible(e)]
    if visible:
        chosen = random.choice(visible)
        chosen.hover(timeout=3000)
        record["result"] = "hovered"
        page.wait_for_timeout(300)
    else:
        record["result"] = "no_hoverable"


def _do_double_click(page, record):
    els = page.query_selector_all("td, div, span, p, li")
    visible = [e for e in els if _safe_visible(e)]
    if visible:
        chosen = random.choice(visible[:20])
        chosen.dblclick(timeout=3000)
        record["result"] = "double_clicked"
    else:
        record["result"] = "no_elements"


def _do_right_click(page, record):
    els = page.query_selector_all("*")
    visible = [e for e in els if _safe_visible(e)]
    if visible:
        chosen = random.choice(visible[:30])
        chosen.click(button="right", timeout=3000)
        record["result"] = "right_clicked"
        page.wait_for_timeout(200)
        page.keyboard.press("Escape")
    else:
        record["result"] = "no_elements"


def _do_keyboard(page, record):
    keys = ["Escape", "Enter", "Tab", "Space", "ArrowDown", "ArrowUp",
            "ArrowLeft", "ArrowRight", "Home", "End", "PageDown", "PageUp",
            "F5", "Control+a", "Control+z"]
    key = random.choice(keys)
    record["key"] = key
    page.keyboard.press(key)
    record["result"] = "key_pressed"
    page.wait_for_timeout(300)


def _do_tab_navigation(page, record):
    tab_count = random.randint(3, 10)
    for _ in range(tab_count):
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)
    record["tab_count"] = tab_count
    page.keyboard.press("Enter")
    record["result"] = "tab_navigated"
    page.wait_for_timeout(500)


def _do_select_change(page, record):
    selects = page.query_selector_all("select")
    visible = [s for s in selects if _safe_visible(s)]
    if visible:
        chosen = random.choice(visible)
        options = chosen.evaluate("e => [...e.options].map(o => o.value).filter(v => v)")
        if options:
            val = random.choice(options)
            chosen.select_option(val)
            record["value"] = val[:60]
            record["result"] = "option_selected"
        else:
            record["result"] = "no_options"
    else:
        record["result"] = "no_selects"


def _do_checkbox_toggle(page, record):
    checks = page.query_selector_all("input[type='checkbox'], input[type='radio']")
    visible = [c for c in checks if _safe_visible(c)]
    if visible:
        chosen = random.choice(visible)
        chosen.click(timeout=3000)
        record["result"] = "toggled"
    else:
        record["result"] = "no_checkboxes"


def _do_resize(page, context, record):
    size = random.choice(VIEWPORT_SIZES)
    context.pages[0].set_viewport_size({"width": size["width"], "height": size["height"]})
    label = size.get("label", f"{size['width']}x{size['height']}")
    record["viewport"] = f"{size['width']}x{size['height']} ({label})"
    record["result"] = "resized"
    page.wait_for_timeout(500)


def _do_back_forward(page, record):
    action = random.choice(["back", "forward"])
    try:
        if action == "back":
            page.go_back(timeout=5000)
        else:
            page.go_forward(timeout=5000)
        record["direction"] = action
        record["result"] = f"{action}_navigated"
        page.wait_for_timeout(500)
    except Exception as e:
        record["result"] = f"{action}_error: {str(e)[:80]}"
