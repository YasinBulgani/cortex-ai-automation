"""LLM-as-Judge senaryo kalite skoru + semantik embedding yardımcıları.

Dalga 0 · E2 · "LLM daha derin entegrasyon" planının ilk somut parçası.

Amaç:
    1. Her TspmScenario için LLM tabanlı 0-100 kalite skoru + sorun listesi
       üret. BDDK / test yazım prensipleri (belirsiz ifadeler, eksik
       "Given/When/Then" dengesi, değer setleri, beklenen sonucun netliği,
       tek sorumluluk) gibi kontroller.
    2. Senaryo başlığı + adım özeti için 768-boyutlu nomic-embed-text
       vektörü üret. Aynı proje içinde **duplicate / semantic overlap**
       tespiti için kosinüs benzerliği ile en yakın komşuyu bul.

Depolama:
    * quality_score / quality_issues / quality_summary / quality_scored_at
      sütunları (``scenario_quality_llm_0001`` migration'u).
    * title_embedding JSONB — pgvector zorunluluğu olmadan, kosinüs
      Python'da hesaplanır (proje başına birkaç yüz senaryo için kafi).

Yalıtım:
    LLM / Ollama erişilemezse **deterministik heuristic** fallback
    devreye girer — kullanıcı her zaman bir skor görür; BDDK
    denetlenebilirlik için prod gereksinimi.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── LLM prompt ────────────────────────────────────────────────────────────────

_JUDGE_SYSTEM = (
    "Sen deneyimli bir QA test mühendisisin. Verilen manuel/BDD test senaryosunu "
    "Türk bankacılık (BDDK) standartlarına göre değerlendiriyorsun. Kısa, "
    "nesnel, yapılandırılmış JSON döndürüyorsun. Başka metin yazma."
)

_JUDGE_USER_TEMPLATE = """Senaryo:
Başlık: {title}
Açıklama: {description}
Adımlar:
{steps}

Bu senaryoyu şu 5 kritere göre 0-100 arasında puanla:
  1. netlik          — ifadelerde muğlaklık, belirsizlik var mı
  2. tamlik          — Given/When/Then üçlüsü veya benzer yapısı eksiksiz mi
  3. test_edilebilir — adımlar gözlemlenebilir/doğrulanabilir mi
  4. beklenen_sonuc  — her adımın/testin beklenen sonucu net mi
  5. tek_sorumluluk  — tek bir iş/akış mı yoksa 3-4 test birleşmiş mi

Toplamda 0-100 bir genel skor, sorunlu noktaların kısa listesini ve
1-2 cümlelik bir özet üret.

Yalnızca şu formatta JSON döndür:
{{
  "score": 0-100 arası int,
  "sub_scores": {{
    "netlik": int,
    "tamlik": int,
    "test_edilebilir": int,
    "beklenen_sonuc": int,
    "tek_sorumluluk": int
  }},
  "issues": [
    {{"severity": "low|medium|high", "field": "title|steps|description|general", "message": "TR açıklama"}}
  ],
  "summary": "1-2 cümlelik TR gerekçe"
}}
"""


def _steps_to_text(steps: list[dict[str, Any]] | None) -> str:
    if not steps:
        return "(adım yok)"
    out: list[str] = []
    for i, st in enumerate(steps, start=1):
        if not isinstance(st, dict):
            continue
        kw = (st.get("keyword") or "").strip()
        tx = (st.get("text") or st.get("action") or "").strip()
        expected = (st.get("expected") or "").strip()
        line = f"  {i}. {kw + ' ' if kw else ''}{tx}"
        if expected:
            line += f" → {expected}"
        out.append(line)
    return "\n".join(out) if out else "(adım yok)"


def _scenario_as_embedding_text(title: str, description: str | None, steps: list[dict[str, Any]] | None) -> str:
    """Embedding için başlık + kısa step özeti. Fazla uzatmadan semantik imza.

    Başlık en ağırlıklı sinyal; duplicate tespiti için başlık + ilk 3 adım
    kafi. 4000 karakterlik knowledge_store kuralı burada da geçerli.
    """
    parts: list[str] = [f"Başlık: {title}"]
    if description:
        parts.append(f"Açıklama: {description.strip()[:300]}")
    compact_steps: list[str] = []
    for st in (steps or [])[:6]:
        if not isinstance(st, dict):
            continue
        tx = (st.get("text") or st.get("action") or "").strip()
        if tx:
            compact_steps.append(tx[:160])
    if compact_steps:
        parts.append("Adımlar: " + " | ".join(compact_steps))
    return "\n".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────


def score_scenario_with_llm(
    title: str,
    description: str | None,
    steps: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Senaryonun kalite skorunu LLM ile üret; LLM yoksa heuristic fallback.

    Dönüş sözleşmesi::

        {
          "score": int 0-100,
          "sub_scores": {netlik, tamlik, test_edilebilir, beklenen_sonuc, tek_sorumluluk},
          "issues": [{severity, field, message}],
          "summary": str,
          "source": "llm" | "heuristic"
        }
    """
    steps_txt = _steps_to_text(steps)

    # 1) LLM yolu
    try:
        from app.domains.ai.service import call_llm

        raw = call_llm(
            _JUDGE_SYSTEM,
            _JUDGE_USER_TEMPLATE.format(
                title=(title or "").strip() or "(başlık yok)",
                description=(description or "").strip() or "(açıklama yok)",
                steps=steps_txt,
            ),
            json_mode=True,
            _trace_agent="scenario_judge",
        )
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(parsed, dict) and "score" in parsed:
            # Alan tiplerini normalize et
            score = int(max(0, min(100, int(parsed.get("score", 0) or 0))))
            sub = parsed.get("sub_scores") or {}
            if not isinstance(sub, dict):
                sub = {}
            issues = parsed.get("issues") or []
            if not isinstance(issues, list):
                issues = []
            # Her issue için alanları garantile
            clean_issues: list[dict[str, Any]] = []
            for it in issues[:10]:
                if not isinstance(it, dict):
                    continue
                sev = str(it.get("severity") or "medium").lower()
                if sev not in {"low", "medium", "high"}:
                    sev = "medium"
                clean_issues.append({
                    "severity": sev,
                    "field": str(it.get("field") or "general")[:32],
                    "message": str(it.get("message") or "")[:400],
                })
            return {
                "score": score,
                "sub_scores": {k: int(v) for k, v in sub.items() if isinstance(v, (int, float))},
                "issues": clean_issues,
                "summary": str(parsed.get("summary") or "")[:500],
                "source": "llm",
            }
    except Exception as exc:  # noqa: BLE001
        logger.debug("LLM judge başarısız, heuristic'e düşülüyor: %s", exc)

    # 2) Heuristic fallback
    return _heuristic_score(title or "", description or "", steps or [])


# ── Heuristic (deterministik) fallback ───────────────────────────────────────


_VAGUE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(bazı|çoğu|genelde|bir şekilde|uygun şekilde|vs\.?|v\.b\.?)\b", re.I), "Muğlak ifade kullanılmış"),
    (re.compile(r"\b(kısa bir süre|bir süre sonra|hızlı|yavaş)\b", re.I), "Zaman/süre belirsiz"),
    (re.compile(r"\b(doğru|yanlış)\b(?! olduğu|lığı)", re.I), "Doğrulama kriteri soyut"),
]

_EXPECTED_KEYWORDS = ("beklenen", "görüntülenir", "döner", "dönmeli", "olmalı", "gösterir", "→")


def _heuristic_score(title: str, description: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    subs = {
        "netlik": 85,
        "tamlik": 85,
        "test_edilebilir": 85,
        "beklenen_sonuc": 85,
        "tek_sorumluluk": 85,
    }

    # 1) netlik — muğlak kelime taraması
    full = " ".join([title, description] + [
        (s.get("text") or s.get("action") or "") for s in steps if isinstance(s, dict)
    ])
    for pat, msg in _VAGUE_PATTERNS:
        if pat.search(full):
            subs["netlik"] -= 10
            issues.append({"severity": "medium", "field": "general", "message": msg})
    subs["netlik"] = max(0, subs["netlik"])

    # 2) tamlik — en az 2 adım?
    if len(steps) < 2:
        subs["tamlik"] = 40
        issues.append({"severity": "high", "field": "steps",
                       "message": "En az bir ön koşul ve bir aksiyon adımı olmalı."})
    elif len(steps) < 3:
        subs["tamlik"] = 70
        issues.append({"severity": "low", "field": "steps",
                       "message": "Given/When/Then üçlüsü tamamlanmamış görünüyor."})

    # 3) test_edilebilir — step text boş mu
    empty = sum(
        1 for s in steps
        if isinstance(s, dict)
        and not (s.get("text") or s.get("action") or "").strip()
    )
    if empty:
        subs["test_edilebilir"] -= 25
        issues.append({"severity": "high", "field": "steps",
                       "message": f"{empty} adım boş — eylem veya doğrulama yok."})
    subs["test_edilebilir"] = max(0, subs["test_edilebilir"])

    # 4) beklenen_sonuc — herhangi bir adımda/metinde beklenen sonuç var mı
    if not any(kw in full.lower() for kw in _EXPECTED_KEYWORDS):
        subs["beklenen_sonuc"] = 55
        issues.append({"severity": "medium", "field": "steps",
                       "message": "Beklenen sonuç (görüntülenir/döner vb.) belirtilmemiş."})

    # 5) tek_sorumluluk — >10 adım şüpheli
    if len(steps) > 10:
        subs["tek_sorumluluk"] = 55
        issues.append({"severity": "medium", "field": "steps",
                       "message": "Çok fazla adım — senaryoyu bölmeyi düşün."})

    score = int(round(sum(subs.values()) / len(subs)))
    summary = "Heuristic değerlendirme — LLM erişilemiyor. "
    if score >= 85:
        summary += "Senaryo yapı olarak sağlam görünüyor."
    elif score >= 65:
        summary += "Küçük iyileştirmelerle test edilebilir."
    else:
        summary += "Tekrar yazılması önerilir."

    return {
        "score": score,
        "sub_scores": subs,
        "issues": issues,
        "summary": summary,
        "source": "heuristic",
    }


# ── Embedding yardımcıları ───────────────────────────────────────────────────


def embed_scenario(title: str, description: str | None, steps: list[dict[str, Any]] | None) -> list[float] | None:
    """768-boyutlu vektör döndürür; Ollama yoksa None."""
    try:
        from app.domains.ai.knowledge_store import _embed  # noqa: WPS436 — paylaşılan helper
    except Exception as exc:
        logger.debug("knowledge_store._embed import edilemedi: %s", exc)
        return None
    text = _scenario_as_embedding_text(title, description, steps)
    return _embed(text)


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / ((na ** 0.5) * (nb ** 0.5))


def find_similar_scenarios(
    target_embedding: list[float] | None,
    candidates: list[tuple[str, str, list[float] | None]],
    top_k: int = 5,
    min_similarity: float = 0.75,
) -> list[dict[str, Any]]:
    """En benzer senaryoları kosinüs benzerliği ile bul.

    Args:
        target_embedding: Kaynak senaryonun vektörü.
        candidates: [(scenario_id, title, embedding), ...] listesi.
        top_k: Döndürülecek maksimum sonuç.
        min_similarity: Altında kalan eşleşmeler gizlenir.
    """
    if not target_embedding:
        return []
    scored: list[tuple[float, str, str]] = []
    for cid, title, emb in candidates:
        sim = cosine(target_embedding, emb)
        if sim >= min_similarity:
            scored.append((sim, cid, title))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"scenario_id": cid, "title": t, "similarity": round(s, 4)}
        for s, cid, t in scored[:top_k]
    ]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
