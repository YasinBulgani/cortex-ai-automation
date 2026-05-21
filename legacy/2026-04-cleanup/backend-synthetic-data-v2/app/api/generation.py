"""
Data Generation & Export API router.
"""
import os
import io
import time
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging

from app.database import get_db
from app.models.schema_model import DetectedSchema, GenerationRule, GenerationHistory, Project
from app.core.generator import SyntheticGenerator
from app.core.scenarios import ScenarioManager
from app.config import get_settings

router = APIRouter(prefix="/api/generate", tags=["Data Generation"])

generator = SyntheticGenerator()
scenario_mgr = ScenarioManager()
settings = get_settings()

# In-memory job store for auto-generation jobs
_jobs: dict = {}  # job_id -> job_info


class GenerateRequest(BaseModel):
    schema_id: str
    row_count: int = 1000
    scenario: str = "default"
    format: str = "json"  # json, csv, sql


class ScenarioGenerateRequest(BaseModel):
    project_id: str
    scenario: str = "default"
    row_counts: dict = {}  # table_name → count
    format: str = "json"


class AIQueryRequest(BaseModel):
    schema_id: str
    prompt: str


class BulkGenerateRequest(BaseModel):
    schema_ids: list[str]
    row_count: int = 1000
    scenario: str = "default"
    format: str = "json"


class AutoJobRequest(BaseModel):
    schema_id: str
    row_count: int = 1000
    scenario: str = "default"
    interval_minutes: int = 60
    label: Optional[str] = None


class ExplainRequest(BaseModel):
    prompt: str


@router.get("/scenarios")
async def list_scenarios():
    """List all available banking scenarios."""
    return scenario_mgr.list_scenarios()


# ── Scenario metadata for explain ──────────────────────────────────────────
_SCENARIO_META = {
    "default": {
        "name": "Varsayılan",
        "description": "Genel amaçlı dengeli veri üretimi",
        "icon": "📊",
    },
    "premium_customer": {
        "name": "Premium / VIP Müşteri",
        "description": "Yüksek bakiyeli, sadık ve gelir grubu yüksek müşteriler",
        "icon": "💎",
    },
    "new_customer": {
        "name": "Yeni Müşteri",
        "description": "Son katılan, sınırlı işlem geçmişi olan profiller",
        "icon": "🆕",
    },
    "high_risk": {
        "name": "Yüksek Risk / Gecikme",
        "description": "Temerrüt, gecikme ve düşük kredi skoru içeren veriler",
        "icon": "⚠️",
    },
    "corporate": {
        "name": "Kurumsal / Ticari",
        "description": "Şirket, KOBİ ve ticari hesap profilleri",
        "icon": "🏢",
    },
    "fraud_test": {
        "name": "Fraud / Dolandırıcılık Testi",
        "description": "Şüpheli işlemler ve anomali içeren test verisi",
        "icon": "🚨",
    },
}

_TABLE_META = {
    "musteriler": {"label": "Müşteriler", "icon": "👥", "desc": "Müşteri profil ve kişisel bilgileri"},
    "hesaplar": {"label": "Hesaplar", "icon": "🏦", "desc": "Banka hesap bakiyesi ve türü"},
    "islemler": {"label": "İşlemler", "icon": "💸", "desc": "Para transferi ve işlem kayıtları"},
    "kredi_kartlari": {"label": "Kredi Kartları", "icon": "💳", "desc": "Kart limiti, harcama ve borç bilgileri"},
    "krediler": {"label": "Krediler", "icon": "📋", "desc": "Kredi tutarı, taksit ve ödeme durumu"},
}


# ── Helper for LLM Parsing ──────────────────────────────────────────────────
def _parse_prompt_with_llm(prompt: str) -> dict:
    import json
    import re
    from app.config import get_settings
    
    settings = get_settings()
    llm_response = ""
    system_prompt = f"""
Sen yapay zeka destekli bir veri üretim asistanısın. Kullanıcının girdisini analiz edip, JSON formatında parametreler döndürmelisin.
Verilen Girdi: "{prompt}"

Parametreler:
- row_count (int): Kaç satır üretileceği (bulamazsan 1000 kullan).
- scenario (str): Veri senaryosu. Şunlardan biri olmalı: "default", "premium_customer", "new_customer", "high_risk", "corporate", "fraud_test".
- recommended_table (str): Hangi tablo için uygun olduğu: "musteriler", "hesaplar", "islemler", "kredi_kartlari", "krediler".
- confidence (str): "high", "medium", "low".

Sadece JSON formatında yanıt ver, metin veya markdown bloğu kullanma. JSON şu şekilde olmalı: {{"row_count": 1000, "scenario": "default", "recommended_table": "musteriler", "confidence": "high"}}
"""
    
    try:
        # 1. Deneme: Google Gemini (Ücretsiz API anahtarı ayarlandıysa)
        api_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY"))
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(system_prompt.replace("{prompt}", prompt))
            llm_response = response.text
        else:
            # 2. Deneme: Ücretsiz g4f (API anahtarı gerektirmez)
            try:
                from g4f.client import Client
                client = Client()
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt.replace("{prompt}", prompt)}]
                )
                llm_response = response.choices[0].message.content
            except Exception as g4f_err:
                logging.warning(f"g4f hatası: {g4f_err}. Fallback regex kullanılıyor.")
                raise ValueError("LLM servislerine ulaşılamadı.")
                
        # Parse JSON from response
        if "```" in llm_response:
            llm_response = re.sub(r"```json|```", "", llm_response).strip()
            
        return json.loads(llm_response)
        
    except Exception as e:
        # Fallback to regex safely if LLM fails (e.g. no internet)
        logging.error(f"LLM parsing error: {e}")
        
        row_count = 1000
        match = re.search(r'\b(\d[\d\s]*)\b', prompt)
        if match:
            row_count = int(match.group(1).replace(" ", ""))
        elif "yüz" in prompt: row_count = 100
        elif "bin" in prompt: row_count = 1000
        
        scenario = "default"
        if any(w in prompt for w in ["premium", "zengin", "vip"]): scenario = "premium_customer"
        elif any(w in prompt for w in ["risk", "gecikme", "kötü"]): scenario = "high_risk"
        elif any(w in prompt for w in ["kurumsal", "şirket"]): scenario = "corporate"
        elif any(w in prompt for w in ["dolandırıcı", "fraud", "şüpheli"]): scenario = "fraud_test"
        
        table = "musteriler"
        if any(w in prompt for w in ["işlem", "transfer"]): table = "islemler"
        elif any(w in prompt for w in ["kart", "kredi kartı"]): table = "kredi_kartlari"
        elif any(w in prompt for w in ["hesap", "bakiye"]): table = "hesaplar"
        elif any(w in prompt for w in ["kredi", "borç"]): table = "krediler"
            
        return {
            "row_count": row_count,
            "scenario": scenario,
            "recommended_table": table,
            "confidence": "low"
        }

@router.post("/explain")
async def explain_data_request(req: ExplainRequest):
    """Parse a natural-language prompt (Turkish) and return step-by-step guidance."""
    prompt = req.prompt.lower().strip()

    # LLM ile analizi yap
    analysis = _parse_prompt_with_llm(prompt)
    
    row_count = max(10, min(analysis.get("row_count", 1000), 100000))
    scenario = analysis.get("scenario", "default")
    recommended_table = analysis.get("recommended_table", "musteriler")
    confidence = analysis.get("confidence", "medium")

    # Alternatif tablolar belirle
    alt_tables = ["hesaplar", "islemler"]
    if recommended_table == "hesaplar": alt_tables = ["musteriler", "islemler"]
    elif recommended_table == "islemler": alt_tables = ["musteriler", "hesaplar"]

    table_info = _TABLE_META.get(recommended_table, {"label": recommended_table, "icon": "📊", "desc": ""})
    scenario_info = _SCENARIO_META.get(scenario, _SCENARIO_META["default"])

    # Build step-by-step instructions
    steps = [
        f"Aşağıdaki hazır şablonlardan **{table_info['icon']} {table_info['label']}** tablosunu seçin.",
        f"Senaryo olarak **{scenario_info['icon']} {scenario_info['name']}** seçin — {scenario_info['description']}.",
        f"Satır sayısı alanına **{row_count:,}** girin.",
        "Gerekirse kolon kurallarını özelleştirin.",
        "**⚡ Üret** butonuna tıklayın — veri birkaç saniyede hazır olur."
    ]

    filters = {}
    if scenario == "high_risk": filters = {"risk_skoru_min": 70, "gecikme_durumu": True}
    elif scenario == "fraud_test": filters = {"şüpheli_işlem": True, "anormal_tutar": True}
    elif scenario == "premium_customer": filters = {"bakiye_min": 50000, "segment": "VIP"}
    elif scenario == "corporate": filters = {"hesap_turu": "Ticari", "vergi_numarası": True}

    return {
        "interpretation": f"{row_count:,} satır · {scenario_info['name']} senaryosu · {table_info['label']} tablosu",
        "recommended_table": recommended_table,
        "table_info": table_info,
        "scenario": scenario,
        "scenario_info": scenario_info,
        "row_count": row_count,
        "steps": steps,
        "filters": filters,
        "confidence": confidence,
        "alternative_tables": [
            {**_TABLE_META.get(t, {"label": t, "icon": "📊", "desc": ""}), "key": t}
            for t in alt_tables
        ],
    }


@router.post("")
async def generate_data(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate synthetic data for a single schema."""
    start = time.time()

    # Load schema
    result = await db.execute(
        select(DetectedSchema).where(DetectedSchema.id == req.schema_id)
    )
    schema_record = result.scalar_one_or_none()
    if not schema_record:
        raise HTTPException(404, "Şema bulunamadı")

    # Load rules
    rules_result = await db.execute(
        select(GenerationRule).where(
            GenerationRule.schema_id == schema_record.id,
            GenerationRule.is_active == True
        )
    )
    rules = [
        {
            "column_name": r.column_name,
            "rule_type": r.rule_type,
            "rule_config": r.rule_config,
        }
        for r in rules_result.scalars().all()
    ]

    # Apply scenario overrides
    if req.scenario != "default":
        rules = scenario_mgr.apply_scenario(req.scenario, rules, schema_record.table_name)

    # Build schema dict
    schema_dict = {
        "table_name": schema_record.table_name,
        "columns": schema_record.columns,
    }

    # Generate
    df = generator.generate(schema_dict, rules, req.row_count)
    duration = int((time.time() - start) * 1000)

    # Preview (first 20 rows)
    preview = json.loads(df.head(20).to_json(orient="records", date_format="iso", default_handler=str))

    # Save history
    history = GenerationHistory(
        project_id=schema_record.project_id,
        schema_ids=[str(schema_record.id)],
        row_count=req.row_count,
        scenario=req.scenario,
        format=req.format,
        status="completed",
        generated_data_preview=preview,
        duration_ms=duration,
    )
    db.add(history)
    await db.flush()

    # Format response
    if req.format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={schema_record.table_name}_synthetic.csv"}
        )
    elif req.format == "sql":
        sql_lines = _dataframe_to_sql(df, schema_record.table_name)
        return StreamingResponse(
            iter([sql_lines]),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={schema_record.table_name}_synthetic.sql"}
        )
    else:
        return {
            "generation_id": str(history.id),
            "table_name": schema_record.table_name,
            "row_count": len(df),
            "scenario": req.scenario,
            "duration_ms": duration,
            "preview": preview,
            "columns": list(df.columns),
        }


@router.post("/scenario")
async def generate_scenario(req: ScenarioGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate multi-table data with a banking scenario."""
    start = time.time()

    # Load all schemas for the project
    result = await db.execute(
        select(DetectedSchema).where(
            DetectedSchema.project_id == req.project_id
        )
    )
    schemas = result.scalars().all()
    if not schemas:
        raise HTTPException(404, "Bu projede şema bulunamadı")

    all_schemas = []
    all_rules = {}

    for s in schemas:
        schema_dict = {"table_name": s.table_name, "columns": s.columns}
        all_schemas.append(schema_dict)

        # Load rules for this schema
        rules_res = await db.execute(
            select(GenerationRule).where(
                GenerationRule.schema_id == s.id,
                GenerationRule.is_active == True
            )
        )
        rules = [
            {"column_name": r.column_name, "rule_type": r.rule_type, "rule_config": r.rule_config}
            for r in rules_res.scalars().all()
        ]

        # Apply scenario
        if req.scenario != "default":
            rules = scenario_mgr.apply_scenario(req.scenario, rules, s.table_name)

        all_rules[s.table_name] = rules

    # Row counts
    row_counts = {}
    for s in all_schemas:
        row_counts[s["table_name"]] = req.row_counts.get(s["table_name"], 1000)

    # Detect relationships
    relationships = []
    for s in schemas:
        for rel in (s.relationships or []):
            relationships.append(rel)

    # Generate all tables
    generated = generator.generate_multi_table(
        all_schemas, all_rules, relationships, row_counts
    )

    duration = int((time.time() - start) * 1000)

    # Build response with previews
    result_tables = {}
    for table_name, df in generated.items():
        result_tables[table_name] = {
            "row_count": len(df),
            "columns": list(df.columns),
            "preview": json.loads(df.head(10).to_json(orient="records", date_format="iso", default_handler=str)),
        }

    return {
        "scenario": req.scenario,
        "tables": result_tables,
        "duration_ms": duration,
    }


@router.post("/ai-query")
async def generate_from_ai(req: AIQueryRequest, db: AsyncSession = Depends(get_db)):
    """Parse natural language prompt with LLM to set generation parameters and run generation."""
    prompt = req.prompt.lower().strip()
    
    # LLM ile analizi yap
    analysis = _parse_prompt_with_llm(prompt)
    
    row_count = max(10, min(analysis.get("row_count", 100), 100000))
    scenario = analysis.get("scenario", "default")
        
    interpretation = f"{row_count} satır - {scenario} senaryosu uygulanarak üretildi"
    
    # Run generation
    gen_req = GenerateRequest(
        schema_id=req.schema_id, 
        row_count=row_count, 
        scenario=scenario, 
        format="json"
    )
    result = await generate_data(gen_req, db)
    
    if isinstance(result, dict) and "preview" in result:
        result["ai_interpretation"] = interpretation
    
    return result



@router.post("/bulk")
async def generate_bulk(req: BulkGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate data for multiple schemas at once and return combined results."""
    start = time.time()
    results = []

    for schema_id in req.schema_ids:
        try:
            gen_req = GenerateRequest(
                schema_id=schema_id,
                row_count=req.row_count,
                scenario=req.scenario,
                format="json",
            )
            result = await generate_data(gen_req, db)
            if isinstance(result, dict):
                results.append(result)
        except Exception as e:
            results.append({"schema_id": schema_id, "error": str(e)})

    duration = int((time.time() - start) * 1000)
    return {
        "tables": results,
        "total_schemas": len(req.schema_ids),
        "success_count": sum(1 for r in results if "error" not in r),
        "duration_ms": duration,
    }


@router.post("/jobs")
async def create_auto_job(req: AutoJobRequest, db: AsyncSession = Depends(get_db)):
    """Create an automatic generation job (runs in background simulation)."""
    job_id = str(uuid.uuid4())[:8].upper()
    job = {
        "job_id": job_id,
        "schema_id": req.schema_id,
        "row_count": req.row_count,
        "scenario": req.scenario,
        "interval_minutes": req.interval_minutes,
        "label": req.label or f"Auto Job {job_id}",
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "last_run": None,
        "run_count": 0,
        "next_run": datetime.utcnow().isoformat(),
    }
    _jobs[job_id] = job
    return {"status": "created", "job": job}


@router.get("/jobs")
async def list_jobs():
    """List all auto-generation jobs."""
    return {"jobs": list(_jobs.values())}


@router.post("/jobs/{job_id}/run")
async def run_job_now(job_id: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger a job run immediately."""
    if job_id not in _jobs:
        raise HTTPException(404, "Job bulunamadı")
    job = _jobs[job_id]
    gen_req = GenerateRequest(
        schema_id=job["schema_id"],
        row_count=job["row_count"],
        scenario=job["scenario"],
        format="json",
    )
    result = await generate_data(gen_req, db)
    job["last_run"] = datetime.utcnow().isoformat()
    job["run_count"] = job.get("run_count", 0) + 1
    return {"status": "ran", "job_id": job_id, "result_summary": {
        "row_count": result.get("row_count", 0) if isinstance(result, dict) else 0,
        "duration_ms": result.get("duration_ms", 0) if isinstance(result, dict) else 0,
    }}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete an auto-generation job."""
    if job_id not in _jobs:
        raise HTTPException(404, "Job bulunamadı")
    del _jobs[job_id]
    return {"status": "deleted", "job_id": job_id}


@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    """Get generation history."""
    result = await db.execute(
        select(GenerationHistory).order_by(GenerationHistory.created_at.desc()).limit(50)
    )
    return [
        {
            "id": str(h.id),
            "row_count": h.row_count,
            "scenario": h.scenario,
            "format": h.format,
            "status": h.status,
            "duration_ms": h.duration_ms,
            "created_at": str(h.created_at),
        }
        for h in result.scalars().all()
    ]


def _dataframe_to_sql(df, table_name: str) -> str:
    """Convert a DataFrame to INSERT statements."""
    lines = []
    cols = ", ".join(df.columns)
    for _, row in df.iterrows():
        vals = ", ".join(
            f"'{str(v)}'" if v is not None else "NULL"
            for v in row.values
        )
        lines.append(f"INSERT INTO {table_name} ({cols}) VALUES ({vals});")
    return "\n".join(lines)
