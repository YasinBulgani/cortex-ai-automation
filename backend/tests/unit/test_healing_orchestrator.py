"""Healing orchestrator ve GitHub client uçtan uca (mock'lı) testler.

Stratejiler:
    * feature_flag monkeypatch ile enabled
    * LocatorHealer LLM'i fake fn ile
    * GitHubClient için FakeTransport — tüm API çağrılarını yakalar
    * repo_root tmp_path
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from app.domains.coverup.healing.github_client import (
    GitHubClient,
    GitHubError,
    HttpResponse,
    TokenAuth,
)
from app.domains.coverup.healing.locator_healer import LocatorHealer
from app.domains.coverup.healing.orchestrator import (
    HealingConfig,
    HealingOrchestrator,
    _branch_name_for,
)
from app.domains.coverup.healing.schemas import FailureEvent


# ── Fake transport ────────────────────────────────────────────────────────


@dataclass
class FakeTransport:
    """Scripted HTTP responses — prod httpx'in yerine konur."""

    responses: Dict[str, List[HttpResponse]] = field(default_factory=dict)
    calls: List[Dict[str, Any]] = field(default_factory=list)

    def push(self, method: str, url_suffix: str, status: int, body: dict | None = None) -> None:
        key = f"{method} {url_suffix}"
        self.responses.setdefault(key, []).append(
            HttpResponse(status_code=status, body=body or {}, text=json.dumps(body or {}))
        )

    def request(
        self, method: str, url: str, *, headers: dict, json: Optional[dict] = None
    ) -> HttpResponse:
        self.calls.append(
            {"method": method, "url": url, "json": json, "headers": headers}
        )
        # suffix match — testler path'in sonunu belirtir
        for key in list(self.responses.keys()):
            m, suffix = key.split(" ", 1)
            if m == method and url.endswith(suffix):
                queue = self.responses[key]
                if queue:
                    return queue.pop(0)
        return HttpResponse(status_code=404, body={"message": f"unmocked {method} {url}"}, text="unmocked")


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _enable_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """coverup.auto_heal.enabled her test için açık (override edilebilir)."""
    from app.domains.coverup.healing import orchestrator as orch

    monkeypatch.setattr(orch.HealingOrchestrator, "_flag_enabled", staticmethod(lambda _t: True))


@pytest.fixture
def sample_event(tmp_path: Path) -> FailureEvent:
    # Dosyayı da oluştur (repo_root=tmp_path)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "login.spec.ts").write_text(
        "import { test } from '@playwright/test';\n"
        "test('login', async ({ page }) => {\n"
        "  await page.locator('.submit-btn').click();\n"
        "});\n",
        encoding="utf-8",
    )
    return FailureEvent(
        run_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        project_id="proj-1",
        tenant_id="tenant-1",
        test_file_path="tests/login.spec.ts",
        test_name="login",
        line_number=3,
        locator=".submit-btn",
        locator_kind="css",
        error_message="Timeout 30000ms waiting for locator('.submit-btn')",
        dom_snapshot="<button data-testid='submit'>Gönder</button>",
        page_url="http://localhost:3000/login",
    )


def _healer_with_proposal(
    *, new_locator: str = "[data-testid='submit']", confidence: float = 0.92
) -> LocatorHealer:
    def _fake(_s: str, _u: str) -> str:
        return json.dumps(
            {
                "proposals": [
                    {
                        "new_locator": new_locator,
                        "new_locator_kind": "test-id",
                        "confidence": confidence,
                        "rationale": "data-testid stabil",
                    },
                    {
                        "new_locator": "button:has-text('Gönder')",
                        "new_locator_kind": "text",
                        "confidence": 0.6,
                    },
                ]
            }
        )

    return LocatorHealer(call_llm=_fake)


def _healer_empty() -> LocatorHealer:
    def _fake(_s: str, _u: str) -> str:
        return json.dumps({"proposals": []})

    return LocatorHealer(call_llm=_fake)


def _gh_client_succeeding() -> tuple[GitHubClient, FakeTransport]:
    t = FakeTransport()
    t.push("GET", "/git/refs/heads/main", 200, {"object": {"sha": "base-sha"}})
    t.push("POST", "/git/refs", 201, {"ref": "refs/heads/auto/..."})
    # contents GET sonra PUT
    t.push("GET", ".ts?ref=auto/heal/aaaaaaaa-tests-login.spec.ts", 200, {"sha": "file-sha"})
    # suffix match daha kısa değişebilir — başka bir stable match kullan:
    # "GET /contents/tests/login.spec.ts?ref=..." → url suffix ile eşleşir
    return GitHubClient(
        auth=TokenAuth(token="ghp_test"),
        owner="acme",
        repo="proj",
        transport=t,
    ), t


# ── Orchestrator tests ────────────────────────────────────────────────────


def test_full_flow_opens_ready_pr_when_confidence_high(
    tmp_path: Path, sample_event: FailureEvent
) -> None:
    t = FakeTransport()
    t.push("GET", "/git/refs/heads/main", 200, {"object": {"sha": "base-sha"}})
    t.push("POST", "/git/refs", 201, {})
    t.push("GET", "/contents/tests/login.spec.ts?ref=" + _branch_name_for(sample_event), 200, {"sha": "file-sha"})
    t.push("PUT", "/contents/tests/login.spec.ts", 200, {})
    t.push("POST", "/pulls", 201, {"number": 42, "html_url": "https://github.com/acme/proj/pull/42"})

    gh = GitHubClient(auth=TokenAuth("ghp_x"), owner="acme", repo="proj", transport=t)
    orch = HealingOrchestrator(
        config=HealingConfig(repo_root=tmp_path),
        healer=_healer_with_proposal(confidence=0.92),
        github=gh,
    )

    run = orch.run(sample_event)
    assert run.status == "succeeded"
    assert run.pr_url == "https://github.com/acme/proj/pull/42"
    assert run.pr_number == 42
    assert run.draft is False  # 0.92 >= 0.80 → ready
    assert run.branch_name and run.branch_name.startswith("auto/heal/")

    # Dosya gerçekten güncellenmiş
    updated = (tmp_path / "tests/login.spec.ts").read_text()
    assert ".submit-btn" not in updated
    assert "[data-testid='submit']" in updated

    # PR body içeriği mantıklı
    pr_call = next(c for c in t.calls if c["method"] == "POST" and c["url"].endswith("/pulls"))
    body = pr_call["json"]["body"]
    assert ".submit-btn" in body
    assert "[data-testid='submit']" in body
    assert "confidence" in body.lower()


def test_low_confidence_opens_draft_pr(
    tmp_path: Path, sample_event: FailureEvent
) -> None:
    t = FakeTransport()
    t.push("GET", "/git/refs/heads/main", 200, {"object": {"sha": "base-sha"}})
    t.push("POST", "/git/refs", 201, {})
    t.push("GET", "/contents/tests/login.spec.ts?ref=" + _branch_name_for(sample_event), 200, {"sha": "file-sha"})
    t.push("PUT", "/contents/tests/login.spec.ts", 200, {})
    t.push("POST", "/pulls", 201, {"number": 7, "html_url": "https://github.com/acme/proj/pull/7"})

    gh = GitHubClient(auth=TokenAuth("x"), owner="acme", repo="proj", transport=t)
    orch = HealingOrchestrator(
        config=HealingConfig(repo_root=tmp_path),
        healer=_healer_with_proposal(confidence=0.55),  # < 0.80 → draft
        github=gh,
    )
    run = orch.run(sample_event)
    assert run.status == "succeeded"
    assert run.draft is True
    pr_call = next(c for c in t.calls if c["method"] == "POST" and c["url"].endswith("/pulls"))
    assert pr_call["json"]["draft"] is True


def test_no_proposals_returns_no_proposal_status(
    tmp_path: Path, sample_event: FailureEvent
) -> None:
    orch = HealingOrchestrator(
        config=HealingConfig(repo_root=tmp_path),
        healer=_healer_empty(),
        github=None,
    )
    run = orch.run(sample_event)
    assert run.status == "no_proposal"
    assert run.pr_url is None


def test_below_min_threshold_skipped(
    tmp_path: Path, sample_event: FailureEvent
) -> None:
    # Tek düşük confidence öneri — min threshold altında skip
    def _fake(_s: str, _u: str) -> str:
        return json.dumps(
            {
                "proposals": [
                    {
                        "new_locator": "[x]",
                        "new_locator_kind": "css",
                        "confidence": 0.1,
                    }
                ]
            }
        )

    orch = HealingOrchestrator(
        config=HealingConfig(repo_root=tmp_path),
        healer=LocatorHealer(call_llm=_fake),
        github=None,
    )
    run = orch.run(sample_event)
    assert run.status == "low_confidence_skipped"
    assert run.decision is not None
    assert run.decision.selected.confidence == 0.1
    # Dosya dokunulmadı
    untouched = (tmp_path / "tests/login.spec.ts").read_text()
    assert ".submit-btn" in untouched


def test_patch_failure_stops_before_pr(
    tmp_path: Path, sample_event: FailureEvent
) -> None:
    # Dosyada iki geçiş — ambiguous → patch fail
    (tmp_path / "tests" / "login.spec.ts").write_text(
        "await page.locator('.submit-btn').click();\n"
        "await page.locator('.submit-btn').isEnabled();\n",
        encoding="utf-8",
    )
    orch = HealingOrchestrator(
        config=HealingConfig(repo_root=tmp_path),
        healer=_healer_with_proposal(confidence=0.95),
        github=None,
    )
    run = orch.run(sample_event)
    assert run.status == "patch_failed"
    assert "ambiguous" in (run.error_message or "")


def test_github_failure_reported(
    tmp_path: Path, sample_event: FailureEvent
) -> None:
    t = FakeTransport()
    t.push(
        "GET", "/git/refs/heads/main", 500, {"message": "internal server error"}
    )
    gh = GitHubClient(auth=TokenAuth("x"), owner="acme", repo="proj", transport=t)
    orch = HealingOrchestrator(
        config=HealingConfig(repo_root=tmp_path),
        healer=_healer_with_proposal(confidence=0.9),
        github=gh,
    )
    run = orch.run(sample_event)
    assert run.status == "pr_failed"
    assert "500" in (run.error_message or "")


def test_disabled_flag_skips_everything(
    tmp_path: Path,
    sample_event: FailureEvent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domains.coverup.healing import orchestrator as orch_mod

    monkeypatch.setattr(
        orch_mod.HealingOrchestrator, "_flag_enabled", staticmethod(lambda _t: False)
    )
    orch = HealingOrchestrator(
        config=HealingConfig(repo_root=tmp_path),
        healer=_healer_with_proposal(confidence=0.95),
        github=None,
    )
    run = orch.run(sample_event)
    assert run.status == "disabled"
    # Dosya dokunulmamış
    assert ".submit-btn" in (tmp_path / "tests/login.spec.ts").read_text()


def test_dry_run_without_github_after_patch(
    tmp_path: Path, sample_event: FailureEvent
) -> None:
    orch = HealingOrchestrator(
        config=HealingConfig(repo_root=tmp_path),
        healer=_healer_with_proposal(confidence=0.9),
        github=None,
    )
    run = orch.run(sample_event)
    # Patch başarılı ama GitHub yok → pr_failed (net mesaj)
    assert run.status == "pr_failed"
    assert "dry-run" in (run.error_message or "").lower() or "github" in (run.error_message or "").lower()
    # Ama dosya değişmiş — operatör PR'ı elle açabilir
    assert "[data-testid='submit']" in (tmp_path / "tests/login.spec.ts").read_text()


def test_branch_name_is_deterministic_and_safe() -> None:
    evt = FailureEvent(
        run_id="abcd1234-ffff-ffff-ffff-ffffffffffff",
        test_file_path="tests/foo/Bar Baz.spec.ts",
        locator=".x",
    )
    name = _branch_name_for(evt)
    assert name.startswith("auto/heal/abcd1234")
    # Slash ve boşluk sanitize edilmiş
    assert " " not in name
    # Kısıtlı karakter seti
    assert all(c.isalnum() or c in "/-._" for c in name)


# ── FailureEvent validation ──────────────────────────────────────────────


def test_failure_event_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        FailureEvent(run_id="r", test_file_path="../etc/passwd", locator="x")


def test_failure_event_rejects_absolute_path() -> None:
    with pytest.raises(ValueError):
        FailureEvent(run_id="r", test_file_path="/etc/passwd", locator="x")


# ── GitHub client ────────────────────────────────────────────────────────


def test_token_auth_empty_raises() -> None:
    auth = TokenAuth(token="   ")
    with pytest.raises(GitHubError):
        auth.get_auth_header()


def test_token_auth_bearer_format() -> None:
    assert TokenAuth(token="ghp_abc").get_auth_header() == "Bearer ghp_abc"


def test_client_raises_on_http_error() -> None:
    t = FakeTransport()
    t.push("GET", "/git/refs/heads/main", 404, {"message": "Not Found"})
    gh = GitHubClient(auth=TokenAuth("x"), owner="a", repo="b", transport=t)
    with pytest.raises(GitHubError) as exc:
        gh.get_default_branch_sha()
    assert exc.value.status_code == 404
