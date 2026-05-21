"""Regenerate manifest.lock.json from current prompt files.

Usage:
    python prompt_center/lock.py

Run this whenever you edit prompt files to update the lock hashes.
CI enforces: if lock hashes differ from disk, the build fails.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
LOCK_PATH = ROOT / "manifest.lock.json"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def compute_file_hashes(manifest: dict) -> dict[str, str]:
    hashes: dict[str, str] = {}
    task_prompts = manifest.get("task_prompts", {})
    seen_paths: set[str] = set()
    for task_def in task_prompts.values():
        for section_path in task_def.get("sections", []):
            if section_path in seen_paths:
                continue
            seen_paths.add(section_path)
            abs_path = ROOT / section_path
            if abs_path.exists():
                hashes[section_path] = _sha256(abs_path.read_text(encoding="utf-8"))
            else:
                print(f"WARNING: section file not found: {abs_path}", file=sys.stderr)
    return hashes


def main(check_only: bool = False) -> int:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest.json not found at {MANIFEST_PATH}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    file_hashes = compute_file_hashes(manifest)
    manifest_hash = _sha256(MANIFEST_PATH.read_text(encoding="utf-8"))

    new_lock = {
        "version": 1,
        "manifest": "manifest.json",
        "hash_algorithm": "sha256",
        "prompt_center_hash": manifest_hash,
        "files": dict(sorted(file_hashes.items())),
    }

    if check_only:
        if not LOCK_PATH.exists():
            print("ERROR: manifest.lock.json does not exist. Run: python prompt_center/lock.py", file=sys.stderr)
            return 1
        existing = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        existing_files = existing.get("files", {})
        drift: list[str] = []
        for path, expected_hash in file_hashes.items():
            if existing_files.get(path) != expected_hash:
                drift.append(path)
        for path in set(existing_files) - set(file_hashes):
            drift.append(f"{path} (removed from manifest but still in lock)")
        if drift:
            print("DRIFT DETECTED — lock file is stale. Run: python prompt_center/lock.py", file=sys.stderr)
            for d in drift:
                print(f"  - {d}", file=sys.stderr)
            return 1
        print("OK: manifest.lock.json is up to date")
        return 0

    LOCK_PATH.write_text(json.dumps(new_lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated manifest.lock.json ({len(file_hashes)} files hashed)")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Neurex QA — prompt registry lock tool")
    parser.add_argument("--check", action="store_true", help="Check only, don't update (for CI)")
    args = parser.parse_args()
    sys.exit(main(check_only=args.check))
