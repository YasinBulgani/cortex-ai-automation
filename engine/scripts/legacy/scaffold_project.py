#!/usr/bin/env python3
"""Legacy entrypoint that forwards to the canonical scaffold script."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "scaffold_project.py"),
        run_name="__main__",
    )
