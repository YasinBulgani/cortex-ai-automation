"""
db.py — Sanal Veritabanı ve Test Geçmişi Yönetimi
SQLite tabanlı, test altyapısı için "mock" e-ticaret/kullanıcı verileri
ve test çalıştırma geçmişini (run_history) tutar.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

def _db_path() -> Path:
    from config.settings import settings
    return settings.DB_PATH

def get_connection():
    """SQLite veritabanı bağlantısı döndürür."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Tabloları oluşturur ve örnek verileri basar."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Test Geçmişi Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE,
                markers TEXT,
                passed INTEGER,
                failed INTEGER,
                duration_ms INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Mock Data: Kullanıcılar (E-Ticaret / Portal Senaryosu için)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password TEXT,
                role TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # 3. Mock Data: Ürünler (E-Ticaret Senaryosu)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL,
                category TEXT,
                stock INTEGER
            )
        """)

        # 4. Platform Kullanıcıları (Auth)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_verified BOOLEAN DEFAULT 0,
                verification_token TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Regresyon Setleri
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regression_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regression_set_features (
                set_id INTEGER,
                feature_name TEXT,
                FOREIGN KEY(set_id) REFERENCES regression_sets(id) ON DELETE CASCADE,
                UNIQUE(set_id, feature_name)
            )
        """)

        # 5. Manuel Testler (TestFLO Benzeri)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'Unexecuted',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_test_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER,
                step_order INTEGER,
                action TEXT NOT NULL,
                action_template TEXT,
                expected TEXT NOT NULL,
                status TEXT DEFAULT 'Unexecuted',
                FOREIGN KEY(test_id) REFERENCES manual_tests(id) ON DELETE CASCADE
            )
        """)

        # 6. Object Repository (XPath/CSS Seçicileri)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS object_repository (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                locator_value TEXT NOT NULL,
                page_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 7. Test Yönetimi: Projeler
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(owner_id) REFERENCES platform_users(id)
            )
        """)

        # 8. Modüller
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # 9. Test Case'ler
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                preconditions TEXT,
                priority TEXT DEFAULT 'P2',
                tags TEXT,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES platform_users(id)
            )
        """)

        # 10. Test Case Adımları
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_case_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_case_id INTEGER NOT NULL,
                step_order INTEGER NOT NULL,
                action TEXT NOT NULL,
                expected TEXT NOT NULL,
                FOREIGN KEY(test_case_id) REFERENCES test_cases(id) ON DELETE CASCADE
            )
        """)

        # 11. Sprint / Release
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                release_version TEXT,
                start_date DATE,
                end_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # 12. Manuel Test Koşusu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                sprint_id INTEGER,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'In Progress',
                started_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(sprint_id) REFERENCES sprints(id),
                FOREIGN KEY(started_by) REFERENCES platform_users(id)
            )
        """)

        # 13. Test Koşusu Sonuçları
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_run_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                test_case_id INTEGER NOT NULL,
                status TEXT DEFAULT 'Not Run',
                actual_result TEXT,
                notes TEXT,
                screenshot_path TEXT,
                executed_by INTEGER,
                executed_at DATETIME,
                FOREIGN KEY(run_id) REFERENCES manual_test_runs(id) ON DELETE CASCADE,
                FOREIGN KEY(test_case_id) REFERENCES test_cases(id),
                FOREIGN KEY(executed_by) REFERENCES platform_users(id)
            )
        """)

        # 14. Bug / Defect
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id INTEGER,
                test_case_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Open',
                jira_key TEXT,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(result_id) REFERENCES manual_run_results(id),
                FOREIGN KEY(test_case_id) REFERENCES test_cases(id),
                FOREIGN KEY(created_by) REFERENCES platform_users(id)
            )
        """)

        # 15. Pipeline Koşu Geçmişi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                test_id INTEGER,
                test_title TEXT,
                status TEXT DEFAULT 'running',
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME,
                allure_path TEXT,
                feature_path TEXT,
                mock_mode INTEGER DEFAULT 0,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        """)

        # platform_users tablosuna role kolonu ekle (migration)
        try:
            cursor.execute("ALTER TABLE platform_users ADD COLUMN role TEXT DEFAULT 'junior_qa'")
        except Exception:
            pass

        # Eğer mock_users boşsa birkaç örnek data atalım
        cursor.execute("SELECT COUNT(*) FROM mock_users")
        if cursor.fetchone()[0] == 0:
            users = [
                ("admin", "admin@test.com", "admin123", "admin", True),
                ("user1", "user1@test.com", "pass123", "customer", True),
                ("test_ai", "ai@test.com", "ai123", "customer", True)
            ]
            cursor.executemany(
                "INSERT INTO mock_users (username, email, password, role, is_active) VALUES (?, ?, ?, ?, ?)",
                users
            )
            
        # Eğer mock_products boşsa birkaç örnek ürün
        cursor.execute("SELECT COUNT(*) FROM mock_products")
        if cursor.fetchone()[0] == 0:
            products = [
                ("Playwright Pro Lisans", 199.99, "Software", 100),
                ("Otomasyon Kitabı", 29.50, "Books", 50),
                ("Mekanik Klavye", 89.00, "Hardware", 15)
            ]
            cursor.executemany(
                "INSERT INTO mock_products (name, price, category, stock) VALUES (?, ?, ?, ?)",
                products
            )
            
        conn.commit()

# --- RUN HISTORY API ---

def record_test_run(run_id: str, markers: str, passed: int, failed: int, duration_ms: int):
    """Test bitişinde istatistikleri DB'ye kaydeder.

    Python 3.12'de sqlite3 default datetime adapter deprecated. Değeri
    ISO 8601 string olarak kendimiz gönderiyoruz — CURRENT_TIMESTAMP ile
    uyumlu "YYYY-MM-DD HH:MM:SS" formatı (timestamp kolonu DATETIME).
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO test_runs (run_id, markers, passed, failed, duration_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (run_id, markers, passed, failed, duration_ms, ts))
        conn.commit()

def get_run_history(limit: int = 15):
    """Dashboard için son X test koşusunu getirir."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT run_id, markers, passed, failed, duration_ms, timestamp 
            FROM test_runs 
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_run_stats():
    """Genel dashboard istatistikleri."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_runs,
                SUM(passed) as total_passed,
                SUM(failed) as total_failed
            FROM test_runs
        """)
        row = dict(cursor.fetchone() or {})
        return {
            "total_runs": row.get("total_runs") or 0,
            "total_passed": row.get("total_passed") or 0,
            "total_failed": row.get("total_failed") or 0
        }

# --- REGRESSION SETS API ---

def create_regression_set(name: str):
    """Yeni bir regresyon seti oluşturur."""
    with get_connection() as conn:
        try:
            conn.execute("INSERT INTO regression_sets (name) VALUES (?)", (name,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def delete_regression_set(set_id: int):
    """Bir regresyon setini ve içindeki feature'ları siler."""
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM regression_sets WHERE id = ?", (set_id,))
        conn.commit()

def add_feature_to_set(set_id: int, feature_name: str):
    """Regresyon setine feature dosyası ekler."""
    with get_connection() as conn:
        try:
            conn.execute("INSERT INTO regression_set_features (set_id, feature_name) VALUES (?, ?)", 
                         (set_id, feature_name))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

def remove_feature_from_set(set_id: int, feature_name: str):
    """Regresyon setinden feature dosyasını çıkarır."""
    with get_connection() as conn:
        conn.execute("DELETE FROM regression_set_features WHERE set_id = ? AND feature_name = ?", 
                     (set_id, feature_name))
        conn.commit()

def get_regression_sets():
    """Tüm regresyon setlerini ve altındaki dosyaları getirir."""
    with get_connection() as conn:
        sets = conn.execute("SELECT id, name, created_at FROM regression_sets ORDER BY id DESC").fetchall()
        result = []
        for row in sets:
            set_dict = dict(row)
            feats = conn.execute("SELECT feature_name FROM regression_set_features WHERE set_id = ?", 
                                 (row['id'],)).fetchall()
            set_dict['features'] = [f['feature_name'] for f in feats]
            result.append(set_dict)
        return result

# --- MANUAL TESTS API (TestFLO Clone) ---

def create_manual_test(title: str):
    with get_connection() as conn:
        cursor = conn.execute("INSERT INTO manual_tests (title) VALUES (?)", (title,))
        conn.commit()
        return cursor.lastrowid

def delete_manual_test(test_id: int):
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM manual_tests WHERE id = ?", (test_id,))
        conn.commit()

def add_manual_step(test_id: int, action: str, expected: str):
    with get_connection() as conn:
        # Get max step_order
        max_order = conn.execute("SELECT MAX(step_order) FROM manual_test_steps WHERE test_id = ?", (test_id,)).fetchone()[0] or 0
        conn.execute("INSERT INTO manual_test_steps (test_id, step_order, action, expected) VALUES (?, ?, ?, ?)", 
                     (test_id, max_order + 1, action, expected))
        conn.commit()

def delete_manual_step(step_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM manual_test_steps WHERE id = ?", (step_id,))
        conn.commit()


def get_comprehensive_reports():
    """Gelişmiş analitik ve rapor grafikleri için metrikler döndürür."""
    with get_connection() as conn:
        # Genel Pass/Fail
        totals = conn.execute("SELECT SUM(passed) as p, SUM(failed) as f FROM test_runs").fetchone()
        p = totals["p"] or 0
        f = totals["f"] or 0
        
        # Süre Trendi (Son 20 Koşu)
        duration_rows = conn.execute("SELECT run_id, duration_ms as time, timestamp FROM test_runs ORDER BY id DESC LIMIT 20").fetchall()
        duration_trend = [{"run_id": r["run_id"], "time": r["time"], "date": r["timestamp"]} for r in reversed(duration_rows)]
        
        # Marker Bazlı Başarı
        marker_rows = conn.execute("SELECT markers, SUM(passed) as p, SUM(failed) as f FROM test_runs GROUP BY markers LIMIT 10").fetchall()
        marker_stats = [{"marker": r["markers"], "passed": r["p"] or 0, "failed": r["f"] or 0} for r in marker_rows]
        
        return {
            "overall_pass_fail": {"passed": p, "failed": f},
            "duration_trend": duration_trend,
            "marker_stats": marker_stats
        }

# ─────────────────────────────────────────────────────────────────────────────
# OBJECT REPOSITORY (XPATH LOCATORS)
# ─────────────────────────────────────────────────────────────────────────────

def get_locators():
    """Tüm kaydedilmiş XPath seçicilerini döndürür."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM object_repository ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

def save_locator(name: str, locator_value: str, page_url: str = "") -> int:
    """Yeni bir XPath kaydeder veya varsa günceller."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO object_repository (name, locator_value, page_url)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET locator_value=excluded.locator_value, page_url=excluded.page_url
        """, (name, locator_value, page_url))
        conn.commit()
        return cursor.lastrowid

def delete_locator(loc_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM object_repository WHERE id = ?", (loc_id,))
        conn.commit()

def resolve_locator(name_or_selector: str) -> str:
    """
    Verilen metin veritabanında 'name' olarak kayıtlıysa locator_value'yu döndürür.
    Değilse, verilen metni raw selector olarak geri döndürür.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT locator_value FROM object_repository WHERE name = ?", (name_or_selector,)).fetchone()
        if row:
            return row["locator_value"]
    return name_or_selector


def update_manual_step_status(step_id: int, status: str):
    with get_connection() as conn:
        conn.execute("UPDATE manual_test_steps SET status = ? WHERE id = ?", (status, step_id))
        conn.commit()
        # Also update parent test status if needed, but doing that at frontend or separate endpoint is easier
        
def update_manual_test_status(test_id: int, status: str):
    with get_connection() as conn:
        conn.execute("UPDATE manual_tests SET status = ? WHERE id = ?", (status, test_id))
        conn.commit()

def get_manual_tests():
    with get_connection() as conn:
        tests = conn.execute("SELECT id, title, status, created_at FROM manual_tests ORDER BY id DESC").fetchall()
        result = []
        for row in tests:
            t = dict(row)
            steps = conn.execute("SELECT id, step_order, action, expected, status FROM manual_test_steps WHERE test_id = ? ORDER BY step_order ASC", 
                                 (row['id'],)).fetchall()
            t['steps'] = [dict(s) for s in steps]
            result.append(t)
        return result

# ─── Auth (SaaS) İşlevleri ───────────────────────────────────────────────────

def create_platform_user(email: str, password_hash: str, token: str) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO platform_users (email, password_hash, verification_token) VALUES (?, ?, ?)",
                (email, password_hash, token)
            )
            conn.commit()
            return {"success": True, "id": cursor.lastrowid}
        except sqlite3.IntegrityError:
            return {"success": False, "error": "Bu e-posta adresi zaten kayıtlı."}

def get_platform_user_by_email(email: str):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM platform_users WHERE email = ?", (email,)).fetchone()

def get_platform_user_by_id(user_id: int):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM platform_users WHERE id = ?", (user_id,)).fetchone()

def verify_platform_user(token: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        user = cursor.execute("SELECT id FROM platform_users WHERE verification_token = ? AND is_verified = 0", (token,)).fetchone()
        if user:
            cursor.execute("UPDATE platform_users SET is_verified = 1, verification_token = NULL WHERE id = ?", (user['id'],))
            conn.commit()
            return True
        return False



# ─────────────────────────────────────────────────────────────────────────────
# PROJECTS
# ─────────────────────────────────────────────────────────────────────────────

def create_project(name: str, description: str = "", owner_id: int = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO projects (name, description, owner_id) VALUES (?, ?, ?)",
            (name, description, owner_id)
        )
        conn.commit()
        return cursor.lastrowid

def get_projects():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

def get_project(project_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None

def update_project(project_id: int, name: str, description: str = ""):
    with get_connection() as conn:
        conn.execute("UPDATE projects SET name = ?, description = ? WHERE id = ?", (name, description, project_id))
        conn.commit()

def delete_project(project_id: int):
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# MODULES
# ─────────────────────────────────────────────────────────────────────────────

def create_module(project_id: int, name: str, description: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO modules (project_id, name, description) VALUES (?, ?, ?)",
            (project_id, name, description)
        )
        conn.commit()
        return cursor.lastrowid

def get_modules(project_id: int):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM modules WHERE project_id = ? ORDER BY id ASC", (project_id,)).fetchall()
        return [dict(r) for r in rows]

def update_module(module_id: int, name: str, description: str = ""):
    with get_connection() as conn:
        conn.execute("UPDATE modules SET name = ?, description = ? WHERE id = ?", (name, description, module_id))
        conn.commit()

def delete_module(module_id: int):
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM modules WHERE id = ?", (module_id,))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# TEST CASES
# ─────────────────────────────────────────────────────────────────────────────

def create_test_case(module_id: int, title: str, description: str = "",
                     preconditions: str = "", priority: str = "P2",
                     tags: str = "", created_by: int = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO test_cases (module_id, title, description, preconditions, priority, tags, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (module_id, title, description, preconditions, priority, tags, created_by)
        )
        conn.commit()
        return cursor.lastrowid

def get_test_cases(module_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM test_cases WHERE module_id = ? ORDER BY id ASC", (module_id,)
        ).fetchall()
        result = []
        for row in rows:
            tc = dict(row)
            steps = conn.execute(
                "SELECT * FROM test_case_steps WHERE test_case_id = ? ORDER BY step_order ASC",
                (row['id'],)
            ).fetchall()
            tc['steps'] = [dict(s) for s in steps]
            result.append(tc)
        return result

def get_test_case(test_case_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM test_cases WHERE id = ?", (test_case_id,)).fetchone()
        if not row:
            return None
        tc = dict(row)
        steps = conn.execute(
            "SELECT * FROM test_case_steps WHERE test_case_id = ? ORDER BY step_order ASC",
            (test_case_id,)
        ).fetchall()
        tc['steps'] = [dict(s) for s in steps]
        return tc

def update_test_case(test_case_id: int, title: str, description: str = "",
                     preconditions: str = "", priority: str = "P2", tags: str = ""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE test_cases SET title=?, description=?, preconditions=?, priority=?, tags=?
               WHERE id=?""",
            (title, description, preconditions, priority, tags, test_case_id)
        )
        conn.commit()

def delete_test_case(test_case_id: int):
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM test_cases WHERE id = ?", (test_case_id,))
        conn.commit()

def add_test_case_step(test_case_id: int, action: str, expected: str) -> int:
    with get_connection() as conn:
        max_order = conn.execute(
            "SELECT MAX(step_order) FROM test_case_steps WHERE test_case_id = ?", (test_case_id,)
        ).fetchone()[0] or 0
        cursor = conn.execute(
            "INSERT INTO test_case_steps (test_case_id, step_order, action, expected) VALUES (?, ?, ?, ?)",
            (test_case_id, max_order + 1, action, expected)
        )
        conn.commit()
        return cursor.lastrowid

def delete_test_case_step(step_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM test_case_steps WHERE id = ?", (step_id,))
        conn.commit()

def bulk_create_test_cases(module_id: int, cases: list, created_by: int = None):
    """AI önizlemeden onaylanan test case'leri toplu kaydeder."""
    created_ids = []
    for case in cases:
        tc_id = create_test_case(
            module_id=module_id,
            title=case.get('title', ''),
            description=case.get('description', ''),
            preconditions=case.get('preconditions', ''),
            priority=case.get('priority', 'P2'),
            tags=case.get('tags', ''),
            created_by=created_by
        )
        for step in case.get('steps', []):
            add_test_case_step(tc_id, step.get('action', ''), step.get('expected', ''))
        created_ids.append(tc_id)
    return created_ids


# ─────────────────────────────────────────────────────────────────────────────
# SPRINTS
# ─────────────────────────────────────────────────────────────────────────────

def create_sprint(project_id: int, name: str, release_version: str = "",
                  start_date: str = None, end_date: str = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO sprints (project_id, name, release_version, start_date, end_date) VALUES (?, ?, ?, ?, ?)",
            (project_id, name, release_version, start_date, end_date)
        )
        conn.commit()
        return cursor.lastrowid

def get_sprints(project_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sprints WHERE project_id = ? ORDER BY id DESC", (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def delete_sprint(sprint_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM sprints WHERE id = ?", (sprint_id,))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# MANUAL TEST RUNS
# ─────────────────────────────────────────────────────────────────────────────

def create_manual_test_run(project_id: int, name: str,
                           sprint_id: int = None, started_by: int = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO manual_test_runs (project_id, sprint_id, name, started_by) VALUES (?, ?, ?, ?)",
            (project_id, sprint_id, name, started_by)
        )
        conn.commit()
        run_id = cursor.lastrowid
        # Projedeki tüm test case'leri bu run'a ekle (Not Run olarak)
        cases = conn.execute(
            """SELECT tc.id FROM test_cases tc
               JOIN modules m ON tc.module_id = m.id
               WHERE m.project_id = ?""", (project_id,)
        ).fetchall()
        for c in cases:
            conn.execute(
                "INSERT INTO manual_run_results (run_id, test_case_id) VALUES (?, ?)",
                (run_id, c['id'])
            )
        conn.commit()
        return run_id

def get_manual_test_runs(project_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.*, s.name as sprint_name, u.email as started_by_email
               FROM manual_test_runs r
               LEFT JOIN sprints s ON r.sprint_id = s.id
               LEFT JOIN platform_users u ON r.started_by = u.id
               WHERE r.project_id = ? ORDER BY r.id DESC""",
            (project_id,)
        ).fetchall()
        result = []
        for row in rows:
            run = dict(row)
            stats = conn.execute(
                """SELECT status, COUNT(*) as cnt FROM manual_run_results
                   WHERE run_id = ? GROUP BY status""", (row['id'],)
            ).fetchall()
            run['stats'] = {s['status']: s['cnt'] for s in stats}
            result.append(run)
        return result

def get_manual_test_run_results(run_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT rr.*, tc.title, tc.priority, tc.tags,
                      m.name as module_name
               FROM manual_run_results rr
               JOIN test_cases tc ON rr.test_case_id = tc.id
               JOIN modules m ON tc.module_id = m.id
               WHERE rr.run_id = ? ORDER BY rr.id ASC""",
            (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def update_run_result(result_id: int, status: str, actual_result: str = "",
                      notes: str = "", executed_by: int = None):
    with get_connection() as conn:
        conn.execute(
            """UPDATE manual_run_results
               SET status=?, actual_result=?, notes=?, executed_by=?, executed_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (status, actual_result, notes, executed_by, result_id)
        )
        conn.commit()

def close_manual_test_run(run_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE manual_test_runs SET status = 'Closed' WHERE id = ?", (run_id,))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# BUGS
# ─────────────────────────────────────────────────────────────────────────────

def create_bug(title: str, description: str = "", severity: str = "Medium",
               result_id: int = None, test_case_id: int = None,
               created_by: int = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO bugs (title, description, severity, result_id, test_case_id, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, description, severity, result_id, test_case_id, created_by)
        )
        conn.commit()
        return cursor.lastrowid

def get_bugs(project_id: int = None):
    with get_connection() as conn:
        if project_id:
            rows = conn.execute(
                """SELECT b.*, u.email as created_by_email
                   FROM bugs b
                   LEFT JOIN platform_users u ON b.created_by = u.id
                   LEFT JOIN manual_run_results rr ON b.result_id = rr.id
                   LEFT JOIN manual_test_runs mtr ON rr.run_id = mtr.id
                   WHERE mtr.project_id = ? OR b.test_case_id IN (
                       SELECT tc.id FROM test_cases tc
                       JOIN modules m ON tc.module_id = m.id
                       WHERE m.project_id = ?
                   )
                   ORDER BY b.id DESC""", (project_id, project_id)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT b.*, u.email as created_by_email
                   FROM bugs b LEFT JOIN platform_users u ON b.created_by = u.id
                   ORDER BY b.id DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

def update_bug_status(bug_id: int, status: str):
    with get_connection() as conn:
        conn.execute("UPDATE bugs SET status = ? WHERE id = ?", (status, bug_id))
        conn.commit()

def update_bug_jira_key(bug_id: int, jira_key: str):
    with get_connection() as conn:
        conn.execute("UPDATE bugs SET jira_key = ? WHERE id = ?", (jira_key, bug_id))
        conn.commit()

def delete_bug(bug_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE RUNS
# ─────────────────────────────────────────────────────────────────────────────

def create_pipeline_run(project_id: int = None, test_id: int = None,
                        test_title: str = "", feature_path: str = "",
                        mock_mode: bool = False) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO pipeline_runs (project_id, test_id, test_title, feature_path, mock_mode, status)
               VALUES (?, ?, ?, ?, ?, 'running')""",
            (project_id, test_id, test_title, feature_path, int(mock_mode))
        )
        conn.commit()
        return cursor.lastrowid

def complete_pipeline_run(run_id: int, status: str, allure_path: str = ""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE pipeline_runs SET status=?, ended_at=CURRENT_TIMESTAMP, allure_path=?
               WHERE id=?""",
            (status, allure_path, run_id)
        )
        conn.commit()

def list_pipeline_runs(project_id: int = None, limit: int = 50):
    with get_connection() as conn:
        if project_id:
            rows = conn.execute(
                """SELECT * FROM pipeline_runs WHERE project_id=?
                   ORDER BY id DESC LIMIT ?""",
                (project_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# RAPORLAMA
# ─────────────────────────────────────────────────────────────────────────────

def get_project_report(project_id: int) -> dict:
    """Proje bazlı test coverage ve pass/fail raporu."""
    with get_connection() as conn:
        total_cases = conn.execute(
            """SELECT COUNT(*) FROM test_cases tc
               JOIN modules m ON tc.module_id = m.id
               WHERE m.project_id = ?""", (project_id,)
        ).fetchone()[0]

        runs = conn.execute(
            "SELECT COUNT(*) FROM manual_test_runs WHERE project_id = ?", (project_id,)
        ).fetchone()[0]

        result_stats = conn.execute(
            """SELECT rr.status, COUNT(*) as cnt
               FROM manual_run_results rr
               JOIN manual_test_runs mtr ON rr.run_id = mtr.id
               WHERE mtr.project_id = ? GROUP BY rr.status""", (project_id,)
        ).fetchall()
        stats = {s['status']: s['cnt'] for s in result_stats}

        bug_count = conn.execute(
            """SELECT COUNT(*) FROM bugs b
               LEFT JOIN manual_run_results rr ON b.result_id = rr.id
               LEFT JOIN manual_test_runs mtr ON rr.run_id = mtr.id
               WHERE mtr.project_id = ?""", (project_id,)
        ).fetchone()[0]

        module_coverage = conn.execute(
            """SELECT m.name, COUNT(tc.id) as case_count
               FROM modules m LEFT JOIN test_cases tc ON tc.module_id = m.id
               WHERE m.project_id = ? GROUP BY m.id""", (project_id,)
        ).fetchall()

        return {
            "total_cases": total_cases,
            "total_runs": runs,
            "result_stats": stats,
            "bug_count": bug_count,
            "module_coverage": [dict(r) for r in module_coverage]
        }
