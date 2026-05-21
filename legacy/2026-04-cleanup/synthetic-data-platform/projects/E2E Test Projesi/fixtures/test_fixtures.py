"""
Test fixture'ları modülü.

Özel test fixture'larını tanımlar.
"""

import pytest
import logging
from utils.test_data import TestData


logger = logging.getLogger(__name__)


@pytest.fixture
def test_user():
    """
    Test kullanıcı fixture'ı.

    Dönüş:
        dict: Test kullanıcı verisi
    """
    return TestData.valid_users[0]


@pytest.fixture
def invalid_credentials():
    """
    Geçersiz kimlik bilgileri fixture'ı.

    Dönüş:
        dict: Geçersiz kimlik bilgileri
    """
    return TestData.invalid_users[1]


@pytest.fixture
def form_test_data():
    """
    Form test veri fixture'ı.

    Dönüş:
        list: Form test verileri
    """
    return TestData.form_data


@pytest.fixture
def api_client():
    """
    API istemci fixture'ı.

    Dönüş:
        object: API istemci nesnesi
    """
    import requests

    class APIClient:
        def __init__(self, base_url='http://localhost:5000/api'):
            self.base_url = base_url
            self.session = requests.Session()

        def get(self, endpoint):
            return self.session.get(f"{self.base_url}/{endpoint}")

        def post(self, endpoint, data):
            return self.session.post(f"{self.base_url}/{endpoint}", json=data)

        def put(self, endpoint, data):
            return self.session.put(f"{self.base_url}/{endpoint}", json=data)

        def delete(self, endpoint):
            return self.session.delete(f"{self.base_url}/{endpoint}")

        def close(self):
            self.session.close()

    return APIClient()
