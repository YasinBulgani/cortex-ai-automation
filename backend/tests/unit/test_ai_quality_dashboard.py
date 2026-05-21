from __future__ import annotations

import json
import os
from pathlib import Path


def test_build_workflow_signoff_summary_prefers_latest_live_eval_report(monkeypatch, tmp_path: Path) -> None:
    from app.domains.ai import router as ai_router

    newer = tmp_path / "ai-workflow-signoff-20260518T061317Z.json"
    newer.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-18T06:13:17Z",
                "release_decision": "needs_external_soak_and_dr_signoff",
                "llm_quality_score": 9.89,
                "prompt_center_hash": "abc123",
                "failed_required_checks": [],
                "checks": [
                    {"name": "workflow_soak", "status": "passed", "required": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    older = tmp_path / "ai-workflow-signoff-20260518T054201Z.json"
    older.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-18T05:42:01Z",
                "release_decision": "needs_remaining_release_gates",
                "llm_quality_score": 9.5,
                "prompt_center_hash": "older",
                "failed_required_checks": [],
                "checks": [
                    {
                        "name": "live_eval_contract_strict",
                        "status": "skipped",
                        "required": False,
                        "message": "Missing required live eval env: GATEWAY_INTERNAL_KEY",
                        "started_at": "2026-05-18T05:42:28Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    monkeypatch.setattr(ai_router, "_reports_dir", lambda: tmp_path)

    summary = ai_router._build_workflow_signoff_summary()
    assert summary is not None
    assert summary["release_decision"] == "needs_external_soak_and_dr_signoff"
    assert summary["report_path"] == str(newer)
    assert summary["live_eval_gate"]["status"] == "skipped"
    assert summary["live_eval_gate"]["report_path"] == str(older)
    assert "GATEWAY_INTERNAL_KEY" in summary["live_eval_gate"]["message"]
