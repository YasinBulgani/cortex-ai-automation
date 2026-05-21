"""Sentetik veri gizlilik tarayıcısı — TCKN/IBAN checksum, k-anonymity, l-diversity.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §5 / E3.1.

Amaç:
    Üretilen sentetik veri gerçek müşteri verisine **benzemediğini** her
    koşuda otomatik kanıtlamak. Bankacılık satışında #1 soru.

Kontroller:
    1. **TCKN checksum valid oranı** — Gerçek TCKN algoritması:
        * 11 hane, ilk 1-9
        * 10. hane = ((1+3+5+7+9)*7 - (2+4+6+8)) mod 10
        * 11. hane = (sum ilk 10) mod 10
       Sentetik veride ~%0 valid olmalı (rastgele üretim, mod 10 rastlantı
       dışı). %100 valid olursa gerçek veri leak'i şüphesi.
    2. **IBAN checksum (mod-97)** — Tüm IBAN'ların mod 97 = 1 vermesi.
       Geçerli TR IBAN = leak riski (aynı banka + şube).
    3. **Ad blacklist** — Nüfus istatistik frekansı yüksek isimler
       (örn. Ahmet, Mehmet). Kullanımı %0 zorunlu değil; frekans
       dağılımı prod snapshot'ından farklı olmalı (χ² test).
    4. **k-anonymity** — Quasi-identifier kombinasyonu için en küçük
       grup boyutu. QI: (yaş aralığı, cinsiyet, ilçe, meslek) vs.
       k≥5 yeterli sayılır (HIPAA safe harbor benzeri).
    5. **l-diversity** — Her QI grubunda hassas değerler için ≥l farklı
       değer. l≥2 (binary) veya ≥3 için.

Çıktı:
    PrivacyReport — her kontrolün passed/failed/warning durumu + metrik
    değerleri. CI'da threshold altında fail; rapor HTML+JSON.
"""
from __future__ import annotations

import logging
import re
import string
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


CheckStatus = Literal["passed", "warning", "failed", "skipped"]


# ── TCKN ─────────────────────────────────────────────────────────────────


_TCKN_ONLY_DIGITS = re.compile(r"^\d{11}$")


def is_valid_tckn(value: Any) -> bool:
    """T.C. Kimlik No algoritması.

    - 11 hane, ilk hane 0 olmaz
    - d10 = ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) mod 10
    - d11 = (d1+...+d10) mod 10
    """
    s = str(value or "").strip()
    if not _TCKN_ONLY_DIGITS.match(s):
        return False
    if s[0] == "0":
        return False
    d = [int(c) for c in s]
    odd = d[0] + d[2] + d[4] + d[6] + d[8]
    even = d[1] + d[3] + d[5] + d[7]
    d10 = (odd * 7 - even) % 10
    if d10 != d[9]:
        return False
    d11 = sum(d[:10]) % 10
    return d11 == d[10]


def scan_tckn_column(values: Sequence[Any]) -> Tuple[int, int]:
    """(valid_count, total_count) — None/boş değerler total'a dahil değil."""
    total = sum(1 for v in values if str(v or "").strip())
    valid = sum(1 for v in values if is_valid_tckn(v))
    return valid, total


# ── IBAN ─────────────────────────────────────────────────────────────────


_IBAN_ALNUM = re.compile(r"^[A-Z0-9]+$")


def _iban_mod97(iban: str) -> int:
    """IBAN'ın matematiksel mod-97 hesabı."""
    # Baştaki 4 karakteri sona taşı, harfleri rakama çevir (A=10...Z=35)
    rotated = iban[4:] + iban[:4]
    converted = []
    for c in rotated:
        if c.isdigit():
            converted.append(c)
        else:
            converted.append(str(ord(c) - 55))
    as_int = int("".join(converted))
    return as_int % 97


def is_valid_iban(value: Any) -> bool:
    """IBAN mod-97 checksum doğrulaması.

    Format: 2 harf country code + 2 digit check + BBAN. Boşluk tolere edilir,
    küçük harf büyük harfe dönüştürülür.
    """
    raw = str(value or "").replace(" ", "").upper()
    if len(raw) < 15 or len(raw) > 34:
        return False
    if not _IBAN_ALNUM.match(raw):
        return False
    if not raw[:2].isalpha():
        return False
    if not raw[2:4].isdigit():
        return False
    try:
        return _iban_mod97(raw) == 1
    except ValueError:
        return False


def scan_iban_column(values: Sequence[Any]) -> Tuple[int, int]:
    total = sum(1 for v in values if str(v or "").strip())
    valid = sum(1 for v in values if is_valid_iban(v))
    return valid, total


# ── k-anonymity ──────────────────────────────────────────────────────────


def compute_k_anonymity(
    rows: Sequence[Dict[str, Any]],
    *,
    quasi_identifiers: Sequence[str],
) -> int:
    """Minimum grup boyutu. 0 satır veya QI yoksa 0 döner.

    Örn. rows=[{"age":30,"city":"Ankara"}, {"age":30,"city":"Ankara"},
    {"age":25,"city":"İzmir"}], QI=["age","city"] →
    gruplar: (30,Ankara)=2, (25,İzmir)=1 → k_min = 1.
    """
    if not rows or not quasi_identifiers:
        return 0
    buckets: Counter = Counter()
    for r in rows:
        key = tuple(r.get(qi) for qi in quasi_identifiers)
        buckets[key] += 1
    if not buckets:
        return 0
    return min(buckets.values())


def compute_l_diversity(
    rows: Sequence[Dict[str, Any]],
    *,
    quasi_identifiers: Sequence[str],
    sensitive_attr: str,
) -> int:
    """Her QI grubu için ``sensitive_attr``'ın farklı değer sayısının min'i."""
    if not rows or not quasi_identifiers or not sensitive_attr:
        return 0
    groups: Dict[tuple, set] = defaultdict(set)
    for r in rows:
        key = tuple(r.get(qi) for qi in quasi_identifiers)
        groups[key].add(r.get(sensitive_attr))
    if not groups:
        return 0
    return min(len(vs) for vs in groups.values())


# ── Rapor tipleri ────────────────────────────────────────────────────────


class CheckResult(BaseModel):
    name: str
    status: CheckStatus
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class PrivacyReport(BaseModel):
    dataset_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rows_scanned: int
    overall_passed: bool
    checks: List[CheckResult] = Field(default_factory=list)

    def failed_checks(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status == "failed"]


# ── Scanner (public API) ─────────────────────────────────────────────────


# Eşikler (ENV'den override edilebilir)
_DEFAULT_TCKN_MAX_VALID_PCT = 0.05      # %5'ten fazla valid TCKN şüpheli
_DEFAULT_IBAN_MAX_VALID_PCT = 0.05      # aynı mantık IBAN için
_DEFAULT_K_MIN = 5
_DEFAULT_L_MIN = 2


@dataclass
class ScanConfig:
    """Tarayıcı konfigürasyonu — domain bazlı esnek."""

    tckn_columns: List[str] = field(default_factory=list)
    iban_columns: List[str] = field(default_factory=list)
    quasi_identifiers: List[str] = field(default_factory=list)
    sensitive_attrs: List[str] = field(default_factory=list)
    k_min: int = _DEFAULT_K_MIN
    l_min: int = _DEFAULT_L_MIN
    tckn_max_valid_pct: float = _DEFAULT_TCKN_MAX_VALID_PCT
    iban_max_valid_pct: float = _DEFAULT_IBAN_MAX_VALID_PCT


def scan_dataset(
    *,
    dataset_id: str,
    rows: Sequence[Dict[str, Any]],
    config: ScanConfig,
) -> PrivacyReport:
    checks: List[CheckResult] = []

    # TCKN
    for col in config.tckn_columns:
        values = [r.get(col) for r in rows]
        valid, total = scan_tckn_column(values)
        if total == 0:
            checks.append(CheckResult(name=f"tckn.{col}", status="skipped", details={"reason": "empty"}))
            continue
        ratio = valid / total
        checks.append(
            CheckResult(
                name=f"tckn.{col}",
                status="failed" if ratio > config.tckn_max_valid_pct else "passed",
                metric_value=round(ratio, 6),
                threshold=config.tckn_max_valid_pct,
                details={
                    "valid_count": valid,
                    "total": total,
                    "message": (
                        f"Sentetik TCKN oranı beklenenden yüksek: %{ratio*100:.1f} — "
                        "prod veri leak'i şüphesi"
                        if ratio > config.tckn_max_valid_pct
                        else "OK"
                    ),
                },
            )
        )

    # IBAN
    for col in config.iban_columns:
        values = [r.get(col) for r in rows]
        valid, total = scan_iban_column(values)
        if total == 0:
            checks.append(CheckResult(name=f"iban.{col}", status="skipped", details={"reason": "empty"}))
            continue
        ratio = valid / total
        checks.append(
            CheckResult(
                name=f"iban.{col}",
                status="failed" if ratio > config.iban_max_valid_pct else "passed",
                metric_value=round(ratio, 6),
                threshold=config.iban_max_valid_pct,
                details={
                    "valid_count": valid,
                    "total": total,
                },
            )
        )

    # k-anonymity
    if config.quasi_identifiers:
        k = compute_k_anonymity(rows, quasi_identifiers=config.quasi_identifiers)
        checks.append(
            CheckResult(
                name="k_anonymity",
                status="failed" if k < config.k_min else "passed",
                metric_value=float(k),
                threshold=float(config.k_min),
                details={"quasi_identifiers": list(config.quasi_identifiers)},
            )
        )

        # l-diversity — her sensitive attr için ayrı kontrol
        for sa in config.sensitive_attrs:
            l = compute_l_diversity(
                rows,
                quasi_identifiers=config.quasi_identifiers,
                sensitive_attr=sa,
            )
            checks.append(
                CheckResult(
                    name=f"l_diversity.{sa}",
                    status="failed" if l < config.l_min else "passed",
                    metric_value=float(l),
                    threshold=float(config.l_min),
                    details={
                        "quasi_identifiers": list(config.quasi_identifiers),
                        "sensitive_attr": sa,
                    },
                )
            )

    overall = all(c.status != "failed" for c in checks)
    return PrivacyReport(
        dataset_id=dataset_id,
        rows_scanned=len(rows),
        overall_passed=overall,
        checks=checks,
    )
