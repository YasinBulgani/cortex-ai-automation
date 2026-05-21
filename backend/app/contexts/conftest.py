"""
Conftest for bounded-context tests (app/contexts/**).

Sets TESTING=true before any module is imported so config.py skips
production-mode secret validation. No real DB or secrets needed.
"""

import os

# TESTING=true makes is_production_like return False regardless of APP_ENV/debug.
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
