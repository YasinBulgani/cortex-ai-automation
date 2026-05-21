"""
TestwrightAI IDE — Editor Routes (güvenli sürüm)

Güvenlik notları:
- _safe_path artık pathlib.Path.resolve() + is_relative_to kullanıyor;
  prefix-startswith kontrolü kaldırıldı (komşu dizin escape'ine kapalı).
- subprocess çağrılarında shell=True YOK; tüm komutlar argv listesi
  ve shutil.which ile allowlisted mutlak yola çözülüyor.
- editor_run: kullanıcı stringi shlex.split ile parse edilir, ilk token
  exact-match allowlist'e bakılır.
- editor_run_tests: path _safe_path'tan geçer, pattern pytest -k için
  strict regex'e göre validate edilir; serbest `extra` kaldırılmış,
  yerine typed & allowlisted opsiyonlar (markers, maxfail, verbose,
  failfast) geldi.
- Tüm subprocess çağrılarına timeout ve stdout çıktısı için boyut cap
  (output cap) uygulanır; böylece pipe deadlock ve DoS risk azalır.
- editor_search query'si argv olarak geçer (grep'e parametre);
  shell enjeksiyonu yok.
- SSE generator'lerinde process teardown finally bloklarıyla koruma
  altına alındı (zombie ve pipe kapanması).

Bu modül internal bir geliştirici aracıdır; auth katmanı engine/app.py
tarafında zorunlu olmalıdır (F-07 kapsamı). Bu modül auth'u presume eder.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Iterator, Mapping

from flask import Response, jsonify, request

# Proje kök dizini (engine/routes/editor_routes.py → iki üst)
# resolve() ile sembolik link ve relative segment'ler temizlenir.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# Değiştirilebilir ama sabit anlam: string + Path her iki karşılaştırma
# noktasında kullanılabilsin diye hazırlandı.
_PROJECT_ROOT_STR: str = str(PROJECT_ROOT)

_IGNORE: frozenset[str] = frozenset({
    "__pycache__", "node_modules", ".git", ".idea", "venv",
    ".venv", "dist", "build", ".pytest_cache", ".mypy_cache",
    ".next", "coverage", "htmlcov", ".tox", ".eggs",
})

# EXACT-match executable allowlist. Hem çıplak ad hem de sürümlü varyant
# (python3, python3.11) resmen listelenmeli — prefix eşleşmesi YOK.
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
    ".py":      "🐍",
    ".ts":      "🔷",
    ".tsx":     "⚛️",
    ".js":      "📜",
    ".json":    "📋",
    ".yaml":    "⚙️",
    ".yml":     "⚙️",
    ".feature": "🥒",
    ".md":      "📄",
    ".html":    "🌐",
    ".css":     "🎨",
    ".sql":     "🗃️",
    ".sh":      "💻",
    ".txt":     "📝",
    ".toml":    "⚙️",
    ".env":     "🔒",
}

_LANG_MAP: dict[str, str] = {
    ".py":      "python",
    ".ts":      "typescript",
    ".tsx":     "typescript",
    ".js":      "javascript",
    ".jsx":     "javascript",
    ".json":    "json",
    ".yaml":    "yaml",
    ".yml":     "yaml",
    ".html":    "html",
    ".css":     "css",
    ".scss":    "scss",
    ".md":      "markdown",
    ".sh":      "shell",
    ".sql":     "sql",
    ".feature": "gherkin",
    ".toml":    "ini",
}

# Güvenli varsayılanlar: komut için maksimum çalışma süresi ve çıktı boyutu.
# Değerler env üzerinden kısıtlanabilir; üst sınır yine enforce edilir.
_DEFAULT_CMD_TIMEOUT = int(os.environ.get("EDITOR_CMD_TIMEOUT", "120"))
_MAX_CMD_TIMEOUT = 600  # 10dk üst sınır
_DEFAULT_TEST_TIMEOUT = int(os.environ.get("EDITOR_TEST_TIMEOUT", "600"))
_MAX_TEST_TIMEOUT = 1800  # 30dk üst sınır
_MAX_OUTPUT_BYTES = 5 * 1024 * 1024  # 5 MB stdout cap / istek

# pytest -k expression: boolean op'lar (and/or/not), parantez, köşeli
# parantez, alfasayısal + seçili noktalama. Shell metakarakter yasak.
_PYTEST_PATTERN_RE = re.compile(r"^[A-Za-z0-9_\-\.\[\] ()]+(?:\s+(?:and|or|not)\s+[A-Za-z0-9_\-\.\[\] ()]+)*$")
# maxfail gibi nümerik opsiyonlar için pozitif tamsayı (1..1000).
_POS_INT_RE = re.compile(r"^[1-9][0-9]{0,3}$")
# marker isimleri (pytest.mark.<name>): pytest'in kabul ettiği tanımlayıcı.
_MARKER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
# search query: kontrol karakterleri hariç, 2-200 karakter.
_SEARCH_Q_RE = re.compile(r"^[^\x00-\x1f\x7f]{2,200}$")


# ═════════════════════════════════════════════════════════════════════════
#  Güvenlik yardımcıları
# ═════════════════════════════════════════════════════════════════════════

def _safe_path(rel_path: str) -> Path:
    """
    rel_path'i PROJECT_ROOT altında mutlak yola çevirir; traversal'ı engeller.

    Güvenlik:
    - Path.resolve() sembolik link, ../, ./ segment'leri çözer.
    - is_relative_to() proper boundary kontrolü sağlar — prefix eşleşmesi yok.
    - Mutlak path girdileri otomatik olarak root-relative kabul edilmez;
      absolute rel_path verilirse ValueError.
    """
    if not isinstance(rel_path, str):
        raise ValueError("path str olmalı")
    if "\x00" in rel_path:
        raise ValueError("geçersiz karakter (NUL) path'te")
    # Mutlak path sokuşturmayı reddet (ör. 'C:/', '/etc/passwd').
    # Bu kontrol lstrip'ten ÖNCE yapılmalı; aksi halde '/etc/passwd'
    # lstrip sonrası 'etc/passwd' olarak sessizce kabul edilir.
    normalized = rel_path.replace("\\", "/")
    if normalized.startswith("/") or Path(normalized).is_absolute():
        raise ValueError("mutlak yol kabul edilmez")
    cleaned = normalized.lstrip("/")
    if not cleaned:
        return PROJECT_ROOT
    candidate = (PROJECT_ROOT / cleaned).resolve()
    # Python 3.9+: is_relative_to. Bu proper boundary kontrolüdür
    # (BGTS_Test_Donusum-evil gibi sibling escape'e karşı güvenli).
    if not _is_relative_to(candidate, PROJECT_ROOT):
        raise ValueError("Path traversal engellendi")
    return candidate


def _is_relative_to(candidate: Path, root: Path) -> bool:
    """Path.is_relative_to Python 3.9+'da var; minimum desteklenen sürüm
    budur, ama taşınabilirlik için saf implementasyon."""
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_allowed_executable(name: str) -> str:
    """
    Verilen executable adını strict allowlist ile eşleştirir ve mutlak
    yola çözer. Eşleşmezse veya PATH'de yoksa PermissionError fırlatır.
    """
    base = os.path.basename(name)
    if base not in _ALLOWED_COMMANDS:
        raise PermissionError(f'"{base}" komutu izin listesinde değil')
    resolved = shutil.which(base)
    if not resolved:
        raise PermissionError(f'"{base}" PATH üzerinde bulunamadı')
    return resolved


def _file_icon(name: str, is_dir: bool) -> str:
    if is_dir:
        return "📁"
    ext = os.path.splitext(name)[1].lower()
    return _ICON_MAP.get(ext, "📄")


# ═════════════════════════════════════════════════════════════════════════
#  Subprocess yardımcıları — timeout + output cap + zombie temizliği
# ═════════════════════════════════════════════════════════════════════════

def _stream_process(
    argv: list[str],
    cwd: str,
    *,
    env: Mapping[str, str] | None = None,
    output_cap: int = _MAX_OUTPUT_BYTES,
    line_decoder: str = "utf-8",
) -> Iterator[tuple[str, object]]:
    """
    Verilen argv'yi subprocess.Popen ile başlatır (shell=False), her satırı
    okur ve (kind, payload) tuple'larını yield eder. Output cap aşılınca
    süreç kill edilir. Finally teardown ile zombie bırakılmaz.

    yields:
        ("line", str)  - stdout satırı
        ("done", int)  - çıkış kodu
        ("error", str) - hata mesajı
    """
    try:
        proc = subprocess.Popen(
            argv,
            shell=False,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=dict(env) if env is not None else None,
        )
    except FileNotFoundError as e:
        yield ("error", f"executable bulunamadı: {e}")
        return
    except PermissionError as e:
        yield ("error", f"izin hatası: {e}")
        return

    total = 0
    try:
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            total += len(line.encode(line_decoder, errors="replace"))
            if total > output_cap:
                yield ("error", f"çıktı sınırı aşıldı ({output_cap} bayt)")
                proc.kill()
                break
            yield ("line", line.rstrip())
        proc.wait(timeout=5)
        yield ("done", proc.returncode)
    except Exception as e:  # pragma: no cover - defansif
        yield ("error", str(e))
    finally:
        if proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
        if proc.stdout is not None:
            try:
                proc.stdout.close()
            except Exception:
                pass


# ═════════════════════════════════════════════════════════════════════════
#  Test runner için tipli flag derleyici
# ═════════════════════════════════════════════════════════════════════════

def _build_pytest_argv(
    py_exe: str,
    test_path: Path,
    *,
    pattern: str | None,
    markers: str | None,
    maxfail: str | None,
    verbose: bool,
    failfast: bool,
) -> list[str]:
    """
    pytest çağrısını argv listesi olarak inşa eder. Serbest string YOK;
    her parametre strict regex'ten geçer.
    """
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
        argv.extend([f"--maxfail={int(maxfail)}"])
    return argv


# ═════════════════════════════════════════════════════════════════════════
#  Flask Blueprint-ish registrar
# ═════════════════════════════════════════════════════════════════════════

def register_editor_routes(app):
    # ── Dosya/Klasör Listesi ─────────────────────────────────────────────
    @app.route("/api/editor/tree", methods=["GET"])
    def editor_tree():
        rel = request.args.get("path", "")
        try:
            abs_path = _safe_path(rel)
            if not abs_path.is_dir():
                return jsonify({"ok": False, "error": "Klasör değil"})

            items = []
            for entry in sorted(
                os.scandir(abs_path),
                key=lambda e: (not e.is_dir(), e.name.lower()),
            ):
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
                    "name":         entry.name,
                    "path":         rel_entry,
                    "type":         "dir" if is_dir else "file",
                    "ext":          ext,
                    "icon":         _file_icon(entry.name, is_dir),
                    "lang":         _LANG_MAP.get(ext, "plaintext"),
                    "has_children": has_ch,
                })

            return jsonify({"ok": True, "items": items, "path": rel})
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Dosya Okuma ──────────────────────────────────────────────────────
    @app.route("/api/editor/file", methods=["GET"])
    def editor_read():
        rel = request.args.get("path", "")
        try:
            abs_path = _safe_path(rel)
            if not abs_path.is_file():
                return jsonify({"ok": False, "error": "Dosya bulunamadı"}), 404

            size = abs_path.stat().st_size
            if size > 1_500_000:
                return jsonify({"ok": False, "error": f"Dosya çok büyük ({size // 1024} KB)"}), 413

            ext = abs_path.suffix.lower()
            if ext not in _TEXT_EXTS and ext not in ("", ".sample", ".example"):
                try:
                    with abs_path.open("rb") as f:
                        chunk = f.read(512)
                    if b"\x00" in chunk:
                        return jsonify({"ok": False, "error": "Binary dosya açılamaz"}), 415
                except Exception:
                    pass

            content = abs_path.read_text(encoding="utf-8", errors="replace")

            return jsonify({
                "ok":      True,
                "content": content,
                "path":    rel,
                "lang":    _LANG_MAP.get(ext, "plaintext"),
                "lines":   content.count("\n") + 1,
                "size":    size,
            })
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Dosya Kaydetme ───────────────────────────────────────────────────
    @app.route("/api/editor/file", methods=["POST"])
    def editor_save():
        data = request.get_json(silent=True) or {}
        rel = data.get("path", "")
        content = data.get("content", "")
        if not isinstance(content, str):
            return jsonify({"ok": False, "error": "content str olmalı"}), 400
        try:
            abs_path = _safe_path(rel)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            return jsonify({
                "ok":    True,
                "path":  rel,
                "bytes": len(content.encode("utf-8")),
                "lines": content.count("\n") + 1,
            })
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Komut Çalıştırıcı (SSE Stream) ──────────────────────────────────
    @app.route("/api/editor/run", methods=["POST"])
    def editor_run():
        """
        Kullanıcı komutunu shlex.split ile argv'ye böler, ilk token'i exact
        allowlist'e karşı kontrol eder, shutil.which ile absolute yola
        çözer ve shell=False ile çalıştırır.
        """
        data = request.get_json(silent=True) or {}
        command = data.get("command", "")
        cwd_rel = data.get("cwd", "")

        if not isinstance(command, str) or not command.strip():
            return jsonify({"ok": False, "error": "Komut boş"}), 400

        # shlex.split ile POSIX-safe parse; quoting doğru işlenir,
        # shell metakarakterleri komut argümanı olarak değil literal olarak kalır.
        try:
            argv_user = shlex.split(command, posix=True)
        except ValueError as e:
            return jsonify({"ok": False, "error": f"komut parse edilemedi: {e}"}), 400
        if not argv_user:
            return jsonify({"ok": False, "error": "Komut boş"}), 400

        try:
            resolved_exe = _resolve_allowed_executable(argv_user[0])
        except PermissionError as e:
            return jsonify({"ok": False, "error": str(e)}), 403

        argv = [resolved_exe, *argv_user[1:]]

        try:
            cwd_path = _safe_path(cwd_rel) if cwd_rel else PROJECT_ROOT
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        if not cwd_path.is_dir():
            cwd_path = PROJECT_ROOT

        timeout_raw = data.get("timeout", _DEFAULT_CMD_TIMEOUT)
        try:
            timeout = int(timeout_raw)
        except (TypeError, ValueError):
            timeout = _DEFAULT_CMD_TIMEOUT
        timeout = max(1, min(timeout, _MAX_CMD_TIMEOUT))

        rel_cwd = os.path.relpath(str(cwd_path), _PROJECT_ROOT_STR)

        def generate():
            yield f"data: {json.dumps({'type':'start','argv':argv,'cwd':rel_cwd,'timeout':timeout})}\n\n"
            import threading

            killed = {"flag": False}

            def watchdog(p: subprocess.Popen):
                # Basit timeout watchdog — dış thread process'i kill eder.
                try:
                    p.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    killed["flag"] = True
                    try:
                        p.kill()
                    except Exception:
                        pass

            try:
                proc = subprocess.Popen(
                    argv, shell=False, cwd=str(cwd_path),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
            except FileNotFoundError as e:
                yield f"data: {json.dumps({'type':'error','msg':f'executable bulunamadı: {e}'})}\n\n"
                return
            except PermissionError as e:
                yield f"data: {json.dumps({'type':'error','msg':str(e)})}\n\n"
                return

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
                        yield f"data: {json.dumps({'type':'error','msg':f'çıktı sınırı aşıldı ({_MAX_OUTPUT_BYTES} bayt)'})}\n\n"
                        try:
                            proc.kill()
                        except Exception:
                            pass
                        break
                    yield f"data: {json.dumps({'type':'out','line':line.rstrip()})}\n\n"
                proc.wait(timeout=5)
                if killed["flag"]:
                    yield f"data: {json.dumps({'type':'error','msg':f'timeout ({timeout}s)'})}\n\n"
                yield f"data: {json.dumps({'type':'done','code':proc.returncode})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type':'error','msg':str(e)})}\n\n"
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

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Dosyalarda Arama ─────────────────────────────────────────────────
    @app.route("/api/editor/search", methods=["GET"])
    def editor_search():
        query = request.args.get("q", "").strip()
        rel = request.args.get("path", "")
        if not _SEARCH_Q_RE.match(query):
            return jsonify({"ok": False, "error": "Geçersiz sorgu (2-200 karakter)"}), 400
        try:
            abs_path = _safe_path(rel)
            # grep'i PATH'den absolute yola çöz; query argv olarak geçer,
            # shell metakarakter yorumlanmaz (shell=False default).
            grep_exe = shutil.which("grep")
            if not grep_exe:
                return jsonify({"ok": False, "error": "grep bulunamadı"}), 500
            argv = [
                grep_exe, "-r", "-n", "-I", "-F",  # -F: literal string, regex yok
                "--include=*.py", "--include=*.ts", "--include=*.feature",
                "--include=*.json", "--include=*.yaml", "--include=*.md",
                "-m", "5",
                "--",  # query sınırlayıcı — "-" ile başlasa bile flag sayılmasın
                query, str(abs_path),
            ]
            result = subprocess.run(
                argv, shell=False,
                capture_output=True, text=True, timeout=15,
            )
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
            return jsonify({"ok": True, "matches": matches[:60], "query": query})
        except subprocess.TimeoutExpired:
            return jsonify({"ok": False, "error": "Arama zaman aşımı"}), 504
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Proje İstatistikleri ─────────────────────────────────────────────
    @app.route("/api/editor/stats", methods=["GET"])
    def editor_stats():
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
            return jsonify({
                "ok":          True,
                "file_counts": dict(top),
                "total_files": sum(counts.values()),
                "total_lines": total_lines,
                "root":        _PROJECT_ROOT_STR,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Test Runner ──────────────────────────────────────────────────────
    @app.route("/api/editor/run-tests", methods=["POST"])
    def editor_run_tests():
        """
        pytest çalıştır. Serbest `extra` parametresi KALDIRILDI; yerine:
          - path     : test path (root-relative, _safe_path)
          - pattern  : pytest -k expression (regex validated)
          - markers  : pytest -m expression (tek marker adı, validated)
          - maxfail  : pozitif tamsayı, 1..9999
          - verbose  : bool (-v)
          - failfast : bool (-x)
        """
        data = request.get_json(silent=True) or {}
        path_str = data.get("path", "tests/")
        pattern = data.get("pattern") or None
        markers = data.get("markers") or None
        maxfail = data.get("maxfail") or None
        verbose = bool(data.get("verbose", True))
        failfast = bool(data.get("failfast", False))

        if not isinstance(path_str, str):
            return jsonify({"ok": False, "error": "path str olmalı"}), 400
        if pattern is not None and not isinstance(pattern, str):
            return jsonify({"ok": False, "error": "pattern str olmalı"}), 400
        if markers is not None and not isinstance(markers, str):
            return jsonify({"ok": False, "error": "markers str olmalı"}), 400
        if maxfail is not None and not isinstance(maxfail, (str, int)):
            return jsonify({"ok": False, "error": "maxfail str/int olmalı"}), 400

        try:
            test_path = _safe_path(path_str)
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400

        try:
            py_exe = _resolve_allowed_executable("python3")
        except PermissionError:
            # Fallback: sistem python3'ü ararken başarısızsa 'python'.
            try:
                py_exe = _resolve_allowed_executable("python")
            except PermissionError as e:
                return jsonify({"ok": False, "error": str(e)}), 500

        try:
            argv = _build_pytest_argv(
                py_exe=py_exe,
                test_path=test_path,
                pattern=pattern,
                markers=markers,
                maxfail=str(maxfail) if maxfail is not None else None,
                verbose=verbose,
                failfast=failfast,
            )
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400

        timeout_raw = data.get("timeout", _DEFAULT_TEST_TIMEOUT)
        try:
            timeout = int(timeout_raw)
        except (TypeError, ValueError):
            timeout = _DEFAULT_TEST_TIMEOUT
        timeout = max(1, min(timeout, _MAX_TEST_TIMEOUT))

        def generate():
            import threading

            results = {
                "passed": [], "failed": [], "error": [], "skipped": [],
                "duration": "",
            }
            killed = {"flag": False}
            yield f"data: {json.dumps({'type':'start','argv':argv,'timeout':timeout})}\n\n"

            try:
                proc = subprocess.Popen(
                    argv, shell=False, cwd=_PROJECT_ROOT_STR,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
            except FileNotFoundError as e:
                yield f"data: {json.dumps({'type':'error','msg':f'executable bulunamadı: {e}'})}\n\n"
                return

            def watchdog(p: subprocess.Popen):
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
                        yield f"data: {json.dumps({'type':'error','msg':f'çıktı sınırı aşıldı ({_MAX_OUTPUT_BYTES} bayt)'})}\n\n"
                        try:
                            proc.kill()
                        except Exception:
                            pass
                        break
                    m = re.match(r"^(.+?::[\w\[\]_\-. ]+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)", s)
                    if m:
                        tname, status = m.group(1).strip(), m.group(2)
                        key = status.lower() if status.lower() in results else "error"
                        results[key].append(tname)
                        yield f"data: {json.dumps({'type':'test','name':tname,'status':status})}\n\n"
                    md = re.search(r"in ([\d.]+)s", s)
                    if md:
                        results["duration"] = md.group(1) + "s"
                    yield f"data: {json.dumps({'type':'out','line':s})}\n\n"
                proc.wait(timeout=5)
                if killed["flag"]:
                    yield f"data: {json.dumps({'type':'error','msg':f'timeout ({timeout}s)'})}\n\n"
                yield f"data: {json.dumps({'type':'done','code':proc.returncode,'results':results})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type':'error','msg':str(e)})}\n\n"
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

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── AI Code Assistant (SSE stream) ────────────────────────────────────
    @app.route("/api/editor/ai-assist", methods=["POST"])
    def editor_ai_assist():
        """Kod parçasını LLM ile analiz et — Anthropic → OpenAI → Ollama."""
        data = request.get_json(silent=True) or {}
        code = str(data.get("code", ""))[:5000]
        action = str(data.get("action", "explain"))

        ACTION_PROMPTS = {
            "explain":   "Bu kodu kısaca Türkçe açıkla (3-5 cümle):",
            "test":      "Bu Python kodu için pytest test fonksiyonları yaz. Sadece kod ver:",
            "docstring": "Her fonksiyon/sınıf için Google-style docstring ekle. Sadece güncellenmiş kodu döndür:",
            "review":    "Bug, güvenlik açığı ve iyileştirme noktalarını Türkçe madde madde listele:",
            "refactor":  "SOLID ve PEP8 standartlarına göre refactor et. Sadece kodu döndür:",
        }
        system_msg = "Sen kıdemli Python/TypeScript test otomasyon mühendisisin. Kısa, net, kullanışlı cevap ver."
        user_msg = ACTION_PROMPTS.get(action, ACTION_PROMPTS["explain"]) + f"\n\n```\n{code}\n```"

        def generate():
            try:
                yield f"data: {json.dumps({'type':'start','action':action})}\n\n"
                ant_key = os.environ.get("ANTHROPIC_API_KEY", "")
                oai_key = os.environ.get("OPENAI_API_KEY", "")

                if ant_key and not ant_key.startswith("sk-place"):
                    import anthropic
                    client = anthropic.Anthropic(api_key=ant_key)
                    with client.messages.stream(
                        model="claude-3-haiku-20240307", max_tokens=1500,
                        system=system_msg,
                        messages=[{"role": "user", "content": user_msg}],
                    ) as stream:
                        for text in stream.text_stream:
                            yield f"data: {json.dumps({'type':'chunk','text':text})}\n\n"
                    yield f"data: {json.dumps({'type':'done','provider':'claude'})}\n\n"

                elif oai_key and not oai_key.startswith("sk-place"):
                    import openai
                    client = openai.OpenAI(api_key=oai_key)
                    with client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                        stream=True, max_tokens=1500,
                    ) as stream:
                        for chunk in stream:
                            text = chunk.choices[0].delta.content or ""
                            if text:
                                yield f"data: {json.dumps({'type':'chunk','text':text})}\n\n"
                    yield f"data: {json.dumps({'type':'done','provider':'openai'})}\n\n"

                else:
                    import urllib.request
                    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
                    try:
                        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=2) as r:
                            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
                        model = next((m for m in models if "llama3" in m or "mistral" in m), models[0] if models else "llama3")
                    except Exception:
                        model = "llama3"

                    payload = json.dumps({
                        "model": model,
                        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                        "stream": True,
                    }).encode()
                    req = urllib.request.Request(
                        f"{ollama_url}/v1/chat/completions", data=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=120) as r:
                        for raw in r:
                            line = raw.decode().strip()
                            if line.startswith("data: ") and line[6:] != "[DONE]":
                                try:
                                    text = json.loads(line[6:])["choices"][0]["delta"].get("content", "")
                                    if text:
                                        yield f"data: {json.dumps({'type':'chunk','text':text})}\n\n"
                                except Exception:
                                    pass
                    yield f"data: {json.dumps({'type':'done','provider':'ollama','model':model})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type':'error','msg':str(e)})}\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
