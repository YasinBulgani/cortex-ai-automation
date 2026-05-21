# Agent 4: In-Memory Storage → Veritabani Migrasyonu

## Cursor'a yapistir:

```
Sen bir backend muhendisisin. BGTS bankacilik test otomasyon platformundaki
in-memory storage kullanan yerleri veritabanina tasiyacaksin. Restart'ta veri
kaybini engelleyeceksin.

## KURALLAR
- Python 3.9 uyumlu
- Tum dosyalar ast.parse gecmeli
- Mevcut endpoint imzalarini (path, method, request/response body) DEGISTIRME
- SQLAlchemy text() kullan (ORM model olusturmak yerine raw SQL)

## SORUN 1: CI/CD Webhook Events (VERI KAYBI)

### Mevcut Durum
Dosya: `backend/app/domains/cicd/router.py`
- Modül seviyesinde: `_events: list[dict] = []` ve `_MAX_EVENTS = 500`
- Tum webhook event'leri bu listeye ekleniyor
- Uygulama restart olunca TUMU kayboluyor
- Bankacilik ortaminda audit trail ZORUNLU — bu kabul edilemez

### Cozum

#### Adim 1: Alembic migration olustur
Dosya: `backend/alembic/versions/20260416_0004_add_cicd_events.py`

```python
"""Add CI/CD webhook events table

CI/CD webhook event'leri icin kalici depolama.
In-memory list yerine PostgreSQL tablosu.

Revision ID: cicd_events_0004
Revises: coverup_0003
"""

from alembic import op

revision = "cicd_events_0004"
down_revision = "coverup_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS cicd_webhook_events (
        id SERIAL PRIMARY KEY,
        source VARCHAR(32) NOT NULL,
        event_type VARCHAR(64),
        payload JSONB NOT NULL DEFAULT '{}',
        commit_sha VARCHAR(64),
        branch VARCHAR(128),
        repo_name VARCHAR(256),
        author VARCHAR(256),
        status VARCHAR(32) DEFAULT 'received',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_cicd_events_source
        ON cicd_webhook_events (source, created_at DESC);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_cicd_events_branch
        ON cicd_webhook_events (branch, created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_cicd_events_branch;")
    op.execute("DROP INDEX IF EXISTS idx_cicd_events_source;")
    op.execute("DROP TABLE IF EXISTS cicd_webhook_events;")
```

#### Adim 2: cicd/router.py guncelle

1. `_events` list ve `_MAX_EVENTS` satirlarini SIL

2. DB dependency import'u ekle:
```python
from sqlalchemy import text
from app.infra.database import get_db
```

3. Event kaydetme yardimci fonksiyonu ekle:
```python
def _store_event(db: Session, source: str, event_type: str, payload: dict,
                 commit_sha: str = "", branch: str = "", repo_name: str = "",
                 author: str = "") -> None:
    """Webhook event'i DB'ye kaydet."""
    db.execute(
        text("""
            INSERT INTO cicd_webhook_events (source, event_type, payload, commit_sha, branch, repo_name, author)
            VALUES (:source, :event_type, :payload::jsonb, :commit_sha, :branch, :repo_name, :author)
        """),
        {
            "source": source,
            "event_type": event_type,
            "payload": json.dumps(payload),
            "commit_sha": commit_sha[:64] if commit_sha else "",
            "branch": branch[:128] if branch else "",
            "repo_name": repo_name[:256] if repo_name else "",
            "author": author[:256] if author else "",
        },
    )
    db.commit()
```

4. Event listeleme yardimcisi:
```python
def _list_events(db: Session, limit: int = 100) -> list[dict]:
    """Son N webhook event'i getir."""
    rows = db.execute(
        text("SELECT * FROM cicd_webhook_events ORDER BY created_at DESC LIMIT :limit"),
        {"limit": limit},
    ).mappings().all()
    return [dict(r) for r in rows]
```

5. Mevcut endpoint'leri guncelle:
   - Webhook handler'lar: `_events.append(...)` → `_store_event(db, ...)`
   - Event listeleme endpoint: `return _events` → `return _list_events(db, ...)`
   - Endpoint function signature'larina `db: Session = Depends(get_db)` ekle

## SORUN 2: CoverUp Reports (VERI KAYBI)

### Mevcut Durum
Dosya: `backend/app/domains/coverup/router.py`
- Modül seviyesinde: `_reports: dict = {}`
- Upload edilen coverage raporlari bu dict'te tutuluyor
- Restart olunca TUMU kayboluyor

### Cozum
- coverage_reports tablosu ZATEN Alembic'te mevcut (20260416_0003_add_coverup_tables.py)
- Ayni mantikla `_reports` dict'ini kaldir
- DB read/write fonksiyonlari ekle
- SQLAlchemy text() ile INSERT/SELECT yap
- get_db dependency ekle

#### coverup/router.py icin degisiklikler:
1. `_reports = {}` satirini SIL
2. DB import'larini ekle
3. Upload endpoint: dict'e yazmak yerine DB'ye INSERT
4. List endpoint: dict'ten okumak yerine DB'den SELECT
5. Get endpoint: dict'ten okumak yerine DB'den SELECT WHERE id = :id
6. Report bulunamazsa HTTPException(404) don

## DOGRULAMA
```bash
python3 -c "
import ast
for f in ['backend/app/domains/cicd/router.py', 'backend/app/domains/coverup/router.py',
          'backend/alembic/versions/20260416_0004_add_cicd_events.py']:
    ast.parse(open(f).read())
    print(f'✅ {f}')
"
```
```
