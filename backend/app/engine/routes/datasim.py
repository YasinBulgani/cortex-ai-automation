"""
Datasim routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/datasim_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/datasim.py — APIRouter, port 8000 (consolidated)

Bu pattern her route file için takip edilir. Bir Python developer kopyala-yapıştır + dönüştür yapar.
"""

from __future__ import annotations

import io
import json
import time
import traceback
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/datasim", tags=["engine", "datasim"])

# Yerel örnek veri setleri klasörü
DATASETS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "engine" / "datasets"


# ─── Katalog: Bankacılık / Finans veri setleri ────────────────────────────────
DATASETS: list[dict] = [
    {
        "id": "bank_marketing",
        "name": "Bank Marketing",
        "emoji": "📣",
        "desc": "Portekiz bankasının telefon pazarlama kampanyası. Müşteri demografisi + kampanya sonucu.",
        "tags": ["Pazarlama", "Sınıflandırma", "Churn"],
        "rows": 300, "cols": 17,
        "columns": "age, job, marital, education, default, balance, housing, loan, contact, day, month, duration, campaign, pdays, previous, poutcome, deposit",
        "source": "Örnek Veri (Yerel)",
        "local_file": "bank_marketing.csv",
        "url": "https://raw.githubusercontent.com/pycaret/pycaret/master/datasets/bank.csv",
        "sample_rows": 300,
    },
    {
        "id": "bank_loan_default",
        "name": "Banka Kredisi Temerrüdü",
        "emoji": "💸",
        "desc": "Kredi başvurusu demografisi ve temerrüt durumu. Kredi riski modellemesi için idealdir.",
        "tags": ["Kredi Riski", "Temerrüt", "Sınıflandırma"],
        "rows": 300, "cols": 9,
        "columns": "age, ed, employ, address, income, debtinc, creddebt, othdebt, default",
        "source": "Örnek Veri (Yerel)",
        "local_file": "bank_loan_default.csv",
        "url": "https://raw.githubusercontent.com/Safa1615/Dataset--loan/main/bank-loan.csv",
        "sample_rows": 300,
    },
    {
        "id": "banking_transactions",
        "name": "Bankacılık İşlemleri",
        "emoji": "🏦",
        "desc": "Müşteri işlemleri, hesap hareketleri, şube bilgileri ve bakiyeler. Türkçe.",
        "tags": ["İşlemler", "Müşteri", "Dolandırıcılık"],
        "rows": 300, "cols": 12,
        "columns": "CustomerID, Age, Gender, TransactionDate, TransactionType, Amount, AccountType, BalanceBefore, BalanceAfter, BranchCode, Description, SuspiciousFlag",
        "source": "Örnek Veri (Yerel)",
        "local_file": "banking_transactions.csv",
        "url": None,
        "sample_rows": 300,
    },
    {
        "id": "loan_approval",
        "name": "Kredi Onayı Tahmini",
        "emoji": "✅",
        "desc": "Gelir, eğitim, mülkiyet durumu gibi faktörlere göre kredi onay/ret tahmini.",
        "tags": ["Kredi", "Onay", "Sınıflandırma"],
        "rows": 300, "cols": 13,
        "columns": "Loan_ID, Gender, Married, Dependents, Education, Self_Employed, ApplicantIncome, CoapplicantIncome, LoanAmount, Loan_Amount_Term, Credit_History, Property_Area, Loan_Status",
        "source": "Örnek Veri (Yerel)",
        "local_file": "loan_approval.csv",
        "url": "https://raw.githubusercontent.com/prasertcbs/basic-dataset/master/Loan-Approval-Prediction.csv",
        "sample_rows": 300,
    },
    {
        "id": "fraud_detection",
        "name": "Sahte İşlem Tespiti",
        "emoji": "🔍",
        "desc": "Banka transferi verisi. Sahte (fraud) ve normal işlemlerin makine öğrenmesiyle tespiti.",
        "tags": ["Dolandırıcılık", "Anomali", "Fintech"],
        "rows": 300, "cols": 11,
        "columns": "step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud",
        "source": "Örnek Veri (Yerel)",
        "local_file": "fraud_detection.csv",
        "url": None,
        "sample_rows": 300,
    },
    {
        "id": "german_credit",
        "name": "Alman Kredi Riski",
        "emoji": "🇩🇪",
        "desc": "UCI'nin klasik Alman kredi veri seti. 20 öznitelik, iyi/kötü kredi sınıflandırması.",
        "tags": ["Kredi Riski", "Klasik", "Sınıflandırma"],
        "rows": 300, "cols": 21,
        "columns": "checking_account, duration, credit_history, purpose, credit_amount, savings_account, employment, installment_rate, personal_status, other_debtors, residence_since, property, age, other_installments, housing, existing_credits, job, liable_people, telephone, foreign_worker, risk",
        "source": "Örnek Veri (Yerel)",
        "local_file": "german_credit.csv",
        "url": None,
        "sample_rows": 300,
    },
    {
        "id": "insurance_claims",
        "name": "Sigorta Talepleri",
        "emoji": "🏥",
        "desc": "Poliçe sahibi demografisi ve sigorta masrafları. Finansal sigortacılık modellemesi için.",
        "tags": ["Sigorta", "Talep", "Finans"],
        "rows": 300, "cols": 7,
        "columns": "age, sex, bmi, children, smoker, region, charges",
        "source": "Örnek Veri (Yerel)",
        "local_file": "insurance_claims.csv",
        "url": None,
        "sample_rows": 300,
    },
    {
        "id": "credit_card_churn",
        "name": "Kredi Kartı Müşteri Churn",
        "emoji": "💳",
        "desc": "Kredi kartı müşterisi terk analizi. Kullanım oranı, ürün sayısı ve demografik veriler.",
        "tags": ["Churn", "Kredi Kartı", "Müşteri"],
        "rows": 300, "cols": 18,
        "columns": "CLIENTNUM, Customer_Age, Gender, Dependent_count, Education_Level, Marital_Status, Income_Category, Card_Category, Months_on_book, Total_Relationship_Count, Months_Inactive_12_mon, Contacts_Count_12_mon, Credit_Limit, Total_Revolving_Bal, Avg_Open_To_Buy, Total_Trans_Amt, Avg_Utilization_Ratio, Attrition_Flag",
        "source": "Örnek Veri (Yerel)",
        "local_file": "credit_card_churn.csv",
        "url": None,
        "sample_rows": 300,
    },
]


# ─── PostgreSQL Bağlantı Bilgileri ────────────────────────────────────────────
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "twai_user",
    "password": "twai2024",
    "databases": {
        "bgts_banking": "🏦 Neurex Bankacılık (PostgreSQL)",
        "bgts_testdb":  "🧪 Neurex Test DB (PostgreSQL)",
    },
}

# ─── SQLite DB Kataloğu ───────────────────────────────────────────────────────
SQLITE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "engine" / "datasets" / "sqlite"

SQLITE_CATALOG: list[dict] = [
    {
        "id": "pg_bgts_banking",
        "file": None,
        "pg_db": "bgts_banking",
        "name": "🐘 Neurex Bankacılık (PostgreSQL)",
        "desc": "PostgreSQL'de 500 müşteri, 1039 hesap, 10.607 işlem, 300 kredi, 333 kart. Canlı DB!",
        "tables": ["customers", "accounts", "transactions", "loans", "cards", "branches"],
        "source": "PostgreSQL localhost:5432",
        "badge": "PG",
    },
    {
        "id": "banking_full",
        "file": "banking_full.db",
        "name": "🏦 Türk Bankacılık DB",
        "desc": "500 müşteri, 1039 hesap, 10.600+ işlem, 300 kredi, 333 kart. Türkçe gerçekçi veri.",
        "tables": ["customers", "accounts", "transactions", "loans", "cards", "branches"],
        "source": "Yerel (Oluşturuldu)",
        "badge": "HOT",
    },
    {
        "id": "chinook",
        "file": "chinook.sqlite",
        "name": "🎵 Chinook Dijital Mağaza",
        "desc": "iTunes verisiyle oluşturulmuş 11 tablolu dijital medya mağazası. Fatura, müşteri, çalışan.",
        "tables": ["Customer", "Invoice", "InvoiceLine", "Employee", "Track", "Album", "Artist"],
        "source": "GitHub (lerocha/chinook-database)",
        "badge": "GERÇEK",
    },
    {
        "id": "northwind",
        "file": "northwind.db",
        "name": "🛒 Northwind ERP",
        "desc": "Microsoft'un klasik ERP örneği. 93 müşteri, 16.000+ sipariş, 609.000+ sipariş detayı.",
        "tables": ["Customers", "Orders", "Order Details", "Products", "Employees", "Suppliers"],
        "source": "GitHub (jpwhite3/northwind-SQLite3)",
        "badge": "GERÇEK",
    },
]


# ─── Schemas ─────────────────────────────────────────────────────────────────

class DatasetLoadRequest(BaseModel):
    id: str
    sample_rows: Optional[int] = None


class GenerateSyntheticRequest(BaseModel):
    csv: str = Field(..., min_length=1)
    count: int = Field(default=100, ge=1, le=5000)
    name: Optional[str] = None
    format: str = Field(default="json", pattern="^(json|csv)$")


class SqliteTablesRequest(BaseModel):
    id: str


class SqlitePreviewRequest(BaseModel):
    id: str
    table: str
    limit: int = Field(default=200, ge=1, le=2000)


class SqliteLearnRequest(BaseModel):
    id: str
    table: str
    count: int = Field(default=200, ge=1, le=5000)
    format: str = Field(default="json", pattern="^(json|csv)$")
    train_rows: int = Field(default=500, ge=1, le=5000)


# ─── Yardımcılar ─────────────────────────────────────────────────────────────

def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _check_mostly() -> tuple[bool, Optional[str]]:
    """mostlyai paketinin kurulu olup olmadığını kontrol eder (v5+ SDK desteği)."""
    try:
        from mostlyai.sdk import MostlyAI  # noqa: F401
        return True, None
    except ImportError:
        try:
            import mostlyai  # noqa: F401
            return True, None
        except ImportError:
            return False, "mostlyai paketi kurulu değil. Lütfen: pip install mostlyai[local]"


def _get_mostly_version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("mostlyai")
    except Exception:
        pass
    try:
        import mostlyai
        return getattr(mostlyai, "__version__", "bilinmiyor")
    except Exception:
        return "bilinmiyor"


def _pg_connect(pg_db: str):
    import psycopg2
    return psycopg2.connect(
        host=PG_CONFIG["host"], port=PG_CONFIG["port"],
        user=PG_CONFIG["user"], password=PG_CONFIG["password"],
        dbname=pg_db,
    )


def _analyze_schema(catalog: dict, table_name: str) -> tuple[list[str], list[str]]:
    """Tablo şemasını analiz eder: FK ilişkileri, iş kuralları, veri tipleri."""
    import sqlite3
    rules: list[str] = []
    relations: list[str] = []
    try:
        if catalog.get("pg_db"):
            conn = _pg_connect(catalog["pg_db"])
            c = conn.cursor()
            c.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name=%s AND table_schema='public'
                ORDER BY ordinal_position
            """, (table_name,))
            cols = c.fetchall()
            c.execute("""
                SELECT kcu.column_name, ccu.table_name, ccu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name
                WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_name=%s
            """, (table_name,))
            for r in c.fetchall():
                relations.append(f"  {table_name}.{r[0]} → {r[1]}.{r[2]}")
            c.execute("""
                SELECT pgc.conname, pg_get_constraintdef(pgc.oid)
                FROM pg_constraint pgc
                JOIN pg_class pgcl ON pgcl.oid = pgc.conrelid
                WHERE pgcl.relname=%s AND pgc.contype='c'
            """, (table_name,))
            for r in c.fetchall():
                rules.append(f"  CHECK({r[1]})")
            c.execute("""
                SELECT pgc.conname, array_agg(a.attname)
                FROM pg_constraint pgc
                JOIN pg_class pgcl ON pgcl.oid = pgc.conrelid
                JOIN pg_attribute a ON a.attrelid = pgcl.oid AND a.attnum = ANY(pgc.conkey)
                WHERE pgcl.relname=%s AND pgc.contype='u'
                GROUP BY pgc.conname
            """, (table_name,))
            for r in c.fetchall():
                rules.append(f"  UNIQUE({', '.join(r[1])})")
            conn.close()
            for col in cols:
                cname, dtype, nullable, default = col
                if "amount" in cname.lower() or "price" in cname.lower() or "balance" in cname.lower():
                    rules.append(f"  {cname}: Sayısal alan (para birimi olabilir, negatif olmayabilir)")
                if "date" in cname.lower() or "time" in cname.lower():
                    rules.append(f"  {cname}: Tarih/zaman alanı")
                if cname.endswith("_id") or cname == "id":
                    rules.append(f"  {cname}: ID/anahtar alan")
                if "status" in cname.lower() or "type" in cname.lower():
                    rules.append(f"  {cname}: Kategori/enum alanı")
        else:
            path = SQLITE_DIR / catalog["file"]
            conn = sqlite3.connect(str(path))
            c = conn.cursor()
            cols = c.execute(f"PRAGMA table_info([{table_name}])").fetchall()
            fks = c.execute(f"PRAGMA foreign_key_list([{table_name}])").fetchall()
            for fk in fks:
                relations.append(f"  {table_name}.{fk[3]} → {fk[2]}.{fk[4]}")
            for col in cols:
                cname = col[1]; dtype = col[2]; notnull = col[3]; dflt = col[4]
                if "amount" in cname.lower() or "balance" in cname.lower():
                    rules.append(f"  {cname}: Para alanı (REAL/NUMERIC)")
                if "date" in cname.lower() or "time" in cname.lower():
                    rules.append(f"  {cname}: Tarih alanı")
                if cname.endswith("_id") or cname == "id":
                    rules.append(f"  {cname}: ID/PK alanı")
                if notnull:
                    rules.append(f"  {cname}: NOT NULL zorunlu")
            conn.close()
    except Exception as e:
        rules.append(f"  (Analiz hatası: {e})")
    return relations, rules


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/datasets", response_model=list[dict])
def list_datasets():
    """Mevcut bankacılık/finans veri setlerinin listesini döner."""
    return DATASETS


@router.post("/datasets/load")
def load_dataset(body: DatasetLoadRequest):
    """
    Seçilen veri setini indirir, ilk N satırını CSV olarak döner.
    """
    dataset = next((d for d in DATASETS if d["id"] == body.id), None)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Veri seti bulunamadı: {body.id}")

    n = body.sample_rows if body.sample_rows is not None else dataset["sample_rows"]

    try:
        import pandas as pd

        local_file = dataset.get("local_file")
        df = None

        if local_file:
            local_path = DATASETS_DIR / local_file
            if local_path.exists():
                df = pd.read_csv(local_path)

        if df is None:
            url = dataset.get("url")
            if not url:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Yerel dosya bulunamadı ve URL tanımlı değil")

            import requests as req
            resp = req.get(url, timeout=30, stream=True)
            resp.raise_for_status()

            chunks: list[bytes] = []
            size = 0
            max_bytes = 2 * 1024 * 1024
            for chunk in resp.iter_content(chunk_size=65536):
                chunks.append(chunk)
                size += len(chunk)
                if size >= max_bytes:
                    break
            raw = b"".join(chunks).decode("utf-8", errors="replace")
            df = pd.read_csv(io.StringIO(raw))

        sample_df = df.head(n)
        return {
            "csv": sample_df.to_csv(index=False),
            "rows": len(df),
            "sample_rows": len(sample_df),
            "cols": len(df.columns),
            "columns": df.columns.tolist(),
            "name": dataset["name"],
            "id": body.id,
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "local": (local_file is not None and (DATASETS_DIR / local_file).exists()),
        }

    except ImportError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="pandas kurulu değil. Lütfen: pip install pandas")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Yükleme hatası: {e}")


@router.get("/check-install")
def check_install():
    """Mostly AI paketinin kurulu olup olmadığını kontrol eder."""
    ok, err = _check_mostly()
    if ok:
        return {"installed": True, "version": _get_mostly_version()}
    return {"installed": False, "error": err}


@router.post("/install")
def install_mostly():
    """Mostly AI paketini otomatik kurar (SSE stream ile ilerlemeyi bildirir)."""
    import subprocess
    import sys

    def _stream():
        yield _sse({"type": "log", "msg": "📦 mostlyai[local] kuruluyor…"})
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "mostlyai[local]", "--quiet"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    yield _sse({"type": "log", "msg": line})
            proc.wait()
            if proc.returncode == 0:
                yield _sse({"type": "done", "success": True, "msg": "✅ mostlyai başarıyla kuruldu!"})
            else:
                yield _sse({"type": "done", "success": False, "msg": "❌ Kurulum başarısız."})
        except Exception as e:
            yield _sse({"type": "done", "success": False, "msg": f"Hata: {e}"})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate")
def generate_synthetic(body: GenerateSyntheticRequest):
    """
    Kullanıcının verdiği örnek CSV'yi alır, Mostly AI ile sentetik veri üretir.
    SSE stream ile ilerlemeyi bildirir.
    """
    ok, err = _check_mostly()
    if not ok:
        def _err_stream():
            yield _sse({"type": "error", "msg": err})
        return StreamingResponse(
            _err_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    csv_text = body.csv.strip()
    count = body.count
    name = (body.name or f"sim_{int(time.time())}")[:64]
    fmt = body.format

    def _stream():
        try:
            import pandas as pd

            yield _sse({"type": "log", "msg": "📥 Örnek veri okunuyor…"})
            try:
                df = pd.read_csv(io.StringIO(csv_text))
            except Exception as e:
                yield _sse({"type": "error", "msg": f"CSV ayrıştırma hatası: {e}"})
                return

            rows_in, cols_in = len(df), len(df.columns)
            yield _sse({"type": "log",
                        "msg": f"📊 {rows_in} satır × {cols_in} sütun okundu: {', '.join(df.columns.tolist())}"})

            yield _sse({"type": "log", "msg": "🤖 Mostly AI yerel motor başlatılıyor…"})
            from mostlyai.sdk import MostlyAI as _MAI
            mostly = _MAI(local=True, quiet=True)

            yield _sse({"type": "log", "msg": "🏋️ Model eğitiliyor (bu birkaç dakika sürebilir)…"})
            generator = mostly.train(data=df, name=name)

            yield _sse({"type": "log", "msg": f"✅ Model hazır. {count} satır sentetik veri üretiliyor…"})
            synthetic = mostly.generate(generator, size=count)
            syn_df = synthetic.data()

            yield _sse({"type": "log", "msg": f"🎉 {len(syn_df)} satır üretildi!"})

            out = syn_df.to_csv(index=False) if fmt == "csv" else \
                syn_df.to_json(orient="records", force_ascii=False, indent=2)

            yield _sse({
                "type": "done",
                "output": out,
                "rows": len(syn_df),
                "cols": syn_df.columns.tolist(),
                "format": fmt,
            })

        except Exception as e:
            tb = traceback.format_exc()
            yield _sse({"type": "error", "msg": str(e), "detail": tb})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sqlite/catalog")
def sqlite_catalog():
    """Mevcut SQLite + PostgreSQL veritabanı kataloğunu döner."""
    result = []
    for db in SQLITE_CATALOG:
        if db.get("pg_db"):
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=PG_CONFIG["host"], port=PG_CONFIG["port"],
                    user=PG_CONFIG["user"], password=PG_CONFIG["password"],
                    dbname=db["pg_db"], connect_timeout=3,
                )
                conn.close()
                result.append({**db, "exists": True, "size_mb": "PG", "type": "postgresql"})
            except Exception:
                result.append({**db, "exists": False, "size_mb": 0, "type": "postgresql"})
        else:
            path = SQLITE_DIR / db["file"]
            size_mb = round(path.stat().st_size / 1024 / 1024, 2) if path.exists() else 0
            result.append({**db, "exists": path.exists(), "size_mb": size_mb, "type": "sqlite"})
    return result


@router.post("/sqlite/tables")
def sqlite_tables(body: SqliteTablesRequest):
    """Seçilen DB'nin tablolarını ve satır sayılarını döner (SQLite + PostgreSQL)."""
    import sqlite3

    catalog = next((d for d in SQLITE_CATALOG if d["id"] == body.id), None)
    if not catalog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"DB bulunamadı: {body.id}")

    try:
        if catalog.get("pg_db"):
            conn = _pg_connect(catalog["pg_db"])
            c = conn.cursor()
            c.execute("""
                SELECT t.table_name,
                       pg_stat_user_tables.n_live_tup,
                       array_agg(column_name::text ORDER BY ordinal_position) as cols
                FROM information_schema.tables t
                JOIN information_schema.columns col
                  ON col.table_name = t.table_name AND col.table_schema = 'public'
                LEFT JOIN pg_stat_user_tables
                  ON pg_stat_user_tables.relname = t.table_name
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                GROUP BY t.table_name, pg_stat_user_tables.n_live_tup
                ORDER BY t.table_name
            """)
            result = []
            for row in c.fetchall():
                tbl, approx_count, cols = row
                c.execute(f'SELECT COUNT(*) FROM "{tbl}"')
                count = c.fetchone()[0]
                c.execute("""
                    SELECT kcu.column_name, ccu.table_name as ref_table
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                      ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_name = %s
                """, (tbl,))
                fks = [{"col": r[0], "ref": r[1]} for r in c.fetchall()]
                result.append({"table": tbl, "rows": count, "columns": cols or [], "foreign_keys": fks})
            conn.close()
        else:
            path = SQLITE_DIR / catalog["file"]
            if not path.exists():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="DB dosyası bulunamadı")
            conn = sqlite3.connect(str(path))
            c = conn.cursor()
            tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            result = []
            for (tbl,) in tables:
                try:
                    count = c.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()[0]
                    cols = [col[1] for col in c.execute(f"PRAGMA table_info([{tbl}])").fetchall()]
                    fks_raw = c.execute(f"PRAGMA foreign_key_list([{tbl}])").fetchall()
                    fks = [{"col": r[3], "ref": r[2]} for r in fks_raw]
                    result.append({"table": tbl, "rows": count, "columns": cols, "foreign_keys": fks})
                except Exception:
                    pass
            conn.close()

        return {
            "db": body.id, "name": catalog["name"], "tables": result,
            "type": "postgresql" if catalog.get("pg_db") else "sqlite",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/sqlite/preview")
def sqlite_preview(body: SqlitePreviewRequest):
    """Seçilen tablo verisini yükler — SQLite veya PostgreSQL."""
    import sqlite3

    catalog = next((d for d in SQLITE_CATALOG if d["id"] == body.id), None)
    if not catalog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"DB bulunamadı: {body.id}")

    try:
        import pandas as pd

        if catalog.get("pg_db"):
            conn = _pg_connect(catalog["pg_db"])
            df = pd.read_sql_query(f'SELECT * FROM "{body.table}" LIMIT {body.limit}', conn)
            cur = conn.cursor()
            cur.execute(f'SELECT COUNT(*) FROM "{body.table}"')
            total = cur.fetchone()[0]
        else:
            path = SQLITE_DIR / catalog["file"]
            if not path.exists():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="DB dosyası bulunamadı")
            conn = sqlite3.connect(str(path))
            df = pd.read_sql_query(f"SELECT * FROM [{body.table}] LIMIT {body.limit}", conn)
            total = conn.execute(f"SELECT COUNT(*) FROM [{body.table}]").fetchone()[0]
        conn.close()
        return {
            "csv": df.to_csv(index=False),
            "rows": total, "preview_rows": len(df),
            "cols": len(df.columns), "columns": df.columns.tolist(),
            "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
            "db": body.id, "table": body.table, "db_name": catalog["name"],
            "type": "postgresql" if catalog.get("pg_db") else "sqlite",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/sqlite/learn")
def sqlite_learn(body: SqliteLearnRequest):
    """DB tablosundan veri çeker → şema analizi → Mostly AI öğrenir → sentetik veri üretir. SSE stream."""
    ok, err = _check_mostly()
    if not ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=err)

    catalog = next((d for d in SQLITE_CATALOG if d["id"] == body.id), None)
    if not catalog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"DB bulunamadı: {body.id}")

    path = SQLITE_DIR / catalog.get("file", "") if not catalog.get("pg_db") else None

    def _stream():
        import sqlite3

        import pandas as pd

        try:
            yield _sse({"type": "log", "msg": f"🗄️ {catalog['name']} → [{body.table}] tablosu okunuyor…"})

            if catalog.get("pg_db"):
                conn = _pg_connect(catalog["pg_db"])
                df = pd.read_sql_query(f'SELECT * FROM "{body.table}" LIMIT {body.train_rows}', conn)
                cur = conn.cursor()
                cur.execute(f'SELECT COUNT(*) FROM "{body.table}"')
                total = cur.fetchone()[0]
                conn.close()
            else:
                conn = sqlite3.connect(str(path))
                df = pd.read_sql_query(f"SELECT * FROM [{body.table}] LIMIT {body.train_rows}", conn)
                total = conn.execute(f"SELECT COUNT(*) FROM [{body.table}]").fetchone()[0]
                conn.close()

            yield _sse({"type": "log", "msg": f"📊 {total:,} kayıttan {len(df)} satır alındı ({len(df.columns)} sütun)"})
            yield _sse({"type": "log", "msg": f"   Sütunlar: {', '.join(df.columns.tolist())}"})

            yield _sse({"type": "log", "msg": "🔬 Şema ve iş kuralları analiz ediliyor…"})
            relations, rules = _analyze_schema(catalog, body.table)
            schema_info = {"relations": relations, "rules": rules}

            if relations:
                yield _sse({"type": "schema", "title": "🔗 Tablo İlişkileri", "items": relations})
                for r in relations:
                    yield _sse({"type": "log", "msg": f"  🔗 {r.strip()}"})
            if rules:
                yield _sse({"type": "schema", "title": "📏 İş Kuralları", "items": rules})
                for r in rules[:6]:
                    yield _sse({"type": "log", "msg": f"  📏 {r.strip()}"})
                if len(rules) > 6:
                    yield _sse({"type": "log", "msg": f"  … ve {len(rules)-6} kural daha"})

            df = df.select_dtypes(exclude=["object"]).join(
                df.select_dtypes(include=["object"]).apply(
                    lambda col: col.astype(str).where(lambda s: s.str.len() < 100, other="[metin]")
                )
            )

            yield _sse({"type": "log", "msg": "🤖 Mostly AI yerel motor başlatılıyor…"})
            from mostlyai.sdk import MostlyAI as _MAI
            mostly = _MAI(local=True, quiet=True)

            model_name = f"{body.id}_{body.table}_{int(time.time())}"
            yield _sse({"type": "log", "msg": f"🏋️ '{body.table}' tablosu için model eğitiliyor…"})
            generator = mostly.train(data=df, name=model_name)

            yield _sse({"type": "log", "msg": f"✅ Model hazır! {body.count} satır sentetik veri üretiliyor…"})
            synthetic = mostly.generate(generator, size=body.count)
            syn_df = synthetic.data()

            yield _sse({"type": "log", "msg": f"🎉 {len(syn_df)} satır yeni sentetik veri üretildi!"})

            out = syn_df.to_csv(index=False) if body.format == "csv" else \
                syn_df.to_json(orient="records", force_ascii=False, indent=2)

            yield _sse({
                "type": "done",
                "output": out,
                "rows": len(syn_df),
                "cols": syn_df.columns.tolist(),
                "format": body.format,
                "source_db": catalog["name"],
                "source_table": body.table,
                "schema": schema_info,
            })

        except Exception as e:
            tb = traceback.format_exc()
            yield _sse({"type": "error", "msg": str(e), "detail": tb})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
