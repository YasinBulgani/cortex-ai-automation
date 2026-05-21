#!/usr/bin/env python3
"""Validate prompt_center manifest references and lock hash."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROMPT_CENTER = ROOT / "prompt_center"
LOCK_PATH = PROMPT_CENTER / "manifest.lock.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-center", default=str(PROMPT_CENTER))
    parser.add_argument("--write-lock", action="store_true")
    args = parser.parse_args()

    prompt_root = Path(args.prompt_center).resolve()
    lock_path = prompt_root / "manifest.lock.json"
    lock = build_lock(prompt_root)

    if args.write_lock:
        lock_path.write_text(
            json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"prompt manifest lock yazildi: {lock_path}")
        print(lock["prompt_center_hash"])
        return

    if not lock_path.exists():
        print(f"::error::Prompt manifest lock bulunamadi: {lock_path}")
        print("Olusturmak icin: scripts/ops/check-prompt-manifest.py --write-lock")
        sys.exit(1)

    expected = json.loads(lock_path.read_text(encoding="utf-8"))
    if expected.get("prompt_center_hash") != lock["prompt_center_hash"]:
        print("::error::prompt_center manifest lock drift tespit edildi")
        print(f"expected={expected.get('prompt_center_hash')}")
        print(f"actual={lock['prompt_center_hash']}")
        print("Bilincli prompt degisikligi ise lock'u guncelleyin:")
        print("  scripts/ops/check-prompt-manifest.py --write-lock")
        sys.exit(1)
    if expected.get("files") != lock["files"]:
        print("::error::prompt_center dosya hash listesi lock ile uyusmuyor")
        sys.exit(1)

    print(f"prompt-manifest-ok {lock['prompt_center_hash']}")


def build_lock(prompt_root: Path) -> dict[str, Any]:
    manifest_path = prompt_root / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"manifest bulunamadi: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    refs = sorted(_manifest_sections(manifest))
    files: dict[str, str] = {}
    for rel in refs:
        path = (prompt_root / rel).resolve()
        try:
            path.relative_to(prompt_root)
        except ValueError as exc:
            raise SystemExit(f"manifest path prompt_center disinda: {rel}") from exc
        if not path.exists() or not path.is_file():
            raise SystemExit(f"manifest referansi bulunamadi: {rel}")
        files[rel] = _sha256(path.read_bytes())

    canonical = json.dumps(
        {
            "manifest": manifest,
            "files": files,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "version": 1,
        "hash_algorithm": "sha256",
        "prompt_center_hash": _sha256(canonical),
        "manifest": "manifest.json",
        "files": files,
    }


def _manifest_sections(manifest: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for group in manifest.values():
        if not isinstance(group, dict):
            continue
        for item in group.values():
            if not isinstance(item, dict):
                continue
            sections = item.get("sections", [])
            if not isinstance(sections, list):
                continue
            for section in sections:
                if isinstance(section, str) and section.strip():
                    refs.add(section)
    return refs


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    main()
