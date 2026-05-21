"""Unit tests for prompt_center/registry.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import sys
# Make sure prompt_center is importable
_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from prompt_center.registry import PromptRegistry, PromptDriftError, PromptNotFoundError


def _make_registry(tmp_path: Path) -> PromptRegistry:
    """Build a test registry with minimal fixture files."""
    tasks_dir = tmp_path / "tasks"
    policies_dir = tmp_path / "policies"
    tasks_dir.mkdir()
    policies_dir.mkdir()

    (policies_dir / "identity.md").write_text("You are a test assistant.")
    (tasks_dir / "generate.md").write_text("Generate: {{ count }} test cases for {{ project }}.")

    manifest = {
        "task_prompts": {
            "generate": {
                "sections": [
                    "policies/identity.md",
                    "tasks/generate.md",
                ]
            }
        }
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return PromptRegistry(root=tmp_path, validate_hashes=False)


class TestPromptRegistry:
    def test_build_assembles_sections(self, tmp_path):
        registry = _make_registry(tmp_path)
        result = registry.build("generate")
        assert "You are a test assistant" in result
        assert "Generate:" in result

    def test_variable_interpolation(self, tmp_path):
        registry = _make_registry(tmp_path)
        result = registry.build("generate", context={"count": 5, "project": "BGTS"})
        assert "5" in result
        assert "BGTS" in result

    def test_missing_variable_preserved_as_placeholder(self, tmp_path):
        registry = _make_registry(tmp_path)
        result = registry.build("generate", context={})
        assert "{{ count }}" in result

    def test_unknown_task_raises(self, tmp_path):
        registry = _make_registry(tmp_path)
        with pytest.raises(PromptNotFoundError):
            registry.build("nonexistent_task")

    def test_list_tasks(self, tmp_path):
        registry = _make_registry(tmp_path)
        assert "generate" in registry.list_tasks()

    def test_invalidate_cache(self, tmp_path):
        registry = _make_registry(tmp_path)
        registry.build("generate")
        assert len(registry._section_cache) > 0
        registry.invalidate_cache()
        assert len(registry._section_cache) == 0

    def test_drift_detection(self, tmp_path):
        import hashlib
        registry = _make_registry(tmp_path)

        # Build a lock with wrong hash
        lock = {
            "version": 1,
            "manifest": "manifest.json",
            "hash_algorithm": "sha256",
            "prompt_center_hash": "fake",
            "files": {
                "policies/identity.md": "deadbeef" * 8,  # wrong hash
            }
        }
        (tmp_path / "manifest.lock.json").write_text(json.dumps(lock))

        registry_with_validation = PromptRegistry(root=tmp_path, validate_hashes=True)
        with pytest.raises(PromptDriftError, match="Prompt drift"):
            registry_with_validation.build("generate")

    def test_missing_section_file_returns_empty(self, tmp_path):
        manifest = {
            "task_prompts": {
                "broken": {
                    "sections": ["tasks/does_not_exist.md"]
                }
            }
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        registry = PromptRegistry(root=tmp_path, validate_hashes=False)
        result = registry.build("broken")
        assert result == ""
