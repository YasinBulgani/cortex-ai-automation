"""Transactional email — provider-agnostic sender + template registry.

This sits alongside ``notifications`` (which is geared toward in-product test
event notifications) and centralizes the *product* emails: welcome, plan
changes, payment receipts/failures, password reset.

Usage:
    from app.domains.email import send_template
    send_template("plan_changed", to="user@x.com", ctx={"plan_label": "Pro"})
"""
from app.domains.email.sender import (
    EmailMessage,
    SendOutcome,
    available_providers,
    get_sender,
    send,
    send_template,
)
from app.domains.email.templates import TEMPLATES, render

__all__ = [
    "EmailMessage",
    "SendOutcome",
    "TEMPLATES",
    "available_providers",
    "get_sender",
    "render",
    "send",
    "send_template",
]
