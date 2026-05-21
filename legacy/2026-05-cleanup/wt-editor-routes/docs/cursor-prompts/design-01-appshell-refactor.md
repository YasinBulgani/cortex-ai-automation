# Design Agent 1: AppShell Refactoring (1032 satir → 4 dosya)

## Cursor'a yapistir:

```
Sen bir senior frontend muhendisisin. BGTS bankacilik test platformunun
AppShell.tsx bilesenini (1032 satir) kucuk, bakimi kolay parcalara boleceksin.

## PROJE BILGILERI
- Framework: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- Dosya: apps/web/components/AppShell.tsx (1032 satir)
- Dark mode: class-based (.dark)
- Design tokens: apps/web/app/styles/tokens.css → Tailwind config'te map'li
- Tailwind custom colors: bg, bg-subtle, fg, muted, border, accent, ai, success, warning, danger

## MEVCUT YAPI
AppShell.tsx su parcalari iciyor:
1. Import'lar ve type'lar (~30 satir)
2. segmentFromPath, navSegment helper'lar (~20 satir)
3. primaryNav fonksiyonu — 50+ nav item tanımlı (~60 satir)
4. SidebarSection component (~80 satir)
5. Ana AppShell component (~840 satir) icinde:
   - Sidebar state management
   - Navigation rendering (grup basliklari, aktif item vurgulama)
   - Persona selector dropdown
   - Product family selector
   - User menu
   - Notification bell
   - Mobile hamburger menu
   - Main content area

## HEDEF YAPI

### 1. apps/web/components/shell/Sidebar.tsx (~250 satir)
Sidebar mantigi ve rendering:
- Sidebar acik/kapali state
- Mobile menu toggle
- Logo alanı
- Persona selector
- Product family selector
- Collapse/expand butonu

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { BgtestLogo } from "@/components/BgtestLogo";
import { SidebarNavigation } from "./SidebarNavigation";
import { PersonaSelector } from "./PersonaSelector";

interface SidebarProps {
  projectId: string;
  currentSegment: string;
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ projectId, currentSegment, collapsed, onToggle }: SidebarProps) {
  return (
    <aside className={cn(
      "fixed inset-y-0 left-0 z-30 flex flex-col bg-bg border-r border-border transition-all",
      collapsed ? "w-16" : "w-64"
    )}>
      {/* Logo */}
      <div className="...">
        <BgtestLogo />
      </div>

      {/* Persona Selector */}
      {!collapsed && <PersonaSelector />}

      {/* Navigation */}
      <SidebarNavigation
        projectId={projectId}
        currentSegment={currentSegment}
        collapsed={collapsed}
      />

      {/* Collapse toggle */}
      <button onClick={onToggle} className="..." aria-label={collapsed ? "Menüyü genişlet" : "Menüyü daralt"}>
        ...
      </button>
    </aside>
  );
}
```

### 2. apps/web/components/shell/SidebarNavigation.tsx (~200 satir)
Navigasyon listesi ve gruplama:
- primaryNav array'ini import et (veya props olarak al)
- Grup basliklarini render et
- Aktif item vurgulama
- Scroll alanı

```tsx
"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { getSegmentLabel } from "@/lib/product";

interface SidebarNavigationProps {
  projectId: string;
  currentSegment: string;
  collapsed: boolean;
}

export function SidebarNavigation({ projectId, currentSegment, collapsed }: SidebarNavigationProps) {
  // primaryNav fonksiyonunu buraya tasi veya import et
  const navItems = primaryNav(projectId);
  
  // Gruplama mantigi
  // ...
}
```

### 3. apps/web/components/shell/TopBar.tsx (~150 satir)
Ust bar: breadcrumb, arama, bildirimler, kullanici menu:
- NotificationBell
- ServiceRestartButton
- AgentRunner
- User avatar + dropdown menu
- Theme toggle

```tsx
"use client";

import { NotificationBell } from "@/components/NotificationBell";
import { ServiceRestartButton } from "@/components/ServiceRestartButton";
import { AgentRunner } from "@/components/AgentRunner";
import ThemeToggle from "@/components/ThemeToggle";

interface TopBarProps {
  userName?: string;
  onLogout: () => void;
}

export function TopBar({ userName, onLogout }: TopBarProps) {
  return (
    <header className="sticky top-0 z-20 h-14 border-b border-border bg-bg/80 backdrop-blur-sm flex items-center px-4 gap-3">
      {/* Sol: Breadcrumb veya baslik */}
      <div className="flex-1" />
      
      {/* Sag: Aksiyonlar */}
      <AgentRunner />
      <ServiceRestartButton />
      <NotificationBell />
      <ThemeToggle />
      {/* User menu */}
    </header>
  );
}
```

### 4. apps/web/components/AppShell.tsx (~200 satir, REFACTORED)
Sadece orchestration — state yonetimi ve layout:

```tsx
"use client";

import { useState, useMemo } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./shell/Sidebar";
import { TopBar } from "./shell/TopBar";
import { useProject } from "@/lib/useProject";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { projectId } = useProject();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  const currentSegment = useMemo(
    () => segmentFromPath(pathname, projectId),
    [pathname, projectId]
  );

  return (
    <div className="flex h-screen bg-bg text-fg">
      <Sidebar
        projectId={projectId || ""}
        currentSegment={currentSegment}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(prev => !prev)}
      />
      
      <div className={cn("flex-1 flex flex-col", sidebarCollapsed ? "ml-16" : "ml-64")}>
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### 5. apps/web/components/shell/index.ts
```ts
export { Sidebar } from "./Sidebar";
export { SidebarNavigation } from "./SidebarNavigation";
export { TopBar } from "./TopBar";
```

## KURALLAR
- Mevcut AppShell'in TUM islevselligini koru — hicbir sey kaybolmamali
- Tailwind class'larini aynen tasi, design token'lar kullan (bg, fg, border, vb.)
- "use client" her dosyada olmali (hooks kullaniyor)
- Dark mode class'larini koru
- Mevcut import path'i degismemeli: `@/components/AppShell` hala calismal
- primaryNav array'ini shell/nav-config.ts'e tasiyabilirsin
- TypeScript strict — tip hatalari olmasin

## ISLEM SIRASI
1. apps/web/components/shell/ klasorunu olustur
2. SidebarNavigation.tsx yaz (primaryNav + gruplama + aktif item)
3. Sidebar.tsx yaz (sidebar frame + navigation + persona)
4. TopBar.tsx yaz (ust bar + aksiyonlar)
5. AppShell.tsx'i refactor et (sadece orchestration)
6. Mevcut tum import'larin calistigini dogrula

## DOGRULAMA
```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -20
```
Sifir hata olmali.
```
