
from flask import Blueprint, request, jsonify
from core.db import get_locators, save_locator, delete_locator
from core.locator_manager import LocatorManager

locators_bp = Blueprint('locators', __name__)

@locators_bp.route("/api/locators", methods=["GET"])
def api_get_locators():
    source = request.args.get("source", "db")
    if source == "json":
        return jsonify({"locators": LocatorManager.as_dict(), "source": "json"})
    return jsonify(get_locators())

@locators_bp.route("/api/locators", methods=["POST"])
def api_save_locator():
    data = request.json
    loc_id = save_locator(data["name"], data["locator_value"], data.get("page_url", ""))
    return jsonify({"status": "ok", "id": loc_id})

@locators_bp.route("/api/locators/<int:loc_id>", methods=["DELETE"])
def api_delete_locator(loc_id):
    delete_locator(loc_id)
    return jsonify({"status": "ok"})

@locators_bp.route("/api/discover", methods=["POST"])
def api_discover_page():
    data = request.json
    url = data.get("url")
    if not url: return jsonify({"error": "URL gereklidir"}), 400
    
    # URL normalizasyonu
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        
    try:
        from playwright.sync_api import sync_playwright
        from core.ai_engine import AIEngine
        import json
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Daha sağlam bekleme stratejisi
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000) # Dinamik içerik için kısa bir bekleme
            
            js_script = """
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
                    
                    results.push({
                        text: text.substring(0, 60).replace(/\n/g, ' '), 
                        selector: selector
                    });
                });
                return results;
            }
            """
            
            raw_elements = page.evaluate(js_script)
            browser.close()
            
            if not raw_elements:
                return jsonify({"status": "ok", "saved_count": 0})
                
            engine = AIEngine()
            prompt = f"Scraped elements: {json.dumps(raw_elements[:20])}. Classify into snake_case names for Object Repository. Return JSON Array with 'name', 'locator_value' keys. ONLY JSON."
            msg = engine.client.chat.completions.create(
                model=engine.execute_model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            response_text = msg.choices[0].message.content.strip()
            # Clean possible markdown
            if "```" in response_text:
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"): response_text = response_text[4:]
            
            ai_locators = json.loads(response_text)
            saved_count = 0
            for loc in ai_locators:
                save_locator(loc["name"], loc["locator_value"], url)
                saved_count += 1
            return jsonify({"status": "ok", "saved_count": saved_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── JSON Locator Management (NexusQA pattern) ──────────────────────────────

@locators_bp.route("/api/locators/json", methods=["GET"])
def api_get_json_locators():
    """Tum JSON locator'lari doner."""
    return jsonify({
        "locators": LocatorManager.as_dict(),
        "keys": LocatorManager.keys(),
        "count": len(LocatorManager.keys()),
    })


@locators_bp.route("/api/locators/json/load", methods=["POST"])
def api_load_json_locators():
    """Belirtilen feature icin locator JSON dosyasini yukler."""
    data = request.json or {}
    feature = data.get("feature", "")
    directory = data.get("directory")
    if not feature:
        return jsonify({"error": "feature parametresi gerekli"}), 400
    try:
        LocatorManager.load(feature, directory)
        return jsonify({
            "status": "ok",
            "feature": feature,
            "total_count": len(LocatorManager.keys()),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@locators_bp.route("/api/locators/json/load-all", methods=["POST"])
def api_load_all_json_locators():
    """Tum JSON locator dosyalarini yukler."""
    data = request.json or {}
    directory = data.get("directory")
    try:
        LocatorManager.load_all(directory)
        return jsonify({
            "status": "ok",
            "total_count": len(LocatorManager.keys()),
            "keys": LocatorManager.keys(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@locators_bp.route("/api/locators/json/resolve", methods=["POST"])
def api_resolve_json_locator():
    """Verilen key'i Playwright selector'a cozumler."""
    data = request.json or {}
    key = data.get("key", "")
    if not key:
        return jsonify({"error": "key parametresi gerekli"}), 400
    resolved = LocatorManager.resolve(key)
    return jsonify({
        "key": key,
        "selector": resolved,
        "from_json": resolved != key,
    })


# ── Locator Bridge (Birlesik Cozumleme) ─────────────────────────────────────

@locators_bp.route("/api/locators/bridge/resolve", methods=["POST"])
def api_bridge_resolve():
    """Tum locator kaynaklarindan birlesik cozumleme yapar."""
    from core.locator_bridge import get_bridge
    data = request.json or {}
    key = data.get("key", "")
    page_name = data.get("page")
    element = data.get("element")
    if not key and not (page_name and element):
        return jsonify({"error": "key veya page+element gerekli"}), 400

    bridge = get_bridge()
    if page_name and element:
        selector = bridge.resolve(page_name, element)
    else:
        selector = bridge.resolve(key)

    return jsonify({"key": key or f"{page_name}.{element}", "selector": selector})


@locators_bp.route("/api/locators/bridge/health", methods=["GET"])
def api_bridge_health():
    """Tum locator kaynaklarinin saglik raporunu doner."""
    from core.locator_bridge import get_bridge
    return jsonify(get_bridge().health_report())
