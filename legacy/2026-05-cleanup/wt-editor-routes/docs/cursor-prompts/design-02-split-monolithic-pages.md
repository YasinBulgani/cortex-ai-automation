# Design Agent 2: Monolitik Sayfalari Parcala (5 sayfa, 6500+ satir)

## Cursor'a yapistir:

```
Sen bir senior frontend muhendisisin. BGTS bankacilik test platformunda
1000+ satirlik monolitik sayfalari kucuk, tekrar kullanilabilir bilesen parcalarina
boleceksin.

## PROJE BILGILERI
- Framework: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- Design tokens: Tailwind config'te tanimli (bg, fg, border, accent, ai, success, warning, danger)
- Component library: apps/web/components/ui/ (button, badge, input, select, modal, tabs, skeleton, toast)
- Nexus components: apps/web/components/nexus/ (PageHeader, SectionCard, DataGrid, StatusBadge, EmptyState, StatCard, FilterBar)

## BOLUNECEK SAYFALAR

### 1. apps/web/app/new-project/page.tsx (1828 satir) → ONCELIK 1

Bu dosya bir proje olusturma sihirbazi — multi-step form.
ONCE DOSYAYI OKU. Muhtemelen su adimlari iciyor:
- Adim gorunumu (step indicator)
- Urun ailesi secimi
- Proje bilgileri formu
- Dokuman yukleme
- Sonuc / ozet

HEDEF:
```
apps/web/app/new-project/
  page.tsx                    (~100 satir, sadece state + step routing)
  _components/
    StepIndicator.tsx         (~60 satir)
    ProductFamilyStep.tsx     (~200 satir)
    ProjectInfoStep.tsx       (~200 satir)
    DocumentUploadStep.tsx    (~200 satir)
    ReviewStep.tsx            (~150 satir)
```

page.tsx sadece:
```tsx
"use client";
import { useState } from "react";
import { StepIndicator } from "./_components/StepIndicator";
import { ProductFamilyStep } from "./_components/ProductFamilyStep";
import { ProjectInfoStep } from "./_components/ProjectInfoStep";
import { DocumentUploadStep } from "./_components/DocumentUploadStep";
import { ReviewStep } from "./_components/ReviewStep";

export default function NewProjectPage() {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({...});

  const steps = [
    { label: "Urun Ailesi", component: ProductFamilyStep },
    { label: "Proje Bilgileri", component: ProjectInfoStep },
    { label: "Dokumanlar", component: DocumentUploadStep },
    { label: "Ozet", component: ReviewStep },
  ];

  const CurrentStep = steps[step].component;

  return (
    <div>
      <StepIndicator steps={steps} current={step} />
      <CurrentStep data={formData} onChange={setFormData} onNext={() => setStep(s => s+1)} />
    </div>
  );
}
```

### 2. apps/web/app/(dashboard)/veri-simulatoru/page.tsx (1296 satir) → ONCELIK 2

Veri simulatoru sayfasi — muhtemelen form + tablo + preview.
ONCE OKU, sonra bol:
```
apps/web/app/(dashboard)/veri-simulatoru/
  page.tsx                     (~100 satir)
  _components/
    SimulatorForm.tsx          (~300 satir, form alanlari)
    SimulatorPreview.tsx       (~200 satir, veri onizleme)
    SimulatorResults.tsx       (~200 satir, sonuc tablosu)
    ColumnConfig.tsx           (~200 satir, sutun yapilandirma)
```

### 3. apps/web/app/(dashboard)/p/[projectId]/locators/page.tsx (1211 satir) → ONCELIK 2

Locator yonetimi — 5 tabli sayfa.
ONCE OKU. Muhtemelen su tab'lar var:
- Locator Yonetimi
- Stabilite Analizi
- Fallback Zinciri
- POM Uretici
- Kirilma Tahmini

HEDEF:
```
apps/web/app/(dashboard)/p/[projectId]/locators/
  page.tsx                           (~80 satir, tab routing)
  _components/
    LocatorManagementTab.tsx         (~250 satir)
    StabilityAnalysisTab.tsx         (~200 satir)
    FallbackChainTab.tsx             (~200 satir)
    POMGeneratorTab.tsx              (~200 satir)
    BreakagePredictionTab.tsx        (~150 satir)
```

page.tsx sadece:
```tsx
"use client";
import { useState } from "react";
import { PageHeader } from "@/components/nexus/PageHeader";
import { LocatorManagementTab } from "./_components/LocatorManagementTab";
import { StabilityAnalysisTab } from "./_components/StabilityAnalysisTab";
// ... diger tab'lar

const TABS = ["Locator Yönetimi", "Stabilite Analizi", "Fallback Zinciri", "POM Üretici", "Kırılma Tahmini"];

export default function LocatorsPage() {
  const [activeTab, setActiveTab] = useState(0);
  return (
    <>
      <PageHeader title="Locator Zekası" icon="🎯" />
      <div className="flex gap-2 border-b border-border mb-4">
        {TABS.map((t, i) => (
          <button key={t} onClick={() => setActiveTab(i)} className={...}>{t}</button>
        ))}
      </div>
      {activeTab === 0 && <LocatorManagementTab />}
      {activeTab === 1 && <StabilityAnalysisTab />}
      {/* ... */}
    </>
  );
}
```

### 4. apps/web/app/(dashboard)/p/[projectId]/coverage/page.tsx (1189 satir) → ONCELIK 3
ONCE OKU, tab yapisini belirle, ayni pattern ile bol.

### 5. apps/web/app/(dashboard)/p/[projectId]/mobile/page.tsx (1072 satir) → ONCELIK 3
ONCE OKU, tab yapisini belirle, ayni pattern ile bol.

## PARCALAMA KURALLARI

1. **page.tsx SADECE orchestration** — state, tab/step routing, layout. Max 100-150 satir.
2. **_components/ klasoru** — Next.js route'a ozel bilesenler icin alt cizgi prefixli
3. **Shared bilesenler nexus/'e** — birden fazla sayfada kullaniliyorsa components/nexus/'e tasi
4. **Props over context** — veri akisi props ile, global state gerekmedikce context kullanma
5. **"use client" her dosyada** — hooks kullanan bilesenler icin gerekli
6. **Design token kullan** — bg-slate-800 yerine bg-bg-subtle, text-slate-300 yerine text-muted
7. **Mevcut islevselligi KORU** — hicbir ozellik kaybolmamali

## ISLEM SIRASI
1. Her sayfayi OKU
2. Mantiksal parcalari belirle (tab, step, form section, vb.)
3. _components/ klasoru olustur
4. Parcalari ayri dosyalara cikart
5. page.tsx'i sadece orchestration olarak yeniden yaz
6. TypeScript derlemesini kontrol et

## DOGRULAMA
```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -20
```
Sifir hata olmali.
```
