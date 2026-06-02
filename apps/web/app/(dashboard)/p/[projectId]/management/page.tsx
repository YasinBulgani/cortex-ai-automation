"use client";

import Link from "next/link";
import {
  useEnsureManagementProject,
  useExecutionSummary,
  useManagementCases,
  useManagementProjects,
  useManagementRuns,
} from "@/lib/hooks/use-management";
import { ManagementShell } from "./_components/ManagementShell";
import { OnboardingWizard } from "./_components/OnboardingWizard";

const ENV_EMOJI: Record<string, string> = { staging: "🧪", production: "🚀", dev: "💻", qa: "🔬", uat: "👥" };

type RunItem = { id: string; name: string; status: string; created_at: string; environment?: string };

export default function ManagementDashboardPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;

  const casesQuery    = useManagementCases(projectId);
  const summaryQuery  = useExecutionSummary(projectId);
  const runsQuery     = useManagementRuns(projectId);
  const projectsQuery = useManagementProjects();
  const ensureProject = useEnsureManagementProject(projectId);

  const summary = summaryQuery.data ?? null;
  const cases   = casesQuery.data ?? [];
  const runs    = (runsQuery.data ?? []) as RunItem[];
  const loading = casesQuery.isLoading || summaryQuery.isLoading;

  const managementProject = projectsQuery.data?.find(
    (p: { id: string; tspm_project_id: string | null }) => p.id === projectId || p.tspm_project_id === projectId,
  );

  const pct      = summary ? Math.round(summary.progress_pct) : 0;
  const passRate = summary ? summary.pass_rate_pct : 0;
  const blocked  = summary?.blocked ?? 0;
  const failed   = summary?.failed ?? 0;
  const total    = summary?.total ?? 0;

  const gateOk = !summary ? false : blocked === 0 && failed === 0 && passRate >= 90 && pct >= 95;
  const gateRisk = !gateOk && !summary ? false : (blocked > 0 || failed > 0 || passRate < 90);

  // Workspace yoksa onboarding
  if (!projectsQuery.isLoading && !managementProject) {
    return (
      <ManagementShell projectId={projectId} title="" description="" active="management">
        <OnboardingWizard
          projectId={projectId}
          onCreateWorkspace={() => ensureProject.mutate()}
          isCreating={ensureProject.isPending}
        />
      </ManagementShell>
    );
  }

  return (
    <ManagementShell projectId={projectId} title="" description="" active="management">

      {/* ── Başlık satırı ── */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-base font-semibold text-white">Management Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {managementProject ? `${managementProject.name} · ${managementProject.key}` : "Yükleniyor…"}
          </p>
        </div>
        <Link href={`/p/${projectId}/management/runs`}
          className="rounded-lg bg-white hover:bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-900 transition-colors">
          + Yeni Run
        </Link>
      </div>

      {/* ── Release durumu ── */}
      {summary && (
        <div className={`rounded-xl border px-5 py-4 ${
          gateOk ? "border-emerald-800/40 bg-emerald-950/20" :
          gateRisk ? "border-red-800/30 bg-red-950/20" :
          "border-slate-800 bg-slate-900/40"
        }`}>
          <div className="flex items-center justify-between gap-6 flex-wrap">
            <div className="flex items-center gap-3">
              <span className={`text-lg ${gateOk ? "text-emerald-400" : gateRisk ? "text-red-400" : "text-amber-400"}`}>
                {gateOk ? "●" : gateRisk ? "●" : "●"}
              </span>
              <div>
                <p className={`text-sm font-semibold ${gateOk ? "text-emerald-300" : gateRisk ? "text-red-300" : "text-amber-300"}`}>
                  {gateOk ? "Release hazır" : gateRisk ? `${blocked + failed} engel var` : "İlerleme devam ediyor"}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {pct}% tamamlandı · pass rate {passRate.toFixed(0)}%
                </p>
              </div>
            </div>
            <div className="flex items-center gap-6 text-right">
              {[
                { label: "Bloke",     value: blocked, bad: blocked > 0 },
                { label: "Başarısız", value: failed,  bad: failed > 0 },
                { label: "Bekliyor",  value: summary.not_run, bad: false },
              ].map(s => (
                <div key={s.label}>
                  <p className={`text-xl font-black ${s.bad ? "text-red-400" : "text-white"}`}>{s.value}</p>
                  <p className="text-[10px] text-slate-600 uppercase tracking-wide">{s.label}</p>
                </div>
              ))}
            </div>
          </div>
          {/* İlerleme çubuğu */}
          <div className="mt-3 h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-700 ${gateOk ? "bg-emerald-500" : gateRisk ? "bg-red-500" : "bg-slate-500"}`}
              style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {/* ── Sayılar ── */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Case",    value: cases.length, sub: `${cases.filter((c: { archived: boolean }) => !c.archived).length} aktif`, href: "management/repository" },
          { label: "Geçti",   value: summary?.passed   ?? "—", sub: `/ ${total}`, href: null },
          { label: "Pass %",  value: summary ? `${passRate.toFixed(0)}%` : "—", sub: pct >= 95 ? "hedef ✓" : "hedef ≥95%", href: "management/reports" },
        ].map(s => (
          <div key={s.label} className={`rounded-xl border border-slate-800 bg-slate-900 p-4 ${s.href ? "hover:border-slate-700 transition-colors" : ""}`}>
            {s.href ? (
              <Link href={`/p/${projectId}/${s.href}`} className="block">
                <p className="text-2xl font-black text-white">{loading ? "…" : s.value}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-600 mt-1">{s.label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{s.sub}</p>
              </Link>
            ) : (
              <>
                <p className="text-2xl font-black text-white">{loading ? "…" : s.value}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-600 mt-1">{s.label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{s.sub}</p>
              </>
            )}
          </div>
        ))}
      </div>

      {/* ── Son runlar ── */}
      <div className="rounded-xl border border-slate-800">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <p className="text-sm font-medium text-white">Son Runlar</p>
          <Link href={`/p/${projectId}/management/runs`} className="text-xs text-slate-500 hover:text-white transition-colors">
            Tümünü gör →
          </Link>
        </div>
        <div className="divide-y divide-slate-800/60">
          {runsQuery.isLoading ? (
            <p className="px-4 py-6 text-center text-sm text-slate-600">Yükleniyor…</p>
          ) : runs.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-slate-500">Henüz run yok</p>
              <Link href={`/p/${projectId}/management/runs`}
                className="mt-2 inline-block text-xs text-slate-500 hover:text-white border border-slate-700 hover:border-slate-500 rounded px-3 py-1.5 transition-colors">
                İlk koşumu başlat
              </Link>
            </div>
          ) : (
            runs.slice(0, 5).map(run => {
              const isActive = run.status === "in_progress";
              return (
                <Link key={run.id} href={`/p/${projectId}/management/runs/${run.id}/execute`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-slate-800/30 transition-colors">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isActive ? "bg-emerald-400 animate-pulse" : "bg-slate-600"}`} />
                  <p className="flex-1 text-sm text-slate-300 truncate">{run.name}</p>
                  {run.environment && (
                    <span className="text-xs text-slate-600">{ENV_EMOJI[run.environment] ?? "⚙️"} {run.environment}</span>
                  )}
                  <span className="text-xs text-slate-600 shrink-0">
                    {new Date(run.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
                  </span>
                </Link>
              );
            })
          )}
        </div>
      </div>

      {/* ── Hızlı erişim (minimal) ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          { label: "Görevlerim", href: "management/tester",    icon: "👤" },
          { label: "Defects",    href: "management/defects",   icon: "🐛" },
          { label: "Raporlar",   href: "management/reports",   icon: "📊" },
          { label: "Standup",    href: "management/standup",   icon: "📱" },
        ].map(item => (
          <Link key={item.href} href={`/p/${projectId}/${item.href}`}
            className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2.5 text-xs text-slate-400 hover:text-white hover:border-slate-700 transition-colors">
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </div>

    </ManagementShell>
  );
}
