"""Wire authentication.feature to pytest-bdd."""

# Step definitions MUST be imported so pytest-bdd can find them.
from tests.bdd.steps.auth_steps import *  # noqa: F401, F403

from pytest_bdd import scenarios

scenarios("features/authentication.feature")
