"""DSL Sözlüğü için AI destekli yardımcılar.

Şu anda iki ana iş yapıyor:

  * `generate_aliases(action_id, lang, count)`
      Var olan bir cümleciğe AI ile yeni TR veya EN alias önerileri üretir.
      Her öneri için mevcut alias'larla embedding-tabanlı benzerlik kontrolü
      yapılır; 0.92 üstü olanlar elenir. Geçerli öneriler `DslEditProposal`
      tablosuna `pending` olarak düşer; admin inceleyip onayladığında
      catalog'a eklenir ve git commit olarak işlenir.

  * `extract_action_from_step(step_text, lang)`
      Gherkin/doğal dil adımından yeni bir DSL aksiyon taslağı çıkarır
      (ileride kullanılacak — şu an sadece yardımcı).

Bu modül hem Gateway'e hem de katalog loader'a dayanır; prod AI akışı
kapalıysa (`AI_GATEWAY_BASE_URL` boş / erişilemiyor) fonksiyonlar
`EditorError` fırlatır.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.domains.ai.gateway_client import gateway_complete
from app.domains.dsl import editor_service
from app.domains.dsl.editor_service import EditorError, NotFoundError
from app.domains.dsl.loader import catalog_cache

logger = logging.getLogger(__name__)

# bge-m3 embedding benzerliği bu eşiği geçerse duplicate sayılır
_DEDUPE_THRESHOLD = 0.92

# LLM JSON yanıtından liste/dict çıkar — gateway_client'takiyle tutarlı
_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _parse_json(raw: str) -> Any:
    text = (raw or "").strip()
    m = _FENCE_RE.match(text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback: ilk { .. son } aralığı
    for s, e in [("{", "}"), ("[", "]")]:
        i, j = text.find(s), text.rfind(e)
        if i >= 0 and j > i:
            try:
                return json.loads(text[i : j + 1])
            except json.JSONDecodeError:
                pass
    return None


# ── Benzerlik eleme ────────────────────────────────────────────────────────


def _dedupe_against_existing(
    candidates: list[str], existing: list[str]
) -> list[str]:
    """Embedding cosine ile near-duplicate aday'ları ele. Başarısızsa
    sadece exact match kontrolü ile yetin.
    """
    norm_existing = {e.strip().lower() for e in existing if e}
    unique: list[str] = []
    for c in candidates:
        s = (c or "").strip()
        if not s:
            continue
        if s.lower() in norm_existing:
            continue
        if s.lower() in {u.lower() for u in unique}:
            continue
        unique.append(s)

    if not unique:
        return []

    # Embedding kontrolü — başarısızsa exact-match'e dayan
    try:
        from app.domains.ai.gateway_client import gateway_embed

        import numpy as np  # type: ignore[import-untyped]

        data = gateway_embed(existing + unique)
        vectors = np.asarray(data["vectors"], dtype=np.float32)
        if not vectors.size:
            return unique
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors = vectors / norms
        n_existing = len(existing)
        existing_vec = vectors[:n_existing]
        unique_vec = vectors[n_existing:]
        if existing_vec.size == 0:
            return unique
        sims = unique_vec @ existing_vec.T  # (M, N)
        keep: list[str] = []
        for i, row in enumerate(sims):
            if float(row.max()) < _DEDUPE_THRESHOLD:
                keep.append(unique[i])
        return keep
    except Exception as exc:  # noqa: BLE001
        logger.debug("Alias dedupe embed skipped: %s", exc)
        return unique


# ── Alias üretimi ──────────────────────────────────────────────────────────


_ALIAS_PROMPT_TEMPLATE = (
    "Bir QA DSL cümleciği için {count} adet {lang_label} alias üret.\n\n"
    "Aksiyon:\n"
    "  id: {id}\n"
    "  category: {category}\n"
    "  description: {description}\n"
    "  parameters: {params}\n"
    "  existing_tr: {existing_tr}\n"
    "  existing_en: {existing_en}\n\n"
    "Kurallar:\n"
    "- Parametreleri {{name}} biçiminde yer tutucu olarak koru.\n"
    "- Mevcut alias'larla anlamca aynı olmamalı, yeni bir ifade olmalı.\n"
    "- Kısa, doğal; soru/nokta ekleme.\n"
    "- lang='tr' ise tamamen Türkçe, lang='en' ise tamamen İngilizce olmalı.\n\n"
    "SADECE JSON dön:\n"
    '{{"aliases": ["alias 1", "alias 2"]}}'
)


def generate_aliases(
    db,
    *,
    action_id: str,
    lang: str,
    count: int,
    actor,
) -> dict[str, Any]:
    """Var olan bir cümleciğe AI ile yeni alias'lar önerir.

    Her kabul edilen aday için `DslEditProposal` (status="pending",
    proposer_kind="ai") oluşturur. Dönüş sözlüğü UI'ın kullanıcıya
    göstereceği özeti taşır: {accepted: [...], rejected: [...], ...}
    """
    if lang not in {"tr", "en"}:
        raise EditorError("lang 'tr' veya 'en' olmalı")
    if count < 1 or count > 10:
        raise EditorError("count 1-10 arası olmalı")

    action = catalog_cache.get(action_id)
    if action is None:
        raise NotFoundError(f"Action bulunamadı: {action_id}")

    aliases = action.aliases or {}
    existing_tr = list(aliases.get("tr") or [])
    existing_en = list(aliases.get("en") or [])
    param_names = [p.name for p in (action.parameters or [])]

    prompt = _ALIAS_PROMPT_TEMPLATE.format(
        count=count,
        lang_label="Türkçe" if lang == "tr" else "İngilizce",
        id=action.id,
        category=action.category,
        description=action.description,
        params=json.dumps(param_names, ensure_ascii=False),
        existing_tr=json.dumps(existing_tr, ensure_ascii=False),
        existing_en=json.dumps(existing_en, ensure_ascii=False),
    )

    try:
        raw = gateway_complete(
            task_type="dsl_alias_gen",
            user_message=prompt,
            temperature=0.6,
            max_tokens=500,
            json_mode=True,
        )
    except RuntimeError as exc:
        raise EditorError(f"AI gateway hatası: {exc}") from exc

    parsed = _parse_json(raw)
    candidates: list[str] = []
    if isinstance(parsed, dict):
        items = parsed.get("aliases") or []
        if isinstance(items, list):
            candidates = [str(x) for x in items if isinstance(x, (str, int))]
    if not candidates:
        return {
            "accepted": [],
            "rejected": [],
            "reason": "AI boş veya geçersiz yanıt verdi",
            "raw": raw[:200],
        }

    # Dedupe
    existing_all = existing_tr + existing_en
    accepted = _dedupe_against_existing(candidates, existing_all)
    rejected = [c for c in candidates if c not in accepted]

    if not accepted:
        return {
            "accepted": [],
            "rejected": rejected,
            "reason": "Tüm adaylar mevcut alias'larla benzer bulundu",
        }

    # Her kabul edilen alias için bir pending proposal (update op'u)
    proposals: list[str] = []
    for alias in accepted:
        new_aliases = dict(aliases)
        new_aliases[lang] = list(new_aliases.get(lang) or []) + [alias]
        updated = action.model_dump(mode="json", exclude_none=True)
        updated.pop("source_yaml", None)
        updated["aliases"] = new_aliases

        before_raw = {
            k: v
            for k, v in action.model_dump(mode="json", exclude_none=True).items()
            if k != "source_yaml"
        }
        diff = editor_service.compute_diff(before_raw, updated)
        # editor_service._record_proposal'e direkt çağırmak yerine doğrudan ekliyoruz
        # çünkü proposer_kind="ai" ve require_review akışına benziyor
        from app.infra.models import DslEditProposal
        import uuid

        prop = DslEditProposal(
            id=str(uuid.uuid4()),
            action_id=action.id,
            proposer_id=getattr(actor, "id", None),
            proposer_kind="ai",
            operation="update",
            status="pending",
            diff=diff,
            ai_reasoning=(
                f"Ollama {lang} alias üretici — yeni alias: '{alias}' "
                f"({len(candidates)} adaydan {len(accepted)} kabul)"
            ),
        )
        db.add(prop)
        db.flush()
        proposals.append(prop.id)

    db.commit()

    return {
        "accepted": accepted,
        "rejected": rejected,
        "proposals": proposals,
        "lang": lang,
        "action_id": action_id,
    }


def extract_action_from_step(step_text: str, lang: str) -> Optional[dict[str, Any]]:
    """Doğal dil adımından yeni DSL aksiyon taslağı üret.

    Bu fonksiyon mobile scenario flow'unda "bilinmeyen step" için kullanılacak.
    Şimdilik minimal — UI tarafı henüz bağlanmadı.
    """
    existing_categories = sorted(
        {a.category for a in catalog_cache.all() if a.category}
    )
    prompt = (
        "Bir test adımından yeni bir DSL aksiyon taslağı üret.\n"
        f'Girdi: {{"step_text": {json.dumps(step_text)}, "lang": "{lang}", '
        f'"existing_categories": {json.dumps(existing_categories)}}}\n\n'
        "SADECE JSON dön. Şemaya uy (id snake_case, category hiyerarşik, "
        "parameters yerinde çıkarılmış)."
    )
    try:
        raw = gateway_complete(
            task_type="dsl_extract",
            user_message=prompt,
            temperature=0.4,
            max_tokens=800,
            json_mode=True,
        )
    except RuntimeError:
        return None
    parsed = _parse_json(raw)
    return parsed if isinstance(parsed, dict) else None
