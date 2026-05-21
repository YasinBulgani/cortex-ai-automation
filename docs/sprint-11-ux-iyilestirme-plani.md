# BGTS Visium Operations — Sprint 11 UX & UI İyileştirme Planı

**Hazırlanma:** 2026-04-16  
**Kapsam:** 74 sayfa, 45 bileşen, 30 tespit edilen sorun  
**Toplam Süre:** ~12-15 iş günü (4 sprint)

---

## 📊 GENEL PUAN DURUMU (Audit Özeti)

| Kategori | Şimdiki Puan | Hedef Puan |
|----------|-------------|-----------|
| Renk Tutarlılığı | 7.2 / 10 | 9.0 / 10 |
| Kullanılabilirlik (UX) | 6.5 / 10 | 8.5 / 10 |
| Responsive Tasarım | 5.0 / 10 | 8.0 / 10 |
| Boş Durum (Empty State) | 6.8 / 10 | 9.0 / 10 |
| Loading / Skeleton | 5.5 / 10 | 8.5 / 10 |
| Türkçe Dil Tutarlılığı | 7.5 / 10 | 9.5 / 10 |
| Navigasyon Netliği | 8.0 / 10 | 9.0 / 10 |
| Erişilebilirlik (A11Y) | 4.5 / 10 | 7.5 / 10 |
| Form & Validasyon | 5.0 / 10 | 8.0 / 10 |
| **TOPLAM ORTALAMA** | **6.3 / 10** | **8.6 / 10** |

---

## 🔴 SPRINT 11A — Kritik Bug'lar + Renk Standardizasyonu
**Süre:** 2-3 gün | **Öncelik:** ACİL

### Amaç
Görünmez buton, typo, light mode artığı ve semantik renk tutarsızlıklarını gidermek.
Her düzeltme kullanıcıya direkt ve anında görünür etki yapar.

---

### ◾ Dosya 1: `apps/web/app/(dashboard)/p/[projectId]/settings/page.tsx`

#### 🐛 BUG #6 — Görünmez Buton (text-blue-400-fg)
| | Bilgi |
|--|--|
| **Sorun** | `className="... text-blue-400-fg ..."` → geçersiz Tailwind class, buton metni render edilmiyor |
| **Satır** | ~138 |
| **Çözüm** | `text-blue-400-fg` → `text-white` |
| **Etki** | "Kaydet" butonu görünür hale gelir |

#### 🐛 BUG #7 — window.confirm (Sistem Modal'ı)
| | Bilgi |
|--|--|
| **Sorun** | `window.confirm(...)` sistem alert kutusu açıyor — tasarım sistemine uymayan deneyim |
| **Satır** | ~56 |
| **Çözüm** | `useConfirm` hook'u kullan (`ConfirmProvider` zaten `layout.tsx`'de mevcut) |
| **Import ekle** | `import { useConfirm } from "@/components/ui/confirm-dialog"` |
| **Kullanım** | `const { confirm } = useConfirm()` → `await confirm({ title: "Projeyi Sil", message: "...", confirmLabel: "Sil", variant: "danger" })` |
| **Etki** | Branded modal dialog açılır, "İptal / Sil" butonları görünür |

#### 🐛 BUG #2 — Light Mode Artığı (Danger Zone)
| | Bilgi |
|--|--|
| **Sorun** | `border-red-200 bg-red-50 text-red-700` — light mode class'lar dark bg üzerinde görünmez |
| **Satır** | ~146–159 |
| **Çözüm** | `border-red-900 bg-red-950/20 text-red-400` kullan |
| **Ayrıca** | Satır ~129: `text-green-600 / text-red-600` → `text-emerald-400 / text-red-400` |
| **Etki** | Tehlike bölgesi dark tema'da okunabilir |

---

### ◾ Dosya 2: `apps/web/app/(dashboard)/p/[projectId]/page.tsx` (Dashboard)

#### 🐛 BUG #8 — Türkçe Aksansız Yazılar
| | Bilgi |
|--|--|
| **Sorun** | `"Hazirla"`, `"Kesfet"`, `"Uret"`, `"Calistir"`, `"Gozlemle"` → aksansız |
| **Satır** | ~136, ~244–346 |
| **Çözüm** | `"Hazırla"`, `"Keşfet"`, `"Üret"`, `"Çalıştır"`, `"Gözlemle"` |
| **Ayrıca** | `"Destekleyen Urunler"` → `"Destekleyen Ürünler"` (~574), `"Ac"` → `"Aç"` (~576) |

---

### ◾ Dosya 3: `apps/web/app/(dashboard)/p/[projectId]/executions/page.tsx`

#### 🐛 BUG #29 — İngilizce Başlık
| | Bilgi |
|--|--|
| **Sorun** | `title="Execution Koşuları"` → karma İngilizce/Türkçe |
| **Satır** | ~111 |
| **Çözüm** | `title="Test Koşuları"` |

#### 🐛 BUG #28 — Emoji + Türkçe karışımı
| | Bilgi |
|--|--|
| **Sorun** | `"🍎 iOS"` `"🤖 Android"` tab label olarak kullanılıyor — emoji tab'da tutarsız |
| **Satır** | ~168–173 |
| **Çözüm** | `"iOS"` `"Android"` (platform badge'leri zaten ikonu taşıyor) |

#### 🔴 BUG #4 — Android Rengi Semantik Çakışma
| | Bilgi |
|--|--|
| **Sorun** | Android: `text-green-400` → `emerald-400` ile başarı metriklerinde karışıyor |
| **Satır** | ~280–287 |
| **Çözüm** | `text-teal-400` kullan |

---

### ◾ Dosya 4: `apps/web/components/AppShell.tsx`

#### 🔴 BUG #3 — Sidebar Kontrast (WCAG AA)
| | Bilgi |
|--|--|
| **Sorun** | `text-slate-400` (#94a3b8) → kontrast ~4.2:1, WCAG AA için 4.5:1 gerekli |
| **Satır** | ~333 (`linkCls` fonksiyonu) + ~79, 88, 575, 580 |
| **Çözüm** | `text-slate-300` (#cbd5e1) → ~6.0:1 kontrast |

---

### ◾ Dosya 5: `apps/web/components/nexus/StatCard.tsx`

#### 🎨 Semantik Renk Token — `success` Tipi Ekleme
| | Bilgi |
|--|--|
| **Sorun** | "Başarı oranı" dashboard'da `violet-400`, analytics'te `emerald-400` → tutarsız |
| **Değişiklik** | `colorMap`'e `success` girdisi ekle: `{ bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" }` |
| **Props tip** | `color?: "blue" \| "emerald" \| "red" \| "amber" \| "violet" \| "slate" \| "success"` |
| **Uygulama** | analytics ve dashboard'daki başarı oranı kartlarında `color="success"` kullan |

**Test Senaryoları (11A):**
- [ ] Settings → "Kaydet" butonundaki text görünüyor mu?
- [ ] Settings → Proje sil → ConfirmDialog açılıyor mu? İptal/Onayla çalışıyor mu?
- [ ] Settings → Danger zone dark temada okunuyor mu?
- [ ] Dashboard → Tüm Türkçe başlıklar aksanlarıyla doğru yazılmış mı?
- [ ] Executions → "Test Koşuları" başlığı görünüyor mu?
- [ ] Sidebar → Tüm link'ler okunaklı mı (kontrast)?

---

## 🟡 SPRINT 11B — Responsive + Skeleton + Loading
**Süre:** 3-4 gün | **Öncelik:** YÜKSEK

### Amaç
Mobil cihazlarda kırılan grid'leri düzeltmek ve yükleme sırasındaki boş ekranları ortadan kaldırmak.

---

### ◾ Dosya 1: `apps/web/components/ui/skeleton.tsx`

#### Temel Skeleton Renk Düzeltmesi
| | Bilgi |
|--|--|
| **Sorun** | `bg-border/50` dark mode'da çok soluk kalıyor |
| **Satır** | ~6 |
| **Çözüm** | `bg-slate-800` kullan (diğer skeleton'larla tutarlı) |

#### Yeni: `StatsSkeleton` Bileşeni
```tsx
export function StatsSkeleton({ count = 4, className }: { count?: number; className?: string }) {
  return (
    <div className={cn("grid gap-3 grid-cols-2", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}
```

---

### ◾ Dosya 2: `apps/web/components/nexus/EmptyState.tsx`

#### SVG Icon Desteği
| | Bilgi |
|--|--|
| **Mevcut** | `icon: string` (sadece emoji) |
| **Yeni** | `icon?: string \| React.ReactNode` |
| **Render** | `typeof icon === 'string' ? <div className="text-5xl mb-4">{icon}</div> : <div className="mb-4 text-slate-400">{icon}</div>` |

#### `size` Prop Ekleme
```tsx
type EmptyStateSize = "sm" | "md" | "lg";
// sm → py-8, md → py-16 (default), lg → py-24
```

---

### ◾ Dosya 3: `apps/web/app/(dashboard)/p/[projectId]/executions/page.tsx`

#### 🔴 BUG #9 — Stats Grid Responsive
| | Bilgi |
|--|--|
| **Sorun** | `grid-cols-5` sabit → mobilde 5 kolon sığmaz, overflow olur |
| **Satır** | ~145 |
| **Çözüm** | `grid-cols-2 sm:grid-cols-3 lg:grid-cols-5` |

#### ⌛ BUG #20 — Stats Skeleton
Loading state'inde stats section için `StatsSkeleton` kullan:
```tsx
{loading ? (
  <StatsSkeleton count={5} className="mb-5 sm:grid-cols-3 lg:grid-cols-5" />
) : (
  /* mevcut stats grid */
)}
```

---

### ◾ Dosya 4: `apps/web/app/(dashboard)/p/[projectId]/scenarios/page.tsx`

#### 🔴 BUG #11 — Stats Grid Responsive
| | Bilgi |
|--|--|
| **Sorun** | `grid-cols-3` sabit → mobilde sıkışık |
| **Satır** | ~275 |
| **Çözüm** | `grid-cols-1 sm:grid-cols-3` |

#### ⌛ BUG #18 — Liste Loading Skeleton
| | Bilgi |
|--|--|
| **Sorun** | Senaryo listesi yüklenirken hiçbir şey gösterilmiyor |
| **Çözüm** | `loading` state'inde `<TableSkeleton rows={8} />` göster |

#### 📄 BUG #25 — Client-Side Pagination
```tsx
const ITEMS_PER_PAGE = 50;
const [page, setPage] = useState(1);

// search veya statusFilter değişince sayfa sıfırla
useEffect(() => { setPage(1); }, [search, statusFilter]);

// Tablo altına sayfalama kontrolü:
const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
const paginatedItems = filtered.slice((page-1)*ITEMS_PER_PAGE, page*ITEMS_PER_PAGE);
```

**Pagination UI:**
```
[← Önceki]  Sayfa 1 / 4  [Sonraki →]    50 - 100 / 187 senaryo
```

---

### ◾ Dosya 5: `apps/web/app/(dashboard)/p/[projectId]/analytics/page.tsx`

#### 🔴 BUG #12 — SVG Chart Responsive
| | Bilgi |
|--|--|
| **Sorun** | `const W = 720` hardcoded → mobilde overflow |
| **Satır** | ~85–86 |
| **Çözüm** | `width` attribute kaldır, `viewBox="0 0 720 200"` + `className="w-full"` |
| **Ekle** | `preserveAspectRatio="xMidYMid meet"` |

#### ⌛ BUG #19 — Yükleme Skeleton
```tsx
{stats === null ? (
  <StatsSkeleton count={4} className="mb-6 lg:grid-cols-4" />
) : (
  /* mevcut stat cards */
)}

{trends.length === 0 && stats === null ? (
  <div className="h-[200px] animate-pulse rounded-lg bg-slate-800" />
) : /* chart veya empty state */}
```

#### 📭 BUG #21 — Analytics Empty State
```tsx
// "Veri yok" metnini EmptyState ile değiştir:
<EmptyState
  icon="📈"
  title="Henüz trend verisi yok"
  description="İlk test koşumunu başlatarak analitik veri oluşturun"
  size="sm"
  action={
    <Link href={`/p/${projectId}/executions/new`} className="...">
      Koşu Başlat
    </Link>
  }
/>
```

---

### ◾ Dosya 6: `apps/web/app/(dashboard)/p/[projectId]/schedules/page.tsx`

#### 📅 Stats Grid Responsive
| | Bilgi |
|--|--|
| **Satır** | ~705–718 |
| **Çözüm** | `grid-cols-4` → `grid-cols-2 lg:grid-cols-4` |

#### 🕒 BUG #30 — Süre Kısaltmaları
| | Bilgi |
|--|--|
| **Sorun** | `"2d"`, `"3h"` → kültürel olarak belirsiz |
| **Satır** | ~93 (`useCountdown`) |
| **Çözüm** | `${h} saat`, `${m} dak`, `${s} sn` |

#### 🔴 BUG #27 — Form Validation UI
Hata durumunda:
```tsx
// Input'a error class:
className={cn("border-slate-700 ...", nameError && "border-red-500 focus:border-red-500")}

// Hata mesajı:
{nameError && (
  <p role="alert" className="text-xs text-red-400 mt-1">{nameError}</p>
)}
```

---

### ◾ Dosya 7: `apps/web/app/(dashboard)/p/[projectId]/settings/page.tsx`

#### ⌛ BUG #17 — Loading Spinner
```tsx
if (loading) return (
  <div className="max-w-2xl mx-auto py-10 px-4">
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5 animate-pulse">
      <div className="h-4 w-24 rounded bg-slate-800" />
      <div className="h-9 rounded bg-slate-800" />
      <div className="h-4 w-20 rounded bg-slate-800" />
      <div className="h-24 rounded bg-slate-800" />
      <div className="h-9 rounded bg-slate-800 w-32 ml-auto" />
    </div>
  </div>
);
```

**Test Senaryoları (11B):**
- [ ] Mobil ekranda (375px) executions stats sığıyor mu?
- [ ] Analytics grafiği dar ekranda doğru scale ediliyor mu?
- [ ] Scenarios 60 kayıtla pagination gösteriyor mu?
- [ ] Settings yüklenirken form skeleton görünüyor mu?
- [ ] Analytics veri yokken EmptyState + CTA görünüyor mu?

---

## 🟢 SPRINT 11C — Erişilebilirlik + İnteraktivite
**Süre:** 3-4 gün | **Öncelik:** ORTA-YÜKSEK

### Amaç
Klavye erişilebilirliği, screen reader desteği ve chart'larda interaktif tooltip eklemek.

---

### ◾ Dosya 1: `apps/web/app/(dashboard)/p/[projectId]/executions/page.tsx`

#### ♿ BUG #13 — Hover-Only Butonlar
| | Bilgi |
|--|--|
| **Sorun** | `opacity-0 group-hover:opacity-100` → klavye kullanıcılar erişemiyor |
| **Satır** | ~313 |
| **Çözüm** | `opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-all` |

#### ♿ BUG #16 — Icon-Only Butonlar aria-label
| Buton | Satır | Mevcut | Eklenecek |
|-------|-------|--------|-----------|
| Allure JSON indir | ~315 | `title="Allure JSON indir"` | `aria-label="Allure JSON indir"` |
| Detay görüntüle | ~328 | `title="Detay"` | `aria-label="Detay görüntüle"` |
| CSV indir | ~116 | `title="CSV olarak indir"` | `aria-label="CSV olarak indir"` |

---

### ◾ Dosya 2: `apps/web/app/(dashboard)/p/[projectId]/scenarios/page.tsx`

#### ♿ BUG #13 — Hover-Only Düzenle Butonu
| | Bilgi |
|--|--|
| **Satır** | ~125 |
| **Çözüm** | `opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity` |

#### ♿ BUG #16 — Düzenle aria-label
| | Bilgi |
|--|--|
| **Satır** | ~126–134 |
| **Ekle** | `aria-label="Senaryoyu düzenle"` |

---

### ◾ Dosya 3: `apps/web/app/(dashboard)/p/[projectId]/analytics/page.tsx`

#### ♿ BUG #14 — SVG Chart aria
| | Bilgi |
|--|--|
| **Sorun** | SVG'de `role="img"` ve `<title>` eksik |
| **Trend Chart SVG** | `role="img" aria-labelledby="trend-chart-title"` + `<title id="trend-chart-title">Başarı oranı trendi çizgi grafiği</title>` |
| **Bar Chart SVG** | `role="img" aria-labelledby="bar-chart-title"` + `<title id="bar-chart-title">Günlük koşum çubuğu grafiği</title>` |

#### 📊 BUG #24 — Interaktif Tooltip
```tsx
const [hoveredPoint, setHoveredPoint] = useState<TrendPoint | null>(null);

// Her circle'a:
<circle
  onMouseEnter={() => setHoveredPoint(p)}
  onMouseLeave={() => setHoveredPoint(null)}
  ...
/>

// SVG içinde tooltip overlay:
{hoveredPoint && (
  <g>
    <rect
      x={hoveredPoint.x - 40} y={hoveredPoint.y - 32}
      width={80} height={24}
      rx={4} fill="#1e293b" stroke="#334155"
    />
    <text
      x={hoveredPoint.x} y={hoveredPoint.y - 16}
      textAnchor="middle" fill="#f1f5f9" fontSize={11}
    >
      {hoveredPoint.date}: %{hoveredPoint.rate.toFixed(1)}
    </text>
  </g>
)}
```

---

### ◾ Dosya 4: `apps/web/app/(dashboard)/p/[projectId]/schedules/page.tsx`

#### ♿ BUG #13 — Hover-Only Action Butonları
| | Bilgi |
|--|--|
| **Satır** | ~547 |
| **Çözüm** | `opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity` |

#### ♿ BUG #16 — Schedule Action aria-label
| Buton | Eklenecek |
|-------|-----------|
| ▶ Çalıştır | `aria-label={triggering === s.id ? "Çalışıyor" : "Şimdi çalıştır"}` |
| ✕ Sil | `aria-label="Zamanlayıcıyı sil"` |

#### ♿ BUG #15 — Form Hata rol
| | Bilgi |
|--|--|
| **Tüm hata div'leri** | `role="alert"` ekle |

---

### ◾ Dosya 5: `apps/web/app/(dashboard)/p/[projectId]/mobile/page.tsx`

#### ♿ BUG #13 — Hover-Only "Cihaza Ekle" Butonu
| | Bilgi |
|--|--|
| **Satır** | ~157–160 |
| **Çözüm** | `opacity-0 group-hover:opacity-100 group-focus-within:opacity-100` |

#### ♿ BUG #16 — Refresh Butonu aria-label
| | Bilgi |
|--|--|
| **Satır** | ~113–122 |
| **Çözüm** | `title="Yenile"` yerine/yanına `aria-label="Cihaz listesini yenile"` |

---

### ◾ Dosya 6: `apps/web/components/AppShell.tsx`

#### 📭 BUG #22 — Proje Listesi Empty State
```tsx
// Satır ~118–119'daki sadece metin olan empty state:
// Eski:
<p className="px-2 py-1.5 text-xs text-slate-600">Proje bulunamadı</p>

// Yeni:
<div className="px-2 py-3 flex flex-col items-center gap-2">
  <svg className="w-5 h-5 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
  </svg>
  <p className="text-xs text-slate-600 text-center">Proje bulunamadı</p>
  <Link href="/projects" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
    Proje oluştur →
  </Link>
</div>
```

**Test Senaryoları (11C):**
- [ ] Executions'ta Tab tuşuyla gezinirken action butonları görünüyor mu?
- [ ] Screen reader analytics chart'ı tanımlıyor mu?
- [ ] Analytics chart üzerine gelince tooltip değer gösteriyor mu?
- [ ] Schedules formu validation hatasını `role="alert"` ile bildiriyor mu?
- [ ] Sidebar proje listesi boşken ikon ve link görünüyor mu?

---

## 🔵 SPRINT 11D — UX Derinleştirme + Pagination + Dil
**Süre:** 3-4 gün | **Öncelik:** ORTA

### Amaç
Executions pagination, schedules form UX, dil tutarlılığı ve Mobile History sorunları.

---

### ◾ Dosya 1: `apps/web/app/(dashboard)/p/[projectId]/executions/page.tsx`

#### 📄 BUG #26 — Executions Pagination
```tsx
const PAGE_SIZE = 25;
const [page, setPage] = useState(1);

// platformTab veya filtreler değişince reset:
useEffect(() => { setPage(1); }, [platformTab, search, statusFilter]);

const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
const paginatedRows = filtered.slice((page-1)*PAGE_SIZE, page*PAGE_SIZE);
```

**Pagination Footer:**
```tsx
<div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
  <span className="text-sm text-slate-500">
    {(page-1)*PAGE_SIZE + 1}–{Math.min(page*PAGE_SIZE, filtered.length)} / {filtered.length} koşum
  </span>
  <div className="flex gap-2">
    <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}
      className="px-3 py-1.5 text-sm rounded-lg border border-slate-700 disabled:opacity-40 hover:bg-slate-800">
      ← Önceki
    </button>
    <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page === totalPages}
      className="px-3 py-1.5 text-sm rounded-lg border border-slate-700 disabled:opacity-40 hover:bg-slate-800">
      Sonraki →
    </button>
  </div>
</div>
```

---

### ◾ Dosya 2: `apps/web/app/(dashboard)/p/[projectId]/mobile/history/page.tsx`

#### 📱 Stats Grid Responsive
| | Bilgi |
|--|--|
| **Sorun** | `grid-cols-4` sabit |
| **Satır** | ~139 |
| **Çözüm** | `grid-cols-2 lg:grid-cols-4` |

#### 📱 BUG #28 — Tab Etiketleri
| Eski | Yeni |
|------|------|
| `"🍎 iOS"` | `"iOS"` |
| `"🤖 Android"` | `"Android"` |
| `"Tümü"` | `"Tümü"` ✅ |

#### 📱 Android Rengi
| | Bilgi |
|--|--|
| **Satır** | ~platformBadge function |
| **Eski** | `text-green-400` (emerald ile karışıyor) |
| **Yeni** | `text-teal-400` |

#### ♿ Hover-Only Action Butonları
| | Bilgi |
|--|--|
| **Satır** | ~300 |
| **Çözüm** | `group-focus-within:opacity-100` ekle |

---

### ◾ Dosya 3: `apps/web/app/(dashboard)/p/[projectId]/schedules/page.tsx`

#### 📅 Cron Expression Helper Metni
```tsx
// Cron input'un altına:
<p className="mt-1 text-xs text-slate-500">
  Format: dakika saat gün ay haftaGünü &nbsp;|&nbsp;
  Örn: <code className="font-mono">0 8 * * *</code> → her gün 08:00
</p>
```

---

### ◾ Dosya 4: `apps/web/app/(dashboard)/p/[projectId]/analytics/page.tsx`

#### 🎨 Grid Responsive
| | Bilgi |
|--|--|
| **Satır** | ~137 |
| **Çözüm** | `grid-cols-4` → `grid-cols-2 lg:grid-cols-4` |

#### 🎨 Semantik Renk Kullanımı
| | Bilgi |
|--|--|
| **Satır** | ~148–149 |
| **Eski** | `color="emerald"` |
| **Yeni** | `color="success"` (Sprint 11A'da StatCard'a eklendi) |

---

### ◾ Dosya 5: `apps/web/app/(dashboard)/p/[projectId]/mobile/page.tsx`

#### 🌐 Türkçe Aksansız Metinler
Dosya içindeki tüm aksansız Türkçe kelimeleri düzelt:
- `"Cihaz secimi"` → `"Cihaz seçimi"`
- `"canli izleme"` → `"canlı izleme"`
- `"raporlar ve AI analizine tasiyabilirsiniz"` → `"raporlar ve AI analizine taşıyabilirsiniz"`

---

**Test Senaryoları (11D):**
- [ ] Executions 30'dan fazla kayıtla pagination gösteriyor mu?
- [ ] Sayfalar arası gezinme çalışıyor mu?
- [ ] Mobile History mobilde 2 kolonlu mu?
- [ ] Tüm platform renkleri semantik mi (success=emerald, Android=teal)?
- [ ] Cron input helper metni görünüyor mu?
- [ ] Mobile sayfasındaki tüm Türkçe metinler aksanlı mı?

---

## 📋 KONSOLİDE GÖREV LİSTESİ

### Dosya Başına İş Özeti

| Dosya | Sprint | Değişiklik Sayısı | Tahmini Süre |
|-------|--------|------------------|-------------|
| `settings/page.tsx` | 11A + 11B | 5 | 2 saat |
| `executions/page.tsx` | 11A + 11B + 11C + 11D | 8 | 4 saat |
| `scenarios/page.tsx` | 11B + 11C | 4 | 3 saat |
| `analytics/page.tsx` | 11B + 11C + 11D | 7 | 4 saat |
| `schedules/page.tsx` | 11B + 11C + 11D | 6 | 3 saat |
| `mobile/page.tsx` | 11C + 11D | 3 | 1.5 saat |
| `mobile/history/page.tsx` | 11D | 4 | 2 saat |
| `page.tsx` (dashboard) | 11A | 1 | 30 dak |
| `AppShell.tsx` | 11A + 11C | 2 | 1.5 saat |
| `StatCard.tsx` | 11A | 1 | 30 dak |
| `skeleton.tsx` | 11B | 2 | 45 dak |
| `EmptyState.tsx` | 11B | 2 | 1 saat |

**Toplam Tahmini:** ~23 saat (yaklaşık 3 tam iş günü odaklı çalışma)

---

## 🎯 BAŞARI KRİTERLERİ

Sprint 11 tamamlandığında:

1. ✅ Settings'te "Kaydet" butonu görünür ve çalışır
2. ✅ Tüm confirm işlemleri branded ConfirmDialog kullanır
3. ✅ Dark tema'da tüm metin renkleri okunabilir (kontrast ≥ 4.5:1)
4. ✅ Tüm grid'ler mobilde kırılmıyor (breakpoint responsive)
5. ✅ Her sayfada loading sırasında skeleton animasyonu var
6. ✅ Analytics chart tooltip değerleri gösteriyor
7. ✅ Klavye ile gezinirken tüm butonlara erişilebiliyor
8. ✅ SVG chart'larda screen reader başlığı var
9. ✅ Scenarios ve Executions 50+ kayıtta pagination gösteriyor
10. ✅ Tüm Türkçe metinler aksanlı ve tutarlı
11. ✅ "Başarı oranı" her yerde emerald (success) rengi kullanıyor
12. ✅ Android teal, iOS blue olarak ayrışıyor

**Hedef Skor:** 6.3/10 → 8.6/10

---

*Bu plan `docs/sprint-11-ux-iyilestirme-plani.md` olarak kaydedilmiştir.*  
*Uygulamaya başlamak için: "sprint 11A başlat" veya "hepsini uygula" de.*
