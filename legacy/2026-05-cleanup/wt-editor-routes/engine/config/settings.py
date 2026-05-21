"""
Merkezi Konfigurasyon Modulu
.env dosyasindan ayarlari yukler ve tum proje genelinde kullanilabilir hale getirir.
Multi-environment (test/staging/prod) ve multi-domain destegi icerir.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Proje kok dizini
BASE_DIR = Path(__file__).resolve().parent.parent

# .env dosyasini yukle (once engine/.env, sonra root .env)
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


class Settings:
    # Proje ROOT dizini
    BASE_DIR: Path = BASE_DIR

    # AI Ayarlari
    # Varsayılan provider: ollama (lokal, token gerekmez, en hızlı)
    # Alternatif: huggingface (cloud, ücretsiz tier)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")

    # Ollama config (default provider) — lokal LLM
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_DEFAULT_MODEL: str = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:14b")
    OLLAMA_POWERFUL_MODEL: str = os.getenv("OLLAMA_POWERFUL_MODEL", "qwen2.5:32b")
    OLLAMA_FAST_MODEL: str = os.getenv("OLLAMA_FAST_MODEL", "llama3.1:8b")
    OLLAMA_CODER_MODEL: str = os.getenv("OLLAMA_CODER_MODEL", "qwen2.5-coder:7b")
    OLLAMA_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "-1")

    # HuggingFace config (alternatif cloud provider)
    HF_TOKEN: str = os.getenv("HF_TOKEN", os.getenv("HUGGINGFACE_TOKEN", ""))
    HF_DEFAULT_MODEL: str = os.getenv("HF_DEFAULT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
    HF_POWERFUL_MODEL: str = os.getenv("HF_POWERFUL_MODEL", "meta-llama/Meta-Llama-3-70B-Instruct")
    HF_FAST_MODEL: str = os.getenv("HF_FAST_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    HF_CODER_MODEL: str = os.getenv("HF_CODER_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")

    # Legacy providers (backward compat)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Tarayici Ayarlari
    BROWSER: str = os.getenv("BROWSER", "chromium")
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"

    # URL
    BASE_URL: str = os.getenv("BASE_URL", "https://example.com")
    if not BASE_URL:
        BASE_URL = "https://example.com"

    # Timeout (ms)
    DEFAULT_TIMEOUT: int = int(os.getenv("DEFAULT_TIMEOUT", "30000"))
    NAVIGATION_TIMEOUT: int = int(os.getenv("NAVIGATION_TIMEOUT", "60000"))

    # Proje Ayarlari
    ACTIVE_PROJECT: str = None

    # Multi-environment & Multi-domain (NexusQA pattern)
    ENVIRONMENT: str = os.getenv("TEST_ENV", "test")
    DOMAIN: str = os.getenv("TEST_DOMAIN", "default")
    DOMAINS: list[str] = [
        d.strip()
        for d in os.getenv("TEST_DOMAINS", "default").split(",")
        if d.strip()
    ]

    # Locator & Test Data dizinleri
    LOCATORS_DIR: Path = BASE_DIR / "data" / "locators"
    TESTDATA_DIR: Path = BASE_DIR / "data" / "testdata"

    # Dizinler
    REPORTS_DIR: Path = BASE_DIR / "reports"
    SCREENSHOTS_DIR: Path = BASE_DIR / "screenshots"
    TESTS_DIR: Path = BASE_DIR / "tests"
    SCRIPTS_DIR: Path = BASE_DIR / "scripts"
    FEATURES_DIR: Path = BASE_DIR / "features"
    ALLURE_RESULTS_DIR: Path = BASE_DIR / "allure-results"
    ALLURE_REPORT_DIR: Path = BASE_DIR / "allure-report"
    DB_PATH: Path = BASE_DIR / "test_data.db"

    # Mobil / Appium Ayarları
    APPIUM_URL: str = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")
    MOBILE_ARTIFACTS_DIR: Path = Path(os.getenv("MOBILE_ARTIFACTS_DIR", str(BASE_DIR / "mobile_uploads")))

    # ── Gerçek Cihaz Farm — BrowserStack ─────────────────────────────────────
    # Ayarlandığında BrowserStack Automate (Playwright CDP) kullanılır
    BROWSERSTACK_USERNAME: str = os.getenv("BROWSERSTACK_USERNAME", "")
    BROWSERSTACK_ACCESS_KEY: str = os.getenv("BROWSERSTACK_ACCESS_KEY", "")
    BROWSERSTACK_BUILD: str = os.getenv("BROWSERSTACK_BUILD", "Visium Farm Build")
    BROWSERSTACK_PROJECT: str = os.getenv("BROWSERSTACK_PROJECT", "BGTS Nexus QA")

    # ── Gerçek Cihaz Farm — Sauce Labs ───────────────────────────────────────
    SAUCE_USERNAME: str = os.getenv("SAUCE_USERNAME", "")
    SAUCE_ACCESS_KEY: str = os.getenv("SAUCE_ACCESS_KEY", "")
    SAUCE_REGION: str = os.getenv("SAUCE_REGION", "eu-central")  # eu-central | us-west

    def __init__(self):
        self.REPORTS_DIR.mkdir(exist_ok=True)
        self.SCREENSHOTS_DIR.mkdir(exist_ok=True)
        self.FEATURES_DIR.mkdir(exist_ok=True)
        self.ALLURE_RESULTS_DIR.mkdir(exist_ok=True)
        self.LOCATORS_DIR.mkdir(parents=True, exist_ok=True)
        self.TESTDATA_DIR.mkdir(parents=True, exist_ok=True)
        self.MOBILE_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    def load_environment(self, env_name: str):
        """
        Belirtilen ortam icin ek .env dosyasini yukler.
        Dosya yolu: engine/config/environments/{env_name}.env
        """
        env_file = BASE_DIR / "config" / "environments" / f"{env_name}.env"
        if env_file.exists():
            load_dotenv(env_file, override=True)
            self._reload_from_env()
            self.ENVIRONMENT = env_name

    def set_domain(self, domain: str):
        """Aktif domain'i degistirir."""
        self.DOMAIN = domain

    def get_domain_url(self, domain: str = None) -> str:
        """
        Domain bazli URL doner.
        Oncelik: URL_{DOMAIN}_{ENV} env var > BASE_URL
        """
        d = domain or self.DOMAIN
        env_key = f"URL_{d.upper()}_{self.ENVIRONMENT.upper()}"
        return os.getenv(env_key, self.BASE_URL)

    def set_active_project(self, project_name: str = None):
        """Aktif projeyi ayarla ve dizinleri guncelle."""
        if project_name is None or project_name == "main":
            self.ACTIVE_PROJECT = None
            base = BASE_DIR
        else:
            self.ACTIVE_PROJECT = project_name
            base = BASE_DIR / "projects" / project_name

        self.REPORTS_DIR = base / "reports"
        self.SCREENSHOTS_DIR = base / "screenshots"
        self.TESTS_DIR = base / "tests"
        self.SCRIPTS_DIR = base / "scripts"
        self.FEATURES_DIR = base / "features"
        self.ALLURE_RESULTS_DIR = base / "allure-results"
        self.ALLURE_REPORT_DIR = base / "allure-report"
        self.DB_PATH = base / "test_data.db"

        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self.FEATURES_DIR.mkdir(parents=True, exist_ok=True)
        self.ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def validate(self):
        """Kritik ayarlari dogrula."""
        if not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY eksik! Lutfen .env dosyasina ekleyin.\n"
                "Ornek icin .env.example dosyasina bakin."
            )

    def _reload_from_env(self):
        """Env degiskenlerini yeniden okur (ortam degistiginde)."""
        self.BROWSER = os.getenv("BROWSER", self.BROWSER)
        self.HEADLESS = os.getenv("HEADLESS", str(self.HEADLESS)).lower() == "true"
        self.BASE_URL = os.getenv("BASE_URL", self.BASE_URL) or "https://example.com"
        self.DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", str(self.DEFAULT_TIMEOUT)))
        self.NAVIGATION_TIMEOUT = int(os.getenv("NAVIGATION_TIMEOUT", str(self.NAVIGATION_TIMEOUT)))
        self.BROWSERSTACK_USERNAME = os.getenv("BROWSERSTACK_USERNAME", self.BROWSERSTACK_USERNAME)
        self.BROWSERSTACK_ACCESS_KEY = os.getenv("BROWSERSTACK_ACCESS_KEY", self.BROWSERSTACK_ACCESS_KEY)
        self.SAUCE_USERNAME = os.getenv("SAUCE_USERNAME", self.SAUCE_USERNAME)
        self.SAUCE_ACCESS_KEY = os.getenv("SAUCE_ACCESS_KEY", self.SAUCE_ACCESS_KEY)


settings = Settings()
