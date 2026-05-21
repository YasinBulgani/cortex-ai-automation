# Agent 6: TSPM Integration Test Suite (148 endpoint, 0 test)

## Cursor'a yapistir:

```
Sen bir senior QA muhendisisin. BGTS bankacilik test otomasyon platformunun
EN BUYUK test bosligini kapatacaksin: TSPM domain'i.

148 endpoint var, 0 test. Bu kabul edilemez.

## PROJE BILGILERI
- Test dizini: backend/tests/integration/
- Router: backend/app/domains/tspm/router.py (5443 satir)
- Bu dosyayi MUTLAKA OKU — endpoint path'lerini, HTTP method'larini ve
  request body schema'larini buradan al. TAHMIN ETME.

## MEVCUT TEST ALTYAPISI

### backend/tests/conftest.py (kullanilabilir fixture'lar):
- `client` — FastAPI TestClient instance (scope=session)
- `db_ready` — DB baglantisi var mi? (bool, scope=session)
- `admin_token` / `auth_headers` — Admin JWT token ve {"Authorization": "Bearer ..."} header
- `operator_token` / `operator_headers` — Operator rolu
- `viewer_token` / `viewer_headers` — Viewer rolu (read-only)

### backend/tests/api/conftest.py (factory fixture'lar):
- `create_project(name=None, description="")` → project_id (str)
- `project_id` → hazir bir project_id
- `create_scenario(project_id, title=None, steps=None)` → scenario_id
- `create_requirement(project_id, external_id=None, title=None)` → requirement_id
- `create_execution(project_id, name=None, scenario_ids=None)` → execution_id
- `create_regression_set(project_id, name=None)` → regression_set_id
- `create_flow(project_id, name=None)` → flow_id
- `create_schedule(project_id, name=None, cron="0 2 * * *")` → schedule_id
- `create_test_data(project_id, name=None, columns=None, rows=None)` → test_data_id

## OLUSTURULACAK DOSYALAR

### 1. backend/tests/integration/test_tspm_core.py

```python
"""TSPM Core: Projects, Scenarios, Requirements, Executions."""
import pytest
from fastapi.testclient import TestClient


class TestProjectsCRUD:
    """Proje CRUD islemleri."""

    def test_create_project(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        r = client.post("/api/v1/tspm/projects",
                        json={"name": "Test Proje 1"}, headers=auth_headers)
        assert r.status_code == 201
        assert "id" in r.json()

    def test_list_projects(self, client, auth_headers, db_ready):
        ...

    def test_get_project(self, client, auth_headers, db_ready, create_project):
        ...

    def test_update_project(self, client, auth_headers, db_ready, create_project):
        ...

    def test_delete_project(self, client, auth_headers, db_ready, create_project):
        ...

    def test_project_requires_auth(self, client):
        r = client.get("/api/v1/tspm/projects")
        assert r.status_code == 401

    def test_project_not_found(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        r = client.get("/api/v1/tspm/projects/00000000-0000-0000-0000-000000000000",
                        headers=auth_headers)
        assert r.status_code == 404


class TestScenariosCRUD:
    """Senaryo CRUD islemleri."""

    def test_create_scenario(self, client, auth_headers, db_ready, create_project):
        ...  # POST /api/v1/tspm/projects/{pid}/scenarios

    def test_list_scenarios(self, ...):
        ...

    def test_get_scenario(self, ...):
        ...

    def test_update_scenario(self, ...):
        ...

    def test_delete_scenario(self, ...):
        ...

    def test_scenario_search(self, ...):
        ...  # GET ?q=... query param

    def test_scenario_bulk_status_update(self, ...):
        ...  # varsa


class TestRequirements:
    """Gereksinim CRUD islemleri."""
    # create, list, get, update, link to scenario
    ...


class TestExecutions:
    """Kosu (execution) CRUD islemleri."""
    # create, list, get, update status, add result
    ...
```

### 2. backend/tests/integration/test_tspm_advanced.py

```python
"""TSPM Advanced: Steps, Tags, Regression Sets, Flows, Schedules."""

class TestSteps:
    """Senaryo adimlari (steps) islemleri."""
    # add step to scenario, list steps, reorder, delete step
    ...

class TestTags:
    """Etiket yonetimi."""
    # create tag, list tags, assign tag to scenario, filter scenarios by tag
    ...

class TestRegressionSets:
    """Regresyon set yonetimi."""
    # create set, add scenarios to set, remove, list sets
    ...

class TestFlows:
    """Akis yonetimi."""
    # create flow, list flows, add scenario to flow, update order
    ...

class TestSchedules:
    """Zamanlama yonetimi."""
    # create schedule, list, update cron expression, delete
    ...
```

### 3. backend/tests/integration/test_tspm_analytics.py

```python
"""TSPM Analytics: Dashboard, Traceability, Imports, Test Data."""

class TestDashboard:
    """Proje dashboard ve istatistikler."""
    # get project stats, scenario count, execution summary
    ...

class TestTraceability:
    """Izlenebilirlik matrisi."""
    # get traceability matrix for project
    ...

class TestImports:
    """Manuel test import islemleri."""
    # import from text, import from file, validate parsed scenarios
    ...

class TestTestData:
    """Test verisi CRUD."""
    # create test data set, list, get, update, delete
    ...
```

### 4. backend/tests/integration/test_tspm_defects.py

```python
"""TSPM Defects: Hata kaydi yonetimi."""

class TestDefects:
    """Hata kaydi CRUD islemleri."""
    # create defect, list, get, update, link to scenario/execution
    ...
```

## ONEMLI KURALLAR

1. ONCE `backend/app/domains/tspm/router.py` dosyasini OKU
2. Endpoint path'lerini router'dan al — TAHMIN ETME
3. Request body'leri icin Pydantic model'leri kontrol et
4. Her test fonksiyonu bagimsiz calisabilmeli
5. db_ready yoksa pytest.skip("DB yok") kullan
6. CRUD sirasi: create → get → list → update → delete
7. Auth guard: her ana endpoint grubu icin 1 adet 401 testi
8. Not found: gecersiz UUID ile 404 testi
9. Minimum TOPLAM 60 test fonksiyonu
10. conftest.py'deki factory fixture'lari KULLAN (create_project, create_scenario, vb.)

## DOGRULAMA
```bash
cd backend && python3 -m pytest tests/integration/test_tspm_*.py --collect-only -q 2>&1 | tail -5
```
En az 60 test toplanmali.
```
