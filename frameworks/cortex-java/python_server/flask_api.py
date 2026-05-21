"""
Cortex Otomasyon Dashboard - Flask backend
==========================================
A single process exposes:
  - AI error classification     (/api/classify_error)
  - Cucumber JSON parse + summary (/api/results)
  - Maven test run + SSE log stream (/api/run, /api/run/<id>/stream)
  - Screenshot listing + serving (/api/screenshots)
  - Feature file listing        (/api/features)
  - Config view (masked)        (/api/config)
  - Dashboard static files      (/)
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    request,
    send_from_directory,
    stream_with_context,
)
from flask_cors import CORS


# ---------------------------------------------------------------------------
# Paths & logging
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
TARGET_DIR = PROJECT_ROOT / "target"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
LOGS_DIR = PROJECT_ROOT / "logs"
FEATURES_DIR = PROJECT_ROOT / "src" / "test" / "resources"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard" / "static"
CONFIG_FILE = PROJECT_ROOT / "src" / "main" / "resources" / "config.properties"
MODEL_PATH = BASE_DIR / "final_model.pkl"
SUGGESTIONS_PATH = BASE_DIR / "suggestions.json"

LOGS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "dashboard.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("cortex-dashboard")


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    static_folder=str(DASHBOARD_DIR),
    static_url_path="",
)
CORS(app)


# ---------------------------------------------------------------------------
# AI model + suggestions
# ---------------------------------------------------------------------------

def _load_model():
    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to load model (%s): %s", MODEL_PATH, exc)
        return None


def _load_suggestions() -> dict[str, list[dict[str, str]]]:
    try:
        with open(SUGGESTIONS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to load suggestions.json: %s", exc)
        return {}


MODEL = _load_model()
SUGGESTIONS = _load_suggestions()


def classify(error_message: str, scenario: str, step: str) -> dict[str, str]:
    if MODEL is None:
        return {
            "predicted_label": "model_unavailable",
            "suggestion": "AI modeli yuklu degil. python_server/train_model.py ile yeniden egitin.",
        }
    cleaned = re.sub(r" at [^\n]+", "", error_message.split("\n")[0].lower().strip())
    cleaned = re.sub(r"'.*?'", "", cleaned)
    try:
        prediction = MODEL.predict([cleaned])[0].lower()
    except Exception as exc:  # noqa: BLE001
        log.error("Prediction failed: %s", exc)
        return {"predicted_label": "unknown", "suggestion": "Hata mesaji islenemedi."}

    options = SUGGESTIONS.get(
        prediction,
        [{"condition": "True", "suggestion": "No suggestion is defined for this error category yet."}],
    )
    suggestion_text = "No suggestion is defined for this error category yet."
    for opt in options:
        cond = opt.get("condition", "True")
        try:
            if eval(cond.replace("msg", "cleaned").replace("step", "step")):  # noqa: S307
                suggestion_text = opt.get("suggestion", suggestion_text)
                break
        except Exception as exc:  # noqa: BLE001
            log.warning("Condition eval failed (%s): %s", cond, exc)

    step_l = (step or "").lower()
    if "click" in step_l and "locator" in prediction:
        suggestion_text = (
            "Tiklama adiminda locator dogru tanimli mi? Elementin tiklanabilir oldugunu dogrulayin."
        )
    elif "type" in step_l and "timeout" in prediction:
        suggestion_text = (
            "Elementin gorunur olmasi icin WebDriverWait suresini artirin veya XPath'i kontrol edin."
        )

    return {"predicted_label": prediction, "suggestion": suggestion_text}


# ---------------------------------------------------------------------------
# Cucumber report parsing
# ---------------------------------------------------------------------------

def parse_cucumber_report(json_path: Path) -> dict[str, Any]:
    if not json_path.exists():
        return {"available": False, "reason": f"{json_path.name} not found."}
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "reason": f"JSON parse error: {exc}"}

    total = passed = failed = skipped = 0
    duration_ns = 0
    features_out: list[dict[str, Any]] = []

    for feature in data:
        feat_scenarios: list[dict[str, Any]] = []
        for scenario in feature.get("elements", []):
            if scenario.get("type") != "scenario":
                continue
            steps = scenario.get("steps", [])
            scenario_dur = sum(
                (s.get("result", {}).get("duration") or 0) for s in steps
            )
            duration_ns += scenario_dur

            status = "passed"
            failed_step = None
            for s in steps:
                r = s.get("result", {})
                if r.get("status") == "failed":
                    status = "failed"
                    failed_step = {
                        "name": s.get("name"),
                        "error": (r.get("error_message") or "").split("\n")[0],
                    }
                    break
            if status != "failed" and steps and all(
                s.get("result", {}).get("status") == "skipped" for s in steps
            ):
                status = "skipped"

            total += 1
            if status == "passed":
                passed += 1
            elif status == "failed":
                failed += 1
            else:
                skipped += 1

            feat_scenarios.append(
                {
                    "name": scenario.get("name"),
                    "status": status,
                    "duration_ms": round(scenario_dur / 1_000_000, 1),
                    "tags": [t.get("name") for t in scenario.get("tags", [])],
                    "failed_step": failed_step,
                    "steps": [
                        {
                            "keyword": s.get("keyword", "").strip(),
                            "name": s.get("name"),
                            "status": s.get("result", {}).get("status"),
                        }
                        for s in steps
                    ],
                }
            )
        if feat_scenarios:
            features_out.append(
                {
                    "name": feature.get("name"),
                    "uri": feature.get("uri"),
                    "scenarios": feat_scenarios,
                }
            )

    return {
        "available": True,
        "generated_at": datetime.fromtimestamp(json_path.stat().st_mtime).isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": round((passed / total) * 100, 1) if total else 0.0,
            "duration_seconds": round(duration_ns / 1_000_000_000, 2),
        },
        "features": features_out,
    }


# ---------------------------------------------------------------------------
# Test run orchestration (Maven)
# ---------------------------------------------------------------------------

RUNS: dict[str, dict[str, Any]] = {}
RUN_LOCK = threading.Lock()


def _maven_cmd(feature: str | None, tag: str | None) -> list[str]:
    mvn = os.environ.get("MAVEN_HOME")
    mvn_bin = "mvn"
    if mvn:
        candidate = Path(mvn) / "bin" / ("mvn.cmd" if os.name == "nt" else "mvn")
        if candidate.exists():
            mvn_bin = str(candidate)
    cmd = [mvn_bin, "-B", "-q", "test"]
    if feature:
        cmd.append(f"-Dcucumber.features={feature}")
    if tag:
        cmd.append(f"-Dcucumber.filter.tags={tag}")
    return cmd


def _run_tests(run_id: str, feature: str | None, tag: str | None) -> None:
    with RUN_LOCK:
        RUNS[run_id]["status"] = "running"
        RUNS[run_id]["started_at"] = datetime.utcnow().isoformat()

    cmd = _maven_cmd(feature, tag)
    log.info("Test run starting (%s): %s", run_id, " ".join(cmd))

    try:
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        with RUN_LOCK:
            RUNS[run_id]["status"] = "error"
            RUNS[run_id]["queue"].put(
                "ERROR: Maven not found. Is JAVA_HOME / MAVEN_HOME set?"
            )
            RUNS[run_id]["queue"].put(None)
        return

    with RUN_LOCK:
        RUNS[run_id]["pid"] = proc.pid

    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        with RUN_LOCK:
            RUNS[run_id]["queue"].put(line)
            RUNS[run_id]["log_lines"].append(line)
            if len(RUNS[run_id]["log_lines"]) > 5000:
                RUNS[run_id]["log_lines"] = RUNS[run_id]["log_lines"][-2500:]

    rc = proc.wait()
    with RUN_LOCK:
        RUNS[run_id]["status"] = "completed" if rc == 0 else "failed"
        RUNS[run_id]["exit_code"] = rc
        RUNS[run_id]["finished_at"] = datetime.utcnow().isoformat()
        RUNS[run_id]["queue"].put(None)
    log.info("Test run finished (%s) rc=%s", run_id, rc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def list_feature_files() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not FEATURES_DIR.exists():
        return out
    for f in sorted(FEATURES_DIR.rglob("*.feature")):
        out.append(
            {
                "relative": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "name": f.stem,
                "folder": f.parent.name,
            }
        )
    return out


def list_screenshots() -> list[dict[str, str]]:
    """Selenium (screenshots/) ve Playwright (screenshots/playwright/) birlikte."""
    if not SCREENSHOTS_DIR.exists():
        return []
    out: list[dict[str, str]] = []
    for f in sorted(SCREENSHOTS_DIR.rglob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
        rel = f.relative_to(SCREENSHOTS_DIR).as_posix()
        engine = "playwright" if "playwright" in rel.split("/") else "selenium"
        out.append(
            {
                "url": f"/api/screenshots/{rel}",
                "name": f.name,
                "folder": f.parent.relative_to(SCREENSHOTS_DIR).as_posix() or ".",
                "engine": engine,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "size_kb": round(f.stat().st_size / 1024, 1),
            }
        )
    return out[:300]


def read_config_safe() -> dict[str, str]:
    if not CONFIG_FILE.exists():
        return {}
    out: dict[str, str] = {}
    secret_re = re.compile(r"(password|key|secret|token)", re.I)
    for line in CONFIG_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if secret_re.search(k):
            v = "***"
        out[k] = v
    return out


# ---------------------------------------------------------------------------
# Routes - data API
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health() -> Response:
    return jsonify(
        {
            "ok": True,
            "model_loaded": MODEL is not None,
            "suggestions_count": len(SUGGESTIONS),
            "active_runs": sum(1 for r in RUNS.values() if r["status"] == "running"),
            "version": "1.0.0",
        }
    )


@app.route("/api/config")
def get_config() -> Response:
    return jsonify(read_config_safe())


@app.route("/api/features")
def get_features() -> Response:
    return jsonify(list_feature_files())


@app.route("/api/results")
def get_results() -> Response:
    return jsonify(parse_cucumber_report(TARGET_DIR / "cucumber.json"))


@app.route("/api/screenshots")
def get_screenshots() -> Response:
    return jsonify(list_screenshots())


@app.route("/api/screenshots/<path:relpath>")
def serve_screenshot(relpath: str):
    safe_root = SCREENSHOTS_DIR.resolve()
    target = (SCREENSHOTS_DIR / relpath).resolve()
    if not str(target).startswith(str(safe_root)):
        abort(403)
    if not target.exists():
        abort(404)
    return send_from_directory(str(target.parent), target.name)


# Legacy endpoint (back-compat with CucumberJsonAnalyzer.java)
@app.route("/classify_error", methods=["POST"])
@app.route("/api/classify_error", methods=["POST"])
def classify_error() -> Response:
    data = request.get_json(silent=True) or {}
    msg = data.get("error_message", "")
    if not msg:
        return jsonify({"error": "error_message is required"}), 400
    res = classify(msg, data.get("scenario", ""), data.get("step", ""))
    return jsonify(res)


# ---------------------------------------------------------------------------
# Routes - test run
# ---------------------------------------------------------------------------

@app.route("/api/run", methods=["POST"])
def start_run() -> Response:
    data = request.get_json(silent=True) or {}
    feature = data.get("feature")
    tag = data.get("tag")

    if feature:
        target_feature = (PROJECT_ROOT / feature).resolve()
        if not str(target_feature).startswith(str(PROJECT_ROOT.resolve())):
            return jsonify({"error": "Feature file path outside project root"}), 400
        if not target_feature.exists():
            return jsonify({"error": "Feature file does not exist"}), 404
        feature_arg = str(target_feature)
    else:
        feature_arg = None

    run_id = uuid.uuid4().hex[:12]
    with RUN_LOCK:
        RUNS[run_id] = {
            "id": run_id,
            "status": "starting",
            "feature": feature,
            "tag": tag,
            "queue": queue.Queue(),
            "log_lines": [],
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "pid": None,
        }
    t = threading.Thread(target=_run_tests, args=(run_id, feature_arg, tag), daemon=True)
    t.start()
    return jsonify({"run_id": run_id, "status": "starting"})


@app.route("/api/run/<run_id>/status")
def run_status(run_id: str) -> Response:
    with RUN_LOCK:
        r = RUNS.get(run_id)
        if not r:
            return jsonify({"error": "Unknown run_id"}), 404
        return jsonify(
            {
                "id": r["id"],
                "status": r["status"],
                "feature": r["feature"],
                "tag": r["tag"],
                "started_at": r["started_at"],
                "finished_at": r["finished_at"],
                "exit_code": r["exit_code"],
                "log_line_count": len(r["log_lines"]),
            }
        )


@app.route("/api/run/<run_id>/stream")
def stream_logs(run_id: str) -> Response:
    with RUN_LOCK:
        r = RUNS.get(run_id)
        if not r:
            return jsonify({"error": "Unknown run_id"}), 404

    @stream_with_context
    def event_stream():
        q: queue.Queue = r["queue"]
        for old_line in list(r["log_lines"]):
            yield f"data: {json.dumps({'line': old_line})}\n\n"
        while True:
            try:
                line = q.get(timeout=30)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            if line is None:
                yield f"data: {json.dumps({'event': 'end', 'status': r['status']})}\n\n"
                break
            yield f"data: {json.dumps({'line': line})}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/api/run/<run_id>/stop", methods=["POST"])
def stop_run(run_id: str) -> Response:
    with RUN_LOCK:
        r = RUNS.get(run_id)
        if not r:
            return jsonify({"error": "Unknown run_id"}), 404
        pid = r.get("pid")
    if not pid:
        return jsonify({"error": "PID missing"}), 400
    try:
        os.kill(pid, signal.SIGTERM)
        return jsonify({"stopped": True})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


@app.route("/api/runs")
def list_runs() -> Response:
    with RUN_LOCK:
        return jsonify(
            [
                {
                    "id": r["id"],
                    "status": r["status"],
                    "feature": r["feature"],
                    "tag": r["tag"],
                    "started_at": r["started_at"],
                    "finished_at": r["finished_at"],
                    "exit_code": r["exit_code"],
                }
                for r in sorted(
                    RUNS.values(),
                    key=lambda x: x.get("started_at") or "",
                    reverse=True,
                )
            ]
        )


# ---------------------------------------------------------------------------
# Cortex authoring — scenario creation API
# ---------------------------------------------------------------------------

CORTEX_FEATURE_DIR = PROJECT_ROOT / "src/test/resources/projects/cortex/features"
CORTEX_LOCATOR_DIR = PROJECT_ROOT / "src/test/resources/projects/cortex/locators"
RECORDINGS_DIR     = PROJECT_ROOT / "src/test/resources/recordings"


@app.route("/api/cortex/steps")
def cortex_steps():
    """Known Gherkin step phrases — feeds the manual editor's autocomplete."""
    phrases = [
        # Navigation
        {"phrase": 'I open "{string}" link',                           "kind": "Given"},
        {"phrase": "I go back and see previous page",                  "kind": "When"},
        {"phrase": "I reload current page",                            "kind": "When"},
        {"phrase": "Close the current tab",                            "kind": "When"},
        # Click
        {"phrase": 'I click "{string}"',                               "kind": "When"},
        {"phrase": 'I click "{string}" if it exists',                  "kind": "When"},
        {"phrase": 'I double click "{string}"',                        "kind": "When"},
        {"phrase": 'I right click on element with key "{string}"',     "kind": "When"},
        {"phrase": 'I hover over "{string}"',                          "kind": "When"},
        {"phrase": 'I scroll to "{string}"',                           "kind": "When"},
        # Input
        {"phrase": 'I write "{string}" into "{string}"',               "kind": "When"},
        {"phrase": 'I type "{string}" into "{string}"',                "kind": "When"},
        {"phrase": 'I clear "{string}"',                               "kind": "When"},
        {"phrase": 'I enter encrypted password alias "{string}" into "{string}"', "kind": "When"},
        # Keys
        {"phrase": 'I press "{string}" key',                           "kind": "When"},
        {"phrase": 'I press "{string}" and "{string}" keys simultaneously', "kind": "When"},
        # Wait
        {"phrase": "I wait for {int} seconds",                         "kind": "When"},
        {"phrase": "I wait for page to load",                          "kind": "When"},
        # Variables
        {"phrase": 'I save the text "{string}" as the variable "{string}"', "kind": "Given"},
        {"phrase": 'I generate a random unique email with domain "{string}" as the variable "{string}"', "kind": "Given"},
        {"phrase": 'I type variable "{string}" into element "{string}"', "kind": "When"},
        # Assertions
        {"phrase": 'I see "{string}"',                                 "kind": "Then"},
        {"phrase": 'I do not see "{string}"',                          "kind": "Then"},
        {"phrase": 'I verify "{string}" contains "{string}"',          "kind": "Then"},
        {"phrase": 'I verify "{string}" value is "{string}"',          "kind": "Then"},
        {"phrase": 'I verify title contains "{string}"',               "kind": "Then"},
        {"phrase": 'I verify url contains "{string}"',                 "kind": "Then"},
        {"phrase": 'I verify "{string}" is enabled',                   "kind": "Then"},
        {"phrase": 'I verify "{string}" is disabled',                  "kind": "Then"},
        # Accessibility (axe-core)
        {"phrase": "I run accessibility audit and expect WCAG 2.1 AA compliance", "kind": "Then"},
        {"phrase": "I run accessibility audit and expect no critical violations", "kind": "Then"},
    ]
    return jsonify(phrases)


@app.route("/api/cortex/tags")
def cortex_tags():
    """Known scenario tags."""
    return jsonify([
        "@cortex", "@smoke", "@pw", "@negative", "@security",
        "@a11y", "@axe", "@edge", "@manual", "@skip", "@no-parallel",
    ])


@app.route("/api/cortex/locator-keys")
def cortex_locator_keys():
    """Backward-compat: just the key names."""
    keys: set[str] = set()
    for root in (CORTEX_LOCATOR_DIR, PROJECT_ROOT / "src/test/resources/shared/locators"):
        if not root.exists():
            continue
        for jf in root.glob("*.json"):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                for entry in data:
                    if isinstance(entry, dict) and "key" in entry and not entry["key"].startswith("_"):
                        keys.add(entry["key"])
            except Exception:
                pass
    return jsonify(sorted(keys))


@app.route("/api/cortex/locator-entries")
def cortex_locator_entries():
    """Full locator entries grouped by key.

    Returns: {
      "loginButton": [
        { type: "css",   value: "[data-testid='login']",   source: "projects/cortex/locators/login.json" },
        { type: "id",    value: "btnLogin",                source: "..." },
        ...
      ],
      ...
    }
    """
    grouped: dict[str, list[dict]] = {}
    roots = [
        (CORTEX_LOCATOR_DIR,                                                "projects/cortex/locators"),
        (PROJECT_ROOT / "src/test/resources/shared/locators",               "shared/locators"),
        (PROJECT_ROOT / "src/test/resources/recordings/locators",           "recordings/locators"),
    ]
    for root, label in roots:
        if not root.exists():
            continue
        for jf in sorted(root.glob("*.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    key = entry.get("key")
                    typ = entry.get("type")
                    val = entry.get("value")
                    if not key or key.startswith("_") or not typ or not val:
                        continue
                    grouped.setdefault(key, []).append({
                        "type": typ,
                        "value": val,
                        "source": f"{label}/{jf.name}",
                    })
            except Exception:
                pass
    return jsonify(grouped)


@app.route("/api/cortex/locator-files")
def cortex_locator_files():
    """List existing locator JSON files (target for new locator entries)."""
    files = []
    roots = [
        (CORTEX_LOCATOR_DIR,                                  "projects/cortex/locators"),
        (PROJECT_ROOT / "src/test/resources/shared/locators", "shared/locators"),
    ]
    for root, label in roots:
        if not root.exists():
            continue
        for jf in sorted(root.glob("*.json")):
            files.append({
                "name": jf.name,
                "path": f"{label}/{jf.name}",
                "abs":  str(jf),
            })
    return jsonify(files)


@app.route("/api/cortex/locator-entry", methods=["POST"])
def cortex_add_locator_entry():
    """Append a locator entry to an existing JSON or create a new file.

    body: {
      file: "projects/cortex/locators/login.json"  (existing, OR
            a new name like "my-feature.json" + base: "projects/cortex" )
      base: "projects/cortex" | "shared"  (only when file is a bare name)
      entry: { key, type, value }
    }
    """
    data = request.get_json(silent=True) or {}
    file = (data.get("file") or "").strip()
    base = (data.get("base") or "projects/cortex").strip()
    entry = data.get("entry") or {}

    key = (entry.get("key") or "").strip()
    typ = (entry.get("type") or "").strip().lower()
    val = (entry.get("value") or "").strip()
    if not key or not typ or not val:
        return jsonify({"error": "entry.key, entry.type, entry.value zorunlu"}), 400

    valid_types = {"id", "name", "css", "xpath", "class", "tag", "linktext", "partiallinktext"}
    if typ not in valid_types:
        return jsonify({"error": f"type one of: {sorted(valid_types)}"}), 400

    # Resolve target path
    if "/" in file:
        # Caller passed a full relative path
        target = PROJECT_ROOT / "src/test/resources" / file
    else:
        # Bare name + base
        sub = base if base.startswith("projects/") or base == "shared" else f"projects/{base}"
        target = PROJECT_ROOT / f"src/test/resources/{sub}/locators" / file
        if not file.endswith(".json"):
            target = target.with_suffix(".json")

    target.parent.mkdir(parents=True, exist_ok=True)
    existing: list = []
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    new_entry = {"key": key, "type": typ, "value": val}
    existing.append(new_entry)
    target.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    rel = str(target.relative_to(PROJECT_ROOT / "src/test/resources"))
    log.info("Locator entry appended to %s: %s", rel, new_entry)
    return jsonify({
        "ok": True,
        "file": rel,
        "entry": new_entry,
        "total_entries_in_file": len(existing),
    })


# ---------------------------------------------------------------------------
# IDE-like file operations
# ---------------------------------------------------------------------------

# Allow-list: directories the IDE can browse / edit. Anything outside is 403.
_BROWSABLE_ROOTS: list[tuple[str, Path]] = [
    ("projects",      PROJECT_ROOT / "src/test/resources/projects"),
    ("shared",        PROJECT_ROOT / "src/test/resources/shared"),
    ("recordings",    PROJECT_ROOT / "src/test/resources/recordings"),
    ("scratch",       PROJECT_ROOT / "src/test/resources/scratch"),
    ("config",        PROJECT_ROOT / "src/main/resources"),
    ("docs",          PROJECT_ROOT / "docs"),
    ("scripts",       PROJECT_ROOT / "scripts"),
]

# Editable extensions
_EDITABLE = {".feature", ".json", ".properties", ".md", ".java",
             ".xml", ".yml", ".yaml", ".sh", ".bat", ".sql", ".txt",
             ".html", ".css", ".js", ".ts", ".py"}


def _resolve_safe(rel: str) -> Path | None:
    """Map an incoming 'root/relative/path' to an absolute path inside an
    allow-listed root. Returns None for anything outside."""
    if not rel:
        return None
    rel = rel.replace("\\", "/").lstrip("/")
    parts = rel.split("/", 1)
    root_name = parts[0]
    tail = parts[1] if len(parts) > 1 else ""
    for label, root in _BROWSABLE_ROOTS:
        if label == root_name:
            candidate = (root / tail).resolve() if tail else root.resolve()
            try:
                candidate.relative_to(root.resolve())
                return candidate
            except ValueError:
                return None
    return None


def _build_tree_node(p: Path, label: str, depth: int = 0, max_depth: int = 8) -> dict:
    rel_root = label
    def _walk(node: Path, depth_: int) -> dict:
        if node.is_dir():
            children = []
            if depth_ < max_depth:
                try:
                    for child in sorted(node.iterdir(),
                                        key=lambda x: (not x.is_dir(), x.name.lower())):
                        if child.name.startswith(".") and child.name not in {".env.example"}:
                            continue
                        if child.name in {"node_modules", "target", "__pycache__", ".venv", ".git"}:
                            continue
                        children.append(_walk(child, depth_ + 1))
                except PermissionError:
                    pass
            return {
                "name": node.name or label,
                "path": _to_rel(node, label, p),
                "type": "dir",
                "children": children,
            }
        return {
            "name": node.name,
            "path": _to_rel(node, label, p),
            "type": "file",
            "size": node.stat().st_size if node.exists() else 0,
            "editable": node.suffix.lower() in _EDITABLE,
        }
    return _walk(p, depth)


def _to_rel(node: Path, label: str, root: Path) -> str:
    try:
        sub = node.relative_to(root)
        return f"{label}/{sub.as_posix()}" if str(sub) != "." else label
    except ValueError:
        return label


@app.route("/api/cortex/files/tree")
def cortex_files_tree():
    """Return the file tree for a given root, or all roots if none specified."""
    root_param = request.args.get("root", "")
    if root_param:
        for label, root in _BROWSABLE_ROOTS:
            if label == root_param and root.exists():
                return jsonify(_build_tree_node(root, label))
        return jsonify({"error": f"Unknown root '{root_param}'"}), 404
    # All roots
    return jsonify([
        _build_tree_node(root, label) for label, root in _BROWSABLE_ROOTS if root.exists()
    ])


@app.route("/api/cortex/files/read")
def cortex_files_read():
    """Return the contents of a file (text)."""
    path_param = request.args.get("path", "")
    target = _resolve_safe(path_param)
    if target is None or not target.exists() or not target.is_file():
        return jsonify({"error": "Dosya bulunamadi veya erisim yok"}), 404
    if target.suffix.lower() not in _EDITABLE:
        return jsonify({"error": "Binary / non-editable extension"}), 415
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "UTF-8 decode hatasi"}), 415
    return jsonify({
        "path": path_param,
        "content": content,
        "size": target.stat().st_size,
        "language": _detect_lang(target),
    })


def _detect_lang(p: Path) -> str:
    return {
        ".feature":   "gherkin",
        ".json":      "json",
        ".java":      "java",
        ".xml":       "xml",
        ".yml":       "yaml",
        ".yaml":      "yaml",
        ".md":        "markdown",
        ".properties":"properties",
        ".sh":        "bash",
        ".bat":       "bat",
        ".sql":       "sql",
        ".html":      "html",
        ".css":       "css",
        ".js":        "javascript",
        ".ts":        "typescript",
        ".py":        "python",
    }.get(p.suffix.lower(), "text")


@app.route("/api/cortex/files/write", methods=["POST"])
def cortex_files_write():
    """Overwrite a file's contents."""
    data = request.get_json(silent=True) or {}
    path_param = (data.get("path") or "").strip()
    content    = data.get("content")
    if content is None:
        return jsonify({"error": "content zorunlu"}), 400

    target = _resolve_safe(path_param)
    if target is None:
        return jsonify({"error": "Erisim yok"}), 403
    if target.exists() and target.is_dir():
        return jsonify({"error": "Hedef bir klasor"}), 400
    if target.suffix.lower() not in _EDITABLE:
        return jsonify({"error": "Non-editable extension"}), 415

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    log.info("File saved: %s (%d bytes)", target, len(content))
    return jsonify({
        "ok": True,
        "path": path_param,
        "size": target.stat().st_size,
    })


@app.route("/api/cortex/files/create", methods=["POST"])
def cortex_files_create():
    """Create a new empty file or directory."""
    data = request.get_json(silent=True) or {}
    path_param = (data.get("path") or "").strip()
    kind = (data.get("kind") or "file").lower()
    target = _resolve_safe(path_param)
    if target is None:
        return jsonify({"error": "Erisim yok"}), 403
    if target.exists():
        return jsonify({"error": "Zaten var"}), 409
    if kind == "dir":
        target.mkdir(parents=True, exist_ok=True)
    else:
        if target.suffix.lower() not in _EDITABLE:
            return jsonify({"error": "Non-editable extension"}), 415
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    return jsonify({"ok": True, "path": path_param})


@app.route("/api/cortex/files/delete", methods=["DELETE"])
def cortex_files_delete():
    """Delete a file (refuses non-empty directories)."""
    path_param = (request.args.get("path") or "").strip()
    target = _resolve_safe(path_param)
    if target is None or not target.exists():
        return jsonify({"error": "Dosya bulunamadi"}), 404
    if target.is_dir():
        try:
            target.rmdir()  # only empty dirs
        except OSError:
            return jsonify({"error": "Klasor bos degil"}), 400
    else:
        target.unlink()
    log.info("File deleted: %s", target)
    return jsonify({"ok": True})


@app.route("/api/cortex/files/rename", methods=["POST"])
def cortex_files_rename():
    """Rename / move a file within the same root."""
    data = request.get_json(silent=True) or {}
    src = _resolve_safe((data.get("from") or "").strip())
    dst = _resolve_safe((data.get("to")   or "").strip())
    if src is None or dst is None or not src.exists():
        return jsonify({"error": "Kaynak/hedef gecersiz"}), 400
    if dst.exists():
        return jsonify({"error": "Hedef zaten var"}), 409
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    return jsonify({"ok": True})


@app.route("/api/cortex/templates")
def cortex_templates():
    """Pre-built scenario templates that can be inserted directly."""
    return jsonify([
        {
            "id": "login-happy-path",
            "title": "Login — Happy Path",
            "tag": "@cortex @smoke @pw",
            "description": "Geçerli kullanıcı, dashboard'a yönlen.",
            "content": """@cortex @smoke @pw
Feature: Cortex Login Happy Path

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  Scenario: Geçerli kullanıcı girişi
    When I write "${ENV:CORTEX_USERNAME}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"
""",
        },
        {
            "id": "login-validation",
            "title": "Login — Validation",
            "tag": "@cortex @negative @pw",
            "description": "Boş alan + hatalı şifre + hata mesajı kontrolü.",
            "content": """@cortex @negative @pw
Feature: Cortex Login Validation

  Background:
    Given I open "cortex.url" link
    * I wait for page to load

  Scenario: Boş alan ile gönderim engellenir
    When I clear "userNameInput"
    And I clear "passwordInput"
    And I click "loginButton"
    Then I see "loginErrorMessage"

  Scenario: Hatalı şifre ile giriş reddedilir
    When I write "${ENV:CORTEX_USERNAME}" into "userNameInput"
    And I write "yanlis_sifre" into "passwordInput"
    And I click "loginButton"
    Then I see "loginErrorMessage"
""",
        },
        {
            "id": "a11y-audit",
            "title": "Accessibility — axe-core",
            "tag": "@cortex @a11y @axe @pw",
            "description": "Sayfanın WCAG 2.1 AA uyumluluğunu otomatik denetle.",
            "content": """@cortex @a11y @axe @pw
Feature: Cortex A11y Audit

  Background:
    Given I open "cortex.url" link
    * I wait for page to load

  Scenario: Login sayfası WCAG 2.1 AA uyumlu
    Then I run accessibility audit and expect WCAG 2.1 AA compliance

  Scenario: Sayfada kritik a11y ihlali yok
    Then I run accessibility audit and expect no critical violations
""",
        },
        {
            "id": "form-submission",
            "title": "Form gönderimi (generic)",
            "tag": "@cortex @pw",
            "description": "Standart form: alanları doldur, submit et, başarı mesajı doğrula.",
            "content": """@cortex @pw
Feature: Generic Form Submission

  Background:
    Given I open "cortex.url" link
    * I wait for page to load

  Scenario: Form doldurma akışı
    When I write "Test User" into "nameInput"
    And I write "test@example.com" into "emailInput"
    And I select "Premium" from "planSelect"
    And I check "termsCheckbox"
    And I click "submitButton"
    Then I see "successMessage"
""",
        },
        {
            "id": "search-flow",
            "title": "Arama akışı",
            "tag": "@cortex @pw",
            "description": "Arama kutusuna metin gir, sonuç listesini kontrol et.",
            "content": """@cortex @pw
Feature: Search Flow

  Background:
    Given I open "cortex.url" link
    * I wait for page to load

  Scenario: Arama sonucu görüntülenir
    When I click "searchInput"
    And I write "Cortex" into "searchInput"
    And I press "ENTER" key
    And I wait for page to load
    Then I see "searchResultsList"
    And I verify "searchResultsList" contains "Cortex"
""",
        },
    ])


@app.route("/api/cortex/feature", methods=["POST"])
def cortex_save_feature():
    """Save (or overwrite) a feature file. Optionally append new locator entries.

    body: {
      name: str,                # filename without .feature
      content: str,             # full Gherkin text
      target_dir: "features" | "recordings",
      locators: [{key,type,value}, ...]   # optional
    }
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    content = data.get("content") or ""
    target = data.get("target_dir") or "features"
    locators = data.get("locators") or []

    if not name or not content.strip():
        return jsonify({"error": "name and content are required"}), 400
    if not re.match(r"^[A-Za-z0-9_-]+$", name):
        return jsonify({"error": "name must match [A-Za-z0-9_-]+"}), 400
    if target not in ("features", "recordings"):
        return jsonify({"error": "target_dir must be 'features' or 'recordings'"}), 400

    if target == "recordings":
        out_dir = RECORDINGS_DIR
        loc_dir = RECORDINGS_DIR / "locators"
    else:
        out_dir = CORTEX_FEATURE_DIR
        loc_dir = CORTEX_LOCATOR_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    loc_dir.mkdir(parents=True, exist_ok=True)

    feature_path = out_dir / f"{name}.feature"
    feature_path.write_text(content, encoding="utf-8")

    locator_path: Path | None = None
    if locators:
        locator_path = loc_dir / f"{name}.json"
        existing = []
        if locator_path.exists():
            try:
                existing = json.loads(locator_path.read_text(encoding="utf-8"))
            except Exception:
                existing = []
        merged = list(existing) + list(locators)
        locator_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info("Cortex feature saved: %s", feature_path)
    return jsonify({
        "ok": True,
        "feature_path": str(feature_path.relative_to(PROJECT_ROOT)),
        "locator_path": str(locator_path.relative_to(PROJECT_ROOT)) if locator_path else None,
    })


import urllib.request as _urlreq
import urllib.error as _urlerr


RECORDER_PORT_RANGE = range(7700, 7710)
_recorder_state: dict[str, Any] = {"pid": None, "port": None, "started_at": None}


def _probe_recorder_port(timeout_total: float = 25.0) -> int | None:
    """Poll 7700-7709 until one responds, give up after `timeout_total` seconds."""
    deadline = time.time() + timeout_total
    while time.time() < deadline:
        for port in RECORDER_PORT_RANGE:
            try:
                with _urlreq.urlopen(f"http://127.0.0.1:{port}/status", timeout=0.4) as resp:
                    if resp.status == 200:
                        return port
            except Exception:
                continue
        time.sleep(0.4)
    return None


@app.route("/api/cortex/recorder/start", methods=["POST"])
def cortex_recorder_start():
    """Spawn the Java recorder via Maven (-Precorder).

    body: { url?, feature_name?, browser? }
    Returns: { ok, pid, url, port }  — port is the recorder's HTTP server port
                                       (7700 by default, falls back to 7701..)
    """
    data = request.get_json(silent=True) or {}
    url     = data.get("url") or "https://cortex-test.bgtsai.com/"
    feature = data.get("feature_name") or ""
    browser = data.get("browser") or "chromium"

    mvn = "./mvnw" if (PROJECT_ROOT / "mvnw").exists() else "mvn"
    cmd = [
        mvn, "-B", "-q",
        "-Precorder", "compile", "exec:java",
        f"-Drecorder.url={url}",
        f"-Drecorder.browser={browser}",
    ]
    if feature:
        cmd.append(f"-Drecorder.feature.name={feature}")

    try:
        log_file = LOGS_DIR / "recorder.log"
        # Truncate to keep the file size manageable
        log_handle = open(log_file, "w", encoding="utf-8", buffering=1)
        log_handle.write(f"[{datetime.now().isoformat()}] Recorder spawn: {' '.join(cmd)}\n")
        proc = subprocess.Popen(
            cmd, cwd=str(PROJECT_ROOT),
            stdout=log_handle, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log.info("Recorder spawned: pid=%s log=%s", proc.pid, log_file)
        # Wait for the recorder's HTTP server to come up so we know its port.
        port = _probe_recorder_port(timeout_total=30.0)
        _recorder_state.update({"pid": proc.pid, "port": port, "started_at": time.time(),
                                "log_file": str(log_file)})
        return jsonify({
            "ok": True,
            "pid": proc.pid,
            "url": url,
            "port": port,
            "log_file": str(log_file.relative_to(PROJECT_ROOT)),
            "port_warning": None if port else "Recorder port 30sn icinde acilmadi — Maven derlenirken olabilir",
        })
    except Exception as exc:
        log.error("Recorder spawn failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/cortex/recorder/log")
def cortex_recorder_log():
    """Tail the recorder subprocess log (stdout+stderr)."""
    log_file = LOGS_DIR / "recorder.log"
    if not log_file.exists():
        return jsonify({"ok": False, "error": "log file yok"}), 404
    lines = int(request.args.get("lines", 200))
    try:
        with open(log_file, encoding="utf-8", errors="replace") as f:
            content = f.read()
        tail = "\n".join(content.splitlines()[-lines:])
        return jsonify({
            "ok": True,
            "path": str(log_file.relative_to(PROJECT_ROOT)),
            "lines": lines,
            "content": tail,
            "total_bytes": len(content),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _recorder_call(method: str, path: str, port: int | None = None) -> tuple[dict[str, Any], int]:
    """Helper: call the recorder HTTP server on the discovered port."""
    p = port or _recorder_state.get("port") or _probe_recorder_port(timeout_total=2.0)
    if not p:
        return {"ok": False, "error": "Recorder calmiyor (port bulunamadi)"}, 404
    req = _urlreq.Request(f"http://127.0.0.1:{p}{path}", method=method)
    try:
        with _urlreq.urlopen(req, timeout=4) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(body) if body else {}, resp.status
            except json.JSONDecodeError:
                return {"raw": body}, resp.status
    except _urlerr.HTTPError as e:
        return {"ok": False, "error": f"{e.code} {e.reason}"}, e.code
    except Exception as e:
        return {"ok": False, "error": str(e)}, 502


@app.route("/api/cortex/recorder/status")
def cortex_recorder_status():
    """Live recorder status: { running, actions, port, pid }."""
    p = _recorder_state.get("port") or _probe_recorder_port(timeout_total=1.0)
    if not p:
        return jsonify({"running": False, "actions": 0, "port": None, "pid": _recorder_state.get("pid")})
    body, status = _recorder_call("GET", "/status", port=p)
    body["port"] = p
    body["pid"] = _recorder_state.get("pid")
    return jsonify(body), status


@app.route("/api/cortex/recorder/stop", methods=["POST"])
def cortex_recorder_stop():
    """Trigger the recorder to save & exit (same as the in-browser Stop button)."""
    body, status = _recorder_call("POST", "/stop")
    if status == 200:
        _recorder_state.update({"pid": None, "port": None})
    return jsonify(body), status


@app.route("/api/cortex/recorder/undo", methods=["POST"])
def cortex_recorder_undo():
    """Remove the last recorded action."""
    body, status = _recorder_call("POST", "/undo")
    return jsonify(body), status


@app.route("/api/cortex/recorder/actions")
def cortex_recorder_actions():
    """Full action list (for live preview)."""
    body, status = _recorder_call("GET", "/actions")
    return jsonify(body), status


# ============================================================
#  Playwright Codegen — alternative recorder backend
# ============================================================
# Why: For sites with shadow DOM, cross-origin OAuth popups, or other
# edge cases where our custom recorder.js struggles, we delegate to
# Microsoft's official `playwright codegen`. Battle-tested, opens a
# Chromium + Inspector window, writes generated JS to a temp file as
# the user interacts.

try:
    from codegen_recorder import (
        start_codegen, stop_codegen, get_job, list_jobs,
        read_output, codegen_to_gherkin, is_codegen_available
    )
    _CODEGEN_OK = True
except ImportError as e:
    print(f"[cortex] codegen_recorder import failed: {e}")
    _CODEGEN_OK = False


@app.route("/api/cortex/codegen/available")
def cortex_codegen_available():
    """Quick check: is Playwright codegen functional?"""
    if not _CODEGEN_OK:
        return jsonify({"available": False, "reason": "codegen_recorder module not loaded"}), 200
    ok, msg = is_codegen_available()
    return jsonify({"available": ok, "version": msg if ok else None, "reason": None if ok else msg}), 200


@app.route("/api/cortex/codegen/start", methods=["POST"])
def cortex_codegen_start():
    """Spawn playwright codegen subprocess for the given URL."""
    if not _CODEGEN_OK:
        return jsonify({"ok": False, "error": "codegen module unavailable"}), 503
    payload = request.get_json(silent=True) or {}
    url = payload.get("url")
    target = payload.get("target", "javascript")
    browser = payload.get("browser", "chromium")
    if not url:
        return jsonify({"ok": False, "error": "url required"}), 400
    job = start_codegen(url=url, target=target, browser=browser)
    return jsonify({"ok": job.status != "error", "job": job.to_dict()}), 200


@app.route("/api/cortex/codegen/status/<job_id>")
def cortex_codegen_status(job_id: str):
    if not _CODEGEN_OK:
        return jsonify({"ok": False, "error": "codegen module unavailable"}), 503
    job = get_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "job not found"}), 404
    return jsonify({"ok": True, "job": job.to_dict()}), 200


@app.route("/api/cortex/codegen/stop/<job_id>", methods=["POST"])
def cortex_codegen_stop(job_id: str):
    if not _CODEGEN_OK:
        return jsonify({"ok": False, "error": "codegen module unavailable"}), 503
    ok = stop_codegen(job_id)
    job = get_job(job_id)
    return jsonify({"ok": ok, "job": job.to_dict() if job else None}), 200


@app.route("/api/cortex/codegen/output/<job_id>")
def cortex_codegen_output(job_id: str):
    """Raw codegen JS (current snapshot, even while running)."""
    if not _CODEGEN_OK:
        return jsonify({"ok": False, "error": "codegen module unavailable"}), 503
    job = get_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "job not found"}), 404
    return jsonify({"ok": True, "source": read_output(job_id), "job": job.to_dict()}), 200


@app.route("/api/cortex/codegen/convert/<job_id>", methods=["POST"])
def cortex_codegen_convert(job_id: str):
    """Parse codegen JS → Gherkin .feature + locator JSON, save to projects/cortex/."""
    if not _CODEGEN_OK:
        return jsonify({"ok": False, "error": "codegen module unavailable"}), 503
    payload = request.get_json(silent=True) or {}
    feature_name = payload.get("feature_name") or f"codegen-{job_id}"
    target_dir = payload.get("target_dir", "recordings")
    src = read_output(job_id)
    if not src.strip():
        return jsonify({"ok": False, "error": "no codegen output yet"}), 400
    gherkin, locators = codegen_to_gherkin(src, feature_name=feature_name)

    # Save the .feature
    root = _cortex_features_root(target_dir)
    root.mkdir(parents=True, exist_ok=True)
    feature_path = root / f"{feature_name}.feature"
    feature_path.write_text(gherkin, encoding="utf-8")

    # Save locators next to features as .json (in projects/cortex/locators/)
    loc_root = _cortex_root() / "locators"
    loc_root.mkdir(parents=True, exist_ok=True)
    locator_path = loc_root / f"{feature_name}.json"
    import json as _json
    locator_path.write_text(_json.dumps(locators, indent=2, ensure_ascii=False), encoding="utf-8")

    return jsonify({
        "ok": True,
        "feature_path": str(feature_path),
        "locator_path": str(locator_path),
        "gherkin": gherkin,
        "locator_count": len(locators),
    }), 200


def _cortex_root() -> Path:
    """projects/cortex root inside framework/src/test/resources/."""
    return Path(__file__).resolve().parent.parent / "src" / "test" / "resources" / "projects" / "cortex"


def _cortex_features_root(target_dir: str) -> Path:
    safe = "features" if target_dir not in ("features", "recordings") else target_dir
    return _cortex_root() / safe


@app.route("/api/cortex/recorder/inject", methods=["POST"])
def cortex_recorder_inject():
    """Inject an action into the running recorder from outside the browser."""
    payload = request.get_json(silent=True) or {}
    body, status = _recorder_call_with_body("POST", "/inject", payload)
    return jsonify(body), status


@app.route("/api/cortex/recorder/last-element")
def cortex_recorder_last_element():
    """Return the most recently captured element (for assert preview)."""
    body, status = _recorder_call("GET", "/last-element")
    return jsonify(body), status


@app.route("/api/cortex/recorder/elements")
def cortex_recorder_elements():
    """Return the latest page scan: all interactive elements + selectors."""
    body, status = _recorder_call("GET", "/elements")
    return jsonify(body), status


@app.route("/api/cortex/recorder/perform", methods=["POST"])
def cortex_recorder_perform():
    """Remote-control: dashboard tells JVM to actually click/fill in the browser."""
    payload = request.get_json(silent=True) or {}
    body, status = _recorder_call_with_body("POST", "/perform", payload)
    return jsonify(body), status


def _recorder_call_with_body(method: str, path: str, payload: dict) -> tuple[dict[str, Any], int]:
    """Like _recorder_call but with a JSON body."""
    p = _recorder_state.get("port") or _probe_recorder_port(timeout_total=2.0)
    if not p:
        return {"ok": False, "error": "Recorder calmiyor"}, 404
    data = json.dumps(payload).encode("utf-8")
    req = _urlreq.Request(
        f"http://127.0.0.1:{p}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with _urlreq.urlopen(req, timeout=4) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return (json.loads(body) if body else {}), resp.status
    except _urlerr.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
            return json.loads(err_body) if err_body else {"error": str(e)}, e.code
        except Exception:
            return {"error": str(e)}, e.code
    except Exception as e:
        return {"ok": False, "error": str(e)}, 502


@app.route("/api/cortex/generate-from-prompt", methods=["POST"])
def cortex_generate_from_prompt():
    """Lightweight Gherkin scaffold from a natural-language prompt.

    Currently a template-based generator (no LLM dependency). When AI Gateway
    is wired up, swap _generate_template() with a model call.
    """
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    tag    = (data.get("tag") or "@cortex @smoke @pw").strip()

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    feature_name, content = _generate_template(prompt, tag)
    return jsonify({"feature_name": feature_name, "content": content})


def _generate_template(prompt: str, tag: str) -> tuple[str, str]:
    """Pick a feature name + generate a Gherkin skeleton from the prompt."""
    lower = prompt.lower()
    # Hint: detect intent words
    if any(w in lower for w in ("login", "giris", "giriş", "sign in")):
        feature_name = "ai-generated-login"
        scenario_title = "AI üretilen giriş senaryosu"
        body = """    When I write "${ENV:CORTEX_USERNAME:test_user}" into "userNameInput"
    And I enter encrypted password alias "cortexUser" into "passwordInput"
    And I click "loginButton"
    And I wait for page to load
    Then I see "dashboardHome"
"""
    elif any(w in lower for w in ("logout", "cikis", "çıkış", "sign out")):
        feature_name = "ai-generated-logout"
        scenario_title = "AI üretilen çıkış senaryosu"
        body = """    When I click "userMenuButton" if it exists
    And I click "logoutButton"
    And I wait for page to load
    Then I see "loginContainer"
"""
    elif any(w in lower for w in ("forgot", "unuttum", "reset")):
        feature_name = "ai-generated-forgot-password"
        scenario_title = "AI üretilen şifre sıfırlama senaryosu"
        body = """    When I click "forgotPasswordLink"
    And I wait for page to load
    And I write "${ENV:CORTEX_USERNAME:test_user}" into "resetEmailInput"
    And I click "resetSubmitButton"
    Then I see "resetSuccessMessage"
"""
    else:
        feature_name = "ai-generated-scenario"
        scenario_title = prompt[:60].rstrip()
        body = """    # TODO: Below is a placeholder. Replace with real steps.
    When I see "loginContainer"
    Then I verify title contains "Cortex"
"""

    content = f"""# Auto-generated from prompt:
# "{prompt}"
{tag}
Feature: {feature_name.replace('-', ' ').title()}

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  Scenario: {scenario_title}
{body}
"""
    return feature_name, content


# ---------------------------------------------------------------------------
# Dashboard static
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    idx = DASHBOARD_DIR / "index.html"
    if not idx.exists():
        return (
            "<h1>Dashboard not installed</h1>"
            "<p>dashboard/static/index.html is missing. Update the repo.</p>",
            500,
        )
    return send_from_directory(str(DASHBOARD_DIR), "index.html")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    port = int(os.environ.get("DASHBOARD_PORT", "5001"))
    host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
    log.info("Cortex Dashboard listening on %s:%s", host, port)
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
