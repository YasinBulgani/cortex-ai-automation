# Design Agent 3: Design Token Tutarliligi (208 hardcoded renk → token)

## Cursor'a yapistir:

```
Sen bir senior frontend muhendisisin. BGTS bankacilik test platformundaki
hardcoded Tailwind renk class'larini design token'lara donustureceksin.

## MEVCUT DESIGN TOKEN SISTEMI

### CSS Variables (apps/web/app/styles/tokens.css):
Light mode:
  --bg: #f8fafc           --bg-subtle: #f1f5f9
  --fg: #0f172a           --muted: #64748b        --muted-fg: #94a3b8
  --border: #e2e8f0       --border-strong: #cbd5e1
  --accent: #2563eb       --accent-fg: #ffffff     --accent-subtle: #eff6ff
  --ai: #7c3aed           --ai-fg: #ffffff         --ai-subtle: #f5f3ff
  --success: #16a34a      --success-fg: #ffffff    --success-subtle: #f0fdf4
  --warning: #d97706      --warning-fg: #ffffff    --warning-subtle: #fffbeb
  --danger: #dc2626       --danger-fg: #ffffff     --danger-subtle: #fef2f2

### Tailwind Config (tailwind.config.ts):
Tum token'lar Tailwind class'lari olarak kullanilabilir:
  bg-bg, bg-bg-subtle, text-fg, text-muted, text-muted-fg,
  border-border, border-border-strong,
  bg-accent, text-accent-fg, bg-accent-subtle,
  bg-ai, text-ai-fg, bg-ai-subtle,
  bg-success, text-success-fg, bg-success-subtle,
  bg-warning, text-warning-fg, bg-warning-subtle,
  bg-danger, text-danger-fg, bg-danger-subtle

## SORUN
208 adet hardcoded Tailwind renk class'i var (bg-red-500, text-emerald-400, bg-slate-800, vb.)
Bu class'lar dark mode'da calismaz ve design system'den kopuktur.

## DONUSUM HARITALARI

### Yesil tonlari (basari, gecti, aktif, bagli):
| Eski | Yeni |
|------|------|
| `bg-emerald-500/10`, `bg-green-50`, `bg-green-100` | `bg-success-subtle` |
| `bg-emerald-500`, `bg-green-500` | `bg-success` |
| `text-emerald-400`, `text-emerald-500`, `text-green-600`, `text-green-700` | `text-success` |

### Kirmizi tonlari (hata, basarisiz, arsiv):
| Eski | Yeni |
|------|------|
| `bg-red-500/10`, `bg-red-50`, `bg-red-100` | `bg-danger-subtle` |
| `bg-red-500`, `bg-red-600` | `bg-danger` |
| `text-red-400`, `text-red-500`, `text-red-600` | `text-danger` |

### Sari/turuncu tonlari (uyari, bekliyor):
| Eski | Yeni |
|------|------|
| `bg-amber-500/10`, `bg-orange-50`, `bg-orange-100`, `bg-yellow-50`, `bg-yellow-100` | `bg-warning-subtle` |
| `bg-amber-500`, `bg-orange-500`, `bg-yellow-500` | `bg-warning` |
| `text-amber-400`, `text-amber-500`, `text-orange-600`, `text-yellow-700` | `text-warning` |

### Mavi tonlari (accent, aktif, kosuyor):
| Eski | Yeni |
|------|------|
| `bg-blue-500/10`, `bg-blue-50`, `bg-blue-100` | `bg-accent-subtle` |
| `bg-blue-500`, `bg-blue-600` | `bg-accent` |
| `text-blue-400`, `text-blue-500`, `text-blue-600` | `text-accent` |

### Mor tonlari (AI, zamanlanmis):
| Eski | Yeni |
|------|------|
| `bg-violet-500/10`, `bg-purple-50`, `bg-purple-100` | `bg-ai-subtle` |
| `bg-violet-500`, `bg-purple-600` | `bg-ai` |
| `text-violet-400`, `text-purple-600` | `text-ai` |

### Gri tonlari (taslak, devre disi, arka plan):
| Eski | Yeni |
|------|------|
| `bg-slate-800`, `bg-gray-800`, `bg-slate-900` | `bg-bg-subtle` |
| `bg-slate-100`, `bg-gray-50`, `bg-gray-100` | `bg-bg-subtle` |
| `text-slate-300`, `text-slate-400`, `text-gray-400`, `text-gray-500` | `text-muted` |
| `text-slate-500`, `text-gray-600` | `text-muted-fg` |
| `border-slate-700`, `border-slate-800`, `border-gray-200`, `border-gray-300` | `border-border` |

## ISLEM SIRASI

### Adim 1: components/ klasorundeki hardcoded renkleri degistir
Oncelik sirasi:
1. `components/nexus/StatusBadge.tsx` — EN ONEMLI, tum sayfalar kullaniyor
2. `components/nexus/StatCard.tsx`
3. `components/nexus/DataGrid.tsx`
4. `components/ui/skeleton.tsx`
5. `components/ui/badge.tsx`
6. Diger component'ler

### Adim 2: app/ altindaki sayfalardaki hardcoded renkleri degistir
- Tum page.tsx dosyalarinda yukaridaki donusum haritasini uygula
- dark: prefix'li class'lara gerek YOK — token'lar otomatik dark mode destekler

### Adim 3: StatusBadge.tsx'i TAMAMEN refactor et

Mevcut (hardcoded):
```tsx
const statusConfig = {
  active: { bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400" },
  error:  { bg: "bg-red-500/10",     text: "text-red-400",    dot: "bg-red-400" },
  // ... 15+ durum
};
```

Yeni (token-based):
```tsx
const statusConfig = {
  active:    { bg: "bg-success-subtle", text: "text-success", dot: "bg-success", label: "Aktif" },
  completed: { bg: "bg-success-subtle", text: "text-success", dot: "bg-success", label: "Tamamlandı" },
  passed:    { bg: "bg-success-subtle", text: "text-success", dot: "bg-success", label: "Geçti" },
  connected: { bg: "bg-success-subtle", text: "text-success", dot: "bg-success", label: "Bağlı" },
  error:     { bg: "bg-danger-subtle",  text: "text-danger",  dot: "bg-danger",  label: "Hata" },
  failed:    { bg: "bg-danger-subtle",  text: "text-danger",  dot: "bg-danger",  label: "Başarısız" },
  archived:  { bg: "bg-danger-subtle",  text: "text-danger",  dot: "bg-danger",  label: "Arşiv" },
  pending:   { bg: "bg-warning-subtle", text: "text-warning", dot: "bg-warning", label: "Bekliyor" },
  running:   { bg: "bg-accent-subtle",  text: "text-accent",  dot: "bg-accent",  label: "Koşuyor" },
  scheduled: { bg: "bg-ai-subtle",      text: "text-ai",      dot: "bg-ai",      label: "Zamanlandı" },
  draft:     { bg: "bg-bg-subtle",      text: "text-muted",   dot: "bg-muted",   label: "Taslak" },
  skipped:   { bg: "bg-bg-subtle",      text: "text-muted",   dot: "bg-muted",   label: "Atlandı" },
  paused:    { bg: "bg-warning-subtle", text: "text-warning", dot: "bg-warning", label: "Duraklatıldı" },
  warning:   { bg: "bg-warning-subtle", text: "text-warning", dot: "bg-warning", label: "Uyarı" },
  disconnected: { bg: "bg-bg-subtle",   text: "text-muted",   dot: "bg-muted",   label: "Bağlı Değil" },
};
```

## KURALLAR
- SADECE renk class'larini degistir, layout/spacing'e dokunma
- Gradient, opacity (bg-emerald-500/10) → token-subtle karsiligi kullan
- Eslesen token yoksa OLDUĞU GIBI BIRAK (nadir durumlarda spesifik renk gerekebilir)
- Dark mode icin ayri class ekleme — token'lar otomatik dark mode destekler
- Dosya dosya ilerle, her biri sonrasi tsc kontrol et

## DOGRULAMA
```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -10
# Ayrica gorunumu kontrol et — renklerin dogru eslesmesi icin app'i ac:
# npm run dev → localhost:3000
```
```
