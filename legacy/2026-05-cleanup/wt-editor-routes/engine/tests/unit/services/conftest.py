"""AI service unit tests — path setup."""
import sys
from pathlib import Path

ENGINE_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if ENGINE_ROOT not in sys.path:
    sys.path.insert(0, ENGINE_ROOT)
