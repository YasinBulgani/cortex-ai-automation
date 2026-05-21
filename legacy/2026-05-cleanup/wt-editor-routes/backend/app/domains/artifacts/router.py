from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import Artifact, User

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _is_admin_user(user: User) -> bool:
    for role in user.roles:
        for role_permission in role.permissions:
            if role_permission.permission == "admin.*":
                return True
    return False


@router.get("/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Artifact dosyasini indirir."""
    art = db.get(Artifact, artifact_id)
    if art is None:
        raise HTTPException(status_code=404, detail="Artefakt bulunamadı")

    if not _is_admin_user(user):
        owner_id = art.job.created_by if art.job is not None else None
        if not owner_id or owner_id != user.id:
            raise HTTPException(status_code=403, detail="Bu artefakta erişim yetkiniz yok")

    path = Path(art.storage_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artefakt dosyası bulunamadı")

    return FileResponse(
        str(path),
        media_type=art.mime_type,
        filename=path.name,
    )
