"""Marketplace — thin service facade for scenario template marketplace.

HTTP-agnostic. Raises KeyError for not-found, ValueError for invalid input.
Wraps the templates module.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.domains.marketplace.templates import (
    Template,
    get_template,
    list_categories,
    list_templates,
    search,
    stats,
)

logger = logging.getLogger(__name__)


def list_items(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List marketplace templates with optional filtering.

    Args:
        category: Filter by category slug.
        tag: Filter by tag.
        query: Full-text AND search query.

    Returns:
        List of template dicts.
    """
    if query:
        templates = search(query)
    else:
        templates = list_templates(category=category, tag=tag)
    return [t.to_dict() for t in templates]


def get_item(template_id: str) -> Dict[str, Any]:
    """Fetch a single marketplace template by ID.

    Args:
        template_id: Template identifier string.

    Returns:
        Template dict.

    Raises:
        KeyError: Template not found.
    """
    t = get_template(template_id)
    if t is None:
        raise KeyError(f"Template '{template_id}' bulunamadı.")
    return t.to_dict()


def install_item(template_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Install a marketplace template into a project.

    Fetches the template and returns it as an installation payload.
    Extend this method to persist the installation to the DB.

    Args:
        template_id: Template to install.
        project_id: Target TSPM project (optional).

    Returns:
        Dict with template data and install metadata.

    Raises:
        KeyError: Template not found.
    """
    t = get_template(template_id)
    if t is None:
        raise KeyError(f"Template '{template_id}' bulunamadı.")

    logger.info("Template kuruldu: %s -> proje=%s", template_id, project_id)
    return {
        "template": t.to_dict(),
        "project_id": project_id,
        "installed": True,
    }


def get_categories() -> List[str]:
    """Return all available marketplace category slugs."""
    return list_categories()


def get_stats() -> Dict[str, Any]:
    """Return marketplace statistics (counts per category, etc.)."""
    return stats()
