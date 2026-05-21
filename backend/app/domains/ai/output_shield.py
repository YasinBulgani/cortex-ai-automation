"""
Output Shield — LLM cevaplarinin guvenlik/uyumluluk denetimi.

prompt_shield.py giriş tarafi; bu modul cikis tarafi. LLM cevabini client'a
dondurmeden once su kontrolleri yapar:

  1. System Prompt Leak      — "my instructions are", "ignore previous" echo
  2. PII Sizintisi            — TCKN/IBAN/kart/email cikti cercevesinde
     (input'ta yoktu ama cikti da varsa = hallucination = sizma)
  3. Kredi Karti (Luhn check) — 13-19 basamakli Luhn-geçerli numara
  4. SQL Injection Ibareleri — generated test kodunda DROP/TRUNCATE patterns
  5. Jailbreak Leak           — "as an AI I cannot" -> policy violation text

Karar:
    ShieldDecision: allow | warn | block
    block => orijinal cevap REDAKT EDILIR veya HATA donulur (config)

DB audit: output_violations tablosu (migration 0007).
Flag: ai.output_shield (default True).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal, Optional

logger = logging.getLogger(__name__)

ShieldDecision = Literal["allow", "warn", "block"]


# ── Pattern kutuphanesi ──────────────────────────────────────────────────


_SYSTEM_PROMPT_LEAK: list[tuple[float, re.Pattern[str], str]] = [
    (0.9, re.compile(r"(?i)\bmy (instructions|system prompt|directives)\b"), "system_prompt_echo"),
    (0.8, re.compile(r"(?i)\bi was (told|instructed|programmed) to\b"), "instruction_echo"),
    (0.9, re.compile(r"(?i)\bignore (all )?(previous|prior|above) (instructions|prompts|rules)\b"), "ignore_instruction_echo"),
    (0.8, re.compile(r"(?i)benim talimatlarim|sistem prompt'um|sistem ifadem"), "system_prompt_echo_tr"),
]


_PII_EXTERNAL: list[tuple[float, re.Pattern[str], str]] = [
    # IBAN — output'ta duz TR IBAN olmamali
    (0.95, re.compile(r"\bTR\d{24}\b"), "iban_leak"),
    # TC Kimlik (11 hane, ilk hane 0 degil — MASAK standardi)
    (0.95, re.compile(r"\b[1-9]\d{10}\b(?![\w.])"), "tckn_leak"),
    # Email
    (0.5, re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", re.I), "email_leak"),
    # Turk cep
    (0.5, re.compile(r"(?:\+90|0)?\s*5\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b"), "phone_leak"),
]


_SQL_DESTRUCTIVE: list[tuple[float, re.Pattern[str], str]] = [
    (0.95, re.compile(r"(?i)\bDROP\s+(TABLE|DATABASE|SCHEMA|USER)\b"), "sql_drop"),
    (0.9, re.compile(r"(?i)\bTRUNCATE\s+TABLE\b"), "sql_truncate"),
    (0.85, re.compile(r"(?i)\bDELETE\s+FROM\s+\w+(?!\s+WHERE)"), "sql_delete_no_where"),
    # Union-based sqli leakage
    (0.8, re.compile(r"(?i)'\s*(OR|AND)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+"), "sqli_payload"),
]


_JAILBREAK_OUTPUT: list[tuple[float, re.Pattern[str], str]] = [
    (0.7, re.compile(r"(?i)\bas an ai (language )?model\b"), "policy_apology"),
    (0.6, re.compile(r"(?i)i (cannot|can't|am unable to)\b.*\b(assist|help)"), "refusal_text"),
    (0.8, re.compile(r"(?i)\bDAN mode\b|\bjailbreak successful\b|\bdeveloper mode\b"), "jailbreak_marker"),
]


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class ShieldHit:
    category: str
    pattern_name: str
    score: float
    excerpt: str


@dataclass
class ShieldResult:
    decision: ShieldDecision
    score: float
    hits: list[ShieldHit] = field(default_factory=list)
    sanitized: Optional[str] = None  # decision=="block" durumunda redact edilmis cevap

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "score": round(self.score, 3),
            "hits": [
                {
                    "category": h.category,
                    "pattern": h.pattern_name,
                    "score": h.score,
                    "excerpt": h.excerpt[:120],
                }
                for h in self.hits
            ],
        }


# ── Luhn check for credit cards ─────────────────────────────────────────


_CARD_LIKE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def _luhn(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def _scan_credit_cards(text: str) -> list[ShieldHit]:
    """Luhn-geçerli kart numaralarini yakala."""
    hits: list[ShieldHit] = []
    for match in _CARD_LIKE.finditer(text):
        candidate = match.group(0)
        if _luhn(candidate):
            # Test kartlari (4111...) bile leak — hepsi yakalanir
            hits.append(ShieldHit(
                category="pii_leak",
                pattern_name="credit_card_luhn",
                score=0.95,
                excerpt=candidate,
            ))
    return hits


# ── Feature flag ────────────────────────────────────────────────────────


def _shield_enabled(tenant_id: Optional[str] = None) -> bool:
    """Feature flag: ai.output_shield — default True."""
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.output_shield", tenant_id=tenant_id, default=True)
    except Exception:
        return True


# ── Public API ───────────────────────────────────────────────────────────


def inspect_output(
    text: str,
    *,
    task_type: str = "",
    original_input: Optional[str] = None,
    block_threshold: float = 0.85,
    warn_threshold: float = 0.5,
    tenant_id: Optional[str] = None,
) -> ShieldResult:
    """
    LLM cevabini denetle ve karar dondur.

    Args:
        text:            LLM'den dönen ham cevap
        task_type:       Kontekst (test_generation'da SQL patterni normal olabilir)
        original_input:  Input'ta PII varsa, cikti'da tekrari normaldir — PII hit
                         degerlendirmesinde bu bilgi kullanilir
        block_threshold: Uzerindeki skor -> block
        warn_threshold:  Uzerindeki -> warn (log + metric), cevap yine doner
        tenant_id:       Feature flag için

    Returns:
        ShieldResult
    """
    if not _shield_enabled(tenant_id):
        return ShieldResult(decision="allow", score=0.0)

    if not text or len(text) < 10:
        return ShieldResult(decision="allow", score=0.0)

    hits: list[ShieldHit] = []

    # 1) System prompt leak
    for score, pattern, name in _SYSTEM_PROMPT_LEAK:
        m = pattern.search(text)
        if m:
            hits.append(ShieldHit("system_prompt_leak", name, score, m.group(0)))

    # 2) PII — cikti'da var, input'ta yoksa leak
    for score, pattern, name in _PII_EXTERNAL:
        m = pattern.search(text)
        if not m:
            continue
        matched = m.group(0)
        # Eger input'ta da bu PII varsa hallucination degil, user girdi
        if original_input and matched in original_input:
            continue
        hits.append(ShieldHit("pii_leak", name, score, matched))

    # 3) Kredi karti (Luhn)
    hits.extend(_scan_credit_cards(text))

    # 4) SQL destructive patterns
    # test_generation/security_audit task'larinda bu patterns beklendigi için skoru dusur
    sql_mult = 0.3 if task_type in ("test_generation", "security_audit") else 1.0
    for score, pattern, name in _SQL_DESTRUCTIVE:
        m = pattern.search(text)
        if m:
            hits.append(ShieldHit("sql_destructive", name, score * sql_mult, m.group(0)))

    # 5) Jailbreak output
    for score, pattern, name in _JAILBREAK_OUTPUT:
        m = pattern.search(text)
        if m:
            hits.append(ShieldHit("jailbreak_output", name, score, m.group(0)))

    # Karar
    if not hits:
        return ShieldResult(decision="allow", score=0.0)

    max_score = max(h.score for h in hits)

    if max_score >= block_threshold:
        sanitized = _redact(text, hits)
        _persist_violation(task_type, hits, "block", tenant_id=tenant_id)
        logger.warning(
            "OutputShield BLOCK (score=%.2f, hits=%d) task=%s",
            max_score, len(hits), task_type,
        )
        return ShieldResult(decision="block", score=max_score, hits=hits, sanitized=sanitized)

    if max_score >= warn_threshold:
        _persist_violation(task_type, hits, "warn", tenant_id=tenant_id)
        logger.info(
            "OutputShield WARN (score=%.2f, hits=%d) task=%s",
            max_score, len(hits), task_type,
        )
        return ShieldResult(decision="warn", score=max_score, hits=hits)

    return ShieldResult(decision="allow", score=max_score, hits=hits)


def _redact(text: str, hits: list[ShieldHit]) -> str:
    """Bloklu durumda hassas parcalari [REDACTED] ile değiştir."""
    redacted = text
    for h in hits:
        if h.excerpt and len(h.excerpt) > 2:
            redacted = redacted.replace(h.excerpt, f"[REDACTED:{h.category}]")
    return redacted


def _persist_violation(
    task_type: str,
    hits: list[ShieldHit],
    decision: str,
    *,
    tenant_id: Optional[str] = None,
) -> None:
    """output_violations tablosuna kaydet (audit).

    Tablo yoksa sessiz atla — migration henuz uygulanmamis olabilir.
    """
    try:
        from app.domains.ai.llm_trace import _get_conn
        from app.domains.ai.correlation import get_correlation_id
        import json
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'output_violations')"
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    return
                cur.execute(
                    """
                    INSERT INTO output_violations
                        (task_type, decision, hits, correlation_id, tenant_id)
                    VALUES (%s, %s, %s::jsonb, %s, %s)
                    """,
                    (
                        task_type,
                        decision,
                        json.dumps([
                            {
                                "category": h.category,
                                "pattern": h.pattern_name,
                                "score": h.score,
                                "excerpt": h.excerpt[:200],
                            }
                            for h in hits
                        ]),
                        get_correlation_id(),
                        tenant_id,
                    ),
                )
        finally:
            conn.close()
    except Exception as exc:
        logger.debug("_persist_violation hatasi: %s", exc)


def get_violation_stats(days: int = 7) -> dict:
    """Dashboard için output_violations istatistigi."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'output_violations')"
                )
                if not cur.fetchone()[0]:
                    return {"enabled": False}
                cur.execute(
                    """
                    SELECT decision, COUNT(*) as cnt
                    FROM output_violations
                    WHERE created_at > NOW() - INTERVAL %s
                    GROUP BY decision
                    """,
                    (f"{int(days)} days",),
                )
                by_decision = {r[0]: r[1] for r in cur.fetchall() or []}

                cur.execute(
                    """
                    SELECT task_type, COUNT(*) as cnt
                    FROM output_violations
                    WHERE created_at > NOW() - INTERVAL %s
                    GROUP BY task_type
                    ORDER BY cnt DESC
                    """,
                    (f"{int(days)} days",),
                )
                by_task = [
                    {"task_type": r[0], "count": r[1]}
                    for r in cur.fetchall() or []
                ]

                return {
                    "enabled": True,
                    "by_decision": by_decision,
                    "by_task": by_task,
                    "period_days": days,
                }
        finally:
            conn.close()
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}
