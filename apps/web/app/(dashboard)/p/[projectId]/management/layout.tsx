"use client";

import React, { useEffect, useState, useRef, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useProjects } from "@/lib/hooks";
import { useKeyboardShortcuts } from "@/lib/useKeyboardShortcuts";
import { useI18n } from "@/lib/i18n";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { GlobalSearch } from "./_components/GlobalSearch";
import { NotificationBell } from "@/components/management/NotificationBell";
import { Button } from "@/components/ui/button";

// ─── Management Error Boundary ───────────────────────────────────────────────

class ManagementErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 p-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-subtle">
            <svg className="h-6 w-6 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
            </svg>
          </div>
          <div>
            <h3 className="text-[14px] font-semibold text-fg">Sayfa Yüklenemedi</h3>
            <p className="mt-1 text-[12px] text-fg-subtle">{this.state.error?.message ?? "Beklenmeyen bir hata oluştu."}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Tekrar Dene
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}

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
function IcInbox() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M22 12h-6l-2 3h-4l-2-3H2"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"/>
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
function IcUsers() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
      <circle cx="9" cy="7" r="4"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M23 21v-2a4 4 0 00-3-3.87"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M16 3.13a4 4 0 010 7.75"/>
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
function IcCopy() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
    </svg>
  );
}

function IcCode() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
    </svg>
  );
}
function IcMatrix() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/>
    </svg>
  );
}
function IcApi() {
  return (
    <svg className="h-[15px] w-[15px] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
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
      { label: "İşlerim",         segment: "management/my-work",      Icon: IcInbox    },
      { label: "Workspace",       segment: "management/workspace",    Icon: IcGrid     },
      { label: "Test Deposu",     segment: "management/repository",   Icon: IcDatabase },
      { label: "Planlar",         segment: "management/plans",        Icon: IcCalendar },
      { label: "Test Koşuları",   segment: "management/runs",         Icon: IcPlay     },
      { label: "Koşu Farkı",      segment: "management/runs/compare", Icon: IcMatrix   },
      { label: "Keşif Testi",     segment: "management/exploratory",  Icon: IcPulse    },
      { label: "Regresyon",       segment: "management/regression",   Icon: IcRefresh  },
    ],
  },
  {
    label: "Analiz",
    items: [
      { label: "Gereksinimler",   segment: "management/requirements",    Icon: IcLink   },
      { label: "İzlenebilirlik",  segment: "management/traceability",    Icon: IcMatrix },
      { label: "Defektler",       segment: "management/defects",         Icon: IcBug    },
      { label: "Raporlar",        segment: "management/reports",         Icon: IcChart  },
      { label: "Tester",          segment: "management/tester",          Icon: IcUser   },
      { label: "Stand-up",        segment: "management/standup",         Icon: IcPulse  },
      { label: "Mobil Test",      segment: "management/mobile",          Icon: IcGrid   },
      { label: "API Test",        segment: "api-testing",                Icon: IcApi    },
    ],
  },
  {
    label: "Test Tasarımı",
    items: [
      { label: "Tasarım Teknikleri",    segment: "management/design",        Icon: IcGrid },
      { label: "Paylaşılan Adımlar",    segment: "management/shared-steps",  Icon: IcCopy },
    ],
  },
];

const NAV_UTILITY: NavItem[] = [
  { label: "Üyeler",          segment: "management/members",       Icon: IcUsers  },
  { label: "Yetki Matrisi",   segment: "management/permissions",   Icon: IcMatrix },
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

// ─── Shortcuts Modal ─────────────────────────────────────────────────────────

type ShortcutEntry = { key: string; description: string };
type ShortcutGroup = { label: string; entries: ShortcutEntry[] };

const SHORTCUT_GROUPS: ShortcutGroup[] = [
  {
    label: "Navigasyon",
    entries: [
      { key: "G D",     description: "Dashboard'a git" },
      { key: "G W",     description: "Workspace'e git" },
      { key: "G R",     description: "Test Deposu'na git" },
      { key: "G P",     description: "Planlar'a git" },
      { key: "G U",     description: "Test Koşuları'na git" },
      { key: "G E",     description: "Regresyon'a git" },
      { key: "G Q",     description: "Gereksinimler'e git" },
      { key: "G X",     description: "İzlenebilirlik'e git" },
      { key: "G F",     description: "Defektler'e git" },
      { key: "G T",     description: "Raporlar'a git" },
      { key: "G S",     description: "Stand-up'a git" },
      { key: "G I",     description: "Ayarlar'a git" },
    ],
  },
  {
    label: "Case İşlemleri",
    entries: [
      { key: "Tıkla",   description: "Case seç / detay aç" },
      { key: "Sağ Tık", description: "Context menu aç" },
      { key: "Esc",     description: "Seçimi / modalı kapat" },
    ],
  },
  {
    label: "Genel",
    entries: [
      { key: "⌘⇧L",    description: "Dil değiştir (TR/EN)" },
      { key: "?",       description: "Kısayol yardım paneli" },
      { key: "Esc",     description: "Açık panelleri kapat" },
    ],
  },
];

function ShortcutsModal({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl border border-border bg-surface-raised shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h2 className="text-[15px] font-semibold text-fg">Klavye Kısayolları</h2>
            <p className="mt-0.5 text-[11px] text-fg-muted">Tüm Management modülü kısayolları</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Content — groups in 2-column grid */}
        <div className="grid gap-6 p-6 sm:grid-cols-2">
          {SHORTCUT_GROUPS.map(group => (
            <div key={group.label}>
              <p className="mb-3 text-[9px] font-bold uppercase tracking-widest text-fg-subtle">
                {group.label}
              </p>
              <div className="space-y-2">
                {group.entries.map(entry => (
                  <div key={entry.key} className="flex items-center justify-between gap-4">
                    <span className="text-[12px] text-fg-muted">{entry.description}</span>
                    <kbd className="shrink-0 rounded-md border border-border bg-surface-overlay px-2 py-0.5 font-mono text-[10px] text-fg-subtle shadow-xs">
                      {entry.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer hint */}
        <div className="border-t border-border bg-surface-overlay px-6 py-3 text-center">
          <p className="text-[10px] text-fg-subtle">
            <kbd className="rounded border border-border bg-surface-raised px-1.5 py-0.5 font-mono text-[9px]">Esc</kbd>
            {" "}veya dışarıya tıklayarak kapatın
          </p>
        </div>
      </div>
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
  const [sidebarOpen,    setSidebarOpen]    = useState(false);
  const [showShortcuts,  setShowShortcuts]  = useState(false);
  const [showSearch,     setShowSearch]     = useState(false);
  const mpid = useManagementProjectId(projectId);

  const isRoot      = pathname === `/p/${projectId}/management`;
  const hideSidebar = HIDE_SIDEBAR_PATTERNS.some(p => pathname.includes(p));
  const { locale, setLocale } = useI18n();

  // The single most-specific (longest) nav segment that matches the current path.
  // Prevents a parent item (e.g. "Test Koşuları" → management/runs) from also
  // highlighting when a child route ("Koşu Farkı" → management/runs/compare) is active.
  const activeSegment = useMemo(() => {
    const allItems = [...NAV_GROUPS.flatMap(g => g.items), ...NAV_UTILITY];
    const base = `/p/${projectId}/`;
    const matches = allItems
      .map(i => i.segment)
      .filter(seg => pathname === `${base}${seg}` || pathname.startsWith(`${base}${seg}/`));
    return matches.sort((a, b) => b.length - a.length)[0] ?? null;
  }, [pathname, projectId]);

  const currentLabel = useMemo(() => {
    const allItems = [...NAV_GROUPS.flatMap(g => g.items), ...NAV_UTILITY];
    return allItems.find(item => item.segment === activeSegment)?.label ?? "Management";
  }, [activeSegment]);

  useEffect(() => {
    if (isRoot) {
      router.replace(`/p/${projectId}/management/dashboard`);
    }
  }, [isRoot, projectId, router]);

  // ── Keyboard shortcuts (chord navigation) ──────────────────────────────────
  useKeyboardShortcuts(useMemo(() => [
    { combo: "g d", description: "Dashboard'a git", handler: () => router.push(`/p/${projectId}/management/dashboard`) },
    { combo: "g m", description: "İşlerim'e git", handler: () => router.push(`/p/${projectId}/management/my-work`) },
    { combo: "g w", description: "Workspace'e git", handler: () => router.push(`/p/${projectId}/management/workspace`) },
    { combo: "g r", description: "Test Deposu'na git", handler: () => router.push(`/p/${projectId}/management/repository`) },
    { combo: "g p", description: "Planlar'a git", handler: () => router.push(`/p/${projectId}/management/plans`) },
    { combo: "g u", description: "Test Koşuları'na git", handler: () => router.push(`/p/${projectId}/management/runs`) },
    { combo: "g e", description: "Regresyon'a git", handler: () => router.push(`/p/${projectId}/management/regression`) },
    { combo: "g q", description: "Gereksinimler'e git", handler: () => router.push(`/p/${projectId}/management/requirements`) },
    { combo: "g x", description: "İzlenebilirlik'e git", handler: () => router.push(`/p/${projectId}/management/traceability`) },
    { combo: "g f", description: "Defektler'e git", handler: () => router.push(`/p/${projectId}/management/defects`) },
    { combo: "g t", description: "Raporlar'a git", handler: () => router.push(`/p/${projectId}/management/reports`) },
    { combo: "g s", description: "Stand-up'a git", handler: () => router.push(`/p/${projectId}/management/standup`) },
    { combo: "g a", description: "API Test'e git", handler: () => router.push(`/p/${projectId}/api-testing`) },
    { combo: "g i", description: "Ayarlar'a git", handler: () => router.push(`/p/${projectId}/management/settings`) },
    { combo: "mod+shift+l", description: "Dil değiştir (TR/EN)", handler: () => setLocale(locale === "tr" ? "en" : "tr") },
    { combo: "?", description: "Kısayol yardım paneli", handler: () => setShowShortcuts(true) },
    { combo: "mod+k", description: "Global Arama", handler: () => setShowSearch(true) },
  ], [projectId, router, locale, setLocale, setShowShortcuts, setShowSearch]));

  if (isRoot) {
    return (
      <div className="flex h-[calc(100vh-48px)] items-center justify-center bg-surface-base">
        <div className="h-4 w-4 rounded-full border-2 border-border border-t-blue-500 animate-spin" />
      </div>
    );
  }

  if (hideSidebar) {
    return (
      <div className="flex h-[calc(100vh-48px)] flex-col bg-surface-base">
        {children}
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-48px)] bg-surface-base">

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

        {/* Global Search trigger */}
        <div className="px-2 py-2 border-b border-border">
          <button
            type="button"
            onClick={() => setShowSearch(true)}
            className="flex w-full items-center gap-2 rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg-subtle transition-colors hover:border-brand/40 hover:bg-surface-overlay hover:text-fg"
          >
            <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <circle cx="11" cy="11" r="8"/>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35"/>
            </svg>
            <span className="flex-1 text-left">Ara…</span>
            <kbd className="rounded border border-border/50 bg-surface-raised px-1.5 py-0.5 font-mono text-[9px] text-fg-disabled">
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Primary nav — grouped */}
        <nav aria-label="Yönetim navigasyonu" className="flex-1 overflow-y-auto p-2">
          {NAV_GROUPS.map(group => (
            <div key={group.label}>
              <p className="px-3 pt-3 pb-1 text-[9px] font-semibold uppercase tracking-widest text-fg-subtle first:pt-1">
                {group.label}
              </p>
              {group.items.map(({ label, segment, Icon }) => {
                const href     = `/p/${projectId}/${segment}`;
                const isActive = segment === activeSegment;
                return (
                  <Link key={segment} href={href} onClick={() => setSidebarOpen(false)}
                    aria-current={isActive ? "page" : undefined}
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
            const isActive = segment === activeSegment;
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

          {/* Language toggle */}
          <button
            type="button"
            onClick={() => setLocale(locale === "tr" ? "en" : "tr")}
            title="Dil değiştir (⌘⇧L)"
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg"
          >
            <span className="shrink-0 text-fg-subtle">
              <svg className="h-[15px] w-[15px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/>
              </svg>
            </span>
            <span className="flex-1">{locale === "tr" ? "English" : "Türkçe"}</span>
            <span className="rounded border border-border bg-surface-overlay px-1.5 py-0.5 font-mono text-[9px] text-fg-disabled">
              {locale.toUpperCase()}
            </span>
          </button>
        </div>

        {/* Shortcut hint — hidden on mobile */}
        <div className="hidden md:block border-t border-border px-3 py-2">
          <button
            type="button"
            onClick={() => setShowShortcuts(true)}
            className="flex w-full items-center justify-between text-[9px] text-fg-disabled hover:text-fg-subtle transition-colors"
          >
            <span className="font-mono">g d/w/r/p/u/s</span>
            <span className="rounded border border-border/50 px-1 py-0.5 font-mono text-[8px]">?</span>
          </button>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 flex-col overflow-auto bg-surface-base">
        {/* Mobile hamburger bar */}
        <div className="flex h-10 items-center justify-between border-b border-border bg-surface-base px-4 md:hidden">
          <button type="button" onClick={() => setSidebarOpen(true)}
            className="flex items-center gap-2 text-[12px] text-fg-muted hover:text-fg">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h7"/>
            </svg>
            <span className="font-semibold text-fg">Management</span>
          </button>
          <span className="text-[11px] text-fg-muted">{currentLabel}</span>
        </div>
        {/* Breadcrumb + notification bell */}
        <div className="flex items-center justify-between gap-1.5 border-b border-border bg-surface-base px-4 py-2 shrink-0">
          <div className="flex items-center gap-1.5 text-[11px]">
            <span className="font-semibold text-brand">Management</span>
            <span className="text-fg-subtle">›</span>
            <span className="text-fg">{currentLabel}</span>
          </div>
          <NotificationBell projectId={projectId} className="scale-90" />
        </div>
        <ManagementErrorBoundary>
          {children}
        </ManagementErrorBoundary>
      </div>

      {/* Keyboard Shortcuts Modal */}
      {showShortcuts && <ShortcutsModal onClose={() => setShowShortcuts(false)} />}

      {/* Global Search Modal */}
      {showSearch && (
        <GlobalSearch
          projectId={projectId}
          mpid={mpid ?? null}
          onClose={() => setShowSearch(false)}
        />
      )}
    </div>
  );
}
