# Design Agent 6: Chart/Grafik Kutuphanesi Ekleme

## Cursor'a yapistir:

```
Sen bir senior frontend muhendisisin. BGTS bankacilik test platformuna
grafik/chart kutuphanesi ekleyerek dashboard ve analitik sayfalarini
gorsel olarak zenginlestireceksin.

## MEVCUT DURUM
- Hicbir chart kutuphanesi kurulu DEGIL
- Dashboard ve analitik sayfalarinda sadece rakamlar ve tablolar var
- StatCard bilesen mevcut (tek deger gosterimi)
- Design token'lar: accent (#2563eb), success (#16a34a), warning (#d97706), danger (#dc2626), ai (#7c3aed)
- Dark mode destegi VAR

## ADIM 1: recharts Kur

```bash
cd apps/web && npm install recharts
```

Neden recharts?
- React-native, component-based API
- Responsive (ResponsiveContainer)
- Customizable (Tailwind class'lari ile uyumlu)
- Tree-shakeable (sadece kullanilan component'ler bundle'a girer)
- Dark mode destegi kolay

## ADIM 2: Chart Wrapper Component'leri Olustur

### apps/web/components/charts/ChartWrapper.tsx
Tum chart'lar icin ortak wrapper:

```tsx
"use client";

import { ResponsiveContainer } from "recharts";

interface ChartWrapperProps {
  children: React.ReactNode;
  height?: number;
  className?: string;
}

export function ChartWrapper({ children, height = 300, className = "" }: ChartWrapperProps) {
  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}
```

### apps/web/components/charts/TrendLineChart.tsx
Zaman serisi trend grafigi (test kosulari, coverage, vb.):

```tsx
"use client";

import { memo } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { ChartWrapper } from "./ChartWrapper";

interface TrendLineChartProps {
  data: Array<Record<string, unknown>>;
  lines: Array<{
    dataKey: string;
    label: string;
    color?: string;  // CSS variable name: "accent", "success", "danger", "warning", "ai"
  }>;
  xAxisKey?: string;
  height?: number;
}

const COLOR_MAP: Record<string, string> = {
  accent:  "var(--accent)",
  success: "var(--success)",
  warning: "var(--warning)",
  danger:  "var(--danger)",
  ai:      "var(--ai)",
  muted:   "var(--muted)",
};

export const TrendLineChart = memo(function TrendLineChart({
  data, lines, xAxisKey = "date", height = 300,
}: TrendLineChartProps) {
  return (
    <ChartWrapper height={height}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey={xAxisKey} stroke="var(--muted)" fontSize={12} />
        <YAxis stroke="var(--muted)" fontSize={12} />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--bg)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            color: "var(--fg)",
          }}
        />
        <Legend />
        {lines.map((line) => (
          <Line
            key={line.dataKey}
            type="monotone"
            dataKey={line.dataKey}
            name={line.label}
            stroke={COLOR_MAP[line.color || "accent"] || line.color}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ChartWrapper>
  );
});
```

### apps/web/components/charts/DonutChart.tsx
Durum dagilimi (passed/failed/skipped):

```tsx
"use client";

import { memo } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import { ChartWrapper } from "./ChartWrapper";

interface DonutChartProps {
  data: Array<{ name: string; value: number; color?: string }>;
  height?: number;
}

const DEFAULT_COLORS = [
  "var(--success)", "var(--danger)", "var(--warning)",
  "var(--accent)", "var(--ai)", "var(--muted)",
];

export const DonutChart = memo(function DonutChart({ data, height = 250 }: DonutChartProps) {
  return (
    <ChartWrapper height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell
              key={entry.name}
              fill={entry.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--bg)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            color: "var(--fg)",
          }}
        />
        <Legend />
      </PieChart>
    </ChartWrapper>
  );
});
```

### apps/web/components/charts/BarChart.tsx
Karsilastirma (domain bazli test sayisi, sprint bazli vb.):

```tsx
"use client";

import { memo } from "react";
import { BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { ChartWrapper } from "./ChartWrapper";

interface BarChartProps {
  data: Array<Record<string, unknown>>;
  bars: Array<{ dataKey: string; label: string; color?: string }>;
  xAxisKey?: string;
  height?: number;
  stacked?: boolean;
}

const COLOR_MAP: Record<string, string> = {
  accent: "var(--accent)", success: "var(--success)",
  warning: "var(--warning)", danger: "var(--danger)",
  ai: "var(--ai)", muted: "var(--muted)",
};

export const StackedBarChart = memo(function StackedBarChart({
  data, bars, xAxisKey = "label", height = 300, stacked = false,
}: BarChartProps) {
  return (
    <ChartWrapper height={height}>
      <RechartsBarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey={xAxisKey} stroke="var(--muted)" fontSize={12} />
        <YAxis stroke="var(--muted)" fontSize={12} />
        <Tooltip contentStyle={{ backgroundColor: "var(--bg)", border: "1px solid var(--border)", borderRadius: "var(--radius)", color: "var(--fg)" }} />
        <Legend />
        {bars.map((bar) => (
          <Bar
            key={bar.dataKey}
            dataKey={bar.dataKey}
            name={bar.label}
            fill={COLOR_MAP[bar.color || "accent"] || bar.color}
            stackId={stacked ? "stack" : undefined}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </RechartsBarChart>
    </ChartWrapper>
  );
});
```

### apps/web/components/charts/index.ts
```ts
export { ChartWrapper } from "./ChartWrapper";
export { TrendLineChart } from "./TrendLineChart";
export { DonutChart } from "./DonutChart";
export { StackedBarChart } from "./BarChart";
```

## ADIM 3: Dashboard Sayfasina Chart'lar Ekle

Proje ozet sayfasini oku:
apps/web/app/(dashboard)/p/[projectId]/page.tsx

Bu sayfaya chart'lar ekle:

```tsx
import { TrendLineChart, DonutChart, StackedBarChart } from "@/components/charts";
import { SectionCard } from "@/components/nexus/SectionCard";

// Ornek: Test Kosu Trendi
<SectionCard title="Test Kosu Trendi" icon="📈">
  <TrendLineChart
    data={executionTrend}  // [{date: "2026-04-10", passed: 45, failed: 3, skipped: 2}, ...]
    lines={[
      { dataKey: "passed", label: "Gecti", color: "success" },
      { dataKey: "failed", label: "Basarisiz", color: "danger" },
      { dataKey: "skipped", label: "Atlandi", color: "muted" },
    ]}
  />
</SectionCard>

// Ornek: Senaryo Durum Dagilimi
<SectionCard title="Senaryo Durumu" icon="🍩">
  <DonutChart
    data={[
      { name: "Aktif", value: stats.active, color: "var(--success)" },
      { name: "Taslak", value: stats.draft, color: "var(--muted)" },
      { name: "Arsiv", value: stats.archived, color: "var(--danger)" },
    ]}
  />
</SectionCard>
```

## ADIM 4: Diger Sayfalara Chart Ekle

Ayni chart component'lerini su sayfalarda kullan:
- analytics sayfasi — trend + bar chart
- coverage sayfasi — line chart (coverage over time)
- reports sayfasi — donut + bar chart
- ai-metrics sayfasi — LLM token kullanimi trend

ONCE her sayfayi oku, mevcut StatCard'lardan veri yapısını anla,
sonra uygun chart component'ini ekle.

## KURALLAR
- Tum chart'lar design token'lari kullanmali (var(--accent), vb.)
- Dark mode otomatik calismali (CSS variable'lar sayesinde)
- Chart'lar responsive olmali (ResponsiveContainer)
- Veri yoksa EmptyState goster, chart render etme
- "use client" her chart dosyasinda olmali (recharts client-side)
- React.memo kullan (data degismezse re-render onle)

## DOGRULAMA
```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -10
# Gorsel kontrol:
# npm run dev → localhost:3000 → proje ozet sayfasi
```
```
