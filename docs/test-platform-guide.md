# BGTS Test Platformu — Kullanıcı Kılavuzu

BGTS Test Dönüşüm projesinin test otomasyon platformu için kapsamlı kılavuz.

---

## İçindekiler

1. [Hızlı Başlangıç](#1-hızlı-başlangıç)
2. [Mimari Genel Bakış](#2-mimari-genel-bakış)
3. [Test Türleri ve Çalıştırma](#3-test-türleri-ve-çalıştırma)
4. [Yeni Test Senaryosu Ekleme](#4-yeni-test-senaryosu-ekleme)
5. [Yeni Page Object Ekleme](#5-yeni-page-object-ekleme)
6. [Locator Güncelleme](#6-locator-güncelleme)
7. [CI/CD Pipeline](#7-cicd-pipeline)
8. [Rapor Üretimi ve Yorumlama](#8-rapor-üretimi-ve-yorumlama)
9. [Test Verisi Yönetimi](#9-test-verisi-yönetimi)
10. [API Test Koleksiyonları](#10-api-test-koleksiyonları)
11. [Sorun Giderme](#11-sorun-giderme)

---

## 1. Hızlı Başlangıç

### Ön Koşullar

- Python 3.11+
- Node.js 18+ (frontend için)
- PostgreSQL 16 ve Redis 7 (backend servisler için)

### Kurulum

```bash
# 1. Repo'yu klonla
git clone <repo-url> && cd Cortex_Ai_Automation

# 2. Python bağımlılıklarını yükle
cd engine
pip install -r requirements.txt

# 3. Playwright tarayıcılarını yükle
python -m playwright install chromium --with-deps

# 4. Ortam değişkenlerini ayarla (isteğe bağlı)
export BASE_URL="http://localhost:3000"
export API_URL="http://localhost:8000/api/v1"
export ENGINE_URL="http://localhost:5001"
```

### İlk Test Koşusu

```bash
# Smoke testleri — en hızlı doğrulama (~2 dk)
python bgts_runner.py --smoke

# Belirli bir feature testi
python bgts_runner.py --feature login

# Shell script ile (daha fazla seçenek)
./scripts/run_bgts_tests.sh --smoke
```

---

## 2. Mimari Genel Bakış

### Dizin Yapısı

```
Cortex_Ai_Automation/
├── engine/                          # Test otomasyon motoru
│   ├── features/BGTS/              # BDD feature dosyaları (Gherkin)
│   │   ├── login.feature
│   │   ├── projects.feature
│   │   ├── scenarios.feature
│   │   ├── approvals.feature
│   │   ├── import.feature
│   │   ├── synthetic_data.feature
│   │   ├── api_tests.feature
│   │   ├── regression.feature
│   │   └── smoke.feature
│   ├── pages/                       # Page Object Model (POM)
│   │   ├── base_page.py            # Temel POM (SALT-OKUNUR)
│   │   ├── login_page.py
│   │   ├── dashboard_page.py
│   │   ├── projects_page.py
│   │   ├── scenarios_page.py
│   │   ├── approvals_page.py
│   │   ├── import_page.py
│   │   └── common_nav.py
│   ├── steps/                       # BDD step tanımları
│   │   ├── common_steps.py          # Genel adımlar (SALT-OKUNUR)
│   │   ├── bgts_login_steps.py
│   │   ├── bgts_project_steps.py
│   │   ├── bgts_scenario_steps.py
│   │   ├── bgts_approval_steps.py
│   │   └── bgts_smoke_steps.py
│   ├── tests/e2e/                   # Pytest test dosyaları
│   │   ├── conftest.py              # Master conftest (fixture'lar)
│   │   ├── test_login.py
│   │   ├── test_projects.py
│   │   ├── test_scenarios.py
│   │   ├── test_approvals.py
│   │   ├── test_smoke.py
│   │   └── test_api_integration.py
│   ├── locators/                    # Merkezi locator deposu
│   │   ├── locator_repository.json  # Tüm UI seçicileri
│   │   └── locator_manager.py       # Locator yönetim sınıfı
│   ├── test_data/                   # Test verileri
│   │   ├── users.json
│   │   ├── projects.json
│   │   ├── scenarios.json
│   │   ├── api_payloads.json
│   │   ├── environments.json
│   │   └── fixtures.py              # Veri yardımcıları + üreticiler
│   ├── config/
│   │   ├── settings.py              # Genel ayarlar
│   │   └── test_config.py           # E2E test yapılandırması
│   ├── core/
│   │   ├── enhanced_framework.py    # Çekirdek framework (SALT-OKUNUR)
│   │   ├── reporter.py              # Çekirdek raporlayıcı (SALT-OKUNUR)
│   │   └── bgts_reporter.py         # BGTS rapor wrapper'ı
│   ├── bgts_runner.py               # BGTS test çalıştırıcısı
│   ├── runner.py                    # Çekirdek runner (SALT-OKUNUR)
│   └── scripts/
│       └── run_bgts_tests.sh        # Shell çalıştırma betiği
├── collections/                     # API test koleksiyonları
│   ├── postman/                     # Postman koleksiyonları
│   └── http/                        # VS Code REST Client dosyaları
├── reports/
│   └── templates/                   # Rapor şablonları
│       ├── html_report.html
│       └── email_report.html
├── .github/workflows/               # CI/CD pipeline'ları
│   ├── bgts-e2e.yml                 # Push/PR tetiklemeli E2E
│   └── bgts-scheduled.yml           # Zamanlanmış regresyon
└── docs/                            # Dokümantasyon
    ├── test-analysis/
    ├── test-design/
    └── validation-report.md
```

### Katmanlı Mimari

```
┌─────────────────────────────────────────────────┐
│              CI/CD (GitHub Actions)              │
├─────────────────────────────────────────────────┤
│           bgts_runner.py (CLI)                  │
│           run_bgts_tests.sh (Shell)             │
├─────────────────────────────────────────────────┤
│        Test Dosyaları (test_*.py)               │
│        @scenario(FEATURE, "Senaryo Adı")        │
├─────────────────────────────────────────────────┤
│     Step Tanımları (bgts_*_steps.py)            │
│     @given / @when / @then + POM kullanımı      │
├─────────────────────────────────────────────────┤
│       Page Object Model (pages/*.py)            │
│       LocatorManager + BasePage                 │
├─────────────────────────────────────────────────┤
│     Locator Repository (JSON)                   │
│     test_id → css → xpath fallback              │
├─────────────────────────────────────────────────┤
│        Test Verisi (JSON + fixtures.py)         │
├─────────────────────────────────────────────────┤
│  Core Framework (SALT-OKUNUR)                   │
│  base_page.py | enhanced_framework.py           │
│  runner.py    | reporter.py | common_steps.py   │
└─────────────────────────────────────────────────┘
```

### Teknoloji Yığını

| Bileşen | Teknoloji |
|---|---|
| BDD Framework | pytest-bdd (Gherkin) |
| Test Runner | pytest + pytest-xdist |
| Tarayıcı Otomasyonu | Playwright (Python) |
| API Testleri | httpx |
| Raporlama | Allure + özel HTML/e-posta |
| CI/CD | GitHub Actions |
| Dil | Python 3.11, Türkçe Gherkin |

---

## 3. Test Türleri ve Çalıştırma

### 3.1 Smoke Testleri

Her deployment sonrası çalıştırılacak minimum doğrulama seti. ~15 senaryo, ~2 dakika.

```bash
# Python runner ile
python bgts_runner.py --smoke

# Shell script ile
./scripts/run_bgts_tests.sh --smoke

# Rapor dahil
python bgts_runner.py --smoke --report
```

**Kapsam:** Backend sağlık, giriş, proje listesi, senaryo listesi, onay kuyruğu, içe aktarma, dashboard, Engine API, çıkış.

### 3.2 Regresyon Testleri

Sprint sonu ve release öncesi tam doğrulama. ~30 senaryo.

```bash
# Temel
python bgts_runner.py --regression

# Paralel (4 worker) + retry (2 deneme) + rapor
python bgts_runner.py --regression --parallel 4 --retry 2 --report

# Shell ile
./scripts/run_bgts_tests.sh --regression --parallel 4 --retry 2
```

**Kapsam:** Kimlik doğrulama, proje CRUD, senaryo CRUD/arama/BDD üretimi, onay akışı, içe aktarma, navigasyon, API endpoint'leri.

### 3.3 API Testleri

Backend ve Engine API endpoint'lerini doğrudan test eder (httpx tabanlı).

```bash
python bgts_runner.py --api

./scripts/run_bgts_tests.sh --api
```

**Kapsam:** Health, auth, TSPM projeler, senaryolar, onaylar, Engine feature/run.

### 3.4 Feature Bazlı Test

Belirli bir modülü tek başına test etmek için:

```bash
python bgts_runner.py --feature login
python bgts_runner.py --feature projects
python bgts_runner.py --feature scenarios
python bgts_runner.py --feature approvals
```

### 3.5 Tüm Testler

```bash
python bgts_runner.py --all --report --json-output reports/full-results.json

# Paralel
python bgts_runner.py --all --parallel 4 --report
```

### 3.6 Pytest ile Doğrudan Çalıştırma

```bash
cd engine

# Marker bazlı
pytest tests/ -m smoke -v --alluredir=allure-results

# Tek test dosyası
pytest tests/e2e/test_login.py -v

# Tek test fonksiyonu
pytest tests/e2e/test_login.py::test_successful_login -v

# Headed mod (tarayıcı görünür)
HEADLESS=false pytest tests/e2e/test_smoke.py -v
```

---

## 4. Yeni Test Senaryosu Ekleme

### Adım 1: Feature Dosyasına Senaryo Ekle

`engine/features/BGTS/<modül>.feature` dosyasına Gherkin senaryosu ekleyin:

```gherkin
Scenario: Yeni fonksiyon testi
  Given kullanıcı "/p/test-project/new-page" sayfasındadır
  When kullanıcı "[data-testid='button']" seçicisini tıklar
  Then "[data-testid='result']" elementi görünür olmalıdır
```

### Adım 2: Step Tanımı Ekle (Gerekirse)

Eğer mevcut `common_steps.py` adımları yeterli değilse, ilgili `bgts_*_steps.py` dosyasına özel adım ekleyin:

```python
@when(parsers.parse('kullanıcı "{action}" özel işlemini yapar'))
@allure.step("Özel işlem: {action}")
def custom_action(page, action: str):
    # POM kullanarak işlemi gerçekleştir
    pass
```

### Adım 3: Test Dosyasına @scenario Ekle

`engine/tests/e2e/test_<modül>.py` dosyasına:

```python
@allure.feature("Modül Adı")
@allure.story("Hikaye")
@pytest.mark.e2e
@pytest.mark.functional
@pytest.mark.P1
@scenario(FEATURE, "Yeni fonksiyon testi")
def test_new_function():
    """Test açıklaması."""
```

### Adım 4: Test Çalıştır

```bash
pytest tests/e2e/test_<modül>.py::test_new_function -v
```

---

## 5. Yeni Page Object Ekleme

### Adım 1: Locator'ları Tanımla

`engine/locators/locator_repository.json` dosyasına yeni sayfa ekleyin:

```json
{
  "new_page": {
    "url_pattern": "/p/{projectId}/new-page",
    "description": "Yeni sayfa açıklaması",
    "elements": {
      "page_container": {
        "css": "[data-testid='new-page']",
        "xpath": "//div[@data-testid='new-page']",
        "test_id": "new-page",
        "description": "Ana kapsayıcı",
        "wait_strategy": "visible"
      },
      "heading": {
        "css": "[data-testid='new-page-heading']",
        "xpath": "//h1[@data-testid='new-page-heading']",
        "test_id": "new-page-heading",
        "description": "Sayfa başlığı",
        "wait_strategy": "visible"
      }
    }
  }
}
```

### Adım 2: POM Sınıfı Oluştur

`engine/pages/new_page.py`:

```python
from __future__ import annotations
from typing import Optional
from playwright.sync_api import Page, expect
from pages.base_page import BasePage
from locators.locator_manager import LocatorManager

_PAGE = "new_page"

class NewPage(BasePage):
    """Yeni sayfa Page Object."""

    def __init__(
        self,
        page: Page,
        project_id: str = "test-project",
        locator_manager: Optional[LocatorManager] = None,
        base_url: str = "",
    ) -> None:
        super().__init__(page)
        self._project_id = project_id
        self.lm = locator_manager or LocatorManager()
        self._base_url = base_url

    def _loc(self, element: str) -> str:
        return self.lm.get_locator_with_fallback(_PAGE, element)

    def goto(self) -> "NewPage":
        url = f"{self._base_url}/p/{self._project_id}/new-page"
        self.navigate(url)
        return self

    def assert_page_loaded(self) -> "NewPage":
        expect(self.page.locator(self._loc("page_container"))).to_be_visible()
        return self
```

### Adım 3: conftest.py'ye Fixture Ekle

`engine/tests/e2e/conftest.py` dosyasına:

```python
from pages.new_page import NewPage

@pytest.fixture()
def new_page(authenticated_page: Page, locator_manager: LocatorManager) -> NewPage:
    return NewPage(
        authenticated_page,
        project_id="test-project",
        locator_manager=locator_manager,
        base_url=test_config.BASE_URL,
    )
```

---

## 6. Locator Güncelleme

### Locator Deposu Yapısı

`engine/locators/locator_repository.json` merkezi locator deposudur. Her element üç strateji içerir:

```json
{
  "element_name": {
    "css": "[data-testid='...']",
    "xpath": "//div[@data-testid='...']",
    "test_id": "...",
    "description": "Türkçe açıklama",
    "wait_strategy": "visible"
  }
}
```

### Fallback Zinciri

`LocatorManager` locator'ları şu sırayla dener: **test_id → css → xpath**

Bu self-healing mekanizması, bir seçici kırıldığında otomatik olarak alternatife geçer.

### Locator Güncelleme Adımları

1. `locator_repository.json` dosyasında ilgili element'i bulun
2. `css`, `xpath` ve `test_id` değerlerini güncelleyin
3. Tüm üç stratejiyi tutarlı tutun
4. `wait_strategy` gerekirse güncelleyin (`visible`, `attached`, `hidden`)

### Locator Sağlık Kontrolü

```python
from locators.locator_manager import LocatorManager

lm = LocatorManager()
# Depodaki tüm sayfaları listele
print(lm.list_pages())
# Bir sayfadaki elementleri listele
print(lm.list_elements("login"))
```

Canlı sayfada doğrulama:

```python
report = lm.validate_locators(playwright_page, page_name="login")
for key, info in report.items():
    print(f"{key}: {info['status']} — {info['strategies']}")
```

---

## 7. CI/CD Pipeline

### 7.1 bgts-e2e.yml — Push/PR Tetiklemeli

**Tetikleme:** `main` branch'e push veya PR açıldığında.

**İş Akışı:**

```
┌──────────────┐     ┌──────────────┐
│ Smoke Tests  │     │  API Tests   │  (Paralel)
│   (~5 dk)    │     │   (~3 dk)    │
└──────┬───────┘     └──────────────┘
       │
       ▼ (smoke başarılıysa)
┌──────────────────┐
│ Regression Tests │  (Smoke'a bağımlı)
│    (~15 dk)      │
└──────────────────┘
```

**Özellikler:**
- PostgreSQL 16 ve Redis 7 service container'ları
- Playwright chromium tarayıcı cache'leme
- Allure results + HTML reports artifact upload
- Hata durumunda screenshot upload
- GitHub Step Summary raporu

**Manuel tetikleme:**

```
workflow_dispatch → test_scope: all | smoke | regression | api
```

### 7.2 bgts-scheduled.yml — Zamanlanmış Regresyon

**Tetikleme:** Hafta içi her gün 02:00 UTC (Türkiye saati 05:00).

**Özellikler:**
- 4 paralel worker ile tam regresyon
- 2 retry denemesi
- Başarısızlık durumunda Slack/Teams webhook bildirimi
- Artifact'lar 30 gün saklanır

### 7.3 Pipeline Sonuçlarını İzleme

1. GitHub Actions sayfasından workflow koşularını izleyin
2. Artifact'lardan Allure raporu indirin
3. "BGTS Regression Test Sonuçları" step summary'yi kontrol edin

---

## 8. Rapor Üretimi ve Yorumlama

### 8.1 Allure Raporu

```bash
# Test çalıştır ve rapor üret
python bgts_runner.py --smoke --report

# Raporu tarayıcıda aç
allure open engine/allure-report
```

### 8.2 JSON Çıktı

```bash
python bgts_runner.py --smoke --json-output reports/results.json
```

JSON çıktısı şunları içerir:

```json
{
  "total": 15,
  "passed": 14,
  "failed": 1,
  "skipped": 0,
  "errors": 0,
  "duration_seconds": 45.23,
  "success_rate": 93.33,
  "failures": [
    {
      "test": "test_smoke::test_smoke_01_backend_health",
      "message": "Health endpoint yanıt vermedi",
      "type": "AssertionError"
    }
  ],
  "timestamp": "2026-04-03T18:00:00"
}
```

### 8.3 HTML Rapor

`reports/templates/html_report.html` şablonu Tailwind CSS dark theme kullanır. `bgts_reporter.py` tarafından render edilir:

```python
from core.bgts_reporter import BGTSReporter

reporter = BGTSReporter()
reporter.generate_html(result_data, output_path="reports/output.html")
```

### 8.4 E-posta Raporu

`reports/templates/email_report.html` e-posta istemcilerine uyumlu inline CSS kullanır:

```python
reporter.generate_email(result_data, output_path="reports/email.html")
```

### 8.5 Rapor Yorumlama

| Metrik | Anlamı |
|---|---|
| `success_rate` | Başarılı test yüzdesi |
| `failures` | Başarısız testlerin listesi ve hata mesajları |
| `duration_seconds` | Toplam koşu süresi |
| `skipped` | Atlanan testler (genelde eksik ön koşul) |

**Allure Raporu İpuçları:**
- "Suites" sekmesi test dosyalarına göre gruplanmış sonuçları gösterir
- "Behaviors" sekmesi `@allure.feature` / `@allure.story` gruplarını gösterir
- Her testin detayında screenshot, trace ve adım geçmişi bulunur
- Başarısız testlerde "Hata Screenshot" eki otomatik eklenir

---

## 9. Test Verisi Yönetimi

### 9.1 JSON Fixture Dosyaları

| Dosya | İçerik | Kullanım |
|---|---|---|
| `users.json` | Kullanıcı hesapları (admin, tester, viewer, deaktif) | Giriş testleri |
| `projects.json` | Test projeleri | Proje CRUD testleri |
| `scenarios.json` | Test senaryoları | Senaryo testleri |
| `api_payloads.json` | API istek gövdeleri | API testleri |
| `environments.json` | Ortam yapılandırmaları (dev, staging, prod) | Çoklu ortam |
| `locator_test_data.json` | Locator test verileri | Locator doğrulama |
| `synthetic_data_config.json` | Sentetik veri üretim ayarları | Veri üretimi |

### 9.2 Test Verisine Erişim

```python
from test_data.fixtures import (
    get_admin_user,
    get_user_by_role,
    get_test_projects,
    get_test_scenarios,
    get_api_payload,
    get_environment,
)

admin = get_admin_user()
tester = get_user_by_role("tester")
projects = get_test_projects()
payload = get_api_payload("create_project")
```

### 9.3 Türk Bankacılık Verisi Üreticileri

`fixtures.py` algoritmik olarak geçerli Türk bankacılık test verileri üretir:

```python
from test_data.fixtures import (
    random_tckn,        # Geçerli TC Kimlik No (11 haneli, mod-10/mod-11)
    validate_tckn,      # TCKN doğrulama
    random_iban,        # Geçerli TR IBAN (ISO 13616 mod-97)
    validate_iban,      # IBAN doğrulama
    random_phone,       # +90 5XX XXX XX XX formatında telefon
    random_email,       # Türkçe uyumlu e-posta
    random_turkish_name,# Ad-soyad çifti
    random_currency_amount,  # TL tutarı
    random_customer_id,      # CIF formatında müşteri no
)

tckn = random_tckn()       # "12345678902"
assert validate_tckn(tckn)  # True

iban = random_iban()        # "TR330006100519786457841326"
assert validate_iban(iban)  # True
```

---

## 10. API Test Koleksiyonları

### 10.1 Postman

`collections/postman/` altında dört dosya bulunur:

| Dosya | Kullanım |
|---|---|
| `BGTS_Backend_API.postman_collection.json` | Backend API tam koleksiyonu — Postman'e import edin |
| `BGTS_Engine_API.postman_collection.json` | Engine API tam koleksiyonu |
| `BGTS_Environment_Dev.postman_environment.json` | Dev ortam değişkenleri |
| `BGTS_Environment_Staging.postman_environment.json` | Staging ortam değişkenleri |

**Import:** Postman → Import → Upload Files → İlgili JSON dosyasını seçin.

### 10.2 VS Code REST Client

`collections/http/` altındaki `.http` dosyaları VS Code REST Client eklentisi ile doğrudan çalıştırılabilir:

- `backend-api.http` — Backend REST API istekleri
- `engine-api.http` — Engine Flask API istekleri
- `smoke-tests.http` — Sıralı smoke test zinciri

**Kullanım:** VS Code'da dosyayı açın → İsteklerin üstündeki "Send Request" bağlantısına tıklayın.

---

## 11. Sorun Giderme

### Playwright Tarayıcı Hatası

```
Error: Browser not installed
```

**Çözüm:**
```bash
python -m playwright install chromium --with-deps
```

### Bağlantı Hatası (Connection Refused)

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Çözüm:** Backend ve Engine servislerinin çalıştığından emin olun:
```bash
# Backend
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Engine
cd engine && python -m flask run --host 0.0.0.0 --port 5001
```

### Locator Bulunamadı

```
KeyError: "Element bulunamadı: 'new_element' (sayfa: 'login')"
```

**Çözüm:** `locator_repository.json` dosyasında ilgili element tanımını kontrol edin. Self-healing kullanmak için:

```python
selector = lm.self_heal("login", "email_input", playwright_page)
```

### Zaman Aşımı (Timeout)

```
TimeoutError: Timeout 30000ms exceeded
```

**Çözüm:**
1. Ortam değişkeni ile timeout artırın: `DEFAULT_TIMEOUT=60000`
2. `test_config.py`'de `NAVIGATION_TIMEOUT` değerini artırın
3. Network yavaşlığı durumunda `wait_for_load_state("networkidle")` ekleyin

### Allure Raporu Üretilemedi

```
Allure CLI bulunamadı
```

**Çözüm:**
```bash
# macOS
brew install allure

# Linux
sudo apt-get install allure

# npm
npm install -g allure-commandline
```

### CI'da Test Başarısızlığı

1. GitHub Actions'da workflow koşusunu açın
2. Artifact'lardan screenshot ve trace dosyalarını indirin
3. Allure results artifact'ını indirip yerel olarak rapor üretin:
```bash
allure serve downloaded-allure-results/
```

### Paralel Test Hatası

```
ModuleNotFoundError: No module named 'pytest_xdist'
```

**Çözüm:**
```bash
pip install pytest-xdist
```

### Retry Çalışmıyor

```bash
# --retry parametresi bgts_runner.py seviyesinde çalışır
python bgts_runner.py --smoke --retry 2

# pytest seviyesinde rerun:
pip install pytest-rerunfailures
pytest tests/ --reruns 2 --reruns-delay 1
```

---

## Ek: Ortam Değişkenleri Referansı

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `BASE_URL` | `http://localhost:3000` | Frontend URL |
| `API_URL` | `http://localhost:8000/api/v1` | Backend API URL |
| `ENGINE_URL` | `http://localhost:5001` | Engine API URL |
| `BROWSER` | `chromium` | Tarayıcı (chromium/firefox/webkit) |
| `HEADLESS` | `true` | Tarayıcı görünürlüğü |
| `DEFAULT_TIMEOUT` | `30000` | Varsayılan bekleme süresi (ms) |
| `NAVIGATION_TIMEOUT` | `60000` | Navigasyon bekleme süresi (ms) |
| `SCREENSHOT_ON_FAILURE` | `true` | Hata durumunda screenshot al |
| `TRACE_ON_FAILURE` | `true` | Hata durumunda trace kaydet |
| `RETRY_COUNT` | `2` | Yeniden deneme sayısı |
| `PARALLEL_WORKERS` | `1` | Paralel worker sayısı |
| `ALLURE_RESULTS_DIR` | `engine/allure-results` | Allure sonuç dizini |
| `TEST_ENV` | `test` | Test ortamı (test/staging/prod) |
| `VIEWPORT_WIDTH` | `1280` | Tarayıcı genişliği |
| `VIEWPORT_HEIGHT` | `720` | Tarayıcı yüksekliği |

---

## Ek: Marker Referansı

| Marker | Açıklama | Kullanım |
|---|---|---|
| `@pytest.mark.smoke` | Smoke testleri | `pytest -m smoke` |
| `@pytest.mark.e2e` | E2E testler | `pytest -m e2e` |
| `@pytest.mark.functional` | Fonksiyonel testler | `pytest -m functional` |
| `@pytest.mark.regression` | Regresyon testleri | `pytest -m regression` |
| `@pytest.mark.api` | API testleri | `pytest -m api` |
| `@pytest.mark.P1` | Yüksek öncelik | `pytest -m P1` |
| `@pytest.mark.P2` | Normal öncelik | `pytest -m P2` |

---

_Bu kılavuz, BGTS Test Dönüşüm projesinin mevcut dosya yapısına dayalı olarak oluşturulmuştur._
