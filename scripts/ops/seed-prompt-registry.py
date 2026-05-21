#!/usr/bin/env python3
"""Seed DB prompt registry from prompt_center/manifest.json.

The DB registry is the runtime source of truth. prompt_center stays as the
versioned file source that can seed or recover the registry.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.domains.prompts.schemas import PromptIn, PromptVersionIn, RolloutIn  # noqa: E402
from app.domains.prompts.service import (  # noqa: E402
    add_version,
    get_prompt,
    list_versions,
    upsert_prompt,
    upsert_rollout,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-center", default=str(ROOT / "prompt_center"))
    parser.add_argument("--env", default="prod", choices=["prod", "staging", "dev"])
    parser.add_argument("--actor", default="seed-prompt-registry")
    args = parser.parse_args()

    prompt_root = Path(args.prompt_center)
    manifest_path = prompt_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    seeded = 0
    unchanged = 0
    for group_name in ("task_prompts", "engine_prompts"):
        prompts = manifest.get(group_name, {})
        for prompt_id, entry in prompts.items():
            sections = entry.get("sections", [])
            system_prompt = "\n\n".join(
                (prompt_root / section).read_text(encoding="utf-8").strip()
                for section in sections
            )
            existing = get_prompt(prompt_id)
            if existing is None:
                upsert_prompt(
                    prompt_id,
                    PromptIn(description=f"Seeded from prompt_center/{group_name}", task_type=prompt_id),
                    actor=args.actor,
                )

            versions = list_versions(prompt_id, limit=1)
            if versions and versions[0].system_prompt == system_prompt:
                active_version = versions[0].version
                unchanged += 1
            else:
                version = add_version(
                    prompt_id,
                    PromptVersionIn(
                        system_prompt=system_prompt,
                        user_template="",
                        notes=f"Seeded from {manifest_path.name}:{group_name}",
                    ),
                    actor=args.actor,
                )
                active_version = version.version
                seeded += 1

            upsert_rollout(
                prompt_id,
                args.env,
                RolloutIn(active_version=active_version, canary_pct=0),
                actor=args.actor,
            )

    print(json.dumps({"seeded": seeded, "unchanged": unchanged}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
