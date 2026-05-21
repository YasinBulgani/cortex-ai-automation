"""
API Testing SQLAlchemy Models
=============================

6 yeni tablo — mevcut tspm_api_* tablolariyla uyumlu.
Prefix: sd_apitest_ (syndata api testing)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.models import Base

_uuid = lambda: str(uuid4())  # noqa: E731
utcnow = lambda: datetime.now(timezone.utc)  # noqa: E731


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. API ENVIRONMENT — Ortam degisken yonetimi
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ApiEnvironment(Base):
    """
    API test ortam degiskenleri — her projenin dev/staging/prod ortamlari.

    variables JSONB ornegi:
    {
      "base_url": "https://api.bank.com/v1",
      "auth_token": "eyJ...",
      "api_key": "sk-...",
      "timeout": "30"
    }
    """
    __tablename__ = "sd_apitest_environments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tspm_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variables: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Hassas degiskenler maskelenir (şifre, token, api_key)
    sensitive_keys: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("idx_apienv_project", "project_id"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. API SPEC — OpenAPI/Swagger spec depolama
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ApiSpec(Base):
    """
    OpenAPI/Swagger spec dosyasi.

    Spec import edildikten sonra prance ile resolve edilir,
    endpoint'ler otomatik cikarilir.
    """
    __tablename__ = "sd_apitest_specs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tspm_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    spec_format: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )  # openapi_3.0, openapi_3.1, swagger_2.0
    spec_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Resolved (dereferenced) spec — $ref'ler cozulmus hali
    resolved_content: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Istatistikler
    endpoint_count: Mapped[int] = mapped_column(Integer, default=0)
    schema_count: Mapped[int] = mapped_column(Integer, default=0)

    # AI analiz sonuclari
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {risk_summary, pii_endpoints[], financial_endpoints[], auth_schemes[], compliance_notes[]}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    endpoints: Mapped[list["ApiEndpoint"]] = relationship(
        back_populates="spec", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_apispec_project", "project_id"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. API ENDPOINT — Spec'ten cikarilan endpoint envanteri
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ApiEndpoint(Base):
    """
    OpenAPI spec'ten cikarilan tek bir endpoint.

    Risk seviyeleri (AI tarafindan):
      critical — Finansal islem, para transferi, odeme
      high     — Kimlik dogrulama, yetkilendirme, PII erisimu
      medium   — Standart CRUD islemleri
      low      — Sadece okuma, public endpoint'ler
    """
    __tablename__ = "sd_apitest_endpoints"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    spec_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_apitest_specs.id", ondelete="CASCADE"),
        nullable=False,
    )
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    operation_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)

    # Parametre detaylari
    parameters: Mapped[list] = mapped_column(JSONB, default=list)
    # [{name, in, required, schema, description}]
    request_body_schema: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    response_schemas: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"200": {schema}, "400": {schema}, ...}

    # Guvenlik
    security_requirements: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    auth_required: Mapped[bool] = mapped_column(Boolean, default=True)

    # AI-driven risk assessment
    risk_level: Mapped[str] = mapped_column(String(32), default="medium")
    has_pii: Mapped[bool] = mapped_column(Boolean, default=False)
    has_financial: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_tags: Mapped[list] = mapped_column(JSONB, default=list)
    # ["BDDK", "KVKK", "PCI-DSS", "MASAK"]

    # Bagimlilklar (endpoint'ler arasi)
    depends_on: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"endpoint_id": "...", "provides": "auth_token", "json_path": "$.token"}]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    spec: Mapped["ApiSpec"] = relationship(back_populates="endpoints")
    test_cases: Mapped[list["ApiTestCase"]] = relationship(
        back_populates="endpoint", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_apiendpoint_spec", "spec_id"),
        Index("idx_apiendpoint_method_path", "method", "path"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. API TEST CASE — AI uretilmis test senaryolari
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ApiTestCase(Base):
    """
    AI tarafindan uretilen veya kullanıcı tarafindan olusturulan
    tek bir API test case'i.

    test_type degerleri:
      positive    — Gecerli parametrelerle başarılı cagri
      negative    — Geçersiz/eksik parametre, yetkisiz erisim
      boundary    — Min/max sinir degerleri, overflow
      security    — OWASP API Top 10, injection, auth bypass
      compliance  — BDDK/KVKK/PCI-DSS uyumluluk
      performance — Response time, throughput, concurrent
      edge_case   — Race condition, idempotency, encoding
      regression  — Onceki hatalardan ogrenilenler
      contract    — Schema uygunluk dogrulamasi
    """
    __tablename__ = "sd_apitest_cases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tspm_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_apitest_endpoints.id", ondelete="SET NULL"),
        nullable=True,
    )
    collection_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tspm_api_collections.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Test metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    # P0=kritik, P1=yuksek, P2=orta, P3=dusuk

    # Guvenlik & Uyumluluk etiketleri
    owasp_category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    # API1..API10
    regulation: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # BDDK, KVKK, PCI-DSS, MASAK
    cwe_id: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    # Common Weakness Enumeration

    # Request detayi
    request_method: Mapped[str] = mapped_column(String(16), nullable=False)
    request_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    request_headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    request_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    request_body: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Pre-request setup
    pre_request_vars: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"auth_token": {"from": "login_response", "path": "$.access_token"}}
    setup_chain: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Oncul istekler listesi

    # Assertions
    assertions: Mapped[list] = mapped_column(JSONB, default=list)
    # [{type, path, operator, expected, message}]
    # type: status_code, json_path, header, response_time, schema, regex, exists, not_exists
    # operator: equals, not_equals, contains, not_contains, gt, lt, gte, lte, matches, one_of

    # AI metadata
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Review workflow
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending, approved, rejected, edited
    reviewer_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Son çalışma durumu (denormalized for quick access)
    last_run_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # passed, failed, error, skipped
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    pass_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)

    # Flaky test quarantine
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quarantine_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    endpoint: Mapped[Optional["ApiEndpoint"]] = relationship(back_populates="test_cases")

    __table_args__ = (
        Index("idx_apitc_project", "project_id"),
        Index("idx_apitc_endpoint", "endpoint_id"),
        Index("idx_apitc_type", "test_type"),
        Index("idx_apitc_review", "review_status"),
        Index("idx_apitc_quarantined", "quarantined"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. API CHAIN — Zincirlenmis istek akislari
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ApiChain(Base):
    """
    Zincirlenmis API istek akisi — React Flow uyumlu.

    Ornek: Login → Account List → Transfer → Verify Balance
    Her adım arasinda veri eslestirmesi (JSON Path) tanimlanir.

    nodes ornegi:
    [
      {"id": "n1", "type": "request", "position": {"x": 0, "y": 0},
       "data": {"test_case_id": "...", "label": "Login"}},
      {"id": "n2", "type": "request", "position": {"x": 300, "y": 0},
       "data": {"test_case_id": "...", "label": "Transfer"}}
    ]

    edges ornegi:
    [
      {"id": "e1", "source": "n1", "target": "n2",
       "data": {"mappings": [
         {"from_path": "$.access_token", "to_var": "auth_token"},
         {"from_path": "$.user.id", "to_var": "user_id"}
       ]}}
    ]
    """
    __tablename__ = "sd_apitest_chains"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tspm_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # React Flow uyumlu node/edge yapisi
    nodes: Mapped[list] = mapped_column(JSONB, default=list)
    edges: Mapped[list] = mapped_column(JSONB, default=list)

    # Variable extractions (tüm chain boyunca)
    global_variables: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"base_url": "{{env.base_url}}", "timeout": "30"}

    # AI metadata
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Chain execution config
    stop_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=0)
    delay_between_ms: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("idx_apichain_project", "project_id"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. API EXECUTION DETAIL — Istek bazinda çalışma detayi
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ApiExecutionDetail(Base):
    """
    Tek bir API istek calismasinin tam detayi.

    Her çalışma (run) birden fazla execution detail icerir.
    Timing breakdown: DNS → TCP → TLS → TTFB → Download
    """
    __tablename__ = "sd_apitest_execution_details"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tspm_api_test_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    test_case_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_apitest_cases.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Actual request (degiskenler cozulmus hali)
    actual_method: Mapped[str] = mapped_column(String(16), nullable=False)
    actual_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    actual_headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    actual_body: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Response
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timing breakdown (milliseconds)
    dns_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tcp_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tls_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ttfb_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    download_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Assertion sonuclari
    assertion_results: Mapped[list] = mapped_column(JSONB, default=list)
    # [{index, type, passed, expected, actual, message}]
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Contract validation
    schema_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    schema_errors: Mapped[list] = mapped_column(JSONB, default=list)

    # Response diff (regression detection)
    diff_from_previous: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # deepdiff sonucu — onceki başarılı calismayla karsilastirma

    # Extracted variables (chain için)
    extracted_variables: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"auth_token": "eyJ...", "user_id": "abc-123"}

    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    execution_order: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_apiexec_run", "run_id"),
        Index("idx_apiexec_testcase", "test_case_id"),
        Index("idx_apiexec_status", "passed"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. HEALING LOG — Self-healing CI retry kayitlari
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class HealingLog(Base):
    """
    Self-healing CI retry kaydi.

    Her başarısız test için siniflandirma, strateji ve
    retry sonuclarini saklar.
    """
    __tablename__ = "api_healing_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    test_case_id: Mapped[str] = mapped_column(String(36), index=True)
    failure_category: Mapped[str] = mapped_column(String(50))
    strategy: Mapped[str] = mapped_column(String(50))
    retries_attempted: Mapped[int] = mapped_column(Integer, default=0)
    healed: Mapped[bool] = mapped_column(Boolean, default=False)
    final_status: Mapped[str] = mapped_column(String(20))
    healing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
