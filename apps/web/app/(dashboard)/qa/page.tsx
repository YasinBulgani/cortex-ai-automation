import { promises as fs } from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import matter from "gray-matter";

export const metadata = { title: "QA Dashboard — Cortex AI Automation" };

// Server component — qa/ klasöründen build-time / SSR'da okur
async function loadQaData() {
  const repoRoot = path.resolve(process.cwd(), "../..");
  const qaRoot = path.join(repoRoot, "qa");

  async function walk(dir: string, pattern: RegExp): Promise<string[]> {
    let out: string[] = [];
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      for (const e of entries) {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) out = out.concat(await walk(full, pattern));
        else if (pattern.test(e.name)) out.push(full);
      }
    } catch {}
    return out;
  }

  const tcFiles = await walk(path.join(qaRoot, "cases"), /^TC-.*\.md$/);
  const runFiles = await walk(path.join(qaRoot, "runs"), /^TR-.*\.yml$/);
  const reqFiles = await walk(path.join(qaRoot, "requirements"), /^REQ-.*\.md$/);

  const tcs = [];
  for (const f of tcFiles) {
    try {
      const raw = await fs.readFile(f, "utf8");
      const m = matter(raw, {
        engines: {
          yaml: {
            parse: (i: string) => {
              const parsed = yaml.load(i, { schema: yaml.JSON_SCHEMA });
              return typeof parsed === "object" && parsed !== null ? parsed : {};
            },
            stringify: (i: object) => yaml.dump(i),
          },
        },
      });
      tcs.push({ ...(m.data as any), _file: f });
    } catch {}
  }

  const runs = [];
  for (const f of runFiles) {
    try {
      const raw = await fs.readFile(f, "utf8");
      const data = yaml.load(raw, { schema: yaml.JSON_SCHEMA }) as any;
      runs.push(data);
    } catch {}
  }

  return { tcs, runs, reqCount: reqFiles.length };
}

interface SuiteAgg {
  total: number;
  automated: number;
  P0: number;
  P1: number;
  P2: number;
  P3: number;
}

export default async function QaDashboardPage() {
  const { tcs, runs, reqCount } = await loadQaData();

  const totalTcs = tcs.length;
  const automated = tcs.filter((t: any) => t.automation?.status === "automated").length;
  const autoPct = totalTcs > 0 ? Math.round((automated / totalTcs) * 100) : 0;

  const sortedRuns = runs
    .slice()
    .sort((a: any, b: any) => (b.started || "").localeCompare(a.started || ""));
  const recentRuns = sortedRuns.slice(0, 8);

  const suites: Record<string, SuiteAgg> = {};
  for (const t of tcs) {
    const s = t.suite || "?";
    suites[s] ??= { total: 0, automated: 0, P0: 0, P1: 0, P2: 0, P3: 0 };
    suites[s].total++;
    if (t.automation?.status === "automated") suites[s].automated++;
    const prio = t.priority as keyof SuiteAgg;
    if (prio === "P0" || prio === "P1" || prio === "P2" || prio === "P3") {
      suites[s][prio]++;
    }
  }

  const lastResultByTc = new Map<string, { runId: string; status: string }>();
  for (const r of runs.slice().sort((a: any, b: any) => (a.started || "").localeCompare(b.started || ""))) {
    for (const res of r.results || []) {
      lastResultByTc.set(res.tc, { runId: r.id, status: res.status });
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 text-sm">
      <header className="mb-8 flex items-baseline justify-between border-b border-gray-200 pb-4">
        <div>
          <h1 className="text-2xl font-semibold">QA Dashboard</h1>
          <p className="text-gray-500">qa/ klasöründen real-time veri</p>
        </div>
        <span className="text-xs text-gray-400">
          {new Date().toISOString().slice(0, 16).replace("T", " ")}
        </span>
      </header>

      <section className="mb-8">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Key Metrics
        </h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Kpi label="Total TC" value={String(totalTcs)} sub={`${Object.keys(suites).length} suite`} />
          <Kpi
            label="Automation"
            value={`${autoPct}%`}
            sub={`${automated}/${totalTcs}`}
            tone={autoPct >= 70 ? "good" : autoPct >= 40 ? "warn" : "bad"}
          />
          <Kpi label="Requirements" value={String(reqCount)} sub="Atomik + umbrella" />
          <Kpi
            label="Test Runs"
            value={String(runs.length)}
            sub={runs.length > 0 ? `son: ${sortedRuns[0]?.started?.slice(0, 10)}` : "yok"}
          />
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Coverage Matrix
        </h2>
        <div className="overflow-x-auto rounded border border-gray-200 bg-white">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-500">
              <tr>
                <th className="px-3 py-2">Suite</th>
                <th className="px-3 py-2 text-right">P0</th>
                <th className="px-3 py-2 text-right">P1</th>
                <th className="px-3 py-2 text-right">P2</th>
                <th className="px-3 py-2 text-right">P3</th>
                <th className="px-3 py-2 text-right">Total</th>
                <th className="px-3 py-2 text-right">Auto</th>
                <th className="px-3 py-2">%</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(suites)
                .sort()
                .map((s) => {
                  const m = suites[s];
                  const pct = m.total > 0 ? Math.round((m.automated / m.total) * 100) : 0;
                  return (
                    <tr key={s} className="border-t border-gray-100">
                      <td className="px-3 py-2 font-medium">{s}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{m.P0 || ""}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{m.P1 || ""}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{m.P2 || ""}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{m.P3 || ""}</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums">{m.total}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{m.automated}</td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-24 overflow-hidden rounded bg-gray-100">
                            <div className="h-full bg-green-500" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-xs text-gray-500">{pct}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Recent Runs
        </h2>
        {recentRuns.length === 0 ? (
          <div className="rounded border border-dashed border-gray-200 bg-gray-50 p-6 text-center text-gray-400">
            Henüz koşum yok. <code>npm run run-record</code> veya{" "}
            <code>npm run import-results</code> deneyin.
          </div>
        ) : (
          <ul className="divide-y divide-gray-100 rounded border border-gray-200 bg-white">
            {recentRuns.map((r: any) => {
              const s = r.summary || {};
              const total = s.total || 1;
              return (
                <li key={r.id} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <div className="font-medium">{r.id}</div>
                    <div className="text-xs text-gray-500">
                      plan: {r.plan} · {r.environment?.branch}@{r.environment?.commit}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs tabular-nums text-gray-500">
                      {s.passed}/{s.total}
                    </span>
                    <div className="flex h-2 w-32 overflow-hidden rounded bg-gray-100">
                      <div style={{ width: `${((s.passed || 0) / total) * 100}%`, background: "#22c55e" }} />
                      <div style={{ width: `${((s.failed || 0) / total) * 100}%`, background: "#ef4444" }} />
                      <div style={{ width: `${((s.blocked || 0) / total) * 100}%`, background: "#f59e0b" }} />
                      <div style={{ width: `${((s.skipped || 0) / total) * 100}%`, background: "#9ca3af" }} />
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Test Cases ({totalTcs})
        </h2>
        <div className="overflow-x-auto rounded border border-gray-200 bg-white">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-500">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Suite</th>
                <th className="px-3 py-2">Prio</th>
                <th className="px-3 py-2">Automation</th>
                <th className="px-3 py-2">Last Status</th>
              </tr>
            </thead>
            <tbody>
              {tcs.slice(0, 100).map((t: any) => {
                const last = lastResultByTc.get(t.id);
                return (
                  <tr key={t.id} className="border-t border-gray-100">
                    <td className="px-3 py-1.5 font-mono text-xs">{t.id}</td>
                    <td className="px-3 py-1.5">{t.title}</td>
                    <td className="px-3 py-1.5 text-gray-500">{t.suite}</td>
                    <td className="px-3 py-1.5">
                      <PriorityBadge p={t.priority} />
                    </td>
                    <td className="px-3 py-1.5">
                      <AutoBadge s={t.automation?.status || "unknown"} />
                    </td>
                    <td className="px-3 py-1.5">
                      {last ? <StatusBadge s={last.status} /> : <span className="text-gray-400">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {tcs.length > 100 ? (
            <div className="px-3 py-2 text-xs text-gray-400">
              + {tcs.length - 100} more (filtre eklenecek)
            </div>
          ) : null}
        </div>
      </section>

      <footer className="mt-12 border-t border-gray-100 pt-4 text-center text-xs text-gray-400">
        qa/ system · {totalTcs} TC · {runs.length} runs · git-native · zero SaaS lock-in
      </footer>
    </main>
  );
}

function Kpi({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "good" | "warn" | "bad" | "neutral";
}) {
  const toneColor =
    tone === "good"
      ? "text-green-600"
      : tone === "warn"
        ? "text-amber-600"
        : tone === "bad"
          ? "text-red-600"
          : "text-gray-900";
  return (
    <div className="rounded border border-gray-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wider text-gray-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${toneColor}`}>{value}</div>
      {sub ? <div className="mt-0.5 text-xs text-gray-500">{sub}</div> : null}
    </div>
  );
}

function PriorityBadge({ p }: { p: string }) {
  const tone =
    p === "P0"
      ? "bg-red-100 text-red-700"
      : p === "P1"
        ? "bg-amber-100 text-amber-700"
        : p === "P2"
          ? "bg-blue-100 text-blue-700"
          : "bg-gray-100 text-gray-600";
  return <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${tone}`}>{p}</span>;
}

function AutoBadge({ s }: { s: string }) {
  const tone =
    s === "automated"
      ? "bg-green-100 text-green-700"
      : s === "in-progress"
        ? "bg-amber-100 text-amber-700"
        : s === "out-of-scope"
          ? "bg-gray-100 text-gray-500"
          : "bg-gray-100 text-gray-600";
  return <span className={`rounded px-1.5 py-0.5 text-xs ${tone}`}>{s}</span>;
}

function StatusBadge({ s }: { s: string }) {
  const tone =
    s === "pass"
      ? "bg-green-100 text-green-700"
      : s === "fail"
        ? "bg-red-100 text-red-700"
        : s === "blocked"
          ? "bg-amber-100 text-amber-700"
          : "bg-gray-100 text-gray-600";
  return <span className={`rounded px-1.5 py-0.5 text-xs ${tone}`}>{s}</span>;
}
