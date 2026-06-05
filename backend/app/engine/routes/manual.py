"""
Manual test routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/manual_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/manual.py — APIRouter, port 8000 (consolidated)

Endpointler:
  GET    /api/manual-tests                        — tüm manuel testleri listele
  POST   /api/manual-tests                        — yeni manuel test oluştur
  DELETE /api/manual-tests/{test_id}              — manuel test sil
  PUT    /api/manual-tests/{test_id}              — test durumunu güncelle
  POST   /api/manual-tests/{test_id}/steps        — adım ekle
  DELETE /api/manual-test-steps/{step_id}         — adım sil
  PUT    /api/manual-test-steps/{step_id}         — adım durumunu güncelle
  POST   /api/generate-manual-from-doc            — doküman yükle, testleri AI ile üret
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["engine", "manual"])


# ─── DB dependency helpers ────────────────────────────────────────────────────

def _db():
    """Engine core.db modülünden manuel test CRUD işlemlerini getirir."""
    try:
        from core.db import (  # type: ignore
            add_manual_step,
            create_manual_test,
            delete_manual_step,
            delete_manual_test,
            get_manual_tests,
            update_manual_step_status,
            update_manual_test_status,
        )
        return {
            "create_manual_test": create_manual_test,
            "delete_manual_test": delete_manual_test,
            "add_manual_step": add_manual_step,
            "delete_manual_step": delete_manual_step,
            "update_manual_step_status": update_manual_step_status,
            "update_manual_test_status": update_manual_test_status,
            "get_manual_tests": get_manual_tests,
        }
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Engine core.db erişilemedi: {e}",
        )


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ManualTestCreate(BaseModel):
    title: str = Field(..., min_length=1)


class ManualTestStatusUpdate(BaseModel):
    status: str


class ManualStepCreate(BaseModel):
    action: str = Field(..., min_length=1)
    expected: str = Field(..., min_length=1)


class ManualStepStatusUpdate(BaseModel):
    status: str


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/manual-tests")
def get_manual_tests_api():
    db = _db()
    return db["get_manual_tests"]()


@router.post("/manual-tests", status_code=status.HTTP_201_CREATED)
def post_manual_test(body: ManualTestCreate):
    db = _db()
    test_id = db["create_manual_test"](body.title)
    return {"ok": True, "id": test_id}


@router.delete("/manual-tests/{test_id}", status_code=status.HTTP_200_OK)
def del_manual_test(test_id: int):
    db = _db()
    db["delete_manual_test"](test_id)
    return {"ok": True}


@router.put("/manual-tests/{test_id}")
def put_manual_test_status(test_id: int, body: ManualTestStatusUpdate):
    db = _db()
    db["update_manual_test_status"](test_id, body.status)
    return {"ok": True}


@router.post("/manual-tests/{test_id}/steps", status_code=status.HTTP_201_CREATED)
def post_manual_step(test_id: int, body: ManualStepCreate):
    db = _db()
    db["add_manual_step"](test_id, body.action, body.expected)
    return {"ok": True}


@router.delete("/manual-test-steps/{step_id}", status_code=status.HTTP_200_OK)
def del_manual_step(step_id: int):
    db = _db()
    db["delete_manual_step"](step_id)
    return {"ok": True}


@router.put("/manual-test-steps/{step_id}")
def put_manual_step_status(step_id: int, body: ManualStepStatusUpdate):
    db = _db()
    db["update_manual_step_status"](step_id, body.status)
    return {"ok": True}


@router.post("/generate-manual-from-doc", status_code=status.HTTP_201_CREATED)
async def generate_manual_from_doc(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya adı boş",
        )

    filename_lower = file.filename.lower()
    if filename_lower.endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF veya DOCX desteği (.txt kullanın)",
        )

    try:
        raw = await file.read()
        content = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    try:
        from core.ai_engine import get_ai_engine  # type: ignore
        engine = get_ai_engine()
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI engine erişilemedi: {e}",
        )

    try:
        tests = engine.extract_manual_tests_from_text(content)
        db = _db()
        count = 0
        for t in tests:
            test_id = db["create_manual_test"](t.get("title", "İsimsiz Test"))
            for s in t.get("steps", []):
                db["add_manual_step"](test_id, s.get("action", "-"), s.get("expected", "-"))
            count += 1
        return {"ok": True, "count": count}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
