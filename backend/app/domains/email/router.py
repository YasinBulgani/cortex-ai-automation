"""Email domain router — prefix /email."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .service import list_templates, preview_email, send_email

router = APIRouter(prefix="/email", tags=["email"])


# ── Request / Response models ────────────────────────────────────────────


class PreviewRequest(BaseModel):
    template_name: str
    context: dict = {}


class SendRequest(BaseModel):
    to: str
    subject: str
    template_name: str
    context: dict = {}


# ── Admin dependency stub ────────────────────────────────────────────────
# Replace with a real auth/permission check (e.g. require_permission("email.send"))


def _require_admin() -> None:  # pragma: no cover
    """Placeholder admin guard — wire to real auth in production."""
    return None


# ── Endpoints ────────────────────────────────────────────────────────────


@router.get("/templates", summary="List available email templates")
def get_templates() -> list[str]:
    """Return a sorted list of registered template IDs."""
    return list_templates()


@router.post("/preview", summary="Render an email template to HTML")
def preview(body: PreviewRequest) -> dict[str, str]:
    """Render *template_name* with *context* and return ``{html: str}``."""
    try:
        html = preview_email(body.template_name, body.context)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"html": html}


@router.post("/send", summary="Send an email (admin only)")
def send(
    body: SendRequest,
    _admin: None = Depends(_require_admin),
) -> dict[str, bool]:
    """Render *template_name* with *context* and send to *to*.

    Returns ``{ok: bool}``. Requires admin privileges (via Depends).
    """
    try:
        ok = send_email(
            to=body.to,
            subject=body.subject,
            template_name=body.template_name,
            context=body.context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": ok}
