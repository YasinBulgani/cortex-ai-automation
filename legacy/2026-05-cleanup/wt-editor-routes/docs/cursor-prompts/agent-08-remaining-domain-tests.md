# Agent 8: Kalan Test Edilmemis Domain'ler

## Cursor'a yapistir:

```
Sen bir senior QA muhendisisin. BGTS bankacilik test otomasyon platformundaki
test edilmemis 6 domain icin integration testler yazacaksin.

## PROJE BILGILERI
- Test dizini: backend/tests/integration/
- Mevcut fixture'lar (backend/tests/conftest.py):
  - `client` — FastAPI TestClient
  - `auth_headers` — Admin Bearer token header
  - `db_ready` — DB baglantisi var mi
  - `create_project` / `project_id` — Proje factory (backend/tests/api/conftest.py)

## KRITIK KURAL
Her router dosyasini ONCE OKU. Endpoint path'lerini, method'lari ve request
body'leri router'dan al. TAHMIN ETME.

---

## DOMAIN 1: Notifications (3 endpoint)
Router: backend/app/domains/notifications/router.py (100 satir)

Dosya: backend/tests/integration/test_notifications.py

```python
"""Bildirim tercihleri integration testleri."""
import pytest
from fastapi.testclient import TestClient


class TestNotifications:

    def test_requires_auth(self, client: TestClient):
        # Endpoint'lere auth olmadan erisim → 401
        ...

    def test_list_notification_prefs(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        # GET endpoint'ini router'dan bul
        ...

    def test_update_notification_prefs(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        # PUT/PATCH endpoint'ini router'dan bul
        ...

    def test_websocket_connection(self, client, auth_headers, db_ready):
        # WebSocket endpoint varsa test et
        # Yoksa bu testi yazma
        ...
```

---

## DOMAIN 2: Audit (1+ endpoint)
Router: backend/app/domains/audit/router.py (72 satir)

Dosya: backend/tests/integration/test_audit.py

```python
"""Denetim izi (audit trail) integration testleri."""

class TestAudit:

    def test_requires_auth(self, client):
        ...  # 401

    def test_list_audit_logs(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        # GET audit logs endpoint
        ...

    def test_audit_log_filter(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        # Query param ile filtreleme (action, user, date range)
        ...

    def test_audit_log_pagination(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        # limit/offset veya page parametreleri
        ...
```

---

## DOMAIN 3: Automation (2 endpoint)
Router: backend/app/domains/automation/router.py (59 satir)

Bu router Engine service'e proxy yapiyor. Engine calismiyorsa 502/503 donebilir.

Dosya: backend/tests/integration/test_automation.py

```python
"""Otomasyon motoru proxy integration testleri."""

class TestAutomation:

    def test_requires_auth(self, client):
        ...  # 401

    def test_trigger_run(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        # POST endpoint — engine down ise 502/503 kabul et
        ...

    def test_get_run_status(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        # GET endpoint — engine down ise 502/503 kabul et
        ...
```

---

## DOMAIN 4: CI/CD (7 endpoint)
Router: backend/app/domains/cicd/router.py (404 satir)

Webhook endpoint'leri signature dogrulama yapabilir. Auth gerektirmeyebilir
(webhook'lar disaridan gelir).

Dosya: backend/tests/integration/test_cicd.py

```python
"""CI/CD webhook integration testleri."""
import hmac
import hashlib
import json

class TestCICD:

    def test_github_webhook_invalid_signature(self, client):
        # POST /api/v1/cicd/webhook/github (veya ne ise)
        # Gecersiz X-Hub-Signature-256 → 401
        ...

    def test_github_webhook_missing_signature(self, client):
        # Signature header yok → 401
        ...

    def test_gitlab_webhook_invalid_token(self, client):
        # POST /api/v1/cicd/webhook/gitlab
        # Gecersiz X-Gitlab-Token → 401
        ...

    def test_list_events(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        # Event listeleme endpoint'i
        ...

    def test_list_events_requires_auth(self, client):
        ...  # 401

    def test_jenkins_webhook(self, client):
        # Jenkins webhook endpoint varsa test et
        ...

    def test_webhook_stores_event(self, client, db_ready):
        # Gecerli webhook → event kayit edilir
        # NOT: Signature secret'i bilmiyorsan bu testi skip et
        ...
```

---

## DOMAIN 5: N8N (2 endpoint)
Router: backend/app/domains/n8n/router.py (100 satir)

Dosya: backend/tests/integration/test_n8n.py

```python
"""N8N entegrasyon integration testleri."""

class TestN8N:

    def test_webhook_endpoint(self, client):
        # POST /api/v1/n8n/webhook/{workflow_id}
        # Endpoint path'ini router'dan dogrula
        ...

    def test_webhook_unknown_workflow(self, client):
        # Gecersiz workflow_id → 404 veya baska status
        ...

    def test_n8n_requires_auth(self, client):
        # Auth gerektiren endpoint varsa test et
        ...
```

---

## DOMAIN 6: AI Synthetic Data (12+ endpoint)
Router: backend/app/domains/ai_synthetic_data/router.py

BU DOSYA MEVCUT MU kontrol et. Yoksa synthetic domain'deki router'i bul:
- backend/app/domains/synthetic/ altinda olabilir
- veya ai/router.py icinde synthetic endpoint'leri olabilir

Dosya: backend/tests/integration/test_synthetic.py

```python
"""Sentetik veri uretimi integration testleri."""

class TestSyntheticData:

    def test_requires_auth(self, client):
        ...  # 401

    def test_list_generators(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        ...

    def test_generate_data(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        ...

    def test_generate_with_invalid_schema(self, client, auth_headers, db_ready):
        if not db_ready: pytest.skip("DB yok")
        ...

    def test_list_generated_datasets(self, client, auth_headers, db_ready):
        ...
```

---

## TOPLAM HEDEF
- 6 domain x ortalama 5 test = minimum 30 test fonksiyonu
- Her dosya icin __init__.py mevcut (zaten var: backend/tests/integration/__init__.py)

## DOGRULAMA
```bash
cd backend && python3 -m pytest tests/integration/test_notifications.py tests/integration/test_audit.py tests/integration/test_automation.py tests/integration/test_cicd.py tests/integration/test_n8n.py tests/integration/test_synthetic.py --collect-only -q 2>&1 | tail -5
```
En az 30 test toplanmali.
```
