"""Git Fetch — thin service facade for repository source-code retrieval.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
Wraps the subprocess-based git clone logic in router.py.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs", ".go",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".xml",
    ".sql", ".rb", ".php", ".kt", ".swift", ".md", ".sh", ".toml",
}
_SKIP_DIRS = {
    "node_modules", "__pycache__", ".venv", "venv", "dist",
    "build", ".next", "target", ".git", ".gradle", ".idea",
}
_MAX_FILE_BYTES = 200 * 1024
_MAX_TOTAL_BYTES = 3 * 1024 * 1024
_MAX_FILES = 100

# In-process repo store (ephemeral — replace with persistent layer as needed)
_repos: Dict[str, Dict[str, Any]] = {}


def _inject_token(url: str, token: str) -> str:
    if not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return url
    netloc = f"{token}@{parsed.hostname or ''}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _repo_name(url: str) -> str:
    return urlparse(url).path.strip("/").split("/")[-1].removesuffix(".git") or "repo"


def _lang(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "ts": "TypeScript", "tsx": "TypeScript/React", "js": "JavaScript",
        "jsx": "JavaScript/React", "py": "Python", "java": "Java", "cs": "C#",
        "go": "Go", "html": "HTML", "css": "CSS", "scss": "SCSS",
        "json": "JSON", "yaml": "YAML", "yml": "YAML", "xml": "XML",
        "sql": "SQL", "rb": "Ruby", "php": "PHP", "kt": "Kotlin",
        "swift": "Swift", "md": "Markdown", "sh": "Shell",
    }.get(ext, "Metin")


def fetch_repo(
    url: str,
    branch: str = "",
    token: str = "",
    extensions: Optional[List[str]] = None,
    path_prefix: str = "",
    max_files: int = 50,
) -> Dict[str, Any]:
    """Clone a git repository and extract source files.

    Args:
        url: HTTPS git repository URL.
        branch: Branch name (empty = default branch).
        token: PAT/token for private repositories.
        extensions: File extension whitelist (empty = all allowed).
        path_prefix: Sub-directory within the repo to search.
        max_files: Maximum files to return (1–100).

    Returns:
        Dict with 'repo_id', 'repo_name', 'branch', 'files', 'total_files', 'skipped'.

    Raises:
        ValueError: Invalid URL, git clone failure, or bad parameters.
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("'url' boş olamaz.")
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError("Yalnızca http/https URL'leri desteklenir.")

    max_files = max(1, min(int(max_files), _MAX_FILES))
    allowed = {e if e.startswith(".") else f".{e}" for e in (extensions or [])} or _ALLOWED_EXTENSIONS

    clone_url = _inject_token(url, token)
    tmp = tempfile.mkdtemp(prefix="neurex_git_")
    try:
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["--branch", branch]
        cmd += [clone_url, tmp]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            err = proc.stderr or proc.stdout or "git clone hatası"
            if token:
                err = err.replace(token, "***")
            raise ValueError(f"Git clone hatası: {err}")

        try:
            bp = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=tmp, capture_output=True, text=True, timeout=5,
            )
            actual_branch = bp.stdout.strip() or branch or "main"
        except Exception:
            actual_branch = branch or "main"

        root = Path(tmp)
        search_root = root / path_prefix.strip("/") if path_prefix.strip("/") else root

        files: List[Dict[str, Any]] = []
        skipped = 0
        total_bytes = 0

        for p in sorted(search_root.rglob("*")):
            if not p.is_file():
                continue
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            if p.suffix not in allowed:
                skipped += 1
                continue
            size = p.stat().st_size
            if size > _MAX_FILE_BYTES or total_bytes + size > _MAX_TOTAL_BYTES:
                skipped += 1
                continue
            if len(files) >= max_files:
                skipped += 1
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                skipped += 1
                continue
            total_bytes += size
            files.append({"name": p.name, "path": str(p.relative_to(root)), "content": content, "size": size, "lang": _lang(p.name)})

        repo_id = uuid.uuid4().hex[:12]
        result: Dict[str, Any] = {
            "repo_id": repo_id,
            "repo_name": _repo_name(url),
            "branch": actual_branch,
            "files": files,
            "total_files": len(files),
            "skipped": skipped,
        }
        _repos[repo_id] = result
        logger.info("Repo çekildi: %s (%d dosya, repo_id=%s)", url, len(files), repo_id)
        return result
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def get_diff(repo_id: str, from_ref: str = "HEAD~1", to_ref: str = "HEAD") -> Dict[str, Any]:
    """Placeholder: return diff metadata for a previously fetched repo.

    Actual diff requires a persistent clone. Returns a stub until extended.

    Raises:
        KeyError: repo_id not found.
    """
    if repo_id not in _repos:
        raise KeyError(f"Repo '{repo_id}' bulunamadı — önce fetch_repo çağırın.")
    return {
        "repo_id": repo_id,
        "from_ref": from_ref,
        "to_ref": to_ref,
        "note": "Diff yalnızca kalıcı clone deposuyla desteklenir.",
    }


def list_commits(repo_id: str) -> List[Dict[str, Any]]:
    """Placeholder: return commit list for a previously fetched repo.

    Shallow clone (depth=1) returns only the tip commit.

    Raises:
        KeyError: repo_id not found.
    """
    if repo_id not in _repos:
        raise KeyError(f"Repo '{repo_id}' bulunamadı — önce fetch_repo çağırın.")
    repo = _repos[repo_id]
    return [{"sha": "shallow", "branch": repo.get("branch"), "note": "--depth 1 — tek commit görünür."}]
