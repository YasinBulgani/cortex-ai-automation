#!/usr/bin/env python3
"""Dry-run or apply AI workflow artifact retention cleanup."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Retention window in days; defaults to AI_WORKFLOW_ARTIFACT_RETENTION_DAYS.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete eligible artifact files and DB rows. Default is dry-run.",
    )
    args = parser.parse_args()

    from app.domains.ai.artifact_retention import cleanup_workflow_artifacts
    from app.infra.database import SessionLocal

    with SessionLocal() as db:
        result = cleanup_workflow_artifacts(
            db,
            retention_days=args.days,
            dry_run=not args.apply,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
