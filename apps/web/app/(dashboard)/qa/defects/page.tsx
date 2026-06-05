"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api-client";

export const dynamic = "force-dynamic";

// ── Types ──────────────────────────────────────────────────────────────────

type TestCaseListItem = {
  id: string;
  title: string;
  suite: string;
  priority: "P0" | "P1" | "P2" | "P3";
  status: string;
  owner: string;
  last_run: string | null;
  last_status: string | null;
  open_defects_count: number;
};

type RunResult = {
  tc: string;
  status: string;
  defect: string | null;
  note: string | null;
};

type Run = {
  id: string;
  plan: string;
  started: string;
  executor: string;
  environment: { branch: string; commit: string };
  summary: { total: number; passed: number; failed: number; blocked: number; skipped: number };
  results: RunResult[];
};

/** Derived defect record built from case + run data */
type DefectRecord = {
  key: string;
  tc_id: string;
  tc_title: string;
  tc_suite: string;
  tc_priority: string;
  run_id: string | null;
  run_started: string | null;
  defect_ref: string | null;
  status: "open" | "in-progress" | "closed";
  note: string | null;
};

// ── Badge tone maps ────────────────────────────────────────────────────────

const PRIO_TONE: Record<string, string> = {
  P0: "bg-red-100 text-red-700",
  P1: "bg-amber-100 text-amber-700",
  P2: "bg-blue-100 text-blue-700",
  P3: "bg-gray-100 text-gray-600",
};

const DEFECT_STATUS_TONE: Record<string, string> = {
  open: "bg-red-100 text-red-700",
  "in-progress": "bg-amber-100 text-amber-700",
  closed: "bg-green-100 text-green-700",
};

// ── Helpers ────────────────────────────────────────────────────────────────

function deriveDefects(cases: TestCaseListItem[], runs: Run[]): DefectRecord[] {
  const records: DefectRecord[] = [];
  const seen = new Set<string>();

  // Sort runs newest-first
  const sortedRuns = runs
    .slice()
    .sort((a, b) => b.started.localeCompare(a.started));

  // Build tc → latest failing result map
  const latestFail = new Map<string, { run: Run; result: RunResult }>();
  for (const run of sortedRuns.slice().reverse()) {
    for (const res of run.results ?? []) {
      if (res.status === "fail" || res.status === "blocked") {
        latestFail.set(res.tc, { run, result: res });
      }
    }
  }

  // 1) Cases with open_defects_count > 0 → "open"
  for (const tc of cases) {
    if (tc.open_defects_count > 0) {
      const key = `${tc.id}-open`;
      if (!seen.has(key)) {
        seen.add(key);
        const hit = latestFail.get(tc.id);
        records.push({
          key,
          tc_id: tc.id,
          tc_title: tc.title,
          tc_suite: tc.suite,
          tc_priority: tc.priority,
          run_id: tc.last_run ?? hit?.run.id ?? null,
          run_started: hit?.run.started ?? null,
          defect_ref: hit?.result.defect ?? null,
          status: "open",
          note: hit?.result.note ?? null,
        });
      }
    }
  }

  // 2) Failing results in recent runs that have a defect ref → derive status from ref prefix
  for (const run of sortedRuns.slice(0, 20)) {
    for (const res of run.results ?? []) {
      if (!res.defect) continue;
      const key = `${res.tc}-${run.id}-${res.defect}`;
      if (seen.has(key)) continue;
      seen.add(key);

      const tc = cases.find((c) => c.id === res.tc);
      // If the defect ref starts with GH- it was opened; infer closed if tc.last_status === pass
      const isClosed =
        tc?.last_status === "pass" || tc?.last_status === "skipped";
      records.push({
        key,
        tc_id: res.tc,
        tc_title: tc?.title ?? res.tc,
        tc_suite: tc?.suite ?? "—",
        tc_priority: tc?.priority ?? "P3",
        run_id: run.id,
        run_started: run.started,
        defect_ref: res.defect,
        status: isClosed ? "closed" : "open",
        note: res.note ?? null,
      });
    }
  }

  // 3) Remaining failing results without a defect ref → "in-progress" (needs triage)
  for (const run of sortedRuns.slice(0, 10)) {
    for (const res of run.results ?? []) {
      if (res.status !== "fail") continue;
      if (res.defect) continue; // already covered above
      const key = `${res.tc}-${run.id}-nref`;
      if (seen.has(key)) continue;
      // Skip if there's already an "open" record for this tc
      if (records.find((r) => r.tc_id === res.tc && r.status === "open")) continue;
      seen.add(key);

      const tc = cases.find((c) => c.id === res.tc);
      records.push({
        key,
        tc_id: res.tc,
        tc_title: tc?.title ?? res.tc,
        tc_suite: tc?.suite ?? "—",
        tc_priority: tc?.priority ?? "P3",
        run_id: run.id,
        run_started: run.started,
        defect_ref: null,
        status: "in-progress",
        note: res.note ?? null,
      });
    }
  }

  return records;
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function DefectsPage() {
  const [cases, setCases] = useState<TestCaseListItem[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [prioFilter, setPrioFilter] = useState<string>("");
  const [q, setQ] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [casesData, runsData] = await Promise.all([
        apiFetch<{ items: TestCaseListItem[]; total: number }>(
          "/api/v1/qa/cases?limit=500",
        ),
        apiFetch<Run[]>("/api/v1/qa/runs?limit=50").catch(() => [] as Run[]),
      ]);
      setCases(casesData.items ?? []);
      setRuns(Array.isArray(runsData) ? runsData : []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const allDefects = useMemo(() => deriveDefects(cases, runs), [cases, runs]);

  const filtered = useMemo(() => {
    const qLower = q.toLowerCase();
    return allDefects.filter((d) => {
      if (statusFilter && d.status !== statusFilter) return false;
      if (prioFilter && d.tc_priority !== prioFilter) return false;
      if (
        qLower &&
        !`${d.tc_id} ${d.tc_title} ${d.tc_suite} ${d.defect_ref ?? ""}`
          .toLowerCase()
          .includes(qLower)
      )
        return false;
      return true;
    });
  }, [allDefects, statusFilter, prioFilter, q]);

  const counts = useMemo(
    () => ({
      open: allDefects.filter((d) => d.status === "open").length,
      inProgress: allDefects.filter((d) => d.status === "in-progress").length,
      closed: allDefects.filter((d) => d.status === "closed").length,
    }),
    [allDefects],
  );

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 text-sm">
      <header className="mb-6 flex items-center justify-between border-b border-gray-200 pb-4">
        <div>
          <h1 className="text-xl font-semibold">Defects</h1>
          <p className="mt-1 text-sm text-gray-500">
            {loading
              ? "Yükleniyor..."
              : `${allDefects.length} defect · ${counts.open} open · ${counts.inProgress} in-progress · ${counts.closed} closed`}
          </p>
        </div>
        <Link
          href="/qa/defects/new"
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          + New Defect
        </Link>
      </header>

      {/* Summary KPIs */}
      {!loading && allDefects.length > 0 && (
        <div className="mb-6 grid grid-cols-3 gap-3">
          <KpiCard
            label="Open"
            value={counts.open}
            tone="bg-red-50 border-red-200 text-red-700"
          />
          <KpiCard
            label="In Progress"
            value={counts.inProgress}
            tone="bg-amber-50 border-amber-200 text-amber-700"
          />
          <KpiCard
            label="Closed"
            value={counts.closed}
            tone="bg-green-50 border-green-200 text-green-700"
          />
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="TC ID, başlık, defect ref ile ara..."
          className="min-w-[240px] flex-1 rounded border border-gray-200 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded border border-gray-200 bg-white px-2 py-1.5 text-sm"
        >
          <option value="">Tüm status</option>
          <option value="open">Open</option>
          <option value="in-progress">In Progress</option>
          <option value="closed">Closed</option>
        </select>
        <select
          value={prioFilter}
          onChange={(e) => setPrioFilter(e.target.value)}
          className="rounded border border-gray-200 bg-white px-2 py-1.5 text-sm"
        >
          <option value="">Tüm öncelik</option>
          {["P0", "P1", "P2", "P3"].map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <button
          onClick={load}
          disabled={loading}
          className="rounded bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
        >
          {loading ? "..." : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && allDefects.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-10 animate-pulse rounded border border-gray-100 bg-gray-50"
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && allDefects.length === 0 && !error && (
        <div className="rounded border border-dashed border-gray-200 bg-gray-50 p-12 text-center">
          <div className="text-3xl text-gray-300">✓</div>
          <p className="mt-3 text-base font-medium text-gray-600">
            Açık defect bulunamadı
          </p>
          <p className="mt-1 text-sm text-gray-400">
            Hiçbir test case&apos;de açık defect yok ve son koşumlarda fail
            yok.
          </p>
          <Link
            href="/qa/defects/new"
            className="mt-4 inline-block rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            + New Defect
          </Link>
        </div>
      )}

      {/* Defects table */}
      {!loading && allDefects.length > 0 && (
        <>
          <div className="overflow-x-auto rounded border border-gray-200 bg-white">
            <table className="w-full">
              <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="px-3 py-2">TC</th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Suite</th>
                  <th className="px-3 py-2">Priority</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Defect Ref</th>
                  <th className="px-3 py-2">Run</th>
                  <th className="px-3 py-2">Note</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => (
                  <tr
                    key={d.key}
                    className="border-t border-gray-100 hover:bg-gray-50"
                  >
                    <td className="px-3 py-1.5 font-mono text-xs">
                      <Link
                        href={`/qa/cases/${d.tc_id}/edit`}
                        className="text-blue-600 hover:underline"
                      >
                        {d.tc_id}
                      </Link>
                    </td>
                    <td className="max-w-xs truncate px-3 py-1.5">
                      {d.tc_title}
                    </td>
                    <td className="px-3 py-1.5 text-gray-500">{d.tc_suite}</td>
                    <td className="px-3 py-1.5">
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-semibold ${PRIO_TONE[d.tc_priority] ?? "bg-gray-100 text-gray-600"}`}
                      >
                        {d.tc_priority}
                      </span>
                    </td>
                    <td className="px-3 py-1.5">
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-semibold ${DEFECT_STATUS_TONE[d.status] ?? "bg-gray-100 text-gray-600"}`}
                      >
                        {d.status}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 font-mono text-xs">
                      {d.defect_ref ? (
                        d.defect_ref.startsWith("GH-") ? (
                          <span className="text-blue-600">{d.defect_ref}</span>
                        ) : (
                          <span className="text-gray-600">{d.defect_ref}</span>
                        )
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-xs text-gray-500">
                      {d.run_id ?? "—"}
                    </td>
                    <td className="max-w-[200px] truncate px-3 py-1.5 text-gray-500">
                      {d.note ?? ""}
                    </td>
                    <td className="px-3 py-1.5">
                      <Link
                        href={`/qa/defects/new?tc=${d.tc_id}&run=${d.run_id ?? ""}`}
                        className="rounded px-2 py-0.5 text-xs text-red-600 hover:underline"
                      >
                        Open Issue
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
            <span>
              {filtered.length} / {allDefects.length} defect görüntüleniyor
            </span>
            <span className="italic">
              Defect verisi case open_defects + koşum sonuçlarından türetilmiştir.
            </span>
          </div>
        </>
      )}
    </main>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: string;
}) {
  return (
    <div className={`rounded border p-4 ${tone}`}>
      <div className="text-xs font-semibold uppercase tracking-wider opacity-70">
        {label}
      </div>
      <div className="mt-1 text-3xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}
