"""Nexus Repo Pydantic şemaları (request / response)."""

from __future__ import annotations

import ipaddress
import socket
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


def _validate_repo_url(value: str) -> str:
    """Klonlanacak repo_url'i güvenlik açısından doğrula.

    git clone, ``ext::``, ``file://``, ``git://`` gibi transport helper'ları
    çalıştırabildiğinden RCE/SSRF riskini engellemek için yalnızca
    https / ssh şemalarına ve özel olmayan (public) host'lara izin verilir.
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("repo_url boş olamaz")

    # git transport helper / option injection engelle
    if raw.startswith("-") or "::" in raw:
        raise ValueError("Geçersiz repo_url biçimi")

    lowered = raw.lower()
    if lowered.startswith(("file:", "git:", "ext:", "ftp:", "ftps:")):
        raise ValueError("Bu şema desteklenmiyor: yalnızca https ve ssh kabul edilir")

    # scp benzeri SSH biçimi: git@host:org/repo
    scp_like = "://" not in raw and "@" in raw and ":" in raw.split("@", 1)[1]

    if scp_like:
        host = raw.split("@", 1)[1].split(":", 1)[0]
    else:
        parsed = urlparse(raw)
        scheme = parsed.scheme.lower()
        if scheme not in ("https", "ssh"):
            raise ValueError("Yalnızca https ve ssh şemaları desteklenir")
        host = parsed.hostname or ""

    if not host:
        raise ValueError("repo_url host bilgisi içermiyor")

    # Host'u çöz ve özel/loopback/link-local aralıklarını engelle (SSRF)
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise ValueError(f"repo_url host'u çözümlenemedi: {host}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("repo_url özel/dahili bir adrese işaret ediyor")

    return raw

# ── NexusProject ──────────────────────────────────────────────────────────────

class NexusProjectCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    repo_url: str = Field(..., max_length=1000)
    repo_type: str = Field("git", pattern="^(git|svn|bitbucket|github)$")
    branch: str = Field("main", max_length=200)
    credential_ref: Optional[str] = None
    llm_provider: str = Field("ollama", pattern="^(ollama|openai|anthropic)$")
    llm_model: str = Field("qwen2.5:32b", max_length=100)

    @field_validator("repo_url")
    @classmethod
    def _check_repo_url(cls, v: str) -> str:
        return _validate_repo_url(v)


class NexusProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    branch: Optional[str] = Field(None, max_length=200)
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    archived: Optional[bool] = None


class NexusProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    repo_url: str
    repo_type: str
    branch: str
    llm_provider: str
    llm_model: str
    archived: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── NexusCrawlJob ─────────────────────────────────────────────────────────────

class NexusCrawlJobOut(BaseModel):
    id: str
    project_id: str
    status: str
    commit_sha: Optional[str]
    files_scanned: int
    endpoints_found: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── NexusScenario ─────────────────────────────────────────────────────────────

class NexusScenarioCreate(BaseModel):
    title: str = Field(..., max_length=500)
    type: str = Field(..., pattern="^(manual|service|automation)$")
    feature_area: Optional[str] = Field(None, max_length=200)
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    gherkin: Optional[str] = None
    notes: Optional[str] = None


class NexusScenarioUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    type: Optional[str] = None
    feature_area: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    gherkin: Optional[str] = None
    notes: Optional[str] = None


class NexusScenarioOut(BaseModel):
    id: str
    project_id: str
    title: str
    type: str
    feature_area: Optional[str]
    priority: str
    status: str
    gherkin: Optional[str]
    notes: Optional[str]
    llm_model: Optional[str]
    llm_prompt_tokens: int
    llm_completion_tokens: int
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── NexusCase ─────────────────────────────────────────────────────────────────

class NexusCaseOut(BaseModel):
    id: str
    scenario_id: str
    name: str
    preconditions: Optional[str]
    steps: Optional[list]
    expected_result: Optional[str]
    test_data: Optional[dict]
    order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── NexusExport ───────────────────────────────────────────────────────────────

class NexusExportCreate(BaseModel):
    format: str = Field(..., pattern="^(gherkin|postman|excel|jira)$")
    scenario_ids: Optional[list[str]] = None  # None = tüm senaryolar
    # Jira için opsiyonel alan — hangi proje/component'e aktarılacağı
    jira_project_key: Optional[str] = None


class NexusExportOut(BaseModel):
    id: str
    project_id: str
    format: str
    file_path: Optional[str]
    scenario_ids: Optional[list]
    status: str
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Genel yanıt sarmalayıcılar ────────────────────────────────────────────────

class NexusEndpointOut(BaseModel):
    id: str
    crawl_job_id: str
    method: str
    path: str
    source_file: Optional[str]
    source_line: Optional[int]
    auth_required: bool
    tags: Optional[list]
    created_at: datetime

    model_config = {"from_attributes": True}


class NexusFileOut(BaseModel):
    id: str
    crawl_job_id: str
    path: str
    language: Optional[str]
    size_bytes: int
    tokens_estimate: int
    summary: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class NexusStatsOut(BaseModel):
    total_scenarios: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    by_priority: dict[str, int]
    total_crawl_jobs: int
    last_crawl_at: Optional[datetime]
    total_endpoints: int
    total_files: int


class NexusHealthOut(BaseModel):
    status: str = "ok"
    feature_enabled: bool
    version: str = "0.1.0"


class NexusGenerateRequest(BaseModel):
    crawl_job_id: str
    scenario_types: list[str] = Field(default=["manual", "service", "automation"])
    max_scenarios: int = Field(default=20, ge=1, le=100)
    language: str = Field(default="tr", pattern="^(tr|en)$")
