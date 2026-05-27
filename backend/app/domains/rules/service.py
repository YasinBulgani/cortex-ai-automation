"""Rules — thin service facade for dataset rule-sets.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
Wraps SQLAlchemy RuleSet + Dataset models.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.models import Dataset, RuleSet

logger = logging.getLogger(__name__)


def list_rules(db: Session, dataset_id: str) -> List[Dict[str, Any]]:
    """List all rule-sets for a dataset, newest first.

    Args:
        db: SQLAlchemy session.
        dataset_id: Parent dataset ID.

    Returns:
        List of rule-set dicts.

    Raises:
        KeyError: Dataset not found.
    """
    if db.get(Dataset, dataset_id) is None:
        raise KeyError(f"Dataset '{dataset_id}' bulunamadı.")

    rule_sets = list(
        db.scalars(
            select(RuleSet)
            .where(RuleSet.dataset_id == dataset_id)
            .order_by(RuleSet.created_at.desc())
        ).all()
    )
    return [{c.key: getattr(rs, c.key) for c in rs.__table__.columns} for rs in rule_sets]


def get_rule(db: Session, dataset_id: str, rule_set_id: str) -> Dict[str, Any]:
    """Fetch a single rule-set.

    Raises:
        KeyError: Dataset or rule-set not found.
    """
    if db.get(Dataset, dataset_id) is None:
        raise KeyError(f"Dataset '{dataset_id}' bulunamadı.")

    rs = db.get(RuleSet, rule_set_id)
    if rs is None or rs.dataset_id != dataset_id:
        raise KeyError(f"RuleSet '{rule_set_id}' bulunamadı.")

    return {c.key: getattr(rs, c.key) for c in rs.__table__.columns}


def create_rule(
    db: Session,
    dataset_id: str,
    data: Dict[str, Any],
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new rule-set for a dataset.

    Args:
        db: SQLAlchemy session.
        dataset_id: Parent dataset ID.
        data: Must include 'name'. Optional: 'rules_body', 'version'.
        created_by: User ID (for audit purposes).

    Returns:
        Created rule-set dict.

    Raises:
        KeyError: Dataset not found.
        ValueError: Missing 'name' field.
    """
    if db.get(Dataset, dataset_id) is None:
        raise KeyError(f"Dataset '{dataset_id}' bulunamadı.")

    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("'name' alanı zorunludur.")

    rs = RuleSet(
        dataset_id=dataset_id,
        name=name,
        rules_body=data.get("rules_body"),
        version=data.get("version"),
    )
    db.add(rs)
    db.commit()
    db.refresh(rs)
    logger.info("RuleSet oluşturuldu: %s (dataset=%s, user=%s)", rs.id, dataset_id, created_by)
    return {c.key: getattr(rs, c.key) for c in rs.__table__.columns}


def evaluate(rules_body: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a rules_body against a context dict.

    Simple structural evaluation — extend with a real rule engine as needed.

    Args:
        rules_body: Rule definitions (dict, list, or JSON string).
        context: Data record to evaluate against.

    Returns:
        Dict with 'passed' (bool) and 'details'.

    Raises:
        ValueError: rules_body is not parseable.
    """
    if isinstance(rules_body, str):
        try:
            rules_body = json.loads(rules_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"rules_body JSON parse hatası: {exc}") from exc

    if not isinstance(rules_body, (dict, list)):
        raise ValueError("rules_body dict veya list olmalıdır.")

    # Placeholder evaluation — always passes; replace with real logic.
    logger.debug("Kural değerlendirmesi: context keys=%s", list(context.keys()))
    return {"passed": True, "details": "Placeholder: kural motoru entegre edilmedi."}
