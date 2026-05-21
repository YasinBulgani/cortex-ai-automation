"""Test data CRUD and basic generation helpers for TSPM."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tspm.models import TspmTestDataSet
from app.domains.tspm.schemas import TestDataSetCreate, TestDataSetOut, TestDataSetUpdate


def create_test_data_for_project(
    db: Session,
    project_id: str,
    body: TestDataSetCreate,
) -> TspmTestDataSet:
    dataset = TspmTestDataSet(
        project_id=project_id,
        name=body.name,
        description=body.description,
        columns=body.columns,
        rows=body.rows,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def list_test_data_for_project(
    db: Session,
    project_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[TspmTestDataSet]:
    return list(
        db.scalars(
            select(TspmTestDataSet)
            .where(TspmTestDataSet.project_id == project_id)
            .order_by(TspmTestDataSet.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )


def update_test_data_for_project(
    db: Session,
    project_id: str,
    data_id: str,
    body: TestDataSetUpdate,
) -> TspmTestDataSet:
    dataset = get_test_data_or_404(db, project_id, data_id)
    if body.name is not None:
        dataset.name = body.name
    if body.description is not None:
        dataset.description = body.description
    if body.columns is not None:
        dataset.columns = body.columns
    if body.rows is not None:
        dataset.rows = body.rows
    db.commit()
    db.refresh(dataset)
    return dataset


def delete_test_data_for_project(db: Session, project_id: str, data_id: str) -> None:
    dataset = get_test_data_or_404(db, project_id, data_id)
    db.delete(dataset)
    db.commit()


def export_test_data_for_project(
    db: Session,
    project_id: str,
    data_id: str,
    *,
    format: str = "csv",
):
    dataset = get_test_data_or_404(db, project_id, data_id)
    columns = dataset.columns or []
    rows = dataset.rows or []

    if format == "json":
        data = [dict(zip(columns, row)) for row in rows]
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{dataset.name}.json"'},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(rows)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{dataset.name}.csv"'},
    )


def mask_test_data_for_project(
    db: Session,
    project_id: str,
    data_id: str,
    body: dict,
) -> dict:
    dataset = get_test_data_or_404(db, project_id, data_id)
    columns_to_mask: list[str] = body.get("columns_to_mask", [])
    mask_type: str = body.get("mask_type", "asterisk")

    columns = dataset.columns or []
    rows = dataset.rows or []
    col_indices = [index for index, column in enumerate(columns) if column in columns_to_mask]

    masked_rows = []
    for row in rows:
        new_row = list(row)
        for idx in col_indices:
            if idx < len(new_row):
                new_row[idx] = _mask_value(new_row[idx], mask_type)
        masked_rows.append(new_row)

    dataset.rows = masked_rows
    db.commit()
    return {"masked_columns": columns_to_mask, "row_count": len(masked_rows)}


def generate_test_data_preview(body: dict) -> dict:
    try:
        from faker import Faker
    except ImportError as exc:
        raise HTTPException(500, "faker paketi yüklü değil. `pip install faker` komutunu çalıştırın.") from exc

    schema: dict[str, str] = body.get("schema", {})
    count: int = min(int(body.get("count", 10)), 1000)
    locale: str = body.get("locale", "tr_TR")

    if not schema:
        raise HTTPException(400, 'schema gerekli. Örnek: {"ad": "name", "email": "email"}')

    fake = Faker(locale)
    faker_map = {
        "name": fake.name,
        "first_name": fake.first_name,
        "last_name": fake.last_name,
        "email": fake.email,
        "phone": fake.phone_number,
        "address": fake.address,
        "city": fake.city,
        "company": fake.company,
        "text": fake.text,
        "sentence": fake.sentence,
        "word": fake.word,
        "uuid": fake.uuid4,
        "number": lambda: str(fake.random_int(1, 9999)),
        "date": lambda: fake.date().isoformat(),
        "boolean": lambda: str(fake.boolean()),
        "iban": fake.iban if hasattr(fake, "iban") else lambda: fake.numerify("TR####################"),
        "tc_kimlik": lambda: fake.numerify("###########"),
    }

    columns = list(schema.keys())
    rows = []
    for _ in range(count):
        row = []
        for _, faker_type in schema.items():
            fn = faker_map.get(faker_type, lambda: fake.word())
            row.append(str(fn()))
        rows.append(row)

    return {"columns": columns, "rows": rows, "count": len(rows)}


def get_test_data_or_404(db: Session, project_id: str, data_id: str) -> TspmTestDataSet:
    dataset = db.get(TspmTestDataSet, data_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(404, "Veri seti bulunamadı")
    return dataset


def _mask_value(value: str, mask_type: str) -> str:
    if not value:
        return value
    if mask_type == "asterisk":
        return value[0] + "*" * (len(value) - 1) if len(value) > 1 else "*"
    if mask_type == "hash":
        return hashlib.sha256(value.encode()).hexdigest()[:12]
    if mask_type == "fake_email":
        return f"user{random.randint(1000, 9999)}@example.com"
    if mask_type == "fake_name":
        names = ["Ali", "Mehmet", "Ayse", "Fatma", "Emre", "Zeynep"]
        surnames = ["Yilmaz", "Demir", "Kaya", "Celik"]
        return random.choice(names) + " " + random.choice(surnames)
    return "*" * len(value)
