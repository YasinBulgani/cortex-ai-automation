# PLAN — Ürün Landing Sayfaları (Mobile Seviyesi+)

> **Status:** Draft v2.0 — hyper-detailed
> **Owner:** TBD
> **Reviewers:** Design, Frontend, Backend, QA, Product
> **Last update:** 2026-05-15
> **Hedef:** 7 ürün için Mobile sayfası **kalitesinin 1.5x üstünde**, üretim-hazır landing sayfaları
> **Mevcut baseline:** `MobileProductPage.tsx` — 716 satır, 8 bölüm, 5/10 → 9/10 paritesi
> **Gerçek tahmin:** **44 efektif gün** (1 dev) / **24 gün** (2 dev paralel)

---

## İÇİNDEKİLER

0. [Glossary & Bağlam](#0-glossary--bağlam)
1. [Faz 0 — Altyapı](#faz-0--ortak-altyapı-4-gün)
2. [Faz 1 — Neurex One](#faz-1--neurex-one--mission-control-5-gün)
3. [Faz 2 — Neurex Studio](#faz-2--neurex-studio--story-workshop-5-gün)
4. [Faz 3 — Neurex Service](#faz-3--neurex-service--api-ops-bridge-6-gün)
5. [Faz 4 — Neurex Web](#faz-4--neurex-web--browser-lab-5-gün)
6. [Faz 5 — Neurex Data](#faz-5--neurex-data--data-foundry-5-gün)
7. [Faz 6 — Neurex Intelligence](#faz-6--neurex-intelligence--neural-cortex-6-gün)
8. [Faz 7 — Neurex Code](#faz-7--neurex-code--forensic-lab-5-gün)
9. [Faz 8 — Polisaj](#faz-8--polisaj-3-gün)
10. [Faz 9 — Test & Rollout](#faz-9--test--rollout-3-gün)
11. [Cross-cutting standartlar](#11-cross-cutting-standartlar)
12. [Risk matrisi](#12-risk-matrisi)
13. [Başarı metriği](#13-başarı-metriği)
14. [Operasyonel ek](#14-operasyonel-ek)

---

## 0. GLOSSARY & BAĞLAM

### Terimler
| Terim | Açıklama |
|---|---|
| **Hero** | Sayfanın en üst bölümü; her ürünün karakteristik görselleştirmesi |
| **LiveStatsBar** | 6-8 metrik + sparkline + delta % içeren yatay bar |
| **AiInsight** | LLM tarafından üretilen aksiyon-odaklı içgörü kartı |
| **Brand glow** | Brand renginde 30% opacity shadow (kart hover'da) |
| **Stagger** | Çocuk elementlerin sırayla 50ms gecikmeli görünmesi |
| **SWR** | Stale-while-revalidate — cache verisini göster, arka planda yenile |
| **Telemetry** | Real-time + son 24h özet veri (sayım, latency, hata) |

### Bağımlılık ağacı
```
Faz 0 (altyapı)
  ├── Faz 1 (One)         → Faz 8 (polisaj)
  ├── Faz 2 (Studio)      → Faz 8
  ├── Faz 3 (Service)     → Faz 8
  ├── Faz 4 (Web)         → Faz 8
  ├── Faz 5 (Data)        → Faz 8
  ├── Faz 6 (Intelligence)→ Faz 8
  └── Faz 7 (Code)        → Faz 8
                              └── Faz 9 (test+rollout)
```

### Dosya konvansiyonları
- Page component: `apps/web/components/products/{Pascal}ProductPage.tsx`
- Alt component: `apps/web/components/products/{kebab}/{Pascal}.tsx`
- Mock: `apps/web/components/products/{kebab}/_mock.ts`
- Tip: `apps/web/components/products/{kebab}/_types.ts`
- Test: `tests/visual/products/{kebab}.spec.ts`

### Takım sözleşmeleri (zorunlu)
- Tüm pages **client component** (`"use client"`) — interaktiflik gerek
- Tüm fetch'ler `apiFetch` üzerinden (kimlik doğrulama otomatik)
- Demo data fallback **zorunlu** — backend yokken sayfa çalışsın
- Brand color **sadece** `PRODUCT_BRAND` map'inden — hardcode yasak
- Animasyonlar `prefers-reduced-motion` respect etmeli
- Tüm metinler **Türkçe** (kullanıcı tercihi)
- Comment yok (sadece WHY non-obvious'sa)

---

## FAZ 0 — ORTAK ALTYAPI (4 gün)

> **Amaç:** Aynı kodu 7 kere yazmamak. Bütün ürün sayfalarının paylaşacağı temel.

### Gün 0.1 (8h) — Tip sistemi + brand map

#### 0.1.1 Brand renk haritası
**Dosya:** `apps/web/lib/products/brand.ts` (yeni)

```typescript
import type { ProductFamilyId } from "@/lib/product";

export type ProductBrand = {
  primary: string;              // tailwind base color (e.g. "indigo")
  primaryHex: string;           // #6366f1 — chart libs için
  gradient: string;             // tailwind class: "from-X to-Y"
  glow: string;                 // tailwind shadow class
  ring: string;                 // focus ring class
  bg: string;                   // tinted background (5% opacity)
  border: string;               // tinted border (20% opacity)
  text: string;                 // tinted text
  brandName: string;            // display name (Intelligence → "Neurex AI")
  iconKey: string;              // lucide icon name (e.g. "Globe", "Brain")
  badgeVariant: "core" | "active" | "beta" | "embedded";
};

export const PRODUCT_BRAND: Record<ProductFamilyId, ProductBrand> = {
  one: {
    primary: "indigo",
    primaryHex: "#6366f1",
    gradient: "from-indigo-500 to-blue-500",
    glow: "shadow-indigo-500/30",
    ring: "ring-indigo-400/50",
    bg: "bg-indigo-500/5",
    border: "border-indigo-500/20",
    text: "text-indigo-300",
    brandName: "Neurex One",
    iconKey: "LayoutDashboard",
    badgeVariant: "core",
  },
  studio: {
    primary: "violet", primaryHex: "#8b5cf6",
    gradient: "from-violet-500 to-purple-600", glow: "shadow-violet-500/30",
    ring: "ring-violet-400/50", bg: "bg-violet-500/5",
    border: "border-violet-500/20", text: "text-violet-300",
    brandName: "Neurex Studio", iconKey: "Palette", badgeVariant: "active",
  },
  service: {
    primary: "sky", primaryHex: "#0ea5e9",
    gradient: "from-sky-400 to-cyan-500", glow: "shadow-sky-500/30",
    ring: "ring-sky-400/50", bg: "bg-sky-500/5",
    border: "border-sky-500/20", text: "text-sky-300",
    brandName: "Neurex Service", iconKey: "Server", badgeVariant: "active",
  },
  web: {
    primary: "emerald", primaryHex: "#10b981",
    gradient: "from-emerald-500 to-teal-500", glow: "shadow-emerald-500/30",
    ring: "ring-emerald-400/50", bg: "bg-emerald-500/5",
    border: "border-emerald-500/20", text: "text-emerald-300",
    brandName: "Neurex Web", iconKey: "Globe", badgeVariant: "active",
  },
  mobile: {
    primary: "rose", primaryHex: "#f43f5e",
    gradient: "from-rose-500 to-pink-500", glow: "shadow-rose-500/30",
    ring: "ring-rose-400/50", bg: "bg-rose-500/5",
    border: "border-rose-500/20", text: "text-rose-300",
    brandName: "Neurex Mobile", iconKey: "Smartphone", badgeVariant: "beta",
  },
  data: {
    primary: "amber", primaryHex: "#f59e0b",
    gradient: "from-amber-500 to-orange-500", glow: "shadow-amber-500/30",
    ring: "ring-amber-400/50", bg: "bg-amber-500/5",
    border: "border-amber-500/20", text: "text-amber-300",
    brandName: "Neurex Data", iconKey: "Database", badgeVariant: "active",
  },
  intelligence: {
    primary: "fuchsia", primaryHex: "#d946ef",
    gradient: "from-fuchsia-500 to-pink-500", glow: "shadow-fuchsia-500/30",
    ring: "ring-fuchsia-400/50", bg: "bg-fuchsia-500/5",
    border: "border-fuchsia-500/20", text: "text-fuchsia-300",
    brandName: "Neurex AI", iconKey: "Brain", badgeVariant: "embedded",
  },
  "nexus-code": {
    primary: "cyan", primaryHex: "#06b6d4",
    gradient: "from-cyan-500 to-teal-400", glow: "shadow-cyan-500/30",
    ring: "ring-cyan-400/50", bg: "bg-cyan-500/5",
    border: "border-cyan-500/20", text: "text-cyan-300",
    brandName: "Neurex Code", iconKey: "Code2", badgeVariant: "beta",
  },
};

export const BADGE_STYLES: Record<ProductBrand["badgeVariant"], string> = {
  core:     "border-blue-500/30 bg-blue-500/10 text-blue-300",
  active:   "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  beta:     "border-amber-500/30 bg-amber-500/10 text-amber-300",
  embedded: "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-300",
};
```

#### 0.1.2 Telemetry tip dosyası
**Dosya:** `apps/web/lib/products/telemetry-types.ts` (yeni)

```typescript
export type Severity = "info" | "success" | "warning" | "error";
export type Trend = "up" | "down" | "flat";

export interface ProductLiveStat {
  key: string;                    // "scenarios_total"
  label: string;                  // "Toplam Senaryo"
  value: number | string;
  unit?: string;                  // "ms", "%", "$"
  delta?: number;                 // % change vs last period
  deltaLabel?: string;            // "son 7 gün"
  trend?: Trend;
  target?: number;                // hedef değer (varsa progress bar)
  sparkline?: number[];           // 7-30 nokta
  severity?: Severity;
}

export interface AiInsight {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  category: string;
  ctaLabel?: string;
  ctaHref?: string;
  createdAt: string;              // ISO
  confidence?: number;            // 0-1
}

export interface ActivityEvent {
  id: string;
  ts: string;                     // ISO
  actor: { name: string; avatar?: string };
  verb: string;                   // "created", "updated", "ran"
  object: string;                 // "scenario", "run", "session"
  objectName: string;
  href?: string;
}

export interface OnboardingStep {
  id: string;
  label: string;
  description?: string;
  done: boolean;
  href?: string;
}

export interface ProductTelemetry {
  productId: string;
  stats: ProductLiveStat[];
  aiInsights: AiInsight[];
  recentActivity: ActivityEvent[];
  onboarding: OnboardingStep[];
  lastUpdated: string;
}
```

**Süre:** 4h (yazma + test)

#### 0.1.3 Routing güncellemesi
**Dosya:** `apps/web/app/(dashboard)/products/[productId]/page.tsx`

```tsx
import { notFound } from "next/navigation";
import { isValidProductFamilyId, type ProductFamilyId } from "@/lib/product";
import { OneProductPage } from "@/components/products/OneProductPage";
import { StudioProductPage } from "@/components/products/StudioProductPage";
import { ServiceProductPage } from "@/components/products/ServiceProductPage";
import { WebProductPage } from "@/components/products/WebProductPage";
import { MobileProductPage } from "@/components/products/MobileProductPage";
import { DataProductPage } from "@/components/products/DataProductPage";
import { IntelligenceProductPage } from "@/components/products/IntelligenceProductPage";
import { NexusCodeProductPage } from "@/components/products/NexusCodeProductPage";

const PAGE_MAP: Record<ProductFamilyId, React.ComponentType> = {
  one: OneProductPage,
  studio: StudioProductPage,
  service: ServiceProductPage,
  web: WebProductPage,
  mobile: MobileProductPage,
  data: DataProductPage,
  intelligence: IntelligenceProductPage,
  "nexus-code": NexusCodeProductPage,
};

export default function ProductPage({ params }: { params: { productId: string } }) {
  if (!isValidProductFamilyId(params.productId)) notFound();
  const Component = PAGE_MAP[params.productId as ProductFamilyId];
  return <Component />;
}
```

**Süre:** 30dk + iskelet stub'larla (her component "Yapım aşamasında" placeholder olarak başlar)

---

### Gün 0.2 (8h) — useProductTelemetry hook + paylaşılan widget'lar

#### 0.2.1 Hook
**Dosya:** `apps/web/lib/products/useProductTelemetry.ts`

```typescript
"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import type { ProductFamilyId } from "@/lib/product";
import type { ProductTelemetry } from "./telemetry-types";
import { getDemoTelemetry } from "./demo-data";

const POLL_INTERVAL_MS = 60_000;
const STALE_AFTER_MS = 30_000;

export function useProductTelemetry(productId: ProductFamilyId): {
  telemetry: ProductTelemetry | null;
  loading: boolean;
  error: Error | null;
  refresh: () => void;
  isDemo: boolean;
} {
  const [telemetry, setTelemetry] = useState<ProductTelemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isDemo, setIsDemo] = useState(false);

  const fetch = useCallback(async () => {
    try {
      const data = await apiFetch<ProductTelemetry>(`/api/v1/products/${productId}/telemetry`);
      setTelemetry(data);
      setIsDemo(false);
      setError(null);
    } catch (err) {
      setTelemetry(getDemoTelemetry(productId));
      setIsDemo(true);
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    fetch();
    const t = setInterval(fetch, POLL_INTERVAL_MS);
    return () => clearInterval(t);
  }, [fetch]);

  return { telemetry, loading, error, refresh: fetch, isDemo };
}
```

#### 0.2.2 Demo data factory
**Dosya:** `apps/web/lib/products/demo-data.ts`

Her ürün için `getDemoTelemetry(productId)` döndüren factory. Sayısal değerler `productId` hash'inden seed'lenir → tutarlı ama farklı.

#### 0.2.3 5 paylaşılan widget
**Dizin:** `apps/web/components/products/_shared/`

##### `ProductHero.tsx`
```typescript
interface Props {
  productId: ProductFamilyId;
  title: string;
  description: string;
  badgeText: string;
  ctaPrimary: { label: string; href?: string; onClick?: () => void };
  ctaSecondary?: { label: string; href?: string; onClick?: () => void };
  visualization: React.ReactNode;   // ürüne özel SVG/canvas
  liveDot?: boolean;                // canlı veri göstergesi
}
```

Layout:
```
┌──────────────────────────────────────────────────────┐
│ [Brand Badge] [Live Dot 🟢]                          │
│                                                       │
│  Title (3xl bold)                                    │
│  Description (slate-400)                             │
│                                                       │
│  [Primary CTA] [Secondary CTA]      [Visualization]  │
└──────────────────────────────────────────────────────┘
```

##### `LiveStatsBar.tsx`
```typescript
interface Props {
  productId: ProductFamilyId;
  stats: ProductLiveStat[];          // 6-8 element
  loading?: boolean;
  cols?: 4 | 6 | 8;
}
```

Her stat:
- Üst sol: label (xs)
- Sağ: delta % + trend ok
- Orta: value (2xl) + unit
- Alt: sparkline (40px height) — brand color
- Hover: tooltip "son 7 gün: avg X, max Y"

##### `AiInsightFeed.tsx`
```typescript
interface Props {
  productId: ProductFamilyId;
  insights: AiInsight[];
  maxItems?: number;                 // default 5
  onDismiss?: (id: string) => void;
  onAction?: (insight: AiInsight) => void;
}
```

Her insight kartı:
```
┌─────────────────────────────────────────┐
│ [Severity icon] Title          [×]     │
│ Description (slate-300, 2 satır max)    │
│ [Category badge] [Confidence %]         │
│                            [CTA →]      │
└─────────────────────────────────────────┘
```

##### `RecentActivity.tsx`
```typescript
interface Props {
  events: ActivityEvent[];
  maxItems?: number;                 // default 20
  showAvatars?: boolean;
  realTime?: boolean;                // pulse animation
}
```

##### `OnboardingChecklist.tsx`
```typescript
interface Props {
  steps: OnboardingStep[];
  productId: ProductFamilyId;
  onStepToggle?: (id: string) => void;
}
```

Layout: 3-5 adım, her birinde checkbox + label + ikon + "Başla" link. Üstte "0/5 tamamlandı" progress bar (brand color).

**Süre:** 6h (5 widget × 1h, + entegrasyon test)

---

### Gün 0.3 (8h) — Backend stub + storybook

#### 0.3.1 Backend telemetry endpoint
**Dosya:** `backend/app/routes/product_telemetry_routes.py` (yeni)

```python
from fastapi import APIRouter, HTTPException
from app.schemas.product_telemetry import ProductTelemetry
from app.services.telemetry import get_product_telemetry

router = APIRouter(prefix="/api/v1/products", tags=["products"])

@router.get("/{product_id}/telemetry", response_model=ProductTelemetry)
async def get_telemetry(product_id: str):
    valid_ids = {"one", "studio", "service", "web", "mobile", "data", "intelligence", "nexus-code"}
    if product_id not in valid_ids:
        raise HTTPException(404, f"Unknown product: {product_id}")
    return await get_product_telemetry(product_id)
```

**Servis:** `backend/app/services/telemetry.py` — şu an stub mock döndürür, sonra gerçek metriklerle değiştirilir.

#### 0.3.2 Storybook (opsiyonel ama şiddetle önerilir)
- `npx storybook init`
- Her shared widget için `*.stories.tsx`
- States: default, loading, empty, error, with brand colors

**Süre:** 6h backend + 2h storybook

---

### Gün 0.4 (8h) — Polish & test

- 5 widget × 3 state (default, loading, empty) için unit test
- `useProductTelemetry` için MSW (mock service worker) ile integration test
- TypeScript strict pass (`npm run type-check`)
- Build temiz (`npm run build`)
- Routing değişikliği regresyon test (mevcut Mobile çalışıyor mu?)

### Faz 0 Acceptance Criteria
- [ ] `lib/products/brand.ts` 8 ürün için tam doldurulmuş
- [ ] `lib/products/telemetry-types.ts` 5 interface dışa aktarılmış
- [ ] `lib/products/useProductTelemetry.ts` SWR + 60s polling + demo fallback
- [ ] `lib/products/demo-data.ts` 8 ürün için seed'lenmiş demo telemetry
- [ ] 5 shared widget Storybook'ta görünüyor
- [ ] Backend `/api/v1/products/{id}/telemetry` 8 ürün için 200 OK döndürüyor
- [ ] Routing değişikliği `/products/mobile` regresyonu yok
- [ ] Build + type-check + lint temiz
- [ ] 7 ürün için iskelet placeholder (`<UnderConstruction />`) routing'de aktif

---

## FAZ 1 — NEUREX ONE — "Mission Control" (5 gün)

> **Persona:** QA Lead — sabah 9'da gelir, kahvesini içerken platformun nabzını görmek ister.
> **User Story:** "Bütün ürünler ve projelerin tek ekrandan sağlık + kullanım + sorun tespiti."
> **Brand:** indigo-500 → blue-500
> **Dosya:** `apps/web/components/products/OneProductPage.tsx` (~750 satır hedef)

### Sayfa wireframe (ASCII)

```
┌──────────────────────────────────────────────────────────────────┐
│ [Hero] Constellation Map (büyük)              [Live Stats Bar]   │
│  • 7 gezegen, animasyonlı veri akışı           6-8 metrik         │
│  • CTA: "Tüm ürünler" / "Sağlık raporu"                           │
├──────────────────────────────────────────────────────────────────┤
│ [Cross-Product Health Grid] 7×4                                   │
│ ┌──────┬───────┬─────────┬─────────┬─────────┐                   │
│ │ Ürün │ Servis│ Kullanım│ Hata %  │ SLA     │                   │
│ ├──────┼───────┼─────────┼─────────┼─────────┤                   │
│ │ One  │  🟢   │  ▮▮▮    │  0.2%   │ 99.9%   │                   │
│ │Studio│  🟢   │  ▮▮     │  1.8%   │ 99.5%   │                   │
│ │ ...  │  ...  │  ...    │  ...    │  ...    │                   │
│ └──────┴───────┴─────────┴─────────┴─────────┘                   │
├──────────────────────────────────────────────────────────────────┤
│ [License Forecast 60%]  [Top 10 Projects 40%]                    │
├──────────────────────────────────────────────────────────────────┤
│ [Integration Matrix grid 7 entegrasyon]                          │
├──────────────────────────────────────────────────────────────────┤
│ [AI Platform Brain]  [Audit Stream live]                         │
├──────────────────────────────────────────────────────────────────┤
│ [Onboarding Checklist]                                            │
└──────────────────────────────────────────────────────────────────┘
```

### Gün 1.1 (8h) — Hero + Constellation Map

#### 1.1.1 Veri yapısı
```typescript
interface PlanetNode {
  id: ProductFamilyId;
  name: string;
  brandHex: string;
  activity: number;          // 0-100, gezegen yarıçap çarpanı
  pulseRate: number;         // 60-200ms aralığı pulse
  position: { x: number; y: number };  // SVG koordinat (precomputed)
}

interface DataFlow {
  from: ProductFamilyId;
  to: ProductFamilyId;
  intensity: number;         // 0-1, partikül hızı
}
```

#### 1.1.2 ConstellationMap component
**Dosya:** `apps/web/components/products/one/ConstellationMap.tsx`

- SVG, 800×400 viewport
- 7 ürün gezegen + ortada "Neurex One" sun
- Pozisyon: `1+360deg/7` etrafında force-distributed
- Edge: 3 paralel chord per pair, animated `stroke-dashoffset`
- Pulse: `<animate attributeName="r" values="..." dur="${pulseRate}s" repeatCount="indefinite" />`
- Hover gezegen: tooltip portal (popover)

##### Tooltip içerik
```
┌─────────────────────────────────┐
│ Neurex Studio                    │
│ ─────────────────────────────── │
│ • 47 senaryo (24h)              │
│ • 12 koşu                       │
│ • %3.2 hata oranı               │
│ • [Ürünü aç →]                  │
└─────────────────────────────────┘
```

##### Reduced motion fallback
```css
@media (prefers-reduced-motion: reduce) {
  .pulse-animation { animation: none; }
  .data-flow { stroke-dasharray: none; }
}
```

#### 1.1.3 Hero entegrasyonu
- `<ProductHero>` shared widget kullan
- `visualization` slot'una `<ConstellationMap />` koy

**Süre:** 8h (4h SVG + 2h pulse + 2h tooltip + entegrasyon)

---

### Gün 1.2 (8h) — Live Stats + Health Grid

#### 1.2.1 Live Stats Bar (6 metrik)
| Key | Label | Hesaplama |
|---|---|---|
| `scenarios_total` | Toplam Senaryo | `SUM(scenarios) WHERE status != 'archived'` |
| `runs_7d` | Koşu (7 gün) | `COUNT(runs) WHERE created_at > NOW() - 7d` |
| `active_users_7d` | Aktif Kullanıcı | `DISTINCT user_id FROM activity WHERE ts > NOW()-7d` |
| `active_projects` | Aktif Proje | `COUNT(projects) WHERE last_activity > NOW()-30d` |
| `ai_calls_24h` | AI Çağrı (24h) | `SUM(ai_calls) WHERE ts > NOW()-1d` |
| `heal_count_7d` | Heal (7 gün) | `COUNT(heal_events) WHERE ts > NOW()-7d` |

Her stat için sparkline = son 7 günlük günlük seri.

#### 1.2.2 Cross-Product Health Grid
**Dosya:** `apps/web/components/products/one/HealthGrid.tsx`

```typescript
interface ProductHealthRow {
  productId: ProductFamilyId;
  service: "up" | "degraded" | "down";
  utilizationPct: number;          // 0-100
  errorRatePct: number;
  slaPct: number;
  trend7d: Trend;
}
```

Layout: tablo, satır hover'da bg highlight + sağ ok ikonu (tıklanır → ürün sayfası).

##### Hücre renk kodlama
- Servis: 🟢 up / 🟡 degraded / 🔴 down
- Kullanım: bar (0-50% slate, 50-80% emerald, 80-100% amber)
- Hata: < 1% emerald, 1-5% amber, > 5% red
- SLA: < 99% red, 99-99.5% amber, > 99.5% emerald

**Süre:** 8h

---

### Gün 1.3 (8h) — License Forecast + Top Projects + Integration Matrix

#### 1.3.1 License & Capacity Forecast
**Dosya:** `apps/web/components/products/one/LicenseForecast.tsx`

- Donut chart (recharts veya custom SVG): plan kullanım %
- Yan tarafta: "Pro plana geçmen 47 gün içinde" predictive text
- Linear regression: `lib/forecast.ts` → least-squares slope
- 30/60/90 gün tahmin sparkline (üç farklı renk)

#### 1.3.2 Top 10 Projects
**Dosya:** `apps/web/components/products/one/TopProjects.tsx`

Tablo:
| Proje | Ürünler | Son aktivite | Sağlık |
|---|---|---|---|
| Banking-2026 | [Studio][Service][Web][Data] | 5dk önce | 92 |
| Mobile-App-V3 | [Mobile][Web] | 1sa önce | 87 |
| ... | | | |

Sağlık skoru = composite (pass rate × 0.4 + heal success × 0.3 + activity × 0.3)

#### 1.3.3 Integration Matrix
**Dosya:** `apps/web/components/products/one/IntegrationMatrix.tsx`

Grid (3 kolon × 3 satır):
```
┌───────────┬───────────┬───────────┐
│  Jira     │  GitHub   │  Jenkins  │
│  🟢 5dk   │  🟢 1dk   │  🟡 23dk  │
│  3 hata   │  0 hata   │  12 hata  │
│ [Test ⚙]  │ [Test ⚙]  │ [Test ⚙]  │
├───────────┼───────────┼───────────┤
│  Slack    │  Sentry   │ Postgres  │
│  ...      │  ...      │  ...      │
└───────────┴───────────┴───────────┘
```

**Süre:** 8h

---

### Gün 1.4 (8h) — AI Brain + Audit Stream + Onboarding

#### 1.4.1 AI Platform Brain
- `<AiInsightFeed insights={...} />` shared widget
- 3-5 cross-product insight (mock):
  - "Web ürününde flaky senaryolar %12 arttı (son 7 gün)"
  - "Heal başarı oranı bu hafta %89 — hedef %85 üstünde 🎉"
  - "Mobile koşu süresi %18 azaldı — son optimizasyon işe yaramış"

#### 1.4.2 Audit Stream
- `<RecentActivity realTime />` shared widget
- WebSocket bağlantısı `/api/v1/ws/audit` (yoksa polling 5s)
- Yeni event geldiğinde slide-in animation (top'tan)

#### 1.4.3 Onboarding (yeni kullanıcı için)
5 adım:
1. ✅ Hesap oluştur
2. ☐ İlk projeyi yarat
3. ☐ Ürün gez (en az 3)
4. ☐ İlk senaryoyu yaz
5. ☐ Ekibi davet et

**Süre:** 8h

---

### Gün 1.5 (8h) — Polish + Test + Review

- Loading skeleton'lar
- Empty state'ler
- Responsive (mobile/tablet/desktop)
- A11y: tüm SVG'lere `aria-label`, keyboard nav
- Performance: React.memo + useMemo Constellation'da
- Visual regression test
- Code review + revisions
- Merge

### Faz 1 Acceptance
- [ ] 8 bölüm tam render < 2sn
- [ ] Constellation animasyonu 60fps Chrome'da
- [ ] Reduced motion mode respect
- [ ] Demo data ile API yokken çalışır
- [ ] Lighthouse: Performance ≥ 85, A11y ≥ 95
- [ ] Mobile viewport (375px) bozulmuyor
- [ ] TypeScript strict, lint temiz
- [ ] Visual regression baseline kaydedildi

---

## FAZ 2 — NEUREX STUDIO — "Story Workshop" (5 gün)

> **Persona:** Test Designer — gereksinimden senaryoya dönüşüm sorumlusu.
> **User Story:** "Gereksinim gör → AI ile senaryo üret → onayla → regresyona dahil et — tek sayfada."
> **Brand:** violet-500 → purple-600
> **Dosya:** `apps/web/components/products/StudioProductPage.tsx`

### Sayfa wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ [Hero] Coverage Wheel (donut)        [Live Stats Bar]            │
├──────────────────────────────────────────────────────────────────┤
│ [Requirement Flow Board — Kanban 5 kolon]    [AI Drawer ▶]      │
│  Gereksinim → Taslak → AI İncele → Onay → Regresyon              │
├──────────────────────────────────────────────────────────────────┤
│ [Coverage Heatmap 8×6]                                            │
├──────────────────────────────────────────────────────────────────┤
│ [Scenario DNA] [Regression Forecaster] [Pattern Library]         │
├──────────────────────────────────────────────────────────────────┤
│ [AI Insights] [Recent Activity]                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Gün 2.1 (8h) — Hero + Coverage Wheel

#### 2.1.1 Coverage Wheel
**Dosya:** `apps/web/components/products/studio/CoverageWheel.tsx`

```typescript
interface CoverageData {
  totalScenarios: number;
  coveredRequirements: number;
  totalRequirements: number;
  coveragePct: number;          // 0-100
  byPriority: { p0: number; p1: number; p2: number; p3: number };
}
```

- SVG donut, 280px outer / 200px inner
- Stroke = `coveragePct` * (2π × r)
- Animasyon: `stroke-dashoffset` 0'dan hedefe 1200ms
- Merkez: büyük yüzde + alt satır "237 / 300 senaryo"
- Hover ring segment'larında: priority breakdown tooltip

#### 2.1.2 Live Stats (6 metrik)
| Key | Label |
|---|---|
| `draft` | Taslak |
| `pending_review` | Onayda |
| `approved` | Onaylı |
| `in_regression` | Regresyonda |
| `skipped` | Skip |
| `created_this_week` | Bu Hafta |

**Süre:** 8h

---

### Gün 2.2 (8h) — Requirement Flow Board (Kanban)

#### 2.2.1 dnd-kit kurulumu
```bash
cd apps/web && npm install @dnd-kit/core @dnd-kit/sortable
```

#### 2.2.2 Kanban component
**Dosya:** `apps/web/components/products/studio/RequirementBoard.tsx`

```typescript
type ColumnId = "requirement" | "draft" | "ai_review" | "approval" | "regression";

interface RequirementCard {
  id: string;
  title: string;
  priority: "p0" | "p1" | "p2" | "p3";
  assignee?: { name: string; avatar?: string };
  estimatedHours?: number;
  scenarioCount?: number;
  column: ColumnId;
}
```

- 5 kolon, her biri scrollable (max-h-96)
- Drag & drop ile kolon değiştir
- Drop event → `PATCH /api/v1/studio/requirements/{id}` body `{ column: newCol }`
- Optimistic update + rollback
- Yeni kart ekleme: kolon başında "+ Yeni" button

##### Edge cases
- Aynı anda 2 kullanıcı drag → server `last_modified_at` check, conflict resolution
- Boş kolon: drop zone vurgu + "Buraya bırak" hint
- Mobile (<768px): kolon swipe ile yatay scroll

**Süre:** 8h

---

### Gün 2.3 (8h) — AI Drawer + Coverage Heatmap

#### 2.3.1 AI Senaryo Üretici Drawer
**Dosya:** `apps/web/components/products/studio/AiScenarioDrawer.tsx`

Sticky right edge:
- Collapsed: 60px wide, sadece ikon + count
- Expanded: 380px wide, animation 240ms

Içerik:
```
┌─────────────────────────────┐
│ [✨ AI Senaryo Üretici]  [×]│
│ ────────────────────────── │
│ [Input: "Mobil ödeme..."]  │
│ [Mode: Gherkin / Manuel]   │
│ [Generate ✨]               │
│                            │
│ ─── Çıktı (stream) ───     │
│ Feature: Ödeme akışı       │
│   Scenario: Başarılı       │
│     Given user...          │
│     When ...               │
│     Then ...               │
│                            │
│ [✓ Onayla] [✏ Düzenle]     │
│ [↻ Tekrar üret]            │
└─────────────────────────────┘
```

- Stream: `POST /api/generate-feature` (Engine port 5001)
- SSE veya fetch chunked response
- Token-by-token append (typewriter effect)

#### 2.3.2 Coverage Heatmap
**Dosya:** `apps/web/components/products/studio/CoverageHeatmap.tsx`

8×6 grid:
- Y axis: modüller (Login, Profile, Search, Cart, Checkout, Orders, Reports, Admin)
- X axis: risk seviyesi (Critical, High, Medium, Low, Edge, Performance)
- Hücre rengi: 0-25% kırmızı, 25-50% amber, 50-75% sky, 75-100% emerald
- Hover: tooltip "X senaryosu, %Y kapsam"
- Tıkla: ilgili senaryoları liste (drawer)

**Süre:** 8h

---

### Gün 2.4 (8h) — DNA Inspector + Regression Forecaster + Pattern Library

#### 2.4.1 Scenario DNA Inspector
**Dosya:** `apps/web/components/products/studio/ScenarioDna.tsx`

Sol panel: senaryo seçici (autocomplete)
Sağ panel: timeline
```
2026-04-01  📝 Created by Ali
2026-04-03  ✏ Edited by Veli (3 değişiklik)
2026-04-05  🤖 AI heal — locator değişti
2026-04-10  ▶ Run #47 PASSED (12.3s)
2026-04-12  ▶ Run #48 FAILED → AI tahminli sebep: "API timeout"
2026-04-13  ✏ Edited by Ali (timeout artırıldı)
2026-04-14  ▶ Run #49 PASSED
```

#### 2.4.2 Regression Forecaster
**Dosya:** `apps/web/components/products/studio/RegressionForecaster.tsx`

```typescript
interface RegressionPlan {
  scenarios: number;
  avgDurationSec: number;
  parallelism: number;
  estimatedTotalSec: number;
  riskScore: number;             // 0-100
  flakyCount: number;
}
```

Görselleştirme: bar (paralel sayısı slider), altta "Tahmini süre: 47dk" güncellenir.

#### 2.4.3 Pattern Library (kelime bulutu)
**Dosya:** `apps/web/components/products/studio/PatternLibrary.tsx`

D3 force-directed word cloud veya basit grid:
```
   Login(47x)    Search(31x)   Click(28x)
       AddToCart(22x)    Logout(18x)
   FillForm(15x)   Wait(12x)   Verify(45x)
```

- Font size = sqrt(usage)
- Tıkla → modal "Reusable component yarat?"

**Süre:** 8h

---

### Gün 2.5 (8h) — AI Insights + Recent Activity + Polish

- AI Insights feed (Studio-specific):
  - "Bu hafta yazılan 12 senaryonun 8'i daha önce yazılmış pattern'la benzer — pattern library'ye eklemek ister misin?"
  - "Coverage Heatmap'te 'Checkout × Critical' hücresi %32 — hedefin altında"
- Recent activity: kim hangi senaryoyu yarattı/değiştirdi
- Onboarding: "İlk gereksinimi import et" → "İlk senaryoyu yaz" → "İlk regresyonu çalıştır"

### Faz 2 Acceptance
- [ ] Coverage Wheel donut animasyonu 1200ms
- [ ] Kanban drag & drop + persist çalışıyor
- [ ] AI drawer streaming gerçek token-by-token
- [ ] Heatmap 8×6 responsive
- [ ] DNA timeline en az 5 event türü
- [ ] Regression forecaster slider canlı update
- [ ] Pattern library en az 8 pattern
- [ ] Lighthouse ≥ 85
- [ ] Sayfa < 800 satır (split component'ler)

---

## FAZ 3 — NEUREX SERVICE — "API Ops Bridge" (6 gün)

> **Persona:** Backend QA Engineer / SRE — API ekibi için.
> **User Story:** "Tüm endpoint'lerin sağlığı, contract drift, security posture, mock state — tek bakışta."
> **Brand:** sky-400 → cyan-500
> **Dosya:** `apps/web/components/products/ServiceProductPage.tsx`

### Sayfa wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ [Hero] Service Mesh Topology (canlı graph)                       │
├──────────────────────────────────────────────────────────────────┤
│ [Latency Heatstrip 24×3]              [Live Stats 8 metrik]      │
├──────────────────────────────────────────────────────────────────┤
│ [Chain Builder Preview] [Contract Drift Watch]                   │
├──────────────────────────────────────────────────────────────────┤
│ [Security Posture Radar] [Mock & Stub Garage]                   │
├──────────────────────────────────────────────────────────────────┤
│ [AI API Detective] [Recent Activity]                             │
└──────────────────────────────────────────────────────────────────┘
```

### Gün 3.1 (8h) — Service Mesh Topology

#### 3.1.1 react-flow kurulumu
```bash
cd apps/web && npm install reactflow
```

#### 3.1.2 ServiceMeshGraph component
**Dosya:** `apps/web/components/products/service/ServiceMeshGraph.tsx`

```typescript
interface MeshNode {
  id: string;                    // "GET /api/users"
  label: string;
  health: "healthy" | "degraded" | "down";
  rps: number;
  p95Ms: number;
  errorPct: number;
  position: { x: number; y: number };  // layout algo'dan
}

interface MeshEdge {
  source: string;
  target: string;
  callsPerMin: number;           // animation hızı
}
```

- Force-directed layout (`d3-force` veya `dagre`)
- Custom node component:
  - Health renk: green/amber/red border
  - Hover: detay popover (latency dağılımı, son istek)
- Custom edge: animated `@reactflow/edge-types` ile partikül akışı
- Zoom/pan support
- Filter bar üstte: "Sadece slow", "Sadece failing", "By service group"

##### Mini-map
Sağ alt köşe: react-flow built-in mini-map.

**Süre:** 8h

---

### Gün 3.2 (8h) — Latency Heatstrip + Live Stats

#### 3.2.1 LatencyHeatstrip
**Dosya:** `apps/web/components/products/service/LatencyHeatstrip.tsx`

```typescript
interface LatencyCell {
  hour: number;                  // 0-23
  percentile: "p50" | "p95" | "p99";
  valueMs: number;
}
```

24 (kolon) × 3 (satır) grid:
- Renk skala: 0-200ms green, 200-500ms emerald, 500-1000ms amber, 1000+ red
- Tıkla hücre → drawer: o saatteki en yavaş 10 endpoint
- Y axis label: p50/p95/p99
- X axis: saat (00, 06, 12, 18, 24)

#### 3.2.2 Live Stats (8 metrik)
1. RPS (current) — sparkline son 60 dk
2. Hata oranı % — son 24h
3. p95 latency
4. Contract drift sayısı (son hafta)
5. Chain test sayısı
6. Aktif mock sayısı
7. Flaky endpoint sayısı
8. Security alert (open)

**Süre:** 8h

---

### Gün 3.3 (8h) — Chain Builder + Contract Drift

#### 3.3.1 Chain Builder Preview
**Dosya:** `apps/web/components/products/service/ChainBuilderPreview.tsx`

Mini visual flow:
```
   ┌────────┐    ┌──────────┐    ┌─────────┐    ┌────────┐
   │ Login  │ →  │CreateOrd.│ →  │ Payment │ →  │ Refund │
   │ ✓ 200  │    │ ✓ 201    │    │ ⚠ 500   │    │ - skip │
   │ 145ms  │    │ 287ms    │    │ 1.2s    │    │        │
   └────────┘    └──────────┘    └─────────┘    └────────┘
```

- Node tıkla → ilgili endpoint detayı
- "+ Yeni chain" CTA → chain builder sayfasına
- Top 3 chain (en çok koşulan) gösterilsin

#### 3.3.2 Contract Drift Watch
**Dosya:** `apps/web/components/products/service/ContractDrift.tsx`

OpenAPI spec değişimleri timeline:
```
2026-05-10  PUT /orders şemasına `tax_amount` eklendi
            ⚠ 3 test güncellenmedi → [Düzelt]

2026-05-08  GET /users response: `email` artık nullable
            ✅ Tüm testler güncel

2026-05-07  DELETE /sessions/{id} → response code 204 → 200
            🔴 BREAKING CHANGE — 7 test fail edebilir
            [Diff göster] [Auto-update tests]
```

**Süre:** 8h

---

### Gün 3.4 (8h) — Security Radar + Mock Garage

#### 3.4.1 Security Posture Radar
**Dosya:** `apps/web/components/products/service/SecurityRadar.tsx`

OWASP API Top 10 (2023):
1. Broken Object Level Auth
2. Broken Authentication
3. Broken Object Property Level Auth
4. Unrestricted Resource Consumption
5. Broken Function Level Auth
6. Unrestricted Access to Sensitive Business Flows
7. Server Side Request Forgery
8. Security Misconfiguration
9. Improper Inventory Management
10. Unsafe Consumption of APIs

Radar chart (`recharts`):
- 10 axis, her axis 0-100 score
- 100 = secure, 0 = vulnerable
- Color: < 50 red, 50-80 amber, 80+ green
- Tıkla axis → o kategorideki açıklar drawer'da

#### 3.4.2 Mock & Stub Garage
**Dosya:** `apps/web/components/products/service/MockGarage.tsx`

Tablo:
| Mock | Endpoint | Kullanım (24h) | Son istek | Aksiyonlar |
|---|---|---|---|---|
| `mock_users_list` | `GET /users` | 1247 | 2dk önce | [⚙][🗑] |
| `mock_payment_fail` | `POST /payments` | 89 | 1sa önce | [⚙][🗑] |
| ... | | | | |

- "Yeni Mock" CTA → modal
- Filter: aktif / pasif / 14 gündür kullanılmamış (temizleme önerisi)

**Süre:** 8h

---

### Gün 3.5 (8h) — AI Detective + Activity + Polish

#### 3.5.1 AI API Detective
Insight'lar:
- "Endpoint `/api/payments` son 3 saatte hata oranı %2 → %40'a fırladı. Son deploy: 14:23. [İncele]"
- "Chain `Order Flow` 2. step (`Inventory check`) her seferinde +200ms gecikiyor — son hafta. [Trace bak]"
- "Mock `mock_legacy_v1` 47 gündür kullanılmadı. Silmeyi öner."

#### 3.5.2 Recent Activity
Service-specific event'ler:
- "Ali yeni chain `Refund Flow` oluşturdu"
- "Veli OWASP API#3 açığını kapattı"
- "Auto-heal: `/users` response schema değişti, 3 test güncellendi"

### Gün 3.6 (8h) — Polish + Test + Mesh perf

- Mesh graph 100+ node ile lag testi (virtualization gerekirse)
- Heatstrip mobile responsive
- Visual regression baseline
- Acceptance review

### Faz 3 Acceptance
- [ ] Mesh graph 50 node + 100 edge ile 60fps
- [ ] Heatstrip 24×3 hücre tıklanabilir
- [ ] Contract drift en az 3 örnek event
- [ ] Security radar 10 axis tam scale
- [ ] Mock garage CRUD
- [ ] AI Detective gerçek-veri benzeri insight (en az 5)
- [ ] Lighthouse ≥ 85

---

## FAZ 4 — NEUREX WEB — "Browser Lab" (5 gün)

> **Persona:** Web QA Engineer — locator, visual diff, a11y derdi.
> **Brand:** emerald-500 → teal-500
> **Dosya:** `apps/web/components/products/WebProductPage.tsx`

### Sayfa wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ [Hero] Browser Cockpit (6 thumbnail canlı)                       │
├──────────────────────────────────────────────────────────────────┤
│ [Live Stats 6 metrik]                                            │
├──────────────────────────────────────────────────────────────────┤
│ [Locator Strategy Tower] [Self-Healing Activity]                 │
├──────────────────────────────────────────────────────────────────┤
│ [Visual Regression Wall — 12 thumbnail grid]                     │
├──────────────────────────────────────────────────────────────────┤
│ [Accessibility Score] [Network HAR Sankey]                       │
├──────────────────────────────────────────────────────────────────┤
│ [Recorder Studio CTA]                                            │
└──────────────────────────────────────────────────────────────────┘
```

### Gün 4.1 (8h) — Browser Cockpit

```typescript
interface BrowserSession {
  id: string;
  browser: "chrome" | "firefox" | "safari" | "edge";
  viewport: { width: number; height: number; label: string };
  status: "idle" | "running" | "passed" | "failed";
  currentScenario?: string;
  progressPct?: number;
  thumbnailUrl?: string;        // base64 or url
  startedAt?: string;
}
```

6 thumbnail grid (3×2 desktop, 2×3 mobile):
- Browser ikon üstte
- Viewport label (Desktop / Tablet / Mobile)
- Mini progress bar (running ise)
- Status badge
- Hover: "Live VNC →" CTA

**Süre:** 8h

---

### Gün 4.2 (8h) — Locator Tower + Self-Healing Timeline

#### Locator Strategy Tower
Yatay stacked bar:
```
data-testid ████████████ 45%
aria-label  ██████ 22%
xpath       █████ 18%
text        ███ 10%
css         █ 5%
```

Sağda AI önerisi: "data-testid'e geçişle flakiness %18 düşer. [Otomatik dönüştür]"

#### Self-Healing Timeline
```
2026-05-15 14:32  🤖 `Login button` locator değişti
                   Eski: `button.btn-primary`
                   Yeni: `[data-testid="login-submit"]`
                   ✓ Otomatik kabul edildi (confidence %94)

2026-05-15 13:18  🤖 `Search input` placeholder değişti
                   ⚠ Manuel onay bekliyor [Onayla]
```

Heal rate sparkline son 30 gün üstte.

**Süre:** 8h

---

### Gün 4.3 (8h) — Visual Regression Wall

```typescript
interface VisualSnapshot {
  id: string;
  pageName: string;
  baselineUrl: string;
  currentUrl: string;
  diffPct: number;
  status: "passed" | "minor_diff" | "major_diff" | "new";
  timestamp: string;
}
```

12 snapshot grid (4×3):
- Thumbnail (300×200)
- Sayfa adı altta
- Diff varsa: kırmızı border + badge "%2.3"
- Hover: before/after slider component

**Slider:** `react-compare-image` veya custom CSS clip-path slider.

**Süre:** 8h

---

### Gün 4.4 (8h) — A11y Score + Network Sankey + Recorder

#### Accessibility Card
- WCAG AA compliance % donut
- Top 5 ihlal listesi:
  - Kontrast: 7 element
  - Alt text eksik: 12 image
  - Focus order yanlış: 3 sayfa
  - aria-label eksik: 5 button
  - Heading hiyerarşisi: 2 sayfa
- Her birinde "Auto-fix" CTA

#### Network HAR Sankey
- Domain → kategori (XHR/JS/CSS/Image/Font) → boyut
- `@nivo/sankey` veya custom SVG
- Toplam: "2.3MB indirildi, 47 request, 3 tracker bloklandı"

#### Recorder Studio
- Geniş kart: "Tarayıcıda kaydet → senaryo üret"
- Son 5 kayıt thumbnail (mini player)
- "Kaydı başlat" CTA → Chrome extension check

**Süre:** 8h

---

### Gün 4.5 (8h) — Polish + Test

### Faz 4 Acceptance
- [ ] 6 browser thumbnail responsive
- [ ] Visual diff slider drag çalışıyor
- [ ] Sankey 5+ domain düzgün
- [ ] Healing timeline son 50 event
- [ ] Lighthouse ≥ 85

---

## FAZ 5 — NEUREX DATA — "Data Foundry" (5 gün)

> **Persona:** Data QA / Privacy Officer
> **Brand:** amber-500 → orange-500
> **Dosya:** `apps/web/components/products/DataProductPage.tsx`

### Sayfa wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ [Hero] Data Particle Stream (kaynak → mask → test envanteri)    │
├──────────────────────────────────────────────────────────────────┤
│ [Live Stats 6]                                                   │
├──────────────────────────────────────────────────────────────────┤
│ [Schema Universe — 3D sphere] [PII Radar — 7-axis]              │
├──────────────────────────────────────────────────────────────────┤
│ [Synthetic Quality Gauges — 4 dial]                              │
├──────────────────────────────────────────────────────────────────┤
│ [Generation Recipes — 8-10 kart]                                 │
├──────────────────────────────────────────────────────────────────┤
│ [Data Lineage Tree] [Compliance Audit Log]                       │
└──────────────────────────────────────────────────────────────────┘
```

### Gün 5.1 (8h) — Particle Stream Hero

CSS keyframe animasyon:
- 3 kolon: Source (DB ikonları) → Mask (filter ikonları) → Test (file ikonları)
- Aralarda partiküller akar (SVG circle + `animate motion path`)
- Üstte canlı sayaç: "Saniyede 47 kayıt üretildi"
- Reduced motion: statik ok ile basitleştir

### Gün 5.2 (8h) — Schema Universe + PII Radar

#### Schema Universe
- 3D sphere effect (CSS `perspective` + `rotate`)
- Tablolar = small spheres on the sphere surface
- İlişkiler = line segments
- Hover: tablo şeması drawer (alanlar, tipler, PII flag)

#### PII Radar
7-axis radar (recharts):
- TCKN, IBAN, Email, Phone, Address, IP, CardNumber
- 2 ring: bulunma sıklığı (outer) + maskeleme oranı (inner)
- "Auto-mask all" CTA

### Gün 5.3 (8h) — Quality Gauges + Recipes

#### Quality Gauges (4 dial)
Her biri 0-100, renk kodlu:
1. Distributional Fidelity — gerçek dağılıma yakınlık
2. Referential Integrity — FK ilişkileri sağlam mı
3. Utility Score — test için kullanışlılık
4. Privacy Risk — re-identification riski (yüksek = kötü)

#### Generation Recipes
8-10 kart:
- "100 banka müşterisi" — TCKN + isim + IBAN + bakiye
- "5K sipariş + ödeme" — order + payment + shipping
- "GDPR-clean kullanıcı kümesi" — masked PII
- "Edge case'ler: boş, max length, special chars"
- "Locale: TR / EN / DE varyantı"
- "Stress test: 1M kayıt"
- "Bozuk veri (negative test)"
- "Compliance: KVKK örnek seti"

Her kartta: ikon, kayıt sayısı tahmini, tahmini süre, "Üret" CTA.

### Gün 5.4 (8h) — Lineage Tree + Compliance Log

#### Data Lineage Tree
```
Test Set: customers_v3
├── Source: production_db.users (snapshot 2026-05-01)
├── Transformations:
│   ├── mask_pii() — TCKN, IBAN, email
│   ├── shuffle_names()
│   └── randomize_dates()
├── Output: synthetic.customers_v3 (10000 rows)
├── Used in: 47 test runs (last 7 days)
└── Last accessed: 2dk önce by Ali
```

#### Compliance Audit Log
| Kim | Ne | Veri | GDPR Madde | Hash | Zaman |
|---|---|---|---|---|---|
| Ali | Export | customers_v3 (10K) | Art. 6 (consent) | sha256:abc... | 14:32 |
| Veli | Delete | user_id=123 | Art. 17 (silme) | sha256:def... | 13:18 |
| ... | | | | | |

### Gün 5.5 (8h) — Polish + Test

### Faz 5 Acceptance
- [ ] Particle stream 60fps
- [ ] Schema universe 20+ tablo lag yok
- [ ] PII radar 7-axis düzgün
- [ ] Recipe "üret" → toast + lineage'a düşsün
- [ ] Lighthouse ≥ 85

---

## FAZ 6 — NEUREX INTELLIGENCE — "Neural Cortex" (6 gün)

> **Persona:** AI Operations / Cost Manager
> **Brand:** fuchsia-500 → pink-500
> **Dosya:** `apps/web/components/products/IntelligenceProductPage.tsx`
> **Display name:** "Neurex AI" (sidebar'da kısaltılmış)

### Sayfa wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ [Hero] Living Brain — 3D nöron ağı                               │
├──────────────────────────────────────────────────────────────────┤
│ [Live Stats 8 metrik]                                            │
├──────────────────────────────────────────────────────────────────┤
│ [Provider Race Track 4 sparkline]                                │
├──────────────────────────────────────────────────────────────────┤
│ [LLM-as-Judge Studio]                                            │
├──────────────────────────────────────────────────────────────────┤
│ [Token Economy] [Prompt Performance Lab]                         │
├──────────────────────────────────────────────────────────────────┤
│ [AI Insights Feed] [Hallucination Watchtower]                   │
└──────────────────────────────────────────────────────────────────┘
```

### Gün 6.1 (8h) — Living Brain Hero

#### Karar: three.js mı CSS mi?
- three.js: 60-80KB bundle artışı, gerçek 3D, WebGL
- CSS-only: 0 bundle, 2D görünüm 3D illüzyonu

**Seçim:** Önce CSS-only ile MVP, kullanıcı feedback'inde upgrade.

#### CSS-only Living Brain
- 50 nöron (SVG circle), force-distributed
- Edges: 100 random pairs, low opacity
- Pulse animation: rastgele nöronlar pulse
- Color: provider'a göre (groq=blue, gemini=purple, ollama=green, g4f=gray)
- Hover nöron: popover "Last call: prompt='X', latency=234ms, tokens=145"

### Gün 6.2 (8h) — Live Stats + Provider Race

#### Live Stats (8)
| Key | Label |
|---|---|
| `calls_per_sec` | Saniyede Çağrı |
| `tokens_per_min` | Token/dk |
| `cost_24h_usd` | Maliyet (24h) |
| `latency_p95_ms` | Latency (p95) |
| `fallback_rate_pct` | Fallback Oranı |
| `cache_hit_pct` | Cache Hit |
| `hallucination_count` | Halüsinasyon (24h) |
| `active_models` | Aktif Model |

#### Provider Race Track
4 paralel sparkline (yarış pisti gibi):
- Y axis: latency (lower = better)
- X axis: son 5 dakika (real-time scroll)
- Renk: provider rengi
- Sağda canlı tablo:
  | Provider | p50 | p95 | $/1K req | Position |
  |---|---|---|---|---|
  | Groq | 89ms | 234ms | $0.05 | 🥇 |
  | Gemini | 145ms | 389ms | $0.12 | 🥈 |
  | ... | | | | |

### Gün 6.3 (8h) — Judge Studio + Token Economy

#### LLM-as-Judge Studio
Son 10 değerlendirme:
| Test | Output | Judge Score | Confidence | Action |
|---|---|---|---|---|
| Senaryo özet #47 | "Kullanıcı login..." | 0.92 / 1.0 | 87% | [👍][👎] |
| Bug report #23 | "Reproducible: ..." | 0.45 / 1.0 | 71% | [👍][👎] |

Click row → modal: full prompt + response + judge reasoning.

#### Token Economy
- Pie chart: hangi modül en çok token harcıyor
  - Studio (senaryo üretimi): 42%
  - Service (chain test): 23%
  - Web (locator önerisi): 18%
  - Code (analiz): 12%
  - Data (recipe): 5%
- Bütçe vs gerçekleşen bar:
  ```
  Bu ay: ████████░░░░ $47 / $100 (47%)
  ```

### Gün 6.4 (8h) — Prompt Lab + Insights + Hallucination

#### Prompt Performance Lab
Top 10 prompts tablosu:
| Prompt Adı | Kullanım | Başarı | Avg Token | Versiyonlar | A/B |
|---|---|---|---|---|---|
| `scenario_from_requirement` | 1247 | 87% | 542 | v3 | [Test] |
| `locator_suggestion` | 892 | 94% | 213 | v2 | [Test] |

A/B test başlat → modal:
- Variant A vs B
- Traffic split (50/50, 80/20)
- Success metric (judge score, user feedback, latency)

#### AI Insights Feed (animated stream)
Her 30sn'de yeni insight kartı slide-in:
- "Web'te `locator_suggestion` v2 başarısı %94 — v1'den %12 yüksek"
- "Studio'da `scenario_from_requirement` token tüketimi %18 arttı (son 7 gün) — prompt optimize edilebilir"

#### Hallucination Watchtower
Heatmap:
- X axis: model (groq-llama-70b, gemini-pro, ollama-mistral, g4f-gpt4)
- Y axis: kategori (locator önerisi, senaryo, bug summary, judge eval)
- Hücre: hallucination rate %

Hover: örnek incele "Model X 2026-05-14'te 'getElementById('login-btn')' önerdi ama element yok"

### Gün 6.5 (8h) — Polish + perf

### Gün 6.6 (8h) — Test + integration

### Faz 6 Acceptance
- [ ] Living Brain 60fps (50 nöron)
- [ ] Race track real-time update (5sn interval)
- [ ] Judge studio feedback POST gidiyor
- [ ] Token economy gerçek bütçe
- [ ] Hallucination heatmap tıklanabilir örnek
- [ ] Lighthouse ≥ 85

---

## FAZ 7 — NEUREX CODE — "Forensic Lab" (5 gün)

> **Persona:** Tech Lead — repo veya prod URL'i ver, derin analiz al.
> **Brand:** cyan-500 → teal-400
> **Dosya:** `apps/web/components/products/NexusCodeProductPage.tsx`

### Sayfa wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ [Hero] Analyzer Console (büyük input + mode chips)               │
├──────────────────────────────────────────────────────────────────┤
│ [Live Stats 6]                                                   │
├──────────────────────────────────────────────────────────────────┤
│ [Analysis Timeline — son 8 analiz card]                          │
├──────────────────────────────────────────────────────────────────┤
│ [DOM/Code Tree Explorer] [User Journey Map]                      │
├──────────────────────────────────────────────────────────────────┤
│ [Bug Prediction Heatmap] [Auto-Generated Test Pack]              │
├──────────────────────────────────────────────────────────────────┤
│ [Privacy Boundary Panel]                                         │
└──────────────────────────────────────────────────────────────────┘
```

### Gün 7.1 (8h) — Analyzer Console + Stats + Timeline

#### Analyzer Console
```
┌────────────────────────────────────────────────────────────────┐
│ ✨ Analyzer                                                    │
│ ┌────────────────────────────────────────────────────────┐    │
│ │ URL, repo path veya DOM yapıştır...                    │    │
│ │                                                        │    │
│ │                                                        │    │
│ └────────────────────────────────────────────────────────┘    │
│  Mode: [● Web] [○ Code] [○ Hybrid]                             │
│                                                                │
│  Local Ollama: 🟢 çevrimiçi (mistral:7b-instruct)              │
│                                                                │
│                                          [Analiz başlat ▶]    │
└────────────────────────────────────────────────────────────────┘
```

#### Live Stats (6)
- Bugün analiz / Üretilen senaryo / Bug tahmini / Ort. süre / Ollama TPS / Cache hit

#### Analysis Timeline
Son 8 analiz, 4×2 grid:
```
┌──────────┬──────────┬──────────┬──────────┐
│[Thumb]   │[Thumb]   │[Thumb]   │[Thumb]   │
│neurex.com│github/x  │bank.com  │repo/y    │
│47 bulgu  │12 bulgu  │89 bulgu  │5 bulgu   │
│✓ Bitti   │⏳ Sürüyor│⚠ Hata    │✓ Bitti   │
└──────────┴──────────┴──────────┴──────────┘
```

### Gün 7.2 (8h) — DOM Explorer + Journey Map

#### DOM/Code Tree Explorer
Sol panel: virtualized tree (`react-virtualized` veya `react-window`)
Sağ panel: seçili node detayı
- AI açıklaması ("Bu bir login form, 3 input alanı, submit button locator='[data-testid=submit]'")
- Risk skoru (0-100)
- "Test üret" CTA

#### Journey Map
Mermaid render:
```
graph LR
  A[Landing] --> B[Login]
  B --> C[Dashboard]
  C --> D[Profile]
  C --> E[Settings]
  C --> F[Logout]
```

Her edge'e click: "Bu yolculuk için test üret"

### Gün 7.3 (8h) — Bug Heatmap + Test Pack

#### Bug Prediction Heatmap
Code map:
- X axis: dosya tipi (component, route, util, model)
- Y axis: dosyalar (top 30 risk skoruna göre sıralı)
- Hücre: AI bug tahmin skoru
- Tıkla → kod parçası + öneri drawer

#### Auto-Generated Test Pack
Liste:
| Senaryo | Adımlar | Playwright | Gherkin | Aksiyon |
|---|---|---|---|---|
| Login flow happy path | 5 step | [Code] | [Gherkin] | [→ Studio] |
| Login wrong password | 4 step | [Code] | [Gherkin] | [→ Studio] |
| ... | | | | |

"Studio'ya gönder" → bulk export modal.

### Gün 7.4 (8h) — Privacy Boundary + AI Insights

#### Privacy Boundary Panel
```
┌──────────────────────────────────────────────────────────┐
│ 🔒 Privacy Boundary                                       │
│ ─────────────────────────────────────────────────────── │
│ Tüm analizler bu makinede çalıştı.                       │
│ Dış API'ye 0 byte gitti. ✓                               │
│                                                          │
│ Local Model: mistral:7b-instruct                         │
│ Quantization: Q4_K_M                                     │
│ RAM kullanımı: 4.2 GB                                    │
│                                                          │
│ Trafik logu (son 24h):                                  │
│   Outbound: 0 request                                   │
│   Inbound (local): 1,247 request                        │
└──────────────────────────────────────────────────────────┘
```

### Gün 7.5 (8h) — Polish + Test

### Faz 7 Acceptance
- [ ] Analyzer console URL → 3sn'de analiz başlar
- [ ] DOM tree 1000+ node lag yok (virtualized)
- [ ] Journey map mermaid render
- [ ] Bug heatmap tıklanabilir
- [ ] Test pack "Studio'ya gönder" gerçek POST
- [ ] Privacy panel 0 outbound vurgular
- [ ] Lighthouse ≥ 85

---

## FAZ 8 — POLİSAJ (3 gün)

### Gün 8.1 (8h) — Sidebar Product Picker yenileme
**Dosya:** `apps/web/components/AppShell.tsx` veya yeni `ProductPicker.tsx`

5 düzeltme:
1. Avatarları SVG ikona dönüştür (lucide: LayoutDashboard, Palette, Server, Globe, Smartphone, Database, Brain, Code2)
2. Brand color uygula (her circle background = brand color)
3. Badge renk kodu (`BADGE_STYLES` map'inden)
4. "Neurex Intelligence" → "Neurex AI" (`brandName` field)
5. Aktif sinyali sadeleştir (sadece sol pill, check kaldır)

Bonus:
- Hover lift (translateX 2px)
- Live ping (aktif ürünlerde yeşil dot)
- Quick stat ("47 senaryo • 12 koşu/gün") tagline altında
- Search bar üstte (8+ ürün için)

### Gün 8.2 (8h) — Animasyon katmanı
- `framer-motion` entegrasyonu (zaten varsa kullan)
- `<motion.div initial={...} animate={...} transition={...}>` her bölüme
- Stagger: 50ms gecikmeli çocuk animasyonu (`staggerChildren`)
- Hover lift component (kartlar 2px yukarı + brand glow)
- Page transition (route arası fade 200ms)
- `prefers-reduced-motion` respect

### Gün 8.3 (8h) — Empty/Loading + a11y final
- Her bölüm için skeleton component
- Empty state: "Henüz veri yok — şu adımı yap" CTA
- Tüm grafiklerin `aria-label` veya screen reader fallback
- Keyboard nav (Tab, Enter, Esc)
- Focus ring tutarlı (brand color)

---

## FAZ 9 — TEST & ROLLOUT (3 gün)

### Gün 9.1 (8h) — Test suite

#### 9.1.1 Visual regression
**Dosya:** `tests/visual/products/{id}.spec.ts` × 8

```typescript
import { test, expect } from "@playwright/test";

test.describe("Neurex Studio landing", () => {
  test("hero + stats render", async ({ page }) => {
    await page.goto("/products/studio");
    await page.waitForSelector('[data-testid="coverage-wheel"]');
    await expect(page).toHaveScreenshot("studio-hero.png", { maxDiffPixels: 100 });
  });

  test("kanban drag works", async ({ page }) => {
    await page.goto("/products/studio");
    const card = page.locator('[data-card-id="req-1"]');
    const targetColumn = page.locator('[data-column="ai_review"]');
    await card.dragTo(targetColumn);
    await expect(card).toBeVisible();
  });
});
```

#### 9.1.2 Smoke
- 8 sayfa açılıyor mu (200 status)
- Hero görünüyor mu
- LiveStatsBar 6+ stat
- AI Insights en az 1 kart

#### 9.1.3 A11y
```typescript
import { injectAxe, checkA11y } from "axe-playwright";

test("a11y violations zero", async ({ page }) => {
  await page.goto("/products/one");
  await injectAxe(page);
  await checkA11y(page, null, { detailedReport: true });
});
```

### Gün 9.2 (8h) — Performance + cross-browser

#### Lighthouse CI
- Her sayfa için: Performance ≥ 85, A11y ≥ 95, Best Practices ≥ 90, SEO ≥ 90
- Bundle size budget: each page chunk < 200KB gzip

#### Cross-browser
- Chrome, Firefox, Safari (desktop + mobile viewport)

### Gün 9.3 (8h) — Rollout strategy

#### Feature flag
```typescript
// lib/featureFlags.ts
export const NEW_PRODUCT_LANDINGS = process.env.NEXT_PUBLIC_NEW_LANDINGS === "true";
```

Routing:
```tsx
if (!NEW_PRODUCT_LANDINGS && productId !== "mobile") {
  return <ProductLandingPage productId={productId} />;
}
```

#### Rollout aşamaları
1. **Internal beta (1 gün):** ekip kullanır, feedback topla
2. **5% canary (2 gün):** rastgele %5 kullanıcı yeni sayfayı görür
3. **25% (3 gün):** genişlet
4. **100% (1 hafta sonra):** tam açık
5. **Eski `ProductLandingPage` deprecate (1 ay sonra):** sil

#### Monitoring
- Sentry: page-level error tracking
- PostHog/Mixpanel: page view, CTA click, time-on-page
- Lighthouse CI: her PR'da otomatik

---

## 11. CROSS-CUTTING STANDARTLAR

### 11.1 Tasarım sistemi
- Tüm border-radius: `rounded-xl` (12px)
- Tüm shadow: brand glow varsa `${brand.glow}`, yoksa `shadow-elevated`
- Tüm spacing: 4/6/8 multiplier (`gap-4`, `p-6`, `mb-8`)
- Tüm transition: `duration-base ease-out`

### 11.2 Tipografi
- Hero title: `text-3xl font-bold`
- Section title: `text-lg font-semibold`
- Stat value: `text-2xl font-bold`
- Body: `text-sm text-slate-300`
- Helper: `text-xs text-slate-500`

### 11.3 Renk kullanımı (brand vs functional)
- **Brand renkleri:** ürün kimliği, hero gradient, CTA primary, sparkline, ring
- **Functional:** semantic
  - Success: emerald
  - Warning: amber
  - Error: red
  - Info: blue

### 11.4 Component naming
- Page: `{Pascal}ProductPage`
- Sub-component: descriptive (`CoverageWheel`, not `Wheel1`)
- Hook: `use{Pascal}` (`useCoverageData`)
- Mock: `_mock.ts` (underscore = internal)
- Type: `_types.ts`

### 11.5 Performans bütçeleri
| Metrik | Hedef |
|---|---|
| LCP | < 2.5s |
| FID | < 100ms |
| CLS | < 0.1 |
| Bundle (page chunk) | < 200KB gzip |
| TTI | < 3.5s |
| Total JS execution | < 2s |

### 11.6 Erişilebilirlik
- WCAG 2.1 AA minimum
- Keyboard nav her interactive element
- ARIA labels her grafik/icon-only button
- Color contrast: text ≥ 4.5:1, UI ≥ 3:1
- Focus visible (brand color ring)
- Reduced motion mode

### 11.7 Internationalization (gelecek)
- Tüm string'ler `t()` helper'dan (i18n hazır olunca)
- Şu an Türkçe hardcode kabul, ama key isimleri tutarlı

### 11.8 Observability
- Her sayfa açılışında `analytics.page("product_landing", { product_id })`
- Her CTA tıklamada `analytics.track("product_cta_click", { product_id, cta_label })`
- Error boundary her sayfada — Sentry'e gönder

### 11.9 Test coverage
- Unit (component): ≥ 70% line coverage
- Integration (page): smoke + visual regression
- E2E: kritik akışlar (Kanban drag, AI streaming, drawer aç-kapa)

### 11.10 Code review checklist
- [ ] TypeScript strict
- [ ] Lint temiz
- [ ] Brand color hardcode yok (`PRODUCT_BRAND` map kullanılmış)
- [ ] Demo data fallback var
- [ ] Loading/empty/error state'ler
- [ ] Responsive (mobile/tablet/desktop)
- [ ] `prefers-reduced-motion` respect
- [ ] A11y: axe-playwright violations 0
- [ ] Visual regression baseline güncel
- [ ] Storybook story (varsa)

---

## 12. RİSK MATRİSİ

| # | Risk | Olasılık | Etki | Tedbir | Owner |
|---|---|---|---|---|---|
| 1 | Backend endpoint'leri hazır değil | Yüksek | Orta | Demo data fallback zorunlu | Frontend |
| 2 | three.js bundle büyütür | Orta | Düşük | CSS-only fallback hazırla | Frontend |
| 3 | react-flow lisans/maintenance | Düşük | Orta | MIT v11 kullan | Tech Lead |
| 4 | Performans düşer (büyük sayfalar) | Orta | Yüksek | React.memo, useMemo, virtualization | Frontend |
| 5 | Tasarım dağıtık olur (7 farklı dev) | Yüksek | Yüksek | Faz 0 shared widget'lar zorunlu, design review | Design |
| 6 | A11y unutulur | Orta | Yüksek | CI'da axe-playwright zorunlu | QA |
| 7 | i18n unutulur | Yüksek | Düşük | Şimdi Türkçe ok, gelecekte refactor | Product |
| 8 | Mobile'da hero animasyonları lag | Orta | Orta | Mobile'da disable veya simplified version | Frontend |
| 9 | Backend telemetri yavaş | Orta | Yüksek | Cache + 60s polling + SWR | Backend |
| 10 | Storybook yarım kalır | Yüksek | Düşük | Sadece shared widget'lar için zorunlu, page'ler opsiyonel | Frontend |
| 11 | Visual regression false-positive | Orta | Orta | `maxDiffPixels: 100` tolerance, brand color stable | QA |
| 12 | Feature flag rollback gerekirse | Düşük | Yüksek | Aşamalı rollout (5% → 25% → 100%) | DevOps |

---

## 13. BAŞARI METRİĞİ

### Sayısal hedefler
- [ ] 8 ürün sayfası, her biri ≥ 600 satır, ≥ 8 bölüm
- [ ] Mobile sayfasıyla görsel kalite paritesi (puan ≥ 8/10)
- [ ] Tüm sayfalar Lighthouse Performance ≥ 85, Accessibility ≥ 95
- [ ] Visual regression test suite (8 sayfa) yeşil
- [ ] Bundle size: page chunk < 200KB gzip
- [ ] Sidebar product picker yenilenmiş
- [ ] Sayfalar arası tutarlı animasyon dili (framer-motion stagger)
- [ ] 0 axe-playwright violation

### Kullanıcı-tabanlı metrik (rollout sonrası 30 gün)
- [ ] Product landing page view +50% (vs eski generic page)
- [ ] CTA click rate +30%
- [ ] Time-on-page +60%
- [ ] User satisfaction (NPS): + 10 puan
- [ ] Support ticket "ne yapacağımı bilmiyorum" tipinde -40%

---

## 14. OPERASYONEL EK

### 14.1 Toplantı kadansı
- **Daily:** 15dk standup (frontend + design)
- **Weekly:** 1h sprint review + planning
- **Faz sonu:** demo + retro (1h)

### 14.2 Karar kayıtları
Her büyük karar `docs/decisions/ADR-XXX-{title}.md` dosyasına:
- Bağlam
- Karar
- Sonuç
- Alternatifler
- Kararı veren

### 14.3 Branch strategy
- Faz başına bir branch: `feat/product-landings-faz-{N}-{slug}`
- Her ürün sayfası kendi PR (faz içinde split)
- Squash merge

### 14.4 Bağımlılık güncellemesi
| Paket | Versiyon | Faz | Sebep |
|---|---|---|---|
| `@dnd-kit/core` | ^6.x | 2 | Kanban |
| `@dnd-kit/sortable` | ^7.x | 2 | Kanban |
| `reactflow` | ^11.x | 3 | Service mesh |
| `recharts` | ^2.x | 3, 5, 6 | Radar, pie |
| `mermaid` | ^10.x | 7 | Journey map |
| `react-virtualized-auto-sizer` | ^1.x | 7 | Virtualized tree |
| `@nivo/sankey` | ^0.84.x | 4 | Network sankey |
| `react-compare-image` | ^3.x | 4 | Visual diff slider |
| `framer-motion` | ^11.x | 8 | Animasyon katmanı |

**Not:** Tüm paketler MIT, bundle impact öncesi `bundlephobia` ile kontrol.

### 14.5 Backend katkı
Frontend ekibi backend stub yazsın (Faz 0). Gerçek implementasyon backend ekibinde, asenkron paralel.

Endpoint listesi:
```
GET  /api/v1/products/{id}/telemetry
GET  /api/v1/platform/cross-product-health
GET  /api/v1/platform/integrations/status
GET  /api/v1/platform/forecast
GET  /api/v1/tspm/projects/{id}/coverage-summary
POST /api/v1/studio/generate-scenario        (Engine port 5001)
GET  /api/v1/studio/patterns/top
GET  /api/v1/service/mesh/topology
GET  /api/v1/service/latency/heatmap
GET  /api/v1/service/contract-drift
GET  /api/v1/service/security/owasp
GET  /api/v1/service/mocks
GET  /api/v1/web/browsers/active
GET  /api/v1/web/locator-stats
GET  /api/v1/web/visual-diff/recent
GET  /api/v1/web/accessibility/score
GET  /api/v1/web/network-har
GET  /api/v1/data/particle-stream            (SSE)
GET  /api/v1/data/pii-radar
GET  /api/v1/data/quality-gauges
GET  /api/v1/data/recipes
POST /api/v1/data/generate
GET  /api/v1/ai/telemetry/live               (SSE)
GET  /api/v1/ai/providers/race
GET  /api/v1/ai/judge/recent
GET  /api/v1/ai/tokens/breakdown
GET  /api/v1/ai/prompts/top
GET  /api/v1/ai/hallucinations/heatmap
POST /api/v1/code/analyze
GET  /api/v1/code/analyses/recent
GET  /api/v1/code/analyses/{id}/dom-tree
GET  /api/v1/code/analyses/{id}/journey
GET  /api/v1/code/analyses/{id}/bug-heatmap
GET  /api/v1/code/analyses/{id}/tests
GET  /api/v1/code/privacy/audit
WS   /api/v1/ws/audit                        (real-time)
```

### 14.6 Documentation
- Storybook: shared widget'lar
- `docs/PRODUCT_LANDINGS.md`: high-level architecture
- `docs/decisions/`: ADR'lar
- README per page (`components/products/{kebab}/README.md`): wireframe + API + edge cases

### 14.7 Onboarding new dev
Yeni geliştirici için:
1. Read `PLAN-PRODUCT-LANDINGS.md` (this file)
2. Read existing `MobileProductPage.tsx` (reference)
3. Read shared widgets (`components/products/_shared/`)
4. Try Storybook
5. Pick a faz from backlog

---

## 15. ZAMAN ÇİZELGESİ

### Senaryo A: 1 dev, full-time
```
Hafta 1:  Faz 0 (4 gün) + Faz 1 başlangıç (1 gün)
Hafta 2:  Faz 1 bitir + Faz 2
Hafta 3:  Faz 3 (6 gün)
Hafta 4:  Faz 4 (5 gün)
Hafta 5:  Faz 5 (5 gün)
Hafta 6:  Faz 6 (6 gün)
Hafta 7:  Faz 7 (5 gün) + Faz 8 başlangıç
Hafta 8:  Faz 8 bitir + Faz 9
Hafta 9:  Rollout + monitoring + bug fix
─────────────────────────────────────
TOPLAM: 9 hafta (~45 iş günü)
```

### Senaryo B: 2 dev paralel
```
Hafta 1:  Faz 0 (her iki dev birlikte)
Hafta 2:  Dev A: Faz 1 (One)        Dev B: Faz 2 (Studio)
Hafta 3:  Dev A: Faz 3 (Service)    Dev B: Faz 4 (Web)
Hafta 4:  Dev A: Faz 5 (Data)       Dev B: Faz 6 (AI) [biraz uzun, ek gün]
Hafta 5:  Dev A: Faz 7 (Code)       Dev B: Faz 6 bitir + Faz 8 başlangıç
Hafta 6:  Birlikte: Faz 8 (polisaj) + Faz 9 (test+rollout)
─────────────────────────────────────
TOPLAM: 6 hafta (~30 iş günü efektif)
```

### Senaryo C: agresif (3 dev)
```
Hafta 1:  Faz 0 (3 dev birlikte, 2 günde biter)
Hafta 1.5: Dev A: Faz 1, Dev B: Faz 2, Dev C: Faz 3
Hafta 3:  Dev A: Faz 4, Dev B: Faz 5, Dev C: Faz 6
Hafta 4.5: Dev A: Faz 7, Dev B+C: Faz 8 (polisaj)
Hafta 5:  Faz 9
─────────────────────────────────────
TOPLAM: 5 hafta (~25 iş günü efektif)
```

---

## 16. SON KONTROL LISTESI (TÜMÜ TAMAMLANDIĞINDA)

### Faz 0
- [ ] `lib/products/brand.ts` ✓
- [ ] `lib/products/telemetry-types.ts` ✓
- [ ] `lib/products/useProductTelemetry.ts` ✓
- [ ] `lib/products/demo-data.ts` ✓
- [ ] 5 shared widget ✓
- [ ] Backend stub endpoint ✓
- [ ] Routing güncellendi ✓
- [ ] Storybook (opsiyonel) ✓

### Faz 1-7 (her ürün için)
- [ ] Page component ≥ 600 satır
- [ ] 8 bölüm tamamlandı
- [ ] Brand color tutarlı
- [ ] Hero unique visualization
- [ ] LiveStatsBar 6+ metrik
- [ ] AiInsightFeed 3+ insight
- [ ] RecentActivity 10+ event
- [ ] OnboardingChecklist 3-5 step
- [ ] Loading/empty state'ler
- [ ] Responsive
- [ ] A11y compliant
- [ ] Visual regression baseline

### Faz 8
- [ ] Sidebar product picker yenilendi (5 düzeltme)
- [ ] framer-motion stagger
- [ ] Skeleton component'ler
- [ ] Reduced motion respect

### Faz 9
- [ ] Visual regression suite yeşil
- [ ] Smoke test pass
- [ ] axe-playwright 0 violation
- [ ] Lighthouse ≥ 85 her sayfa
- [ ] Cross-browser pass
- [ ] Feature flag setup
- [ ] Rollout plan dokümante
- [ ] Monitoring (Sentry + analytics) aktif

---

## SON SÖZ

Bu plan **opera benzeri** — her faz bir perde, her ürün bir sahne. Mobile sayfası şimdiki kalite çıtası; bu planın bitiminde **8 ürün de o seviyede VEYA üstünde** olacak.

Plan **kapsayıcı ama esnek**:
- Her faz bağımsız mergelenebilir
- Her ürün sayfası tek başına ship edilebilir
- Backend endpoint'leri yoksa demo data ile çalışır
- 1, 2 veya 3 dev senaryosu hazır

**Başlangıç noktası:** Faz 0 — 4 gün altyapı.
**İlk ship:** Faz 1 sonu (Neurex One) — 9 günde production'da.
**Tam bitiş:** ~45 gün (1 dev) / ~30 gün (2 dev) / ~25 gün (3 dev).

> _"Şu an Mobile yalnız. Bu planın sonunda 8 ürünün hepsi onun seviyesinde dönecek. Çığ değil — çığlık."_
