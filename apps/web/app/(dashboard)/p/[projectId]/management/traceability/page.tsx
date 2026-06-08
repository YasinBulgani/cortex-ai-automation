"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import {
  useRequirementTraceability,
  type RequirementTraceabilityRow,
} from "@/lib/hooks/use-management";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// ── Constants ──────────────────────────────────────────────────────────────────

const COVERAGE_BADGE: Record<string, string> = {
  covered:           "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  partially_covered: "border-amber-500/30 bg-amber-500/10 text-amber-400",
  not_covered:       "border-border bg-surface-overlay text-fg-subtle",
  out_of_scope:      "border-purple-500/30 bg-purple-500/10 text-purple-400",
};

const COVERAGE_LABEL: Record<string, string> = {
  covered:           "Kapsandı",
  partially_covered: "Kısmi",
  not_covered:       "Kapsamdışı",
  out_of_scope:      "Kapsam Dışı",
};

const STATUS_DOT: Record<string, string> = {
  passed:  "bg-emerald-500",
  failed:  "bg-red-500",
  blocked: "bg-amber-500",
  skipped: "bg-slate-400",
  not_run: "bg-fg-disabled",
};

const STATUS_LABEL: Record<string, string> = {
  passed:  "Geçti",
  failed:  "Başarısız",
  blocked: "Engellendi",
  skipped: "Atlandı",
  not_run: "Çalıştırılmadı",
};

const PRIORITY_BADGE: Record<string, string> = {
  P0: "text-red-400 border-red-500/30 bg-red-500/10",
  P1: "text-orange-400 border-orange-500/30 bg-orange-500/10",
  P2: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  P3: "text-fg-muted border-border bg-surface-overlay",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function CoverageBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="h-1.5 w-20 flex-none rounded-full bg-surface-accent overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-[11px] text-fg-subtle tabular-nums">{Math.round(pct)}%</span>
    </div>
  );
}

function SummaryCard({ label, value, sub, tone }: {
  label: string; value: number | string; sub: string;
  tone?: "success" | "warning" | "danger" | "info" | "neutral";
}) {
  const bg = {
    success: "border-emerald-500/20 bg-emerald-500/5",
    warning: "border-amber-500/20 bg-amber-500/5",
    danger:  "border-red-500/20 bg-red-500/5",
    info:    "border-blue-500/20 bg-blue-500/5",
    neutral: "border-border bg-surface-raised",
  }[tone ?? "neutral"];

  return (
    <div className={cn("rounded-xl border p-4 shadow-sm", bg)}>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums text-fg">{value}</p>
      <p className="mt-1 text-[11px] text-fg-muted">{sub}</p>
    </div>
  );
}

// ── Coverage donut ────────────────────────────────────────────────────────────

function DonutChart({ covered, partial, notCovered, outOfScope }: {
  covered: number; partial: number; notCovered: number; outOfScope: number;
}) {
  const total = covered + partial + notCovered + outOfScope;
  if (total === 0) return <p className="text-[12px] text-fg-subtle py-4">Veri yok</p>;

  const SIZE = 96;
  const cx = SIZE / 2; const cy = SIZE / 2; const r = 36; const sw = 14;

  const segs = [
    { value: covered,    color: "#10b981", label: "Kapsandı" },
    { value: partial,    color: "#f59e0b", label: "Kısmi" },
    { value: notCovered, color: "#64748b", label: "Kapsamsız" },
    { value: outOfScope, color: "#a855f7", label: "Kapsam Dışı" },
  ];

  let cum = -90;
  const arcs = segs.map((seg, i) => {
    if (!seg.value) return null;
    const ang = (seg.value / total) * 360;
    const s = cum; const e = cum + ang; cum = e;
    const sr = (s * Math.PI) / 180; const er = (e * Math.PI) / 180;
    const x1 = cx + r * Math.cos(sr); const y1 = cy + r * Math.sin(sr);
    const x2 = cx + r * Math.cos(er); const y2 = cy + r * Math.sin(er);
    return (
      <path key={i}
        d={`M ${x1} ${y1} A ${r} ${r} 0 ${ang > 180 ? 1 : 0} 1 ${x2} ${y2}`}
        fill="none" stroke={seg.color} strokeWidth={sw} strokeLinecap="butt" />
    );
  });

  const pct = Math.round((covered / total) * 100);
  return (
    <div className="flex items-center gap-5">
      <div className="relative shrink-0">
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="currentColor" strokeWidth={sw} className="text-surface-accent" />
          {arcs}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[16px] font-bold text-fg">{pct}%</span>
          <span className="text-[9px] text-fg-subtle leading-tight">kapsandı</span>
        </div>
      </div>
      <div className="space-y-1.5">
        {segs.map(seg => seg.value > 0 && (
          <div key={seg.label} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-sm shrink-0" style={{ backgroundColor: seg.color }} />
            <span className="text-[11px] text-fg-muted">{seg.label}</span>
            <span className="ml-auto pl-4 text-[11px] font-semibold text-fg tabular-nums">{seg.value}</span>
          </div>
        ))}
        <div className="flex items-center gap-2 border-t border-border pt-1.5">
          <span className="text-[10px] text-fg-subtle">Toplam</span>
          <span className="ml-auto pl-4 text-[11px] font-semibold text-fg tabular-nums">{total}</span>
        </div>
      </div>
    </div>
  );
}

// ── Row component ─────────────────────────────────────────────────────────────

function TraceabilityRow({
  row,
  projectId,
  expanded,
  onToggle,
}: {
  row: RequirementTraceabilityRow;
  projectId: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const coverageClass = row.covered
    ? COVERAGE_BADGE.covered
    : row.coverage_pct > 0
    ? COVERAGE_BADGE.partially_covered
    : COVERAGE_BADGE.not_covered;

  const coverageLabel = row.covered
    ? COVERAGE_LABEL.covered
    : row.coverage_pct > 0
    ? COVERAGE_LABEL.partially_covered
    : COVERAGE_LABEL.not_covered;

  return (
    <>
      {/* Header row */}
      <tr
        className={cn(
          "cursor-pointer border-b border-border transition-colors hover:bg-surface-overlay",
          expanded && "bg-surface-overlay",
        )}
        onClick={onToggle}
      >
        {/* Expand arrow */}
        <td className="w-8 px-3 py-3">
          <svg
            className={cn("h-3.5 w-3.5 text-fg-subtle transition-transform", expanded && "rotate-90")}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </td>

        {/* Requirement key */}
        <td className="py-3 pr-4">
          <span className="font-mono text-[11px] text-fg-subtle">{row.external_key}</span>
        </td>

        {/* Title */}
        <td className="py-3 pr-4">
          <p className="truncate text-[13px] font-medium text-fg max-w-[280px]">{row.title}</p>
          {row.stale && (
            <span className="mt-0.5 inline-flex items-center gap-1 text-[10px] text-amber-400">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Güncel değil
            </span>
          )}
        </td>

        {/* Priority */}
        <td className="py-3 pr-4">
          <span className={cn("inline-flex rounded border px-1.5 py-0.5 text-[10px] font-medium", PRIORITY_BADGE[row.priority] ?? PRIORITY_BADGE.P3)}>
            {row.priority}
          </span>
        </td>

        {/* Coverage % */}
        <td className="py-3 pr-4">
          <CoverageBar pct={row.coverage_pct} />
        </td>

        {/* Coverage status */}
        <td className="py-3 pr-4">
          <span className={cn("inline-flex rounded border px-2 py-0.5 text-[10px] font-medium", coverageClass)}>
            {coverageLabel}
          </span>
        </td>

        {/* Case count */}
        <td className="py-3 pr-3 text-right">
          <span className="rounded-full bg-surface-accent px-2 py-0.5 text-[11px] font-medium text-fg-muted tabular-nums">
            {row.cases.length} case
          </span>
        </td>
      </tr>

      {/* Expanded: linked cases */}
      {expanded && row.cases.length > 0 && (
        <tr className="border-b border-border bg-surface-overlay/50">
          <td colSpan={7} className="px-10 py-3">
            <div className="space-y-1.5">
              {row.cases.map(c => {
                const dot = STATUS_DOT[c.last_run_status ?? "not_run"] ?? STATUS_DOT.not_run;
                const lbl = STATUS_LABEL[c.last_run_status ?? "not_run"] ?? "Çalıştırılmadı";
                return (
                  <div key={c.case_id} className="flex items-center gap-3 rounded-lg border border-border bg-surface-raised px-3 py-2">
                    <span className={cn("h-2 w-2 shrink-0 rounded-full", dot)} title={lbl} />
                    <span className="shrink-0 font-mono text-[10px] text-fg-disabled">{c.case_key}</span>
                    <span className="flex-1 min-w-0 truncate text-[12px] text-fg">{c.title}</span>
                    <span className={cn(
                      "shrink-0 rounded border px-1.5 py-0.5 text-[10px]",
                      COVERAGE_BADGE[c.coverage_status] ?? COVERAGE_BADGE.not_covered
                    )}>
                      {COVERAGE_LABEL[c.coverage_status] ?? c.coverage_status}
                    </span>
                    <Link
                      href={`/p/${projectId}/management/cases/${c.case_id}`}
                      className="shrink-0 text-[11px] text-brand hover:underline"
                      onClick={e => e.stopPropagation()}
                    >
                      Aç →
                    </Link>
                  </div>
                );
              })}
            </div>
          </td>
        </tr>
      )}

      {expanded && row.cases.length === 0 && (
        <tr className="border-b border-border bg-surface-overlay/50">
          <td colSpan={7} className="px-10 py-4 text-[12px] text-fg-subtle">
            Bu gereksinime bağlı test case bulunmuyor.{" "}
            <Link href={`/p/${projectId}/management/requirements`} className="text-brand hover:underline">
              Gereksinimler sayfasından case ekleyebilirsiniz.
            </Link>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function TraceabilityPage() {
  const projectId = useRouteParam("projectId");
  const mpid      = useManagementProjectId(projectId || undefined);

  const { data = [], isLoading, isError, refetch } = useRequirementTraceability(mpid || undefined);

  const [search, setSearch]         = useState("");
  const [coverFilter, setCoverFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  function toggleExpand(id: string) {
    setExpandedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function expandAll() {
    setExpandedIds(new Set(filtered.map(r => r.requirement_id)));
  }
  function collapseAll() {
    setExpandedIds(new Set());
  }

  function exportCSV() {
    const headers = [
      "Gereksinim Key", "Başlık", "Öncelik", "Durum", "Kaynak",
      "Kapsam %", "Kapsandı mı?", "Güncel Değil mi?", "Case Key", "Case Başlığı", "Son Çalıştırma", "Case Kapsam"
    ];
    const rows: string[][] = [];
    for (const req of filtered) {
      if (req.cases.length === 0) {
        rows.push([
          req.external_key || req.requirement_key,
          req.title,
          req.priority,
          req.status,
          req.source,
          String(Math.round(req.coverage_pct)),
          req.covered ? "Evet" : "Hayır",
          req.stale ? "Evet" : "Hayır",
          "—", "—", "—", "—",
        ]);
      } else {
        for (const c of req.cases) {
          rows.push([
            req.external_key || req.requirement_key,
            req.title,
            req.priority,
            req.status,
            req.source,
            String(Math.round(req.coverage_pct)),
            req.covered ? "Evet" : "Hayır",
            req.stale ? "Evet" : "Hayır",
            c.case_key,
            c.title,
            c.last_run_status ?? "çalıştırılmadı",
            c.coverage_status,
          ]);
        }
      }
    }
    const csv = "﻿" + [headers, ...rows]
      .map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(";"))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "traceability.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  const filtered = useMemo(() => {
    let rows = data;
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(r =>
        r.title.toLowerCase().includes(q) ||
        r.external_key.toLowerCase().includes(q) ||
        r.cases.some(c => c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q))
      );
    }
    if (coverFilter !== "all") {
      rows = rows.filter(r => {
        if (coverFilter === "covered")    return r.covered;
        if (coverFilter === "partial")    return !r.covered && r.coverage_pct > 0;
        if (coverFilter === "uncovered")  return r.coverage_pct === 0;
        if (coverFilter === "stale")      return r.stale;
        return true;
      });
    }
    if (priorityFilter !== "all") {
      rows = rows.filter(r => r.priority === priorityFilter);
    }
    return rows;
  }, [data, search, coverFilter, priorityFilter]);

  const stats = useMemo(() => {
    const total        = data.length;
    const covered      = data.filter(r => r.covered).length;
    const partial      = data.filter(r => !r.covered && r.coverage_pct > 0).length;
    const notCovered   = data.filter(r => r.coverage_pct === 0).length;
    const stale        = data.filter(r => r.stale).length;
    const outOfScope   = 0; // not tracked at row level
    const avgCoverage  = total > 0
      ? Math.round(data.reduce((s, r) => s + r.coverage_pct, 0) / total)
      : 0;
    return { total, covered, partial, notCovered, stale, outOfScope, avgCoverage };
  }, [data]);

  return (
    <div className="min-h-full space-y-5 bg-surface-base px-6 py-6">
      {/* ── Page header ── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Neurex Management</p>
          <h1 className="mt-1 text-[20px] font-semibold text-fg">İzlenebilirlik Matrisi</h1>
          <p className="mt-1 text-[12px] text-fg-muted">
            Gereksinim → Test Case → Çalıştırma → Defect izlenebilirlik zinciri
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/p/${projectId}/management/requirements`}
            className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-[12px] font-medium text-fg-muted hover:text-fg transition-colors"
          >
            Gereksinimler
          </Link>
          <Button
            variant="outline"
            size="sm"
            onClick={exportCSV}
            disabled={!data.length}
            className="bg-surface-raised text-fg-muted hover:text-fg"
          >
            CSV İndir
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void refetch()}
            className="bg-surface-raised text-fg-muted hover:text-fg"
          >
            Yenile
          </Button>
        </div>
      </div>

      {/* ── Summary row ── */}
      {!isLoading && !isError && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
          <SummaryCard label="Toplam Gereksinim" value={stats.total} sub="izlenen gereksinim" />
          <SummaryCard label="Tamamen Kapsandı" value={stats.covered} sub={`%${stats.total ? Math.round((stats.covered / stats.total) * 100) : 0} kapsam`} tone="success" />
          <SummaryCard label="Kısmi Kapsam" value={stats.partial} sub="en az 1 case bağlı" tone="warning" />
          <SummaryCard label="Kapsamsız" value={stats.notCovered} sub="test case bağlı değil" tone="danger" />
          <SummaryCard label="Güncel Değil" value={stats.stale} sub="gereksinim değişti" tone="warning" />
        </div>
      )}

      {/* ── Charts row ── */}
      {!isLoading && !isError && stats.total > 0 && (
        <div className="grid gap-5 xl:grid-cols-2">
          <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
            <h2 className="mb-4 text-[14px] font-semibold text-fg">Kapsam Dağılımı</h2>
            <DonutChart
              covered={stats.covered}
              partial={stats.partial}
              notCovered={stats.notCovered}
              outOfScope={stats.outOfScope}
            />
          </section>

          <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
            <h2 className="mb-4 text-[14px] font-semibold text-fg">Öncelik Bazlı Kapsam</h2>
            <div className="space-y-4">
              {(["P0", "P1", "P2", "P3"] as const).map(p => {
                const pRows = data.filter(r => r.priority === p);
                const pCovered = pRows.filter(r => r.covered).length;
                const pct = pRows.length > 0 ? Math.round((pCovered / pRows.length) * 100) : 0;
                if (!pRows.length) return null;
                return (
                  <div key={p} className="space-y-1">
                    <div className="flex items-center justify-between text-[12px]">
                      <div className="flex items-center gap-2">
                        <span className={cn("inline-flex rounded border px-1.5 py-0.5 text-[10px] font-medium", PRIORITY_BADGE[p])}>
                          {p}
                        </span>
                        <span className="text-fg-muted">{pRows.length} gereksinim</span>
                      </div>
                      <span className="tabular-nums text-fg-subtle">{pCovered}/{pRows.length} ({pct}%)</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-surface-accent">
                      <div
                        className={cn("h-full rounded-full transition-all", pct >= 80 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500")}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      )}

      {/* ── Filters ── */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Gereksinim veya case ara..."
          className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-[12px] text-fg placeholder:text-fg-disabled outline-none focus:border-brand/50 w-60"
        />
        <div className="flex gap-1.5">
          {[
            { value: "all",       label: "Tümü" },
            { value: "covered",   label: "Kapsandı" },
            { value: "partial",   label: "Kısmi" },
            { value: "uncovered", label: "Kapsamsız" },
            { value: "stale",     label: "Güncel Değil" },
          ].map(f => (
            <button
              key={f.value}
              onClick={() => setCoverFilter(f.value)}
              className={cn(
                "rounded-lg border px-3 py-1.5 text-[11px] font-medium transition-colors",
                coverFilter === f.value
                  ? "border-brand/40 bg-brand-soft text-brand"
                  : "border-border text-fg-muted hover:text-fg"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5 ml-auto">
          {(["P0", "P1", "P2", "P3"] as const).map(p => (
            <button
              key={p}
              onClick={() => setPriorityFilter(priorityFilter === p ? "all" : p)}
              className={cn(
                "rounded border px-2 py-1 text-[10px] font-medium transition-colors",
                priorityFilter === p
                  ? PRIORITY_BADGE[p]
                  : "border-border text-fg-muted hover:text-fg"
              )}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* ── Matrix table ── */}
      <section className="rounded-xl border border-border bg-surface-raised shadow-sm overflow-hidden">
        <div className="flex items-center justify-between border-b border-border bg-surface-overlay px-4 py-3">
          <h2 className="text-[13px] font-semibold text-fg">
            İzlenebilirlik Tablosu
            <span className="ml-2 text-[11px] font-normal text-fg-subtle">
              ({filtered.length} / {data.length} gereksinim)
            </span>
          </h2>
          <div className="flex gap-2">
            <button
              onClick={expandAll}
              className="text-[11px] text-brand hover:underline"
            >
              Tümünü Genişlet
            </button>
            <span className="text-fg-subtle">·</span>
            <button
              onClick={collapseAll}
              className="text-[11px] text-fg-muted hover:text-fg"
            >
              Daralt
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-2 p-6">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-surface-overlay" />
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <p className="text-[13px] font-medium text-fg-muted">Veri yüklenirken hata oluştu.</p>
            <Button variant="primary" size="sm" onClick={() => void refetch()}>
              Tekrar Dene
            </Button>
          </div>
        ) : data.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <svg className="h-12 w-12 text-fg-disabled" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
            <div>
              <p className="text-[14px] font-semibold text-fg">Henüz gereksinim bağlantısı yok</p>
              <p className="mt-1 text-[12px] text-fg-muted">
                Test case&apos;leri gereksinimlerle ilişkilendirin ve izlenebilirlik matrisini doldurmaya başlayın.
              </p>
            </div>
            <Link
              href={`/p/${projectId}/management/requirements`}
              className="rounded-lg bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105"
            >
              Gereksinim Ekle
            </Link>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-[13px] text-fg-muted">Filtrelerle eşleşen gereksinim bulunamadı.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left">
              <thead>
                <tr className="border-b border-border bg-surface-overlay">
                  <th className="w-8 px-3 py-2" />
                  <th className="py-2 pr-4 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Anahtar</th>
                  <th className="py-2 pr-4 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Gereksinim</th>
                  <th className="py-2 pr-4 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Öncelik</th>
                  <th className="py-2 pr-4 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Kapsam %</th>
                  <th className="py-2 pr-4 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Durum</th>
                  <th className="py-2 pr-3 text-right text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Case</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(row => (
                  <TraceabilityRow
                    key={row.requirement_id}
                    row={row}
                    projectId={projectId ?? ""}
                    expanded={expandedIds.has(row.requirement_id)}
                    onToggle={() => toggleExpand(row.requirement_id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Export hint ── */}
      {!isLoading && data.length > 0 && (
        <div className="flex items-center justify-between rounded-xl border border-border bg-surface-raised px-4 py-3">
          <p className="text-[12px] text-fg-muted">
            Tüm izlenebilirlik verilerini dışa aktarmak için Raporlar sayfasını kullanabilirsiniz.
          </p>
          <Link
            href={`/p/${projectId}/management/reports`}
            className="text-[12px] text-brand hover:underline"
          >
            Raporlara Git →
          </Link>
        </div>
      )}
    </div>
  );
}
