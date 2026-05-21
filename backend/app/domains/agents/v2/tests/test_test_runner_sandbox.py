"""Sandbox guard tests for the Playwright runner."""

from __future__ import annotations

from pathlib import Path

from app.domains.agents.v2.tools.test_runner import (
    _container_path_for,
    _is_host_allowed,
)


def test_is_host_allowed_exact_and_wildcard():
    allowlist = ["staging.bank.example.tr", "*.test.internal"]

    assert _is_host_allowed("https://staging.bank.example.tr/login", allowlist)
    assert _is_host_allowed("https://app.test.internal", allowlist)
    assert not _is_host_allowed("https://evil.example.com", allowlist)


def test_container_path_requires_workdir_boundary(tmp_path):
    spec = tmp_path / "tests" / "flow.spec.ts"
    spec.parent.mkdir()
    spec.write_text("test('x', () => {})", encoding="utf-8")

    assert _container_path_for(spec, tmp_path) == "/work/tests/flow.spec.ts"
    assert _container_path_for(Path("/tmp/outside.spec.ts"), tmp_path) is None
