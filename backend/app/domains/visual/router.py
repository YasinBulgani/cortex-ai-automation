"""Visual regression REST API — PNG upload + baseline compare."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.deps import _user_permissions, get_current_user, require_permission
from app.infra.models import User

from .compare import compare_png

router = APIRouter(prefix="/visual", tags=["visual"])


_ADMIN_PERM = "admin.visual"


@router.post("/compare")
async def _compare(
    image: Annotated[UploadFile, File(description="PNG ekran görüntüsü")],
    name: Annotated[str, Form(min_length=1, description="Baseline adı, ör. 'login'")],
    user: Annotated[User, Depends(get_current_user)],
    threshold_ratio: Annotated[
        Optional[float], Form(ge=0.0, le=1.0, description="Fark oranı eşiği")
    ] = None,
    update_baseline: Annotated[
        bool, Form(description="True → baseline değiştir (admin.visual yetkisi gerekir)")
    ] = False,
) -> dict:
    # Baseline overwrite, /baseline/update ile aynı yetki kapısının arkasında
    # olmalı — aksi halde her kullanıcı yetki kontrolünü atlayabilir.
    if update_baseline:
        perms = _user_permissions(user)
        if "admin.*" not in perms and _ADMIN_PERM not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Baseline güncellemek için yetkiniz yok: {_ADMIN_PERM}",
            )
    raw = await image.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Boş image"
        )
    result = compare_png(
        name=name,
        actual_bytes=raw,
        scope=str(user.tenant_id),
        threshold_ratio=threshold_ratio,
        update_baseline=update_baseline,
    )
    if not result.ok and result.status == "pillow_unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pillow kurulu değil — visual regression devre dışı",
        )
    # Response 200 + ok flag (fail durumunda bile artefakt path'leri dönmeli)
    return {
        "ok": result.ok,
        "status": result.status,
        "reason": result.reason,
        "baseline_path": result.baseline_path,
        "diff_path": result.diff_path,
        "diff_pixels": result.diff_pixels,
        "total_pixels": result.total_pixels,
        "diff_ratio": result.diff_ratio,
        "threshold_ratio": result.threshold_ratio,
        "width": result.width,
        "height": result.height,
    }


@router.post("/baseline/update", status_code=status.HTTP_204_NO_CONTENT)
async def _force_update(
    image: Annotated[UploadFile, File()],
    name: Annotated[str, Form(min_length=1)],
    user: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> None:
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Boş image")
    result = compare_png(
        name=name,
        actual_bytes=raw,
        scope=str(user.tenant_id),
        update_baseline=True,
    )
    if result.status == "pillow_unavailable":
        raise HTTPException(status_code=503, detail="Pillow yok")
    if result.status == "invalid_image":
        raise HTTPException(status_code=400, detail=result.reason)
