# BGTS Test Dönüşüm — BDD Step Definitions Eşleştirme Rehberi

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Framework:** pytest-bdd (Python) veya Behave  
**Dil:** Türkçe Gherkin (`# language: tr`)

---

## 1. Türkçe Gherkin Anahtar Kelime Eşleştirmesi

| Türkçe | İngilizce | pytest-bdd Decorator |
|--------|-----------|---------------------|
| Özellik | Feature | — (dosya seviyesi) |
| Arka plan | Background | `@scenario` içinde otomatik |
| Senaryo | Scenario | `@scenario("file.feature", "Senaryo adı")` |
| Senaryo Taslağı | Scenario Outline | `@scenario` + `examples` |
| Diyelim ki | Given | `@given("...")` |
| Ve | And | Önceki keyword'ü tekrarlar |
| O zaman | Then | `@then("...")` |
| Örnekler | Examples | Parametrize decorator ile |

---

## 2. Ortak Step Definitions (Tüm Feature'larda Kullanılan)

### Fixture: API Client

```python
# conftest.py
import pytest
import httpx

@pytest.fixture
def api_client():
    return httpx.Client(base_url="http://127.0.0.1:8000")

@pytest.fixture
def admin_token(api_client):
    res = api_client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "admin123"
    })
    return res.json()["access_token"]

@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
```

### Given Steps (Ön Koşullar)

| Türkçe Step | Step Definition | Parametre |
|-------------|----------------|-----------|
| `kullanıcı oturum açmış ve geçerli JWT token'a sahip` | `admin_token` fixture kullanılır | — |
| `"Test Projesi" adıyla bir proje mevcut` | `POST /tspm/projects` ile proje oluşturur | `proje_adi` |
| `projede senaryolar mevcut` | `POST .../scenarios` ile N senaryo oluşturur | — |
| `admin kullanıcısı mevcut` | Seed data'dan gelir | — |
| `devre dışı bırakılmış kullanıcı mevcut` | DB'de `is_active=False` user oluşturur | — |
| `"pending" statusünde bir onay mevcut` | `POST .../approvals` ile onay oluşturur | — |

### Then Steps (Doğrulamalar)

| Türkçe Step | Assertion | Pattern |
|-------------|-----------|---------|
| `yanıt kodu {kod} olmalı` | `assert response.status_code == kod` | `(\d+)` |
| `yanıtta "{alan}" alanı dolu olmalı` | `assert response.json()[alan]` | `"(.+)"` |
| `yanıtta "{alan}" değeri "{değer}" olmalı` | `assert response.json()[alan] == değer` | `"(.+)".*"(.+)"` |
| `yanıtta "{alan}" değeri {sayı} olmalı` | `assert response.json()[alan] == int(sayı)` | `"(.+)".*(\d+)` |
| `yanıtta "{mesaj}" mesajı olmalı` | `assert mesaj in response.json()["detail"]` | `"(.+)"` |
| `yanıtta "{alan}" değeri null olmalı` | `assert response.json()[alan] is None` | `"(.+)"` |
| `yanıtta "{alan}" değeri false olmalı` | `assert response.json()[alan] == False` | `"(.+)"` |
| `yanıtta "{alan}" değeri true olmalı` | `assert response.json()[alan] == True` | `"(.+)"` |

---

## 3. Feature → Step Definition Eşleştirmesi

### authentication.feature

```python
# steps/test_authentication.py
from pytest_bdd import scenario, given, when, then, parsers

@scenario("../features/authentication.feature", "Geçerli bilgilerle başarılı oturum açma")
def test_successful_login(): pass

@given("kullanıcı login endpoint'ine istek hazırlıyor")
def login_request(request_context):
    request_context["body"] = {}

@given(parsers.parse('e-posta alanına "{email}" yazıyor'))
def set_email(request_context, email):
    request_context["body"]["email"] = email

@given(parsers.parse('parola alanına "{password}" yazıyor'))
def set_password(request_context, password):
    request_context["body"]["password"] = password

@when('POST "/api/v1/auth/login" isteği gönderilir')
def send_login(api_client, request_context):
    request_context["response"] = api_client.post(
        "/api/v1/auth/login", json=request_context["body"]
    )

@then(parsers.parse("yanıt kodu {code:d} olmalı"))
def check_status(request_context, code):
    assert request_context["response"].status_code == code

@then("token JWT formatında (3 nokta-ayrılmış segment) olmalı")
def check_jwt_format(request_context):
    token = request_context["response"].json()["access_token"]
    assert len(token.split(".")) == 3
```

### scenario_management.feature

```python
# steps/test_scenario_management.py

@given(parsers.parse('projede "{title}" başlıklı senaryo mevcut'))
def create_scenario(api_client, auth_headers, project_id, title):
    res = api_client.post(
        f"/api/v1/tspm/projects/{project_id}/scenarios",
        headers=auth_headers,
        json={"title": title, "steps": []},
    )
    return res.json()["id"]

@when("senaryo başlığı güncellenir")
def update_scenario(api_client, auth_headers, project_id, scenario_id, new_title):
    return api_client.put(
        f"/api/v1/tspm/projects/{project_id}/scenarios/{scenario_id}",
        headers=auth_headers,
        json={"title": new_title},
    )

@then(parsers.parse('yanıtta "current_version" değeri {version:d} olmalı'))
def check_version(response, version):
    assert response.json()["current_version"] == version
```

---

## 4. Parametrize Pattern'ları

### Senaryo Taslağı (Scenario Outline) Eşleştirmesi

```python
@scenario(
    "../features/authentication.feature",
    "Geçersiz giriş verileri ile validation hatası",
)
def test_invalid_login(): pass

# Örnekler tablosundaki her satır otomatik olarak
# parametrize edilir: email, parola, kod
```

### Ortak Fixtures

```python
@pytest.fixture
def request_context():
    """Adımlar arası veri paylaşımı."""
    return {}

@pytest.fixture
def project_id(api_client, auth_headers):
    """Test için proje oluşturur."""
    res = api_client.post(
        "/api/v1/tspm/projects",
        headers=auth_headers,
        json={"name": f"BDD Test {uuid4().hex[:8]}"},
    )
    return res.json()["id"]

@pytest.fixture
def scenario_ids(api_client, auth_headers, project_id):
    """Test için N senaryo oluşturur."""
    ids = []
    for i in range(3):
        res = api_client.post(
            f"/api/v1/tspm/projects/{project_id}/scenarios",
            headers=auth_headers,
            json={"title": f"BDD Senaryo {i+1}"},
        )
        ids.append(res.json()["id"])
    return ids
```

---

## 5. Feature Dosyası → Test Dosyası Eşleştirmesi

| Feature Dosyası | Test Dosyası | Step Modülü |
|-----------------|-------------|-------------|
| `authentication.feature` | `tests/bdd/test_auth.py` | `steps/auth_steps.py` |
| `project_management.feature` | `tests/bdd/test_projects.py` | `steps/project_steps.py` |
| `scenario_management.feature` | `tests/bdd/test_scenarios.py` | `steps/scenario_steps.py` |
| `execution_and_analytics.feature` | `tests/bdd/test_executions.py` | `steps/execution_steps.py` |
| `requirements_coverage.feature` | `tests/bdd/test_requirements.py` | `steps/requirement_steps.py` |
| `regression_sets.feature` | `tests/bdd/test_regression.py` | `steps/regression_steps.py` |
| `schedules_and_test_data.feature` | `tests/bdd/test_schedules.py` | `steps/schedule_steps.py` |
| `approvals_and_imports.feature` | `tests/bdd/test_approvals.py` | `steps/approval_steps.py` |
| `flows_integrations_api_tests.feature` | `tests/bdd/test_flows.py` | `steps/flow_steps.py` |
| `members_and_dashboard.feature` | `tests/bdd/test_members.py` | `steps/member_steps.py` |

---

## 6. Çalıştırma

```bash
# Tüm BDD testlerini çalıştır
cd backend
PYTHONPATH=. pytest tests/bdd/ -v --gherkin-terminal-reporter

# Belirli bir feature
PYTHONPATH=. pytest tests/bdd/test_auth.py -v

# Tag bazlı çalıştırma
PYTHONPATH=. pytest tests/bdd/ -v -k "critical"
PYTHONPATH=. pytest tests/bdd/ -v -k "pozitif"
PYTHONPATH=. pytest tests/bdd/ -v -k "negatif or boundary"
```
