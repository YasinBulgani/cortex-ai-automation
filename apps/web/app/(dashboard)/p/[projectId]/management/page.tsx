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

// ── Yardımcı bileşenler ──────────────────────────────────────────────────────

function ReleaseHealthBanner({
  health,
  passRate,
  blocked,
  failed,
  pct,
}: {
  health: "go" | "risk" | "stop";
  passRate: number;
  blocked: number;
  failed: number;
  pct: number;
}) {
  const cfg = {
    go:   { bg: "from-emerald-950/80 to-slate-950", border: "border-emerald-500/30", badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40", dot: "bg-emerald-500", label: "GO", icon: "✅" },
    risk: { bg: "from-amber-950/60 to-slate-950",   border: "border-amber-500/30",   badge: "bg-amber-500/20  text-amber-300  border-amber-500/40",   dot: "bg-amber-500",   label: "RİSKLİ", icon: "⚠️" },
    stop: { bg: "from-rose-950/70  to-slate-950",   border: "border-rose-500/30",    badge: "bg-rose-500/20   text-rose-300   border-rose-500/40",    dot: "bg-rose-500",   label: "STOP",   icon: "🚫" },
  }[health];

  return (
    <div className={`rounded-2xl border ${cfg.border} bg-gradient-to-br ${cfg.bg} p-5`}>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <div className={`w-14 h-14 rounded-2xl border ${cfg.border} flex items-center justify-center text-2xl`}>
            {cfg.icon}
          </div>
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className={`text-xs font-bold uppercase tracking-widest px-2.5 py-1 rounded-full border ${cfg.badge}`}>
                {cfg.label}
              </span>
              <span className={`w-2 h-2 rounded-full animate-pulse ${cfg.dot}`} />
            </div>
            <p className="text-white font-semibold text-lg leading-tight">Release Sağlığı</p>
            <p className="text-slate-400 text-xs mt-0.5">
              {health === "go" ? "Tüm kriterler karşılanıyor" : health === "risk" ? "Dikkat gerektiren maddeler var" : `${blocked} bloke · ${failed} başarısız — release engellenebilir`}
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-4xl font-black text-white">{pct}<span className="text-2xl text-slate-400">%</span></p>
          <p className="text-xs text-slate-500">tamamlandı</p>
        </div>
      </div>

      {/* İlerleme çubuğu */}
      <div className="mt-4 space-y-1">
        <div className="h-3 rounded-full bg-slate-800 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              health === "go" ? "bg-gradient-to-r from-emerald-500 to-teal-400" :
              health === "risk" ? "bg-gradient-to-r from-amber-500 to-yellow-400" :
              "bg-gradient-to-r from-rose-500 to-orange-400"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>0%</span><span>50%</span><span>100%</span>
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label, value, note, trend, trendDir, accent, icon, href, projectId,
}: {
  label: string; value: string; note?: string; trend?: string; trendDir?: "up" | "down" | "flat";
  accent: string; icon: string; href?: string; projectId?: string;
}) {
  const trendColor = trendDir === "up" ? "text-emerald-400" : trendDir === "down" ? "text-rose-400" : "text-slate-500";
  const trendIcon  = trendDir === "up" ? "↑" : trendDir === "down" ? "↓" : "→";
  const inner = (
    <div className={`rounded-2xl border border-slate-800 bg-slate-900 p-4 space-y-3 h-full ${href ? "hover:border-slate-600 transition-colors cursor-pointer" : ""}`}>
      <div className="flex items-center justify-between">
        <span className="text-xl">{icon}</span>
        {trend && (
          <span className={`text-xs font-semibold ${trendColor}`}>{trendIcon} {trend}</span>
        )}
      </div>
      <div>
        <p className={`text-3xl font-black ${accent}`}>{value}</p>
        <p className="text-xs text-slate-400 mt-0.5 font-medium uppercase tracking-wide">{label}</p>
      </div>
      {note && <p className="text-xs text-slate-500">{note}</p>}
    </div>
  );
  if (href && projectId) return <Link href={`/p/${projectId}/${href}`}>{inner}</Link>;
  return inner;
}

function RunCard({ run, projectId }: { run: { id: string; name: string; status: string; created_at: string; environment?: string }; projectId: string }) {
  const statusCfg: Record<string, { dot: string; label: string; bg: string }> = {
    in_progress: { dot: "bg-violet-500 animate-pulse", label: "Devam ediyor", bg: "border-violet-500/30 bg-violet-500/5" },
    not_started: { dot: "bg-slate-500",                label: "Başlamadı",    bg: "border-slate-700" },
    completed:   { dot: "bg-emerald-500",              label: "Tamamlandı",   bg: "border-emerald-500/20" },
    failed:      { dot: "bg-rose-500",                 label: "Başarısız",    bg: "border-rose-500/20" },
  };
  const cfg = statusCfg[run.status] ?? statusCfg.not_started;
  const ENV_EMOJI: Record<string, string> = { staging: "🧪", production: "🚀", dev: "💻", qa: "🔬", uat: "👥" };

  return (
    <Link href={`/p/${projectId}/management/runs/${run.id}/execute`}>
      <div className={`rounded-xl border ${cfg.bg} p-3.5 flex items-center justify-between gap-3 hover:bg-slate-800/50 transition-colors`}>
        <div className="flex items-center gap-3 min-w-0">
          <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${cfg.dot}`} />
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">{run.name}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-slate-500">{cfg.label}</span>
              {run.environment && (
                <span className="text-xs text-slate-400">
                  {ENV_EMOJI[run.environment] ?? "⚙️"} {run.environment}
                </span>
              )}
            </div>
          </div>
        </div>
        <span className="text-xs text-slate-500 shrink-0">
          {new Date(run.created_at).toLocaleDateString("tr-TR")}
        </span>
      </div>
    </Link>
  );
}

function ReleaseGateRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-800 last:border-0">
      <div className="flex items-center gap-2.5">
        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${ok ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"}`}>
          {ok ? "✓" : "✗"}
        </span>
        <span className="text-sm text-slate-300">{label}</span>
      </div>
      <span className={`text-sm font-bold font-mono ${ok ? "text-emerald-400" : "text-rose-400"}`}>{value}</span>
    </div>
  );
}

// ── Ana sayfa ────────────────────────────────────────────────────────────────

export default function ManagementDashboardPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;

  const casesQuery    = useManagementCases(projectId);
  const summaryQuery  = useExecutionSummary(projectId);
  const runsQuery     = useManagementRuns(projectId);
  const projectsQuery = useManagementProjects();
  const ensureProject = useEnsureManagementProject(projectId);

  const summary = summaryQuery.data ?? null;
  const cases   = casesQuery.data ?? [];
  const runs    = runsQuery.data ?? [];
  const loading = casesQuery.isLoading || summaryQuery.isLoading;

  const managementProject = projectsQuery.data?.find(
    (p) => p.id === projectId || p.tspm_project_id === projectId,
  );

  // KPI hesaplamaları
  const totalCases   = cases.length;
  const activeCases  = cases.filter((c: { archived: boolean }) => !c.archived).length;
  const activeRuns   = runs.filter((r: { status: string }) => r.status === "in_progress");
  const pct          = summary ? Math.round(summary.progress_pct) : 0;
  const passRate     = summary ? summary.pass_rate_pct : 0;
  const blocked      = summary?.blocked ?? 0;
  const failed       = summary?.failed  ?? 0;
  const total        = summary?.total   ?? 0;

  // Sağlık hesabı
  const health: "go" | "risk" | "stop" =
    !summary ? "risk" :
    (blocked === 0 && failed === 0 && passRate >= 90) ? "go" :
    (blocked > 3  || failed > 5  || passRate < 70)   ? "stop" :
    "risk";

  // Release gate kontrolleri
  const gateChecks = summary ? [
    { label: "Execution ≥ %95", value: `${pct}%`,              ok: pct >= 95 },
    { label: "Pass rate ≥ %90", value: `${passRate.toFixed(1)}%`, ok: passRate >= 90 },
    { label: "Blocked = 0",     value: String(blocked),          ok: blocked === 0 },
    { label: "Failed = 0",      value: String(failed),           ok: failed === 0 },
  ] : [];

  // Workspace yoksa onboarding
  if (!projectsQuery.isLoading && !managementProject) {
    return (
      <ManagementShell projectId={projectId} title="Management Dashboard" description="" active="management">
        <OnboardingWizard
          projectId={projectId}
          onCreateWorkspace={() => ensureProject.mutate()}
          isCreating={ensureProject.isPending}
        />
      </ManagementShell>
    );
  }

  return (
    <ManagementShell
      projectId={projectId}
      title="Management Dashboard"
      description=""
      active="management"
    >
      {/* ── 1. Release health banner ── */}
      <ReleaseHealthBanner
        health={health}
        passRate={passRate}
        blocked={blocked}
        failed={failed}
        pct={pct}
      />

      {/* ── 2. KPI kartları ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          icon="📋" label="Manuel Case" accent="text-white"
          value={loading ? "…" : totalCases.toLocaleString()}
          note={`${activeCases} aktif`}
          href="management/repository" projectId={projectId}
        />
        <KpiCard
          icon="▶️" label="Aktif Run" accent="text-violet-400"
          value={loading ? "…" : String(activeRuns.length)}
          note={activeRuns.length > 0 ? "devam ediyor" : "koşum yok"}
          trend={activeRuns.length > 0 ? "canlı" : undefined}
          trendDir={activeRuns.length > 0 ? "up" : "flat"}
          href="management/runs" projectId={projectId}
        />
        <KpiCard
          icon="✅" label="Pass Rate" accent={passRate >= 90 ? "text-emerald-400" : passRate >= 70 ? "text-amber-400" : "text-rose-400"}
          value={loading ? "…" : `${passRate.toFixed(1)}%`}
          note={summary ? `${summary.passed}/${total} geçti` : "—"}
          trendDir={passRate >= 90 ? "up" : passRate < 70 ? "down" : "flat"}
        />
        <KpiCard
          icon="🚫" label="Bloke" accent={blocked === 0 ? "text-emerald-400" : "text-amber-400"}
          value={loading ? "…" : String(blocked)}
          note={failed > 0 ? `+${failed} başarısız` : "temiz"}
          trendDir={blocked === 0 ? "flat" : "down"}
          href="management/defects" projectId={projectId}
        />
      </div>

      {/* ── 3. Ana içerik: Release gate + Aktif runlar ── */}
      <div className="grid gap-4 lg:grid-cols-5">

        {/* Release Gate (3 kolon) */}
        <div className="lg:col-span-3 rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
            <div>
              <p className="text-sm font-semibold text-white">Release Gate</p>
              <p className="text-xs text-slate-500 mt-0.5">Çıkış kriterleri kontrol listesi</p>
            </div>
            <Link
              href={`/p/${projectId}/management/reports`}
              className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
            >
              Tam Rapor →
            </Link>
          </div>
          <div className="px-5 py-2">
            {loading ? (
              <p className="py-6 text-center text-slate-500 text-sm">Yükleniyor…</p>
            ) : gateChecks.length === 0 ? (
              <p className="py-6 text-center text-slate-500 text-sm">Koşum verisi yok</p>
            ) : (
              gateChecks.map((g) => <ReleaseGateRow key={g.label} {...g} />)
            )}
          </div>

          {/* Run dağılımı bar */}
          {summary && summary.total > 0 && (
            <div className="px-5 pb-4 pt-2 border-t border-slate-800">
              <p className="text-xs text-slate-500 mb-2">Case dağılımı</p>
              <div className="h-3 rounded-full overflow-hidden flex gap-0.5">
                {([
                  ["passed",  summary.passed,  "bg-emerald-500"],
                  ["failed",  summary.failed,  "bg-rose-500"],
                  ["blocked", summary.blocked, "bg-amber-500"],
                  ["skipped", summary.skipped, "bg-slate-500"],
                  ["not_run", summary.not_run, "bg-slate-700"],
                ] as [string, number, string][]).map(([key, cnt, color]) =>
                  cnt > 0 ? (
                    <div
                      key={key}
                      title={`${key}: ${cnt}`}
                      className={`${color} transition-all`}
                      style={{ width: `${(cnt / summary.total) * 100}%` }}
                    />
                  ) : null
                )}
              </div>
              <div className="flex flex-wrap gap-3 mt-2">
                {([
                  ["Geçti",    summary.passed,  "bg-emerald-500"],
                  ["Başarısız",summary.failed,  "bg-rose-500"],
                  ["Bloke",    summary.blocked, "bg-amber-500"],
                  ["Atlandı",  summary.skipped, "bg-slate-500"],
                  ["Bekliyor", summary.not_run, "bg-slate-700"],
                ] as [string, number, string][]).map(([label, cnt, color]) => (
                  <div key={label} className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${color}`} />
                    <span className="text-xs text-slate-400">{label} <strong className="text-white">{cnt}</strong></span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Aktif runlar + hızlı aksiyonlar (2 kolon) */}
        <div className="lg:col-span-2 space-y-3">
          {/* Aktif runlar */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-800">
              <p className="text-sm font-semibold text-white">Aktif Runlar</p>
              <Link href={`/p/${projectId}/management/runs`} className="text-xs text-violet-400 hover:text-violet-300">
                Tümü →
              </Link>
            </div>
            <div className="p-3 space-y-2">
              {runsQuery.isLoading ? (
                <p className="text-center py-4 text-slate-500 text-sm">Yükleniyor…</p>
              ) : runs.length === 0 ? (
                <div className="py-6 text-center space-y-2">
                  <p className="text-2xl">▶️</p>
                  <p className="text-xs text-slate-500">Henüz run yok</p>
                  <Link
                    href={`/p/${projectId}/management/runs`}
                    className="inline-block text-xs text-violet-400 hover:text-violet-300"
                  >
                    İlk koşumu başlat →
                  </Link>
                </div>
              ) : (
                runs.slice(0, 4).map((run: { id: string; name: string; status: string; created_at: string; environment?: string }) => (
                  <RunCard key={run.id} run={run} projectId={projectId} />
                ))
              )}
            </div>
          </div>

          {/* Hızlı aksiyonlar */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4 space-y-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Hızlı Erişim</p>
            {[
              { icon: "👤", label: "Görevlerim", sub: "Atanan case'ler",         href: "management/tester" },
              { icon: "📊", label: "Standup Görünümü", sub: "Mobil release özeti", href: "management/standup" },
              { icon: "📁", label: "Repository",  sub: "Case yazma & arama",    href: "management/repository" },
              { icon: "📝", label: "Defects",     sub: "Açık hatalar",           href: "management/defects" },
            ].map((item) => (
              <Link key={item.href} href={`/p/${projectId}/${item.href}`}>
                <div className="flex items-center gap-3 rounded-xl p-2.5 hover:bg-slate-800 transition-colors">
                  <span className="text-lg w-7 text-center">{item.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-white leading-tight">{item.label}</p>
                    <p className="text-xs text-slate-500">{item.sub}</p>
                  </div>
                  <span className="ml-auto text-slate-600 text-xs">→</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </ManagementShell>
  );
}
