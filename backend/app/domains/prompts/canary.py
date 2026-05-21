"""Canary trafik dağıtımı — deterministik, test edilebilir.

``should_canary(tenant, prompt_id, pct)`` → bool.

Uygulama:
    sha1(tenant + ':' + prompt_id) ilk 8 hex → int → % 100. Sonuç < pct ise
    canary. Aynı tenant + prompt hep aynı karara düşer (UI flicker önlenir).
    ``tenant`` None/boş ise False (anonim canary'e alınmaz).

Feature-flag modülündeki canary pattern'inin aynısı — ama bağımsız tutuldu
(prompt canary rollout ayrı bir lifecycle, flag'lerden de bağımsız olabilir).
"""
from __future__ import annotations

import hashlib
from typing import Optional


def canary_bucket(tenant_id: str, prompt_id: str) -> int:
    raw = f"{tenant_id}:{prompt_id}".encode("utf-8")
    return int(hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:8], 16) % 100


def should_canary(
    tenant_id: Optional[str], prompt_id: str, pct: int
) -> bool:
    if pct <= 0:
        return False
    if pct >= 100:
        # Anonim tenant bile %100 canary'ye girer
        return True
    if not tenant_id:
        return False
    return canary_bucket(tenant_id, prompt_id) < pct
