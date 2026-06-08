"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useManagementRuns, useCompareRuns, type RunCompareItem, type RunCompareSummary } from "@/lib/hooks/use-management";
import { PageErrorBoundary } from "../../_components/PageErrorBoundary";
import { P_DOT, R_DOT } from "../../_components/workspace/shared";

function RunSelect({ label, value, onChange, runs, exclude }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  runs: { id: string; name: string }[];
  exclude?: string;
}) {
  return (
    <div className="flex-1">
      <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-brand/40"
      >
        <option value="">— Koşu seçin —</option>
        {runs.filter(r => r.id !== exclude).map(r => (
          <option key={r.id} value={r.id}>{r.name}</option>
        ))}
      </select>
    </div>
  );
}

function SummaryCard({ s, accent }: { s: RunCompareSummary; accent: string }) {
  return (
    <div className="flex-1 rounded-xl border border-border bg-surface-raised p-3">
      <p className="truncate text-[12px] font-semibold text-fg">{s.name}</p>
      <p className="mt-0.5 text-[10px] text-fg-subtle">{s.environment ?? "—"}</p>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={`text-[22px] font-bold ${accent}`}>{s.pass_rate}%</span>
        <span className="text-[10px] text-fg-subtle">geçti</span>
      </div>
      <p className="mt-1 text-[10px] text-fg-muted">{s.passed} geçti · {s.failed} başarısız · {s.total} toplam</p>
    </div>
  );
}

const STATUS_BADGE = (status: string | null) => {
  const r = status ? R_DOT[status] : null;
  if (!r) return <span className="text-[10px] text-fg-disabled">—</span>;
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-semibold ${r.bg} ${r.text}`}>
      <span className={`h-1 w-1 rounded-full ${r.dot}`} />{r.label}
    </span>
  );
};

function DiffSection({ title, items, tone, showBase = true }: {
  title: string;
  items: RunCompareItem[];
  tone: string;
  showBase?: boolean;
}) {
  if (items.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface-raised">
      <div className={`flex items-center gap-2 border-b border-border px-4 py-2 text-[12px] font-semibold ${tone}`}>
        {title}
        <span className="rounded-full bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted">{items.length}</span>
      </div>
      <ul className="divide-y divide-border">
        {items.map((it, i) => (
          <li key={`${it.case_id ?? it.case_key ?? i}`} className="flex items-center gap-3 px-4 py-2">
            {it.priority && <span className={`h-2 w-2 shrink-0 rounded-full ${P_DOT[it.priority] ?? "bg-slate-500"}`} />}
            {it.case_key && <span className="shrink-0 font-mono text-[10px] text-fg-subtle">{it.case_key}</span>}
            <span className="min-w-0 flex-1 truncate text-[12px] text-fg">{it.title}</span>
            {showBase && (
              <div className="flex shrink-0 items-center gap-1.5">
                {STATUS_BADGE(it.base_status)}
                <span className="text-fg-disabled">→</span>
                {STATUS_BADGE(it.target_status)}
              </div>
            )}
            {!showBase && STATUS_BADGE(it.target_status ?? it.base_status)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CompareBody({ projectId }: { projectId: string }) {
  const { data: runs = [] } = useManagementRuns(projectId);
  const [baseId, setBaseId] = useState("");
  const [targetId, setTargetId] = useState("");
  const { data: diff, isLoading, isError } = useCompareRuns(projectId, baseId, targetId);

  return (
    <div className="mx-auto w-full max-w-4xl p-4 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-[18px] font-semibold text-fg">Koşu Karşılaştırma</h1>
          <p className="mt-0.5 text-[12px] text-fg-muted">İki koşu arasındaki regresyon farkını görün</p>
        </div>
        <Link href={`/p/${projectId}/management/runs`} className="text-[12px] text-fg-subtle hover:text-fg">← Koşular</Link>
      </div>

      {/* Selectors */}
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end">
        <RunSelect label="Temel (eski) koşu" value={baseId} onChange={setBaseId} runs={runs} exclude={targetId} />
        <span className="hidden pb-2 text-fg-subtle sm:block">vs</span>
        <RunSelect label="Karşılaştırılan (yeni) koşu" value={targetId} onChange={setTargetId} runs={runs} exclude={baseId} />
      </div>

      {!baseId || !targetId ? (
        <div className="rounded-xl border border-dashed border-border bg-surface-raised p-10 text-center text-[13px] text-fg-muted">
          Karşılaştırmak için iki koşu seçin.
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-blue-500" />
        </div>
      ) : isError || !diff ? (
        <div className="rounded-xl border border-danger/30 bg-danger-subtle p-6 text-center text-[13px] text-danger">
          Karşılaştırma yüklenemedi.
        </div>
      ) : (
        <div className="space-y-5">
          {/* Summaries */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <SummaryCard s={diff.base} accent="text-fg" />
            <span className="text-center text-fg-subtle">→</span>
            <SummaryCard s={diff.target} accent={diff.target.pass_rate >= diff.base.pass_rate ? "text-emerald-400" : "text-red-400"} />
          </div>

          {diff.newly_failed.length === 0 && diff.fixed.length === 0 && diff.still_failing.length === 0 &&
           diff.new_cases.length === 0 && diff.removed_cases.length === 0 && (
            <div className="rounded-xl border border-dashed border-border bg-surface-raised p-8 text-center text-[13px] text-fg-muted">
              İki koşu arasında durum farkı yok.
            </div>
          )}

          <DiffSection title="🔴 Yeni Bozulanlar (regresyon)" items={diff.newly_failed} tone="text-red-400" />
          <DiffSection title="🟢 Düzelenler" items={diff.fixed} tone="text-emerald-400" />
          <DiffSection title="⚠️ Hâlâ Başarısız" items={diff.still_failing} tone="text-amber-400" />
          <DiffSection title="➕ Yeni Eklenen Case'ler" items={diff.new_cases} tone="text-blue-400" showBase={false} />
          <DiffSection title="➖ Çıkarılan Case'ler" items={diff.removed_cases} tone="text-fg-muted" showBase={false} />
        </div>
      )}
    </div>
  );
}

export default function RunComparePage() {
  const projectId = useRouteParam("projectId");
  // mpid resolves the management project id used by run queries
  const mpid = useManagementProjectId(projectId || undefined);
  if (!projectId) return null;
  return (
    <PageErrorBoundary>
      <CompareBody projectId={mpid || projectId} />
    </PageErrorBoundary>
  );
}
