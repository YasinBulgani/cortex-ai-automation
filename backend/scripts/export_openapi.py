"""Export FastAPI OpenAPI schema to a JSON file.

Usage:
    cd backend
    TESTING=true python scripts/export_openapi.py [-o ../openapi.json]

The exported file is used by:
  - packages/contracts codegen (npm run -w @neurex/contracts generate:file)
  - CI drift detection (contracts-drift job in contract.yml)
  - Swagger UI / Postman import
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))
sys.path.insert(0, str(_BACKEND_ROOT.parent))

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("APP_ENV", "test")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI schema")
    parser.add_argument(
        "-o", "--output",
        default=str(_BACKEND_ROOT.parent / "openapi.json"),
        help="Output path for the JSON schema (default: ../openapi.json)",
    )
    parser.add_argument(
        "--indent", type=int, default=2,
        help="JSON indentation (default: 2)",
    )
    parser.add_argument(
        "--pretty", action="store_true", default=True,
        help="Pretty-print output (default: true)",
    )
    args = parser.parse_args()

    try:
        from app.main import app
    except Exception as exc:
        print(f"ERROR: could not import FastAPI app: {exc}", file=sys.stderr)
        return 1

    schema = app.openapi()
    path_count = len(schema.get("paths", {}))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(schema, indent=args.indent if args.pretty else None, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Exported {path_count} paths → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
