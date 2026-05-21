"""Referans tablolar — TCMB banks, MCC codes, vb."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_REFERENCE_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def _load_json(filename: str) -> dict[str, Any]:
    path = _REFERENCE_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def tcmb_banks() -> dict[str, dict[str, str]]:
    """TR banka kodları (5-dijit) → detay."""
    return _load_json("tcmb_banks.json")


def mcc_codes() -> dict[str, dict[str, str]]:
    """MCC kodları (4-dijit) → kategori."""
    return _load_json("mcc_codes.json")


def bank_info(code: str) -> dict[str, str] | None:
    """Bankanın detayı (code → name/short/type/swift)."""
    return tcmb_banks().get(code)


def mcc_info(code: str) -> dict[str, str] | None:
    """MCC'nin detayı."""
    return mcc_codes().get(code)


def list_banks_by_type(bank_type: str) -> list[tuple[str, dict[str, str]]]:
    """type: 'kamu' | 'özel' | 'katılım' | 'yabancı' | 'dijital' | 'kalkınma'"""
    return [
        (code, info)
        for code, info in tcmb_banks().items()
        if info.get("type") == bank_type
    ]


def list_high_risk_mcc() -> list[tuple[str, dict[str, str]]]:
    """Yüksek risk MCC'leri (fraud pattern'larında öncelikli)."""
    return [
        (code, info)
        for code, info in mcc_codes().items()
        if info.get("risk") == "high"
    ]


__all__ = [
    "tcmb_banks",
    "mcc_codes",
    "bank_info",
    "mcc_info",
    "list_banks_by_type",
    "list_high_risk_mcc",
]
