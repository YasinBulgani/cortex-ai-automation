"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useProjects } from "@/lib/hooks";

// ─── Icons ────────────────────────────────────────────────────────────────────

function IcDatabase() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <ellipse cx="12" cy="5" rx="9" ry="3"/>
      <path d="M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3"/>
      <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/>
    </svg>
  );
}
function IcHome() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 10.5L12 3l9 7.5"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 10v10h14V10"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 20v-6h6v6"/>
    </svg>
  );
}
function IcCalendar() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
      <line x1="16" y1="2" x2="16" y2="6"/>
      <line x1="8" y1="2" x2="8" y2="6"/>
      <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
  );
}
function IcBug() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M8 2a2 2 0 014 0M16 2a2 2 0 00-4 0M5 8h14M5 8a7 7 0 0014 0M5 8l-2-2m16 2 2-2M7 14H4m16 0h-3m-6 6v-6m0 6H8m4 0h4"/>
    </svg>
  );
}
function IcRefresh() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M1 4v6h6M23 20v-6h-6"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
    </svg>
  );
}
function IcPlay() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <circle cx="12" cy="12" r="9"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 8l6 4-6 4V8z"/>
    </svg>
  );
}
function IcLink() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
    </svg>
  );
}
function IcChart() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
      <line x1="2" y1="20" x2="22" y2="20"/>
    </svg>
  );
}
function IcUpload() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
      <polyline strokeLinecap="round" strokeLinejoin="round" points="17 8 12 3 7 8"/>
      <line strokeLinecap="round" x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  );
}
function IcGrid() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <rect x="3" y="3" width="7" height="7" rx="1.5"/>
      <rect x="14" y="3" width="7" height="7" rx="1.5"/>
      <rect x="3" y="14" width="7" height="7" rx="1.5"/>
      <rect x="14" y="14" width="7" height="7" rx="1.5"/>
    </svg>
  );
}

function IcGear() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <circle cx="12" cy="12" r="3"/>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
    </svg>
  );
}
function IcUser() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
}
function IcPulse() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <polyline strokeLinecap="round" strokeLinejoin="round" points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  );
}

// ─── Nav config ───────────────────────────────────────────────────────────────

type NavItem = { label: string; segment: string; Icon: () => React.ReactElement };
type NavGroup = { label: string; items: NavItem[] };

const NAV_GROUPS: NavGroup[] = [
  {
    label: "QA Akışı",
    items: [
      { label: "Dashboard",       segment: "management/dashboard",    Icon: IcHome     },
      { label: "Test Deposu",     segment: "management/repository",   Icon: IcDatabase },
      { label: "Planlar",         segment: "management/plans",        Icon: IcCalendar },
      { label: "Test Koşuları",   segment: "management/runs",         Icon: IcPlay     },
      { label: "Regresyon",       segment: "management/regression",   Icon: IcRefresh  },
    ],
  },
  {
    label: "Analiz",
    items: [
      { label: "Gereksinimler",   segment: "management/requirements", Icon: IcLink  },
      { label: "Defektler",       segment: "management/defects",      Icon: IcBug   },
      { label: "Raporlar",        segment: "management/reports",      Icon: IcChart },
      { label: "Tester",          segment: "management/tester",       Icon: IcUser  },
      { label: "Stand-up",        segment: "management/standup",      Icon: IcPulse },
    ],
  },
  {
    label: "Test Tasarımı",
    items: [
      { label: "BVA",                    segment: "management/design/bva",  Icon: IcGrid },
      { label: "Eşdeğerlik Bölümü",      segment: "management/design/eq",   Icon: IcGrid },
      { label: "Karar Tablosu",          segment: "management/design/dt",   Icon: IcGrid },
    ],
  },
];

const NAV_UTILITY: NavItem[] = [
  { label: "İçe/Dışa Aktar",  segment: "management/import-export", Icon: IcUpload },
  { label: "Entegrasyonlar",  segment: "management/integrations",  Icon: IcLink   },
  { label: "Denetim İzi",     segment: "management/audit",         Icon: IcPulse  },
  { label: "Ayarlar",         segment: "management/settings",      Icon: IcGear   },
];

// Execute sayfası tam ekran — sidebar gizlenir
const HIDE_SIDEBAR_PATTERNS = ["/execute"];

// ─── Project Picker ──────────────────────────────────────────────────────────

function ProjectPicker({ projectId }: { projectId: string }) {
  const { data: projects = [], isLoading } = useProjects();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = projects.find(p => p.id === projectId);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  function handleSelect(id: string) {
    setOpen(false);
    if (id !== projectId) {
      router.push(`/p/${id}/management/dashboard`);
    }
  }

  return (
    <div ref={ref} className="relative border-b border-border bg-surface-raised">
      {/* Trigger */}
      <button
        onClick={() => setOpen(v => !v)}
        className="group flex w-full items-center gap-2.5 px-3 py-3 transition-colors hover:bg-surface-overlay"
      >
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-brand/15 bg-brand-soft">
          <svg className="h-3.5 w-3.5 text-brand" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
          </svg>
        </div>
        <div className="flex-1 min-w-0 text-left">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Proje</p>
          <p className="truncate text-[12px] font-semibold leading-tight text-fg group-hover:text-brand">
            {isLoading ? "Yükleniyor…" : (current?.name ?? "Proje Seç")}
          </p>
        </div>
        <svg
          className={cn("h-3.5 w-3.5 shrink-0 text-fg-subtle transition-transform", open && "rotate-180")}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute left-2 right-2 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-xl border border-border bg-surface-raised shadow-elevated">
          {isLoading ? (
            <div className="px-4 py-3 text-[12px] text-fg-subtle">Yükleniyor…</div>
          ) : projects.length === 0 ? (
            <div className="px-4 py-3 text-[12px] text-fg-subtle">Proje bulunamadı</div>
          ) : (
            projects.map(p => (
              <button
                key={p.id}
                onClick={() => handleSelect(p.id)}
                className={cn(
                  "flex w-full items-center gap-2.5 px-3 py-2.5 text-left transition-colors",
                  p.id === projectId
                    ? "bg-brand-soft text-fg"
                    : "text-fg-muted hover:bg-surface-overlay hover:text-fg",
                )}
              >
                <span className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded text-[9px] font-bold",
                  p.id === projectId ? "bg-brand-soft text-brand" : "bg-surface-overlay text-fg-subtle",
                )}>
                  {(p.name?.[0] ?? "P").toUpperCase()}
                </span>
                <span className="flex-1 min-w-0 truncate text-[12px]">{p.name}</span>
                {p.id === projectId && (
                  <svg className="h-3 w-3 shrink-0 text-brand" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                  </svg>
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ─── Layout ───────────────────────────────────────────────────────────────────

export default function ManagementLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { projectId: string };
}) {
  const { projectId } = params;
  const pathname = usePathname() ?? "";
  const router   = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isRoot      = pathname === `/p/${projectId}/management`;
  const hideSidebar = HIDE_SIDEBAR_PATTERNS.some(p => pathname.includes(p));

  const currentLabel = useMemo(() => {
    const allItems = [...NAV_GROUPS.flatMap(g => g.items), ...NAV_UTILITY];
    return allItems.find(item => pathname.includes(item.segment))?.label ?? "Management";
  }, [pathname]);

  useEffect(() => {
    if (isRoot) {
      router.replace(`/p/${projectId}/management/dashboard`);
    }
  }, [isRoot, projectId, router]);

  if (isRoot) {
    return (
      <div className="flex h-[calc(100vh-48px)] items-center justify-center bg-bg">
        <div className="h-4 w-4 rounded-full border-2 border-border border-t-blue-500 animate-spin" />
      </div>
    );
  }

  if (hideSidebar) {
    return (
      <div className="flex h-[calc(100vh-48px)] flex-col bg-bg">
        {children}
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-48px)] bg-bg">

      {/* ── Mobile backdrop ───────────────────────────────────────────────── */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setSidebarOpen(false)}/>
      )}

      {/* ── Left sidebar ──────────────────────────────────────────────────── */}
      <aside className={cn(
        "flex w-[208px] flex-none flex-col overflow-hidden border-r border-border bg-surface-raised shadow-sm",
        "fixed inset-y-0 left-0 z-50 transition-transform duration-200 md:relative md:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>

        {/* Project Picker */}
        <ProjectPicker projectId={projectId} />

        {/* Primary nav — grouped */}
        <nav className="flex-1 overflow-y-auto p-2">
          {NAV_GROUPS.map(group => (
            <div key={group.label}>
              <p className="px-3 pt-3 pb-1 text-[9px] font-semibold uppercase tracking-widest text-fg-subtle first:pt-1">
                {group.label}
              </p>
              {group.items.map(({ label, segment, Icon }) => {
                const href     = `/p/${projectId}/${segment}`;
                const isActive = pathname === `/p/${projectId}/${segment}` || pathname.startsWith(`/p/${projectId}/${segment}/`);
                return (
                  <Link key={segment} href={href} onClick={() => setSidebarOpen(false)}
                    className={cn(
                      "relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                      isActive
                        ? "bg-brand-soft text-brand shadow-xs"
                        : "text-fg-muted hover:bg-surface-overlay hover:text-fg",
                    )}>
                    <span className={cn("shrink-0", isActive ? "text-brand" : "text-fg-subtle")}>
                      <Icon />
                    </span>
                    {label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Utility nav */}
        <div className="border-t border-border p-2 space-y-0.5">
          {NAV_UTILITY.map(({ label, segment, Icon }) => {
            const href     = `/p/${projectId}/${segment}`;
            const isActive = pathname === `/p/${projectId}/${segment}` || pathname.startsWith(`/p/${projectId}/${segment}/`);
            return (
              <Link key={segment} href={href} onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                  isActive
                    ? "bg-brand-soft text-brand shadow-xs"
                    : "text-fg-muted hover:bg-surface-overlay hover:text-fg",
                )}>
                <span className={cn("shrink-0", isActive ? "text-brand" : "text-fg-subtle")}>
                  <Icon />
                </span>
                {label}
              </Link>
            );
          })}
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 flex-col overflow-auto bg-surface-base">
        {/* Mobile hamburger bar */}
        <div className="flex h-10 items-center border-b border-border bg-surface-base px-4 md:hidden">
          <button type="button" onClick={() => setSidebarOpen(true)}
            className="flex items-center gap-2 text-[12px] text-fg-muted hover:text-fg">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h7"/>
            </svg>
            Menu
          </button>
        </div>
        {/* Breadcrumb */}
        <div className="flex items-center gap-1.5 border-b border-border bg-surface-base px-4 py-2 text-[11px] shrink-0">
          <span className="font-semibold text-brand">Management</span>
          <span className="text-fg-subtle">›</span>
          <span className="text-fg">{currentLabel}</span>
        </div>
        {children}
      </div>
    </div>
  );
}
