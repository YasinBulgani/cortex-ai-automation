"""Nexus Repo — Repo Tarama Motoru.

Akış:
  1. Repo'yu geçici dizine klonla (git clone --depth 1)
     - Public repo: doğrudan URL
     - Token auth: URL'e token gömülür (HTTPS Basic)
     - SSH: credential_ref → NEXUS_SSH_KEY_<REF> env var
  2. Kaynak dosyaları yürü — dil tespiti, boyut, token tahmini
  3. Endpoint'leri tespit et (regex tabanlı, framework'e göre)
  4. Önemli dosyaları Ollama ile özetle (LLM summarizer)
  5. NexusCrawlJob kaydını güncelle
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse

from sqlalchemy.orm import Session

from app.config import settings
from app.infra.database import SessionLocal
from .models import NexusCrawlJob, NexusFile, NexusEndpoint, NexusLLMLog

_log = logging.getLogger(__name__)

# Desteklenen uzantı → dil eşlemesi
_EXT_LANG: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
}

# Dosya başına token tahmini: 4 karakter ≈ 1 token (ortalama)
_CHARS_PER_TOKEN = 4

# Bir taramada işlenecek maksimum dosya sayısı (timeout koruması)
_MAX_FILES = 500

# Maksimum dosya boyutu — bu sınırı geçen dosyalar özetlenmez
_MAX_FILE_BYTES = 200_000


# ── Endpoint Regex Desenleri ──────────────────────────────────────────────────

# FastAPI / Flask / Django / Express / Spring / Rails
_ENDPOINT_PATTERNS: list[tuple[str, str]] = [
    # FastAPI / Starlette
    (r'@(?:app|router)\.(get|post|put|patch|delete|head|options)\s*\(\s*["\']([^"\']+)["\']', "python"),
    # Flask
    (r'@(?:app|bp|blueprint)\.(route)\s*\(\s*["\']([^"\']+)["\']', "python"),
    # Django urls.py
    (r'(?:path|re_path|url)\s*\(\s*["\']([^"\']+)["\']', "python"),
    # Express.js
    (r'(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', "javascript"),
    # NestJS / TypeScript decorators
    (r'@(?:Get|Post|Put|Patch|Delete|Head)\s*\(\s*["\']([^"\']*)["\']', "typescript"),
    # Spring MVC
    (r'@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']', "java"),
    # Rails routes.rb
    (r'(?:get|post|put|patch|delete)\s+["\']([^"\']+)["\']', "ruby"),
    # Go (gorilla/mux, gin, chi)
    (r'(?:r|router|mux)\.(GET|POST|PUT|PATCH|DELETE|Handle(?:Func)?)\s*\(\s*["\']([^"\']+)["\']', "go"),
]

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _detect_endpoints(content: str, file_path: str, lang: str) -> list[dict]:
    """Regex ile HTTP endpoint'lerini tespit et."""
    results: list[dict] = []
    lines = content.split("\n")

    for pattern_str, pattern_lang in _ENDPOINT_PATTERNS:
        if pattern_lang and pattern_lang != lang:
            continue
        pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
        for match in pattern.finditer(content):
            groups = match.groups()
            if len(groups) == 1:
                method = "GET"
                path = groups[0]
            elif len(groups) == 2:
                method = groups[0].upper() if groups[0].lower() in _HTTP_METHODS else "GET"
                path = groups[1] if groups[1] else groups[0]
            else:
                continue

            # Satır numarasını bul
            line_no = content[: match.start()].count("\n") + 1

            results.append({
                "method": method,
                "path": path,
                "source_file": file_path,
                "source_line": line_no,
                "auth_required": _guess_auth(content, match.start()),
            })

    return results


def _guess_auth(content: str, pos: int) -> bool:
    """Endpoint yakınında auth/security decorator var mı tahmin et."""
    window = content[max(0, pos - 300): pos + 50]
    auth_hints = re.compile(
        r"@(?:login_required|requires_auth|JWTBearer|Depends\s*\(\s*get_current|"
        r"auth_required|permission_classes|PreAuthorize|Secured)\b",
        re.IGNORECASE,
    )
    return bool(auth_hints.search(window))


def _resolve_clone_url(repo_url: str, credential_ref: Optional[str]) -> tuple[str, dict]:
    """
    Kimlik bilgilerini URL'e veya git env'e göm.

    credential_ref biçimleri:
      token:<ENV_VAR_NAME>        → HTTPS Basic; URL'e token gömülür
      user:<ENV_VAR_NAME>         → kullanıcı adı + token (user:token)
      ssh:<ENV_VAR_NAME>          → SSH özel anahtar (env'den okunur, geçici dosyaya yazılır)
      None / boş                  → public repo, kimlik gerekmez
    """
    env_extra: dict = {}

    if not credential_ref:
        return repo_url, env_extra

    try:
        kind, env_var = credential_ref.split(":", 1)
        kind = kind.strip().lower()
        secret = os.environ.get(env_var.strip(), "").strip()

        if not secret:
            _log.warning("credential_ref '%s' için env var '%s' boş — anonim klonlamaya düşülüyor", credential_ref, env_var)
            return repo_url, env_extra

        if kind == "token":
            # HTTPS URL'e token gömme: https://TOKEN@host/path
            parsed = urlparse(repo_url)
            authed = parsed._replace(netloc=f"oauth2:{secret}@{parsed.hostname}"
                                     + (f":{parsed.port}" if parsed.port else ""))
            return urlunparse(authed), env_extra

        if kind == "user":
            # user:password biçimi; secret = "username:password" veya sadece token
            parsed = urlparse(repo_url)
            authed = parsed._replace(netloc=f"{secret}@{parsed.hostname}"
                                     + (f":{parsed.port}" if parsed.port else ""))
            return urlunparse(authed), env_extra

        if kind == "ssh":
            # SSH anahtarı geçici dosyaya yaz
            key_dir = tempfile.mkdtemp(prefix="nexus_ssh_")
            key_path = os.path.join(key_dir, "id_rsa")
            with open(key_path, "w") as f:
                f.write(secret)
            os.chmod(key_path, 0o600)
            env_extra["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
            env_extra["_ssh_key_dir"] = key_dir  # temizlik için
            return repo_url, env_extra

    except (ValueError, AttributeError) as e:
        _log.warning("credential_ref parse hatası: %s — anonim klonlamaya düşülüyor", e)

    return repo_url, env_extra


def _clone_repo(
    repo_url: str,
    branch: str,
    target_dir: str,
    credential_ref: Optional[str] = None,
) -> Optional[str]:
    """Repo'yu klonla; commit SHA döndür. Hata varsa None."""
    clone_url, env_extra = _resolve_clone_url(repo_url, credential_ref)
    ssh_key_dir = env_extra.pop("_ssh_key_dir", None)

    git_env = {**os.environ, **env_extra}

    def _run_clone(url: str, extra_args: list[str] | None = None) -> int:
        cmd = ["git", "clone", "--depth", "1"] + (extra_args or []) + [url, target_dir]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=git_env)
        return r.returncode

    try:
        rc = _run_clone(clone_url, ["--branch", branch, "--single-branch"])
        if rc != 0:
            # Branch bulunamadıysa branch parametresi olmadan tekrar dene
            if os.path.isdir(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            rc = _run_clone(clone_url)
            if rc != 0:
                _log.error("git clone başarısız (rc=%d): %s", rc, repo_url)
                return None

        # Commit SHA al
        sha_result = subprocess.run(
            ["git", "-C", target_dir, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return sha_result.stdout.strip() if sha_result.returncode == 0 else None

    except Exception as e:
        _log.exception("git clone hatası: %s", e)
        return None
    finally:
        if ssh_key_dir and os.path.isdir(ssh_key_dir):
            shutil.rmtree(ssh_key_dir, ignore_errors=True)


# ── LLM Dosya Özetleyici ──────────────────────────────────────────────────────

# Özetlenecek dosya sayısı üst sınırı (Ollama yavaş olabilir)
_MAX_FILES_TO_SUMMARIZE = 30
# Özetlenecek dosya boyutu alt sınırı — çok küçük dosyaları atla
_MIN_FILE_BYTES_SUMMARIZE = 500

_SUMMARIZE_PROMPT = (
    "Aşağıdaki kaynak kodu dosyasını 2-3 cümle ile özetle. "
    "Dosyanın amacını, içerdiği temel sınıf/fonksiyonları ve önemli iş mantığını belirt. "
    "Teknik jargon kullan, Türkçe yaz.\n\n"
    "DOSYA: {path}\n\n"
    "KOD:\n{content}"
)


def _summarize_file_llm(path: str, content: str, model: str) -> Optional[str]:
    """AI Gateway üzerinden tek dosya özeti üret. Hata olursa None."""
    from app.domains.ai.gateway_client import gateway_complete

    prompt = _SUMMARIZE_PROMPT.format(
        path=path,
        content=content[:6000],
    )
    try:
        return gateway_complete(
            task_type="nexus_code_analyze",
            user_message=prompt,
            temperature=0.1,
            max_tokens=300,
        ).strip()
    except Exception as e:
        _log.debug("Dosya özeti başarısız (%s): %s", path, e)
        return None


def run_crawl_job(job_id: str) -> None:
    """Arka planda çalıştırılacak crawl iş fonksiyonu."""
    db: Session = SessionLocal()
    tmp_dir: Optional[str] = None

    try:
        job: Optional[NexusCrawlJob] = db.query(NexusCrawlJob).filter(NexusCrawlJob.id == job_id).first()
        if not job:
            _log.error("CrawlJob bulunamadı: %s", job_id)
            return

        project = job.project
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        # ── 1. Klonla ────────────────────────────────────────────────
        tmp_dir = tempfile.mkdtemp(prefix="nexus_crawl_")
        repo_dir = os.path.join(tmp_dir, "repo")

        commit_sha = _clone_repo(project.repo_url, project.branch, repo_dir, project.credential_ref)
        if commit_sha is None and not os.path.isdir(repo_dir):
            job.status = "failed"
            job.error_message = "Repo klonlanamadı. URL ve kimlik bilgilerini kontrol edin."
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            return

        job.commit_sha = commit_sha
        db.commit()

        # ── 2. Dosyaları yürü ────────────────────────────────────────
        files_scanned = 0
        all_endpoints: list[dict] = []
        # (relative_path, content) → özetlenecek dosyalar
        summarize_queue: list[tuple[str, str]] = []

        for root, dirs, files in os.walk(repo_dir):
            # Gürültülü dizinleri atla
            dirs[:] = [
                d for d in dirs
                if d not in {".git", "node_modules", "__pycache__", ".venv", "venv",
                             "dist", "build", ".next", "target", "vendor", ".gradle"}
            ]

            for fname in files:
                if files_scanned >= _MAX_FILES:
                    break

                fpath = os.path.join(root, fname)
                ext = Path(fname).suffix.lower()
                lang = _EXT_LANG.get(ext)
                if not lang:
                    continue  # Sadece kaynak kod dosyaları

                try:
                    stat = os.stat(fpath)
                    size = stat.st_size
                    relative_path = os.path.relpath(fpath, repo_dir)

                    content: Optional[str] = None
                    if size <= _MAX_FILE_BYTES:
                        with open(fpath, encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                    tokens_est = (size // _CHARS_PER_TOKEN) if size > 0 else 0

                    # DB kaydı
                    nf = NexusFile(
                        crawl_job_id=job.id,
                        path=relative_path,
                        language=lang,
                        size_bytes=size,
                        tokens_estimate=tokens_est,
                    )
                    db.add(nf)
                    files_scanned += 1

                    # Endpoint tespiti
                    if content:
                        endpoints = _detect_endpoints(content, relative_path, lang)
                        all_endpoints.extend(endpoints)

                    # LLM özet kuyruğuna ekle (büyük/önemli dosyalar öncelikli)
                    if (
                        content
                        and size >= _MIN_FILE_BYTES_SUMMARIZE
                        and len(summarize_queue) < _MAX_FILES_TO_SUMMARIZE
                    ):
                        summarize_queue.append((relative_path, content))

                except (OSError, PermissionError):
                    continue

        db.flush()

        # ── 3. Endpoint kayıtları ────────────────────────────────────
        seen: set[tuple] = set()
        for ep in all_endpoints:
            key = (ep["method"], ep["path"])
            if key in seen:
                continue
            seen.add(key)
            ne = NexusEndpoint(
                crawl_job_id=job.id,
                method=ep["method"],
                path=ep["path"],
                source_file=ep.get("source_file"),
                source_line=ep.get("source_line"),
                auth_required=ep.get("auth_required", False),
            )
            db.add(ne)

        db.commit()

        # ── 4. LLM dosya özetleri (Ollama hızlı model) ───────────────
        # Ollama erişilebilirse ve proje Ollama kullanıyorsa özetle
        summarize_model = "nexus_code_analyze"  # gateway task type — provider gateway tarafından seçilir
        if summarize_queue:
            _log.info("CrawlJob %s: %d dosya özetleniyor...", job_id, len(summarize_queue))
            summarized = 0
            for rel_path, content in summarize_queue:
                start_ts = time.time()
                summary = _summarize_file_llm(rel_path, content, summarize_model)
                latency_ms = int((time.time() - start_ts) * 1000)

                if summary:
                    # İlgili NexusFile kaydını güncelle
                    db.query(NexusFile).filter(
                        NexusFile.crawl_job_id == job.id,
                        NexusFile.path == rel_path,
                    ).update({"summary": summary})
                    summarized += 1

                # LLM log
                db.add(NexusLLMLog(
                    project_id=project.id,
                    operation="crawl_file_summary",
                    model=summarize_model,
                    prompt_tokens=len(content) // 4,
                    completion_tokens=len(summary or "") // 4,
                    latency_ms=latency_ms,
                    success=summary is not None,
                ))

            db.commit()
            _log.info("CrawlJob %s: %d/%d dosya özetlendi", job_id, summarized, len(summarize_queue))

        job.files_scanned = files_scanned
        job.endpoints_found = len(seen)
        job.status = "done"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        _log.info("CrawlJob %s tamamlandı: %d dosya, %d endpoint", job_id, files_scanned, len(seen))

    except Exception as exc:
        _log.exception("CrawlJob %s başarısız: %s", job_id, exc)
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            try:
                db.commit()
            except Exception:
                pass
    finally:
        db.close()
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
