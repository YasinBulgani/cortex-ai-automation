"""
tests/unit/conftest.py — Unit test path bootstrap

Ensures the engine root directory is on sys.path before any test module
imports routes or core modules, so sub-packages like `scripts.*` resolve.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)
