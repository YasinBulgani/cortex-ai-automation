"""KVKK/BDDK compliance mapping — kontrol → feature → kanıt testi.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §5 / E3.6.

Amaç:
    Bir denetim durumunda "şu KVKK maddesini hangi feature karşılıyor, hangi
    test bunu kanıtlıyor" matrisini otomatik üret. Tek kaynak (bu modül)
    → pytest marker + CLI rapor + JSON/HTML evidence pack.

Kullanım:
    pytest -m "compliance:kvkk-15" tests/          # KVKK md.15 ile ilişkili testler
    python -m app.domains.compliance.cli --export out.json

Test tagging:
    @pytest.mark.compliance("kvkk-15", "bddk-art-12")
    def test_audit_retention_7y(): ...

    pytest.ini'de marker register edilir.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Kontrol tanımları ────────────────────────────────────────────────────


@dataclass(frozen=True)
class Control:
    """Bir regülasyon maddesi."""

    id: str                       # "kvkk-15", "bddk-art-12", "iso27001-a.9.2.1"
    standard: str                 # "KVKK" | "BDDK" | "ISO27001" | "SOC2"
    article: str                  # "Madde 15", "Article 12", "A.9.2.1"
    title: str                    # Kısa başlık
    description: str              # Maddenin özü
    risk_level: str = "medium"    # "low" | "medium" | "high" | "critical"


@dataclass(frozen=True)
class Mapping:
    """Bir kontrolü karşılayan feature + kanıtlayan test."""

    control_id: str
    feature_name: str             # "audit.hash_chain", "ai.prompt_shield"
    feature_module: str           # "backend/app/domains/audit/chain.py"
    test_marker: str              # "kvkk-15"
    test_location: str            # "tests/unit/test_audit_chain.py"
    notes: str = ""


# ── Veri — tek kaynak, kod içinde (git history audit'i için) ────────────


CONTROLS: tuple[Control, ...] = (
    # ── KVKK ────────────────────────────────────────────────────────────
    Control(
        id="kvkk-md-5",
        standard="KVKK",
        article="Madde 5",
        title="Kişisel verilerin işlenme şartları",
        description=(
            "Açık rıza ve/veya kanunun öngördüğü hallerde işleme. "
            "Sentetik veri kullanımı gerçek veri işleme riskini azaltır."
        ),
        risk_level="critical",
    ),
    Control(
        id="kvkk-md-6",
        standard="KVKK",
        article="Madde 6",
        title="Özel nitelikli kişisel veriler",
        description="Sağlık, cinsel hayat, din, ceza vb. özel nitelikli veriler için ek koruma.",
        risk_level="high",
    ),
    Control(
        id="kvkk-md-12",
        standard="KVKK",
        article="Madde 12",
        title="Veri güvenliği",
        description="Hukuka aykırı erişim, ifşa, değiştirmeyi önleme yükümlülüğü.",
        risk_level="critical",
    ),
    Control(
        id="kvkk-md-15",
        standard="KVKK",
        article="Madde 15",
        title="İlgili kişinin hakları ve veri sahibinin talep süreci",
        description="Veri sahibinin bilgi alma, silme, düzeltme haklarının audit edilebilirliği.",
        risk_level="high",
    ),
    # ── BDDK ────────────────────────────────────────────────────────────
    Control(
        id="bddk-bgy-6",
        standard="BDDK",
        article="BGY Madde 6",
        title="Bilgi sistemleri denetim kayıtları",
        description="Kritik işlemler için değiştirilemez (tamper-evident) log tutma.",
        risk_level="critical",
    ),
    Control(
        id="bddk-bgy-12",
        standard="BDDK",
        article="BGY Madde 12",
        title="Görevler ayrılığı (SoD)",
        description="Aynı kullanıcı kritik bir işlemi hem yapan hem onaylayan olamaz.",
        risk_level="high",
    ),
    Control(
        id="bddk-bgy-14",
        standard="BDDK",
        article="BGY Madde 14",
        title="Test ortamlarında gerçek veri kullanımı",
        description="Üretim dışı ortamlarda gerçek müşteri verisi kullanılmamalı veya maskelenmeli.",
        risk_level="critical",
    ),
    # ── ISO 27001 (destekleyici) ────────────────────────────────────────
    Control(
        id="iso27001-a.9.2.3",
        standard="ISO27001",
        article="A.9.2.3",
        title="Privileged access rights",
        description="Ayrıcalıklı erişim haklarının kısıtlanması ve izlenmesi.",
        risk_level="high",
    ),
    Control(
        id="iso27001-a.12.4.1",
        standard="ISO27001",
        article="A.12.4.1",
        title="Event logging",
        description="Event log'ların üretilmesi, korunması, düzenli gözden geçirilmesi.",
        risk_level="high",
    ),
    Control(
        id="iso27001-a.14.3.1",
        standard="ISO27001",
        article="A.14.3.1",
        title="Protection of test data",
        description="Test verisinin dikkatle seçilmesi, korunması ve kontrollü kullanımı.",
        risk_level="medium",
    ),
)


MAPPINGS: tuple[Mapping, ...] = (
    # KVKK md-5 ve BDDK-bgy-14 → sentetik veri + PII scanner
    Mapping(
        control_id="kvkk-md-5",
        feature_name="synthetic_data",
        feature_module="backend/app/domains/ai_synthetic_data/",
        test_marker="kvkk-md-5",
        test_location="backend/tests/unit/test_privacy_scanner.py",
        notes="Sentetik veri üretimi ile gerçek veri işleme gereği azaltılır",
    ),
    Mapping(
        control_id="kvkk-md-5",
        feature_name="privacy_scanner",
        feature_module="backend/app/domains/ai_synthetic_data/privacy_scanner.py",
        test_marker="kvkk-md-5",
        test_location="backend/tests/unit/test_privacy_scanner.py",
        notes="TCKN/IBAN checksum + k-anon ile sentetik veri gerçek veriye benzerliği test edilir",
    ),
    Mapping(
        control_id="bddk-bgy-14",
        feature_name="privacy_scanner",
        feature_module="backend/app/domains/ai_synthetic_data/privacy_scanner.py",
        test_marker="bddk-bgy-14",
        test_location="backend/tests/unit/test_privacy_scanner.py",
    ),
    # KVKK md-12 + BDDK-bgy-6 + ISO A.12.4.1 → audit hash-chain
    Mapping(
        control_id="kvkk-md-12",
        feature_name="audit_hash_chain",
        feature_module="backend/app/domains/audit/chain.py",
        test_marker="kvkk-md-12",
        test_location="backend/tests/unit/test_audit_chain.py",
        notes="Tamper-evident log — değişim tespiti guaranteed",
    ),
    Mapping(
        control_id="bddk-bgy-6",
        feature_name="audit_hash_chain",
        feature_module="backend/app/domains/audit/chain.py",
        test_marker="bddk-bgy-6",
        test_location="backend/tests/unit/test_audit_chain.py",
    ),
    Mapping(
        control_id="iso27001-a.12.4.1",
        feature_name="audit_hash_chain",
        feature_module="backend/app/domains/audit/chain.py",
        test_marker="iso27001-a.12.4.1",
        test_location="backend/tests/unit/test_audit_chain.py",
    ),
    # KVKK md-15 → audit chain + retention (7y)
    Mapping(
        control_id="kvkk-md-15",
        feature_name="audit_hash_chain",
        feature_module="backend/app/domains/audit/chain.py",
        test_marker="kvkk-md-15",
        test_location="backend/tests/unit/test_audit_chain.py",
        notes="Veri sahibinin hakları için bilgi alma/değişiklik audit kayıtları",
    ),
    # BDDK-bgy-12 + ISO A.9.2.3 → RBAC + SoD
    Mapping(
        control_id="bddk-bgy-12",
        feature_name="rbac_sod",
        feature_module="backend/app/domains/rbac/policy.py",
        test_marker="bddk-bgy-12",
        test_location="backend/tests/unit/test_rbac_policy.py",
        notes="Segregation of Duties — aynı actor çatışan aksiyonları yapamaz",
    ),
    Mapping(
        control_id="iso27001-a.9.2.3",
        feature_name="rbac_sod",
        feature_module="backend/app/domains/rbac/policy.py",
        test_marker="iso27001-a.9.2.3",
        test_location="backend/tests/unit/test_rbac_policy.py",
    ),
    # ISO A.14.3.1 → sentetik veri + privacy scanner
    Mapping(
        control_id="iso27001-a.14.3.1",
        feature_name="privacy_scanner",
        feature_module="backend/app/domains/ai_synthetic_data/privacy_scanner.py",
        test_marker="iso27001-a.14.3.1",
        test_location="backend/tests/unit/test_privacy_scanner.py",
    ),
    # KVKK md-6 + md-12 → prompt shield (hassas veri sızıntısı önleme)
    Mapping(
        control_id="kvkk-md-6",
        feature_name="prompt_shield",
        feature_module="backend/app/domains/ai/prompt_shield.py",
        test_marker="kvkk-md-6",
        test_location="backend/tests/unit/test_prompt_shield.py",
        notes="Prompt injection ile hassas veri sızması önlenir",
    ),
    Mapping(
        control_id="kvkk-md-12",
        feature_name="prompt_shield",
        feature_module="backend/app/domains/ai/prompt_shield.py",
        test_marker="kvkk-md-12",
        test_location="backend/tests/unit/test_prompt_shield.py",
    ),
)


# ── Sorgu API ────────────────────────────────────────────────────────────


def get_control(control_id: str) -> Optional[Control]:
    for c in CONTROLS:
        if c.id == control_id:
            return c
    return None


def list_controls(standard: Optional[str] = None) -> List[Control]:
    if standard is None:
        return list(CONTROLS)
    return [c for c in CONTROLS if c.standard.lower() == standard.lower()]


def mappings_for(control_id: str) -> List[Mapping]:
    return [m for m in MAPPINGS if m.control_id == control_id]


def controls_for_feature(feature_name: str) -> List[Control]:
    ids = {m.control_id for m in MAPPINGS if m.feature_name == feature_name}
    return [c for c in CONTROLS if c.id in ids]


def unmapped_controls() -> List[Control]:
    """Hiçbir mapping'i olmayan kontroller — coverage gap raporu."""
    mapped = {m.control_id for m in MAPPINGS}
    return [c for c in CONTROLS if c.id not in mapped]


def all_markers() -> List[str]:
    """pytest.ini'ye register edilecek ``compliance:<id>`` marker'ları."""
    return sorted({f"compliance:{m.test_marker}" for m in MAPPINGS})


# ── Evidence pack ────────────────────────────────────────────────────────


def build_evidence_pack() -> Dict[str, object]:
    """Denetim için tek tıklama indirilebilir JSON."""
    return {
        "generated_standards": sorted({c.standard for c in CONTROLS}),
        "controls": [asdict(c) for c in CONTROLS],
        "mappings": [asdict(m) for m in MAPPINGS],
        "unmapped": [asdict(c) for c in unmapped_controls()],
        "coverage_pct": round(
            100.0 * (1 - len(unmapped_controls()) / max(1, len(CONTROLS))), 2
        ),
    }


def export_evidence(target: Path) -> Path:
    """Evidence pack JSON'u diske yaz, path döner."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_evidence_pack(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target
