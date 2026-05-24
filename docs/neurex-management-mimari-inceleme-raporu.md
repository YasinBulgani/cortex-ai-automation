# Neurex Management Mimari İnceleme Raporu

Tarih: 2026-05-24

## Kapsam

Bu inceleme `Neurex Management` alanının mevcut monorepo mimarisine gerçekten bağlanıp bağlanmadığını kontrol eder:

- ürün registry ve product package
- global ürün kimliği ve design token eşleşmesi
- proje içi route varlığı
- backend domain ve router kaydı
- database migration ve model varlığı
- RBAC/permission uyumu
- test ve dokümantasyon tutarlılığı

## Durum Özeti

| Katman | Durum | Not |
|--------|-------|-----|
| Ürün package | Tamamlandı | `packages/product-management` eklendi. |
| Product registry | Tamamlandı | `apps/web/lib/product.ts` registry compose zincirine bağlandı. |
| Product family type | Tamamlandı | `management` product-kit `ProductFamilyId` içine eklendi. |
| Route katalogu | Kısmi | Route key'leri var; gerçek `/p/[projectId]/management/*` sayfaları yok. |
| Landing page | Tamamlandı | `ManagementProductPage.tsx` eklendi. |
| Design token | Tamamlandı | Web ve design-system product meta güncellendi. |
| Demo telemetry | Tamamlandı | `management` demo verisi eklendi. |
| Frontend test beklentileri | Tamamlandı | Product/design-token testleri 9 ürüne güncellendi. |
| Backend domain | Eksik | `backend/app/domains/test_management` yok. |
| Router registry | Eksik | `test_management_router` import/include yok. |
| DB migration | Eksik | Manuel test tabloları için Alembic migration yok. |
| RBAC | Eksik | `test_management.*` izinleri ve rol eşlemeleri yok. |
| Import/export servisleri | Eksik | Mapping, staging, rollback ve export servisleri yok. |
| Evidence storage bağlantısı | Eksik | `artifacts` domain ile execution evidence ilişkisi kodda yok. |

## Mimari Bulgular

### 1. Ürün Kayıt Katmanı Sağlam

`Neurex Management` artık ürün ailesinin gerçek bir üyesi:

- `packages/product-management/src/index.ts`
- `packages/product-kit/src/types.ts`
- `packages/product-kit/src/routes.ts`
- `apps/web/lib/product.ts`
- `apps/web/lib/products/brand.ts`
- `apps/web/lib/products/demo-data.ts`

Bu katmanda kalan kritik boşluk yok.

### 2. Project Route Ağacı Eksik

Route katalogu aşağıdaki path'leri üretiyor:

- `management`
- `management/repository`
- `management/plans`
- `management/runs`
- `management/requirements`
- `management/defects`
- `management/reports`
- `management/import-export`
- `management/settings`

Ancak `apps/web/app/(dashboard)/p/[projectId]/management/` altında gerçek sayfalar yok. Kullanıcı proje içinden Management menüsüne girdiğinde 404 riski var.

Gerekli ilk dosyalar:

```text
apps/web/app/(dashboard)/p/[projectId]/management/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/repository/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/plans/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/runs/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/requirements/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/defects/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/reports/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/import-export/page.tsx
apps/web/app/(dashboard)/p/[projectId]/management/settings/page.tsx
```

### 3. Backend Domain Henüz Yok

Planlanan domain:

```text
backend/app/domains/test_management/
```

Mevcut kodda bu domain yok. Bu nedenle `/api/v1/test-management/*` prefix'i mimari dokümanda var ama runtime'da yok.

Gerekli ilk dosyalar:

```text
backend/app/domains/test_management/__init__.py
backend/app/domains/test_management/models.py
backend/app/domains/test_management/schemas.py
backend/app/domains/test_management/router.py
backend/app/domains/test_management/service.py
backend/app/domains/test_management/repository.py
backend/app/domains/test_management/import_export.py
backend/app/domains/test_management/reporting.py
backend/app/domains/test_management/permissions.py
```

### 4. Router Registry Bağlantısı Eksik

`backend/app/core/router_registry.py` içinde `test_management_router` import/include yok.

Beklenen bağlantı:

```python
from app.domains.test_management.router import router as test_management_router

_PREFIXED_ROUTERS = [
    ...
    test_management_router,
]
```

Router kendi prefix'ini `/test-management` olarak taşımalı; registry de diğer domainler gibi `/api/v1` eklemeli.

### 5. Database Migration Eksik

Henüz şu tablolar için migration yok:

- `test_management_projects`
- `test_suites`
- `test_folders`
- `test_cases`
- `test_case_steps`
- `test_case_versions`
- `test_case_attachments`
- `test_plans`
- `test_cycles`
- `test_runs`
- `test_run_cases`
- `test_run_step_results`
- `execution_evidence`
- `requirement_links`
- `defect_links`
- `test_import_jobs`

İlk migration, manuel test hafızasını ve koşum geçmişini kayıpsız saklayacak minimum tablo setini kurmalı.

### 6. TSPM Sınırı Yazıldı, Kodda Bağ Yok

Mimari karar:

- `tspm`: senaryo tasarımı, AI üretim, approvals, flows, automation-oriented execution
- `test_management`: manuel test repository, plan/run, evidence, defect, manual QA reporting

Kodda henüz iki domain arasında ilişki yok. İlk uygulamada doğrudan tablo paylaşımı yerine açık servis sınırı önerilir.

### 7. RBAC Eksik

Mevcut izin modellerinde `test_management.*` izinleri yok.

Eklenmesi gereken öneri izinler:

- `test_management.read`
- `test_management.write`
- `test_management.execute`
- `test_management.assign`
- `test_management.import`
- `test_management.export`
- `test_management.report`
- `test_management.admin`
- `test_management.audit`

Rol eşlemesi:

- `qa_lead`: read/write/assign/import/export/report
- `manual_tester`: read/execute/evidence
- `auditor`: read/audit/report
- `viewer`: read/report
- `admin`: admin.*

### 8. Test Durumu

Geçen kontroller:

```text
npm run type-check --workspace @neurex/product-management
npm run type-check --workspace @neurex/product-kit
npm test --workspace apps/web -- --runTestsByPath lib/__tests__/product.test.ts lib/__tests__/design-tokens.test.ts --runInBand
```

Bilinen bağımsız type-check hataları:

```text
apps/web/app/(dashboard)/kb/[articleId]/page.tsx
apps/web/app/(dashboard)/qa/page.tsx
apps/web/lib/hooks/index.ts
packages/design-system/src/primitives/popover.test.tsx
```

Bu hatalar Management eklemesinden kaynaklanmıyor.

## Öncelikli Sonraki İş

1. `apps/web/app/(dashboard)/p/[projectId]/management/*` mock route ağacını kur.
2. `backend/app/domains/test_management` domain iskeletini ekle.
3. İlk Alembic migration ile repository + run tablolarını oluştur.
4. `router_registry.py` içine `test_management_router` bağla.
5. RBAC izinlerini auth/rbac katmanına ekle.
6. Import/export staging servisinin minimum sözleşmesini çıkar.
7. Frontend route smoke testleri ve backend router registration testleri ekle.

## Karar

Mimari incelemeye göre `Neurex Management` ürün kimliği artık doğru bağlandı. Kalan eksikler ürün tanımı değil, uygulama mimarisinin runtime parçalarıdır: gerçek proje route'ları, backend API, database migration, RBAC ve import/export servisleri.
