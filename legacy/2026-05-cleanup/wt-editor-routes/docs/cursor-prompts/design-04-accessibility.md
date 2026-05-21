# Design Agent 4: Erisilebilirlik (Accessibility / a11y)

## Cursor'a yapistir:

```
Sen bir frontend muhendisisin ve erisilebilirlik (a11y) uzmanisin.
BGTS bankacilik test platformunun WCAG 2.1 AA uyumluluğunu saglayacaksin.

## MEVCUT DURUM
- Toplam 52 aria-* kullanimi (77 sayfa icin ÇOK AZ)
- 4 adet React.memo (performans icin de onemli ama bu agent'in konusu degil)
- 0 adet alt text (img tag'leri icin)
- StatusBadge'daki dot indicator icin aria-hidden yok
- Interactive element'lerde aria-label eksik
- Keyboard navigation desteği belirsiz

## YAPILACAKLAR

### 1. Interactive Button'lara aria-label ekle

ONCE su dosyalari oku ve ikon-only button'lari bul:

#### apps/web/components/AppShell.tsx (veya shell/ altindaki dosyalar)
Sidebar'daki ikon button'lar:
```tsx
// ONCE (ikon-only, label yok):
<button onClick={toggleSidebar}>
  <ChevronIcon />
</button>

// SONRA:
<button onClick={toggleSidebar} aria-label="Kenar çubuğunu daralt">
  <ChevronIcon aria-hidden="true" />
</button>
```

Her ikon-only button'a `aria-label` ekle:
- Sidebar toggle → "Kenar çubuğunu daralt" / "Kenar çubuğunu genişlet"
- Theme toggle → "Karanlık moda geç" / "Aydınlık moda geç"
- Notification bell → "Bildirimler"
- Close button'lar → "Kapat"
- Delete button'lar → "Sil"
- Edit button'lar → "Düzenle"
- Search icon → "Ara"

#### apps/web/components/ui/ altindaki bilesenler
- modal.tsx: Close button'a `aria-label="Kapat"` ekle
- tabs.tsx: Tab list'e `role="tablist"`, tab'lere `role="tab"`, `aria-selected` ekle
- data-table.tsx: Sortable header'lara `aria-sort` ekle
- select.tsx: `aria-expanded`, `aria-haspopup` ekle (Radix UI zaten sagliyorsa dokunma)
- toast.tsx: `role="alert"` ve `aria-live="polite"` ekle

### 2. StatusBadge.tsx'e a11y ekle

```tsx
// ONCE:
<span className={`...`}>
  {dot && <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} shrink-0`} />}
  {displayLabel}
</span>

// SONRA:
<span className={`...`} role="status" aria-label={`Durum: ${displayLabel}`}>
  {dot && <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} shrink-0`} aria-hidden="true" />}
  {displayLabel}
</span>
```

### 3. Dekoratif ikon'lara aria-hidden ekle

Tum SVG ikon'lar ve emoji'ler dekoratif ise (yaninda metin varsa):
```tsx
// ONCE:
<span>🔍</span> Arama

// SONRA:
<span aria-hidden="true">🔍</span> Arama
```

Dosyalari tara: components/ ve app/ altinda emoji kullanan yerleri bul.
PageHeader, SectionCard, nav item'lar genellikle emoji ikon kullaniyor.

### 4. Form label'lari

apps/web/components/ui/input.tsx ve diger form element'leri kontrol et:
```tsx
// Her input'un bir label'i olmali:
<label htmlFor="project-name" className="text-sm text-muted-fg">Proje Adı</label>
<Input id="project-name" ... />
```

Sayfalar icinde label olmadan kullanilan input'lari bul ve `aria-label` ekle:
```tsx
// Label yoksa aria-label kullan:
<Input aria-label="Proje adı" ... />
```

### 5. Sayfa basliklarini kontrol et

Her sayfa bir `<h1>` icermeli. PageHeader bileseninin `<h1>` kullandigini dogrula:
```tsx
// apps/web/components/nexus/PageHeader.tsx
// title prop'u <h1> icinde render edilmeli:
<h1 className="text-2xl font-bold text-fg">{title}</h1>
```

### 6. Focus yonetimi

#### Skip to content link
apps/web/app/layout.tsx veya AppShell'in en basina:
```tsx
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 bg-accent text-accent-fg px-4 py-2 rounded"
>
  İçeriğe geç
</a>
```

Ve main content alanina id ekle:
```tsx
<main id="main-content" className="...">
```

#### Focus ring
Tailwind'de focus ring'in gorunur oldugundan emin ol:
```tsx
// Tum interactive element'lerde:
className="... focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
```

### 7. Tablo erisilebilirligi

apps/web/components/nexus/DataGrid.tsx ve apps/web/components/ui/data-table.tsx:
```tsx
<table role="grid" aria-label="Veri tablosu">
  <thead>
    <tr>
      <th scope="col">Başlık</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>...</td>
    </tr>
  </tbody>
</table>
```

### 8. Loading state erisilebilirligi

apps/web/app/(dashboard)/loading.tsx:
```tsx
<div role="status" aria-label="Yükleniyor">
  <Spinner aria-hidden="true" />
  <span className="sr-only">Yükleniyor...</span>
</div>
```

## ONCELIK SIRASI
1. Skip to content link (layout.tsx) — 5 dakika, buyuk etki
2. StatusBadge aria eklemeleri — 5 dakika, cok kullaniliyor
3. Ikon button aria-label'lari — 15 dakika
4. Form aria-label'lari — 20 dakika
5. Tablo erisilebilirligi — 15 dakika
6. Dekoratif ikon aria-hidden — 20 dakika
7. Focus ring kontrolu — 10 dakika

## DOGRULAMA
```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -10
# Ayrica:
# Chrome DevTools → Lighthouse → Accessibility audit
# veya axe-core browser extension ile kontrol
```
```
