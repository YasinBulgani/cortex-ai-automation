"""Integration-related service helpers for TSPM."""

from __future__ import annotations

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tspm.models import TspmIntegration, TspmProject, utcnow
from app.domains.tspm.schemas import (
    IntegrationCreate,
    IntegrationUpdate,
    SyncResultOut,
)


def create_integration_for_project(
    db: Session,
    project_id: str,
    body: IntegrationCreate,
) -> TspmIntegration:
    integration = TspmIntegration(
        project_id=project_id,
        provider=body.provider,
        config=body.config,
        is_active=body.is_active,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def list_integrations_for_project(
    db: Session,
    project_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[TspmIntegration]:
    return list(
        db.scalars(
            select(TspmIntegration)
            .where(TspmIntegration.project_id == project_id)
            .order_by(TspmIntegration.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )


def update_integration_for_project(
    db: Session,
    project_id: str,
    integration_id: str,
    body: IntegrationUpdate,
) -> TspmIntegration:
    integration = get_integration_or_404(db, project_id, integration_id)
    if body.provider is not None:
        integration.provider = body.provider
    if body.config is not None:
        integration.config = body.config
    if body.is_active is not None:
        integration.is_active = body.is_active
    db.commit()
    db.refresh(integration)
    return integration


def delete_integration_for_project(
    db: Session,
    project_id: str,
    integration_id: str,
) -> None:
    integration = get_integration_or_404(db, project_id, integration_id)
    db.delete(integration)
    db.commit()


def sync_integration_for_project(
    db: Session,
    project_id: str,
    integration_id: str,
) -> SyncResultOut:
    integration = get_integration_or_404(db, project_id, integration_id)
    integration.last_sync_at = utcnow()
    db.commit()
    return SyncResultOut(synced_count=0, message="Sync completed (stub)")


def test_integration_notification(
    db: Session,
    project_id: str,
    integration_id: str,
) -> dict:
    integration = get_integration_or_404(db, project_id, integration_id)
    config = integration.config or {}
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        raise HTTPException(400, "Bu entegrasyon için webhook_url yapılandırılmamış")

    project = db.get(TspmProject, project_id)
    project_name = project.name if project else project_id

    if integration.provider == "slack":
        payload = {
            "text": f"✅ BGTS Test Bildirimi — *{project_name}* projesi için entegrasyon test edildi.",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *BGTS* bağlantı testi başarılı!\nProje: `{project_name}`",
                    },
                }
            ],
        }
    else:
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": "BGTS Test Bildirimi",
            "themeColor": "0076D7",
            "title": "BGTS Test Bildirimi",
            "text": f"✅ **{project_name}** projesi için entegrasyon testi başarılı.",
        }

    try:
        response = httpx.post(webhook_url, json=payload, timeout=10.0)
        if response.status_code >= 400:
            raise HTTPException(502, f"Webhook yanıt kodu: {response.status_code}")
        return {"ok": True, "status_code": response.status_code}
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Webhook zaman aşımı") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


def get_integration_or_404(
    db: Session,
    project_id: str,
    integration_id: str,
) -> TspmIntegration:
    integration = db.get(TspmIntegration, integration_id)
    if integration is None or integration.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entegrasyon bulunamadı")
    return integration
