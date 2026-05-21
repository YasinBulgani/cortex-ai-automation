"""
Simülasyon / demo verisi — PostgreSQL’e örnek dataset, sürüm, şema v1, kural seti,
başarılı iş, olaylar ve indirilebilir CSV artefakt yazar (RQ gerekmez).

Çalıştırma (migrate + seed.py sonrası):
  cd backend && PYTHONPATH=. python scripts/seed_demo.py

Ortam:
  SEED_ADMIN_EMAIL   — created_by için kullanıcı (varsayılan admin@example.com)
  DEMO_DATASET_NAME  — tekrar çalıştırmada atlamak için sabit isim (varsayılan Simülasyon_Demo)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.domains.catalog.schema_v1 import parse_and_validate_snapshot
from app.infra.database import SessionLocal
from app.infra.models import (
    Artifact,
    Dataset,
    DatasetVersion,
    GenerationJob,
    JobEvent,
    RuleSet,
    SchemaSnapshot,
    User,
    utcnow,
)

DEMO_DATASET_NAME = os.environ.get("DEMO_DATASET_NAME", "Simülasyon_Demo")
DEMO_CSV = """full_name,email,city
Ayşe Yılmaz,ayse.demo@ornek.com,Istanbul
Mehmet Kaya,mehmet.demo@ornek.com,Ankara
"""


def seed_demo(db: Session) -> None:
    admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@example.com")
    admin = db.scalar(select(User).where(User.email == admin_email))
    if admin is None:
        raise SystemExit(
            f"Kullanıcı bulunamadı: {admin_email}. Önce python scripts/seed.py çalıştırın."
        )

    existing = db.scalar(select(Dataset).where(Dataset.name == DEMO_DATASET_NAME))
    if existing is not None:
        _print_summary(db, existing.id)
        print(f"\nDemo zaten yüklü (dataset adı: {DEMO_DATASET_NAME}).")
        return

    snap_dict = parse_and_validate_snapshot(
        {
            "version": 1,
            "fields": [
                {"name": "full_name", "type": "string"},
                {"name": "email", "type": "string"},
                {"name": "city", "type": "string", "nullable": True},
            ],
        }
    )

    ds = Dataset(
        name=DEMO_DATASET_NAME,
        description="Simülasyon: UI ve API akışını denemek için örnek veri seti.",
        created_by=admin.id,
    )
    db.add(ds)
    db.flush()

    ver = DatasetVersion(dataset_id=ds.id, version=1, status="draft")
    db.add(ver)
    db.flush()

    db.add(
        SchemaSnapshot(
            dataset_version_id=ver.id,
            snapshot=snap_dict,
            profile={"source": "seed_demo", "rows_hint": 2},
            pii_flags={"email": "potential_pii"},
        )
    )

    rs = RuleSet(
        dataset_id=ds.id,
        name="demo_kurallar_v1",
        rules_body="""# Örnek kural seti (simülasyon)
row_count: 2
notes: Üretim motoru henüz bu alanı yorumlamıyor; UI/API demosu içindir.
""",
        version=1,
    )
    db.add(rs)
    db.flush()

    job = GenerationJob(
        dataset_version_id=ver.id,
        rule_set_id=rs.id,
        status="succeeded",
        error_message=None,
        created_by=admin.id,
    )
    db.add(job)
    db.flush()

    now = utcnow()
    db.add(
        JobEvent(
            job_id=job.id,
            ts=now,
            level="info",
            message="Simülasyon: iş önceden tamamlanmış olarak işaretlendi.",
            payload={"seed": "seed_demo.py"},
        )
    )
    db.add(
        JobEvent(
            job_id=job.id,
            ts=now,
            level="info",
            message="Örnek CSV artefakt oluşturuldu.",
            payload=None,
        )
    )

    out_dir = Path(settings.artifacts_dir) / job.id
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "demo_output.csv"
    csv_path.write_text(DEMO_CSV, encoding="utf-8")
    resolved = str(csv_path.resolve())

    db.add(
        Artifact(
            job_id=job.id,
            storage_path=resolved,
            mime_type="text/csv",
            size_bytes=csv_path.stat().st_size,
        )
    )

    db.commit()
    print("Demo verisi yüklendi.\n")
    _print_summary(db, ds.id, job.id, ver.id, rs.id, resolved)


def _print_summary(
    db: Session,
    dataset_id: str,
    job_id: Optional[str] = None,
    version_id: Optional[str] = None,
    rule_id: Optional[str] = None,
    artifact_path: Optional[str] = None,
) -> None:
    if job_id is None:
        rs = db.scalar(
            select(RuleSet).where(RuleSet.dataset_id == dataset_id).limit(1)
        )
        if rs:
            rule_id = rs.id
        ver = db.scalar(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version.desc())
            .limit(1)
        )
        if ver:
            version_id = ver.id
            job = db.scalar(
                select(GenerationJob)
                .where(GenerationJob.dataset_version_id == ver.id)
                .order_by(GenerationJob.created_at.desc())
                .limit(1)
            )
            if job:
                job_id = job.id
                art = db.scalar(
                    select(Artifact).where(Artifact.job_id == job.id).limit(1)
                )
                if art:
                    artifact_path = art.storage_path

    print("--- Simülasyon özeti ---")
    print(f"Dataset ID:     {dataset_id}")
    if version_id:
        print(f"Sürüm ID:       {version_id}")
    if rule_id:
        print(f"Kural seti ID:  {rule_id}")
    if job_id:
        print(f"İş ID:          {job_id}")
    if artifact_path:
        print(f"Artefakt dosya: {artifact_path}")
    print("------------------------")
    print("Giriş: admin@example.com / admin123")
    print("UI: Veri setleri → Simülasyon_Demo → İşler → tamamlanan işten CSV indir.")


if __name__ == "__main__":
    s = SessionLocal()
    try:
        seed_demo(s)
    finally:
        s.close()
