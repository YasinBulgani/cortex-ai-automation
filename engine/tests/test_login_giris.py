import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="E2E placeholder — requires live browser. Use tests/e2e/ for browser tests.")
scenarios("../features/Otomasyonlar/login_giris.feature")
