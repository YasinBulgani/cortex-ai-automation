"""DSL sözlüğü düzenlemeleri için minimal git istemcisi.

Desteklenen iki mod:

    * `direct_commit` — aktif branch'e doğrudan commit (+ opsiyonel push).
    * `pr`            — yeni bir `dsl/edit-<id>` branch'i aç, push et, GitHub
      üzerinde Pull Request oluştur.

Tasarım kararları:
    * `git` CLI'ya subprocess ile konuşuyoruz — `GitPython`/`pygit2` ek bağımlılık
      getiriyor ve container tarafında zaten `git` var.
    * Yazarlık (author) backend .env'den gelir; her commit'e request eden kullanıcı
      trailer olarak `Change-Proposed-By: <email>` şeklinde eklenir.
    * Kritik invariant: worktree clean değilse commit yapılmaz (yarış koşulunu
      önlemek için). Konfig `DSL_GIT_STRICT_CLEAN=false` ile devre dışı bırakılabilir.
    * `DSL_GIT_ENABLED=false` ise hiçbir git işlemi yapılmaz — YAML diske yazılır,
      proposal `status="merged"` ama `commit_sha=None` kalır. Dev/test için uygun.

Hatalar `GitClientError` olarak yükseltilir; router 500 yerine 409/503 çevirir.
"""

from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import httpx

logger = logging.getLogger(__name__)


class GitClientError(RuntimeError):
    """Git veya remote API operasyonu başarısız olduğunda."""


@dataclass(frozen=True)
class GitConfig:
    enabled: bool = False
    mode: str = "direct_commit"            # "direct_commit" | "pr"
    repo_path: Path = Path.cwd()
    remote: str = "origin"
    base_branch: str = "main"
    branch_prefix: str = "dsl/edit-"
    author_name: str = "DSL Bot"
    author_email: str = "[email protected]"
    push: bool = False                     # direct_commit için push yap?
    strict_clean: bool = True              # worktree kirli ise işlem reddedilir
    provider: str = "github"               # "github" | "gitea" | "none"
    github_token: str = ""
    github_repo: str = ""                  # "owner/repo"
    github_reviewers: tuple[str, ...] = ()
    gitea_base_url: str = ""
    gitea_token: str = ""
    gitea_repo: str = ""                   # "owner/repo"

    @classmethod
    def from_env(cls, repo_path: Optional[Path] = None) -> "GitConfig":
        env = os.environ.get
        reviewers = [
            r.strip() for r in (env("DSL_GIT_REVIEWERS", "") or "").split(",") if r.strip()
        ]
        return cls(
            enabled=_bool(env("DSL_GIT_ENABLED", "false")),
            mode=(env("DSL_GIT_MODE", "direct_commit") or "direct_commit").lower(),
            repo_path=Path(repo_path or env("DSL_GIT_REPO_PATH") or _infer_repo_root()),
            remote=env("DSL_GIT_REMOTE", "origin") or "origin",
            base_branch=env("DSL_GIT_BASE_BRANCH", "main") or "main",
            branch_prefix=env("DSL_GIT_BRANCH_PREFIX", "dsl/edit-") or "dsl/edit-",
            author_name=env("DSL_GIT_AUTHOR_NAME", "DSL Bot") or "DSL Bot",
            author_email=env("DSL_GIT_AUTHOR_EMAIL", "[email protected]")
            or "[email protected]",
            push=_bool(env("DSL_GIT_DIRECT_PUSH", "false")),
            strict_clean=_bool(env("DSL_GIT_STRICT_CLEAN", "true")),
            provider=(env("DSL_GIT_PROVIDER", "github") or "github").lower(),
            github_token=env("GITHUB_TOKEN", "") or "",
            github_repo=env("DSL_GIT_GITHUB_REPO", "") or "",
            github_reviewers=tuple(reviewers),
            gitea_base_url=env("GITEA_BASE_URL", "") or "",
            gitea_token=env("GITEA_TOKEN", "") or "",
            gitea_repo=env("DSL_GIT_GITEA_REPO", "") or "",
        )


def _bool(val: str | None) -> bool:
    return (val or "").strip().lower() in {"1", "true", "yes", "on"}


def _infer_repo_root() -> str:
    """Backend'in çalıştığı dizinden yukarı çıkarak repo root'unu bul."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".git").exists():
            return str(parent)
    return str(Path.cwd())


# ── Subprocess yardımcıları ─────────────────────────────────────────────────


def _run(
    cfg: GitConfig,
    args: Sequence[str],
    *,
    check: bool = True,
    env_extra: Optional[dict[str, str]] = None,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    """git subprocess runner — stdout/stderr text döner, hata varsa raise."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    cmd = ["git", *args]
    logger.debug("git: %s (cwd=%s)", shlex.join(cmd), cfg.repo_path)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cfg.repo_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitClientError("git CLI bulunamadı (PATH'e ekleyin)") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitClientError(f"git timeout: {shlex.join(cmd)}") from exc

    if check and proc.returncode != 0:
        raise GitClientError(
            f"git {args[0]} başarısız (exit={proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '').strip()[:400]}"
        )
    return proc


def _commit_env(cfg: GitConfig) -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": cfg.author_name,
        "GIT_AUTHOR_EMAIL": cfg.author_email,
        "GIT_COMMITTER_NAME": cfg.author_name,
        "GIT_COMMITTER_EMAIL": cfg.author_email,
    }


# ── Sorgular ───────────────────────────────────────────────────────────────


def head_sha(cfg: GitConfig) -> str:
    proc = _run(cfg, ["rev-parse", "HEAD"])
    return proc.stdout.strip()


def current_branch(cfg: GitConfig) -> str:
    proc = _run(cfg, ["rev-parse", "--abbrev-ref", "HEAD"])
    return proc.stdout.strip()


def is_clean_for(cfg: GitConfig, paths: Iterable[Path]) -> bool:
    """İstenen dosyalarda lokal (staged+unstaged) değişiklik olmasın.

    Diğer dosyalar kirli olsa bile bu operasyonun kendi dosyalarıyla çakışma
    olmadığı sürece geçilir.
    """
    rel = [str(p.resolve().relative_to(cfg.repo_path.resolve())) for p in paths]
    if not rel:
        return True
    proc = _run(cfg, ["status", "--porcelain=v1", "--", *rel])
    return proc.stdout.strip() == ""


def ensure_clean_or_raise(cfg: GitConfig, paths: Iterable[Path]) -> None:
    if not cfg.strict_clean:
        return
    if not is_clean_for(cfg, paths):
        raise GitClientError(
            "DSL YAML dosyalarında zaten commit edilmemiş değişiklik var. "
            "Önce temizleyin ya da DSL_GIT_STRICT_CLEAN=false yapın."
        )


# ── Commit / Branch / Push / PR ────────────────────────────────────────────


@dataclass(frozen=True)
class CommitResult:
    sha: str
    branch: str
    pushed: bool
    pr_url: Optional[str] = None


def _branch_name(cfg: GitConfig, slug: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", slug.strip("-")).strip("-")[:64] or "edit"
    return f"{cfg.branch_prefix}{safe}"


def stage_paths(cfg: GitConfig, paths: Iterable[Path]) -> list[str]:
    """Verilen yolları stage'le. Repo-relative yol listesi döner."""
    rel: list[str] = []
    for p in paths:
        try:
            rel.append(str(p.resolve().relative_to(cfg.repo_path.resolve())))
        except ValueError as exc:
            raise GitClientError(
                f"Yol repo dışında: {p} (repo={cfg.repo_path})"
            ) from exc
    if not rel:
        return []
    _run(cfg, ["add", "--", *rel])
    return rel


def has_staged_changes(cfg: GitConfig) -> bool:
    proc = _run(cfg, ["diff", "--cached", "--name-only"])
    return bool(proc.stdout.strip())


def commit(cfg: GitConfig, message: str) -> str:
    """Staged değişiklikleri commit'le — SHA döner."""
    _run(cfg, ["commit", "-m", message], env_extra=_commit_env(cfg))
    return head_sha(cfg)


def push_branch(cfg: GitConfig, branch: str) -> None:
    """Branch'i remote'a push'la (upstream ayarlı değilse `-u`)."""
    _run(cfg, ["push", "--set-upstream", cfg.remote, branch], timeout=60.0)


def create_branch_from_base(cfg: GitConfig, branch: str) -> None:
    """Yeni branch'i base'den ayır. Başlangıç state'i base ile aynı olur."""
    _run(cfg, ["fetch", cfg.remote, cfg.base_branch], check=False, timeout=60.0)
    # Zaten varsa çakışmasın
    existing = _run(cfg, ["branch", "--list", branch], check=False)
    if existing.stdout.strip():
        _run(cfg, ["checkout", branch])
    else:
        _run(cfg, ["checkout", "-b", branch, f"{cfg.remote}/{cfg.base_branch}"], check=False)
        # fetch yapılamadıysa local base'den ayır
        if current_branch(cfg) != branch:
            _run(cfg, ["checkout", "-b", branch, cfg.base_branch])


def checkout_branch(cfg: GitConfig, branch: str) -> None:
    _run(cfg, ["checkout", branch])


# ── Yüksek seviye operasyon ────────────────────────────────────────────────


def commit_dsl_change(
    cfg: GitConfig,
    *,
    paths: Iterable[Path],
    message: str,
    proposal_id: str,
    slug: str,
    mode: Optional[str] = None,
) -> CommitResult:
    """DSL değişikliği için commit (+ opsiyonel PR) akışı.

    Çağrı öncesi YAML dosyaları diske yazılmış olmalı. Bu fonksiyon:
      1. (strict mode) staged/unstaged değişiklik kontrolü
      2. Hedef dosyaları stage'e al
      3. direct_commit modunda mevcut branch'e commit at; `push=true` ise push
         pr modunda yeni branch aç → commit → push → PR oluştur
    """
    paths_list = list(paths)
    if not paths_list:
        raise GitClientError("commit edilecek dosya yok")

    if not cfg.enabled:
        # git devre dışı — YAML zaten yazıldı, commit atlanır
        logger.info("DSL_GIT_ENABLED=false — git commit atlandı (%s)", proposal_id)
        return CommitResult(sha="", branch=current_branch(cfg), pushed=False)

    effective_mode = (mode or cfg.mode).lower()
    if effective_mode not in {"direct_commit", "pr"}:
        raise GitClientError(f"geçersiz DSL_GIT_MODE: {effective_mode}")

    # (1) Temizlik kontrolü yalnızca hedef dosyalar için
    ensure_clean_or_raise(cfg, paths_list)

    starting_branch = current_branch(cfg)

    try:
        if effective_mode == "pr":
            branch = _branch_name(cfg, slug)
            create_branch_from_base(cfg, branch)
        else:
            branch = starting_branch

        # (2) Stage
        rel = stage_paths(cfg, paths_list)
        if not rel or not has_staged_changes(cfg):
            logger.info("DSL commit no-op — staged diff yok (%s)", proposal_id)
            return CommitResult(
                sha=head_sha(cfg), branch=branch, pushed=False
            )

        # (3) Commit
        sha = commit(cfg, message)

        pushed = False
        pr_url: Optional[str] = None
        if effective_mode == "pr":
            push_branch(cfg, branch)
            pushed = True
            pr_url = _open_pull_request(
                cfg,
                branch=branch,
                title=message.splitlines()[0][:100],
                body=message,
            )
        else:
            if cfg.push:
                try:
                    _run(cfg, ["push", cfg.remote, branch], timeout=60.0)
                    pushed = True
                except GitClientError as exc:
                    logger.warning(
                        "DSL commit atıldı ama push başarısız: %s", exc
                    )

        return CommitResult(sha=sha, branch=branch, pushed=pushed, pr_url=pr_url)

    finally:
        # PR modunda base branch'e dön; kullanıcı deneyimi için
        if effective_mode == "pr" and current_branch(cfg) != starting_branch:
            try:
                _run(cfg, ["checkout", starting_branch], check=False)
            except GitClientError:
                pass


# ── Pull Request Açma ──────────────────────────────────────────────────────


def _open_pull_request(
    cfg: GitConfig,
    *,
    branch: str,
    title: str,
    body: str,
) -> Optional[str]:
    """Provider'a göre PR aç. Başarısızsa None döner (commit zaten atıldı)."""
    if cfg.provider == "github":
        return _open_github_pr(cfg, branch=branch, title=title, body=body)
    if cfg.provider == "gitea":
        return _open_gitea_pr(cfg, branch=branch, title=title, body=body)
    return None


def _open_github_pr(
    cfg: GitConfig,
    *,
    branch: str,
    title: str,
    body: str,
) -> Optional[str]:
    if not cfg.github_token or not cfg.github_repo:
        logger.warning("GitHub token veya repo tanımlı değil — PR atlanıyor")
        return None
    url = f"https://api.github.com/repos/{cfg.github_repo}/pulls"
    payload = {
        "title": title,
        "head": branch,
        "base": cfg.base_branch,
        "body": body,
        "draft": False,
    }
    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {cfg.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        pr = resp.json()
        pr_url = pr.get("html_url")
        # Reviewer ekle (hata olsa bile PR açık kalır)
        if cfg.github_reviewers and pr.get("number"):
            try:
                httpx.post(
                    f"{url}/{pr['number']}/requested_reviewers",
                    json={"reviewers": list(cfg.github_reviewers)},
                    headers={
                        "Authorization": f"Bearer {cfg.github_token}",
                        "Accept": "application/vnd.github+json",
                    },
                    timeout=15.0,
                )
            except httpx.HTTPError as exc:
                logger.warning("Reviewer eklenemedi: %s", exc)
        return pr_url
    except httpx.HTTPStatusError as exc:
        logger.error(
            "GitHub PR HTTP %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return None
    except httpx.RequestError as exc:
        logger.error("GitHub PR bağlantı hatası: %s", exc)
        return None


def _open_gitea_pr(
    cfg: GitConfig,
    *,
    branch: str,
    title: str,
    body: str,
) -> Optional[str]:
    if not cfg.gitea_base_url or not cfg.gitea_token or not cfg.gitea_repo:
        logger.warning("Gitea config eksik — PR atlanıyor")
        return None
    base = cfg.gitea_base_url.rstrip("/")
    url = f"{base}/api/v1/repos/{cfg.gitea_repo}/pulls"
    try:
        resp = httpx.post(
            url,
            json={
                "title": title,
                "head": branch,
                "base": cfg.base_branch,
                "body": body,
            },
            headers={
                "Authorization": f"token {cfg.gitea_token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        pr = resp.json()
        return pr.get("html_url") or pr.get("url")
    except httpx.HTTPError as exc:
        logger.error("Gitea PR hatası: %s", exc)
        return None
