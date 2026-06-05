"""Automation templates service — in-memory store backed by builtin templates.

Provides CRUD + apply operations for automation test templates.
No DB dependency — state is kept in module-level _STORE dict.
"""
from __future__ import annotations

import copy
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Builtin templates — seeded at module load and on each _fresh_service() call
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "login-flow",
        "name": "Login Akışı",
        "category": "auth",
        "steps": [
            "open {url}",
            "fill email={email}",
            "fill password={password}",
            "click submit",
            "assert logged_in",
        ],
    },
    {
        "id": "api-crud",
        "name": "API CRUD Testi",
        "category": "api",
        "steps": [
            "POST /api/{resource} body={payload}",
            "assert status=201",
            "GET /api/{resource}/{id}",
            "assert status=200",
            "DELETE /api/{resource}/{id}",
            "assert status=204",
        ],
    },
    {
        "id": "smoke-check",
        "name": "Smoke Check",
        "category": "smoke",
        "steps": [
            "open {base_url}",
            "assert page_title contains {expected_title}",
            "assert no_console_errors",
        ],
    },
]

# Module-level mutable store — reset via _STORE.clear() + seed in tests
_STORE: dict[str, dict[str, Any]] = {}

# Seed on import
for _t in BUILTIN_TEMPLATES:
    _STORE[_t["id"]] = copy.deepcopy(_t)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_templates(*, category: str | None = None) -> list[dict[str, Any]]:
    """Return all templates, optionally filtered by category."""
    templates = list(_STORE.values())
    if category is not None:
        templates = [t for t in templates if t.get("category") == category]
    return templates


def get_template(template_id: str) -> dict[str, Any]:
    """Return a deep copy of the template by ID.

    Raises
    ------
    KeyError
        If the template does not exist.
    """
    if template_id not in _STORE:
        raise KeyError(f"Template '{template_id}' not found")
    return copy.deepcopy(_STORE[template_id])


def create_template(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new template and persist it in the store.

    Parameters
    ----------
    data:
        Must contain at least ``name``. Optional keys: ``id``, ``category``,
        ``steps``.

    Raises
    ------
    ValueError
        If ``name`` is missing or the given ``id`` already exists.
    """
    if not data.get("name"):
        raise ValueError("'name' is required")
    template_id = data.get("id") or str(uuid.uuid4())
    if template_id in _STORE:
        raise ValueError(f"Template '{template_id}' already exists")
    template = {
        "id": template_id,
        "name": data["name"],
        "category": data.get("category", "custom"),
        "steps": list(data.get("steps", [])),
    }
    _STORE[template_id] = template
    return copy.deepcopy(template)


def delete_template(template_id: str) -> None:
    """Delete a template by ID.

    Raises
    ------
    KeyError
        If the template does not exist.
    """
    if template_id not in _STORE:
        raise KeyError(f"Template '{template_id}' not found")
    del _STORE[template_id]


def apply_template(template_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Render template steps by substituting ``params`` placeholders.

    Parameters
    ----------
    template_id:
        ID of the template to apply.
    params:
        Dict of ``{placeholder: value}`` substitutions (e.g. ``{"url": "https://..."}``)

    Returns
    -------
    dict with keys ``template_id``, ``params``, ``category``, ``rendered_steps``.

    Raises
    ------
    KeyError
        If the template does not exist.
    """
    template = get_template(template_id)  # raises KeyError if missing
    rendered: list[str] = []
    for step in template.get("steps", []):
        for key, value in params.items():
            step = step.replace(f"{{{key}}}", str(value))
        rendered.append(step)
    return {
        "template_id": template_id,
        "params": params,
        "category": template.get("category", "custom"),
        "rendered_steps": rendered,
    }
