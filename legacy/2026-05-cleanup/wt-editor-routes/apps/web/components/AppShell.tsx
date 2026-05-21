"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect, useMemo, useRef } from "react";
import { NotificationBell } from "@/components/NotificationBell";
import { ServiceRestartButton } from "@/components/ServiceRestartButton";
import { cn } from "@/lib/utils";
import { BgtestLogo } from "@/components/BgtestLogo";
import { AgentRunner } from "@/components/AgentRunner";
import { ENGINE_BASE } from "@/lib/api";
import {
  NAV_GROUP_LABELS,
  PRODUCT_NAME,
  PRODUCT_SHORT,
  getProjectPrimaryNav,
  getSegmentLabel,
  isSegmentInProduct,
  type ProductFamilyId,
} from "@/lib/product";
import { useProject } from "@/lib/useProject";

function segmentFromPath(pathname: string | null, projectId?: string): string {
  if (!pathname) return "";
  return projectId
    ? pathname.replace(`/p/${projectId}`, "").replace(/^\//, "").split("/")[0]
    : pathname.split("/").filter(Boolean).pop() ?? "";
}

function pageNameFromPath(pathname: string | null, projectId?: string): string {
  const segment = segmentFromPath(pathname, projectId);
  return getSegmentLabel(segment);
}

type Project = { id: string; name: string };

function navActive(pathname: string | null, href: string, projectId: string) {
  if (!pathname) return false;
  if (href === `/p/${projectId}`) return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

function navSegment(href: string, projectId: string) {
  return href.replace(`/p/${projectId}`, "").replace(/^\//, "").split("/")[0] || "";
}

/** Birincil navigasyon — tüm önemli sayfalar gruplu */
const primaryNav = (projectId: string) => [
  { href: `/p/${projectId}`,                       label: "Proje Özeti",          group: "" },
  { href: `/p/${projectId}/import`,               label: "İçe Aktar",            group: "Kesfet" },
  { href: `/p/${projectId}/requirements`,         label: "Gereksinimler",        group: "" },
  { href: `/p/${projectId}/coverage`,             label: "Kapsam",               group: "" },
  { href: `/p/${projectId}/analysis`,             label: "Analiz",               group: "" },
  { href: `/p/${projectId}/scenarios`,            label: "Senaryolar",           group: "Tasarla" },
  { href: `/p/${projectId}/test-cases`,           label: "AI Test Case",         group: "" },
  { href: `/p/${projectId}/approvals`,            label: "Onaylar",              group: "" },
  { href: `/p/${projectId}/workflows`,            label: "İş Akışları",          group: "" },
  { href: `/p/${projectId}/synthetic`,            label: "Sentetik Veri",        group: "Veri" },
  { href: `/p/${projectId}/privacy`,              label: "Gizlilik",             group: "" },
  { href: `/p/${projectId}/test-data`,            label: "Test Verileri",        group: "" },
  { href: `/p/${projectId}/manual-to-automation`, label: "Dokümandan Otomasyon", group: "Uret" },
  { href: `/p/${projectId}/automation-gen`,       label: "AI Otomasyon Üret",    group: "" },
  { href: `/p/${projectId}/manual`,               label: "Manuel Testler",       group: "" },
  { href: `/p/${projectId}/automation`,           label: "Otomasyonlar",         group: "" },
  { href: `/p/${projectId}/page-objects`,         label: "Page Objects",         group: "" },
  { href: `/p/${projectId}/locators`,             label: "Locator'lar",          group: "" },
  { href: `/p/${projectId}/recorder`,             label: "Kaydedici",            group: "" },
  { href: `/p/${projectId}/flows`,                label: "Akışlar",              group: "" },
  { href: `/p/${projectId}/api-testing`,           label: "API Test Tasarimi",    group: "Calistir" },
  { href: `/p/${projectId}/chain-builder`,        label: "Chain Builder",        group: "" },
  { href: `/p/${projectId}/environments`,         label: "Ortamlar",             group: "" },
  { href: `/p/${projectId}/api-tests`,            label: "API Koleksiyonlari",   group: "" },
  { href: `/p/${projectId}/test-history`,         label: "Test Geçmişi",         group: "" },
  { href: `/p/${projectId}/executions`,           label: "Koşular",              group: "" },
  { href: `/p/${projectId}/runs`,                 label: "Koşu Geçmişi",         group: "" },
  { href: `/p/${projectId}/regression`,           label: "Regresyon",            group: "" },
  { href: `/p/${projectId}/schedules`,            label: "Zamanlayıcı",          group: "" },
  { href: `/p/${projectId}/cicd`,                 label: "CI/CD",                group: "" },
  { href: `/p/${projectId}/integrations`,         label: "Entegrasyonlar",       group: "" },
  { href: `/p/${projectId}/reports`,              label: "Raporlar",             group: "Gozlemle" },
  { href: `/p/${projectId}/analytics`,            label: "Analitik",             group: "" },
  { href: `/p/${projectId}/debug-report`,         label: "AI Debug Raporu",      group: "" },
  { href: `/p/${projectId}/flaky`,                label: "Flaky Testler",        group: "" },
  { href: `/p/${projectId}/prioritize`,          label: "Önceliklendirme",      group: "" },
  { href: `/p/${projectId}/healing`,             label: "Self-Healing",         group: "" },
  { href: `/p/${projectId}/playwright-console`,  label: "Playwright Konsol",    group: "" },
  { href: `/p/${projectId}/visual`,               label: "Görsel Regresyon",     group: "" },
  { href: `/p/${projectId}/accessibility`,        label: "Erişilebilirlik",      group: "" },
  { href: `/p/${projectId}/monkey`,               label: "Monkey Test",          group: "" },
  { href: `/p/${projectId}/security`,             label: "Güvenlik Taraması",    group: "" },
  { href: `/p/${projectId}/ai-chat`,              label: "AI Asistan",           group: "Advanced" },
  { href: `/p/${projectId}/ai-metrics`,           label: "LLM Metrikleri",       group: "" },
  { href: `/p/${projectId}/qa-orchestrator`,      label: "QA Orkestratör",       group: "" },
  { href: `/p/${projectId}/nl-test-gen`,          label: "NL Test Üretici",      group: "" },
  { href: `/p/${projectId}/wizard`,               label: "Akış Sihirbazı",       group: "" },
  { href: `/p/${projectId}/mobile`,               label: "Visium Farm",          group: "Mobil" },
  { href: `/p/${projectId}/mobile/history`,       label: "Mobil Geçmiş",         group: "Mobil" },
  { href: `/dsl-catalog`,                         label: "DSL Sözlüğü",          group: "Katalog" },
  { href: `/dsl-catalog/mobile`,                  label: "Mobil DSL",            group: "Katalog" },
  { href: `/dsl-catalog/review`,                  label: "DSL İnceleme",         group: "Katalog" },
  { href: `/dsl-catalog/editor/new`,              label: "+ Yeni Cümlecik",      group: "Katalog" },
  { href: `/p/${projectId}/settings`,             label: "Ayarlar",              group: "" },
  { href: "/info/whats-new",                      label: "✨ Yenilikler",         group: "" },
];

/** SidebarSection: aktif projede tek tikla sayfa, ok ile proje listesi */
function SidebarSection({
  label,
  icon,
  projects,
  targetPath,
  testId,
  activeProjectId,
}: {
  label: string;
  icon: React.ReactNode;
  projects: Project[];
  targetPath: string;
  testId: string;
  activeProjectId?: string;
}) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const dest = activeProjectId ? `/p/${activeProjectId}${targetPath}` : null;
  const sectionActive = !!dest && (!!pathname?.startsWith(`${dest}/`) || pathname === dest);

  return (
    <div data-testid={testId}>
      <div className={cn("flex w-full items-stretch gap-0 overflow-hidden rounded-lg", open && "bg-slate-800")}>
        {dest ? (
          <Link
            href={dest}
            className={cn(
              "flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
              "hover:bg-slate-800 text-slate-400 hover:text-white",
              sectionActive && "bg-slate-800 text-white"
            )}
            data-testid={`${testId}-link`}
          >
            <span className="text-slate-500">{icon}</span>
            <span className="truncate text-left">{label}</span>
          </Link>
        ) : (
          <button
            type="button"
            onClick={() => setOpen(!open)}
            className={cn(
              "flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
              "hover:bg-slate-800 text-slate-400 hover:text-white",
              sectionActive && "bg-slate-800 text-white"
            )}
            data-testid={`${testId}-expand`}
          >
            <span className="text-slate-500">{icon}</span>
            <span className="flex-1 truncate text-left">{label}</span>
          </button>
        )}
        <button
          type="button"
          onClick={e => { e.preventDefault(); setOpen(v => !v); }}
          className="flex shrink-0 items-center px-2 text-slate-600 hover:bg-slate-800 hover:text-slate-400 transition-colors"
          aria-label={`${label} için başka proje seç`}
          data-testid={`${testId}-toggle-projects`}
        >
          <svg className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>
      {open && (
        <div className="mt-0.5 ml-3 flex flex-col gap-0.5 border-l border-slate-800 pl-2">
          {projects.length === 0 ? (
            <p className="px-2 py-1.5 text-xs text-slate-600">Proje bulunamadı</p>
          ) : (
            projects.map(p => (
              <button
                key={p.id}
                type="button"
                onClick={() => { router.push(`/p/${p.id}${targetPath}`); setOpen(false); }}
                className="rounded px-2 py-1.5 text-left text-xs text-slate-500 hover:bg-slate-800 hover:text-white transition-colors truncate"
                title={p.name}
              >
                {p.name}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function AppShell({
  children,
  projects,
  projectId,
  topBanner,
}: {
  children: React.ReactNode;
  projects: Project[];
  projectId?: string;
  topBanner?: React.ReactNode;
}) {
  const pathname = usePathname();
  const { projectId: ctxProjectId } = useProject();
  const [storedProjectId, setStoredProjectId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("bgts_active_project");
      if (raw) { const p = JSON.parse(raw); if (p?.id) setStoredProjectId(String(p.id)); }
    } catch {}
  }, []);

  const effectiveProjectId = projectId ?? ctxProjectId ?? storedProjectId ?? projects[0]?.id;
  const primaryLinks = useMemo(
    () => (effectiveProjectId ? getProjectPrimaryNav(effectiveProjectId) : []),
    [effectiveProjectId]
  );
  const currentSegment = useMemo(
    () => segmentFromPath(pathname, effectiveProjectId),
    [pathname, effectiveProjectId]
  );

  const visiblePrimaryLinks = useMemo(() => {
    if (!primaryLinks.length) return [];
    return primaryLinks.filter(link => {
      if (link.path === null) return true;
      const segment = link.segment;
      if (!segment) return true;
      if (segment === currentSegment) return true;
      return isSegmentInProduct("one" as ProductFamilyId, segment);
    });
  }, [currentSegment, primaryLinks]);

  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(() => new Set());

  const toggleGroup = (group: string) =>
    setCollapsedGroups(prev => { const n = new Set(prev); n.has(group) ? n.delete(group) : n.add(group); return n; });

  useEffect(() => { setSidebarOpen(false); }, [pathname]);

  // A11y: Mobile drawer için WAI-ARIA dialog pattern.
  // - Açılınca: fokusu drawer'ın ilk fokuslanabilir öğesine götür.
  // - Kapanınca: fokusu hamburger butonuna geri döndür (blur kaybolmasın).
  // - Escape tuşu drawer'ı kapatır.
  const hamburgerRef = useRef<HTMLButtonElement | null>(null);
  const prevSidebarOpenRef = useRef(sidebarOpen);
  useEffect(() => {
    if (sidebarOpen) {
      const drawer = document.querySelector<HTMLElement>('[data-testid="sidebar"]');
      const firstFocusable = drawer?.querySelector<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      firstFocusable?.focus();
    } else if (prevSidebarOpenRef.current) {
      // Drawer az önce kapandı — fokusu tetikleyen butona (hamburger) geri al
      requestAnimationFrame(() => hamburgerRef.current?.focus());
    }
    prevSidebarOpenRef.current = sidebarOpen;
  }, [sidebarOpen]);

  // Global Escape listener — drawer açıkken çalışır; fokus herhangi bir
  // drawer öğesinde veya overlay'de olsa bile yakalar.
  useEffect(() => {
    if (!sidebarOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSidebarOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [sidebarOpen]);

  const currentProject = projects.find(p => p.id === effectiveProjectId);
  const [projectDropOpen, setProjectDropOpen] = useState(false);

  const linkCls = (active: boolean) => cn(
    "flex items-center gap-2 rounded px-2 py-1 text-[13px] transition-colors text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 motion-reduce:transition-none",
    // a11y: görünür focus ring (WCAG 2.4.7) — klavye kullanıcıları için.
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900",
    active && "bg-slate-800 text-white font-medium"
  );

  // A11y props bundle: navigation link'lerine tek spread ile uygulanır.
  // - `className`: linkCls ile aynı
  // - `aria-current="page"` aktif link'te (WCAG 2.4.8 Location)
  // - `data-nav-item`: Arrow Up/Down klavye nav'ının bulacağı marker
  const navLink = (active: boolean) => ({
    className: linkCls(active),
    "data-nav-item": "" as const,
    ...(active ? { "aria-current": "page" as const } : {}),
  });

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      {topBanner}
      <div className="flex min-h-0 flex-1">

        {/* Skip-to-content — WCAG 2.4.1 Bypass Blocks. Klavye'de Tab ile
            ilk fokuslanabilir öğe; görünmezken ekran okuyucu okur,
            focus'landığında görünür hale gelir ve ana içeriğe atlatır. */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-none focus:ring-2 focus:ring-blue-300"
          data-testid="skip-to-content"
        >
          Ana içeriğe atla
        </a>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/60 md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Sidebar — mobile'da dialog, desktop'ta statik navigation container.
            Klavye için: Escape kapatır, focus trap drawer içinde tutulur. */}
        <aside
          className={cn(
            "flex w-48 flex-col border-r border-border bg-white",
            "fixed inset-y-0 left-0 z-40 transition-transform duration-200 md:static md:translate-x-0",
            // prefers-reduced-motion: animasyonu devre dışı bırak
            "motion-reduce:transition-none",
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
          data-testid="sidebar"
          role="dialog"
          aria-label="Ana navigasyon menüsü"
          aria-modal={sidebarOpen ? "true" : undefined}
          onKeyDown={(e) => {
            if (e.key === "Escape" && sidebarOpen) {
              e.stopPropagation();
              setSidebarOpen(false);
            }
          }}
        >
          {/* Logo */}
          <div className="flex items-center justify-between px-4 py-4 border-b border-slate-800">
            <Link
              href="/"
              data-testid="sidebar-logo"
              className="rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              aria-label="Anasayfaya git"
            >
              <BgtestLogo className="h-8" />
            </Link>
            <button
              type="button"
              className="rounded-lg p-1 text-slate-500 hover:bg-slate-800 hover:text-white md:hidden transition-colors motion-reduce:transition-none focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              onClick={() => setSidebarOpen(false)}
              aria-label="Menüyü kapat"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <nav
            id="sidebar-nav"
            className="flex flex-1 flex-col overflow-y-auto px-2 py-2 gap-0"
            data-testid="sidebar-nav"
            aria-label="Ana navigasyon"
            onKeyDown={(e) => {
              // Arrow Up/Down klavye navigasyonu — aynı <nav> içindeki
              // fokuslanabilir menü öğeleri arasında dolaşır. WCAG 2.1.1.
              if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
              const nav = e.currentTarget;
              const items = Array.from(
                nav.querySelectorAll<HTMLElement>('a[data-nav-item], button[data-nav-item]')
              ).filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null);
              if (items.length === 0) return;
              const active = document.activeElement as HTMLElement | null;
              const idx = active ? items.indexOf(active) : -1;
              let next: number;
              if (e.key === "ArrowDown") next = idx < 0 ? 0 : (idx + 1) % items.length;
              else next = idx <= 0 ? items.length - 1 : idx - 1;
              items[next]?.focus();
              e.preventDefault();
            }}
          >
            {/* Portfolio home */}
            <Link href="/portfolio" {...navLink(pathname === "/portfolio")} data-testid="sidebar-link-dashboard">
              <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v2a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 12a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1v-7z" />
              </svg>
              Portföy
            </Link>

            {/* Visium Intelligence */}
            <Link href="/bgtest-wizard" {...navLink(!!pathname?.startsWith("/bgtest-wizard"))} data-testid="sidebar-link-bgtest-wizard">
              <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Visium Intelligence
            </Link>
            <Link href="/veri-kaynagi" {...navLink(!!pathname?.startsWith("/veri-kaynagi"))} data-testid="sidebar-link-veri-kaynagi">
              <svg className="h-3.5 w-3.5 shrink-0 ml-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
              Veri Kaynağı
            </Link>
            <Link href="/veri-simulatoru" {...navLink(!!pathname?.startsWith("/veri-simulatoru"))} data-testid="sidebar-link-veri-simulatoru">
              <svg className="h-3.5 w-3.5 shrink-0 ml-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
              Veri Simülatörü
            </Link>

            {/* Projeler */}
            <Link href="/projects" {...navLink(pathname === "/projects")} data-testid="sidebar-link-projects">
              <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              Projeler
            </Link>

            {currentProject && (
              <div className="mx-1 mt-1 mb-0.5 flex items-center gap-1.5 rounded-md bg-blue-500/10 px-2 py-1.5" data-testid="sidebar-active-project">
                <svg className="h-3 w-3 shrink-0 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <p className="text-[12px] font-medium text-blue-300 truncate" title={currentProject.name}>
                  {currentProject.name}
                </p>
              </div>
            )}

            {visiblePrimaryLinks.length > 0 && (() => {
              let curGroup = "";
              return (
                <div className="mt-1 flex flex-col">
                  {visiblePrimaryLinks.map((l, idx) => {
                    if (l.group) curGroup = l.group;
                    const effGroup = curGroup;
                    const collapsed = !!effGroup && collapsedGroups.has(effGroup);
                    const slug = l.href.split("/").pop() || "root";
                    const showHeader = l.group && (idx === 0 || visiblePrimaryLinks[idx - 1].group !== l.group);
                    const isActive = !!effectiveProjectId && navActive(pathname, l.href, effectiveProjectId);
                    return (
                      <div key={l.href}>
                        {showHeader && (
                          <button
                            type="button"
                            onClick={() => toggleGroup(l.group)}
                            className="flex w-full items-center gap-1 px-2 py-1.5 mt-1 rounded hover:bg-slate-800/60 group select-none transition-colors"
                          >
                            <span className="flex-1 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-600 group-hover:text-slate-400">
                              {NAV_GROUP_LABELS[l.group] ?? l.group}
                            </span>
                            <svg className={cn("h-2.5 w-2.5 shrink-0 text-slate-700 transition-transform duration-150 group-hover:text-slate-500", collapsed && "-rotate-90")}
                              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                        )}
                        {!collapsed && (
                          <Link
                            href={l.href}
                            className={cn(
                              "flex items-center justify-between rounded px-2 py-1 text-[13px] leading-snug transition-colors",
                              "text-muted hover:text-fg hover:bg-bg-subtle",
                              isActive && "text-accent bg-accent-subtle border-l-2 border-accent pl-[7px] font-medium"
                            )}
                            data-testid={`sidebar-link-${slug}`}
                          >
                            <span>{l.label}</span>
                          </Link>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })()}

            {/* Shortcuts */}
            <div className="mt-3">
              <button
                type="button"
                onClick={() => setShortcutsOpen(v => !v)}
                className="flex w-full items-center gap-1 px-2 py-1.5 rounded hover:bg-slate-800/60 group transition-colors motion-reduce:transition-none focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                data-testid="sidebar-shortcuts-toggle"
                data-nav-item=""
                aria-expanded={shortcutsOpen}
                aria-controls="sidebar-shortcuts-panel"
              >
                <span className="flex-1 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-600 group-hover:text-slate-400">
                  Kısayollar
                </span>
                <svg className={cn("h-2.5 w-2.5 shrink-0 text-slate-700 transition-transform duration-150 group-hover:text-slate-500", shortcutsOpen && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {shortcutsOpen && (
                <div className="mt-1 space-y-1" id="sidebar-shortcuts-panel" role="region" aria-label="Kısayollar">
                  <SidebarSection
                    label="Veri Merkezi"
                    icon={<svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>}
                    projects={projects}
                    targetPath="/test-data"
                    testId="sidebar-section-test-data"
                    activeProjectId={projectIdForSidebarSections}
                  />
                  <SidebarSection
                    label="Koşular"
                    icon={<svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>}
                    projects={projects}
                    targetPath="/executions"
                    testId="sidebar-section-otomasyon"
                    activeProjectId={projectIdForSidebarSections}
                  />
                </div>
              )}
            </div>

            <div className="mt-3">
              <button
                type="button"
                onClick={() => setToolsOpen(v => !v)}
                className="flex w-full items-center gap-1 px-2 py-1.5 rounded hover:bg-slate-800/60 group transition-colors motion-reduce:transition-none focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                data-testid="sidebar-tools-toggle"
                data-nav-item=""
                aria-expanded={toolsOpen}
                aria-controls="sidebar-tools-panel"
              >
                <span className="flex-1 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-600 group-hover:text-slate-400">
                  Araçlar ve Yönetim
                </span>
                <svg className={cn("h-2.5 w-2.5 shrink-0 text-slate-700 transition-transform duration-150 group-hover:text-slate-500", toolsOpen && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {toolsOpen && (
                <div id="sidebar-tools-panel" role="region" aria-label="Araçlar ve Yönetim">
            {/* E2E section */}
            <div data-testid="sidebar-section-e2e">
              <div className={cn("flex w-full items-stretch gap-0 overflow-hidden rounded-lg", e2eOpen && "bg-slate-800")}>
                <Link
                  href="/e2e"
                  className={cn(
                    "flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                    "text-slate-400 hover:bg-slate-800 hover:text-white",
                    pathname?.startsWith("/e2e") && "bg-slate-800 text-white"
                  )}
                  data-testid="sidebar-link-e2e"
                >
                  <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h10M7 16h6M5 4h14a2 2 0 012 2v12a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z" />
                  </svg>
                  <span className="truncate text-left">E2E</span>
                </Link>
                <button
                  type="button"
                  onClick={e => { e.preventDefault(); setE2eOpen(v => !v); }}
                  className="flex shrink-0 items-center px-2 text-slate-600 hover:bg-slate-800 hover:text-slate-400 transition-colors"
                  aria-label="E2E alt menüsünü aç/kapat"
                  data-testid="sidebar-toggle-e2e"
                >
                  <svg className={cn("h-3.5 w-3.5 transition-transform", e2eOpen && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
              {e2eOpen && (
                <div className="mt-0.5 ml-3 flex flex-col gap-0.5 border-l border-slate-800 pl-2">
                  <Link
                    href="/e2e/analizden-senaryo-cikartma"
                    className={cn(
                      "rounded px-2 py-1.5 text-left text-xs text-slate-500 hover:bg-slate-800 hover:text-white transition-colors truncate",
                      pathname === "/e2e/analizden-senaryo-cikartma" && "bg-slate-800 text-white font-medium"
                    )}
                    data-testid="sidebar-link-e2e-analizden-senaryo-cikartma"
                  >
                    Analizden Senaryo Çıkartma
                  </Link>
                </div>
              )}
            </div>

            {/* Admin divider */}
            <div className="my-2 border-t border-slate-800" />

            <Link href="/admin/users" {...navLink(!!pathname?.startsWith("/admin/users"))} data-testid="sidebar-link-admin-users">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                Yönetim
              </span>
            </Link>
            <Link href="/admin/audit" {...navLink(!!pathname?.startsWith("/admin/audit"))} data-testid="sidebar-link-admin-audit">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Denetim Günlüğü
              </span>
            </Link>
            <Link href="/admin/settings" {...navLink(!!pathname?.startsWith("/admin/settings"))} data-testid="sidebar-link-admin-settings">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                AI Ayarları
              </span>
            </Link>
            <Link href="/symbols" {...navLink(pathname === "/symbols")} data-testid="sidebar-link-symbols">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                </svg>
                Simge rehberi
              </span>
            </Link>
                </div>
              )}
            </div>
          </nav>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-14 items-center gap-3 border-b border-border bg-white/80 backdrop-blur-sm px-4 md:px-6" data-testid="header">
            <button
              type="button"
              ref={hamburgerRef}
              className="shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-white md:hidden transition-colors motion-reduce:transition-none focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              onClick={() => setSidebarOpen(true)}
              aria-label="Menüyü aç"
              aria-expanded={sidebarOpen}
              aria-controls="sidebar-nav"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <nav className="flex min-w-0 flex-1 items-center gap-1.5 text-sm text-slate-500" aria-label="breadcrumb">
              <Link href="/projects" className="shrink-0 font-semibold text-blue-400 hover:text-blue-300 transition-colors" data-testid="header-breadcrumb-home">
                {PRODUCT_SHORT}
              </Link>
              {currentProject && (
                <>
                  <svg className="h-3.5 w-3.5 shrink-0 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                  <Link href={`/p/${currentProject.id}`} className="truncate font-medium text-slate-300 hover:text-white transition-colors" data-testid="header-breadcrumb-project">
                    {currentProject.name}
                  </Link>
                </>
              )}
              {currentProject && pageNameFromPath(pathname, currentProject.id) && pageNameFromPath(pathname, currentProject.id) !== "Proje Özeti" && (
                <>
                  <svg className="h-3.5 w-3.5 shrink-0 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                  <span className="truncate text-slate-500" data-testid="header-breadcrumb-page">
                    {pageNameFromPath(pathname, currentProject.id)}
                  </span>
                </>
              )}
              {!currentProject && <span className="text-slate-300 font-medium">{PRODUCT_NAME}</span>}
            </nav>

            {currentProject && (
              <div className="relative shrink-0 hidden md:block">
                <button
                  type="button"
                  onClick={() => setProjectDropOpen(v => !v)}
                  className="flex items-center gap-1.5 rounded-full border border-border bg-bg-subtle px-3 py-1 text-xs font-medium text-fg hover:border-accent/50 hover:text-accent transition-colors"
                  data-testid="header-project-pill"
                >
                  <svg className="h-3.5 w-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <span className="max-w-[140px] truncate">{currentProject.name}</span>
                  <svg className={cn("h-3 w-3 text-slate-600 transition-transform", projectDropOpen && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {projectDropOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setProjectDropOpen(false)} />
                    <div className="absolute left-1/2 top-full z-50 mt-2 w-52 -translate-x-1/2 rounded-xl border border-border bg-white py-1 shadow-lg">
                      <div className="border-b border-border px-3 py-2">
                        <p className="text-[10px] uppercase tracking-wider text-slate-500">Aktif Proje</p>
                        <p className="text-sm font-semibold text-white truncate">{currentProject.name}</p>
                      </div>
                      <Link href={`/p/${currentProject.id}/settings`} className="flex items-center gap-2 px-3 py-2 text-sm text-fg hover:bg-bg-subtle transition-colors" onClick={() => setProjectDropOpen(false)} data-testid="header-project-pill-settings">
                        Proje Ayarları
                      </Link>
                      <Link href="/projects" className="flex items-center gap-2 px-3 py-2 text-sm text-fg hover:bg-bg-subtle transition-colors" onClick={() => setProjectDropOpen(false)} data-testid="header-project-pill-all">
                        Tüm Projeler
                      </Link>
                    </div>
                  </>
                )}
              </div>
            )}

            <div className="flex shrink-0 items-center gap-2">
              <ServiceRestartButton />
              <AgentRunner />
              <NotificationBell />
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white transition hover:bg-blue-500"
                  aria-label="Kullanıcı menüsü"
                  data-testid="header-btn-user-menu"
                >
                  YB
                </button>
                {userMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                    <div className="absolute right-0 top-full z-50 mt-2 w-48 rounded-xl border border-border bg-white py-1 shadow-lg">
                      <div className="border-b border-border px-3 py-2">
                        <p className="text-sm font-medium text-white">Yasin Bulgan</p>
                        <p className="text-xs text-slate-500">yasin.bulgan@bgtest.com</p>
                      </div>
                      <Link href="/profile" className="block px-3 py-2 text-sm text-fg hover:bg-bg-subtle transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-profile">
                        Profil
                      </Link>
                      <div className="border-t border-border" />
                      <button
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm text-danger hover:bg-danger-subtle hover:text-danger transition-colors"
                        onClick={async () => {
                          setUserMenuOpen(false);
                          try { await fetch(`${ENGINE_BASE}/api/auth/logout`, { method: "POST", credentials: "include" }); } catch {}
                          window.location.href = "/login";
                        }}
                        data-testid="user-menu-btn-logout"
                      >
                        Çıkış Yap
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </header>

          <main
            id="main-content"
            tabIndex={-1}
            className="flex-1 bg-slate-950 focus:outline-none"
          >
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
