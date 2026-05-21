"""
Playwright Codegen Recorder — wrapper around `python -m playwright codegen`.

Why this exists
---------------
Our custom recorder.js works but is fragile (Shadow DOM, cross-origin iframes,
React hydration, popup tabs). For sites where reliability matters more than
in-browser UX, we delegate to Microsoft's official `playwright codegen`.

Flow:
  1. Flask spawns `python -m playwright codegen <url>` subprocess
  2. Codegen opens Chromium + Playwright Inspector window
  3. User performs actions; Inspector writes JS code to --output file
  4. User clicks Stop in Inspector OR we kill the process
  5. We parse the generated JS → Gherkin
"""
from __future__ import annotations

import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class CodegenJob:
    id: str
    url: str
    output_file: str
    pid: Optional[int] = None
    started_at: float = field(default_factory=time.time)
    stopped_at: Optional[float] = None
    status: str = "starting"       # starting | running | stopped | error
    error: Optional[str] = None
    _proc: Optional[subprocess.Popen] = None  # not serialized

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_proc", None)
        return d


# Module-level job registry
_JOBS: dict[str, CodegenJob] = {}
_JOBS_LOCK = threading.Lock()


def _python_exe() -> str:
    """Find the Python executable to use — prefer the .venv we set up."""
    here = Path(__file__).resolve().parent
    # framework/.venv/bin/python (Mac/Linux) or .venv/Scripts/python.exe (Win)
    candidates = [
        here.parent / ".venv" / "bin" / "python",
        here.parent / ".venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


def is_codegen_available() -> tuple[bool, str]:
    """Check if `python -m playwright codegen` is functional."""
    try:
        r = subprocess.run(
            [_python_exe(), "-m", "playwright", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return False, f"playwright module not installed: {r.stderr.strip()}"
        return True, r.stdout.strip()
    except FileNotFoundError:
        return False, "python not found"
    except subprocess.TimeoutExpired:
        return False, "playwright check timed out"
    except Exception as e:
        return False, str(e)


def start_codegen(url: str, target: str = "javascript", browser: str = "chromium") -> CodegenJob:
    """
    Spawn `python -m playwright codegen` as background process.

    Returns the CodegenJob immediately. Poll status via get_job().
    """
    job_id = uuid.uuid4().hex[:12]
    out_dir = Path.home() / ".cortex" / "codegen"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file = out_dir / f"{job_id}.{_target_ext(target)}"

    job = CodegenJob(id=job_id, url=url, output_file=str(output_file))

    available, version = is_codegen_available()
    if not available:
        job.status = "error"
        job.error = f"Playwright codegen unavailable: {version}"
        with _JOBS_LOCK:
            _JOBS[job_id] = job
        return job

    cmd = [
        _python_exe(), "-m", "playwright", "codegen",
        f"--target={target}",
        f"--browser={browser}",
        f"--output={output_file}",
        url,
    ]

    # Detach so it survives Flask reload; we still hold a handle.
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        job._proc = proc
        job.pid = proc.pid
        job.status = "running"
    except Exception as e:
        job.status = "error"
        job.error = str(e)

    with _JOBS_LOCK:
        _JOBS[job_id] = job

    # Background watcher to flip status when process ends
    threading.Thread(target=_watch_job, args=(job_id,), daemon=True).start()
    return job


def _watch_job(job_id: str) -> None:
    job = _JOBS.get(job_id)
    if not job or not job._proc:
        return
    proc = job._proc
    proc.wait()
    with _JOBS_LOCK:
        job.stopped_at = time.time()
        if job.status == "running":
            job.status = "stopped"
        if proc.returncode and proc.returncode != 0:
            try:
                err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
                if err.strip():
                    job.error = err.strip()[-500:]
            except Exception:
                pass


def stop_codegen(job_id: str) -> bool:
    """Terminate the codegen process (user might close Inspector themselves)."""
    job = _JOBS.get(job_id)
    if not job or not job._proc:
        return False
    try:
        if job._proc.poll() is None:
            os.killpg(os.getpgid(job._proc.pid), signal.SIGTERM)
            time.sleep(0.3)
            if job._proc.poll() is None:
                os.killpg(os.getpgid(job._proc.pid), signal.SIGKILL)
        return True
    except Exception:
        return False


def get_job(job_id: str) -> Optional[CodegenJob]:
    return _JOBS.get(job_id)


def list_jobs() -> list[dict]:
    with _JOBS_LOCK:
        return [j.to_dict() for j in _JOBS.values()]


def read_output(job_id: str) -> str:
    job = _JOBS.get(job_id)
    if not job:
        return ""
    p = Path(job.output_file)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _target_ext(target: str) -> str:
    return {"javascript": "js", "python": "py", "java": "java", "csharp": "cs"}.get(target, "txt")


# ============================================================
#  Playwright JS → Gherkin parser
# ============================================================
#
# Codegen JS looks like:
#   const { test, expect } = require('@playwright/test');
#   test('test', async ({ page }) => {
#     await page.goto('https://cortex-test.bgtsai.com/');
#     await page.getByRole('textbox', { name: 'E-posta' }).fill('user@x.com');
#     await page.getByRole('button', { name: 'Giriş Yap' }).click();
#   });

_GHERKIN_HEADER = """@cortex @recorded @codegen
Feature: {name}

  Scenario: {scenario}
"""


def codegen_to_gherkin(js_source: str, feature_name: str = "Recorded Scenario") -> tuple[str, dict[str, dict]]:
    """
    Convert Playwright codegen JS → Gherkin .feature + locator pool.

    Returns (gherkin_text, locators_dict_for_json_file).
    """
    lines: list[str] = []
    locators: dict[str, dict] = {}
    counter = {"goto": 0, "fill": 0, "click": 0, "press": 0, "select": 0, "check": 0, "hover": 0, "other": 0}

    for raw in js_source.splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("import") or line.startswith("const ") \
           or line.startswith("test(") or line in ("});", "}", ");"):
            continue

        step = _convert_line(line, locators, counter)
        if step:
            lines.append(f"    {step}")

    body = "\n".join(lines) if lines else "    # (no actions recorded)"
    gherkin = _GHERKIN_HEADER.format(name=feature_name, scenario=feature_name) + body + "\n"
    return gherkin, locators


def _convert_line(line: str, locators: dict, counter: dict) -> str | None:
    """One JS line → one Gherkin step + locator side-effect."""

    # page.goto('https://...')
    m = re.search(r"page\.goto\(\s*['\"]([^'\"]+)['\"]", line)
    if m:
        counter["goto"] += 1
        return f'Given I open the recorded url "{m.group(1)}"'

    # page.getByRole('button', { name: 'Giriş Yap' }).click()
    m = re.search(r"page\.getByRole\(\s*['\"](\w+)['\"]\s*,\s*\{\s*name:\s*['\"]([^'\"]+)['\"]\s*\}\s*\)\.(\w+)\(\s*(['\"]([^'\"]*)['\"]\s*)?\)", line)
    if m:
        role, name, action, _wrap, value = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        key = _make_key(action, role, name)
        locators[key] = {"key": key, "type": "role", "value": f"{role}|{name}"}
        return _gherkin_for(action, key, value)

    # page.getByLabel('E-posta').fill('user@x.com')
    m = re.search(r"page\.getByLabel\(\s*['\"]([^'\"]+)['\"]\s*\)\.(\w+)\(\s*(['\"]([^'\"]*)['\"]\s*)?\)", line)
    if m:
        label, action, _w, value = m.group(1), m.group(2), m.group(3), m.group(4)
        key = _make_key(action, "label", label)
        locators[key] = {"key": key, "type": "label", "value": label}
        return _gherkin_for(action, key, value)

    # page.getByPlaceholder('Email').fill('...')
    m = re.search(r"page\.getByPlaceholder\(\s*['\"]([^'\"]+)['\"]\s*\)\.(\w+)\(\s*(['\"]([^'\"]*)['\"]\s*)?\)", line)
    if m:
        ph, action, _w, value = m.group(1), m.group(2), m.group(3), m.group(4)
        key = _make_key(action, "placeholder", ph)
        locators[key] = {"key": key, "type": "css", "value": f'[placeholder="{ph}"]'}
        return _gherkin_for(action, key, value)

    # page.getByText('Submit').click()
    m = re.search(r"page\.getByText\(\s*['\"]([^'\"]+)['\"]\s*\)\.(\w+)\(\s*(['\"]([^'\"]*)['\"]\s*)?\)", line)
    if m:
        text, action, _w, value = m.group(1), m.group(2), m.group(3), m.group(4)
        key = _make_key(action, "text", text)
        locators[key] = {"key": key, "type": "css", "value": f'text="{text}"'}
        return _gherkin_for(action, key, value)

    # page.getByTestId('email-input').fill('x')
    m = re.search(r"page\.getByTestId\(\s*['\"]([^'\"]+)['\"]\s*\)\.(\w+)\(\s*(['\"]([^'\"]*)['\"]\s*)?\)", line)
    if m:
        tid, action, _w, value = m.group(1), m.group(2), m.group(3), m.group(4)
        key = _make_key(action, "testid", tid)
        locators[key] = {"key": key, "type": "css", "value": f'[data-testid="{tid}"]'}
        return _gherkin_for(action, key, value)

    # page.locator('#login').click()
    m = re.search(r"page\.locator\(\s*['\"]([^'\"]+)['\"]\s*\)\.(\w+)\(\s*(['\"]([^'\"]*)['\"]\s*)?\)", line)
    if m:
        sel, action, _w, value = m.group(1), m.group(2), m.group(3), m.group(4)
        key = _make_key(action, "locator", sel)
        locators[key] = {"key": key, "type": "css", "value": sel}
        return _gherkin_for(action, key, value)

    # page.waitForURL(...) / await page.waitForLoadState(...) → comment
    if "waitForURL" in line or "waitForLoadState" in line:
        return f"# {line}"

    return None


def _gherkin_for(action: str, key: str, value: str | None) -> str:
    counter_local = {"action": action}
    if action == "click":
        return f'When I click "{key}"'
    if action == "fill":
        return f'* I write "{value or ""}" into "{key}"'
    if action == "press":
        return f'* I press "{(value or "Enter").upper()}"'
    if action == "selectOption":
        return f'* I write "{value or ""}" into "{key}"'   # selection works through write+enter
    if action == "check":
        return f'When I click "{key}"'
    if action == "uncheck":
        return f'When I click "{key}"'
    if action == "hover":
        return f'* I hover over "{key}"'
    if action == "scrollIntoViewIfNeeded":
        return f'* I scroll to "{key}"'
    # Fallback
    return f'* I {action} "{key}"'


def _make_key(action: str, kind: str, raw: str) -> str:
    """Generate a camelCase Gherkin key from raw label/text/selector."""
    s = re.sub(r"[^a-zA-Z0-9]+", " ", raw).strip()
    parts = s.split()
    if not parts:
        return f"{action}Element"
    head = parts[0].lower()
    tail = "".join(p.capitalize() for p in parts[1:])
    suffix = {"click": "Btn", "fill": "Field", "check": "Box", "hover": "Item"}.get(action, "")
    return f"{head}{tail}{suffix}"


if __name__ == "__main__":
    # Quick CLI for testing the parser
    if len(sys.argv) > 1 and sys.argv[1] == "--parse":
        src = Path(sys.argv[2]).read_text() if len(sys.argv) > 2 else sys.stdin.read()
        gherkin, locators = codegen_to_gherkin(src, "Test Run")
        print(gherkin)
        print("---LOCATORS---")
        import json
        print(json.dumps(locators, indent=2))
