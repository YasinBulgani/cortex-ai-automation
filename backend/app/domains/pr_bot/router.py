"""PR bot domain router — prefix /pr-bot."""
from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .service import PRSummary, build_pr_summary

router = APIRouter(prefix="/pr-bot", tags=["pr-bot"])


# ── Request model ────────────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    changed_files: list[str]
    coverage_path: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────


def _summary_to_dict(summary: PRSummary) -> dict[str, Any]:
    """Convert PRSummary dataclass to a JSON-serialisable dict."""
    return dataclasses.asdict(summary)


def _llm_available() -> bool:
    """Cheaply detect whether an LLM backend is configured."""
    return bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("LLM_ENDPOINT")
    )


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/analyze", summary="Analyse changed PR files and return a PR summary")
def analyze(body: AnalyzeRequest) -> dict[str, Any]:
    """Run TIA + coverage + eval summary for the given changed files.

    Returns a ``PRSummary`` serialised as a dict.
    """
    repo_root = Path(os.environ.get("REPO_ROOT", "."))
    coverage_paths: list[Path] | None = None
    if body.coverage_path:
        coverage_paths = [Path(body.coverage_path)]

    try:
        summary = build_pr_summary(
            repo_root=repo_root,
            changed_files=body.changed_files,
            coverage_paths=coverage_paths,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"PR analysis failed: {exc}"
        ) from exc

    return _summary_to_dict(summary)


@router.get("/health", summary="PR bot health check")
def health() -> dict[str, Any]:
    """Return service liveness and whether an LLM backend is reachable."""
    return {"status": "ok", "llm_available": _llm_available()}
