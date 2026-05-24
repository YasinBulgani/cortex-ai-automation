# Neurex Management - Geliştirme Öncesi Son Toparlama

Tarih: 2026-05-24

## Kısa Karar

`Neurex Management` için ana ürün fikri doğru: manuel testleri saklayan, koşturan, kanıtlayan ve raporlayan ayrı bir yönetim alanı. Mevcut plan iyi bir iskelet veriyor; geliştirmeye başlamadan önce mantıksal olarak eksik kalan birkaç alanı netleştirmek gerekiyor.

Bu doküman, geliştirme başlamadan önce kapatılması gereken son mimari ve ürün boşluklarını tek yerde toplar.

## Eksik Kalan Mantıksal Alanlar

| Alan | Neden eksik? | Karar |
|------|--------------|-------|
| Workspace/project scope | Test case ve run verisi hangi tenant/proje altında tutulacak net olmalı. | Tüm Management tabloları `tenant_id/workspace_id` ve `project_id` ile scope edilir. |
| Test case lifecycle | Draft, review, ready, deprecated var ama onay akışı net değil. | İlk sürümde basit lifecycle; Faz 2'de approval workflow. |
| Version conflict | Import veya edit sırasında aynı case'in eski/yeni sürümü çakışabilir. | Her update yeni version snapshot üretir; import conflict preview zorunlu olur. |
| Reusable test data | Test data alanı var ama ortak veri seti yönetimi ayrılmadı. | Case-level `test_data` MVP'de yeterli; reusable dataset Faz 2. |
| Evidence retention | Kanıt dosyaları büyür ve saklama politikası ister. | Evidence `artifacts` domain'e bağlanır; retention policy ayarı Management Settings'e eklenir. |
| Notification | Tester ataması, blocked test, failed critical test için bildirim yok. | İlk sürümde in-app notification eventleri tanımlanır; e-posta/Slack Faz 2. |
| Audit ve compliance | Versiyon var ama kim neyi ne zaman yaptı raporu ayrışmadı. | Audit event standardı tanımlanır: create/update/archive/execute/import/export. |
| Baseline ve release freeze | Koşulan case versiyonu sabitlenmeli. | `test_run_case.case_version_no` zorunlu; run başladıktan sonra case değişikliği run'ı etkilemez. |
| Duplicate detection | Excel import ile aynı case tekrar gelebilir. | MVP import preview duplicate uyarısı verir; otomatik merge yapmaz. |
| Bulk operations | QA Lead çoklu atama, status değiştirme, plana ekleme ister. | Repository ve run listelerinde bulk action MVP kapsamına alınır. |
| Custom fields governance | `custom_fields` var ama schema yoksa veri dağılır. | MVP'de JSON saklanır; Settings'te field schema Faz 2. |
| Global search | Manuel test sayısı artınca arama kritik olur. | Case key/title/tag/step/action/expected alanlarında ilk sürüm arama gerekir. |
| Reporting formulas | Rapor adları var ama hesap tanımları ayrıntılı değil. | MVP raporları formül bazında sabitlenir. |
| Defect state sync | Dış defect statüsü değişince run raporu etkilenir. | MVP manuel link/status; Jira/Azure sync Faz 2. |
| API pagination/filter | Büyük repository'de liste endpointleri şişer. | Tüm listelerde pagination, search, sort, filter standart olur. |
| Soft delete/archive | Test case fiziksel silinirse geçmiş koşum bozulur. | Silme yok; archive/deprecate var. |
| Data migration path | Mevcut TSPM/manual test verisi varsa aktarım yolu gerekir. | İlk migration sonrası script/adapter backlog'a alınır. |
| Permission boundaries | QA Lead ve Manual Tester ayrımı endpoint bazında yok. | Permission matrisi geliştirme öncesi kesinleşir. |
| Error taxonomy | Import/run/evidence hataları kullanıcıya anlaşılır dönmeli. | Domain error kodları `TM_*` prefix'iyle tanımlanır. |
| Observability | Run execution ve import işlemleri izlenebilir olmalı. | Import/run eventleri log + metrics üretir. |

## Netleştirilmiş Domain Sınırı

| Domain | Sahip olduğu veri | Sahip olmadığı veri |
|--------|-------------------|---------------------|
| `test_management` | Manuel test case, step, version, plan, cycle, run, run result, evidence link, defect link, manual reports | AI prompt, automation script, CI run engine |
| `tspm` | Senaryo tasarımı, approvals, AI taslakları, flows, regression planning, automation-oriented execution | Manuel execution evidence ve tester workload ana kaydı |
| `artifacts` | Dosya saklama metadata, storage path, artifact lifecycle | Test sonucu anlamı |
| `auth/rbac` | Rol ve izin | Test case içeriği |
| `integrations` veya ilgili domain | Jira/Azure/GitHub bağlantı ayarları | Run sonucu hesaplama |

## MVP İçin Minimum Veri Sözleşmesi

MVP şu kayıtları gerçekten saklamadan başlamamalı:

1. `test_management_projects`
2. `test_suites`
3. `test_folders`
4. `test_cases`
5. `test_case_steps`
6. `test_case_versions`
7. `test_plans`
8. `test_cycles`
9. `test_runs`
10. `test_run_cases`
11. `test_run_step_results`
12. `execution_evidence`
13. `requirement_links`
14. `defect_links`
15. `test_import_jobs`
16. `test_import_job_rows`
17. `test_management_audit_events`

## MVP Endpoint Grupları

Geliştirmeye başlarken endpointleri şu gruplarla açmak yeterli:

```text
/api/v1/test-management/projects
/api/v1/test-management/projects/{project_id}/repository
/api/v1/test-management/projects/{project_id}/suites
/api/v1/test-management/projects/{project_id}/folders
/api/v1/test-management/projects/{project_id}/cases
/api/v1/test-management/projects/{project_id}/cases/{case_id}/versions
/api/v1/test-management/projects/{project_id}/plans
/api/v1/test-management/projects/{project_id}/cycles
/api/v1/test-management/projects/{project_id}/runs
/api/v1/test-management/projects/{project_id}/run-cases
/api/v1/test-management/projects/{project_id}/evidence
/api/v1/test-management/projects/{project_id}/requirements
/api/v1/test-management/projects/{project_id}/defects
/api/v1/test-management/projects/{project_id}/imports
/api/v1/test-management/projects/{project_id}/exports
/api/v1/test-management/projects/{project_id}/reports
/api/v1/test-management/projects/{project_id}/settings
```

## MVP Ekran Grupları

Geliştirmeye başlarken frontend route sırası:

1. `management/page.tsx` - Dashboard
2. `management/repository/page.tsx` - Test case havuzu
3. `management/cases/[caseId]/page.tsx` - Test case detay
4. `management/cases/new/page.tsx` - Test case oluşturma
5. `management/plans/page.tsx` - Test planları
6. `management/runs/page.tsx` - Run listesi
7. `management/runs/[runId]/execute/page.tsx` - Tester yürütme ekranı
8. `management/import-export/page.tsx` - Excel/CSV import export
9. `management/reports/page.tsx` - Execution/coverage/workload raporları
10. `management/settings/page.tsx` - Status, fields, retention, permissions ayarları

## Permission Matrisi

| Permission | QA Lead | Manual Tester | Developer Viewer | Product Viewer | Auditor | Admin |
|------------|---------|---------------|------------------|----------------|---------|-------|
| `test_management.read` | Evet | Evet | Evet | Evet | Evet | Evet |
| `test_management.write` | Evet | Hayır | Hayır | Hayır | Hayır | Evet |
| `test_management.execute` | Evet | Evet | Hayır | Hayır | Hayır | Evet |
| `test_management.assign` | Evet | Hayır | Hayır | Hayır | Hayır | Evet |
| `test_management.import` | Evet | Hayır | Hayır | Hayır | Hayır | Evet |
| `test_management.export` | Evet | Hayır | Hayır | Evet | Evet | Evet |
| `test_management.report` | Evet | Sınırlı | Evet | Evet | Evet | Evet |
| `test_management.audit` | Hayır | Hayır | Hayır | Hayır | Evet | Evet |
| `test_management.admin` | Hayır | Hayır | Hayır | Hayır | Hayır | Evet |

## Rapor Formülleri

| Rapor | Minimum hesap |
|-------|---------------|
| Execution Summary | total, not_run, passed, failed, blocked, skipped, retest |
| Pass Rate | `passed / (passed + failed + blocked + skipped)` |
| Progress | `(passed + failed + blocked + skipped) / total` |
| Requirement Coverage | `covered requirements / total linked requirements` |
| Tester Workload | user bazında assigned not_run + in_progress |
| Critical Failure | failed run case where case priority/severity critical |
| Blocked Aging | blocked durumunda geçen süre |
| Release GO/NO-GO | critical fail, blocked, coverage ve progress eşiklerine göre karar |

## Import Kuralları

Excel/CSV import MVP kuralları:

- Import doğrudan repository'ye yazmaz; önce staging preview oluşturur.
- Her satır için validation sonucu tutulur.
- Aynı `case_key` varsa conflict olarak işaretlenir.
- `case_key` yoksa title + suite + folder + step signature ile duplicate adayı aranır.
- Kullanıcı conflict çözmeden commit yapamaz.
- Commit sonrası import job rollback referansı saklanır.
- Import edilen her case için initial version snapshot oluşur.

## Evidence Kuralları

- Evidence dosyası test case'e değil, run result'a bağlanır.
- Evidence step-level veya case-level olabilir.
- Dosya metadata `execution_evidence` tablosunda; storage path `artifacts` domain'de tutulur.
- Failed ve blocked sonuçlarda en az bir actual result zorunludur.
- Screenshot/log/video/document tipleri ilk sürümde desteklenir.

## Geliştirme Sırası

Geliştirmeye başlarken önerilen sıra:

1. Backend domain klasörü ve router skeleton.
2. Alembic migration: repository + run ana tabloları.
3. Pydantic schemas ve SQLAlchemy models.
4. Repository CRUD servisleri.
5. Frontend mock route ağacı.
6. Test case repository ekranı.
7. Test plan/run create akışı.
8. Run execute ekranı.
9. Evidence upload/link.
10. Import preview + commit.
11. Report endpointleri.
12. RBAC enforcement.
13. Audit events.
14. Smoke/integration testleri.

## Geliştirmeye Başlamadan Önce Hazır Sayılma Kriteri

Şu kararlar artık yeterince net:

- Ürün adı ve yeri: `Neurex Management`
- Ana route: `/p/[projectId]/management`
- Backend prefix: `/api/v1/test-management`
- Domain sınırı: manuel QA operasyonu
- TSPM sınırı: senaryo/AI/akış tasarımı
- İlk veri modeli: repository + plan/run + evidence + import
- İlk kullanıcı rolleri: QA Lead, Manual Tester, Viewer, Auditor, Admin
- İlk raporlar: execution, coverage, workload, release readiness

Sonuç: Mantıksal olarak büyük bir ürün alanı eksiği kalmadı. Bundan sonrası geliştirme işi: önce runtime skeleton, sonra kalıcı veri modeli, sonra ekranlar.
