# Neurex QA — Gelişmiş Tasarım Planı v2

## Vizyon

Şu anda Cortex'e **eşit** seviyedeyiz. Hedef: Linear / Vercel / Stripe / Notion seviyesinde **dünya markası kalitesinde** bir QA operasyon platformu.

Üç temel prensip:
1. **Hızlı**: Her etkileşim < 100ms hissetmeli (optimistic UI, skeleton, prefetch)
2. **Akıllı**: AI her yerde, bağlamsal ve sessiz — gürültü değil yardım
3. **Güzel**: Her detay özen — animasyon, tipografi, ikonografi, boşluk

---

## FAZ A — Tasarım Sistemi Temeli (3-4 gün)

> Şu anda her sayfada renkler, padding'ler, font'lar tutarsız. Önce ortak dili kuralım.

### A.1 Design Tokens
**Dosya:** `apps/web/lib/design-tokens.ts` (yeni) + `apps/web/app/globals.css`

```ts
// Renk skalası — semantic tokens
export const tokens = {
  // Surface katmanları (yüzey hiyerarşisi)
  surface: {
    base: 'slate-950',     // En arka katman
    raised: 'slate-900',   // Kart, panel
    overlay: 'slate-800',  // Dropdown, modal
    accent: 'slate-700',   // Hover, active
  },
  // Brand renkleri — per ürün
  brand: {
    primary: { neurex: 'violet-500', mobile: 'rose-500', web: 'blue-500',
               service: 'emerald-500', studio: 'amber-500', data: 'cyan-500' },
  },
  // Semantic
  status: { success, warning, danger, info, neutral },
  // Tipografi skalası — modüler ölçek 1.250
  text: { xs: '11px', sm: '13px', base: '14px', lg: '16px', xl: '20px', '2xl': '28px', '3xl': '36px' },
}
```

### A.2 Tipografi Sistemi
- **Inter Variable** (gövde) + **JetBrains Mono** (kod)
- Sabit satır yükseklikleri (1.4 / 1.5 / 1.6)
- Tracking: başlıklarda -0.02em, gövde 0
- Numerik fontlar tabular: `font-feature-settings: "tnum"`

### A.3 Component Library Genişletme
**Klasör:** `apps/web/components/ui/`

Eksik komponentler:
- `Tooltip` (radix-ui tabanlı, klavye erişimi)
- `Popover` (Combobox, MenuButton için)
- `Dialog` (mevcut Modal yerine portal-based)
- `Sheet` (sağdan slide-in panel — detay görünüm için)
- `DataTable` (sortable, filterable, virtualized)
- `Sparkline` (mini trend grafik)
- `Avatar` (initial + gradient + image fallback)
- `Combobox` (typeahead dropdown)
- `KeyboardShortcut` (`<kbd>K</kbd>` görsel)
- `EmptyState` (illüstrasyon + CTA)
- `Skeleton` (zaten var, çeşitlendir)

---

## FAZ B — Per-Ürün Tema & Brand (2 gün)

> Her ürün ailesi kendi rengiyle "kimliğini" yansıtsın.

### B.1 Ürün Renk Sistemi
**Dosya:** `apps/web/lib/product.ts` (extend)

```ts
PRODUCT_BRAND_COLORS: Record<ProductFamilyId, {
  primary: string;        // ana vurgu (text, border)
  primarySoft: string;    // bg blue-900/30
  accent: string;         // gradient end
  emoji: string;          // 🚀 marka simgesi
}>
```

| Ürün | Birincil | Aksent | Emoji |
|------|----------|--------|-------|
| One | violet-500 | indigo-600 | ⚡ |
| Studio | amber-500 | orange-600 | ✏️ |
| Service | emerald-500 | teal-600 | 🔌 |
| Web | blue-500 | sky-600 | 🌐 |
| Mobile | rose-500 | pink-600 | 📱 |
| Data | cyan-500 | sky-600 | 💾 |
| Intelligence | violet-500 | purple-600 | 🧠 |
| Code | slate-500 | zinc-600 | 💻 |

### B.2 Dinamik Tema Uygulaması
- Ürün moduna girince: header'da ince renkli çizgi (`border-t-2 border-rose-500`)
- Aktif nav linki o ürünün rengiyle
- Logo gradient o ürün rengine geçer (kısa animasyon)
- CSS değişkeni: `--brand-primary` runtime'da değişir

### B.3 Sidebar Branding
- Ürün modunda logo ikonu o ürünün emoji'siyle değişir
- Subtitle altında ince renkli pulse dot
- "← Tüm Ürünlere Dön" butonu ürün rengiyle hover

---

## FAZ C — Command Palette (Cmd+K) Yenileme (2-3 gün)

> Ana kullanıcılar fareyi bırakmalı. Her şey klavyeden.

### C.1 Mevcut CommandPalette'i Modernleştir
**Dosya:** `apps/web/components/CommandPalette.tsx`

Eksikler:
- ❌ Klavye nav (↑↓ ile gezinme)
- ❌ Fuzzy search (sırayla harf eşleştirme — "akm" → "Aktivite Monitörü")
- ❌ Recent commands (son 5)
- ❌ Pinned shortcuts
- ❌ Inline preview (sayfa önizlemesi)
- ❌ Action verbs ("Yeni proje oluştur", "Senaryo çalıştır")

Hedef: **CmdK + cmdk lib** ile Linear seviye command bar.

### C.2 Command Kategorileri
```
GİT (Pages)
  → Aktivite Monitörü                    [G A]
  → Projeler                              [G P]
  → Senaryo IDE                           [G I]

YAP (Actions)
  → Yeni Proje Oluştur                   [N P]
  → Yeni Senaryo                          [N S]
  → Senaryo Çalıştır                      [Run]
  → AI Asistan'a Sor                      [Cmd+J]

PROJEYE GEÇ (Switcher)
  → 🔍 [Otomatik proje arama]

ÜRÜNE GEÇ (Mini-app switcher)
  → ⚡ Neurex One
  → 📱 Neurex Mobile
  → ...

SON KULLANILAN
  → Ödeme API › Senaryolar               (3 dk önce)
  → Login akışı doğrulama                (15 dk önce)
```

### C.3 Klavye Kısayolları
**Dosya:** `apps/web/lib/keyboard-shortcuts.ts` (yeni)

```
Cmd+K       → Command palette aç
Cmd+J       → AI asistan panel aç/kapa
Cmd+B       → Sidebar toggle
G then A    → Aktivite Monitörü'ne git
G then P    → Portfolio
G then I    → IDE
N then S    → Yeni senaryo
?           → Klavye kısayolları yardımı
```

---

## FAZ D — AI-First UX Katmanı (3-4 gün)

> Cortex'te AI sadece bir sayfa. Bizde her sayfada, ama gürültüsüz.

### D.1 AI Asistan Sağ Panel
**Dosya:** `apps/web/components/AiAssistant.tsx` (zaten var, yeniden tasarla)

- **Cmd+J** ile aç/kapa
- Sayfa bağlamına duyarlı: scenarios sayfasındayken "Bu projede nasıl test yazılır?" anlar
- Streaming response (token token akış)
- Önerilen aksiyonlar: tıklayınca uygulama içinde yapar
- Conversation history (sayfa bazlı veya global)
- Markdown + code highlighting

### D.2 Inline AI Yardımcıları
- **Senaryo editörü**: Boş alanda "✨ AI ile yaz" butonu → Gherkin önerileri
- **Hata mesajı**: Stack trace üzerine "🔧 Bu hatayı analiz et"
- **Boş tablo**: "📋 İlk verilerini AI ile oluştur"
- **Form alanları**: Description için "✨ Otomatik tamamla"

### D.3 AI Statüs Bar
Header'da küçük chip:
- `🟢 Ollama (qwen2.5:14b) — 2.3M token` (sağlıklı)
- `🟡 Groq quota %85` (uyarı)
- `🔴 Tüm sağlayıcılar pasif` (kritik)

Tıklayınca AI Health detay paneli açılır.

### D.4 Anlamsal Komut
"feedback bug listele" → Filtreli liste açar
"son 7 günde başarısız koşular" → Filtre uygular + gösterir
"@yasin son senaryoları" → Kullanıcı bazlı filtre

---

## FAZ E — Real-time & Live Veri (2-3 gün)

> Statik dashboard'lar 2010'da kaldı. Her şey live.

### E.1 WebSocket Altyapısı
**Dosya:** `apps/web/lib/useWebSocket.ts` (zaten var, genişlet)

Subscriptions:
- `runs:{projectId}` — koşu durumu canlı
- `executions:{projectId}` — adım adım progress
- `notifications:{userId}` — sistem bildirimleri
- `presence:{projectId}` — kim bu projeye bakıyor

### E.2 Live Indicators
- Aktivite Monitörü stat kartları **gerçek zamanlı** güncellenir (polling değil)
- Pulse dots: aktif koşu sayısı yanında nabız animasyonu
- Senaryo tablosunda: çalışan testler için satır animasyonu (subtle)
- "X kişi bu projeye bakıyor" göstergesi (üst sağda avatarlar)

### E.3 Toast Sistemi Genişlet
- Otomatik gruplama (5 bildirim → "5 yeni")
- Action button (Geri al, Görüntüle)
- Persistent toasts (kritik hatalar için)
- Toast queue + animation

---

## FAZ F — Veri Görselleştirme Şöleni (3-4 gün)

> Sayılar değil, hikayeler göster.

### F.1 Sparklines Her Yerde
**Dosya:** `apps/web/components/ui/sparkline.tsx` (yeni)

- Stat kartlarda: sayının yanında son 7 günün mini grafiği
- Proje kartlarında: pass rate trendi
- Senaryo satırlarında: son 10 koşu mini bar grafiği

### F.2 Aktivite Monitörü Ana Dashboard
- **Hero metric**: bugünkü pass rate, büyük ortada, trend ok
- **Heatmap**: GitHub tarzı 365 gün × proje aktivitesi
- **Top changes**: en çok bozulan / iyileşen senaryolar
- **Team velocity**: kullanıcı bazlı throughput
- **AI cost gauge**: token harcaması progress bar

### F.3 Proje Detay Sayfaları
- **scenarios**: kategori bazlı pie chart, status histogram
- **runs**: timeline view (Gantt benzeri)
- **reports**: full grafiksel rapor — coverage donut, pass rate trend, error categories

### F.4 Charts Library Seçimi
- **Recharts** veya **Visx** (MIT, hafif, customizable)
- Tema entegrasyonu: dark mode renkleri otomatik
- Responsive container

---

## FAZ G — Personalization & Workspace (2 gün)

> Her kullanıcının kendi düzeni olsun.

### G.1 Saved Views
- Filtre kombinasyonları kaydedilebilir: "Mobile + son 7 gün + başarısız"
- Sidebar'da "Kayıtlı Görünümler" bölümü
- Paylaşılabilir URL: `/portfolio?view=acil-bugs-mobile`

### G.2 Pinned Items
- Sık kullanılan proje/senaryo/rapor pin'lenebilir
- Sidebar'da "📌 Pinned" bölümü
- Hızlı erişim için Cmd+1, Cmd+2... kısayolları

### G.3 Recently Viewed
- Header'da clock ikonu → son 10 sayfa dropdown
- Otomatik kayıt, tıklayınca dön

### G.4 User Preferences
**Dosya:** `apps/web/app/(dashboard)/profile/page.tsx` (genişlet)

- Tema: Dark / Light / Sistem
- Yoğunluk: Compact / Comfortable / Spacious
- Default landing: Aktivite / Portfolio / Son proje
- Klavye kısayolu profili: Vim / Default

---

## FAZ H — Performans & Scale (2-3 gün)

> 3157 proje var, 5K daha gelecek. Sayfa donmasın.

### H.1 Virtualization
**Dosya:** `apps/web/components/ui/virtual-list.tsx` (yeni)

- `@tanstack/react-virtual` entegrasyonu
- Portfolio liste görünümü → virtualized (60K satır da olsa akıcı)
- Senaryo listesi, runs listesi → virtualized

### H.2 Optimistic Updates
- Yeni proje oluştur → form gönderilir gönderilmez listede görünür
- Onayla butonu → durum hemen değişir, backend background'da
- Rollback: hata durumunda geri al + toast

### H.3 Smart Prefetching
- Sidebar nav linklerine hover → o sayfanın data'sı prefetch
- Proje kartı hover → o projenin scenarios endpoint prefetch
- Next.js router prefetch + TanStack Query prefetchQuery

### H.4 Image / Asset Optimizasyonu
- Logo SVG inline
- Avatar gradient'ler CSS-only (asset değil)
- Bundle size: 200KB altı target

---

## FAZ I — Onboarding & Empty States (1-2 gün)

> Boş ekran = kayıp kullanıcı.

### I.1 İllüstrasyonlar
**Klasör:** `apps/web/components/illustrations/`

- Boş portfolio: 📁 + "İlk projeyi oluştur"
- Boş senaryolar: 📝 + "AI ile senaryo üret"  
- Boş runs: ▶️ + "İlk koşunu başlat"
- Hata sayfası: 🤖 + "Üzgünüz, bu sayfa kayboldu"
- 404: animasyonlu astronot

Stil: Linear / Stripe tarzı geometrik, tek renkli, ürün marka rengi accent.

### I.2 Interactive Tour
**Library:** `intro.js` veya custom

- İlk girişte: 3 adımlı mini-tour (sidebar, command palette, AI)
- Her ürün ilk seçildiğinde: o ürünün özelliklerini tanıt
- "?" ikonu → context help

### I.3 Achievement / Progress
- Profil sayfasında: oluşturulan senaryo, çalıştırılan koşu sayıları
- Milestone bildirimleri: "🎉 100. senaryonu oluşturdun!"
- Streak counter: "7 gün üst üste test çalıştırdın 🔥"

---

## FAZ J — Mobile-First Responsive (2 gün)

> Şu an desktop-only. Mobile'da bozuk.

### J.1 Mobile Sidebar Yenile
- Drawer yerine **bottom sheet** (iOS tarzı)
- Hamburger yerine **bottom nav** (4 sekme)
- Swipe gesture'ları

### J.2 Touch-Optimized
- Tap target'lar min 44×44
- Swipe to delete (proje listede)
- Pull to refresh
- Long press menu

### J.3 PWA Setup
**Dosya:** `apps/web/public/manifest.json` + service worker

- Yüklenebilir uygulama
- Offline support (cache-first stratejisi)
- Push notification API

---

## FAZ K — Backend & Veri Modeli (3-4 gün, paralel)

> Frontend ne kadar şık olursa olsun, backend tamamlamalı.

### K.1 Project → ProductFamily Eşleme
**Dosya:** `backend/app/models/project.py` (yeni field)

```python
class Project(Base):
    ...
    product_family_id: Mapped[str | None]  # 'mobile', 'service', etc.
```

Migration + UI: yeni proje formuna ürün ailesi seçici, mevcut projelere bulk-assign.

### K.2 Tagging Sistemi
- Project, Scenario, Run'a tag'ler
- Tag bazlı arama, filtre

### K.3 Saved Views API
- `POST /api/v1/views` — kullanıcı görünüm kaydetsin
- Filtre kombinasyonları kalıcı

### K.4 WebSocket Endpoints
**Dosya:** `backend/app/ws_routes.py` (yeni)

- `/ws/runs/{project_id}` — koşu güncellemeleri
- `/ws/notifications/{user_id}`
- Redis pub/sub backend

### K.5 Audit Log Genişletme
- Her aksiyon log'lansın (create/update/delete)
- Activity feed enriched (kim, ne, ne zaman, nereden)

---

## FAZ L — Mikro-Animasyonlar & Polish (2 gün)

> Detaylar her şeydir. Linear bu yüzden Linear.

### L.1 Animasyon Library
**Library:** Framer Motion

- Sayfa transition: fade + subtle slide
- Modal: scale + opacity (spring)
- Toast: slide from right + spring
- Sidebar collapse: width transition smooth
- Card hover: lift (shadow + translateY -2px)

### L.2 Micro-interactions
- Button press: scale 0.98 (haptic feel)
- Switch toggle: spring physics
- Progress bar: shimmer effect
- Loading: pulse senkron, gradient sweep

### L.3 Sound (opsiyonel)
- Başarı: ince chime
- Hata: subtle thud
- Bildirim: pluck
- Settings'te toggle

---

## FAZ M — Erişilebilirlik (A11y) Tam Geçiş (1-2 gün)

> Sadece güzel değil, **herkes için** kullanılabilir.

- Tüm interactive element keyboard navigable
- ARIA labels tam
- Focus ring tutarlı (`focus-visible:ring-2 ring-blue-500`)
- Screen reader test (VoiceOver, NVDA)
- Renk kontrastı WCAG AA min
- Reduce motion media query desteği
- Skip-to-content (zaten var, genelle)

---

## Öncelik Sırası

```
HAFTA 1-2 (Temel)
├─ FAZ A — Design Tokens & Component Library     [3-4 gün] 🔥 KRİTİK
├─ FAZ B — Per-Ürün Tema                          [2 gün]
└─ FAZ C — Command Palette                        [2-3 gün] 🔥 YÜKSEK ETKİ

HAFTA 3 (Akıl)  
├─ FAZ D — AI-First UX                            [3-4 gün] 🔥 DİFERANSİATÖR
└─ FAZ E — Real-time                              [2-3 gün]

HAFTA 4 (Görsel)
├─ FAZ F — Veri Viz                               [3-4 gün]
└─ FAZ L — Mikro-animasyonlar                     [2 gün]

HAFTA 5 (Kullanıcı)
├─ FAZ G — Personalization                        [2 gün]
├─ FAZ H — Performans                             [2-3 gün]
├─ FAZ I — Onboarding                             [1-2 gün]
└─ FAZ M — A11y                                   [1-2 gün]

HAFTA 6 (Mobil & Backend)
├─ FAZ J — Mobile/PWA                             [2 gün]
└─ FAZ K — Backend Genişletme  (paralel)          [3-4 gün]

──────────────────────────────────────────────────
TOPLAM: 5-6 hafta tek developer (ya da 2-3 hafta 2 dev)
```

---

## Teknik Eklenecek Bağımlılıklar

```json
{
  "framer-motion": "^11.0.0",        // Animasyonlar
  "cmdk": "^1.0.0",                  // Command palette
  "@tanstack/react-virtual": "^3.0", // Virtualization
  "@radix-ui/react-tooltip": "^1.0", // Erişilebilir tooltip
  "@radix-ui/react-popover": "^1.0", // Popover/Combobox
  "@radix-ui/react-dialog": "^1.0",  // Modal/Sheet
  "recharts": "^2.10",               // Grafikler
  "fuzzysort": "^3.0",               // Fuzzy search
  "intro.js": "^7.0"                 // Onboarding tour (opsiyonel)
}
```

Bundle artışı: ~80-120KB gzip. Performans için tree-shaking + dynamic import.

---

## Başarı Kriterleri

| Metrik | Şu an | Hedef |
|--------|-------|-------|
| **First Paint** | ~1.2s | < 600ms |
| **TTI** | ~2.5s | < 1.2s |
| **Lighthouse Performance** | 70 | 95+ |
| **Lighthouse Accessibility** | 85 | 100 |
| **Klavye-only kullanılabilirlik** | %30 | %100 |
| **Mobile usability** | %20 | %95 |
| **Sidebar nav derinliği** | 2 | 1 (Cortex paritesi ✓) |
| **Animasyon yumuşaklığı** | 30fps | 60fps sabit |
| **Sayfa başına bundle** | 350KB | 200KB |
| **AI yanıt süresi** | 8-15s | < 3s ilk token |

---

## Sonuç: Nereye Varıyoruz

**Şu an**: Cortex'e eşit, çalışır mimari.

**Bu plan sonrası**: 
- Linear seviye **klavye odaklı** UX
- Stripe seviye **veri görselleştirme**
- Notion seviye **flexibility & personalization**
- Vercel seviye **performans & polish**
- Cortex'in **2-3 katı kapasiteli** AI entegrasyonu

Sadece "test platformu" değil, **AI-native QA operasyon merkezi**.

---

## Bir Sonraki Adım

Hangi faz ile başlayalım? Önerim:
1. **FAZ A** (Design Tokens) — diğer her şeyin temeli
2. **FAZ C** (Command Palette) — anında "vay be" etkisi
3. **FAZ B** (Per-Ürün Tema) — görsel kimliği netleştirir

Bu üçünü ilk hafta bitirebiliriz, sonrası ivmeyle gider.
