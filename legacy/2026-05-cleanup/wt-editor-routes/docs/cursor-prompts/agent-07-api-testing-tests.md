# Agent 7: API Testing Domain Integration Tests

## Cursor'a yapistir:

```
Sen bir senior QA muhendisisin. BGTS bankacilik test otomasyon platformunun
api_testing domain'i icin integration testler yazacaksin.

## PROJE BILGILERI
- Router: backend/app/domains/api_testing/router.py
- Bu dosyayi MUTLAKA OKU — endpoint path'lerini, HTTP method'larini ve
  request body schema'larini buradan al.
- Schema'lar: backend/app/domains/api_testing/ altindaki schema dosyalarini da oku

## DIKKAT: IKI FARKLI ROUTER VAR
1. `backend/app/domains/api_testing/router.py` → prefix YOK veya `/api-testing`
   Bu router main.py'de `app.include_router(api_testing_router)` ile kayitli (prefix="/api/v1" YOK!)
   Yani endpoint'ler `/api-testing/...` seklinde olabilir

2. `backend/app/domains/tspm/router.py` icinde de api-test endpoint'leri var:
   `/api/v1/tspm/projects/{pid}/api-tests/collections/...`
   Bu TSPM'e ait — Agent 6'da test ediliyor, buraya DAHIL ETME

ONCE `backend/app/main.py` dosyasindaki router kaydi kontrol et:
```python
app.include_router(api_testing_router)  # prefix nedir?
```

## MEVCUT TESTLER
- `backend/tests/api/test_api_tests.py` → 6 test var, ama bunlar TSPM uzerinden
  /api/v1/tspm/projects/{pid}/api-tests/ endpoint'lerini test ediyor.
- api_testing domain'in KENDI router'i icin 0 test var.

## MEVCUT FIXTURE'LAR
- `client` — TestClient
- `auth_headers` — Admin Bearer token
- `db_ready` — DB hazir mi?
- `create_project` / `project_id` — Proje factory

## OLUSTUR: backend/tests/integration/test_api_testing_domain.py

ONCE router'i oku, sonra endpoint gruplarina gore test sinifi yaz.
Muhtemel gruplar (router'dan dogrula):

### Environments CRUD
```python
class TestEnvironments:
    def test_create_environment(self, client, auth_headers, db_ready, project_id):
        ...
    def test_list_environments(self, ...):
        ...
    def test_update_environment(self, ...):
        ...
    def test_delete_environment(self, ...):
        ...
    def test_environment_requires_auth(self, client):
        ...
```

### OpenAPI Spec Management
```python
class TestOpenAPISpecs:
    def test_upload_spec(self, ...):
        # Minimal valid OpenAPI spec upload
        ...
    def test_list_specs(self, ...):
        ...
    def test_get_spec(self, ...):
        ...
    def test_invalid_spec_rejected(self, ...):
        ...
```

### Discovered Endpoints
```python
class TestEndpoints:
    def test_list_endpoints(self, ...):
        ...
    def test_filter_endpoints(self, ...):
        ...
```

### AI Test Case Generation
```python
class TestCases:
    def test_generate_test_cases(self, ...):
        ...
    def test_list_test_cases(self, ...):
        ...
    def test_get_test_case(self, ...):
        ...
```

### Request Chains
```python
class TestChains:
    def test_create_chain(self, ...):
        ...
    def test_execute_chain(self, ...):
        ...
    def test_get_chain_results(self, ...):
        ...
```

## ONEMLI KURALLAR
1. MUTLAKA router dosyasini oku, endpoint path'leri tahmin etme
2. Her test bagimsiz calisabilmeli
3. db_ready yoksa pytest.skip
4. Auth guard: her grup icin 1 adet 401 testi
5. Minimum TOPLAM 25 test fonksiyonu
6. API testing endpoint'leri project_id gerektirebilir — factory kullan

## DOGRULAMA
```bash
cd backend && python3 -m pytest tests/integration/test_api_testing_domain.py --collect-only -q 2>&1 | tail -5
```
```
