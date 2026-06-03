"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import {
  useExecutionSummary,
  useManagementAuditEvents,
  useManagementDefects,
  useManagementRepository,
  useManagementRequirements,
  useManagementRuns,
  useReleaseReport,
  type TestCase,
} from "@/lib/hooks/use-management";
import { cn } from "@/lib/utils";

function asText(value: unknown, fallback = "Tanimsiz") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function StatCard({ label, value, note, tone = "neutral" }: {
  label: string;
  value: string | number;
  note: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
  const toneClass = {
    neutral: "border-border bg-surface-raised",
    success: "border-emerald-500/20 bg-emerald-500/5",
    warning: "border-amber-500/20 bg-amber-500/5",
    danger: "border-red-500/20 bg-red-500/5",
    info: "border-blue-500/20 bg-blue-500/5",
  }[tone];

  return (
    <section className={cn("rounded-xl border p-4 shadow-sm", toneClass)}>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-normal text-fg">{value}</p>
      <p className="mt-1 text-[11px] text-fg-muted">{note}</p>
    </section>
  );
}

function MiniBar({ label, value, max, tone }: { label: string; value: number; max: number; tone: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3 text-[12px]">
        <span className="truncate text-fg-muted">{label}</span>
        <span className="font-mono text-fg-subtle">{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-overlay">
        <div className={cn("h-full rounded-full", tone)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function EmptyState({ projectId }: { projectId: string }) {
  return (
    <section className="rounded-xl border border-dashed border-border bg-surface-raised p-8 text-center">
      <p className="text-[14px] font-semibold text-fg">Henüz veri bulunmuyor</p>
      <p className="mx-auto mt-2 max-w-md text-[12px] text-fg-muted">
        Repository üzerinden ilk test suite'inizi ve manuel case'lerinizi ekleyerek Management dashboard'unu doldurmaya baslayin.
      </p>
      <div className="mt-4 flex justify-center gap-2">
        <Link
          href={`/p/${projectId}/management/repository`}
          className="rounded-lg bg-brand px-3 py-2 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
        >
          Repository'ye git
        </Link>
        <Link
          href={`/p/${projectId}/management/cases/new`}
          className="rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[12px] font-semibold text-fg-muted transition-colors hover:text-fg"
        >
          Case ekle
        </Link>
      </div>
    </section>
  );
}

export default function ManagementDashboardPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid = useManagementProjectId(projectId || undefined);

  const repoQ = useManagementRepository(mpid || undefined);
  const runsQ = useManagementRuns(mpid || undefined);
  const summaryQ = useExecutionSummary(mpid || undefined);
  const defectsQ = useManagementDefects(mpid || undefined);
  const requirementsQ = useManagementRequirements(mpid || undefined);
  const releaseQ = useReleaseReport(mpid || undefined);
  const auditQ = useManagementAuditEvents(mpid || undefined, 10);

  const cases = useMemo(() => (repoQ.data?.cases ?? []).filter(tc => !tc.archived), [repoQ.data]);
  const runs = runsQ.data ?? [];
  const defects = defectsQ.data ?? [];
  const requirements = requirementsQ.data ?? [];
  const summary = summaryQ.data;
  const release = releaseQ.data;

  const activeRuns = runs.filter(run => ["running", "in_progress", "active"].includes(run.status)).length;
  const failedCases = cases.filter(tc => tc.last_run_status === "failed").length;
  const blockedCases = cases.filter(tc => tc.last_run_status === "blocked").length;
  const notRunCases = cases.filter(tc => !tc.last_run_status || tc.last_run_status === "not_run").length;
  const criticalDefects = defects.filter(d => ["critical", "blocker", "P0"].includes(d.severity)).length;
  const coveragePct = requirements.length
    ? Math.round((requirements.filter(r => r.coverage_status === "covered").length / requirements.length) * 100)
    : release?.requirement_coverage_pct ?? 0;

  const latestCases = [...cases]
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
    .slice(0, 5);
  const latestRuns = [...runs]
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, 5);

  const workload = useMemo(() => {
    const byOwner = new Map<string, number>();
    cases.forEach(tc => byOwner.set(asText(tc.owner_id, "Atanmamis"), (byOwner.get(asText(tc.owner_id, "Atanmamis")) ?? 0) + 1));
    return [...byOwner.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [cases]);

  const moduleDistribution = useMemo(() => {
    const byModule = new Map<string, number>();
    cases.forEach((tc: TestCase) => {
      const moduleName = asText(tc.custom_fields?.module ?? tc.custom_fields?.module_name ?? tc.suite_id, "Genel");
      byModule.set(moduleName, (byModule.get(moduleName) ?? 0) + 1);
    });
    return [...byModule.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [cases]);

  const isLoading = repoQ.isLoading || runsQ.isLoading || summaryQ.isLoading;
  const hasData = cases.length > 0 || runs.length > 0 || defects.length > 0 || requirements.length > 0;

  return (
    <div className="min-h-full space-y-5 bg-surface-base px-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Neurex Management</p>
          <h1 className="mt-1 text-[20px] font-semibold tracking-normal text-fg">Dashboard</h1>
          <p className="mt-1 text-[12px] text-fg-muted">Manuel test kapsamı, run sagligi, defect riski ve release hazirligi.</p>
        </div>
        <div className="flex gap-2">
          <Link href={`/p/${projectId}/management/repository`} className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-[12px] font-semibold text-fg-muted hover:text-fg">
            Repository
          </Link>
          <Link href={`/p/${projectId}/management/runs`} className="rounded-lg bg-brand px-3 py-2 text-[12px] font-semibold text-brand-fg shadow-sm hover:brightness-105">
            Run baslat
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-xl border border-border bg-surface-raised" />)}
        </div>
      ) : !hasData ? (
        <EmptyState projectId={projectId} />
      ) : (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Toplam manuel case" value={cases.length} note={`${repoQ.data?.suites.length ?? 0} suite, ${repoQ.data?.folders.length ?? 0} klasor`} />
            <StatCard label="Aktif test run" value={activeRuns} note={`${runs.length} toplam run`} tone="info" />
            <StatCard label="Pass rate" value={`${summary?.pass_rate_pct ?? release?.pass_rate_pct ?? 0}%`} note={`${summary?.passed ?? 0} passed`} tone="success" />
            <StatCard label="Failed case" value={summary?.failed ?? failedCases} note="Acil triage bekleyen case" tone="danger" />
            <StatCard label="Blocked case" value={summary?.blocked ?? blockedCases} note="Ortam veya veri engeli" tone="warning" />
            <StatCard label="Not run case" value={summary?.not_run ?? notRunCases} note="Kapsama alinmis ama kosulmamis" />
            <StatCard label="Kritik defect" value={criticalDefects} note={`${defects.length} toplam defect`} tone={criticalDefects ? "danger" : "success"} />
            <StatCard label="Test kapsami" value={`${coveragePct}%`} note={`${requirements.length} requirement linki`} tone="info" />
          </div>

          <div className="grid gap-5 xl:grid-cols-3">
            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm xl:col-span-2">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-[14px] font-semibold text-fg">Regresyon ve release hazirligi</h2>
                <span className="rounded-full border border-border bg-surface-overlay px-2 py-1 text-[11px] text-fg-muted">
                  {release?.decision ?? "Beklemede"}
                </span>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <MiniBar label="Run progress" value={summary?.progress_pct ?? release?.progress_pct ?? 0} max={100} tone="bg-blue-500" />
                <MiniBar label="Pass rate" value={summary?.pass_rate_pct ?? release?.pass_rate_pct ?? 0} max={100} tone="bg-emerald-500" />
                <MiniBar label="Requirement coverage" value={coveragePct} max={100} tone="bg-teal-500" />
              </div>
              <div className="mt-5 grid gap-2 md:grid-cols-2">
                {(release?.checklist ?? []).slice(0, 4).map(item => (
                  <div key={item.label} className="rounded-lg border border-border bg-surface-overlay px-3 py-2">
                    <p className="text-[12px] font-medium text-fg">{item.label}</p>
                    <p className="text-[11px] text-fg-subtle">{item.metric} · {item.status}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Tester workload</h2>
              <div className="space-y-3">
                {workload.length ? workload.map(([owner, count]) => (
                  <MiniBar key={owner} label={owner} value={count} max={cases.length} tone="bg-violet-500" />
                )) : <p className="py-8 text-center text-[12px] text-fg-muted">Henüz atama bulunmuyor</p>}
              </div>
            </section>
          </div>

          {/* Quick Actions */}
          <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
            <h2 className="mb-3 text-[12px] font-medium uppercase tracking-wider text-fg-subtle">Hızlı Aksiyonlar</h2>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "+ Yeni Case",       href: `/p/${projectId}/management/cases/new`,         color: "bg-brand text-brand-fg hover:brightness-105"               },
                { label: "▶ Run Başlat",      href: `/p/${projectId}/management/runs`,               color: "bg-blue-600 text-white hover:bg-blue-500"                   },
                { label: "Regresyon Seti",    href: `/p/${projectId}/management/regression`,         color: "bg-purple-600 text-white hover:bg-purple-500"               },
                { label: "Plan Oluştur",      href: `/p/${projectId}/management/plans`,              color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
                { label: "Import",            href: `/p/${projectId}/management/import-export`,      color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
                { label: "Raporlar",          href: `/p/${projectId}/management/reports`,            color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
                { label: "Standup",           href: `/p/${projectId}/management/standup`,            color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
              ].map(({ label, href, color }) => (
                <Link key={label} href={href}
                  className={`rounded-lg px-3 py-1.5 text-[12px] font-medium shadow-sm transition-all ${color}`}>
                  {label}
                </Link>
              ))}
            </div>
          </section>

          <div className="grid gap-5 xl:grid-cols-3">
            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Son calistirilan testler</h2>
              <div className="space-y-2">
                {latestRuns.length ? latestRuns.map(run => (
                  <Link key={run.id} href={`/p/${projectId}/management/runs/${run.id}/execute`} className="block rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-brand/30">
                    <p className="truncate text-[12px] font-medium text-fg">{run.name}</p>
                    <p className="mt-0.5 text-[11px] text-fg-subtle">{run.status} · {run.environment ?? "ortam yok"}</p>
                  </Link>
                )) : <p className="py-8 text-center text-[12px] text-fg-muted">Henüz test run bulunmuyor</p>}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Son guncellenen case'ler</h2>
              <div className="space-y-2">
                {latestCases.length ? latestCases.map(tc => (
                  <Link key={tc.id} href={`/p/${projectId}/management/cases/${tc.id}`} className="block rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-brand/30">
                    <p className="truncate text-[12px] font-medium text-fg">{tc.case_key} · {tc.title}</p>
                    <p className="mt-0.5 text-[11px] text-fg-subtle">{tc.priority} · {tc.type} · {tc.status}</p>
                  </Link>
                )) : <p className="py-8 text-center text-[12px] text-fg-muted">Repository uzerinden case ekleyin</p>}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Modul dagilimi</h2>
              <div className="space-y-3">
                {moduleDistribution.length ? moduleDistribution.map(([moduleName, count]) => (
                  <MiniBar key={moduleName} label={moduleName} value={count} max={cases.length} tone="bg-cyan-500" />
                )) : <p className="py-8 text-center text-[12px] text-fg-muted">Modul bilgisi bulunmuyor</p>}
              </div>
            </section>
          </div>

          {/* Activity Feed */}
          {auditQ.data && auditQ.data.length > 0 && (
            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-[14px] font-semibold text-fg">Son Aktiviteler</h2>
                <Link href={`/p/${projectId}/management/audit`}
                  className="text-[11px] text-brand hover:underline">Tümünü gör →</Link>
              </div>
              <div className="space-y-2">
                {auditQ.data.slice(0, 8).map(ev => (
                  <div key={ev.id} className="flex items-center gap-3 rounded-lg border border-border bg-surface-overlay px-3 py-2">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-accent text-[9px] font-bold text-fg-subtle">
                      {ev.entity_type?.[0]?.toUpperCase() ?? "?"}
                    </span>
                    <span className="flex-1 min-w-0 truncate text-[12px] text-fg-muted">{ev.action}</span>
                    <span className="shrink-0 text-[10px] text-fg-subtle tabular-nums">
                      {new Date(ev.created_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
