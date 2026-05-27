"""automation_templates service — manages reusable test automation templates.

HTTP-agnostic. Raises ValueError/KeyError, never HTTPException.
"""
from __future__ import annotations

import copy
import uuid
from typing import Dict, List, Optional

_STORE: Dict[str, Dict] = {}

BUILTIN_TEMPLATES = [
    {
        "id": "login-flow",
        "name": "Login Akışı",
        "category": "auth",
        "steps": [
            "goto login",
            "fill credentials",
            "click submit",
            "assert logged in",
        ],
    },
    {
        "id": "api-crud",
        "name": "API CRUD",
        "category": "api",
        "steps": [
            "POST create",
            "GET read",
            "PUT update",
            "DELETE remove",
        ],
    },
    {
        "id": "form-validation",
        "name": "Form Doğrulama",
        "category": "ui",
        "steps": [
            "fill valid data",
            "submit",
            "fill invalid data",
            "check errors",
        ],
    },
]

# Seed store with builtins at import time
for _t in BUILTIN_TEMPLATES:
    _STORE[_t["id"]] = copy.deepcopy(_t)


def _all_templates() -> List[Dict]:
    return list(_STORE.values())


def list_templates(category: Optional[str] = None) -> List[Dict]:
    """Return all templates, optionally filtered by category."""
    templates = _all_templates()
    if category is not None:
        templates = [t for t in templates if t.get("category") == category]
    return templates


def get_template(template_id: str) -> Dict:
    """Return a single template by ID.

    Raises:
        KeyError: if template_id is not found.
    """
    if template_id not in _STORE:
        raise KeyError(f"Template not found: {template_id!r}")
    return copy.deepcopy(_STORE[template_id])


def create_template(data: Dict) -> Dict:
    """Create and store a new template.

    Raises:
        ValueError: if 'name' is missing or empty.
    """
    name = data.get("name", "").strip()
    if not name:
        raise ValueError("'name' is required to create a template")

    template_id = data.get("id") or str(uuid.uuid4())
    if template_id in _STORE:
        raise ValueError(f"Template with id {template_id!r} already exists")

    template = {
        "id": template_id,
        "name": name,
        "category": data.get("category", "general"),
        "steps": list(data.get("steps", [])),
    }
    _STORE[template_id] = template
    return copy.deepcopy(template)


def delete_template(template_id: str) -> Dict:
    """Delete a template by ID and return the deleted record.

    Raises:
        KeyError: if template_id is not found.
    """
    if template_id not in _STORE:
        raise KeyError(f"Template not found: {template_id!r}")
    return _STORE.pop(template_id)


def apply_template(template_id: str, params: Dict) -> Dict:
    """Instantiate a template with the given params.

    Returns a new dict with params merged into the template steps
    (params values can override step placeholders via simple substitution).

    Raises:
        KeyError: if template_id is not found.
    """
    tmpl = get_template(template_id)
    rendered_steps = []
    for step in tmpl["steps"]:
        rendered = step
        for key, value in params.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        rendered_steps.append(rendered)

    return {
        "template_id": template_id,
        "name": tmpl["name"],
        "category": tmpl["category"],
        "params": params,
        "rendered_steps": rendered_steps,
    }
