"""Override parent autouse fixtures that require the full FastAPI app import.

Multi-team unit tests are pure-Python: mention parser, crypto, i18n, etc.
We don't want them blocked by unrelated environment issues in app.main.
"""

import pytest


@pytest.fixture(autouse=True)
def clear_client_cookies():
    """No-op override — these tests don't use the HTTP client."""
    yield
