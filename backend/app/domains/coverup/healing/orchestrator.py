"""Self-healing orchestrator — failure → LLM → patch → PR.

Akış:
    1. feature_flag ``coverup.auto_heal.enabled`` kapalı → status='disabled'
    2. locator_healer.propose(event) → öneriler listesi
    3. En yüksek confidence < 0.2 veya hiç yoksa → 'no_proposal'
    4. patch_applier ile dosyayı değiştir → başarısızsa 'patch_failed'
    5. GitHub: branch + commit + PR aç
       * confidence < 0.8 → draft
       * ≥ 0.8 → ready
    6. HealingRun.status='succeeded', pr_url doldur.

Decoupling:
    * LLM çağrısı ``locator_healer`` içinde (enjekte edilmiş)
    * GitHub client enjekte — ``None`` ise ``status='pr_failed'`` (dry-run
      dışında fake GitHub client ile test edilebilir)
    * Repo kökü, base branch, varsayılan commit mesajı konfig'den alınır
      (``HealingConfig``)

Idempotency:
    Aynı branch zaten varsa GitHub 422 döner → orchestrator bunu yakalayıp
    `status='pr_failed', error='branch_exists'` olarak raporlar. Yeniden
    deneme için caller farklı bir ``run_id`` kullanır veya branch silinmeli.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.infra.telemetry import set_span_attr, trace_span

from .github_client import GitHubClient, GitHubError, PullRequestResult
from .locator_healer import LocatorHealer
from .patch_applier import apply_locator_swap, PatchResult
from .schemas import (
    FailureEvent,
    HealingDecision,
    HealingProposal,
    HealingRun,
)

logger = logging.getLogger(__name__)


# Confidence eşikleri — plan §10 R2 gereği düşük güven → draft PR
_AUTO_READY_THRESHOLD = 0.80
_MIN_ACCEPT_THRESHOLD = 0.20


@dataclass
class HealingConfig:
    repo_root: Path
    base_branch: str = "main"
    default_commit_msg: str = "fix(e2e): heal locator via TestwrightAI self-healing"


def _branch_name_for(event: FailureEvent) -> str:
    """Deterministik, human-readable branch adı.

    Format: ``auto/heal/<short-run-id>-<slug-of-file>``
    """
    short = event.run_id.replace("-", "")[:8] or uuid.uuid4().hex[:8]
    file_slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", event.test_file_path).strip("-")[:40]
    return f"auto/heal/{short}-{file_slug}".lower()


def _pr_body(
    event: FailureEvent,
    decision: HealingDecision,
    patch: PatchResult,
) -> str:
    """PR açıklama body'si — review eden mühendis için özet."""
    alts = ""
    if decision.alternatives:
        alts = "\n\n### Diğer öneriler\n" + "\n".join(
            f"- `{p.new_locator}` _(confidence={p.confidence:.2f})_ — {p.rationale}"
            for p in decision.alternatives
        )
    body = f"""\
## 🩹 Self-healing locator swap

Bu PR, **TestwrightAI** tarafından otomatik olarak açıldı. Başarısız olan
bir Playwright testinde kırık selector, LLM desteğiyle yeniden üretildi.

### Kırık test
- **Dosya:** `{event.test_file_path}`{f' (satır {patch.line_number})' if patch.line_number else ''}
- **Test:** `{event.test_name or '—'}`
- **Eski locator** (`{event.locator_kind}`): `{event.locator}`

### Seçilen öneri
- **Yeni locator** (`{decision.selected.new_locator_kind}`): `{decision.selected.new_locator}`
- **Confidence:** {decision.selected.confidence:.2f}
- **Gerekçe:** {decision.selected.rationale or '—'}

### Hata mesajı (ilk 500 karakter)
```
{(event.error_message or '')[:500]}
```

### Değişiklik özeti
```diff
- {event.locator}
+ {decision.selected.new_locator}
```
{alts}

---
_Audit: run_id=`{event.run_id}` · source=`{event.source}` · tenant=`{event.tenant_id or '—'}`_
"""
    return body


class HealingOrchestrator:
    """Tek giriş: ``run(event) -> HealingRun``."""

    def __init__(
        self,
        *,
        config: HealingConfig,
        healer: LocatorHealer,
        github: Optional[GitHubClient] = None,
    ) -> None:
        self._cfg = config
        self._healer = healer
        self._gh = github

    # ── Public ────────────────────────────────────────────────────────────

    def run(self, event: FailureEvent) -> HealingRun:
        run = HealingRun(id=uuid.uuid4().hex, event=event)

        with trace_span(
            "coverup.heal.orchestrator.run",
            attrs={
                "run_id": run.id,
                "event_run_id": event.run_id,
                "tenant_id": event.tenant_id or "unknown",
                "test_file": event.test_file_path,
                "framework": event.framework,
            },
        ):
            result = self._run_inner(event, run)
            set_span_attr("status", result.status)
            if result.pr_url:
                set_span_attr("pr_url", result.pr_url)
            if result.decision:
                set_span_attr("confidence", result.decision.selected.confidence)
            return result

    def _run_inner(self, event: FailureEvent, run: HealingRun) -> HealingRun:
        if not self._flag_enabled(event.tenant_id):
            run.mark_done("disabled")
            return run

        # 1) LLM önerileri
        proposals = self._healer.propose(event)
        run.proposals = list(proposals)
        if not proposals:
            run.mark_done("no_proposal", error="healer returned 0 proposals")
            return run

        best = proposals[0]
        if best.confidence < _MIN_ACCEPT_THRESHOLD:
            decision = HealingDecision(
                selected=best, alternatives=proposals[1:]
            )
            run.decision = decision
            run.mark_done(
                "low_confidence_skipped",
                error=f"best confidence {best.confidence:.2f} < {_MIN_ACCEPT_THRESHOLD}",
            )
            return run

        decision = HealingDecision(selected=best, alternatives=proposals[1:])
        run.decision = decision

        # 2) Patch
        patch = apply_locator_swap(
            repo_root=self._cfg.repo_root,
            file_relative=event.test_file_path,
            old_locator=event.locator,
            new_locator=best.new_locator,
            expected_line=event.line_number,
        )
        if not patch.success:
            run.mark_done("patch_failed", error=patch.reason)
            return run

        # 3) PR
        if self._gh is None:
            # Dry-run modu (test/dev) — patch disk'e yazıldı ama PR açılmaz.
            run.mark_done(
                "pr_failed", error="github client bağlı değil (dry-run)"
            )
            return run

        try:
            pr = self._open_pr(event, decision, patch)
        except GitHubError as exc:
            run.mark_done("pr_failed", error=str(exc))
            return run

        run.branch_name = pr.head_ref
        run.pr_url = pr.html_url
        run.pr_number = pr.number
        run.draft = pr.draft
        run.mark_done("succeeded")
        return run

    # ── Internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _flag_enabled(tenant_id: Optional[str]) -> bool:
        try:
            from app.domains.feature_flags.service import feature_flags

            return feature_flags.is_enabled(
                "coverup.auto_heal.enabled",
                tenant_id=tenant_id,
                default=False,
            )
        except Exception as exc:  # pragma: no cover - import guard
            logger.debug("healing: feature_flag hata (%s) — disabled", exc)
            return False

    def _open_pr(
        self,
        event: FailureEvent,
        decision: HealingDecision,
        patch: PatchResult,
    ) -> PullRequestResult:
        assert self._gh is not None
        branch = _branch_name_for(event)
        base_sha = self._gh.get_default_branch_sha(self._cfg.base_branch)
        if not base_sha:
            raise GitHubError("Base branch SHA alınamadı")

        self._gh.create_branch(branch, base_sha)

        # Commit: patch_applier dosyayı zaten disk'e yazdı, ama GitHub
        # çalışma dizininden bağımsız — /contents PUT ile branch'e commit
        # ediyoruz. Disk'teki dosyayı oku (patch yeni içeriği tutuyor).
        abs_file = self._cfg.repo_root / event.test_file_path
        try:
            new_content = abs_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise GitHubError(f"Patch'li dosya okunamadı: {exc}") from exc

        short = decision.selected.new_locator
        if len(short) > 60:
            short = short[:57] + "..."
        commit_msg = (
            f"{self._cfg.default_commit_msg}\n\n"
            f"- file: {event.test_file_path}\n"
            f"- old: {event.locator}\n"
            f"- new: {decision.selected.new_locator}\n"
            f"- confidence: {decision.selected.confidence:.2f}\n"
            f"- run_id: {event.run_id}\n"
        )
        self._gh.put_file(
            branch=branch,
            path=event.test_file_path,
            content_text=new_content,
            commit_message=commit_msg,
        )

        draft = decision.selected.confidence < _AUTO_READY_THRESHOLD
        title = f"fix(e2e): heal locator in {Path(event.test_file_path).name} [auto]"
        return self._gh.open_pull_request(
            title=title,
            head=branch,
            base=self._cfg.base_branch,
            body=_pr_body(event, decision, patch),
            draft=draft,
        )
