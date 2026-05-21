"""
Nexus QA — AI Prompt erişim katmanı.

Geriye dönük uyumluluk için `get_system_prompt(...)` burada tutulur; kanonik
prompt kaynakları `prompt_center/` altındaki merkezi registry'den yüklenir.
"""
from __future__ import annotations

from app.core.models import TaskType
from app.core.prompt_registry import get_all_task_prompts, get_task_prompt

PROMPTS: dict[TaskType, str] = get_all_task_prompts()
DEFAULT_PROMPT = PROMPTS[TaskType.CHAT]


def get_system_prompt(task_type: TaskType) -> str:
    """Task type için system prompt döndür."""
    return get_task_prompt(task_type)
