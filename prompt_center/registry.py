"""Neurex QA — Prompt Registry SDK.

Loads prompt sections from the prompt_center directory and assembles
them into final system prompts based on manifest.json task definitions.

Features:
- File-level hash validation via manifest.lock.json (detects drift)
- In-process cache — files read once per process, re-read on hash change
- Variable interpolation: {{ key }} placeholders in prompt text
- Type-safe API

Usage:
    from prompt_center.registry import PromptRegistry

    registry = PromptRegistry()
    system_prompt = registry.build("generate_test_cases", context={"project": "BGTS"})

    # Or use default instance:
    from prompt_center.registry import registry
    prompt = registry.build("analyze_document")
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_PROMPT_CENTER_ROOT = Path(__file__).resolve().parent
_MANIFEST_PATH = _PROMPT_CENTER_ROOT / "manifest.json"
_LOCK_PATH = _PROMPT_CENTER_ROOT / "manifest.lock.json"

_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class PromptDriftError(RuntimeError):
    """Raised when a prompt file's hash doesn't match the lock file."""


class PromptNotFoundError(KeyError):
    """Raised when a task name is not in manifest.json."""


class PromptRegistry:
    """Thread-safe prompt registry with hash validation and caching."""

    def __init__(
        self,
        root: Optional[Path] = None,
        validate_hashes: bool = True,
    ) -> None:
        self._root = root or _PROMPT_CENTER_ROOT
        self._validate = validate_hashes
        self._lock = threading.Lock()
        self._section_cache: dict[str, str] = {}
        self._manifest: dict[str, Any] = {}
        self._lock_hashes: dict[str, str] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            manifest_path = self._root / "manifest.json"
            lock_path = self._root / "manifest.lock.json"

            if not manifest_path.exists():
                raise FileNotFoundError(f"manifest.json not found at {manifest_path}")

            self._manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            if lock_path.exists():
                lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
                self._lock_hashes = lock_data.get("files", {})
            else:
                self._lock_hashes = {}

            self._loaded = True

    def _read_section(self, relative_path: str) -> str:
        if relative_path in self._section_cache:
            return self._section_cache[relative_path]

        abs_path = self._root / relative_path
        if not abs_path.exists():
            logger.warning("Prompt section not found: %s", abs_path)
            return ""

        content = abs_path.read_text(encoding="utf-8")

        if self._validate and relative_path in self._lock_hashes:
            expected = self._lock_hashes[relative_path]
            actual = _sha256(content)
            if actual != expected:
                raise PromptDriftError(
                    f"Prompt drift detected in '{relative_path}': "
                    f"expected {expected[:12]}…, got {actual[:12]}…. "
                    f"Run 'make prompt-lock' to update the lock file."
                )

        self._section_cache[relative_path] = content
        return content

    def _interpolate(self, text: str, context: dict[str, Any]) -> str:
        def _replace(m: re.Match) -> str:
            key = m.group(1)
            val = context.get(key)
            if val is None:
                logger.debug("Prompt variable '{{ %s }}' not provided in context", key)
                return m.group(0)
            return str(val)

        return _VAR_RE.sub(_replace, text)

    def build(
        self,
        task: str,
        *,
        context: Optional[dict[str, Any]] = None,
        separator: str = "\n\n---\n\n",
    ) -> str:
        """Assemble the system prompt for *task* from its sections.

        Args:
            task: Key from manifest.json task_prompts (e.g. "generate_test_cases").
            context: Optional dict for {{ variable }} substitution in prompt text.
            separator: String inserted between sections.

        Returns:
            Assembled system prompt string.

        Raises:
            PromptNotFoundError: If *task* is not in the manifest.
            PromptDriftError: If a section file hash doesn't match the lock.
        """
        self._load()

        task_prompts = self._manifest.get("task_prompts", {})
        if task not in task_prompts:
            available = ", ".join(sorted(task_prompts.keys()))
            raise PromptNotFoundError(
                f"Task '{task}' not found in prompt registry. Available: {available}"
            )

        sections = task_prompts[task].get("sections", [])
        parts: list[str] = []
        for section_path in sections:
            content = self._read_section(section_path)
            if content.strip():
                parts.append(content.strip())

        assembled = separator.join(parts)

        if context:
            assembled = self._interpolate(assembled, context)

        return assembled

    def list_tasks(self) -> list[str]:
        """Return sorted list of available task names."""
        self._load()
        return sorted(self._manifest.get("task_prompts", {}).keys())

    def invalidate_cache(self) -> None:
        """Force re-read of all section files on next build() call."""
        with self._lock:
            self._section_cache.clear()
            self._loaded = False

    def get_section_hashes(self) -> dict[str, str]:
        """Return actual SHA-256 hashes of all tracked section files."""
        self._load()
        result: dict[str, str] = {}
        for relative_path in self._lock_hashes:
            abs_path = self._root / relative_path
            if abs_path.exists():
                result[relative_path] = _sha256(abs_path.read_text(encoding="utf-8"))
        return result


registry = PromptRegistry()
