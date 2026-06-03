"""
Editor routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/editor_routes.py — register_editor_routes(app), port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/editor.py — APIRouter, port 8000 (consolidated)

Güvenlik notları (Flask orijinalinden korundu):
- _safe_path: Path.resolve() + is_relative_to ile traversal engeli.
- subprocess: shell=False; tüm komutlar argv listesi ve shutil.which allowlist.
- editor_run: shlex.split ile parse, exact-match allowlist.
- editor_run_tests: typed & allowlisted opsiyonlar (markers, maxfail, verbose, failfast).
- Tüm subprocess çağrılarına timeout ve output cap.
- SSE generator'lerinde process teardown finally bloklarıyla.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Iterator, Mapping, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/editor", tags=["engine", "editor"])

# ─── Proje kök dizini ────────────────────────────────────────────────────────

PROJECT_ROOT: Path = Path(__file__).resolve().parents[5]  # repo root
_PROJECT_ROOT_STR: str = str(PROJECT_ROOT)

_IGNORE: frozenset[str] = frozenset({
    "__pycache__", "node_modules", ".git", ".idea", "venv",
    ".venv", "dist", "build", ".pytest_cache", ".mypy_cache",
    ".next", "coverage", "htmlcov", ".tox", ".eggs",
})

_ALLOWED_COMMANDS: frozenset[str] = frozenset({
    "python", "python3", "python3.10", "python3.11", "python3.12",
    "pytest", "py.test",
    "npm", "npx", "ts-node", "node",
    "flask", "pip", "pip3",
    "ls", "cat", "grep", "find",
    "git", "which", "echo",
})

_TEXT_EXTS: frozenset[str] = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".json", ".yaml", ".yml",
    ".html", ".css", ".scss",
    ".md", ".txt", ".sh", ".bash",
    ".feature", ".sql", ".toml", ".cfg",
    ".ini", ".env", ".gitignore", ".makefile",
    ".dockerfile", ".conf", ".log",
})

_ICON_MAP: dict[str, str] = {
    ".py": "py", ".ts": "ts", ".tsx": "tsx", ".js": "js",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".feature": "feature", ".md": "md", ".html": "html",
    ".css": "css", ".sql": "sql", ".sh": "sh",
    ".txt": "txt", ".toml": "toml", ".env": "env",
}

_LANG_MAP: dict[str, str] = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".json": "json",
    ".yaml": "yaml", ".yml": "yaml", ".html": "html",
    ".css": "css", ".scss": "scss", ".md": "markdown",
    ".sh": "shell", ".sql": "sql", ".feature": "gherkin", ".toml": "ini",
}

_DEFAULT_CMD_TIMEOUT = int(os.environ.get("EDITOR_CMD_TIMEOUT", "120"))
_MAX_CMD_TIMEOUT = 600
_DEFAULT_TEST_TIMEOUT = int(os.environ.get("EDITOR_TEST_TIMEOUT", "600"))
_MAX_TEST_TIMEOUT = 1800
_MAX_OUTPUT_BYTES = 5 * 1024 * 1024

_PYTEST_PATTERN_RE = re.compile(
    r"^[A-Za-z0-9_\-\.\[\] ()]+(?:\s+(?:and|or|not)\s+[A-Za-z0-9_\-\.\[\] ()]+)*$"
)
_POS_INT_RE = re.compile(r"^[1-9][0-9]{0,3}$")
_MARKER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_SEARCH_Q_RE = re.compile(r"^[^\x00-\x1f\x7f]{2,200}$")


# ─── Güvenlik yardımcıları ───────────────────────────────────────────────────

def _is_relative_to(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_path(rel_path: str) -> Path:
    if not isinstance(rel_path, str):
        raise ValueError("path str olmalı")
    if "\x00" in rel_path:
        raise ValueError("geçersiz karakter (NUL) path'te")
    normalized = rel_path.replace("\\", "/")
    if normalized.startswith("/") or Path(normalized).is_absolute():
        raise ValueError("mutlak yol kabul edilmez")
    cleaned = normalized.lstrip("/")
    if not cleaned:
        return PROJECT_ROOT
    candidate = (PROJECT_ROOT / cleaned).resolve()
    if not _is_relative_to(candidate, PROJECT_ROOT):
        raise ValueError("Path traversal engellendi")
    return candidate


def _resolve_allowed_executable(name: str) -> str:
    base = os.path.basename(name)
    if base not in _ALLOWED_COMMANDS:
        raise PermissionError(f'"{base}" komutu izin listesinde değil')
    resolved = shutil.which(base)
    if not resolved:
        raise PermissionError(f'"{base}" PATH üzerinde bulunamadı')
    return resolved


def _file_icon(name: str, is_dir: bool) -> str:
    if is_dir:
        return "dir"
    ext = os.path.splitext(name)[1].lower()
    return _ICON_MAP.get(ext, "file")


def _build_pytest_argv(
    py_exe: str,
    test_path: Path,
    *,
    pattern: Optional[str],
    markers: Optional[str],
    maxfail: Optional[str],
    verbose: bool,
    failfast: bool,
) -> list[str]:
    argv = [py_exe, "-m", "pytest", str(test_path), "--tb=short", "--no-header", "--color=no"]
    if verbose:
        argv.append("-v")
    if failfast:
        argv.append("-x")
    if pattern:
        if not _PYTEST_PATTERN_RE.match(pattern):
            raise ValueError("geçersiz -k pattern'i")
        argv.extend(["-k", pattern])
    if markers:
        if not _MARKER_RE.match(markers):
            raise ValueError("geçersiz marker adı")
        argv.extend(["-m", markers])
    if maxfail:
        if not _POS_INT_RE.match(maxfail):
            raise ValueError("maxfail pozitif tamsayı olmalı")
        argv.append(f"--maxfail={int(maxfail)}")
    return argv


# ─── Schemas ─────────────────────────────────────────────────────────────────

class SaveFileBody(BaseModel):
    path: str = Field(..., min_length=1)
    content: str


class RunCommandBody(BaseModel):
    command: str = Field(..., min_length=1)
    cwd: str = ""
    timeout: int = _DEFAULT_CMD_TIMEOUT


class RunTestsBody(BaseModel):
    path: str = "tests/"
    pattern: Optional[str] = None
    markers: Optional[str] = None
    maxfail: Optional[str] = None
    verbose: bool = True
    failfast: bool = False
    timeout: int = _DEFAULT_TEST_TIMEOUT


class AIAssistBody(BaseModel):
    code: str = ""
    action: str = "explain"


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/tree")
def editor_tree(path: str = Query(default="")):
    """Dosya/klasör ağacını listeler."""
    try:
        abs_path = _safe_path(path)
        if not abs_path.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Klasör değil")

        items = []
        for entry in sorted(os.scandir(abs_path), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name in _IGNORE or entry.name.startswith("."):
                continue
            rel_entry = os.path.relpath(entry.path, _PROJECT_ROOT_STR)
            ext = os.path.splitext(entry.name)[1].lower()
            is_dir = entry.is_dir()
            has_ch = False
            if is_dir:
                try:
                    has_ch = any(
                        not c.name.startswith(".") and c.name not in _IGNORE
                        for c in os.scandir(entry.path)
                    )
                except PermissionError:
                    pass
            items.append({
                "name": entry.name, "path": rel_entry,
                "type": "dir" if is_dir else "file",
                "ext": ext, "icon": _file_icon(entry.name, is_dir),
                "lang": _LANG_MAP.get(ext, "plaintext"),
                "has_children": has_ch,
            })
        return {"ok": True, "items": items, "path": path}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/file")
def editor_read(path: str = Query(...)):
    """Dosya içeriğini döner."""
    try:
        abs_path = _safe_path(path)
        if not abs_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dosya bulunamadı")

        size = abs_path.stat().st_size
        if size > 1_500_000:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Dosya çok büyük ({size // 1024} KB)",
            )

        ext = abs_path.suffix.lower()
        if ext not in _TEXT_EXTS and ext not in ("", ".sample", ".example"):
            try:
                with abs_path.open("rb") as f:
                    chunk = f.read(512)
                if b"\x00" in chunk:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Binary dosya açılamaz",
                    )
            except HTTPException:
                raise
            except Exception:
                pass

        content = abs_path.read_text(encoding="utf-8", errors="replace")
        return {
            "ok": True, "content": content, "path": path,
            "lang": _LANG_MAP.get(ext, "plaintext"),
            "lines": content.count("\n") + 1, "size": size,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/file")
def editor_save(body: SaveFileBody):
    """Dosya içeriğini kaydeder."""
    try:
        abs_path = _safe_path(body.path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(body.content, encoding="utf-8")
        return {
            "ok": True, "path": body.path,
            "bytes": len(body.content.encode("utf-8")),
            "lines": body.content.count("\n") + 1,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/run")
def editor_run(body: RunCommandBody):
    """Komutu SSE stream olarak çalıştırır."""
    command = body.command.strip()
    if not command:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Komut boş")

    try:
        argv_user = shlex.split(command, posix=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"komut parse edilemedi: {exc}",
        )
    if not argv_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Komut boş")

    try:
        resolved_exe = _resolve_allowed_executable(argv_user[0])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    argv = [resolved_exe, *argv_user[1:]]

    try:
        cwd_path = _safe_path(body.cwd) if body.cwd else PROJECT_ROOT
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not cwd_path.is_dir():
        cwd_path = PROJECT_ROOT

    timeout = max(1, min(int(body.timeout), _MAX_CMD_TIMEOUT))
    rel_cwd = os.path.relpath(str(cwd_path), _PROJECT_ROOT_STR)

    def generate() -> Iterator[str]:
        yield f"data: {json.dumps({'type': 'start', 'argv': argv, 'cwd': rel_cwd, 'timeout': timeout})}\n\n"
        killed = {"flag": False}

        try:
            proc = subprocess.Popen(
                argv, shell=False, cwd=str(cwd_path),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
        except FileNotFoundError as exc:
            yield f"data: {json.dumps({'type': 'error', 'msg': f'executable bulunamadı: {exc}'})}\n\n"
            return
        except PermissionError as exc:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(exc)})}\n\n"
            return

        def watchdog(p: subprocess.Popen) -> None:
            try:
                p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                killed["flag"] = True
                try:
                    p.kill()
                except Exception:
                    pass

        wd = threading.Thread(target=watchdog, args=(proc,), daemon=True)
        wd.start()

        total = 0
        try:
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                total += len(line.encode("utf-8", errors="replace"))
                if total > _MAX_OUTPUT_BYTES:
                    yield f"data: {json.dumps({'type': 'error', 'msg': f'çıktı sınırı aşıldı ({_MAX_OUTPUT_BYTES} bayt)'})}\n\n"
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break
                yield f"data: {json.dumps({'type': 'out', 'line': line.rstrip()})}\n\n"
            proc.wait(timeout=5)
            if killed["flag"]:
                yield f"data: {json.dumps({'type': 'error', 'msg': f'timeout ({timeout}s)'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'code': proc.returncode})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(exc)})}\n\n"
        finally:
            if proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=5)
                except Exception:
                    pass
            try:
                if proc.stdout is not None:
                    proc.stdout.close()
            except Exception:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/search")
def editor_search(q: str = Query(...), path: str = Query(default="")):
    """Dosyalarda metin arar."""
    query = q.strip()
    if not _SEARCH_Q_RE.match(query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz sorgu (2-200 karakter)",
        )
    try:
        abs_path = _safe_path(path)
        grep_exe = shutil.which("grep")
        if not grep_exe:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="grep bulunamadı")

        argv = [
            grep_exe, "-r", "-n", "-I", "-F",
            "--include=*.py", "--include=*.ts", "--include=*.feature",
            "--include=*.json", "--include=*.yaml", "--include=*.md",
            "-m", "5", "--", query, str(abs_path),
        ]
        result = subprocess.run(argv, shell=False, capture_output=True, text=True, timeout=15)
        matches: list[dict] = []
        for line in result.stdout.strip().split("\n"):
            if not line or ":" not in line:
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                matches.append({
                    "file": os.path.relpath(parts[0], _PROJECT_ROOT_STR),
                    "line": parts[1],
                    "text": parts[2].strip()[:120],
                })
        return {"ok": True, "matches": matches[:60], "query": query}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Arama zaman aşımı")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/stats")
def editor_stats():
    """Proje istatistiklerini döner."""
    try:
        counts: dict[str, int] = {}
        total_lines = 0
        for root, dirs, files in os.walk(_PROJECT_ROOT_STR):
            dirs[:] = [d for d in dirs if d not in _IGNORE and not d.startswith(".")]
            for fname in files:
                if fname.startswith("."):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                counts[ext] = counts.get(ext, 0) + 1
                if ext in _TEXT_EXTS:
                    try:
                        fpath = os.path.join(root, fname)
                        if os.path.getsize(fpath) < 500_000:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                total_lines += sum(1 for _ in f)
                    except Exception:
                        pass
        top = sorted(counts.items(), key=lambda x: -x[1])[:10]
        return {
            "ok": True, "file_counts": dict(top),
            "total_files": sum(counts.values()),
            "total_lines": total_lines, "root": _PROJECT_ROOT_STR,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/run-tests")
def editor_run_tests(body: RunTestsBody):
    """pytest çalıştırır, SSE stream döner."""
    try:
        test_path = _safe_path(body.path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        py_exe = _resolve_allowed_executable("python3")
    except PermissionError:
        try:
            py_exe = _resolve_allowed_executable("python")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    try:
        argv = _build_pytest_argv(
            py_exe=py_exe, test_path=test_path,
            pattern=body.pattern, markers=body.markers,
            maxfail=str(body.maxfail) if body.maxfail is not None else None,
            verbose=body.verbose, failfast=body.failfast,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    timeout = max(1, min(int(body.timeout), _MAX_TEST_TIMEOUT))

    def generate() -> Iterator[str]:
        results = {
            "passed": [], "failed": [], "error": [], "skipped": [], "duration": "",
        }
        killed = {"flag": False}
        yield f"data: {json.dumps({'type': 'start', 'argv': argv, 'timeout': timeout})}\n\n"

        try:
            proc = subprocess.Popen(
                argv, shell=False, cwd=_PROJECT_ROOT_STR,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
        except FileNotFoundError as exc:
            yield f"data: {json.dumps({'type': 'error', 'msg': f'executable bulunamadı: {exc}'})}\n\n"
            return

        def watchdog(p: subprocess.Popen) -> None:
            try:
                p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                killed["flag"] = True
                try:
                    p.kill()
                except Exception:
                    pass

        wd = threading.Thread(target=watchdog, args=(proc,), daemon=True)
        wd.start()

        total = 0
        try:
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                s = line.rstrip()
                total += len(line.encode("utf-8", errors="replace"))
                if total > _MAX_OUTPUT_BYTES:
                    yield f"data: {json.dumps({'type': 'error', 'msg': f'çıktı sınırı aşıldı ({_MAX_OUTPUT_BYTES} bayt)'})}\n\n"
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break
                m = re.match(r"^(.+?::[\w\[\]_\-. ]+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)", s)
                if m:
                    tname, st = m.group(1).strip(), m.group(2)
                    key = st.lower() if st.lower() in results else "error"
                    results[key].append(tname)  # type: ignore[arg-type]
                    yield f"data: {json.dumps({'type': 'test', 'name': tname, 'status': st})}\n\n"
                md = re.search(r"in ([\d.]+)s", s)
                if md:
                    results["duration"] = md.group(1) + "s"
                yield f"data: {json.dumps({'type': 'out', 'line': s})}\n\n"
            proc.wait(timeout=5)
            if killed["flag"]:
                yield f"data: {json.dumps({'type': 'error', 'msg': f'timeout ({timeout}s)'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'code': proc.returncode, 'results': results})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(exc)})}\n\n"
        finally:
            if proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=5)
                except Exception:
                    pass
            try:
                if proc.stdout is not None:
                    proc.stdout.close()
            except Exception:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/ai-assist")
def editor_ai_assist(body: AIAssistBody):
    """Kod parçasını AI ile analiz eder — SSE stream döner."""
    code = str(body.code)[:5000]
    action = str(body.action)

    ACTION_PROMPTS = {
        "explain":   "Bu kodu kısaca Türkçe açıkla (3-5 cümle):",
        "test":      "Bu Python kodu için pytest test fonksiyonları yaz. Sadece kod ver:",
        "docstring": "Her fonksiyon/sınıf için Google-style docstring ekle. Sadece güncellenmiş kodu döndür:",
        "review":    "Bug, güvenlik açığı ve iyileştirme noktalarını Türkçe madde madde listele:",
        "refactor":  "SOLID ve PEP8 standartlarına göre refactor et. Sadece kodu döndür:",
    }
    system_msg = "Sen kıdemli Python/TypeScript test otomasyon mühendisisin. Kısa, net, kullanışlı cevap ver."
    user_msg = ACTION_PROMPTS.get(action, ACTION_PROMPTS["explain"]) + f"\n\n```\n{code}\n```"

    def stream_via_ai_gateway() -> Iterator[str]:
        try:
            import httpx  # type: ignore[import]
            base_url = os.environ.get("AI_GATEWAY_BASE_URL", "http://ai-gateway:8080").rstrip("/")
            key = os.environ.get("GATEWAY_INTERNAL_KEY", "")
            payload = {
                "task_type": "chat",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.2,
                "max_tokens": 1500,
                "stream": True,
            }
            headers = {"X-Internal-Key": key} if key else {}
            with httpx.stream("POST", f"{base_url}/ai/stream", json=payload, headers=headers, timeout=120.0) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        yield f"data: {json.dumps({'type': 'done', 'provider': 'ai-gateway'})}\n\n"
                        return
                    try:
                        data = json.loads(raw)
                    except Exception:
                        continue
                    if data.get("error"):
                        yield f"data: {json.dumps({'type': 'error', 'msg': str(data['error'])})}\n\n"
                        return
                    text = data.get("token") or data.get("text") or ""
                    if text:
                        yield f"data: {json.dumps({'type': 'chunk', 'text': text})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(exc)})}\n\n"

    def generate() -> Iterator[str]:
        try:
            yield f"data: {json.dumps({'type': 'start', 'action': action})}\n\n"

            gateway_url = os.environ.get("AI_GATEWAY_BASE_URL", "")
            if gateway_url:
                yield from stream_via_ai_gateway()
                return

            import urllib.request

            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            try:
                with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=2) as r:
                    models = [m["name"] for m in json.loads(r.read()).get("models", [])]
                model = next((m for m in models if "llama3" in m or "mistral" in m), models[0] if models else "llama3")
            except Exception:
                model = "llama3"

            payload_bytes = json.dumps({
                "model": model,
                "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                "stream": True,
            }).encode()
            req = urllib.request.Request(
                f"{ollama_url}/v1/chat/completions",
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                for raw in r:
                    line = raw.decode().strip()
                    if line.startswith("data: ") and line[6:] != "[DONE]":
                        try:
                            text = json.loads(line[6:])["choices"][0]["delta"].get("content", "")
                            if text:
                                yield f"data: {json.dumps({'type': 'chunk', 'text': text})}\n\n"
                        except Exception:
                            pass
            yield f"data: {json.dumps({'type': 'done', 'provider': 'ollama', 'model': model})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(exc)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
