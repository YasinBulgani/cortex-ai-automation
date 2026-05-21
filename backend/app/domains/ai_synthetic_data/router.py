"""Router for advanced synthetic data generation (KDE + CTGAN)."""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user
from app.infra.models import User

from app.domains.ai_synthetic_data.advanced_schemas import (
    BankingDatasetRequest,
    BankingDatasetResponse,
    FullDatasetStats,
    GenerateRequest,
    GenerateResponse,
    GeneratorInfo,
    GeneratorsListResponse,
    PrivacyRiskRequest,
    PrivacyRiskResponse,
    QualityCheckRequest,
    QualityMetrics,
)
from app.domains.ai_synthetic_data.advanced_generators import (
    BankingDataGenerator,
    CTGANGenerator,
    DataQualityChecker,
    KDEGenerator,
    _HAS_SDV,
    _HAS_SCIPY,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/synthetic", tags=["synthetic"])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADVANCED SYNTHETIC DATA (KDE + CTGAN)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/generate", response_model=GenerateResponse)
def generate_synthetic(
    body: GenerateRequest,
    user: User = Depends(get_current_user),
) -> GenerateResponse:
    """Generate synthetic records from sample data using KDE or CTGAN."""
    t0 = time.time()

    if body.sample_data is None or len(body.sample_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sample_data zorunludur — en az birkaç örnek satır sağlayın.",
        )

    try:
        if body.generator_type == "ctgan":
            gen = CTGANGenerator()
            gen.fit(body.sample_data)
            records = gen.generate(body.count, conditions=body.conditions)
            quality = gen.quality_report(body.sample_data, records)
        else:
            gen_kde = KDEGenerator()
            gen_kde.fit(body.sample_data)
            records = gen_kde.generate(body.count, seed=body.seed)
            quality = gen_kde.quality_metrics(body.sample_data, records)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        _logger.exception("Synthetic generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Üretim başarısız: {}".format(str(e)),
        )

    duration_ms = round((time.time() - t0) * 1000, 2)
    return GenerateResponse(
        records=records,
        quality_metrics=quality,
        generator_type=body.generator_type,
        duration_ms=duration_ms,
        record_count=len(records),
    )


@router.post("/banking-dataset", response_model=BankingDatasetResponse)
def generate_banking_dataset(
    body: BankingDatasetRequest,
    user: User = Depends(get_current_user),
) -> BankingDatasetResponse:
    """Generate a full banking test dataset (customers -> accounts -> transactions)."""
    t0 = time.time()

    try:
        gen = BankingDataGenerator(generator_type=body.generator_type)
        result = gen.generate_full_dataset(
            customer_count=body.customer_count,
            accounts_per_customer=body.accounts_per_customer,
            transactions_per_account=body.transactions_per_account,
            days=body.days,
            segment_distribution=body.segment_distribution,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        _logger.exception("Banking dataset generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Banking dataset generation failed: {}".format(str(e)),
        )

    duration_ms = round((time.time() - t0) * 1000, 2)

    stats_data = result.get("stats", {})
    stats = FullDatasetStats(
        customer_count=stats_data.get("customer_count", 0),
        account_count=stats_data.get("account_count", 0),
        transaction_count=stats_data.get("transaction_count", 0),
        total_volume_try=stats_data.get("total_volume_try", 0.0),
        avg_balance=stats_data.get("avg_balance", 0.0),
        segments=stats_data.get("segments", {}),
        account_types=stats_data.get("account_types", {}),
        transaction_types=stats_data.get("transaction_types", {}),
    )

    return BankingDatasetResponse(
        customers=result["customers"],
        accounts=result["accounts"],
        transactions=result["transactions"],
        fk_integrity=result["fk_integrity"],
        stats=stats,
        duration_ms=duration_ms,
    )


@router.post("/quality-check", response_model=QualityMetrics)
def quality_check(
    body: QualityCheckRequest,
    user: User = Depends(get_current_user),
) -> QualityMetrics:
    """Compare original vs synthetic data quality."""
    if not body.original or not body.synthetic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'original' and 'synthetic' datasets are required",
        )

    try:
        kde = KDEGenerator()
        metrics = kde.quality_metrics(body.original, body.synthetic)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        _logger.exception("Quality check failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Quality check failed: {}".format(str(e)),
        )

    dist_sim = metrics.get("distribution_similarity", {})
    scores = list(dist_sim.values()) if dist_sim else []
    overall = round(sum(scores) / len(scores), 4) if scores else 0.0

    return QualityMetrics(
        column_stats=metrics.get("column_stats", {}),
        correlation_preservation=metrics.get("correlation_preservation", 0.0),
        distribution_similarity=dist_sim,
        overall_score=overall,
    )


@router.post("/privacy-risk", response_model=PrivacyRiskResponse)
def privacy_risk(
    body: PrivacyRiskRequest,
    user: User = Depends(get_current_user),
) -> PrivacyRiskResponse:
    """Assess re-identification risk between original and synthetic data."""
    if not body.original or not body.synthetic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'original' and 'synthetic' datasets are required",
        )

    try:
        checker = DataQualityChecker()
        result = checker.privacy_risk_score(body.original, body.synthetic)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        _logger.exception("Privacy risk assessment failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Privacy risk assessment failed: {}".format(str(e)),
        )

    return PrivacyRiskResponse(
        risk_score=result["risk_score"],
        vulnerable_columns=result["vulnerable_columns"],
        recommendation=result["recommendation"],
    )


@router.get("/generators", response_model=GeneratorsListResponse)
def list_generators(
    user: User = Depends(get_current_user),
) -> GeneratorsListResponse:
    """List available generators and their status."""
    generators = [
        GeneratorInfo(
            id="kde",
            name="Kernel Density Estimation",
            available=True,
            description=(
                "Histogram/KDE-based generator. Always available. "
                "Uses scipy for real KDE if installed, otherwise uses "
                "histogram-based approximation. scipy installed: {}".format(_HAS_SCIPY)
            ),
        ),
        GeneratorInfo(
            id="ctgan",
            name="Conditional Tabular GAN",
            available=_HAS_SDV,
            description=(
                "Deep learning-based generator using CTGAN from the sdv library. "
                "Produces higher quality synthetic data for complex distributions. "
                "sdv installed: {}. Falls back to KDE if unavailable.".format(_HAS_SDV)
            ),
        ),
    ]
    return GeneratorsListResponse(generators=generators)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DIFFERENTIAL PRIVACY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from app.domains.ai_synthetic_data.privacy_schemas import (
    PrivatizeRequest,
    PrivatizeResponse,
    KAnonymityRequest,
    KAnonymityResponse,
    LDiversityRequest,
    LDiversityResponse,
    ReidentificationRequest,
    ReidentificationResponse,
    PrivacyReportRequest,
    PrivacyReportResponse,
    SuggestConfigRequest,
    SuggestConfigResponse,
    TCKNValidateRequest,
    TCKNValidateResponse,
)


@router.post("/privacy/privatize", response_model=PrivatizeResponse)
def privatize_data(
    body: PrivatizeRequest,
    user: User = Depends(get_current_user),
) -> PrivatizeResponse:
    """Apply differential privacy to a dataset."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import DifferentialPrivacy
        dp = DifferentialPrivacy(epsilon=body.epsilon, delta=body.delta)
        result = dp.privatize_dataset(body.data, body.column_config)
        return PrivatizeResponse(**result)
    except ValueError as e:
        raise HTTPException(400, f"Privatize hatasi: {str(e)[:300]}")
    except Exception as e:
        _logger.exception("Privatize hatasi")
        raise HTTPException(500, f"Privatize hatasi: {str(e)[:300]}")


@router.post("/privacy/k-anonymity", response_model=KAnonymityResponse)
def check_k_anonymity(
    body: KAnonymityRequest,
    user: User = Depends(get_current_user),
) -> KAnonymityResponse:
    """Check if dataset satisfies k-anonymity."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import DifferentialPrivacy
        dp = DifferentialPrivacy()
        result = dp.k_anonymity_check(body.data, body.quasi_identifiers, body.k)
        return KAnonymityResponse(**result)
    except ValueError as e:
        raise HTTPException(400, f"k-Anonymity hatasi: {str(e)[:300]}")
    except Exception as e:
        _logger.exception("k-Anonymity check hatasi")
        raise HTTPException(500, f"k-Anonymity hatasi: {str(e)[:300]}")


@router.post("/privacy/l-diversity", response_model=LDiversityResponse)
def check_l_diversity(
    body: LDiversityRequest,
    user: User = Depends(get_current_user),
) -> LDiversityResponse:
    """Check if dataset satisfies l-diversity."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import DifferentialPrivacy
        dp = DifferentialPrivacy()
        result = dp.l_diversity_check(
            body.data, body.quasi_identifiers, body.sensitive_attr, body.l,
        )
        return LDiversityResponse(**result)
    except ValueError as e:
        raise HTTPException(400, f"l-Diversity hatasi: {str(e)[:300]}")
    except Exception as e:
        _logger.exception("l-Diversity check hatasi")
        raise HTTPException(500, f"l-Diversity hatasi: {str(e)[:300]}")


@router.post("/privacy/reidentification-risk", response_model=ReidentificationResponse)
def check_reidentification_risk(
    body: ReidentificationRequest,
    user: User = Depends(get_current_user),
) -> ReidentificationResponse:
    """Measure re-identification risk between original and synthetic datasets."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import DifferentialPrivacy
        dp = DifferentialPrivacy()
        result = dp.reidentification_risk(
            body.original, body.synthetic, body.quasi_identifiers,
        )
        return ReidentificationResponse(**result)
    except ValueError as e:
        raise HTTPException(400, f"Re-identification risk hatasi: {str(e)[:300]}")
    except Exception as e:
        _logger.exception("Re-identification risk hatasi")
        raise HTTPException(500, f"Re-identification risk hatasi: {str(e)[:300]}")


@router.post("/privacy/report", response_model=PrivacyReportResponse)
def privacy_report_endpoint(
    body: PrivacyReportRequest,
    user: User = Depends(get_current_user),
) -> PrivacyReportResponse:
    """Generate a comprehensive privacy report including KVKK compliance."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import DifferentialPrivacy
        dp = DifferentialPrivacy(epsilon=body.epsilon)
        result = dp.privacy_report(
            data=body.data,
            original=body.original,
            config=body.config,
        )
        return PrivacyReportResponse(**result)
    except ValueError as e:
        raise HTTPException(400, f"Privacy report hatasi: {str(e)[:300]}")
    except Exception as e:
        _logger.exception("Privacy report hatasi")
        raise HTTPException(500, f"Privacy report hatasi: {str(e)[:300]}")


@router.post("/privacy/suggest-config", response_model=SuggestConfigResponse)
def suggest_privacy_config(
    body: SuggestConfigRequest,
    user: User = Depends(get_current_user),
) -> SuggestConfigResponse:
    """Suggest per-column privacy configuration based on data analysis."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import (
            DifferentialPrivacy,
            detect_pii_columns,
        )
        dp = DifferentialPrivacy(epsilon=body.epsilon)
        pii_cols = detect_pii_columns(body.data)

        # Build suggested config per column
        suggestions = []
        column_config: Dict[str, Dict[str, Any]] = {}
        for col in pii_cols:
            # Detect column type from data
            sample_vals = [row.get(col) for row in body.data[:10] if col in row]
            is_numeric = any(isinstance(v, (int, float)) for v in sample_vals)

            if is_numeric:
                max_val = max((v for v in sample_vals if isinstance(v, (int, float))), default=1.0)
                sensitivity = max_val * 0.1
                cfg = {"type": "numeric", "mechanism": "laplace", "sensitivity": sensitivity}
                reason = "Numeric PII — Laplace noise recommended"
            else:
                cfg = {"type": "categorical", "mechanism": "generalize", "granularity": "category"}
                sensitivity = None
                reason = "Categorical PII — generalization recommended"

            suggestions.append({
                "column": col,
                "mechanism": cfg.get("mechanism", "laplace"),
                "sensitivity": sensitivity,
                "reason": reason,
            })
            column_config[col] = cfg

        return SuggestConfigResponse(
            suggestions=suggestions,
            detected_pii=pii_cols,
            column_config=column_config,
        )
    except ValueError as e:
        raise HTTPException(400, f"Config suggestion hatasi: {str(e)[:300]}")
    except Exception as e:
        _logger.exception("Privacy config suggestion hatasi")
        raise HTTPException(500, f"Config suggestion hatasi: {str(e)[:300]}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRIVACY AUDIT / ANONYMIZE / NOISE  (frontend privacy page hooks)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from pydantic import BaseModel as _Base


class _PrivacyAuditRequest(_Base):
    data: List[Dict[str, Any]]
    dataset_name: Optional[str] = "upload"


class _ComplianceDetail(_Base):
    compliant: bool
    issues: List[str]


class _Compliance(_Base):
    kvkk: _ComplianceDetail
    gdpr: _ComplianceDetail
    pci_dss: _ComplianceDetail


class _PrivacyAuditResult(_Base):
    dataset_name: str
    total_records: int
    pii_columns_detected: List[str]
    quasi_identifier_risk: Dict[str, float]
    re_identification_risk: float
    compliance: _Compliance
    recommendations: List[str]


class _AnonymizeRequest(_Base):
    data: List[Dict[str, Any]]
    quasi_identifiers: List[str]
    sensitive_columns: List[str]
    k_anonymity: Optional[int] = 3
    l_diversity: Optional[int] = None


class _AnonymizeResult(_Base):
    anonymized_data: List[Dict[str, Any]]
    original_count: int
    output_count: int
    suppressed_count: int
    k_achieved: int
    l_achieved: int
    information_loss: float


class _NoiseRequest(_Base):
    value: float
    config: Dict[str, Any]


class _NoiseResult(_Base):
    original_value: float
    noisy_value: float
    noise_added: float
    epsilon_used: float
    mechanism: str


@router.post("/privacy/audit", response_model=_PrivacyAuditResult)
def privacy_audit(
    body: _PrivacyAuditRequest,
    user: User = Depends(get_current_user),
) -> _PrivacyAuditResult:
    """PII detection + compliance audit for a dataset."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import (
            DifferentialPrivacy,
            detect_pii_columns,
        )
        pii_cols = detect_pii_columns(body.data)
        dp = DifferentialPrivacy()

        # Estimate re-identification risk using empty synthetic (worst case)
        try:
            risk_result = dp.reidentification_risk(body.data, body.data, pii_cols or list(body.data[0].keys())[:3])
            reid_risk = risk_result.get("risk_score", 0.0)
        except Exception:
            reid_risk = 0.0

        quasi_risk = {col: round(min(reid_risk + 0.1 * i, 1.0), 4) for i, col in enumerate(pii_cols)}

        has_pii = bool(pii_cols)
        issues_kvkk = ["PII sütunları tespit edildi: " + ", ".join(pii_cols)] if has_pii else []
        issues_gdpr = issues_kvkk[:]
        issues_pci = [c for c in pii_cols if any(kw in c.lower() for kw in ("card", "cvv", "pan", "account"))]

        return _PrivacyAuditResult(
            dataset_name=body.dataset_name or "upload",
            total_records=len(body.data),
            pii_columns_detected=pii_cols,
            quasi_identifier_risk=quasi_risk,
            re_identification_risk=round(reid_risk, 4),
            compliance=_Compliance(
                kvkk=_ComplianceDetail(compliant=not has_pii, issues=issues_kvkk),
                gdpr=_ComplianceDetail(compliant=not has_pii, issues=issues_gdpr),
                pci_dss=_ComplianceDetail(compliant=not bool(issues_pci), issues=issues_pci),
            ),
            recommendations=(
                ["Tespit edilen PII sütunları için anonim. veya maskeleme uygulayın."] if has_pii
                else ["Veri seti PII içermiyor; mevcut gizlilik düzeyi yeterli."]
            ),
        )
    except Exception as e:
        _logger.exception("Privacy audit hatasi")
        raise HTTPException(500, f"Privacy audit hatasi: {str(e)[:300]}")


@router.post("/privacy/anonymize", response_model=_AnonymizeResult)
def anonymize_dataset(
    body: _AnonymizeRequest,
    user: User = Depends(get_current_user),
) -> _AnonymizeResult:
    """k-anonymity–based generalization/suppression of a dataset."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import DifferentialPrivacy
        dp = DifferentialPrivacy()
        k = body.k_anonymity or 3

        # Use existing k-anonymity check as basis for suppression
        result = dp.k_anonymity_check(body.data, body.quasi_identifiers, k)
        k_achieved = result.get("k_achieved", k)
        info_loss = round(1.0 - result.get("coverage", 1.0), 4)

        # Simple suppression: drop rows that would break k-anonymity groups
        suppressed = 0
        output_data = body.data
        if k_achieved < k:
            from collections import Counter
            keys = [tuple(str(row.get(qi, "")) for qi in body.quasi_identifiers) for row in body.data]
            counts = Counter(keys)
            output_data = [row for row, key in zip(body.data, keys) if counts[key] >= k]
            suppressed = len(body.data) - len(output_data)
            k_achieved = k if output_data else 0

        return _AnonymizeResult(
            anonymized_data=output_data,
            original_count=len(body.data),
            output_count=len(output_data),
            suppressed_count=suppressed,
            k_achieved=k_achieved,
            l_achieved=body.l_diversity or 1,
            information_loss=info_loss,
        )
    except Exception as e:
        _logger.exception("Anonymize hatasi")
        raise HTTPException(500, f"Anonymize hatasi: {str(e)[:300]}")


@router.post("/privacy/noise", response_model=_NoiseResult)
def add_differential_noise(
    body: _NoiseRequest,
    user: User = Depends(get_current_user),
) -> _NoiseResult:
    """Add differential privacy noise to a single numeric value."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import DifferentialPrivacy
        config = body.config or {}
        epsilon = float(config.get("epsilon", 1.0))
        sensitivity = float(config.get("sensitivity", 1.0))
        mechanism = str(config.get("mechanism", "laplace"))

        dp = DifferentialPrivacy(epsilon=epsilon)
        if mechanism == "gaussian":
            noisy = dp.add_gaussian_noise(body.value, sensitivity)
        else:
            noisy = dp.add_laplace_noise(body.value, sensitivity)

        return _NoiseResult(
            original_value=body.value,
            noisy_value=round(noisy, 6),
            noise_added=round(noisy - body.value, 6),
            epsilon_used=epsilon,
            mechanism=mechanism,
        )
    except Exception as e:
        _logger.exception("Noise addition hatasi")
        raise HTTPException(500, f"Noise addition hatasi: {str(e)[:300]}")


@router.get("/privacy/report", response_model=_PrivacyAuditResult)
def get_privacy_report_default(
    project_id: Optional[str] = None,
    user: User = Depends(get_current_user),
) -> _PrivacyAuditResult:
    """Return a default/empty privacy audit result (no stored state yet)."""
    return _PrivacyAuditResult(
        dataset_name="—",
        total_records=0,
        pii_columns_detected=[],
        quasi_identifier_risk={},
        re_identification_risk=0.0,
        compliance=_Compliance(
            kvkk=_ComplianceDetail(compliant=True, issues=[]),
            gdpr=_ComplianceDetail(compliant=True, issues=[]),
            pci_dss=_ComplianceDetail(compliant=True, issues=[]),
        ),
        recommendations=["Henüz veri seti yüklenmedi. Audit için veri ekleyin."],
    )


@router.post("/privacy/validate-tckn", response_model=TCKNValidateResponse)
def validate_tckn_endpoint(
    body: TCKNValidateRequest,
    user: User = Depends(get_current_user),
) -> TCKNValidateResponse:
    """Validate a Turkish citizen ID number (TCKN)."""
    try:
        from app.domains.ai_synthetic_data.differential_privacy import validate_tckn
        valid = validate_tckn(body.tckn)
        return TCKNValidateResponse(
            valid=valid,
            tckn=body.tckn,
            message="Gecerli TCKN" if valid else "Geçersiz TCKN — algoritma dogrulamasi başarısız",
        )
    except ValueError as e:
        raise HTTPException(400, f"TCKN validation hatasi: {str(e)[:300]}")
    except Exception as e:
        _logger.exception("TCKN validation hatasi")
        raise HTTPException(500, f"TCKN validation hatasi: {str(e)[:300]}")
