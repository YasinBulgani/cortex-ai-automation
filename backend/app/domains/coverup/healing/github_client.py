"""Minimal GitHub istemcisi — self-healing PR akışı için.

Neden kendi inceliğimiz:
    * PyGithub güçlü ama ağır (100+ sınıf, cache mantığı, vb.). Bizim
      ihtiyacımız sadece 4 endpoint: branch oluştur, blob/tree/commit zinciri
      veya contents update, PR aç, PR yorum ekle.
    * Hafif istemci test edilmesi ve mock'lanması kolay. App'e geçişte
      ``auth`` ve ``session`` soyutlaması değişir, geri kalan aynı kalır.

Auth soyutlaması:
    ``TokenAuth`` (PAT) şu an tek implementasyon. GitHub App geldiğinde
    ``AppAuth`` aynı arayüzle dropped-in olacak (get_auth_header()).

Hata modeli:
    * Network/HTTP hatası → ``GitHubError`` raise. Caller yakalar ve
      HealingRun.status='pr_failed' ile kayıt eder.
    * 404/422 gibi beklenebilir durumlar da ``GitHubError`` ama
      ``status_code`` alanı ile ayırt edilebilir.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubError(RuntimeError):
    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@runtime_checkable
class GitHubAuth(Protocol):
    def get_auth_header(self) -> str:  # pragma: no cover - protocol
        ...


@dataclass
class TokenAuth:
    """PAT — ``github_*`` token + ``ghp_*`` token ikisi de OK."""

    token: str

    def get_auth_header(self) -> str:
        if not self.token or not self.token.strip():
            raise GitHubError("Boş GitHub token")
        return f"Bearer {self.token.strip()}"


# ── Data types ───────────────────────────────────────────────────────────


@dataclass
class PullRequestResult:
    number: int
    html_url: str
    head_ref: str
    draft: bool


# ── HTTP transport adapter ───────────────────────────────────────────────


@runtime_checkable
class HttpTransport(Protocol):
    """HTTP backend abstraction — test'te fake, prod'da httpx.

    Yalnız ``request(method, url, headers, json)`` metodunu expose eder.
    Response tipi ``HttpResponse``; status_code, json() ve raw text sağlar.
    """

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict,
        json: Optional[dict] = None,
    ) -> "HttpResponse":  # pragma: no cover - protocol
        ...


@dataclass
class HttpResponse:
    status_code: int
    body: dict = field(default_factory=dict)
    text: str = ""


class _HttpxTransport:
    """httpx-backed transport. Httpx opsiyonel; yoksa raise."""

    def __init__(self, *, timeout: float = 15.0) -> None:
        try:
            import httpx  # type: ignore
        except ImportError as exc:
            raise GitHubError(
                "httpx kurulu değil — GitHub client için zorunlu"
            ) from exc
        self._httpx = httpx
        self._timeout = timeout

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict,
        json: Optional[dict] = None,
    ) -> HttpResponse:
        try:
            resp = self._httpx.request(
                method, url, headers=headers, json=json, timeout=self._timeout
            )
        except Exception as exc:
            raise GitHubError(f"HTTP hata: {exc}") from exc
        body: dict = {}
        try:
            body = resp.json() if resp.content else {}
        except ValueError:
            body = {}
        return HttpResponse(status_code=resp.status_code, body=body, text=resp.text)


# ── Client ───────────────────────────────────────────────────────────────


@dataclass
class GitHubClient:
    """Basit, test-edilebilir GitHub istemcisi.

    ``transport`` enjekte edilebilir — testte fake ile mock'lanır.
    """

    auth: GitHubAuth
    owner: str
    repo: str
    transport: Optional[HttpTransport] = None

    def __post_init__(self) -> None:
        if self.transport is None:
            self.transport = _HttpxTransport()

    # ── Headers ───────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": self.auth.get_auth_header(),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TestwrightAI-SelfHealing/1.0",
        }

    def _url(self, path: str) -> str:
        base = f"{GITHUB_API}/repos/{self.owner}/{self.repo}"
        if path.startswith("/"):
            return f"{base}{path}"
        return f"{base}/{path}"

    def _req(
        self, method: str, path: str, *, json: Optional[dict] = None
    ) -> HttpResponse:
        assert self.transport is not None
        resp = self.transport.request(method, self._url(path), headers=self._headers(), json=json)
        if resp.status_code >= 400:
            msg = (resp.body.get("message") or resp.text or "unknown")[:500]
            raise GitHubError(
                f"GitHub {method} {path} → {resp.status_code}: {msg}",
                status_code=resp.status_code,
            )
        return resp

    # ── Public: high-level ────────────────────────────────────────────────

    def get_default_branch_sha(self, branch: str = "main") -> str:
        resp = self._req("GET", f"/git/refs/heads/{branch}")
        return str(resp.body.get("object", {}).get("sha", "")) or ""

    def create_branch(self, new_branch: str, from_sha: str) -> None:
        """Yeni ref oluştur. Varsa ``status_code=422`` hatası ile fail eder."""
        self._req(
            "POST",
            "/git/refs",
            json={"ref": f"refs/heads/{new_branch}", "sha": from_sha},
        )

    def put_file(
        self,
        *,
        branch: str,
        path: str,
        content_text: str,
        commit_message: str,
    ) -> None:
        """Var olan bir dosyayı içerikle değiştir. File yoksa 404.

        GitHub /contents API'si tek commit'te tek dosya ile sınırlı — self-heal
        senaryomuzda tek dosya yeterli (patch_applier tek dosyayı değiştirir).
        """
        # Önce mevcut SHA'yı al (contents update için gerekli)
        resp = self._req("GET", f"/contents/{path}?ref={branch}")
        file_sha = resp.body.get("sha")
        if not file_sha:
            raise GitHubError(f"Dosya SHA bulunamadı: {path}@{branch}")

        encoded = base64.b64encode(content_text.encode("utf-8")).decode("ascii")
        self._req(
            "PUT",
            f"/contents/{path}",
            json={
                "message": commit_message,
                "content": encoded,
                "sha": file_sha,
                "branch": branch,
            },
        )

    def open_pull_request(
        self,
        *,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
        draft: bool = False,
    ) -> PullRequestResult:
        resp = self._req(
            "POST",
            "/pulls",
            json={
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "draft": draft,
            },
        )
        number = int(resp.body.get("number") or 0)
        url = str(resp.body.get("html_url") or "")
        return PullRequestResult(number=number, html_url=url, head_ref=head, draft=draft)
