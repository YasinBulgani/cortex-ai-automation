"""Git repository kaynak dosyalarını çek — kaynak kod analizi için."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import get_current_user
from app.infra.models import User

router = APIRouter(prefix="/git", tags=["git"])

_ALLOWED_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs", ".go",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".xml",
    ".sql", ".rb", ".php", ".kt", ".swift", ".md", ".sh", ".toml",
}

_SKIP_DIRS = {
    "node_modules", "__pycache__", ".venv", "venv", "dist",
    "build", ".next", "target", ".git", ".gradle", ".idea",
}

_MAX_FILE_BYTES = 200 * 1024   # 200 KB / dosya
_MAX_TOTAL_BYTES = 3 * 1024 * 1024  # 3 MB toplam
_MAX_FILES = 100


class GitFetchRequest(BaseModel):
    url: str = Field(..., description="Git repo URL (https://...)")
    branch: str = Field("", description="Branch adı (boş = default branch)")
    token: str = Field("", description="Private repo için PAT / token")
    extensions: list[str] = Field(default_factory=list, description="Uzantı filtresi (boş = tümü)")
    path_prefix: str = Field("", description="Repo içi alt klasör (örn: src/)")
    max_files: int = Field(50, ge=1, le=_MAX_FILES)


class FetchedFile(BaseModel):
    name: str
    path: str
    content: str
    size: int
    lang: str


class GitFetchResponse(BaseModel):
    repo_name: str
    branch: str
    files: list[FetchedFile]
    total_files: int
    skipped: int


def _lang(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "ts": "TypeScript", "tsx": "TypeScript/React",
        "js": "JavaScript", "jsx": "JavaScript/React",
        "py": "Python", "java": "Java", "cs": "C#", "go": "Go",
        "html": "HTML", "css": "CSS", "scss": "SCSS",
        "json": "JSON", "yaml": "YAML", "yml": "YAML",
        "xml": "XML", "sql": "SQL", "rb": "Ruby", "php": "PHP",
        "kt": "Kotlin", "swift": "Swift", "md": "Markdown", "sh": "Shell",
    }.get(ext, "Metin")


def _inject_token(url: str, token: str) -> str:
    if not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return url
    host = parsed.hostname or ""
    netloc = f"{token}@{host}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _repo_name(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    name = path.rsplit("/", 1)[-1]
    return name.removesuffix(".git") or "repo"


@router.post("/fetch", response_model=GitFetchResponse)
def fetch_git_repo(
    body: GitFetchRequest,
    _: Annotated[User, Depends(get_current_user)],
) -> GitFetchResponse:
    """Repo'yu depth=1 klonla, kaynak dosyaları döndür."""
    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Yalnızca http/https URL desteklenir")

    allowed = set(body.extensions) if body.extensions else _ALLOWED_EXTENSIONS
    clone_url = _inject_token(body.url, body.token)

    tmp = tempfile.mkdtemp(prefix="bgts_git_")
    try:
        cmd = ["git", "clone", "--depth=1", "--single-branch"]
        if body.branch:
            cmd += ["--branch", body.branch]
        cmd += [clone_url, tmp]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()[:300]
            if body.token:
                err = err.replace(body.token, "***")
            raise HTTPException(status_code=422, detail=f"Git clone hatası: {err}")

        try:
            bp = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=tmp, capture_output=True, text=True, timeout=5,
            )
            actual_branch = bp.stdout.strip() or body.branch or "main"
        except Exception:
            actual_branch = body.branch or "main"

        root = Path(tmp)
        search_root = root / body.path_prefix.strip("/") if body.path_prefix.strip("/") else root

        files: list[FetchedFile] = []
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
            if len(files) >= body.max_files:
                skipped += 1
                continue

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                skipped += 1
                continue

            total_bytes += size
            files.append(FetchedFile(
                name=p.name,
                path=str(p.relative_to(root)),
                content=content,
                size=size,
                lang=_lang(p.name),
            ))

        return GitFetchResponse(
            repo_name=_repo_name(body.url),
            branch=actual_branch,
            files=files,
            total_files=len(files),
            skipped=skipped,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
