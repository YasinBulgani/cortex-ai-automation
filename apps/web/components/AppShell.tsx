"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { NotificationBell } from "@/components/NotificationBell";
import { NotificationCenter } from "@/components/NotificationCenter";
import { KeyboardShortcutsHelp } from "@/components/KeyboardShortcutsHelp";
import { ServiceRestartButton } from "@/components/ServiceRestartButton";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AiAssistantPanel } from "@/components/AiAssistantPanel";
import { AiStatusChip } from "@/components/AiStatusChip";
import { OnboardingTour } from "@/components/OnboardingTour";
import { RecentFavoritesPanel } from "@/components/RecentFavoritesPanel";
import { SidebarSearch } from "@/components/SidebarSearch";
import { cn } from "@/lib/utils";
import { ENGINE_BASE, clearTokens } from "@/lib/api";
import {
  PRODUCT_SHORT,
  PRODUCT_FAMILY,
  PRODUCT_FAMILY_STORAGE_KEY,
  PRODUCT_AVAILABILITY_META,
  PROJECT_NAV_DEFINITIONS,
  NAV_GROUP_LABELS,
  type ProductFamilyId,
} from "@/lib/product";
import { useProject } from "@/lib/useProject";
import { SidebarProjectSwitcher } from "@/components/SidebarProjectSwitcher";
import { PRODUCT_BRAND } from "@/lib/products/brand";

type Project = { id: string; name: string };
const ALL_PRODUCTS_OPTION = { id: "all" as const, label: "QA Operations Platform", short: "Tümü" };

// ─── Sidebar ikonları ────────────────────────────────────────────────────────

function IconChart()    { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>; }
function IconFolder()   { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>; }
function IconEdit()     { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>; }
function IconFlow()     { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4" /></svg>; }
function IconBrain()    { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>; }
function IconCode()     { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>; }
function IconBook()     { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>; }
function IconDatabase() { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>; }
function IconTerminal() { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 9l-4 3 4 3M16 9l4 3-4 3M13 5l-2 14" /></svg>; }
function IconSettings() { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>; }
function IconUsers()    { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>; }
function IconLogout()   { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>; }
function IconBell()     { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>; }
function IconChevron({ open }: { open: boolean }) {
  return <svg className={cn("h-3 w-3 shrink-0 transition-transform duration-150", open && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>;
}

// ─── Global navigasyon (BGTS Cortex yapısı) ──────────────────────────────────

const GLOBAL_NAV = [
  {
    section: "PANEL",
    items: [
      { href: "/", label: "Aktivite Monitörü", icon: <IconChart />, exact: true as const },
    ],
  },
  {
    section: "ÇALIŞMA ALANLARI",
    items: [
      { href: "/portfolio", label: "Portfolio", icon: <IconFolder /> },
    ],
  },
  {
    section: "OTOMASYON",
    items: [
      { href: "/task-drafts",   label: "Senaryo Oluşturucu", icon: <IconEdit /> },
      { href: "/flow-designer", label: "Akış Tasarımcısı",   icon: <IconFlow /> },
    ],
  },
  {
    section: "AGENTLAR",
    items: [
      { href: "/ai-agents",  label: "AI Ajanları",        icon: <IconBrain /> },
      { href: "/ai-workflows", label: "Workflow Health", icon: <IconFlow /> },
      { href: "/nexus-code", label: "Neurex Code",         icon: <IconCode /> },
    ],
  },
  {
    section: "BİLGİ",
    items: [
      { href: "/dsl-catalog",  label: "DSL Kataloğu", icon: <IconBook /> },
      { href: "/veri-kaynagi", label: "Veri Merkezi",  icon: <IconDatabase /> },
    ],
  },
  {
    section: "ALTYAPI",
    items: [
      { href: "/ide",             label: "Senaryo IDE",  icon: <IconTerminal /> },
      { href: "/admin/prompts",   label: "Prompt Registry", icon: <IconBook /> },
      { href: "/notifications",   label: "Bildirimler",  icon: <IconBell /> },
      { href: "/admin/settings",  label: "Ayarlar",      icon: <IconSettings /> },
    ],
  },
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function navActive(pathname: string | null, href: string, exact = false): boolean {
  if (!pathname) return false;
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

// ─── NavItem ─────────────────────────────────────────────────────────────────

function NavItem({
  href, label, icon, active, testId,
}: {
  href: string; label: string; icon: React.ReactNode; active: boolean; testId?: string;
}) {
  return (
    <Link
      href={href}
      data-testid={testId}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 relative",
        active
          ? "bg-blue-50/80 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:w-1 before:h-6 before:bg-blue-600 dark:before:bg-blue-400 before:rounded-r-full"
          : "text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-white"
      )}
    >
      <span className={cn("transition-colors", active ? "text-blue-600 dark:text-blue-400" : "text-gray-400 dark:text-slate-400")}>
        {icon}
      </span>
      {label}
    </Link>
  );
}

// ─── Ana bileşen ──────────────────────────────────────────────────────────────

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
  const router = useRouter();
  const path   = usePathname();
  const { projectId: ctxProjectId } = useProject();

  const [storedProjectId, setStoredProjectId] = useState<string | null>(null);
  const [sidebarOpen,     setSidebarOpen]     = useState(false);
  const [userMenuOpen,    setUserMenuOpen]     = useState(false);
  const [projectDropOpen, setProjectDropOpen] = useState(false);
  const [productPickerOpen, setProductPickerOpen] = useState(false);
  const [activeProductId, setActiveProductId] = useState<string>("all");

  useEffect(() => {
    try {
      const raw = localStorage.getItem("bgts_active_project");
      if (raw) { const p = JSON.parse(raw); if (p?.id) setStoredProjectId(String(p.id)); }
      const product = localStorage.getItem(PRODUCT_FAMILY_STORAGE_KEY);
      if (product) setActiveProductId(product);
    } catch { /* ignore */ }
  }, []);

  const activeProduct = activeProductId === "all"
    ? ALL_PRODUCTS_OPTION
    : PRODUCT_FAMILY.find(p => p.id === activeProductId) ?? ALL_PRODUCTS_OPTION;
  const activeProductLabel = "label" in activeProduct ? activeProduct.label : activeProduct.name;

  const selectProduct = (id: string) => {
    setActiveProductId(id);
    try {
      if (id === "all") localStorage.removeItem(PRODUCT_FAMILY_STORAGE_KEY);
      else localStorage.setItem(PRODUCT_FAMILY_STORAGE_KEY, id);
    } catch { /* ignore */ }
    setProductPickerOpen(false);
  };

  const effectiveProjectId = projectId ?? ctxProjectId ?? storedProjectId ?? projects[0]?.id;
  const currentProject = projects.find(p => p.id === effectiveProjectId);

  // Stale localStorage cleanup: stored project no longer exists in fetched list.
  // Without this, deleted projects keep generating /p/<gone-id>/* URLs that 404.
  useEffect(() => {
    if (projects.length === 0) return; // not loaded yet
    if (!storedProjectId) return;
    if (projects.some(p => p.id === storedProjectId)) return; // still valid
    try { localStorage.removeItem("bgts_active_project"); } catch { /* ignore */ }
    setStoredProjectId(null);
  }, [projects, storedProjectId]);

  useEffect(() => { setSidebarOpen(false); }, [path]);

  // ─── FAZ B: Per-ürün tema — html'e data-product ekle ─────────────────────
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (activeProductId === "all") {
      document.documentElement.removeAttribute("data-product");
    } else {
      document.documentElement.setAttribute("data-product", activeProductId);
    }
    return () => {
      if (typeof document !== "undefined") {
        document.documentElement.removeAttribute("data-product");
      }
    };
  }, [activeProductId]);

  const hamburgerRef = useRef<HTMLButtonElement | null>(null);

  // ─── Sidebar içeriği ────────────────────────────────────────────────────────
  const SidebarContent = () => (
    <div className="flex h-full flex-col">

      {/* Logo + Ürün Selector */}
      <div className="relative border-b border-gray-100 dark:border-slate-700">
        <div className="flex items-center gap-3 px-5 py-4">
          <Link
            href={activeProductId === "all" ? "/" : `/products/${activeProductId}`}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl shadow-md transition-colors duration-base"
            style={{
              background: activeProductId === "all"
                ? "linear-gradient(135deg, #2563eb, #6366f1, #8b5cf6)"
                : `linear-gradient(135deg, var(--brand-primary), var(--brand-secondary, var(--brand-primary)))`,
            }}
            data-testid="sidebar-logo"
          >
            <span className="text-sm font-black text-white">
              {activeProductId === "all" ? "NX" : (PRODUCT_FAMILY.find(p => p.id === activeProductId)?.shortName?.[0] ?? "N")}
            </span>
          </Link>
          <button
            type="button"
            onClick={() => setProductPickerOpen(v => !v)}
            className="flex min-w-0 flex-1 items-center gap-1 rounded-lg px-1.5 py-1 -mx-1.5 hover:bg-slate-700/50 transition-colors"
            data-testid="sidebar-product-picker"
            aria-haspopup="menu"
            aria-expanded={productPickerOpen}
          >
            <div className="min-w-0 flex-1 text-left">
              <p className="truncate text-sm font-bold text-gray-900 dark:text-white">Neurex QA</p>
              <p className="truncate text-[10px] text-gray-500 dark:text-slate-400 -mt-0.5">{activeProductLabel}</p>
            </div>
            <IconChevron open={productPickerOpen} />
          </button>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="shrink-0 rounded-lg p-1 text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-700 dark:hover:text-white md:hidden"
            aria-label="Menüyü kapat"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Ürün picker dropdown */}
        {productPickerOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setProductPickerOpen(false)} />
            <div role="menu" className="absolute left-3 right-3 top-full z-50 mt-1 rounded-xl border border-slate-700 bg-slate-800 py-1 shadow-2xl max-h-[80vh] overflow-y-auto animate-slide-down origin-top">
              <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Ürün Odağı</p>
              <button
                type="button"
                role="menuitem"
                onClick={() => selectProduct("all")}
                className={cn(
                  "flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors",
                  activeProductId === "all" ? "bg-blue-900/30 text-blue-300" : "text-slate-300 hover:bg-slate-700 hover:text-white"
                )}
              >
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-slate-600 to-slate-700 text-[10px] font-bold text-white">★</div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">QA Operations Platform</p>
                  <p className="truncate text-[10px] text-slate-500">Tüm ürünler — varsayılan görünüm</p>
                </div>
                {activeProductId === "all" && (
                  <svg className="h-4 w-4 shrink-0 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
              <div className="my-1 border-t border-slate-700" />
              {PRODUCT_FAMILY.map(p => {
                const isActive = activeProductId === p.id;
                const meta = PRODUCT_AVAILABILITY_META[p.availability];
                const initial = p.shortName[0]?.toUpperCase() ?? "?";
                const brand = PRODUCT_BRAND[p.id as ProductFamilyId];
                return (
                  <button
                    key={p.id}
                    type="button"
                    role="menuitem"
                    onClick={() => { selectProduct(p.id); router.push(`/products/${p.id}`); }}
                    className={cn(
                      "flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors",
                      isActive
                        ? `${brand?.bg ?? "bg-blue-900/30"} ${brand?.text ?? "text-blue-300"}`
                        : "text-slate-300 hover:bg-slate-700 hover:text-white"
                    )}
                    data-testid={`product-picker-${p.id}`}
                  >
                    <div
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${brand?.gradient ?? "from-violet-600 to-indigo-600"} text-[10px] font-bold text-white`}
                    >
                      {initial}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className="truncate text-sm font-medium">{p.name}</p>
                        <span className={`shrink-0 rounded-full px-1 py-0 text-[8px] font-semibold ${meta.className}`}>{meta.label}</span>
                      </div>
                      <p className="truncate text-[10px] text-slate-500">{p.tagline}</p>
                    </div>
                    {isActive && (
                      <svg className={`h-4 w-4 shrink-0 ${brand?.text ?? "text-blue-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Sidebar quick search */}
      <SidebarSearch
        items={[
          { label: "Knowledge Base", path: "/kb", group: "Yardım" },
          { label: "Workflow Galerisi", path: "/workflows-gallery", group: "Yardım" },
          { label: "Status", path: "/status", group: "Sistem" },
          ...(currentProject
            ? [
                { label: "Senaryolar", path: `/p/${currentProject.id}/scenarios`, group: "Proje" },
                { label: "Koşumlar", path: `/p/${currentProject.id}/executions`, group: "Proje" },
                { label: "Mobil", path: `/p/${currentProject.id}/mobile`, group: "Proje" },
                { label: "API Test", path: `/p/${currentProject.id}/api-tests`, group: "Proje" },
                { label: "Flaky", path: `/p/${currentProject.id}/flaky`, group: "Proje" },
                { label: "Pipeline", path: `/p/${currentProject.id}/pipeline`, group: "Proje" },
              ]
            : []),
        ]}
      />

      {/* Recent + Favorites */}
      <RecentFavoritesPanel />

      {/* Navigation — ya global ya da ürün-spesifik */}
      <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5" data-testid="sidebar-nav">

        {activeProductId === "all" ? (
          /* MOD 1: GLOBAL — tüm linkler */
          GLOBAL_NAV.map(({ section, items }) => (
            <div key={section}>
              <p className="mb-1 mt-4 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-slate-500 first:mt-1">
                {section}
              </p>
              {items.map(item => (
                <NavItem
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={navActive(path, item.href, "exact" in item ? item.exact : false)}
                  testId={`sidebar-link-${item.href.replace(/\//g, "-").replace(/^-/, "")}`}
                />
              ))}
            </div>
          ))
        ) : (
          /* MOD 2: ÜRÜN MİNİ-UYGULAMASI */
          (() => {
            const productId = activeProductId as ProductFamilyId;
            const modules = PROJECT_NAV_DEFINITIONS.filter(d =>
              d.productIds.includes(productId) && d.path !== null && d.group
            );
            const groups = new Map<string, typeof modules>();
            for (const m of modules) {
              const g = m.group || "Diğer";
              if (!groups.has(g)) groups.set(g, []);
              groups.get(g)!.push(m);
            }
            return (
              <>
                {/* "Tüm Ürünlere Dön" */}
                <button
                  type="button"
                  onClick={() => selectProduct("all")}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-slate-400 hover:text-white hover:bg-slate-700 transition-colors mb-2"
                  data-testid="sidebar-back-to-all"
                >
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                  Tüm Ürünlere Dön
                </button>

                {/* PANEL bölümü */}
                <p className="mb-1 mt-1 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-slate-500">
                  Panel
                </p>
                <NavItem
                  href={`/products/${activeProductId}`}
                  label="Genel Bakış"
                  icon={<IconChart />}
                  active={path === `/products/${activeProductId}`}
                  testId="sidebar-product-overview"
                />
                <NavItem
                  href="/portfolio"
                  label="Projeler"
                  icon={<IconFolder />}
                  active={navActive(path, "/portfolio")}
                  testId="sidebar-product-portfolio"
                />

                {/* Modül grupları — proje varsa link, yoksa portfolio'ya yönlendir */}
                {Array.from(groups.entries()).map(([groupLabel, items]) => (
                  <div key={groupLabel}>
                    <p className="mb-1 mt-4 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-slate-500">
                      {NAV_GROUP_LABELS[groupLabel] ?? groupLabel}
                    </p>
                    {items.map(m => {
                      const href = currentProject
                        ? `/p/${currentProject.id}/${m.path}`
                        : `/portfolio?next=${m.path}`;
                      const isActive = currentProject && (path === href || path?.startsWith(`${href}/`));
                      return (
                        <Link
                          key={m.key}
                          href={href}
                          className={cn(
                            "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 relative",
                            isActive
                              ? "bg-blue-50/80 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:w-1 before:h-6 before:bg-blue-600 dark:before:bg-blue-400 before:rounded-r-full"
                              : "text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-white"
                          )}
                          data-testid={`product-module-${m.key}`}
                          title={!currentProject ? "Önce bir proje seçin" : undefined}
                        >
                          <span className={cn("text-gray-400 dark:text-slate-400 w-4 h-4 shrink-0", isActive && "text-blue-600 dark:text-blue-400")}>•</span>
                          {m.label}
                          {!currentProject && (
                            <svg className="ml-auto h-3 w-3 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          )}
                        </Link>
                      );
                    })}
                  </div>
                ))}
              </>
            );
          })()
        )}

      </nav>

      {/* Aktif proje seçici */}
      <SidebarProjectSwitcher />

      {/* Alt bölüm: dil + çıkış */}
      <div className="border-t border-gray-100 dark:border-slate-700 px-3 py-3 space-y-1">
        <button
          type="button"
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-slate-700 transition-all duration-150"
        >
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
          </svg>
          <span>Türkçe</span>
          <span className="ml-auto rounded border border-gray-200 dark:border-slate-600 px-1.5 py-0.5 text-[10px] font-semibold text-gray-500 dark:text-slate-400">TR</span>
        </button>
        <button
          type="button"
          onClick={async () => {
            try { await fetch(`${ENGINE_BASE}/api/auth/logout`, { method: "POST", credentials: "include" }); } catch {}
            clearTokens();
            window.location.href = "/login";
          }}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-gray-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-150"
          data-testid="sidebar-btn-logout"
        >
          <IconLogout />
          Çıkış
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen flex-col bg-slate-900">
      {topBanner}
      <div className="flex min-h-0 flex-1">

        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-none"
          data-testid="skip-to-content"
        >
          Ana içeriğe atla
        </a>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-30 bg-black/60 md:hidden" onClick={() => setSidebarOpen(false)} aria-hidden="true" />
        )}

        {/* Sidebar */}
        <aside
          className={cn(
            "flex w-64 flex-col border-r border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800",
            "fixed inset-y-0 left-0 z-40 transition-transform duration-200 md:static md:translate-x-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
          )}
          data-testid="sidebar"
          role="navigation"
          aria-label="Ana navigasyon"
        >
          <SidebarContent />
        </aside>

        {/* İçerik alanı */}
        <div className="flex min-w-0 flex-1 flex-col">

          {/* Header */}
          <header
            className="relative flex h-12 items-center gap-3 border-b border-white/10 bg-slate-900/80 backdrop-blur-sm px-4"
            data-testid="header"
          >
            {/* Per-ürün accent çizgisi — sadece ürün modunda */}
            {activeProductId !== "all" && (
              <span
                className="absolute bottom-0 left-0 right-0 h-px"
                style={{ background: "linear-gradient(90deg, transparent, var(--brand-primary), transparent)" }}
                aria-hidden="true"
              />
            )}
            {/* Mobile hamburger */}
            <button
              type="button"
              ref={hamburgerRef}
              className="shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-white md:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Menüyü aç"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Breadcrumb */}
            <nav className="flex min-w-0 flex-1 items-center gap-1.5 text-sm text-slate-400" aria-label="breadcrumb">
              <Link href="/" className="shrink-0 font-semibold text-blue-400 hover:text-blue-300 transition-colors" data-testid="header-breadcrumb-home">
                {PRODUCT_SHORT}
              </Link>
              {currentProject && (
                <>
                  <svg className="h-3.5 w-3.5 shrink-0 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                  <Link href={`/p/${currentProject.id}/scenarios`} className="truncate font-medium text-slate-300 hover:text-white transition-colors" data-testid="header-breadcrumb-project">
                    {currentProject.name}
                  </Link>
                </>
              )}
            </nav>

            {/* Proje pill — hızlı proje değiştirme */}
            <div className="relative shrink-0 hidden md:block">
              <button
                type="button"
                onClick={() => setProjectDropOpen(v => !v)}
                className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-medium text-slate-300 hover:border-blue-500/50 hover:text-blue-300 transition-colors"
                aria-haspopup="menu"
                aria-expanded={projectDropOpen}
                data-testid="header-project-pill"
              >
                <IconFolder />
                <span className="max-w-[130px] truncate">
                  {currentProject ? currentProject.name : "Proje Seç"}
                </span>
                <IconChevron open={projectDropOpen} />
              </button>
              {projectDropOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setProjectDropOpen(false)} />
                  <div role="menu" className="absolute left-1/2 top-full z-50 mt-2 w-64 -translate-x-1/2 rounded-xl border border-slate-700 bg-slate-800 py-1 shadow-2xl animate-slide-down origin-top">
                    {currentProject && (
                      <div className="border-b border-slate-700 px-3 py-2">
                        <p className="text-[10px] uppercase tracking-wider text-slate-500">Aktif Proje</p>
                        <p className="text-sm font-semibold text-white truncate">{currentProject.name}</p>
                      </div>
                    )}
                    {projects.length > 0 && (
                      <div className={cn("py-1 max-h-56 overflow-y-auto", currentProject && projects.filter(p => p.id !== currentProject.id).length > 0 && "border-b border-slate-700")}>
                        {currentProject && <p className="px-3 pt-1 pb-1 text-[10px] uppercase tracking-wider text-slate-500">Diğer Projeler</p>}
                        {projects
                          .filter(p => !currentProject || p.id !== currentProject.id)
                          .slice(0, 6)
                          .map(p => {
                            const sub = currentProject && path?.startsWith(`/p/${currentProject.id}/`)
                              ? path.slice(`/p/${currentProject.id}`.length)
                              : "/scenarios";
                            return (
                              <button key={p.id} type="button" role="menuitem"
                                onClick={() => { setProjectDropOpen(false); router.push(`/p/${p.id}${sub}`); }}
                                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                                data-testid={`header-project-pill-switch-${p.id}`}
                              >
                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-slate-500" />
                                <span className="truncate">{p.name}</span>
                              </button>
                            );
                          })}
                      </div>
                    )}
                    <Link href="/portfolio" className="flex items-center gap-2 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setProjectDropOpen(false)} data-testid="header-project-pill-all">
                      <IconFolder />
                      Tüm Projeler
                    </Link>
                  </div>
                </>
              )}
            </div>

            {/* Sağ aksiyonlar */}
            <div className="flex shrink-0 items-center gap-2">
            <AiStatusChip />
            <ServiceRestartButton />
            <ThemeToggle />
            <NotificationBell />
            <NotificationCenter />
            <KeyboardShortcutsHelp
              shortcuts={[
                { combo: "mod+k", description: "Komut paleti", handler: () => {} },
                { combo: "mod+j", description: "AI asistan", handler: () => {} },
                { combo: "g s", description: "Senaryolara git", handler: () => {} },
                { combo: "g r", description: "Çalıştırmalara git", handler: () => {} },
                { combo: "?", description: "Kısayolları göster", handler: () => {} },
              ]}
            />

            {/* Kullanıcı menüsü */}
              <div data-testid="user-menu" className="relative">
                <button
                  type="button"
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-600 text-xs font-bold text-white transition hover:bg-violet-500"
                  aria-label="Kullanıcı menüsü"
                  data-testid="header-btn-user-menu"
                >
                  YB
                </button>
                {userMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                    <div className="absolute right-0 top-full z-50 mt-2 w-52 rounded-xl border border-slate-700 bg-slate-800 py-1 shadow-xl animate-slide-down origin-top-right">
                      <div className="border-b border-slate-700 px-3 py-2">
                        <p className="text-sm font-medium text-white">Yasin Bulgan</p>
                        <p className="text-xs text-slate-400">yasin.bulgan@bgtest.com</p>
                      </div>
                      <Link href="/profile" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-profile">Profil</Link>
                      <Link href="/admin/users" className="flex items-center gap-2 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-admin"><IconUsers />Yönetim</Link>
                      <Link href="/ai-quality" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-aiq">AI Kalite</Link>
                      <Link href="/ai-workflows" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-ai-workflows">Workflow Health</Link>
                      <Link href="/mobil-otomasyon" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-mobil">Mobil Otomasyon</Link>
                      <Link href="/admin/billing" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-billing">Faturalama</Link>
                      <Link href="/system" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-system">Sistem Durumu</Link>
                      <Link href="/system/services" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-services">Servis Yönetimi</Link>
                      <Link href="/info" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-info">Sistem Bilgileri</Link>
                      <Link href="/symbols" className="block px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors" onClick={() => setUserMenuOpen(false)} data-testid="user-menu-link-symbols">Tasarım Sözlüğü</Link>
                      <div className="border-t border-slate-700" />
                      <button
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm text-rose-400 hover:bg-rose-500/10 transition-colors"
                        onClick={async () => {
                          setUserMenuOpen(false);
                          try { await fetch(`${ENGINE_BASE}/api/auth/logout`, { method: "POST", credentials: "include" }); } catch {}
                          clearTokens();
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

          {/* Ana içerik */}
          <main id="main-content" tabIndex={-1} className="flex-1 bg-slate-900 focus:outline-none overflow-auto">
            {children}
          </main>
        </div>
      </div>

      {/* AI Asistan Panel — global, Cmd+J ile açılır */}
      <AiAssistantPanel />

      {/* İlk girişte tur */}
      <OnboardingTour />
    </div>
  );
}
