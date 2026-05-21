"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useProject } from "@/lib/useProject";
import { useMyInbox, webDashboardKeys, type InboxItem, type InboxKind } from "@/lib/hooks/use-web-dashboard";
import { useToast } from "@/components/ui/toast";
import { InboxItemDrawer } from "./InboxItemDrawer";

type Kind = InboxKind;

const DEMO_ITEMS: InboxItem[] = [
  { id: "1", kind: "approve",     title: "Checkout Step 2 — visual diff onayı bekliyor",  context: "12.4% pixel diff · v2.4.0 → v2.5.0",      age: "23 dk",  priority: "high" },
  { id: "2", kind: "fix",         title: "Auth flow test'in 3 koşudur flaky",              context: "Safari 17.4 · 'token undefined' hatası",   age: "1 sa",   priority: "high" },
  { id: "3", kind: "review",      title: "PR #482 — locator değişikliği",                   context: "47 test bu locator'ı kullanıyor",          age: "2 sa",   priority: "med"  },
  { id: "4", kind: "investigate", title: "Homepage LCP 2.5s → 2.9s yükseldi",              context: "Son deploy sonrası perf regression",       age: "4 sa",   priority: "med"  },
  { id: "5", kind: "approve",     title: "Profile page — yeni baseline alındı",            context: "AI 'kabul edilebilir' diyor (skor 0.94)",  age: "6 sa",   priority: "low"  },
];

const KIND_META = {
  review:      { icon: "👀", label: "İncele",   cls: "bg-sky-500/15 text-sky-300 border-sky-500/30" },
  approve:     { icon: "✅", label: "Onayla",   cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  fix:         { icon: "🔧", label: "Düzelt",   cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  investigate: { icon: "🔎", label: "Araştır",  cls: "bg-violet-500/15 text-violet-300 border-violet-500/30" },
} as const;

const PRIORITY_DOT = {
  high: "bg-rose-400",
  med:  "bg-amber-400",
  low:  "bg-slate-500",
} as const;

function InboxSkeleton() {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5 animate-pulse">
          <div className="h-9 w-9 rounded-xl bg-slate-800" />
          <div>
            <div className="h-3 w-20 rounded bg-slate-800 mb-1.5" />
            <div className="h-2 w-32 rounded bg-slate-800" />
          </div>
        </div>
      </div>
      <ul className="divide-y divide-slate-800/60">
        {Array.from({ length: 4 }).map((_, i) => (
          <li key={i} className="px-5 py-3 flex items-center gap-3 animate-pulse">
            <div className="h-2 w-2 rounded-full bg-slate-800" />
            <div className="h-4 w-16 rounded bg-slate-800" />
            <div className="flex-1">
              <div className="h-3 w-3/4 rounded bg-slate-800 mb-1.5" />
              <div className="h-2 w-1/2 rounded bg-slate-800" />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

const ACTION_LABEL: Record<string, string> = {
  approve:  "Onaylandı",
  reject:   "Reddedildi",
  snooze:   "24 saat ertelendi",
  reassign: "Devredildi",
};

export function MyInbox() {
  const { projectId } = useProject();
  const qc = useQueryClient();
  const { toast } = useToast();
  const { data, isLoading } = useMyInbox(projectId);
  const items = data?.items ?? DEMO_ITEMS;
  const isDemo = !data && !isLoading;
  const [openItem, setOpenItem] = useState<InboxItem | null>(null);
  const [filter, setFilter] = useState<"all" | Kind>("all");

  if (isLoading) return <InboxSkeleton />;
  const filtered = filter === "all" ? items : items.filter((i) => i.kind === filter);
  const counts = {
    all: items.length,
    review:      items.filter((i) => i.kind === "review").length,
    approve:     items.filter((i) => i.kind === "approve").length,
    fix:         items.filter((i) => i.kind === "fix").length,
    investigate: items.filter((i) => i.kind === "investigate").length,
  };

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-rose-500 to-orange-500 flex items-center justify-center text-base shrink-0">
            📥
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-white truncate">My Inbox</h2>
              {isDemo && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">
                  Demo
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 truncate">
              <span className="text-rose-300 font-semibold">{items.filter((i) => i.priority === "high").length} yüksek</span>
              {" · "}sana atanmış {items.length} açık iş
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-[11px]">
          {(["all", "approve", "fix", "review", "investigate"] as const).map((k) => {
            const label = k === "all" ? "Tümü" : KIND_META[k as Kind].label;
            const active = filter === k;
            return (
              <button
                key={k}
                onClick={() => setFilter(k)}
                className={`px-2 py-1 rounded-md font-medium transition-colors ${
                  active
                    ? "bg-slate-800 text-white"
                    : "text-slate-500 hover:text-slate-200"
                }`}
              >
                {label}
                <span className="ml-1 text-[10px] text-slate-500">{counts[k]}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Items */}
      <ul className="divide-y divide-slate-800/60">
        {filtered.length === 0 ? (
          <li className="px-5 py-8 text-center text-sm text-slate-500">Bu filtrede iş yok 🎉</li>
        ) : (
          filtered.map((item) => {
            const k = KIND_META[item.kind];
            return (
              <li
                key={item.id}
                onClick={() => setOpenItem(item)}
                className="px-5 py-3 flex items-center gap-3 hover:bg-slate-800/30 cursor-pointer transition-colors"
              >
                <span className={`h-2 w-2 rounded-full ${PRIORITY_DOT[item.priority]} shrink-0`} />
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${k.cls} shrink-0`}>
                  {k.icon} {k.label}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-white truncate">{item.title}</p>
                  <p className="text-[11px] text-slate-400 truncate">{item.context}</p>
                </div>
                <span className="text-[11px] text-slate-500 shrink-0">{item.age}</span>
                <span className="text-slate-600">→</span>
              </li>
            );
          })
        )}
      </ul>

      <div className="px-5 py-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
        <span>Son güncelleme: 2 dk önce</span>
        <button className="text-rose-300 hover:underline">Inbox kurallarını düzenle</button>
      </div>

      <InboxItemDrawer
        item={openItem}
        onClose={() => setOpenItem(null)}
        onResolved={(_id, action) => {
          toast(ACTION_LABEL[action] ?? "Aksiyon uygulandı", "success");
          void qc.invalidateQueries({ queryKey: webDashboardKeys.inbox(projectId ?? null) });
        }}
      />
    </section>
  );
}
