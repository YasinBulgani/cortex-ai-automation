# Neurex — Geliştirilmiş Tasarım Vizyonu

> 10 ajanlı tasarım denetimi sentezi · 2026-06-09 · feature/qa-system-bootstrap
> Kapsam: `apps/web` (Next.js 14 App Router, Tailwind, TS)

## 1. Yönetici Özeti — Genel Olgunluk: 58/100

Neurex *altyapı* olarak güçlü, *disiplin* olarak zayıf bir tasarım sistemine sahip. Token
mimarisi (288 satırlık `tokens.css`, 9 ürün teması, light/dark, WCAG media query'leri)
profesyonel bir SaaS çekirdeği kalitesinde — ancak bileşen katmanı bu temeli kullanmıyor.
Puanı 58'de tutan şey "sistemin var olması ama uygulanmaması" uçurumu.

| Eksen | Puan |
|---|---|
| Token altyapısı | ~80 |
| Bileşen tutarlılığı (enforcement) | ~45 |
| Erişilebilirlik (uygulanan) | ~40 |
| Responsive olgunluk | ~45 |
| Marka & motion | ~50 |

**6 bağımsız ajan aynı kök nedeni raporladı: token bypass salgını.**

## 2. Güçlü Yönler (sıfırdan inşa gerekmiyor)

- Kapsamlı token mimarisi (4 surface, 4 border, 8 shadow, semantic durum renkleri, z-index/radius/animation token'ları)
- `data-product` ile 9 ürün dinamik temalama — doğru tasarlanmış, ölçeklenebilir
- Radix UI primitive'leri (ARIA + focus otomasyonu)
- Inter + JetBrains Mono `next/font`, CVA başlangıcı, organize keyframe seti

## 3. Kritik Sorunlar (kanıtlı, tekilleştirilmiş)

### 🔴 P0
- **Renk-yalnız Pass/Fail göstergeleri** (WCAG 1.4.1, critical) — `qa/page.tsx:304`, `cases/page.tsx:278`, `defects/page.tsx:388`
- **798 kontrast hatası** — `text-gray/slate-500` açık zeminde ~2.9:1 (AA min 4.5); tanımlı `--fg-subtle` (5.2:1) kullanılmıyor
- **Token bypass** — inline hex (`#22c55e`), `bg-blue-600` ×19, `stroke='#7C3AED'`, 16 violet/indigo
- **`globals.css`'te 250 satırlık "rescue layer" anti-pattern** — `html:not(.dark) [class*="bg-slate-900"]` regex hack'leri + `z-index:99999 !important`

### 🟠 P1
QA modülü dark mode'da kırılıyor · 135+ butonda focus-visible yok · 456 kez 12px-altı font ·
modallarda ARIA/focus-trap yok · z-index token'ları (`--z-modal/toast`) hiç kullanılmıyor

### 🟡 P2
Buton hover tutarsızlığı (`brightness` vs semantic) · tipografi kaosu (`text-xs` ×561, heading
bileşeni yok) · tablet (768px) breakpoint boşluğu · 8px grid yok

## 4. Vizyon — Kuzey Yıldızı

> *Neurex, "token sistemi olan bir uygulama" olmaktan çıkıp "token sistemi tarafından
> yönetilen bir uygulama" olacak.*

- **Sıfır hardcoded renk** kuralı + ESLint `no-restricted-syntax` ile CI bloku → rescue layer silinebilir (`globals.css` <100 satır)
- **8px spacing token skalası**, z-index/blur/animation token'larının fiili kullanımı
- **Navigasyon:** header'da Ürün Pill (Linear pattern), tablet collapse, aktif state boost
- **Bileşen:** tek status kaynağı (CVA) → Toast/Badge/Alert aynı base; `<Heading>`, `FormField`, `IconButton`, Floating-UI tooltip; Storybook + Chromatic
- **Veri viz:** "spotlight → grid → detay" hiyerarşisi (Datadog), sparkline upgrade, relative time
- **A11y:** WCAG 2.1 AA *taban çizgisi* — renk+ikon durum, `@axe-core/playwright` CI'da
- **Marka:** monogram logo (token-driven), 4-tier motion skalası, `motion-reduce:` her animasyonda
- **Stratejik:** Style Dictionary + Figma Tokens Studio köprüsü

## 5. Yol Haritası (Etki × Efor)

| # | Girişim | Etki | Efor | Faz |
|---|---------|------|------|-----|
| 1 | Erişilebilir badge (ikon + renk) | High | S | Hızlı kazanım |
| 2 | Kontrast migrasyonu (`text-slate-*`→`text-fg-*`) | High | M | Hızlı kazanım |
| 3 | Focus-visible CVA base'de (135+) | High | M | Hızlı kazanım |
| 4 | Font min 12px (456) | High | M | Hızlı kazanım |
| 5 | Modal ARIA + focus trap (Radix kurulu) | High | S | Hızlı kazanım |
| 6 | Z-index token enforce + `99999` sil | Med | S | Hızlı kazanım |
| 7 | Toast/Badge/Alert tek status palette (CVA) | Med | S | Hızlı kazanım |
| 8 | `useTruncated` hook (title+aria-label) | High | S | Hızlı kazanım |
| 9 | Heading bileşeni (h1-h6 skala) | High | S | Hızlı kazanım |
| 10 | QA modülü token + dark refactor | High | M | Orta vade |
| 11 | Button variant genişletme + hover unify | High | M | Orta vade |
| 12 | 8px spacing token skalası + grid | High | M | Orta vade |
| 13 | Responsive `md:` taban (tablet) | High | M | Orta vade |
| 14 | Header Ürün Pill + tablet collapse | High | L | Orta vade |
| 15 | Dashboard spotlight→grid hiyerarşisi | High | M | Orta vade |
| 16 | Tooltip refactor (Floating UI) | High | L | Orta vade |
| 17 | FormField composite | High | M | Orta vade |
| 18 | `globals.css` rescue layer silme (token sonrası) | Med | M | Orta vade |
| 19 | 4-tier motion + micro-interaction | Med | M | Orta vade |
| 20 | `@axe-core/playwright` CI a11y testi | Med | M | Orta vade |
| 21 | Logo redesign (monogram + token) | High | M | Stratejik |
| 22 | Storybook + Chromatic regresyon | High | L | Stratejik |
| 23 | Style Dictionary + Figma Tokens Studio | High | XL | Stratejik |

## 6. Hızlı Kazanımlar (bu hafta)

1. Erişilebilir badge'ler (ikon + renk) → a11y ~%55→%92
2. Modal ARIA + focus trap (Radix zaten kurulu)
3. `<Heading>` bileşeni
4. Z-index token enforce + `99999 !important` sil
5. Toast tokenizasyonu (`bg-green-50` → `bg-success-subtle`)
6. `useTruncated` hook (400+ truncate)
7. `motion-reduce:animate-none` (skeleton/toast/onboarding)
8. Onboarding marka rengi token'a

**Stratejik not:** 1–9 puanı 58 → ~68'e taşır. Asıl sıçrama (80+, Linear/Vercel/Datadog
seviyesi), ESLint hardcoded-renk yasağı + rescue layer silinmesiyle gelir — o noktadan sonra
token sistemi *fiilen* yönetir hale gelir.
