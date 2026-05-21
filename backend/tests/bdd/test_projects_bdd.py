"""Wire project_management.feature to pytest-bdd."""

# auth_steps ortak HTTP + assertion step'lerini sağlar (POST/GET, yanıt kodu,
# yanıt alanı vb.). project_steps'in auth_steps'e üstün gelmesi için
# auth_steps ÖNCE import edilir ve proje-özel adımlar üzerine bindirilir.
from tests.bdd.steps.auth_steps import *  # noqa: F401, F403
from tests.bdd.steps.project_steps import *  # noqa: F401, F403

from pytest_bdd import scenarios

scenarios("features/project_management.feature")
