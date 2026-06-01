# Neurex Management - Tüm Eksikler ve Kararlar

Tarih: 2026-05-24

## Amaç

Bu doküman `Neurex Management` için bugüne kadar çıkarılan bütün ürün, mimari, veri, entegrasyon ve geliştirme eksiklerini tek yerde toplar. Geliştirmeye başlamadan önce ana referans dokümanı budur.

## Nihai Ürün Tanımı

`Neurex Management`, Neurex ürün ailesinde manuel QA operasyonunu yöneten üründür.

Ana sorumlulukları:

- manuel test case havuzu
- test suite/folder yapısı
- test plan/cycle/run yönetimi
- tester atama
- adım bazlı expected/actual result
- evidence saklama
- defect linkleme
- requirement coverage
- import/export
- audit ve raporlama

Ana sınır:

```text
TSPM               = senaryo tasarımı, AI üretim, approval, flow, automation-oriented süreç
Neurex Management = manuel test repository, manuel run, evidence, tester workload, manual QA raporları
```

## Eksiklerin Genel Özeti

| Kategori | Durum | Öncelik |
|----------|-------|---------|
| Ürün registry | Tamamlandı | Kapalı |
| Product landing | Tamamlandı | Kapalı |
| Design token / demo data | Tamamlandı | Kapalı |
| Doküman ve veri akışı | Tamamlandı | Kapalı |
| Proje içi frontend route'ları | Eksik | P0 |
| Backend domain | Eksik | P0 |
| Database migration | Eksik | P0 |
| Router registry bağlantısı | Eksik | P0 |
| RBAC permission | Eksik | P0 |
| Import/export uygulaması | Eksik | P1 |
| Evidence storage bağlantısı | Eksik | P1 |
| Requirement/defect entegrasyonları | Eksik | P1 |
| Reporting engine | Eksik | P1 |
| Audit policy | Eksik | P1 |
| Notifications | Eksik | P2 |
| AI test generation | Eksik | P2 |
| Exploratory testing | Eksik | P2 |
| Automation result mapping | Eksik | P2 |
| Enterprise governance | Eksik | P3 |

## P0 - Geliştirme Başlamadan Önce Kapanması Gerekenler

### 1. Backend Domain Yok

Eksik:

```text
backend/app/domains/test_management/
```

Karar:

Bu domain ayrı kurulacak. TSPM içine gömülmeyecek.

Gerekli dosyalar:

```text
backend/app/domains/test_management/__init__.py
backend/app/domains/test_management/models.py
backend/app/domains/test_management/schemas.py
backend/app/domains/test_management/router.py
backend/app/domains/test_management/service.py
backend/app/domains/test_management/repository.py
backend/app/domains/test_management/import_export.py
backend/app/domains/test_management/reporting.py
backend/app/domains/test_management/audit.py
backend/app/domains/test_management/permissions.py
```

### 2. Database Migration Yok

Eksik tablolar:

```text
test_management_projects
test_suites
test_folders
test_cases
test_case_steps
test_case_versions
test_plans
test_cycles
test_runs
test_run_cases
test_run_step_results
execution_evidence
requirement_links
defect_links
test_import_jobs
test_import_job_rows
test_management_audit_events
```

Karar:

İlk migration repository + run + evidence + import + audit temelini birlikte kuracak. Otomasyon mapping ve exploratory tabloları Faz 2'ye kalacak.

### 3. Router Registry Bağlantısı Yok

Eksik:

`backend/app/core/router_registry.py` içine `test_management_router` eklenmedi.

Karar:

Router kendi prefix'ini `/test-management` olarak taşıyacak. Registry `/api/v1` ekleyecek.

Beklenen:

```python
from app.domains.test_management.router import router as test_management_router

_PREFIXED_ROUTERS = [
    ...
    test_management_router,
]
```

### 4. Frontend Project Route Ağacı Yok

Eksik:

Route katalogu var ama gerçek sayfalar yok.

Gerekli route'lar:

```text
apps/web/app/(dashboard)/p/[projectId]/management/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/repository/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/cases/[caseId]/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/cases/new/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/plans/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/runs/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/runs/[runId]/execute/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/requirements/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/defects/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/reports/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/import-export/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/settings/page.tsx
```

### 5. RBAC İzinleri Eksik

Eksik:

`test_management.*` izinleri yok.

MVP için karar:

İlk sürümde fazla parçalamadan şu izinler kullanılacak:

```text
test_management.read
test_management.write
test_management.execute
test_management.admin
```

Faz 2'de genişletilecek:

```text
test_management.assign
test_management.import
test_management.export
test_management.report
test_management.audit
```

## P1 - MVP Kalitesini Belirleyen Eksikler

### 6. TSPM ve Management Veri Çakışması Riski

Sorun:

TSPM'de scenario, requirement, execution kavramları var. Management da test case, requirement link ve run tutacak.

Karar:

- TSPM scenario tasarımı tutar.
- Management manuel test case ve manuel execution tutar.
- TSPM scenario, Management case'e kaynak olabilir ama ana kayıt olmaz.
- Ortak veri gerekiyorsa `source_ref` veya explicit link kullanılır.

Önerilen alan:

```text
test_cases.source_type = manual | tspm | import | ai
test_cases.source_ref = external id veya tspm scenario id
```

### 7. Requirement Referans mı Kopya mı?

Sorun:

Jira/Azure/TSPM requirement'ı tamamen kopyalanırsa güncellik bozulur; sadece key tutulursa rapor zayıflar.

Karar:

Snapshot + referans birlikte tutulur.

Minimum alanlar:

```text
external_source
external_key
title_snapshot
url
source_updated_at
linked_case_id
coverage_status
```

### 8. Test Case Version Snapshot Büyümesi

Sorun:

Her değişiklikte JSON snapshot tutmak doğru ama tablo büyür.

Karar:

MVP'de snapshot tutulur. Ek alanlar şimdiden bırakılır:

```text
change_summary
changed_fields
snapshot_size_bytes
```

Retention/compaction Faz 2.

### 9. Run Başladıktan Sonra Case Değişirse

Sorun:

Tester eski versiyonu koşarken repository güncel versiyona geçebilir.

Karar:

`test_run_cases.case_version_no` zorunlu. Run execute ekranında versiyon farkı gösterilir:

```text
Bu koşum TC-123 v4 ile çalışıyor. Repository current version: v5.
```

### 10. Evidence Storage Büyümesi

Sorun:

Screenshot, log, video ve doküman dosyaları hızla büyür.

Karar:

Evidence `artifacts` domain'e bağlanır. Management sadece ilişkiyi tutar.

MVP retention default:

```text
screenshot: 180 gün
log: 90 gün
video: 30 gün
document: 365 gün
critical failed evidence: 365 gün
```

Retention override Settings içinde tutulur.

### 11. Import Duplicate ve Conflict

Sorun:

Excel import en karmaşık akışlardan biri. Aynı test farklı title ile, aynı title farklı step ile gelebilir.

Karar:

MVP otomatik merge yapmaz.

Import row status:

```text
new
duplicate_candidate
conflict
invalid
ready
committed
skipped
```

Commit öncesi conflict çözümü zorunlu.

### 12. Status Aggregation

Sorun:

Step result'lardan case/run status hesaplama ekipten ekibe değişebilir.

MVP default:

```text
if any step failed       => run_case.status = failed
else if any step blocked => run_case.status = blocked
else if all required passed => run_case.status = passed
else if all skipped      => run_case.status = skipped
else                     => run_case.status = in_progress
```

Karar:

MVP'de sabit. Faz 2'de configurable aggregation policy.

### 13. Defect Sync Karmaşıklığı

Sorun:

Jira bug kapandı diye run case otomatik retest'e mi düşecek? Bu net değil.

Karar:

MVP'de defect sadece link + status snapshot.

Faz 2:

- two-way sync
- bug closed -> retest suggestion
- bug reopened -> affected run warning

### 14. Custom Fields Governance

Sorun:

Sınırsız JSON custom field raporlamayı bozar.

Karar:

MVP'de `custom_fields jsonb` var ama Settings içinde field schema taslağı tutulur.

Minimum schema:

```text
field_key
label
type
required
allowed_values
applies_to
```

### 15. Latest Run Result Performansı

Sorun:

Repository listesinde binlerce case için son run sonucu join ile pahalılaşır.

Karar:

`test_cases` üzerinde denormalized alanlar tutulabilir:

```text
last_run_status
last_run_at
last_failed_at
last_run_id
```

Bu alanlar run case final status değiştiğinde güncellenir.

### 16. Audit Event Kapsamı

Sorun:

Her step update audit'e yazılırsa audit tablosu büyür; hiç yazılmazsa compliance zayıflar.

Karar:

Audit'e yazılacaklar:

- project/suite/folder/case create/update/archive
- version created
- plan/run created
- run case final status changed
- evidence uploaded/deleted
- defect linked/unlinked
- import committed
- export generated

Audit'e yazılmayacaklar:

- her step partial update
- UI filter/search
- dashboard read

## P2 - Rekabetçi Ürün Olmak İçin Eksikler

### 17. Exploratory Testing Yok

Rakipler:

- Testmo
- qTest Explorer
- Azure Test & Feedback

Eksik:

Plansız keşif testi için session, timebox, not, evidence ve defect akışı yok.

Faz 2 tablolar:

```text
exploratory_sessions
exploratory_notes
exploratory_evidence
```

### 18. AI Test Case Generation Yok

Rakipler:

- BrowserStack
- qTest
- Kualitee
- aqua
- TestCollab

Eksik:

Requirement/story/screenshot'tan test case üretimi yok.

Faz 2:

- AI test case draft
- duplicate detection
- coverage gap önerisi
- user approval before save

### 19. Jira/Azure Two-Way Sync Yok

Rakipler:

- Xray
- Zephyr
- TestRail
- BrowserStack

Eksik:

Issue create/update/status sync yok.

Faz 2:

- Jira issue create
- Azure work item create
- status sync
- requirement sync
- defect retest suggestion

### 20. Automation Result Mapping Yok

Rakipler:

- Xray
- Qase
- Testmo

Eksik:

JUnit XML, Playwright, Cypress, Selenium result import yok.

Faz 2:

```text
automation_result_imports
automation_case_mappings
automation_run_results
```

### 21. Release GO/NO-GO Karar Motoru Zayıf

Eksik:

Rapor adı var ama threshold ve karar modeli yok.

Faz 2:

```text
release_readiness_rules
release_readiness_snapshots
```

Karar parametreleri:

- critical fail count
- blocked count
- progress threshold
- coverage threshold
- open critical defect threshold

### 22. Test Data Binding Zayıf

Eksik:

Neurex Data ile güçlü bağ henüz yok.

Faz 2:

- dataset binding
- masked data reference
- run-time data snapshot
- data freshness warning

## P3 - Enterprise Seviyesi Eksikler

### 23. Baseline / Freeze

Eksik:

Release veya audit için frozen baseline yok.

Faz 3:

```text
test_baselines
test_baseline_items
```

### 24. Signed Execution Evidence

Eksik:

Evidence hash/signature yok.

Faz 3:

- artifact hash
- signed execution pack
- immutable evidence mode

### 25. Advanced Retention Policy

Eksik:

Tenant/proje bazlı retention UI yok.

Faz 3:

- retention by file type
- legal hold
- archive to cold storage

### 26. Advanced Analytics

Eksik:

Trend, flaky manual test, tester throughput, defect leakage gibi metrikler yok.

Faz 3:

- manual flaky signal
- module risk trend
- tester throughput
- defect leakage
- test aging

## Geliştirmede İzlenecek Nihai Sıra

### Sprint 1 - Runtime Skeleton

1. Backend `test_management` domain klasörü.
2. Router skeleton.
3. Router registry bağlantısı.
4. Frontend `/management/*` route ağacı.
5. Mock dashboard/repository/run ekranları.
6. Smoke tests.

### Sprint 2 - Repository Persistence

1. Alembic migration: project/suite/folder/case/step/version.
2. Case CRUD.
3. Repository list/filter/search.
4. Version snapshot.
5. Archive/deprecate.

### Sprint 3 - Plan ve Run

1. Plan/cycle/run tabloları.
2. Run case assignment.
3. Tester execute ekranı.
4. Step result kayıt.
5. Run aggregation.

### Sprint 4 - Evidence, Defect, Requirement

1. Evidence upload + artifacts link.
2. Defect link.
3. Requirement link.
4. Coverage matrix.
5. Basic reports.

### Sprint 5 - Import/Export ve Audit

1. Import job/staging.
2. Conflict preview.
3. Commit.
4. Export.
5. Audit events.
6. RBAC enforcement.

### Sprint 6 - Rekabetçi Faz 2 Başlangıcı

1. Exploratory sessions.
2. AI test case draft.
3. Jira/Azure sync.
4. Automation result mapping.
5. Release GO/NO-GO.

## Geliştirmeye Başlamadan Önce Son Kabul

Geliştirmeye başlamaya hazırız çünkü şu kararlar net:

- Ürün adı: `Neurex Management`
- Ana frontend route: `/p/[projectId]/management`
- Backend prefix: `/api/v1/test-management`
- Ana domain: `backend/app/domains/test_management`
- Ana veri: manuel test case, step, version, plan, run, result, evidence, defect, requirement
- Ana kullanıcılar: QA Lead, Manual Tester, Developer Viewer, Product Viewer, Auditor, Admin
- MVP sınırı: manuel QA operasyonu
- Faz 2 sınırı: AI, exploratory, two-way sync, automation result mapping

## Sonuç

Toplanan eksikler artık ikiye ayrılmış durumda:

1. **Geliştirmeye başlamak için zorunlu eksikler:** backend domain, DB migration, route sayfaları, RBAC, router registry.
2. **Ürünü rakiplerle yarıştıracak eksikler:** exploratory testing, AI generation, Jira/Azure sync, automation mapping, release readiness.

Bu dokümandaki P0 maddeleri tamamlanmadan gerçek geliştirme stabil ilerlemez. P0 tamamlandıktan sonra ürün kullanılabilir MVP olur; P1 ve P2 ile rekabetçi test management ürünü seviyesine çıkar.
