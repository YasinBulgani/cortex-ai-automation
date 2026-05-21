"""
Engine tarafı için merkezi prompt yükleyici.

Kanonik kaynak repo kökündeki `prompt_center/` dizinidir.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROMPT_ROOT = _REPO_ROOT / "prompt_center"


def _join(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


@lru_cache(maxsize=1)
def _load_manifest() -> dict:
    return json.loads((_PROMPT_ROOT / "manifest.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _read(relative_path: str) -> str:
    return (_PROMPT_ROOT / relative_path).read_text(encoding="utf-8").strip()


def _build(group: str, key: str) -> str:
    manifest = _load_manifest()
    entry = manifest.get(group, {}).get(key)
    if not isinstance(entry, dict):
        raise KeyError(f"Prompt bulunamadı: {group}.{key}")
    return _join([_read(section) for section in entry.get("sections", [])])


@lru_cache(maxsize=None)
def get_engine_prompt(name: str) -> str:
    return _build("engine_prompts", name)


@lru_cache(maxsize=None)
def get_task_prompt(name: str) -> str:
    return _build("task_prompts", name)
