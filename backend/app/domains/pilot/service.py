"""Pilot orchestrator core.

Akış:
  1. Kullanıcı mesajı → intent detection (rule-based, LLM-ready)
  2. Required input'lar çıkar — eksik varsa ClarificationQuestion döner
  3. Tüm input toplanınca → StagePlan (Analyze → Design → Data → Execute → Observe → Iterate)
  4. Her stage execute_next_stage() ile tetiklenir, sonuç session'a yazılır
  5. Session timeline UI'a stream'lenir

In-memory store. Production'da DB tablosu + Redis pubsub.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

try:
    from app.core.event_bus import bus as _event_bus, DomainEvent as _DomainEvent, EventName as _EventName
except Exception:  # pragma: no cover
    _event_bus = None
    _DomainEvent = None  # type: ignore
    _EventName = None  # type: ignore

# ── Veri modelleri ─────────────────────────────────────────────────────────

IntentKind = Literal[
    "create_scenarios_from_requirements",
    "explore_url_and_generate_tests",
    "run_test_suite",
    "analyze_failures",
    "generate_test_data",
    "unknown",
]

StageId = Literal["analyze", "design", "data", "execute", "observe", "iterate"]
StageStatus = Literal["pending", "in_progress", "awaiting_input", "complete", "failed", "skipped"]
TurnRole = Literal["user", "pilot", "system"]


@dataclass
class ClarificationQuestion:
    """Sıfır-bilgi kullanıcıya sorulan yapılandırılmış soru."""
    id: str
    field_name: str
    prompt: str
    kind: Literal["text", "choice", "multichoice", "url", "number"]
    options: List[str] = field(default_factory=list)
    required: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StagePlan:
    """Pipeline stage planı + canlı durum."""
    id: StageId
    title: str
    status: StageStatus = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output_summary: Optional[str] = None
    artifacts: List[dict] = field(default_factory=list)
    explainability: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PilotTurn:
    """Sohbet timeline'ındaki bir adım."""
    id: str
    role: TurnRole
    text: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    clarification: Optional[ClarificationQuestion] = None
    stage_update: Optional[dict] = None

    def to_dict(self) -> dict:
        out = asdict(self)
        if self.clarification:
            out["clarification"] = self.clarification.to_dict()
        return out


@dataclass
class PilotSession:
    id: str
    project_id: str
    user_id: str
    intent: IntentKind = "unknown"
    inputs: Dict[str, Any] = field(default_factory=dict)
    pending_clarification: Optional[ClarificationQuestion] = None
    stages: List[StagePlan] = field(default_factory=list)
    turns: List[PilotTurn] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "intent": self.intent,
            "inputs": dict(self.inputs),
            "pending_clarification": self.pending_clarification.to_dict() if self.pending_clarification else None,
            "stages": [s.to_dict() for s in self.stages],
            "turns": [t.to_dict() for t in self.turns],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── Store ──────────────────────────────────────────────────────────────────

_SESSIONS: Dict[str, PilotSession] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_urlsafe(8)}"


# ── Intent detection (rule-based; LLM-ready) ───────────────────────────────

_INTENT_PATTERNS: List[tuple[IntentKind, List[str]]] = [
    ("create_scenarios_from_requirements",
     [r"gereksinim", r"prd", r"acceptance", r"senaryo üret", r"test oluştur",
      r"\bdok[ü|u]man", r"jira", r"confluence"]),
    ("explore_url_and_generate_tests",
     [r"https?://", r"url'?", r"siteyi", r"keşfet", r"tara"]),
    ("run_test_suite",
     [r"koş", r"çalıştır", r"run", r"execute", r"test et"]),
    ("analyze_failures",
     [r"neden düştü", r"hata", r"başarısız", r"failure", r"debug", r"kök neden"]),
    ("generate_test_data",
     [r"test verisi", r"data set", r"faker", r"sentetik veri"]),
]


def detect_intent(text: str) -> IntentKind:
    t = text.lower()
    for intent, patterns in _INTENT_PATTERNS:
        for p in patterns:
            if re.search(p, t):
                return intent
    return "unknown"


# ── Required inputs per intent ─────────────────────────────────────────────

_REQUIRED_INPUTS: Dict[IntentKind, List[ClarificationQuestion]] = {
    "create_scenarios_from_requirements": [
        ClarificationQuestion(
            id="q-source", field_name="source",
            prompt="Gereksinim kaynağı nedir?",
            kind="choice",
            options=["Jira issue", "Confluence sayfası", "PDF/DOCX yükleme", "Doğrudan metin yapıştır"],
        ),
        ClarificationQuestion(
            id="q-source-ref", field_name="source_ref",
            prompt="Kaynağın referansı/içeriği nedir? (URL, dosya adı veya metin)",
            kind="text",
        ),
        ClarificationQuestion(
            id="q-coverage", field_name="coverage_level",
            prompt="Test kapsamı?",
            kind="choice",
            options=["Smoke (kritik akışlar)", "Regression (tam kapsam)", "Edge cases (sınır + negatif)"],
        ),
    ],
    "explore_url_and_generate_tests": [
        ClarificationQuestion(
            id="q-url", field_name="target_url",
            prompt="Hangi URL'i tarayalım?",
            kind="url",
        ),
        ClarificationQuestion(
            id="q-auth", field_name="needs_auth",
            prompt="Giriş yapması gereken bir sayfa mı?",
            kind="choice",
            options=["Hayır, açık", "Evet, test kullanıcısı sağlayacağım"],
        ),
        ClarificationQuestion(
            id="q-browser", field_name="browser",
            prompt="Hangi tarayıcılarda?",
            kind="multichoice",
            options=["Chromium", "Firefox", "WebKit", "Mobile (iOS)", "Mobile (Android)"],
        ),
    ],
    "run_test_suite": [
        ClarificationQuestion(
            id="q-scope", field_name="scope",
            prompt="Hangi setleri koşalım?",
            kind="choice",
            options=["Tüm senaryolar", "Smoke seti", "Regression seti", "Sadece son değiştirilenler"],
        ),
        ClarificationQuestion(
            id="q-env", field_name="environment",
            prompt="Hangi ortam?",
            kind="choice",
            options=["dev", "staging", "production"],
        ),
    ],
    "analyze_failures": [
        ClarificationQuestion(
            id="q-run", field_name="run_id",
            prompt="Hangi koşumun analizini yapalım? (run_id veya 'son')",
            kind="text",
        ),
    ],
    "generate_test_data": [
        ClarificationQuestion(
            id="q-entity", field_name="entity",
            prompt="Hangi varlık için veri? (örn: kullanıcı, hesap, işlem)",
            kind="text",
        ),
        ClarificationQuestion(
            id="q-count", field_name="count",
            prompt="Kaç kayıt?",
            kind="number",
        ),
    ],
    "unknown": [
        ClarificationQuestion(
            id="q-goal", field_name="goal",
            prompt="Ne yapmak istediğinizi biraz daha açar mısınız? Örnek: 'Bu PRD'yi test et', 'https://app.bgtest.com'i tara', 'Smoke setini koş'.",
            kind="text",
        ),
    ],
}


def _stage_plan_for(intent: IntentKind) -> List[StagePlan]:
    """Intent'e göre stage zincirini oluştur."""
    base = [
        StagePlan(id="analyze", title="Analiz"),
        StagePlan(id="design",  title="Senaryo Tasarımı"),
        StagePlan(id="data",    title="Test Verisi"),
        StagePlan(id="execute", title="Koşum"),
        StagePlan(id="observe", title="Gözlem & Self-Heal"),
        StagePlan(id="iterate", title="İyileştirme"),
    ]
    if intent == "explore_url_and_generate_tests":
        # POM/locator ekstra bir adım
        base.insert(1, StagePlan(id="design", title="Sayfa Keşfi & POM"))
        # 1'i collapse et — basit tutalım, 6 stage kalsın
        base = base[:6]
    if intent == "run_test_suite":
        for s in base:
            if s.id in ("analyze", "design", "data"):
                s.status = "skipped"
                s.output_summary = "Bu intent için atlandı"
    if intent == "analyze_failures":
        for s in base:
            if s.id in ("analyze", "design", "data", "execute"):
                s.status = "skipped"
                s.output_summary = "Bu intent için atlandı"
    if intent == "generate_test_data":
        for s in base:
            if s.id in ("analyze", "design", "execute", "observe", "iterate"):
                s.status = "skipped"
    return base


# ── Public API ─────────────────────────────────────────────────────────────

def create_session(*, project_id: str, user_id: str) -> PilotSession:
    sid = _new_id("ps")
    s = PilotSession(id=sid, project_id=project_id, user_id=user_id)
    s.turns.append(PilotTurn(
        id=_new_id("t"),
        role="system",
        text="Merhaba — ne yapmak istiyorsunuz? Örnek: 'Bu PRD'yi test et' veya 'https://...'yi tara ve test et'.",
    ))
    _SESSIONS[sid] = s
    return s


def get_session(session_id: str) -> Optional[PilotSession]:
    return _SESSIONS.get(session_id)


def list_sessions(*, project_id: Optional[str] = None, user_id: Optional[str] = None) -> List[PilotSession]:
    items = list(_SESSIONS.values())
    if project_id:
        items = [s for s in items if s.project_id == project_id]
    if user_id:
        items = [s for s in items if s.user_id == user_id]
    items.sort(key=lambda s: s.updated_at, reverse=True)
    return items


def _next_missing_input(session: PilotSession) -> Optional[ClarificationQuestion]:
    """İlk eksik input için soru döner."""
    questions = _REQUIRED_INPUTS.get(session.intent, [])
    for q in questions:
        if q.required and q.field_name not in session.inputs:
            return q
    return None


def converse(session_id: str, user_text: str) -> PilotSession:
    """Kullanıcı mesajı geldiğinde session'ı ilerlet."""
    s = _SESSIONS.get(session_id)
    if s is None:
        raise ValueError(f"Pilot session bulunamadı: {session_id}")

    s.turns.append(PilotTurn(id=_new_id("t"), role="user", text=user_text))
    s.updated_at = _now()

    if s.intent == "unknown":
        s.intent = detect_intent(user_text)
        if s.intent != "unknown":
            s.stages = _stage_plan_for(s.intent)
            s.turns.append(PilotTurn(
                id=_new_id("t"),
                role="pilot",
                text=f"Niyetinizi anladım: **{_intent_label(s.intent)}**. Birkaç hızlı soru:",
            ))

    nq = _next_missing_input(s)
    if nq:
        s.pending_clarification = nq
        s.turns.append(PilotTurn(
            id=_new_id("t"),
            role="pilot",
            text=nq.prompt,
            clarification=nq,
        ))
        # Stage status'u awaiting_input olarak işaretle
        if s.stages:
            for st in s.stages:
                if st.status == "pending":
                    st.status = "awaiting_input"
                    break
    else:
        s.pending_clarification = None
        s.turns.append(PilotTurn(
            id=_new_id("t"),
            role="pilot",
            text="Harika — tüm bilgileri aldım. Pipeline'ı başlatıyorum. Aşamaları aşağıda canlı izleyebilirsiniz.",
        ))
        for st in s.stages:
            if st.status in ("awaiting_input", "pending"):
                st.status = "pending"

    return s


def answer_clarification(session_id: str, answer: Any) -> PilotSession:
    """Pending soru için cevap kaydet, sonraki soruyu sor veya pipeline başlat."""
    s = _SESSIONS.get(session_id)
    if s is None:
        raise ValueError(f"Pilot session bulunamadı: {session_id}")
    if s.pending_clarification is None:
        raise ValueError("Cevap bekleyen soru yok")

    field_name = s.pending_clarification.field_name
    s.inputs[field_name] = answer
    s.turns.append(PilotTurn(
        id=_new_id("t"),
        role="user",
        text=f"{field_name} = {answer!r}",
    ))
    s.pending_clarification = None
    s.updated_at = _now()

    nq = _next_missing_input(s)
    if nq:
        s.pending_clarification = nq
        s.turns.append(PilotTurn(
            id=_new_id("t"),
            role="pilot",
            text=nq.prompt,
            clarification=nq,
        ))
    else:
        s.turns.append(PilotTurn(
            id=_new_id("t"),
            role="pilot",
            text="Tüm bilgiler tamam. Pipeline başlıyor — execute_next_stage ile aşama aşama ilerleyebilirsiniz.",
        ))
        for st in s.stages:
            if st.status == "awaiting_input":
                st.status = "pending"
    return s


def execute_next_stage(session_id: str) -> PilotSession:
    """Sıradaki pending stage'i koş (mock — gerçek ajanlara hook'lanacak)."""
    s = _SESSIONS.get(session_id)
    if s is None:
        raise ValueError(f"Pilot session bulunamadı: {session_id}")
    if s.pending_clarification:
        raise ValueError("Önce bekleyen soruyu cevaplayın")

    stage = next((st for st in s.stages if st.status == "pending"), None)
    if stage is None:
        s.turns.append(PilotTurn(
            id=_new_id("t"),
            role="pilot",
            text="Tüm aşamalar tamamlandı. 🎉",
        ))
        return s

    stage.status = "in_progress"
    stage.started_at = _now()
    s.updated_at = _now()
    s.turns.append(PilotTurn(
        id=_new_id("t"),
        role="system",
        text=f"▶ {stage.title} başladı",
        stage_update={"stage_id": stage.id, "status": "in_progress"},
    ))

    # Stage işi — gerçekte ajanlara bağlanacak; şimdilik intent + inputs'a göre özet üret.
    try:
        summary, artifacts, explain = _run_stage(s, stage.id)
        stage.status = "complete"
        stage.completed_at = _now()
        stage.output_summary = summary
        stage.artifacts = artifacts
        stage.explainability = explain
        s.turns.append(PilotTurn(
            id=_new_id("t"),
            role="pilot",
            text=f"✓ {stage.title}: {summary}",
            stage_update={"stage_id": stage.id, "status": "complete"},
        ))
        # Domain event yayını — modüller arası tetikleme için
        if _event_bus is not None and _DomainEvent is not None:
            try:
                _event_bus.publish(_DomainEvent(
                    name="pipeline.stage.completed",
                    payload={
                        "session_id": s.id,
                        "stage_id": stage.id,
                        "stage_title": stage.title,
                        "summary": summary,
                        "artifacts": artifacts,
                    },
                    project_id=s.project_id,
                    actor_id=s.user_id,
                    correlation_id=s.id,
                ))
            except Exception:
                pass
    except Exception as exc:
        stage.status = "failed"
        stage.completed_at = _now()
        stage.error = str(exc)
        s.turns.append(PilotTurn(
            id=_new_id("t"),
            role="pilot",
            text=f"✗ {stage.title} hata verdi: {exc}",
            stage_update={"stage_id": stage.id, "status": "failed"},
        ))
    return s


def _run_stage(session: PilotSession, stage_id: StageId) -> tuple[str, list[dict], list[str]]:
    """Mock stage runner — gerçek ajanlara bağlanacak köprü.

    Returns: (summary, artifacts, explainability_steps)
    """
    intent = session.intent
    inputs = session.inputs

    if stage_id == "analyze":
        src = inputs.get("source", "doğrudan metin")
        ref = inputs.get("source_ref", "—")
        return (
            f"{src} kaynağından gereksinimler çıkarıldı (3 AC tespit edildi).",
            [{"kind": "requirement", "title": "REQ-001: Kullanıcı girişi"},
             {"kind": "requirement", "title": "REQ-002: Şifre sıfırlama"}],
            [f"Kaynak: {src} → {ref}",
             "document_parser ile parse edildi",
             "AC çıkarımı: 3 acceptance criteria"],
        )
    if stage_id == "design":
        return (
            "8 senaryo üretildi (smoke=3, regression=4, edge=1).",
            [{"kind": "scenario", "title": "Senaryo 1: Geçerli giriş"},
             {"kind": "scenario", "title": "Senaryo 2: Yanlış şifre"}],
            ["scenario_service.generate_for_requirement çağrıldı",
             "Türkçe → Gherkin pipeline kullanıldı"],
        )
    if stage_id == "data":
        return (
            "4 parametre seti oluşturuldu (faker.tr ile TCKN+IBAN+telefon).",
            [{"kind": "dataset", "title": "Geçerli kullanıcılar (5)"}],
            ["test_data_service ile sentetik veri",
             "Boundary + equivalence partitioning"],
        )
    if stage_id == "execute":
        browsers = inputs.get("browser", ["Chromium"])
        env = inputs.get("environment", "staging")
        return (
            f"{env} ortamında {browsers} üzerinde koşum tamamlandı (8/8 başarılı).",
            [{"kind": "execution", "run_id": "run-" + secrets.token_urlsafe(4)}],
            [f"Ortam: {env}",
             f"Tarayıcı: {browsers}",
             "Parallel executor 4 worker kullandı"],
        )
    if stage_id == "observe":
        return (
            "Self-heal: 1 locator drift tespit edildi, otomatik PR açıldı.",
            [{"kind": "pr", "title": "Healer: locator update for login form"}],
            ["Healer ajan DOM diff yaptı",
             "Stability score 78 → 92",
             "GitHub PR #142"],
        )
    if stage_id == "iterate":
        return (
            "Trend pozitif (+%4 pass rate). Öneri: 2 yeni edge case ekle.",
            [{"kind": "recommendation", "title": "Edge: çok büyük input alanı"}],
            ["test_recommendation_engine analizi",
             "trend_forecasting linear regression"],
        )
    raise ValueError(f"Bilinmeyen stage: {stage_id}")


def _intent_label(intent: IntentKind) -> str:
    return {
        "create_scenarios_from_requirements": "Gereksinimden senaryo üretimi",
        "explore_url_and_generate_tests": "URL keşfi + test üretimi",
        "run_test_suite": "Test setini koşma",
        "analyze_failures": "Başarısızlık kök neden analizi",
        "generate_test_data": "Test verisi üretimi",
        "unknown": "Belirsiz",
    }.get(intent, intent)


def clear() -> None:
    """Test helper."""
    _SESSIONS.clear()
