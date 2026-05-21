"""LLM-boundary PII Redactor — TEK kaynak.

Metin içinde geçen TCKN, IBAN, e-posta, telefon, kredi kartı gibi hassas
verileri LLM'e gitmeden önce veya yanıttan döndürmeden önce tespit edip
sabit bir placeholder ile değiştirir. KVKK/BDDK uyumu için critical katman.

Kullanım:
    from app.domains.ai.pii_redactor import redact, detect_pii_categories
    masked = redact("TC: 12345678901, IBAN: TR33...")
    # -> "TC: [TC_KIMLIK], IBAN: [IBAN]"

Tasarım:
    * Placeholder formatı kararlı: [TC_KIMLIK], [IBAN], [EMAIL], [TELEFON], [KART]
      (engine + testler bu format üzerinde kilitli; geriye dönük uyumlu).
    * Pattern'ler ``packages/banking-domain`` KVKK modülüyle aynı semantik;
      bu modül LLM hattı için optimize (speed + kararlı placeholder).
    * Hem sync (string) hem streaming için tasarlandı — ileride "chunk-aware"
      mode için hook bırakıldı.

Not:
    Column-name / schema-level PII tespiti ``ai_synthetic_data/differential_privacy.py``
    ve ``tspm/db_schema_parser.py`` modüllerinde; onların sorumluluğu farklı
    (kolon adı heuristic, değer değil). Bu modül sadece metin-içi-değer redaksiyonu yapar.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ── Placeholder sabitleri (geriye dönük uyumluluk için KİLİTLİ) ──────────
PH_TCKN = "[TC_KIMLIK]"
PH_IBAN = "[IBAN]"
PH_EMAIL = "[EMAIL]"
PH_PHONE = "[TELEFON]"
PH_CARD = "[KART]"


# ── Pattern tanımları — sıra önemli (kart IBAN'dan önce, aksi halde 16
# rakamı IBAN parçası sanılabilir). Her tuple: (kategori, pattern, placeholder) ─
_PII_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # Türk IBAN — TR + 2 kontrol + 4x4x4x4x4x2 (boşlukla olsun olmasın)
    (
        "iban_tr",
        re.compile(
            r"\b[Tt][Rr]\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b"
        ),
        PH_IBAN,
    ),
    # Kredi kartı: 13-19 rakam, boşluk/tire separatorlarıyla (Luhn doğrulaması yapmıyoruz —
    # pessimistic fail-open; false positive kabul edilebilir, kaçak değil).
    (
        "card",
        re.compile(r"\b(?:\d[ -]?){13,19}\b"),
        PH_CARD,
    ),
    # Türk cep telefonu: +90 / 0 prefix + 5xx + 3+2+2 (boşluk/tire ile)
    (
        "phone_tr",
        re.compile(
            r"(?:\+90|0)?\s?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b"
        ),
        PH_PHONE,
    ),
    # E-posta — RFC5322 basitleştirilmiş
    (
        "email",
        re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b"),
        PH_EMAIL,
    ),
    # TCKN — 11 rakam, ilk rakam 0 olamaz (algoritmik doğrulama yapmıyoruz)
    (
        "tckn",
        re.compile(r"\b[1-9]\d{10}\b"),
        PH_TCKN,
    ),
]


@dataclass(frozen=True)
class RedactionResult:
    masked: str
    counts: Dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def redact(text: str) -> str:
    """Metindeki PII'ları placeholder'larla değiştir, sonuç stringi döndür."""
    if not text:
        return text
    result = text
    for _cat, pattern, placeholder in _PII_PATTERNS:
        result = pattern.sub(placeholder, result)
    return result


def redact_with_stats(text: str) -> RedactionResult:
    """Redakte edilmiş metin + kategori başına eşleşme sayısı."""
    if not text:
        return RedactionResult(masked=text or "", counts={})
    counts: Dict[str, int] = {}
    result = text
    for cat, pattern, placeholder in _PII_PATTERNS:
        found = pattern.findall(result)
        if found:
            counts[cat] = len(found)
            result = pattern.sub(placeholder, result)
    return RedactionResult(masked=result, counts=counts)


def detect_pii_categories(text: str) -> Dict[str, List[str]]:
    """Metinde bulunan PII kategorilerini ve eşleşmelerini döndür (redakte etme)."""
    if not text:
        return {}
    out: Dict[str, List[str]] = {}
    for cat, pattern, _ph in _PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            # set ile tekrarları at + stable sıra için listele
            out[cat] = sorted(set(matches))
    return out


def has_pii(text: str) -> bool:
    return bool(detect_pii_categories(text))


def redact_messages(messages: List[dict]) -> List[dict]:
    """OpenAI/Anthropic mesaj listesindeki 'content' alanlarını redakte eder.

    Multipart content (list of blocks) de desteklenir.
    """
    out = []
    for msg in messages:
        if not isinstance(msg, dict):
            out.append(msg)
            continue
        content = msg.get("content")
        new_msg = dict(msg)
        if isinstance(content, str):
            new_msg["content"] = redact(content)
        elif isinstance(content, list):
            new_content = []
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    b = dict(block)
                    b["text"] = redact(block["text"])
                    new_content.append(b)
                else:
                    new_content.append(block)
            new_msg["content"] = new_content
        out.append(new_msg)
    return out


# ── Geriye dönük uyumluluk API'si (engine llm_gateway için) ─────────────
def legacy_pattern_list() -> List[Tuple[str, str]]:
    """``(regex, placeholder)`` tuple listesi — eski engine kodu için."""
    return [(p.pattern, ph) for _cat, p, ph in _PII_PATTERNS]
