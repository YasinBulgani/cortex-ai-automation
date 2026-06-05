"use client";

import Link from "next/link";
import { useMemo, useEffect, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import {
  useExecutionSummary,
  useManagementAuditEvents,
  useManagementDefects,
  useManagementDashboardSummary,
  useManagementPlans,
  useManagementRepository,
  useManagementRequirements,
  useManagementRuns,
  useReleaseReport,
  useReleaseSignoffs,
  useCreateReleaseSignoff,
  type ReleaseBlocker,
  type TestCase,
} from "@/lib/hooks/use-management";
import { cn } from "@/lib/utils";
import { QuickSetupWizard } from "../_components/QuickSetupWizard";

const REFETCH_INTERVAL = 30_000; // ms

function AutoRefreshBadge() {
  const [countdown, setCountdown] = useState(30);
  const [pulsing, setPulsing] = useState(false);

  useEffect(() => {
    setCountdown(30);
    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          // Trigger pulse animation briefly
          setPulsing(true);
          setTimeout(() => setPulsing(false), 600);
          return 30;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-1.5 rounded-full border border-border bg-surface-raised px-2.5 py-1 text-[10px] text-fg-muted">
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full bg-emerald-400 transition-all",
          pulsing ? "scale-125 opacity-100" : "animate-pulse opacity-70",
        )}
      />
      <span>
        {countdown === 30 ? "30s otomatik yenileniyor" : `${countdown}s sonra yenilenir`}
      </span>
    </div>
  );
}

function asText(value: unknown, fallback = "Tanimsiz") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

const STATUS_TR: Record<string, string> = {
  // test result statuses
  passed:        "Geçti",
  failed:        "Başarısız",
  blocked:       "Engellendi",
  skipped:       "Atlandı",
  not_run:       "Çalıştırılmadı",
  // run / plan / cycle statuses
  in_progress:   "Devam Ediyor",
  running:       "Çalışıyor",
  completed:     "Tamamlandı",
  not_started:   "Başlamadı",
  draft:         "Taslak",
  active:        "Aktif",
  archived:      "Arşivlendi",
  // release decision
  GO:            "GO",
  NO_GO:         "NO GO",
  PENDING:       "Beklemede",
  // priority
  P0:            "P0 — Kritik",
  P1:            "P1 — Yüksek",
  P2:            "P2 — Orta",
  P3:            "P3 — Düşük",
  // test type
  manual:        "Manuel",
  automated:     "Otomatik",
  exploratory:   "Keşif",
  // checklist item status
  ok:            "Tamam",
  warning:       "Uyarı",
  error:         "Hata",
};

function tr(value: string | undefined | null, fallback?: string): string {
  if (!value) return fallback ?? "";
  return STATUS_TR[value] ?? fallback ?? value;
}

function StatCard({ label, value, note, tone = "neutral", href }: {
  label: string;
  value: string | number;
  note: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  href?: string;
}) {
  const toneClass = {
    neutral: "border-border bg-surface-raised",
    success: "border-emerald-500/20 bg-emerald-500/5",
    warning: "border-amber-500/20 bg-amber-500/5",
    danger: "border-red-500/20 bg-red-500/5",
    info: "border-blue-500/20 bg-blue-500/5",
  }[tone];

  const inner = (
    <>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-normal text-fg">{value}</p>
      <p className="mt-1 text-[11px] text-fg-muted">{note}</p>
    </>
  );

  if (href) {
    return (
      <Link href={href} className={cn("block rounded-xl border p-4 shadow-sm transition-colors hover:border-brand/40 hover:brightness-105", toneClass)}>
        {inner}
      </Link>
    );
  }
  return <section className={cn("rounded-xl border p-4 shadow-sm", toneClass)}>{inner}</section>;
}

// ─── Project Health Widget ────────────────────────────────────────────────────

interface HealthCriteria {
  label: string;
  passed: boolean;
  note: string;
}

function ProjectHealthWidget({
  passRatePct,
  coveragePct,
  criticalDefects,
  activeRuns,
}: {
  passRatePct: number;
  coveragePct: number;
  criticalDefects: number;
  activeRuns: number;
}) {
  const criteria: HealthCriteria[] = [
    {
      label: "Test Geçme Oranı",
      passed: passRatePct >= 85,
      note: passRatePct >= 85 ? `${passRatePct}% (hedef 85%)` : `${passRatePct}% (hedef 85%)`,
    },
    {
      label: "Kapsam",
      passed: coveragePct >= 70,
      note: coveragePct >= 70 ? `${coveragePct}% ✓` : `${coveragePct}% (hedef 70%)`,
    },
    {
      label: "Kritik Defect",
      passed: criticalDefects === 0,
      note: criticalDefects === 0 ? "Kritik defect yok" : `${criticalDefects} kritik defect`,
    },
    {
      label: "Aktif Koşum",
      passed: activeRuns > 0,
      note: activeRuns > 0 ? `${activeRuns} aktif koşum var` : "Aktif koşum yok",
    },
  ];

  const score = criteria.filter(c => c.passed).length * 25;
  const barColor =
    score >= 76 ? "bg-emerald-500" :
    score >= 51 ? "bg-amber-500"   : "bg-red-500";
  const scoreColor =
    score >= 76 ? "text-emerald-400" :
    score >= 51 ? "text-amber-400"   : "text-red-400";
  const labelColor =
    score >= 76 ? "Mükemmel" :
    score >= 51 ? "Orta"     : "Kritik";
  const filledBlocks = Math.round(score / 10);

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Proje Sağlığı</h2>
        <span className={cn("text-[11px] font-semibold", scoreColor)}>{labelColor}</span>
      </div>

      {/* Score bar */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex gap-0.5">
          {Array.from({ length: 10 }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "h-2.5 w-5 rounded-sm transition-colors",
                i < filledBlocks ? barColor : "bg-surface-accent",
              )}
            />
          ))}
        </div>
        <span className={cn("text-[13px] font-bold tabular-nums", scoreColor)}>
          {score}/100
        </span>
      </div>

      {/* Criteria grid */}
      <div className="grid gap-2 sm:grid-cols-2">
        {criteria.map(c => (
          <div
            key={c.label}
            className={cn(
              "flex items-center gap-2.5 rounded-lg border px-3 py-2",
              c.passed
                ? "border-emerald-500/20 bg-emerald-500/5"
                : "border-red-500/20 bg-red-500/5",
            )}
          >
            <span className={cn("flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] font-bold",
              c.passed ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
            )}>
              {c.passed ? "✓" : "✗"}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-medium text-fg">{c.label}</p>
              <p className={cn("text-[10px]", c.passed ? "text-emerald-400/80" : "text-red-400/80")}>{c.note}</p>
            </div>
          </div>
        ))}
      </div>
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

// ─── Setup Tracker Widget ─────────────────────────────────────────────────────

interface SetupCriterion {
  label: string;
  done: boolean;
  href: string;
}

function SetupTrackerWidget({
  projectId,
  totalCases,
  plansCount,
  runsCount,
  hasCompletedRun,
  requirementsCount,
}: {
  projectId: string;
  totalCases: number;
  plansCount: number;
  runsCount: number;
  hasCompletedRun: boolean;
  requirementsCount: number;
}) {
  const criteria: SetupCriterion[] = [
    {
      label: "İlk test senaryosu oluşturuldu",
      done: totalCases > 0,
      href: `/p/${projectId}/management/cases/new`,
    },
    {
      label: "İlk test planı var",
      done: plansCount > 0,
      href: `/p/${projectId}/management/plans`,
    },
    {
      label: "İlk test koşumu çalıştırıldı",
      done: runsCount > 0 && hasCompletedRun,
      href: `/p/${projectId}/management/runs`,
    },
    {
      label: "Gereksinim bağlantısı eklendi",
      done: requirementsCount > 0,
      href: `/p/${projectId}/management/requirements`,
    },
  ];

  const doneCount = criteria.filter(c => c.done).length;
  const pct = Math.round((doneCount / criteria.length) * 100);
  const allDone = doneCount === criteria.length;

  if (allDone) {
    return (
      <section className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-xl">🎉</span>
          <div>
            <p className="text-[14px] font-semibold text-emerald-400">Hazırsınız!</p>
            <p className="text-[12px] text-fg-muted">Tüm kurulum adımları tamamlandı.</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Kurulum Durumu</h2>
        <span className="text-[12px] font-semibold text-fg-muted">{pct}% Tamamlandı</span>
      </div>

      {/* Progress bar */}
      <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-surface-overlay">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="space-y-2">
        {criteria.map(c => (
          <div key={c.label} className="flex items-center gap-3">
            <span
              className={cn(
                "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                c.done
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-surface-overlay text-fg-subtle",
              )}
            >
              {c.done ? "✓" : "○"}
            </span>
            {c.done ? (
              <span className="text-[12px] text-fg-muted line-through">{c.label}</span>
            ) : (
              <Link href={c.href} className="text-[12px] text-fg hover:text-brand transition-colors">
                {c.label}
              </Link>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Blockers Widget ──────────────────────────────────────────────────────────

function BlockersWidget({ blockers, projectId }: { blockers: ReleaseBlocker[]; projectId: string }) {
  if (!blockers.length) {
    return (
      <section className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5 shadow-sm">
        <h2 className="mb-2 text-[14px] font-semibold text-fg">Release Blocker'lar</h2>
        <p className="text-[12px] text-emerald-400">Aktif blocker bulunmuyor — release hazir.</p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Release Blocker'lar</h2>
        <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-[11px] font-semibold text-red-400">
          {blockers.length} blocker
        </span>
      </div>
      <div className="space-y-2">
        {blockers.map(b => (
          <div key={b.label} className="rounded-lg border border-red-500/20 bg-surface-overlay px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[12px] font-medium text-fg">{b.label}</p>
              <span className="shrink-0 rounded bg-red-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-red-400 tabular-nums">
                {b.value}
              </span>
            </div>
            {b.detail && <p className="mt-0.5 text-[11px] text-fg-subtle">{b.detail}</p>}
          </div>
        ))}
      </div>
      <div className="mt-3">
        <Link
          href={`/p/${projectId}/management/defects`}
          className="text-[11px] text-brand hover:underline"
        >
          Defect listesine git →
        </Link>
      </div>
    </section>
  );
}

// ─── Release Signoff Widget ───────────────────────────────────────────────────

function ReleaseSignoffWidget({
  mpid,
  projectId,
  decision,
}: {
  mpid: string;
  projectId: string;
  decision: string;
}) {
  const signoffsQ = useReleaseSignoffs(mpid);
  const createSignoff = useCreateReleaseSignoff(mpid);
  const [showForm, setShowForm] = useState(false);
  const [role, setRole] = useState("QA Lead");
  const [comment, setComment] = useState("");
  const [approvalDecision, setApprovalDecision] = useState<"approved" | "rejected">("approved");

  const latestSignoff = (signoffsQ.data ?? []).sort(
    (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  )[0];

  const decisionColor =
    decision === "GO"
      ? "text-emerald-400"
      : decision === "NO_GO"
      ? "text-red-400"
      : "text-amber-400";

  function handleSubmit() {
    void createSignoff.mutateAsync({
      release_name: undefined,
      role,
      decision: approvalDecision,
      comment: comment.trim() || undefined,
      report_snapshot: {},
    }).then(() => {
      setShowForm(false);
      setComment("");
    });
  }

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Release Signoff</h2>
        <span className={cn("text-[12px] font-semibold", decisionColor)}>
          {tr(decision, "Beklemede")}
        </span>
      </div>

      {latestSignoff && (
        <div className="mb-3 rounded-lg border border-border bg-surface-overlay px-3 py-2">
          <p className="text-[12px] font-medium text-fg">
            {latestSignoff.decision === "approved" ? "Onaylandi" : "Reddedildi"} —{" "}
            {latestSignoff.role ?? "Bilinmeyen Rol"}
          </p>
          {latestSignoff.comment && (
            <p className="mt-0.5 text-[11px] text-fg-muted">{latestSignoff.comment}</p>
          )}
          <p className="mt-0.5 text-[10px] text-fg-subtle tabular-nums">
            {new Date(latestSignoff.signed_at).toLocaleDateString("tr-TR", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}
          </p>
        </div>
      )}

      {!signoffsQ.data?.length && (
        <p className="mb-3 text-[12px] text-fg-muted">Henuz onay verilmedi.</p>
      )}

      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="w-full rounded-lg bg-brand px-3 py-2 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
        >
          Onayla / Reddet
        </button>
      ) : (
        <div className="space-y-2">
          <div className="flex gap-2">
            <button
              onClick={() => setApprovalDecision("approved")}
              className={cn(
                "flex-1 rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors",
                approvalDecision === "approved"
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                  : "border-border bg-surface-overlay text-fg-muted",
              )}
            >
              Onayla
            </button>
            <button
              onClick={() => setApprovalDecision("rejected")}
              className={cn(
                "flex-1 rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors",
                approvalDecision === "rejected"
                  ? "border-red-500/40 bg-red-500/10 text-red-400"
                  : "border-border bg-surface-overlay text-fg-muted",
              )}
            >
              Reddet
            </button>
          </div>
          <input
            value={role}
            onChange={e => setRole(e.target.value)}
            placeholder="Rol (QA Lead, PM, ...)"
            className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[12px] text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1 focus:ring-brand"
          />
          <textarea
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder="Yorum (opsiyonel)"
            rows={2}
            className="w-full resize-none rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[12px] text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1 focus:ring-brand"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              disabled={createSignoff.isPending}
              className="flex-1 rounded-lg bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg disabled:opacity-50"
            >
              {createSignoff.isPending ? "Gonderiliyor..." : "Gonder"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[12px] text-fg-muted"
            >
              Iptal
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

export default function ManagementDashboardPage() {
  const router = useRouter();
  const rawProjectId = useRouteParam("projectId");

  useEffect(() => {
    if (!rawProjectId) {
      router.replace("/projects");
    }
  }, [rawProjectId, router]);

  const projectId = rawProjectId ?? "";
  const mpid = useManagementProjectId(rawProjectId || undefined);

  if (!rawProjectId) return null;

  const summaryFast = useManagementDashboardSummary(mpid || undefined);

  const repoQ = useManagementRepository(mpid || undefined);
  const runsQ = useManagementRuns(mpid || undefined);
  const summaryQ = useExecutionSummary(mpid || undefined);
  const defectsQ = useManagementDefects(mpid || undefined);
  const requirementsQ = useManagementRequirements(mpid || undefined);
  const releaseQ = useReleaseReport(mpid || undefined);
  const auditQ = useManagementAuditEvents(mpid || undefined, 10);
  const plansQ = useManagementPlans(mpid || undefined);

  const refreshAll = useCallback(() => {
    void summaryFast.refetch().catch(console.error);
    void repoQ.refetch().catch(console.error);
    void runsQ.refetch().catch(console.error);
    void summaryQ.refetch().catch(console.error);
    void defectsQ.refetch().catch(console.error);
    void requirementsQ.refetch().catch(console.error);
    void releaseQ.refetch().catch(console.error);
    void auditQ.refetch().catch(console.error);
    void plansQ.refetch().catch(console.error);
  }, [summaryFast, repoQ, runsQ, summaryQ, defectsQ, requirementsQ, releaseQ, auditQ, plansQ]);

  // Auto-refetch every 30s
  useEffect(() => {
    if (!mpid) return;
    const id = setInterval(refreshAll, REFETCH_INTERVAL);
    return () => clearInterval(id);
  }, [mpid, refreshAll]);

  const cases = useMemo(() => (repoQ.data?.cases ?? []).filter(tc => !tc.archived), [repoQ.data]);
  const runs = runsQ.data ?? [];
  const defects = defectsQ.data ?? [];
  const requirements = requirementsQ.data ?? [];
  const summary = summaryQ.data;
  const release = releaseQ.data;
  const blockers = release?.blockers ?? [];

  // Use the fast aggregated endpoint when available, fall back to client-side computation
  const activeRuns = summaryFast.data?.active_runs ?? runs.filter(run => ["running", "in_progress", "active"].includes(run.status)).length;
  const failedCases = summaryFast.data?.failed_cases ?? cases.filter(tc => tc.last_run_status === "failed").length;
  const blockedCases = summaryFast.data?.blocked_cases ?? cases.filter(tc => tc.last_run_status === "blocked").length;
  const notRunCases = summaryFast.data?.not_run_cases ?? cases.filter(tc => !tc.last_run_status || tc.last_run_status === "not_run").length;
  const criticalDefects = summaryFast.data?.critical_defects ?? defects.filter(d => ["critical", "blocker", "P0"].includes(d.severity)).length;
  const coveragePct = summaryFast.data?.coverage_pct ?? (requirements.length
    ? Math.round((requirements.filter(r => r.coverage_status === "covered").length / requirements.length) * 100)
    : release?.requirement_coverage_pct ?? 0);
  const totalCases = summaryFast.data?.total_cases ?? cases.length;
  const suiteCount = summaryFast.data?.suite_count ?? (repoQ.data?.suites.length ?? 0);
  const folderCount = summaryFast.data?.folder_count ?? (repoQ.data?.folders.length ?? 0);

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

  // If the fast summary endpoint already returned data, skip showing the skeleton
  // Only treat as loading when there is no error — errors must not cause infinite loading
  const hasError =
    summaryFast.isError ||
    repoQ.isError ||
    runsQ.isError ||
    summaryQ.isError ||
    defectsQ.isError ||
    requirementsQ.isError ||
    releaseQ.isError ||
    auditQ.isError ||
    plansQ.isError;

  const isLoading = summaryFast.data
    ? false
    : !hasError && (repoQ.isLoading || runsQ.isLoading || summaryQ.isLoading);

  const hasData = totalCases > 0 || runs.length > 0 || defects.length > 0 || requirements.length > 0;

  // Error fallback — show only when there is no cached data at all
  if (hasError && !summaryFast.data && !repoQ.data) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-sm text-fg-subtle">Veriler yüklenirken bir hata oluştu.</p>
        <button
          onClick={refreshAll}
          className="rounded-lg bg-brand px-4 py-2 text-sm text-white"
        >
          Tekrar Dene
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-full space-y-5 bg-surface-base px-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Neurex Management</p>
          <h1 className="mt-1 text-[20px] font-semibold tracking-normal text-fg">Dashboard</h1>
          <p className="mt-1 text-[12px] text-fg-muted">Manuel test kapsamı, run sagligi, defect riski ve release hazirligi.</p>
        </div>
        <div className="flex items-center gap-2">
          <AutoRefreshBadge />
          <Link href={`/p/${projectId}/management/repository`} className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-[12px] font-semibold text-fg-muted hover:text-fg">
            Repository
          </Link>
          <Link href={`/p/${projectId}/management/runs`} className="rounded-lg bg-brand px-3 py-2 text-[12px] font-semibold text-brand-fg shadow-sm hover:brightness-105">
            Run baslat
          </Link>
        </div>
      </div>

      {isLoading && !hasError ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-xl border border-border bg-surface-raised" />)}
        </div>
      ) : !hasData ? (
        mpid ? <QuickSetupWizard projectId={projectId} mpid={mpid} /> : <EmptyState projectId={projectId} />
      ) : (
        <>
          <div className="grid gap-5 xl:grid-cols-2">
            <ProjectHealthWidget
              passRatePct={summaryFast.data?.pass_rate_pct ?? summary?.pass_rate_pct ?? release?.pass_rate_pct ?? 0}
              coveragePct={coveragePct}
              criticalDefects={criticalDefects}
              activeRuns={activeRuns}
            />
            <SetupTrackerWidget
              projectId={projectId}
              totalCases={totalCases}
              plansCount={plansQ.data?.length ?? 0}
              runsCount={runs.length}
              hasCompletedRun={runs.some(r => r.status === "completed")}
              requirementsCount={requirements.length}
            />
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Toplam manuel case" value={totalCases} note={`${suiteCount} suite, ${folderCount} klasor`} href={`/p/${projectId}/management/repository`} />
            <StatCard label="Aktif koşum" value={activeRuns} note={`${runs.length} toplam koşum`} tone="info" href={`/p/${projectId}/management/runs`} />
            <StatCard label="Geçme oranı" value={`${summaryFast.data?.pass_rate_pct ?? summary?.pass_rate_pct ?? release?.pass_rate_pct ?? 0}%`} note={`${summary?.passed ?? 0} geçti`} tone="success" href={`/p/${projectId}/management/reports`} />
            <StatCard label="Başarısız case" value={failedCases} note="Acil triage bekleyen case" tone="danger" href={`/p/${projectId}/management/repository`} />
            <StatCard label="Engellenen case" value={blockedCases} note="Ortam veya veri engeli" tone="warning" href={`/p/${projectId}/management/repository`} />
            <StatCard label="Çalıştırılmayan case" value={notRunCases} note="Kapsama alınmış ama çalıştırılmamış" href={`/p/${projectId}/management/repository`} />
            <StatCard label="Kritik defect" value={criticalDefects} note={`${defects.length} toplam defect`} tone={criticalDefects ? "danger" : "success"} href={`/p/${projectId}/management/defects`} />
            <StatCard label="Test kapsami" value={`${coveragePct}%`} note={`${requirements.length} requirement linki`} tone="info" href={`/p/${projectId}/management/requirements`} />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <BlockersWidget blockers={blockers} projectId={projectId} />
            {mpid && (
              <ReleaseSignoffWidget
                mpid={mpid}
                projectId={projectId}
                decision={release?.decision ?? "PENDING"}
              />
            )}
          </div>

          <div className="grid gap-5 xl:grid-cols-3">
            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm xl:col-span-2">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-[14px] font-semibold text-fg">Regresyon ve release hazirligi</h2>
                <span className="rounded-full border border-border bg-surface-overlay px-2 py-1 text-[11px] text-fg-muted">
                  {tr(release?.decision, "Beklemede")}
                </span>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <MiniBar label="Koşum ilerlemesi" value={summary?.progress_pct ?? release?.progress_pct ?? 0} max={100} tone="bg-blue-500" />
                <MiniBar label="Geçme oranı" value={summary?.pass_rate_pct ?? release?.pass_rate_pct ?? 0} max={100} tone="bg-emerald-500" />
                <MiniBar label="Gereksinim kapsamı" value={coveragePct} max={100} tone="bg-teal-500" />
              </div>
              <div className="mt-5 grid gap-2 md:grid-cols-2">
                {(release?.checklist ?? []).slice(0, 4).map(item => (
                  <div key={item.label} className="rounded-lg border border-border bg-surface-overlay px-3 py-2">
                    <p className="text-[12px] font-medium text-fg">{item.label}</p>
                    <p className="text-[11px] text-fg-subtle">{item.metric} · {tr(item.status, item.status)}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Test uzmanı iş yükü</h2>
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
                { label: "Defect Ekle",       href: `/p/${projectId}/management/defects`,             color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
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
                    <p className="mt-0.5 text-[11px] text-fg-subtle">{tr(run.status)} · {run.environment ?? "ortam yok"}</p>
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
                    <p className="mt-0.5 text-[11px] text-fg-subtle">{tr(tc.priority)} · {tr(tc.type)} · {tr(tc.status)}</p>
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
                      {new Date(ev.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
                      {" "}
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
