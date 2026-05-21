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
            detail="sample_data is required — provide at least a few sample rows",
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
            detail="Generation failed: {}".format(str(e)),
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
            message="Gecerli TCKN" if valid else "Gecersiz TCKN — algoritma dogrulamasi basarisiz",
        )
    except ValueError as e:
        raise HTTPException(400, f"TCKN validation hatasi: {str(e)[:300]}")
    except Exception as e:
        _logger.exception("TCKN validation hatasi")
        raise HTTPException(500, f"TCKN validation hatasi: {str(e)[:300]}")
