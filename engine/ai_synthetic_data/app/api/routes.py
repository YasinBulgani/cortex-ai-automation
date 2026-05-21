"""
Synthetic Data Platform API Routes.

Mevcut endpoint'ler (korundu):
  POST /api/data/analyze-and-infer  — CSV analiz + kural cikarimi
  POST /api/data/generate           — Basit kurala dayali uretim

Faz 1 endpoint'ler (yeni):
  POST /api/data/connect            — Dis DB'ye baglan
  GET  /api/data/tables             — Bagli DB'deki tablolari listele
  POST /api/data/profile/{table}    — Gelismis tablo profilleme
  POST /api/data/generate/advanced  — KDE bazli gercekci uretim
  POST /api/data/generate/banking   — Bankacilik domain uretim

Faz 2 endpoint'ler:
  POST /api/data/generate/relational — Coklu tablo FK koruyan uretim

Faz 3 endpoint'ler:
  POST /api/data/evaluate           — Kalite metrikleri
  POST /api/data/privacy-check      — Gizlilik risk degerlendirmesi
"""
from __future__ import annotations

import io
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.analyzer import SchemaAnalyzer
from app.core.classifier import SemanticClassifier
from app.core.rule_engine import RuleEngine
from app.core.generator import SyntheticGenerator

router = APIRouter(prefix="/api/data", tags=["Data Processing"])

analyzer = SchemaAnalyzer()
classifier = SemanticClassifier()
rule_engine = RuleEngine()
generator = SyntheticGenerator()


# ══════════════════════════════════════════════════════════════════════════════
# Mevcut Endpoint'ler (MVP — degistirilmedi)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/analyze-and-infer")
async def analyze_and_infer(file: UploadFile = File(...)):
    """CSV okur, analiz eder, semantik siniflandirir, kural cikarir."""
    content = await file.read()
    str_content = content.decode("utf-8")
    df = pd.read_csv(io.StringIO(str_content))

    schema = analyzer.analyze_dataframe(file.filename, df)
    schema = classifier.enrich_schema(schema)
    rules = rule_engine.infer_rules(schema)

    return {"schema": schema, "inferred_rules": rules}


@router.post("/generate")
async def generate_synthetic(request_data: dict):
    """Kurala dayali basit sentetik veri uretir."""
    schema = request_data.get("schema", {})
    rules = request_data.get("rules", [])
    row_count = request_data.get("row_count", 100)

    df = generator.generate(schema, rules, row_count=row_count)
    return df.to_dict(orient="records")


# ══════════════════════════════════════════════════════════════════════════════
# Faz 1: DB Connector + Gelismis Profilleme + KDE Uretim
# ══════════════════════════════════════════════════════════════════════════════

_datasource = None


def _get_datasource():
    global _datasource
    if _datasource is None:
        from app.core.datasource import DataSourceManager
        _datasource = DataSourceManager()
    return _datasource


class ConnectRequest(BaseModel):
    connection_string: str
    alias: str = "default"


class AdvancedGenerateRequest(BaseModel):
    table_name: str
    row_count: int = 1000
    method: str = "kde"  # kde | gmm | parametric | auto
    conditional: dict[str, str] | None = None


class BankingGenerateRequest(BaseModel):
    entity: str = "customer"  # customer | account | transaction
    count: int = 100
    segment: str = "Bireysel"


class RelationalGenerateRequest(BaseModel):
    customer_count: int = 100
    accounts_per_customer: str = "1-3"  # range
    transactions_per_account: str = "5-30"
    segment_distribution: dict[str, float] | None = None


@router.post("/connect")
async def connect_to_db(req: ConnectRequest):
    """Dis veritabanina baglan ve semayi kesfet."""
    ds = _get_datasource()
    result = ds.connect(req.connection_string)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["detail"])

    tables = ds.list_tables()
    relationships = ds.discover_relationships()
    return {
        **result,
        "tables": tables,
        "table_count": len(tables),
        "relationships": relationships,
    }


@router.get("/tables")
async def list_tables():
    """Bagli DB'deki tablolari listele."""
    ds = _get_datasource()
    try:
        tables = ds.list_tables()
        return {"tables": tables, "count": len(tables)}
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/profile/{table_name}")
async def profile_table(table_name: str, sample_size: int = 5000):
    """Tabloyu ornekle ve gelismis profilleme yap."""
    ds = _get_datasource()
    try:
        df = ds.sample(table_name, n=sample_size)
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Tablo bulunamadi: {e}")

    schema_info = ds.discover_schema(table_name)
    profile = analyzer.analyze_advanced(table_name, df)
    profile["schema_info"] = schema_info

    enriched = classifier.enrich_schema(profile)
    rules = rule_engine.infer_rules(enriched)
    profile["inferred_rules"] = rules

    return profile


@router.post("/generate/advanced")
async def generate_advanced(req: AdvancedGenerateRequest):
    """KDE/GMM bazli gercekci sentetik veri uret."""
    ds = _get_datasource()

    try:
        df = ds.sample(req.table_name, n=5000)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Veri okunamadi: {e}")

    from app.core.kde_synth import KDESynthesizer

    synth = KDESynthesizer()

    if req.conditional and len(req.conditional) == 2:
        target = req.conditional.get("target")
        condition = req.conditional.get("condition")
        if target and condition and target in df.columns and condition in df.columns:
            synth.fit(df.drop(columns=[target]))
            synth.fit_conditional(df, target, condition)
            base_df = synth.sample(req.row_count)
            cond_values = base_df[condition].tolist()
            base_df[target] = synth.sample_conditional(req.row_count, cond_values)
            return base_df.to_dict(orient="records")

    synth.fit(df)
    result_df = synth.sample(req.row_count)
    return result_df.to_dict(orient="records")


@router.post("/generate/banking")
async def generate_banking(req: BankingGenerateRequest):
    """Bankacilik domain bilgisi ile sentetik veri uret."""
    from app.core import banking_distributions as bd

    if req.entity == "customer":
        data = {
            "tckn": bd.generate_tckn(req.count),
            "segment": [req.segment] * req.count,
            "bakiye": bd.generate_balance(req.segment, req.count).tolist(),
            "kredi_skoru": bd.generate_credit_score(req.count).tolist(),
            "yas": bd.generate_age(req.count).tolist(),
            "telefon": bd.generate_phone(req.count),
        }
    elif req.entity == "account":
        data = {
            "iban": bd.generate_iban(req.count),
            "bakiye": bd.generate_balance(req.segment, req.count).tolist(),
        }
    elif req.entity == "transaction":
        data = {
            "tutar": bd.generate_transaction_amount("EFT", req.count).tolist(),
            "tarih": bd.generate_transaction_dates(req.count),
            "siklik": bd.generate_transaction_frequency(req.segment, req.count).tolist(),
        }
    else:
        raise HTTPException(status_code=400, detail=f"Bilinmeyen entity: {req.entity}")

    return pd.DataFrame(data).to_dict(orient="records")


@router.post("/generate/relational")
async def generate_relational(req: RelationalGenerateRequest):
    """Customer -> Account -> Transaction iliskisel zincir uret."""
    from app.core import banking_distributions as bd
    import random as _rnd

    seg_dist = req.segment_distribution or {
        "Bireysel": 0.62, "Premium": 0.18, "Kurumsal": 0.15, "VIP": 0.05,
    }
    segments = list(seg_dist.keys())
    weights = list(seg_dist.values())
    total = sum(weights)
    weights = [w / total for w in weights]

    cust_segments = _rnd.choices(segments, weights=weights, k=req.customer_count)

    customers = []
    for i, seg in enumerate(cust_segments):
        customers.append({
            "customer_id": f"MUS{i+1:06d}",
            "tckn": bd.generate_tckn(1)[0],
            "segment": seg,
            "bakiye": float(bd.generate_balance(seg, 1)[0]),
            "kredi_skoru": int(bd.generate_credit_score(1)[0]),
            "yas": int(bd.generate_age(1)[0]),
            "telefon": bd.generate_phone(1)[0],
        })

    lo, hi = [int(x) for x in req.accounts_per_customer.split("-")]
    accounts = []
    acc_idx = 0
    for cust in customers:
        n_acc = _rnd.randint(lo, hi)
        for _ in range(n_acc):
            acc_idx += 1
            accounts.append({
                "account_id": f"HSP{acc_idx:08d}",
                "customer_id": cust["customer_id"],
                "iban": bd.generate_iban(1)[0],
                "bakiye": float(bd.generate_balance(cust["segment"], 1)[0]),
            })

    lo_t, hi_t = [int(x) for x in req.transactions_per_account.split("-")]
    transactions = []
    tx_idx = 0
    tx_types = ["EFT", "Havale", "ATM", "POS", "Fatura", "Maas"]
    for acc in accounts:
        n_tx = _rnd.randint(lo_t, hi_t)
        dates = bd.generate_transaction_dates(n_tx)
        for j in range(n_tx):
            tx_idx += 1
            tx_type = _rnd.choice(tx_types)
            transactions.append({
                "transaction_id": f"TXN{tx_idx:010d}",
                "account_id": acc["account_id"],
                "tutar": float(bd.generate_transaction_amount(tx_type, 1)[0]),
                "islem_tipi": tx_type,
                "tarih": dates[j],
            })

    return {
        "customers": customers,
        "accounts": accounts,
        "transactions": transactions,
        "summary": {
            "customer_count": len(customers),
            "account_count": len(accounts),
            "transaction_count": len(transactions),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# Faz 3: Kalite Metrikleri + Gizlilik Risk Degerlendirmesi
# ══════════════════════════════════════════════════════════════════════════════

class EvaluateRequest(BaseModel):
    real_data: list[dict]
    synthetic_data: list[dict]
    target_column: str | None = None


class PrivacyCheckRequest(BaseModel):
    real_data: list[dict]
    synthetic_data: list[dict]
    quasi_identifiers: list[str] | None = None
    k: int = 5
    epsilon: float = 3.0


@router.post("/evaluate")
async def evaluate_quality(req: EvaluateRequest):
    """Sentetik verinin kalite metriklerini hesapla."""
    from app.core.quality import QualityEvaluator

    real_df = pd.DataFrame(req.real_data)
    synth_df = pd.DataFrame(req.synthetic_data)
    evaluator = QualityEvaluator()

    report = evaluator.generate_quality_report(real_df, synth_df, req.target_column)
    return report


@router.post("/privacy-check")
async def privacy_check(req: PrivacyCheckRequest):
    """Sentetik verinin gizlilik risk degerlendirmesini yap."""
    from app.core.privacy import PrivacyGuard

    real_df = pd.DataFrame(req.real_data)
    synth_df = pd.DataFrame(req.synthetic_data)
    guard = PrivacyGuard()

    report = guard.compute_privacy_report(
        real_df, synth_df,
        quasi_identifiers=req.quasi_identifiers,
        k=req.k,
    )
    return report


@router.post("/apply-privacy")
async def apply_privacy(req: PrivacyCheckRequest):
    """Sentetik veriye diferansiyel gizlilik noise uygula."""
    from app.core.privacy import PrivacyGuard

    synth_df = pd.DataFrame(req.synthetic_data)
    guard = PrivacyGuard()

    protected_df = guard.apply_dp_noise(synth_df, epsilon=req.epsilon)
    return {
        "protected_data": protected_df.to_dict(orient="records"),
        "epsilon": req.epsilon,
        "rows": len(protected_df),
    }


@router.get("/status")
async def platform_status():
    """Platform durumu ve desteklenen ozellikler."""
    from app.core.deep_synth import DeepSynthesizer

    ds = DeepSynthesizer()
    return {
        "status": "running",
        "version": "2.0.0",
        "features": {
            "csv_upload": True,
            "db_connector": True,
            "kde_synthesis": True,
            "copula_synthesis": True,
            "deep_synthesis": ds.is_sdv_available,
            "relational_synthesis": True,
            "banking_distributions": True,
            "quality_evaluation": True,
            "privacy_guard": True,
            "temporal_patterns": True,
        },
        "synthesizers": ["stat", "kde", "copula", "ctgan", "tvae"],
    }
