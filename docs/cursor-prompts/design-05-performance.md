# Design Agent 5: Performans Optimizasyonu

## Cursor'a yapistir:

```
Sen bir senior frontend performans muhendisisin. BGTS bankacilik test
platformunun React rendering performansini optimize edeceksin.

## MEVCUT DURUM
- 4 adet React.memo (cok az)
- 139 adet useMemo/useCallback (makul ama yetersiz)
- 83 sayfa "use client" (cok fazla — bazi server component olabilir)
- 0 adet next/image kullanimi
- 5 sayfa 1000+ satir (buyuk bundle)

## YAPILACAKLAR

### 1. Sik Render Edilen Component'lere React.memo Ekle

Bu component'ler her parent render'da yeniden render oluyor:

#### apps/web/components/nexus/StatusBadge.tsx
```tsx
// ONCE:
export function StatusBadge({ status, label, dot, size }: StatusBadgeProps) { ... }

// SONRA:
import { memo } from "react";

export const StatusBadge = memo(function StatusBadge({ status, label, dot = true, size = "xs" }: StatusBadgeProps) {
  // ... ayni icerik
});
```

#### Ayni sekilde memo ekle:
- `apps/web/components/nexus/PageHeader.tsx` — her sayfada 1 kez render, props nadiren degisir
- `apps/web/components/nexus/SectionCard.tsx` — listeler icinde cok kullaniliyor
- `apps/web/components/nexus/StatCard.tsx` — dashboard'larda grid icinde
- `apps/web/components/nexus/EmptyState.tsx` — props sabit
- `apps/web/components/nexus/FilterBar.tsx` — her filtreleme'de tum sayfa render olabilir
- `apps/web/components/ui/badge.tsx` — tablolarda satir basina render
- `apps/web/components/ui/skeleton.tsx` — loading state'lerde cok kullaniliyor

### 2. Buyuk Listelerde useCallback Ekle

Tablo/liste sayfalarinda event handler'lar her render'da yeniden olusturuluyor.

ONCE su sayfalari oku ve inline fonksiyonlari bul:
- apps/web/app/(dashboard)/p/[projectId]/scenarios/page.tsx
- apps/web/app/(dashboard)/p/[projectId]/test-cases/page.tsx
- apps/web/app/(dashboard)/p/[projectId]/executions/page.tsx

Pattern:
```tsx
// ONCE (her render'da yeni fonksiyon):
<button onClick={() => deleteScenario(id)}>Sil</button>

// SONRA:
const handleDelete = useCallback((id: string) => {
  deleteScenario(id);
}, [deleteScenario]);

// veya list item icinde:
<button onClick={() => handleDelete(id)}>Sil</button>
```

### 3. useMemo ile Pahali Hesaplamalari Cache'le

Filtreleme, sıralama ve gruplama islemleri icin useMemo kullan:

```tsx
// ONCE:
const filteredItems = items.filter(i => i.status === activeFilter);
const groupedItems = groupBy(filteredItems, 'category');

// SONRA:
const filteredItems = useMemo(
  () => items.filter(i => i.status === activeFilter),
  [items, activeFilter]
);
const groupedItems = useMemo(
  () => groupBy(filteredItems, 'category'),
  [filteredItems]
);
```

Su dosyalarda filtreleme/siralama var mi kontrol et:
- Scenarios page
- Test cases page
- Executions page
- Locators page
- Coverage page

### 4. next/image Kullan

Projede img tag varsa next/image ile degistir:

```tsx
// ONCE:
<img src="/logo.png" width={120} height={40} />

// SONRA:
import Image from "next/image";
<Image src="/logo.png" width={120} height={40} alt="BGTS Logo" />
```

Dosyalari tara:
```bash
grep -rn "<img " apps/web/components/ apps/web/app/ --include="*.tsx"
```
Her birini next/image ile degistir. Alt text eklemeyi unutma.

### 5. Lazy Loading ile Buyuk Component'leri Bol

Tab icerikleri icin dynamic import kullan:

```tsx
// apps/web/app/(dashboard)/p/[projectId]/locators/page.tsx
import dynamic from "next/dynamic";

const StabilityTab = dynamic(() => import("./_components/StabilityAnalysisTab"), {
  loading: () => <Skeleton className="h-64" />,
});
const POMTab = dynamic(() => import("./_components/POMGeneratorTab"), {
  loading: () => <Skeleton className="h-64" />,
});

// Kullanim:
{activeTab === 1 && <StabilityTab />}
{activeTab === 3 && <POMTab />}
```

Sadece AKTIF OLMAYAN tab'lar icin lazy loading yap.
Ilk tab (varsayilan gorunen) normal import olmali.

### 6. Server Component Firsatlari

Bu sayfalar "use client" OLMADAN calisabilir (sadece statik icerik):
- apps/web/app/info/ altindaki sayfalar (bilgi sayfalari)
- apps/web/app/(dashboard)/loading.tsx (zaten server component olabilir)

Kontrol et: hooks (useState, useEffect, useCallback, vb.) kullanmayan sayfalarda
"use client" GEREKSIZ — kaldir.

DIKKAT: useQuery, useRouter, usePathname kullanan sayfalardan "use client" KALDIRMA.

## KURALLAR
- React.memo EKLEYİNCE component islevselligini DEGISTIRME
- memo sardiktan sonra prop degisikliklerini kontrol et (obje/array prop varsa dikkat)
- useCallback'te dependency array'i DOGRU yaz
- useMemo'da gereksiz yerde KULLANMA (basit islemler icin overhead yaratir)
- Sadece expensive computation ve sik render edilen component'ler icin optimize et

## DOGRULAMA
```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -10
# Performans kontrolu:
# React DevTools → Profiler → record interaction → highlight updates
```
```
