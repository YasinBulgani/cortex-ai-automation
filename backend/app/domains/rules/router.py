from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.utils import client_ip
from app.deps import get_current_user
from app.domains.audit.service import log_audit
from app.domains.rules.schemas import RuleSetCreate, RuleSetOut
from app.infra.database import get_db
from app.infra.models import Dataset, RuleSet, User

router = APIRouter(prefix="/datasets", tags=["rules"])


@router.get("/{dataset_id}/rule-sets", response_model=list[RuleSetOut])
def list_rule_sets(
    dataset_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[RuleSet]:
    """Is kurali setlerini listeler."""
    if db.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
    return list(
        db.scalars(
            select(RuleSet)
            .where(RuleSet.dataset_id == dataset_id)
            .order_by(RuleSet.created_at.desc())
        ).all()
    )


@router.post(
    "/{dataset_id}/rule-sets",
    response_model=RuleSetOut,
    status_code=status.HTTP_201_CREATED,
)
def create_rule_set(
    dataset_id: str,
    body: RuleSetCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> RuleSet:
    """Yeni is kurali seti olusturur."""
    if db.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail="Veri seti bulunamadı")
    rs = RuleSet(
        dataset_id=dataset_id,
        name=body.name,
        rules_body=body.rules_body,
        version=body.version,
    )
    db.add(rs)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="ruleset.create",
        resource_type="rule_set",
        resource_id=rs.id,
        payload={"dataset_id": dataset_id, "name": body.name},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(rs)
    return rs


@router.get("/{dataset_id}/rule-sets/{rule_set_id}", response_model=RuleSetOut)
def get_rule_set(
    dataset_id: str,
    rule_set_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> RuleSet:
    """Kural seti detayini getirir."""
    rs = db.get(RuleSet, rule_set_id)
    if rs is None or rs.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Kural seti bulunamadı")
    return rs
