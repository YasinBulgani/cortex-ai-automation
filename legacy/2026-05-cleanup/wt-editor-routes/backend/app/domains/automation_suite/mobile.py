"""Mobil senaryo üretici — doğal dil + cihaz context → Gherkin.

`POST /api/v1/automation-suite/mobile/generate` ile çağrılır. Kullanıcı
Visium Farm sayfasında doğal dilde bir senaryo yazar, backend mobil DSL
katalogunu bu isteğe AI'e (Ollama + qwen2.5-coder) prompt olarak verir ve
yalnızca izin verilen cümleciklerden bir Gherkin çıkar.

Adımlar:
    1. Mobil kategorideki cümlecikleri katalogdan topla (alias listesi).
    2. Gateway `mobile_scenario` task'ıyla Ollama çağır — çıkış plain
       Gherkin metni.
    3. Üretilen Gherkin'in her adımını DSL ile eşleştir; bilinmeyen adımlar
       raporlanır (UI bunları highlight ederek kullanıcıya gösterir).
    4. `save_feature=true` ise çıktıyı `engine/features/ai-mobile/<slug>.feature`
       dosyasına yaz (ileride run trigger için). Şu an varsayılan False —
       kullanıcı Visium Farm üzerinden manuel çalıştırır.

Bu modül LLM cevabını YAML'e yazmaz, git commit atmaz. Tek çıktı Gherkin
metni + match raporudur.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.domains.ai.gateway_client import gateway_complete
from app.domains.dsl.loader import catalog_cache
from app.domains.dsl.service import search_actions

logger = logging.getLogger(__name__)

_GHERKIN_STEP_RE = re.compile(
    r"^\s*(Given|When|Then|And|But)\s+(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


# ── Şemalar ────────────────────────────────────────────────────────────────


class MobileGenerateRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=4000)
    device: Optional[dict[str, Any]] = Field(
        default=None,
        description="Playwright DeviceProfile veya {platform, name, os} dict",
    )
    app: Optional[dict[str, Any]] = Field(
        default=None, description="APK/IPA meta — package, name, upload_id"
    )
    max_steps: int = Field(default=8, ge=3, le=15)


class MobileGenerateResponse(BaseModel):
    gherkin: str
    matched_action_ids: list[str] = Field(default_factory=list)
    unknown_steps: list[str] = Field(default_factory=list)
    used_model: Optional[str] = None
    device_label: Optional[str] = None
    mobile_alias_count: int = 0


@dataclass
class _AllowedAliases:
    tr: list[str]
    en: list[str]
    action_ids: list[str]


# ── Yardımcılar ────────────────────────────────────────────────────────────


def _collect_mobile_aliases() -> _AllowedAliases:
    """Kataloğun `mobile.*` kategorisindeki tüm cümleciklerin alias listesi."""
    catalog_cache.ensure_loaded()
    tr: list[str] = []
    en: list[str] = []
    action_ids: list[str] = []
    for a in catalog_cache.all():
        cat = (a.category or "").split(".", 1)[0]
        if cat != "mobile":
            continue
        action_ids.append(a.id)
        for alias in (a.aliases or {}).get("tr") or []:
            tr.append(alias)
        for alias in (a.aliases or {}).get("en") or []:
            en.append(alias)
    return _AllowedAliases(tr=tr, en=en, action_ids=action_ids)


def _device_label(device: Optional[dict[str, Any]]) -> str:
    if not device:
        return "genel mobil cihaz"
    parts = [
        str(device.get("name") or device.get("slug") or ""),
        str(device.get("os") or ""),
        str(device.get("platform") or ""),
    ]
    label = " · ".join([p for p in parts if p]).strip(" ·")
    return label or "mobil cihaz"


def _app_label(app: Optional[dict[str, Any]]) -> Optional[str]:
    if not app:
        return None
    if isinstance(app, dict):
        return (
            app.get("name")
            or app.get("package")
            or app.get("filename")
            or None
        )
    return str(app)


def _match_gherkin_with_dsl(gherkin: str) -> tuple[list[str], list[str]]:
    """Gherkin içindeki her adımı DSL search ile eşleştir.

    `_match_gherkin_with_dsl` ile paraleldir ama bu sürüm mobile odaklı,
    sadece match açısından çalışır.
    """
    matched: list[str] = []
    unknown: list[str] = []
    seen: set[str] = set()
    if not gherkin:
        return matched, unknown
    for m in _GHERKIN_STEP_RE.finditer(gherkin):
        step_text = m.group(2).strip()
        if not step_text:
            continue
        normalized = re.sub(r'"[^"]*"', "{text}", step_text)
        hits = search_actions(normalized, limit=1)
        if hits.items:
            aid = hits.items[0].action.id
            if aid not in seen:
                matched.append(aid)
                seen.add(aid)
        else:
            unknown.append(step_text)
    return matched, unknown


# ── Ana akış ───────────────────────────────────────────────────────────────


def generate_mobile_scenario(req: MobileGenerateRequest) -> MobileGenerateResponse:
    allowed = _collect_mobile_aliases()
    if not allowed.action_ids:
        raise RuntimeError(
            "Mobil katalog boş — 'packages/dsl/catalog/mobile-actions.yaml' yüklenmiş mi?"
        )

    device_label = _device_label(req.device)
    app_label = _app_label(req.app)

    payload = {
        "description": req.description,
        "device": {
            "platform": (req.device or {}).get("platform"),
            "name": (req.device or {}).get("name"),
            "os": (req.device or {}).get("os"),
        },
        "app": {"name": app_label} if app_label else None,
        "allowed_aliases": {"tr": allowed.tr, "en": allowed.en},
        "max_steps": req.max_steps,
    }

    user_message = (
        "Mobil cihazda çalışacak bir test senaryosu yaz.\n"
        f"Cihaz: {device_label}\n"
        f"Uygulama: {app_label or '(belirtilmedi)'}\n"
        f"Kullanıcı isteği: {req.description}\n\n"
        "SADECE aşağıdaki allowed_aliases listesindeki cümlelerle kur. "
        "Tırnak içindeki yer tutucuları ({selector}, {direction}, vb.) gerçek "
        "değerlerle doldur. Markdown kod çiti (```) KULLANMA.\n\n"
        f"BAĞLAM: {json.dumps(payload, ensure_ascii=False)}"
    )

    try:
        raw = gateway_complete(
            task_type="mobile_scenario",
            user_message=user_message,
            temperature=0.35,
            max_tokens=1200,
        )
    except RuntimeError as exc:
        raise RuntimeError(f"AI Gateway hatası: {exc}") from exc

    gherkin = _strip_markdown_fence(raw).strip()
    if not gherkin:
        raise RuntimeError("AI boş Gherkin döndü")

    matched, unknown = _match_gherkin_with_dsl(gherkin)
    return MobileGenerateResponse(
        gherkin=gherkin,
        matched_action_ids=matched,
        unknown_steps=unknown,
        used_model=None,
        device_label=device_label,
        mobile_alias_count=len(allowed.action_ids),
    )


def _strip_markdown_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        # ```gherkin\n...\n``` → içi
        lines = text.splitlines()
        if len(lines) >= 2:
            if lines[-1].startswith("```"):
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            return "\n".join(lines).strip()
    return text
