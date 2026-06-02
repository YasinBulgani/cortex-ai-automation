# ADR-0013: Engine Route Test Isolation Pattern

## Status

Accepted

## Date

2026-05-27

## Context

The Neurex QA engine (`engine/app.py`) imports a large number of heavy dependencies at module level: browser automation libraries, database clients, ML model loaders, and other production-only packages. This made it impossible to run blueprint-level route tests in CI environments for two reasons:

1. **Heavy dependency imports**: Packages like Playwright, ChromeDriver, and database drivers are not available in lightweight CI containers, causing `ImportError` on any attempt to import `app.py`.
2. **Python 3.9/3.10 syntax incompatibility**: Some engine modules used `dict | None` union syntax (PEP 604) introduced in Python 3.10, while CI runs on Python 3.9 for compatibility with the banking client's deployment target. Direct import of these modules caused `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`.

The existing approach of trying to mock after import was insufficient — by the time `app.py` finished loading, the incompatible syntax had already been evaluated.

## Decision

Build **minimal Flask test applications per-blueprint** using `sys.modules` monkeypatching **before** any engine import occurs.

### Pattern

```python
import sys
from unittest.mock import MagicMock

# Step 1: Patch all heavy/incompatible deps BEFORE importing engine modules
sys.modules["playwright"] = MagicMock()
sys.modules["playwright.sync_api"] = MagicMock()
sys.modules["heavy_db_driver"] = MagicMock()
sys.modules["some_py310_module"] = MagicMock()

# Step 2: Import ONLY the specific blueprint under test (not app.py)
from engine.routes.my_feature import bp  # noqa: E402

# Step 3: Build a minimal Flask app with just this blueprint
from flask import Flask
app = Flask(__name__)
app.register_blueprint(bp)

# Step 4: Use Flask test client — no real DB, no real browser
client = app.test_client()
```

### Key Rules

- Monkeypatching via `sys.modules` must happen in the module that sets up the test fixture, before any `import` of engine code.
- Each test module patches only the deps it needs to suppress.
- `MagicMock()` satisfies attribute access chains like `mock.some.nested.attr` automatically.
- Blueprint tests import the blueprint directly, never `app.py`.
- Test apps are ephemeral — created in fixture scope, torn down after each test module.

## Consequences

### Positive

- **Full test isolation**: No real database connections, no real browser sessions, no network calls in unit/route tests.
- **Python 3.9 compatibility**: By patching modules before they are imported, Python 3.9 never evaluates syntax-incompatible code paths.
- **Fast CI**: Tests run in milliseconds with zero infrastructure dependencies.
- **Independent blueprint testing**: Each route blueprint can be tested independently; a bug in one blueprint does not prevent other blueprint tests from running.
- **No production code changes required**: The engine source is not modified; only the test setup layer adds the `sys.modules` patches.

### Negative / Trade-offs

- **Patch maintenance**: When new heavy dependencies are added to engine modules, test fixtures must be updated to add the corresponding `sys.modules` entry.
- **Mock fidelity**: Tests verify routing, request/response serialization, and business logic — but cannot verify actual database queries or browser interactions. Those remain the responsibility of integration and E2E tests.
- **Import order sensitivity**: The monkeypatching must appear before any import of engine code in the same process. Developers must be careful not to accidentally import engine modules at the top of a test file before the patching block.

### Neutral

- This pattern is specific to the Flask engine layer. The FastAPI backend uses dependency injection and does not require `sys.modules` patching.
- Compatible with pytest fixtures, conftest.py, and standard CI runner environments (GitHub Actions, GitLab CI).
