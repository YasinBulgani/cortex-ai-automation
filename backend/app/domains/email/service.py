"""Email domain service facade — HTTP-agnostic.

Wraps sender.py and templates.py.
Raises ValueError (bad input), never HTTPException.
"""
from __future__ import annotations

from .sender import EmailMessage, SendOutcome, send
from .templates import TEMPLATES, render


def list_templates() -> list[str]:
    """Return sorted list of available template IDs."""
    return sorted(TEMPLATES.keys())


def preview_email(template_name: str, context: dict) -> str:
    """Render template to HTML and return the HTML string.

    Raises ValueError if template_name is not registered.
    """
    if template_name not in TEMPLATES:
        raise ValueError(
            f"Unknown template: {template_name!r}. "
            f"Available: {sorted(TEMPLATES.keys())}"
        )
    _subject, html, _text = render(template_name, context)
    return html


def send_email(
    to: str,
    subject: str,
    template_name: str,
    context: dict,
) -> bool:
    """Render template and send email. Returns True on successful delivery.

    Raises ValueError if template_name is not registered or ``to`` is empty.
    """
    if not to:
        raise ValueError("Recipient address (to) must not be empty.")
    if template_name not in TEMPLATES:
        raise ValueError(
            f"Unknown template: {template_name!r}. "
            f"Available: {sorted(TEMPLATES.keys())}"
        )
    _subject, html, text = render(template_name, context)
    message = EmailMessage(
        to=to,
        subject=subject,
        html=html,
        text=text,
    )
    outcome: SendOutcome = send(message)
    return outcome.delivered
