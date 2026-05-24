# BGTS Test Dönüşüm — RBAC Yetkilendirme Test Matrisi

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kaynak:** `backend/app/domains/auth/permissions.py`

---

## 1. Rol-İzin Tanımları

| Rol | İzinler |
|-----|---------|
| **admin** | `project.create`, `project.read`, `project.update`, `project.delete`, `scenario.create`, `scenario.read`, `scenario.update`, `scenario.delete`, `approval.decide`, `execution.create`, `execution.update`, `import.create`, `flow.manage`, `requirement.manage`, `schedule.manage`, `integration.manage`, `api_test.manage`, `test_data.manage`, `admin.*` |
| **operator** | `project.create`, `project.read`, `project.update`, `scenario.create`, `scenario.read`, `scenario.update`, `scenario.delete`, `approval.decide`, `execution.create`, `execution.update`, `import.create`, `flow.manage`, `requirement.manage`, `schedule.manage`, `integration.manage`, `api_test.manage`, `test_data.manage` |
| **viewer** | `project.read`, `scenario.read` |

---

## 2. Endpoint × Rol Erişim Matrisi

### Proje İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `/tspm/projects` | GET | `project.read` | ✅ | ✅ | ✅ |
| `/tspm/projects` | POST | `project.create` | ✅ | ✅ | ❌ |
| `/tspm/projects/{id}/dashboard` | GET | `project.read` | ✅ | ✅ | ✅ |

### Senaryo İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../scenarios` | GET | `scenario.read` | ✅ | ✅ | ✅ |
| `.../scenarios` | POST | `scenario.create` | ✅ | ✅ | ❌ |
| `.../scenarios/{id}` | GET | `scenario.read` | ✅ | ✅ | ✅ |
| `.../scenarios/{id}` | PUT | `scenario.update` | ✅ | ✅ | ❌ |
| `.../scenarios/bulk-delete` | POST | `scenario.delete` | ✅ | ✅ | ❌ |
| `.../scenarios/generate-bdd` | POST | `scenario.create` | ✅ | ✅ | ❌ |
| `.../scenarios/save-bdd` | POST | `scenario.create` | ✅ | ✅ | ❌ |

### Onay İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../approvals` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../approvals/{id}/decide` | POST | `approval.decide` | ✅ | ✅ | ❌ |

### Koşu İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../executions` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../executions` | POST | `execution.create` | ✅ | ✅ | ❌ |
| `.../executions/{id}` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../executions/{id}` | POST (re-run) | `execution.create` | ✅ | ✅ | ❌ |
| `.../results/{id}` | PATCH | `execution.update` | ✅ | ✅ | ❌ |
| `.../execution-trends` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../execution-stats` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../flaky-tests` | GET | `project.read` | ✅ | ✅ | ✅ |

### Akış İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../flows` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../flows` | POST | `flow.manage` | ✅ | ✅ | ❌ |
| `.../flows/{id}` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../flows/{id}/graph` | PUT | `flow.manage` | ✅ | ✅ | ❌ |

### Regresyon Set İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../regression-sets` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../regression-sets` | POST | `scenario.create` | ✅ | ✅ | ❌ |
| `.../regression-sets/{id}` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../regression-sets/{id}/add` | POST | `scenario.update` | ✅ | ✅ | ❌ |
| `.../regression-sets/suggest` | POST | `scenario.read` | ✅ | ✅ | ✅ |
| `.../regression-sets/accept-suggestions` | POST | `scenario.create` | ✅ | ✅ | ❌ |

### Gereksinim İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../requirements` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../requirements` | POST | `requirement.manage` | ✅ | ✅ | ❌ |
| `.../requirements/{id}` | PUT | `requirement.manage` | ✅ | ✅ | ❌ |
| `.../requirements/{id}` | DELETE | `requirement.manage` | ✅ | ✅ | ❌ |
| `.../coverage-matrix` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../coverage-gaps` | GET | `project.read` | ✅ | ✅ | ✅ |

### Zamanlama İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../schedules` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../schedules` | POST | `schedule.manage` | ✅ | ✅ | ❌ |
| `.../schedules/{id}` | PUT | `schedule.manage` | ✅ | ✅ | ❌ |
| `.../schedules/{id}` | DELETE | `schedule.manage` | ✅ | ✅ | ❌ |
| `.../schedules/{id}/trigger` | POST | `schedule.manage` | ✅ | ✅ | ❌ |

### Test Verisi İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../test-data` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../test-data` | POST | `test_data.manage` | ✅ | ✅ | ❌ |
| `.../test-data/{id}` | PUT | `test_data.manage` | ✅ | ✅ | ❌ |
| `.../test-data/{id}` | DELETE | `test_data.manage` | ✅ | ✅ | ❌ |

### Entegrasyon İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../integrations` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../integrations` | POST | `integration.manage` | ✅ | ✅ | ❌ |
| `.../integrations/{id}` | PUT | `integration.manage` | ✅ | ✅ | ❌ |
| `.../integrations/{id}` | DELETE | `integration.manage` | ✅ | ✅ | ❌ |
| `.../integrations/{id}/sync` | POST | `integration.manage` | ✅ | ✅ | ❌ |

### API Test İşlemleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../api-tests/collections` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../api-tests/collections` | POST | `api_test.manage` | ✅ | ✅ | ❌ |
| `.../api-tests/collections/{id}` | DELETE | `api_test.manage` | ✅ | ✅ | ❌ |
| `.../api-tests/.../requests` | POST | `api_test.manage` | ✅ | ✅ | ❌ |
| `.../api-tests/.../run` | POST | `api_test.manage` | ✅ | ✅ | ❌ |

### Proje Üyeleri

| Endpoint | Metod | Gerekli İzin | admin | operator | viewer |
|----------|-------|-------------|-------|----------|--------|
| `.../members` | GET | `project.read` | ✅ | ✅ | ✅ |
| `.../members` | POST | `project.update` | ✅ | ✅ | ❌ |
| `.../members/{id}` | DELETE | `project.update` | ✅ | ✅ | ❌ |

---

## 3. Önemli Bulgular ve Riskler

| # | Bulgu | Risk | Öneri |
|---|-------|------|-------|
| 1 | Router'da `get_current_user` dependency var ama izin kontrolü yok | **YÜKSEK** | Her endpoint'e `require_permission()` dependency ekle |
| 2 | Proje sahipliği kontrolü yok; herkes her projeye erişebilir | **YÜKSEK** | Project member tablosu üzerinden erişim kontrolü |
| 3 | `viewer` rolünün yazma endpoint'lerine erişimi bloklanmıyor | **YÜKSEK** | Middleware seviyesinde rol bazlı kontrol |
| 4 | `project.delete` izni tanımlı ama DELETE endpoint yok | DÜŞÜK | Proje silme endpoint'i eklenebilir |

---

## 4. RBAC Test Senaryoları (Detay)

### Yüksek Öncelikli Test Senaryoları

| ID | Başlık | Rol | Endpoint | Beklenen |
|----|--------|-----|----------|----------|
| RBAC-01 | Viewer senaryo oluşturamaz | viewer | POST .../scenarios | 403 |
| RBAC-02 | Viewer senaryo silemez | viewer | POST .../bulk-delete | 403 |
| RBAC-03 | Viewer onay veremez | viewer | POST .../decide | 403 |
| RBAC-04 | Viewer koşu oluşturamaz | viewer | POST .../executions | 403 |
| RBAC-05 | Viewer akış oluşturamaz | viewer | POST .../flows | 403 |
| RBAC-06 | Viewer zamanlama oluşturamaz | viewer | POST .../schedules | 403 |
| RBAC-07 | Viewer proje oluşturamaz | viewer | POST /tspm/projects | 403 |
| RBAC-08 | Viewer senaryo okuyabilir | viewer | GET .../scenarios | 200 |
| RBAC-09 | Viewer proje listesi okuyabilir | viewer | GET /tspm/projects | 200 |
| RBAC-10 | Operator proje silemez | operator | DELETE /tspm/projects/{id} | 403 |
| RBAC-11 | Operator tüm CRUD yapabilir | operator | POST/PUT/DELETE (çeşitli) | 200/201/204 |
| RBAC-12 | Admin her şeyi yapabilir | admin | Tüm endpoint'ler | Başarılı |

**Toplam RBAC Test Senaryosu: 60+ endpoint × 3 rol = 180+ kombinasyon**
