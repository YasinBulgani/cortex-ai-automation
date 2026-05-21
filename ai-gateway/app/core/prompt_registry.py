"""
BGTS merkezi prompt registry erişim katmanı.

Kanonik prompt kaynakları repo kökündeki `prompt_center/` altında tutulur.
Bu modül AI Gateway tarafında TaskType bazlı system prompt üretir.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from app.core.models import TaskType

logger = logging.getLogger(__name__)

_FALLBACK_PROMPT = (
    "Sen Nexus QA için bir AI asistanısın. "
    "Türkçe yanıt ver. Görevini dikkatli ve doğru şekilde yerine getir."
)


def _resolve_prompt_root() -> Path:
    configured = os.getenv("PROMPT_CENTER_ROOT")
    if configured:
        return Path(configured)

    current = Path(__file__).resolve()
    candidates = [
        current.parents[3] / "prompt_center",  # local repo: <repo>/ai-gateway/app/core
        current.parents[2] / "prompt_center",  # container: /app/app/core
        Path("/prompt_center"),                 # docker volume mount
    ]
    for candidate in candidates:
        if (candidate / "manifest.json").exists():
            return candidate
    return candidates[0]


_PROMPT_ROOT = _resolve_prompt_root()


def _join(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


@lru_cache(maxsize=1)
def _load_manifest() -> dict:
    try:
        return json.loads((_PROMPT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("prompt_center/manifest.json bulunamadı (%s) — boş manifest ile devam", _PROMPT_ROOT)
        return {}
    except Exception as exc:
        logger.warning("manifest.json okunamadı: %s — boş manifest ile devam", exc)
        return {}


@lru_cache(maxsize=None)
def _read(relative_path: str) -> str:
    try:
        return (_PROMPT_ROOT / relative_path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.debug("prompt dosyası bulunamadı: %s", relative_path)
        return ""
    except Exception as exc:
        logger.debug("prompt dosyası okunamadı %s: %s", relative_path, exc)
        return ""


def _build_from_sections(sections: list[str]) -> str:
    return _join([_read(section) for section in sections])


@lru_cache(maxsize=None)
def get_task_prompt(task_type: TaskType | str) -> str:
    key = task_type.value if isinstance(task_type, TaskType) else str(task_type)
    manifest = _load_manifest()
    entry = manifest.get("task_prompts", {}).get(key)
    if not isinstance(entry, dict):
        fallback = manifest.get("task_prompts", {}).get(TaskType.CHAT.value, {})
        result = _build_from_sections(fallback.get("sections", []))
        return result or _FALLBACK_PROMPT
    result = _build_from_sections(entry.get("sections", []))
    return result or _FALLBACK_PROMPT


@lru_cache(maxsize=1)
def get_all_task_prompts() -> dict[TaskType, str]:
    return {task_type: get_task_prompt(task_type) for task_type in TaskType}
