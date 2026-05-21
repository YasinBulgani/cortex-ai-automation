"""
Proje ayarları ve konfigürasyon modülü.

Ortam-spesifik ayarları ve temel konfigürasyonları yönetir.
"""

import os
from dotenv import load_dotenv


# .env dosyasını yükle
load_dotenv()


class Settings:
    """
    Uygulama ayarlarını yönetir.
    """

    # Ortam seçimi
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')

    # Temel URL'ler
    BASE_URLS = {
        'dev': os.getenv('BASE_URL_DEV', 'http://localhost:3000'),
        'staging': os.getenv('BASE_URL_STAGING', 'https://staging.example.com'),
        'prod': os.getenv('BASE_URL_PROD', 'https://example.com')
    }

    BASE_URL = BASE_URLS.get(ENVIRONMENT, BASE_URLS['dev'])
    API_URL = os.getenv('API_URL', 'http://localhost:5000/api')

    # Browser ayarları
    BROWSER = os.getenv('BROWSER', 'chromium')
    HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'

    # Timeout ayarları (milisaniye cinsinden)
    DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', '5000'))
    NAVIGATION_TIMEOUT = int(os.getenv('NAVIGATION_TIMEOUT', '30000'))

    # Tekrar deneme ayarları
    RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '1'))

    # Kullanıcı kimlik bilgileri
    TEST_USERNAME = os.getenv('USERNAME', 'test_user')
    TEST_PASSWORD = os.getenv('PASSWORD', 'test_password')

    # Logging ayarları
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/test_execution.log')

    # Viewport ayarları
    VIEWPORT_WIDTH = int(os.getenv('VIEWPORT_WIDTH', '1920'))
    VIEWPORT_HEIGHT = int(os.getenv('VIEWPORT_HEIGHT', '1080'))

    # Locale ayarı
    LOCALE = os.getenv('LOCALE', 'tr-TR')


def get_base_url() -> str:
    """
    Geçerli ortam için temel URL'yi al.

    Dönüş:
        str: Temel URL
    """
    return Settings.BASE_URL


def get_api_url() -> str:
    """
    API URL'sini al.

    Dönüş:
        str: API URL
    """
    return Settings.API_URL
