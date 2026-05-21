"""Wire scenario_management.feature to pytest-bdd."""

# auth_steps ortak HTTP + assertion'ları, project_steps proje-özel adımları,
# scenario_steps ise senaryo-özel adımları ve tabloları sağlar.
from tests.bdd.steps.auth_steps import *  # noqa: F401, F403
from tests.bdd.steps.project_steps import *  # noqa: F401, F403
from tests.bdd.steps.scenario_steps import *  # noqa: F401, F403

from pytest_bdd import scenarios

scenarios("features/scenario_management.feature")
