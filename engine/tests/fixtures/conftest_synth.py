"""
pytest conftest hook: `synthetic` fixture'ını tüm engine testlerine expose eder.

engine/tests/conftest.py içine eklenecek import:
    from tests.fixtures.conftest_synth import synthetic
"""

import pytest
from .synthetic_data_hook import SyntheticDataGenerator


@pytest.fixture(scope="session")
def synthetic() -> SyntheticDataGenerator:
    """Reproducible synthetic data generator. Seed=42 for deterministic test runs."""
    return SyntheticDataGenerator(seed=42)


@pytest.fixture
def fresh_synthetic() -> SyntheticDataGenerator:
    """Fresh (non-seeded) generator per test — for randomized edge cases."""
    return SyntheticDataGenerator()
