# Design Agent 7: Loading, Error, Empty State Tutarliligi

## Cursor'a yapistir:

```
Sen bir senior frontend UX muhendisisin. BGTS bankacilik test platformundaki
loading, error ve empty state gosterimlerini tutarli ve kullanici dostu hale
getireceksin.

## MEVCUT DURUM
- EmptyState component MEVCUT: apps/web/components/nexus/EmptyState.tsx
- Skeleton component MEVCUT: apps/web/components/ui/skeleton.tsx
- loading.tsx MEVCUT: apps/web/app/(dashboard)/loading.tsx
- error.tsx MEVCUT: apps/web/app/(dashboard)/error.tsx
- Toast component MEVCUT: apps/web/components/ui/toast.tsx
- SORUN: Her sayfa farkli pattern kullaniyor — bazi sayfalar loading gostermiyor,
  bazilari farkli empty state yapiyor, error handling tutarsiz

## YAPILACAKLAR

### 1. Standart Loading Skeleton Olustur

Sayfa bazli skeleton component'ler olustur:

#### apps/web/components/skeletons/PageSkeleton.tsx
```tsx
import { Skeleton } from "@/components/ui/skeleton";

export function PageSkeleton() {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* PageHeader skeleton */}
      <div className="flex items-center gap-3">
        <Skeleton className="h-8 w-8 rounded" />
        <Skeleton className="h-8 w-48" />
      </div>
      
      {/* StatCard row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
      
      {/* Content area */}
      <Skeleton className="h-64 rounded-lg" />
    </div>
  );
}
```

#### apps/web/components/skeletons/TableSkeleton.tsx
```tsx
import { Skeleton } from "@/components/ui/skeleton";

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 4 }: TableSkeletonProps) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex gap-4 p-3 bg-bg-subtle border-b border-border">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 p-3 border-b border-border last:border-0">
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
```

#### apps/web/components/skeletons/FormSkeleton.tsx
```tsx
import { Skeleton } from "@/components/ui/skeleton";

export function FormSkeleton({ fields = 4 }: { fields?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-full rounded" />
        </div>
      ))}
      <Skeleton className="h-10 w-32 rounded" />
    </div>
  );
}
```

#### apps/web/components/skeletons/index.ts
```ts
export { PageSkeleton } from "./PageSkeleton";
export { TableSkeleton } from "./TableSkeleton";
export { FormSkeleton } from "./FormSkeleton";
```

### 2. Standart Error State Component

#### apps/web/components/nexus/ErrorState.tsx
```tsx
"use client";

import { memo } from "react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState = memo(function ErrorState({
  title = "Bir hata oluştu",
  message = "İşlem sırasında beklenmeyen bir hata meydana geldi. Lütfen tekrar deneyin.",
  onRetry,
  className = "",
}: ErrorStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-16 text-center ${className}`}>
      <div className="w-16 h-16 rounded-full bg-danger-subtle flex items-center justify-center mb-4">
        <span className="text-2xl" aria-hidden="true">⚠️</span>
      </div>
      <h3 className="text-lg font-semibold text-fg mb-2">{title}</h3>
      <p className="text-sm text-muted max-w-md mb-6">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-accent text-accent-fg rounded hover:opacity-90 transition-opacity text-sm font-medium"
        >
          Tekrar Dene
        </button>
      )}
    </div>
  );
});
```

### 3. Tum Sayfalara Tutarli Pattern Uygula

Her useQuery kullanan sayfada su pattern olmali:

```tsx
const { data, isLoading, isError, error, refetch } = useQuery({...});

if (isLoading) return <TableSkeleton />;  // veya PageSkeleton
if (isError) return <ErrorState message={error.message} onRetry={refetch} />;
if (!data || data.length === 0) return <EmptyState title="..." description="..." />;

// Normal icerik
return <div>...</div>;
```

Su sayfalari kontrol et ve eksikleri tamamla:
1. apps/web/app/(dashboard)/p/[projectId]/scenarios/page.tsx
2. apps/web/app/(dashboard)/p/[projectId]/test-cases/page.tsx
3. apps/web/app/(dashboard)/p/[projectId]/executions/page.tsx
4. apps/web/app/(dashboard)/p/[projectId]/requirements/page.tsx
5. apps/web/app/(dashboard)/p/[projectId]/api-testing/page.tsx
6. apps/web/app/(dashboard)/p/[projectId]/locators/page.tsx
7. apps/web/app/(dashboard)/p/[projectId]/coverage/page.tsx
8. apps/web/app/(dashboard)/p/[projectId]/reports/page.tsx

Her sayfayi OKU, su kontrolleri yap:
- ✅ Loading state var mi? (isLoading → Skeleton)
- ✅ Error state var mi? (isError → ErrorState)
- ✅ Empty state var mi? (veri bos → EmptyState)
- Eksik olanlari ekle

### 4. Inline Error Mesajlarini Toast'a Tasi

Bazi sayfalarda inline hata gosterimi var — bunlari tutarli yap:

```tsx
// ONCE (inline):
{error && <div className="text-red-500">{error}</div>}

// SONRA (toast):
import { useToast } from "@/components/ui/toast";

const { toast } = useToast();

// mutation.onError icinde:
onError: (err) => {
  toast({ title: "Hata", description: err.message, variant: "destructive" });
}
```

### 5. Transition Animasyonlari Ekle

Sayfa gecislerinde ve icerik yuklenirken animasyon:

```tsx
// Icerik yuklendikten sonra fade-in:
<div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
  {/* icerik */}
</div>

// Skeleton'dan iceriye gecis:
{isLoading ? (
  <TableSkeleton />
) : (
  <div className="animate-in fade-in duration-200">
    <DataGrid data={data} />
  </div>
)}
```

Tailwind animate-in class'i icin tailwindcss-animate eklentisi gerekebilir.
Mevcut mu kontrol et: `npm list tailwindcss-animate`
Yoksa: `npm install tailwindcss-animate` ve tailwind.config.ts'e plugin olarak ekle.

## KURALLAR
- Mevcut EmptyState component'ini kullan, yeni olusturma
- Her sayfanin loading/error/empty state'i OLMALI
- Design token'lar kullan (bg-danger-subtle, text-muted, vb.)
- Skeleton boyutlari gercek icerigin boyutlarina yakin olmali (CLS onleme)
- Toast mesajlari Turkce olmali

## DOGRULAMA
```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -10
# Gorsel kontrol:
# npm run dev → sayfalar arasi gezin, loading state'leri kontrol et
```
```
