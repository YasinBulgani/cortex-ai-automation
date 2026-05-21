"""Eval harness için çekirdek tipleri.

Tasarım notu:
    * ``EvalCase`` ve ``Suite`` YAML'den yüklenen statik veriyi temsil eder,
      immutable (frozen dataclass) olmaları YAML → Python → YAML round-trip
      garanti etmez ama **runtime'da test case mutasyonunu önler**.
    * ``CaseResult`` ve ``SuiteResult`` runtime'da üretilir, ``BaseModel``
      seçildi çünkü JSON raporuna bire bir serialize edilecek.
    * ``ScorerOutput`` içindeki ``value`` 0..1 aralığındadır (threshold
      karşılaştırması standart bir eşik sisteminde yapılsın diye). Boolean
      scorerler de ``value=1.0 if passed else 0.0`` şeklinde raporlanır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field


# ── Statik (YAML) tipler ──────────────────────────────────────────────────


@dataclass(frozen=True)
class EvalCase:
    """Tek bir test vakası. YAML'de bir liste elemanı olarak görünür."""

    id: str
    inputs: Dict[str, Any]
    expected: Dict[str, Any]
    tags: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EvalCase":
        if "id" not in raw or not str(raw["id"]).strip():
            raise ValueError("EvalCase.id zorunlu ve boş olamaz")
        return cls(
            id=str(raw["id"]),
            inputs=dict(raw.get("inputs") or {}),
            expected=dict(raw.get("expected") or {}),
            tags=tuple(raw.get("tags") or ()),
            description=str(raw.get("description") or ""),
        )


@dataclass(frozen=True)
class SuiteThresholds:
    """Suite'in toplam skoru için eşikler.

    Anahtar = scorer adı veya aggregate metrik adı (ör. ``precision_at_1``,
    ``mrr``, ``exact_match``). Değer = minimum ortalama skor.

    Suite PASS olabilmesi için **tüm** belirtilen eşikler aşılmalı.
    Boş dict → sadece her case'in kendi pass durumu toplulaştırılır
    (``overall_case_pass_rate >= 1.0`` yani hepsi geçmeli).
    """

    mean_thresholds: Dict[str, float] = field(default_factory=dict)
    min_case_pass_rate: float = 1.0

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "SuiteThresholds":
        if not raw:
            return cls()
        raw_mean: Dict[str, Any] = dict(raw.get("mean") or {})
        mean = {k: float(v) for k, v in raw_mean.items()}
        return cls(
            mean_thresholds=mean,
            min_case_pass_rate=float(raw.get("min_case_pass_rate", 1.0)),
        )


@dataclass(frozen=True)
class Suite:
    """Çalıştırılabilir bir eval suite'i.

    ``adapter_name`` runtime'da kayıtlı adapter registry'sinden çözümlenir
    — bu, YAML dosyasının Python import'una bağımlı olmamasını sağlar.
    """

    name: str
    adapter_name: str
    cases: tuple[EvalCase, ...]
    scorers: tuple[str, ...]
    thresholds: SuiteThresholds = field(default_factory=SuiteThresholds)
    description: str = ""

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Suite":
        if "name" not in raw or not str(raw["name"]).strip():
            raise ValueError("Suite.name zorunlu")
        if "adapter" not in raw or not str(raw["adapter"]).strip():
            raise ValueError("Suite.adapter zorunlu")
        raw_cases = raw.get("cases") or []
        if not isinstance(raw_cases, list) or not raw_cases:
            raise ValueError(f"Suite '{raw.get('name')}' en az bir case içermeli")
        cases = tuple(EvalCase.from_dict(c) for c in raw_cases)
        scorers_raw = raw.get("scorers") or []
        if not isinstance(scorers_raw, list) or not scorers_raw:
            raise ValueError(f"Suite '{raw.get('name')}' en az bir scorer içermeli")
        return cls(
            name=str(raw["name"]),
            adapter_name=str(raw["adapter"]),
            cases=cases,
            scorers=tuple(str(s) for s in scorers_raw),
            thresholds=SuiteThresholds.from_dict(raw.get("thresholds")),
            description=str(raw.get("description") or ""),
        )


# ── Runtime (Result) tipleri ──────────────────────────────────────────────


class ScorerOutput(BaseModel):
    """Tek scorer'ın bir case üstündeki sonucu.

    ``value`` 0..1 (ortalanabilir), ``passed`` genelde ``value == 1.0``
    veya custom eşik. ``details`` debug için free-form.
    """

    name: str
    value: float = Field(ge=0.0, le=1.0)
    passed: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class CaseResult(BaseModel):
    """Bir case'in tüm scorer skorları + çalışma metadata'sı."""

    case_id: str
    passed: bool  # Tüm scorer'lar geçtiyse True
    scores: List[ScorerOutput] = Field(default_factory=list)
    latency_ms: int = 0
    actual: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class SuiteResult(BaseModel):
    """Bir suite çalıştırmasının tam raporu — JSON'a serialize edilir."""

    suite_name: str
    adapter_name: str
    cases: List[CaseResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    passed: bool = False  # Suite seviyesi threshold'lar geçtiyse True
    aggregate: Dict[str, float] = Field(default_factory=dict)
    threshold_failures: List[str] = Field(default_factory=list)
    total_latency_ms: int = 0

    def case_pass_rate(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 for c in self.cases if c.passed) / len(self.cases)

    def count_passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)


# ── Protokoller (extension points) ─────────────────────────────────────────


@runtime_checkable
class Scorer(Protocol):
    """Bir scorer saf fonksiyondur: (expected, actual) → ScorerOutput."""

    name: str

    def score(
        self, *, case: EvalCase, actual: Dict[str, Any]
    ) -> ScorerOutput:  # pragma: no cover - protocol
        ...


@runtime_checkable
class Adapter(Protocol):
    """Adapter SUT'a (system-under-test) çağrı yapıp ``actual`` döndürür.

    ``available()`` False dönerse runner suite'i **skip** eder (error değil).
    Bu, gateway/network/model bağımlılığı olan suite'lerin CI'da graceful
    atlanmasını sağlar.
    """

    name: str

    def available(self) -> bool:  # pragma: no cover - protocol
        ...

    def run(
        self, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:  # pragma: no cover - protocol
        ...
