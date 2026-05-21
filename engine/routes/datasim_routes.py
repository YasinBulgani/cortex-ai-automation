"""
datasim_routes.py — Mostly AI tabanlı sentetik veri üretim endpoint'leri
"""
import io
import json
import time
import traceback
from pathlib import Path
from flask import Blueprint, request, jsonify, Response, stream_with_context

# Yerel örnek veri setleri klasörü
DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"

datasim_bp = Blueprint('datasim', __name__)


# ─── Katalog: Bankacılık / Finans veri setleri ────────────────────────────────
DATASETS = [
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


# ─── /api/datasim/datasets ───────────────────────────────────────────────────
@datasim_bp.route('/api/datasim/datasets', methods=['GET'])
def list_datasets():
    """Mevcut bankacılık/finans veri setlerinin listesini döner."""
    return jsonify(DATASETS)


# ─── /api/datasim/datasets/load ─────────────────────────────────────────────
@datasim_bp.route('/api/datasim/datasets/load', methods=['POST'])
def load_dataset():
    """
    Seçilen veri setini indirir, ilk N satırını CSV olarak döner.

    Body (JSON):
        id          : str  - Dataset ID
        sample_rows : int  - Kaç satır dönsün (varsayılan: veri setinin sample_rows değeri)
    """
    import requests as req

    body = request.get_json(silent=True) or {}
    ds_id = body.get('id', '')
    dataset = next((d for d in DATASETS if d['id'] == ds_id), None)
    if not dataset:
        return jsonify({"error": f"Veri seti bulunamadı: {ds_id}"}), 404

    n = int(body.get('sample_rows', dataset['sample_rows']))

    try:
        import pandas as pd

        # ── Önce yerel dosyayı dene ──────────────────────────────────────
        local_file = dataset.get('local_file')
        df = None

        if local_file:
            local_path = DATASETS_DIR / local_file
            if local_path.exists():
                df = pd.read_csv(local_path)

        # ── Yerel dosya yoksa internetten indir ──────────────────────────
        if df is None:
            url = dataset.get('url')
            if not url:
                return jsonify({"error": "Yerel dosya bulunamadı ve URL tanımlı değil"}), 404

            import requests as req
            resp = req.get(url, timeout=30, stream=True)
            resp.raise_for_status()

            chunks = []; size = 0; max_bytes = 2 * 1024 * 1024
            for chunk in resp.iter_content(chunk_size=65536):
                chunks.append(chunk); size += len(chunk)
                if size >= max_bytes: break
            raw = b''.join(chunks).decode('utf-8', errors='replace')
            df = pd.read_csv(io.StringIO(raw))

        sample_df = df.head(n)
        csv_out = sample_df.to_csv(index=False)

        return jsonify({
            "csv": csv_out,
            "rows": len(df),
            "sample_rows": len(sample_df),
            "cols": len(df.columns),
            "columns": df.columns.tolist(),
            "name": dataset['name'],
            "id": ds_id,
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "local": (local_file is not None and (DATASETS_DIR / local_file).exists()),
        })

    except ImportError:
        return jsonify({"error": "pandas kurulu değil. Lütfen: pip install pandas"}), 503
    except Exception as e:
        return jsonify({"error": f"Yükleme hatası: {e}"}), 500


# ─── Mostly AI kurulum durumunu kontrol et ────────────────────────────────────
def _check_mostly():
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


def _get_mostly_version():
    """mostlyai sürümünü döner."""
    try:
        import importlib.metadata
        return importlib.metadata.version('mostlyai')
    except Exception:
        pass
    try:
        import mostlyai
        return getattr(mostlyai, '__version__', 'bilinmiyor')
    except Exception:
        return 'bilinmiyor'


# ─── /api/datasim/check-install ──────────────────────────────────────────────
@datasim_bp.route('/api/datasim/check-install', methods=['GET'])
def check_install():
    ok, err = _check_mostly()
    if ok:
        ver = _get_mostly_version()
        return jsonify({"installed": True, "version": ver})
    return jsonify({"installed": False, "error": err})


# ─── /api/datasim/install ────────────────────────────────────────────────────
@datasim_bp.route('/api/datasim/install', methods=['POST'])
def install_mostly():
    """Mostly AI paketini otomatik kurar (SSE stream ile ilerlemeyi bildirir)."""
    import subprocess, sys

    def _stream():
        yield _sse({"type": "log", "msg": "📦 mostlyai[local] kuruluyor…"})
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "mostlyai[local]", "--quiet"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
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

    return Response(stream_with_context(_stream()),
                    mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ─── /api/datasim/generate ───────────────────────────────────────────────────
@datasim_bp.route('/api/datasim/generate', methods=['POST'])
def generate_synthetic():
    """
    Kullanıcının verdiği örnek CSV'yi alır, Mostly AI ile sentetik veri üretir.

    Body (JSON):
        csv      : str   - Örnek veri CSV metni
        count    : int   - Üretilecek satır sayısı (varsayılan 100)
        name     : str   - Model adı (isteğe bağlı)
        format   : str   - "json" | "csv" (varsayılan "json")
    """
    ok, err = _check_mostly()
    if not ok:
        def _err_stream():
            yield f"data: {json.dumps({'type': 'error', 'msg': err}, ensure_ascii=False)}\n\n"
        from flask import Response, stream_with_context
        return Response(stream_with_context(_err_stream()), 
                        mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    body = request.get_json(silent=True) or {}
    csv_text = (body.get('csv') or '').strip()
    count    = max(1, min(int(body.get('count', 100)), 5000))
    name     = (body.get('name') or f'sim_{int(time.time())}')[:64]
    fmt      = body.get('format', 'json')

    if not csv_text:
        return jsonify({"error": "CSV verisi boş olamaz"}), 400

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

            if fmt == 'csv':
                out = syn_df.to_csv(index=False)
            else:
                out = syn_df.to_json(orient='records', force_ascii=False, indent=2)

            yield _sse({
                "type": "done",
                "output": out,
                "rows": len(syn_df),
                "cols": syn_df.columns.tolist(),
                "format": fmt
            })

        except Exception as e:
            tb = traceback.format_exc()
            yield _sse({"type": "error", "msg": str(e), "detail": tb})

    return Response(stream_with_context(_stream()),
                    mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ─── PostgreSQL Bağlantı Bilgileri ────────────────────────────────────────────
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "twai_user",
    "password": "twai2024",
    "databases": {
        "bgts_banking": "🏦 TestwrightAI Bankacılık (PostgreSQL)",
        "bgts_testdb":  "🧪 TestwrightAI Test DB (PostgreSQL)",
    }
}

# ─── SQLite DB Kataloğu ───────────────────────────────────────────────────────
SQLITE_DIR = Path(__file__).resolve().parent.parent / "datasets" / "sqlite"

SQLITE_CATALOG = [
    {
        "id": "pg_bgts_banking",
        "file": None,
        "pg_db": "bgts_banking",
        "name": "🐘 TestwrightAI Bankacılık (PostgreSQL)",
        "desc": "PostgreSQL'de 500 müşteri, 1039 hesap, 10.607 işlem, 300 kredi, 333 kart. Canlı DB!",
        "tables": ["customers", "accounts", "transactions", "loans", "cards", "branches"],
        "source": "PostgreSQL localhost:5432",
        "badge": "PG"
    },
    {
        "id": "banking_full",
        "file": "banking_full.db",
        "name": "🏦 Türk Bankacılık DB",
        "desc": "500 müşteri, 1039 hesap, 10.600+ işlem, 300 kredi, 333 kart. Türkçe gerçekçi veri.",
        "tables": ["customers", "accounts", "transactions", "loans", "cards", "branches"],
        "source": "Yerel (Oluşturuldu)",
        "badge": "HOT"
    },
    {
        "id": "chinook",
        "file": "chinook.sqlite",
        "name": "🎵 Chinook Dijital Mağaza",
        "desc": "iTunes verisiyle oluşturulmuş 11 tablolu dijital medya mağazası. Fatura, müşteri, çalışan.",
        "tables": ["Customer", "Invoice", "InvoiceLine", "Employee", "Track", "Album", "Artist"],
        "source": "GitHub (lerocha/chinook-database)",
        "badge": "GERÇEK"
    },
    {
        "id": "northwind",
        "file": "northwind.db",
        "name": "🛒 Northwind ERP",
        "desc": "Microsoft'un klasik ERP örneği. 93 müşteri, 16.000+ sipariş, 609.000+ sipariş detayı.",
        "tables": ["Customers", "Orders", "Order Details", "Products", "Employees", "Suppliers"],
        "source": "GitHub (jpwhite3/northwind-SQLite3)",
        "badge": "GERÇEK"
    },
]


@datasim_bp.route('/api/datasim/sqlite/catalog', methods=['GET'])
def sqlite_catalog():
    """Mevcut SQLite + PostgreSQL veritabanı kataloğunu döner."""
    result = []
    for db in SQLITE_CATALOG:
        if db.get('pg_db'):
            # PostgreSQL DB
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=PG_CONFIG['host'], port=PG_CONFIG['port'],
                    user=PG_CONFIG['user'], password=PG_CONFIG['password'],
                    dbname=db['pg_db'], connect_timeout=3
                )
                conn.close()
                result.append({**db, "exists": True, "size_mb": "PG", "type": "postgresql"})
            except Exception:
                result.append({**db, "exists": False, "size_mb": 0, "type": "postgresql"})
        else:
            # SQLite DB
            path = SQLITE_DIR / db['file']
            size_mb = round(path.stat().st_size / 1024 / 1024, 2) if path.exists() else 0
            result.append({**db, "exists": path.exists(), "size_mb": size_mb, "type": "sqlite"})
    return jsonify(result)


def _pg_connect(pg_db):
    import psycopg2
    return psycopg2.connect(
        host=PG_CONFIG['host'], port=PG_CONFIG['port'],
        user=PG_CONFIG['user'], password=PG_CONFIG['password'],
        dbname=pg_db
    )


@datasim_bp.route('/api/datasim/sqlite/tables', methods=['POST'])
def sqlite_tables():
    """Seçilen DB'nin tablolarını ve satır sayılarını döner (SQLite + PostgreSQL)."""
    import sqlite3
    body = request.get_json(silent=True) or {}
    db_id = body.get('id', '')
    catalog = next((d for d in SQLITE_CATALOG if d['id'] == db_id), None)
    if not catalog:
        return jsonify({"error": f"DB bulunamadı: {db_id}"}), 404

    try:
        if catalog.get('pg_db'):
            # PostgreSQL
            conn = _pg_connect(catalog['pg_db'])
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
                # Kesin sayım
                c.execute(f'SELECT COUNT(*) FROM "{tbl}"')
                count = c.fetchone()[0]
                # FK ilişkileri
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
            # SQLite
            path = SQLITE_DIR / catalog['file']
            if not path.exists():
                return jsonify({"error": "DB dosyası bulunamadı"}), 404
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
        return jsonify({"db": db_id, "name": catalog['name'], "tables": result,
                        "type": "postgresql" if catalog.get('pg_db') else "sqlite"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@datasim_bp.route('/api/datasim/sqlite/preview', methods=['POST'])
def sqlite_preview():
    """Seçilen tablo verisini yükler — SQLite veya PostgreSQL."""
    import sqlite3, pandas as pd
    body = request.get_json(silent=True) or {}
    db_id = body.get('id', '')
    table = body.get('table', '')
    limit = min(int(body.get('limit', 200)), 2000)

    catalog = next((d for d in SQLITE_CATALOG if d['id'] == db_id), None)
    if not catalog:
        return jsonify({"error": f"DB bulunamadı: {db_id}"}), 404

    try:
        if catalog.get('pg_db'):
            conn = _pg_connect(catalog['pg_db'])
            df = pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT {limit}', conn)
            cur = conn.cursor()
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            total = cur.fetchone()[0]
        else:
            path = SQLITE_DIR / catalog['file']
            if not path.exists():
                return jsonify({"error": "DB dosyası bulunamadı"}), 404
            conn = sqlite3.connect(str(path))
            df = pd.read_sql_query(f'SELECT * FROM [{table}] LIMIT {limit}', conn)
            total = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        conn.close()
        return jsonify({
            "csv": df.to_csv(index=False),
            "rows": total, "preview_rows": len(df),
            "cols": len(df.columns), "columns": df.columns.tolist(),
            "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
            "db": db_id, "table": table, "db_name": catalog['name'],
            "type": "postgresql" if catalog.get('pg_db') else "sqlite"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _analyze_schema(catalog, table_name):
    """Tablo şemasını analiz eder: FK ilişkileri, iş kuralları, veri tipleri."""
    import sqlite3
    rules = []
    relations = []
    try:
        if catalog.get('pg_db'):
            conn = _pg_connect(catalog['pg_db'])
            c = conn.cursor()
            # Sütun bilgileri
            c.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name=%s AND table_schema='public'
                ORDER BY ordinal_position
            """, (table_name,))
            cols = c.fetchall()
            # FK ilişkileri
            c.execute("""
                SELECT kcu.column_name, ccu.table_name, ccu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name
                WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_name=%s
            """, (table_name,))
            for r in c.fetchall():
                relations.append(f"  {table_name}.{r[0]} → {r[1]}.{r[2]}")
            # CHECK constraints
            c.execute("""
                SELECT pgc.conname, pg_get_constraintdef(pgc.oid)
                FROM pg_constraint pgc
                JOIN pg_class pgcl ON pgcl.oid = pgc.conrelid
                WHERE pgcl.relname=%s AND pgc.contype='c'
            """, (table_name,))
            for r in c.fetchall():
                rules.append(f"  CHECK({r[1]})")
            # Unique constraints
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
            # Otomatik iş kuralı çıkarımı
            for col in cols:
                cname, dtype, nullable, default = col
                if 'amount' in cname.lower() or 'price' in cname.lower() or 'balance' in cname.lower():
                    rules.append(f"  {cname}: Sayısal alan (para birimi olabilir, negatif olmayabilir)")
                if 'date' in cname.lower() or 'time' in cname.lower():
                    rules.append(f"  {cname}: Tarih/zaman alanı")
                if cname.endswith('_id') or cname == 'id':
                    rules.append(f"  {cname}: ID/anahtar alan")
                if 'status' in cname.lower() or 'type' in cname.lower():
                    rules.append(f"  {cname}: Kategori/enum alanı")
        else:
            path = SQLITE_DIR / catalog['file']
            conn = sqlite3.connect(str(path))
            c = conn.cursor()
            cols = c.execute(f"PRAGMA table_info([{table_name}])").fetchall()
            fks = c.execute(f"PRAGMA foreign_key_list([{table_name}])").fetchall()
            for fk in fks:
                relations.append(f"  {table_name}.{fk[3]} → {fk[2]}.{fk[4]}")
            for col in cols:
                cname = col[1]; dtype = col[2]; notnull = col[3]; dflt = col[4]
                if 'amount' in cname.lower() or 'balance' in cname.lower():
                    rules.append(f"  {cname}: Para alanı (REAL/NUMERIC)")
                if 'date' in cname.lower() or 'time' in cname.lower():
                    rules.append(f"  {cname}: Tarih alanı")
                if cname.endswith('_id') or cname == 'id':
                    rules.append(f"  {cname}: ID/PK alanı")
                if notnull: rules.append(f"  {cname}: NOT NULL zorunlu")
            conn.close()
    except Exception as e:
        rules.append(f"  (Analiz hatası: {e})")
    return relations, rules


@datasim_bp.route('/api/datasim/sqlite/learn', methods=['POST'])
def sqlite_learn():
    """DB tablosundan veri çeker → şema analizi → Mostly AI öğrenir → sentetik veri üretir."""
    ok, err = _check_mostly()
    if not ok:
        return jsonify({"error": err}), 503

    import sqlite3, pandas as pd

    body = request.get_json(silent=True) or {}
    db_id  = body.get('id', '')
    table  = body.get('table', '')
    count  = max(1, min(int(body.get('count', 200)), 5000))
    fmt    = body.get('format', 'json')
    limit  = min(int(body.get('train_rows', 500)), 5000)

    catalog = next((d for d in SQLITE_CATALOG if d['id'] == db_id), None)
    if not catalog:
        return jsonify({"error": f"DB bulunamadı: {db_id}"}), 404

    path = SQLITE_DIR / catalog.get('file', '') if not catalog.get('pg_db') else None

    def _stream():
        try:
            yield _sse({"type": "log", "msg": f"🗄️ {catalog['name']} → [{table}] tablosu okunuyor…"})

            # ── Veri oku ──────────────────────────────────────────────────
            if catalog.get('pg_db'):
                conn = _pg_connect(catalog['pg_db'])
                df = pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT {limit}', conn)
                cur = conn.cursor(); cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                total = cur.fetchone()[0]; conn.close()
            else:
                conn = __import__('sqlite3').connect(str(path))
                df = pd.read_sql_query(f'SELECT * FROM [{table}] LIMIT {limit}', conn)
                total = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]; conn.close()

            yield _sse({"type": "log", "msg": f"📊 {total:,} kayıttan {len(df)} satır alındı ({len(df.columns)} sütun)"})
            yield _sse({"type": "log", "msg": f"   Sütunlar: {', '.join(df.columns.tolist())}"})

            # ── Şema + İş Kuralı Analizi ──────────────────────────────────
            yield _sse({"type": "log", "msg": "🔬 Şema ve iş kuralları analiz ediliyor…"})
            relations, rules = _analyze_schema(catalog, table)
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

            # ── Veri temizleme ────────────────────────────────────────────
            df = df.select_dtypes(exclude=['object']) \
                   .join(df.select_dtypes(include=['object']).apply(
                       lambda col: col.astype(str).where(lambda s: s.str.len() < 100, other='[metin]')
                   ))

            # ── Mostly AI eğitim ──────────────────────────────────────────
            yield _sse({"type": "log", "msg": "🤖 Mostly AI yerel motor başlatılıyor…"})
            from mostlyai.sdk import MostlyAI as _MAI
            mostly = _MAI(local=True, quiet=True)

            model_name = f"{db_id}_{table}_{int(time.time())}"
            yield _sse({"type": "log", "msg": f"🏋️ '{table}' tablosu için model eğitiliyor…"})
            generator = mostly.train(data=df, name=model_name)

            yield _sse({"type": "log", "msg": f"✅ Model hazır! {count} satır sentetik veri üretiliyor…"})
            synthetic = mostly.generate(generator, size=count)
            syn_df = synthetic.data()

            yield _sse({"type": "log", "msg": f"🎉 {len(syn_df)} satır yeni sentetik veri üretildi!"})

            out = syn_df.to_csv(index=False) if fmt == 'csv' else \
                  syn_df.to_json(orient='records', force_ascii=False, indent=2)

            yield _sse({
                "type": "done",
                "output": out,
                "rows": len(syn_df),
                "cols": syn_df.columns.tolist(),
                "format": fmt,
                "source_db": catalog['name'],
                "source_table": table,
                "schema": schema_info,
            })

        except Exception as e:
            tb = traceback.format_exc()
            yield _sse({"type": "error", "msg": str(e), "detail": tb})

    return Response(stream_with_context(_stream()),
                    mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ─── Yardımcı ────────────────────────────────────────────────────────────────
def _sse(obj):
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"
