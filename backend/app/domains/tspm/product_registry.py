"""Product runtime registry shared by the TSPM project core."""

from __future__ import annotations

from typing import Final

PRODUCT_DEFAULT_ENTRY_KEYS: Final[dict[str, str]] = {
    "one": "settings",
    "studio": "import",
    "service": "api-testing",
    "web": "manual-to-automation",
    "mobile": "mobile",
    "data": "synthetic",
    "intelligence": "ai-metrics",
    "nexus-code": "project-overview",
}

VALID_PRODUCT_IDS: Final[set[str]] = set(PRODUCT_DEFAULT_ENTRY_KEYS)
DEFAULT_PRODUCT_ID: Final[str] = "one"


def normalize_product_id(value: str | None) -> str:
    candidate = (value or DEFAULT_PRODUCT_ID).strip()
    return candidate if candidate in VALID_PRODUCT_IDS else DEFAULT_PRODUCT_ID


def validate_product_id(value: str) -> str:
    candidate = value.strip()
    if candidate not in VALID_PRODUCT_IDS:
        allowed = ", ".join(sorted(VALID_PRODUCT_IDS))
        raise ValueError(f"Geçersiz ürün kimliği: {candidate}. İzin verilenler: {allowed}")
    return candidate


def normalize_product_tags(values: list[str] | None, *, primary: str | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    primary_id = normalize_product_id(primary)
    for raw in values or []:
        product_id = validate_product_id(str(raw))
        if product_id == primary_id or product_id in seen:
            continue
        seen.add(product_id)
        result.append(product_id)
    return result


def default_entry_key_for(product_id: str | None) -> str:
    return PRODUCT_DEFAULT_ENTRY_KEYS[normalize_product_id(product_id)]
