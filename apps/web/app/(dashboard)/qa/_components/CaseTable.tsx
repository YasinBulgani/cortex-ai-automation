"use client";

import { useEffect, useMemo, useState } from "react";

type TestCase = {
  id: string;
  title: string;
  suite: string;
  priority: "P0" | "P1" | "P2" | "P3";
  type: string[];
  status: string;
  automation_status: string;
  owner: string;
  last_run: string | null;
  last_status: string | null;
  open_defects_count: number;
};

const PRIO_TONE: Record<string, string> = {
  P0: "bg-red-100 text-red-700",
  P1: "bg-amber-100 text-amber-700",
  P2: "bg-blue-100 text-blue-700",
  P3: "bg-gray-100 text-gray-600",
};

const STATUS_TONE: Record<string, string> = {
  pass: "bg-green-100 text-green-700",
  fail: "bg-red-100 text-red-700",
  blocked: "bg-amber-100 text-amber-700",
  skipped: "bg-gray-100 text-gray-600",
};

const AUTO_TONE: Record<string, string> = {
  automated: "bg-green-100 text-green-700",
  "in-progress": "bg-amber-100 text-amber-700",
  "out-of-scope": "bg-gray-100 text-gray-500",
  "not-automated": "bg-gray-100 text-gray-600",
};

export default function CaseTable({ initialCases }: { initialCases: TestCase[] }) {
  const [cases, setCases] = useState<TestCase[]>(initialCases);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [suiteFilter, setSuiteFilter] = useState<string>("");
  const [prioFilter, setPrioFilter] = useState<string>("");
  const [autoFilter, setAutoFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  const [selected, setSelected] = useState<TestCase | null>(null);

  const suites = useMemo(() => Array.from(new Set(cases.map((c) => c.suite))).sort(), [cases]);

  const filtered = useMemo(() => {
    const qLower = q.toLowerCase();
    return cases.filter((c) => {
      if (qLower && !`${c.id} ${c.title} ${c.suite} ${c.owner}`.toLowerCase().includes(qLower))
        return false;
      if (suiteFilter && c.suite !== suiteFilter) return false;
      if (prioFilter && c.priority !== prioFilter) return false;
      if (autoFilter && c.automation_status !== autoFilter) return false;
      if (statusFilter === "never-run" && c.last_status) return false;
      if (statusFilter && statusFilter !== "never-run" && c.last_status !== statusFilter) return false;
      return true;
    });
  }, [cases, q, suiteFilter, prioFilter, autoFilter, statusFilter]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (suiteFilter) params.set("suite", suiteFilter);
      if (prioFilter) params.set("priority", prioFilter);
      if (autoFilter) params.set("automation_status", autoFilter);
      const res = await fetch(`/api/v1/qa/cases?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCases(data.items);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="ID, başlık, suite, owner ile filtrele..."
          className="flex-1 min-w-[240px] rounded border border-gray-200 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <select value={suiteFilter} onChange={(e) => setSuiteFilter(e.target.value)} className="rounded border border-gray-200 bg-white px-2 py-1.5 text-sm">
          <option value="">Tüm suite</option>
          {suites.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select value={prioFilter} onChange={(e) => setPrioFilter(e.target.value)} className="rounded border border-gray-200 bg-white px-2 py-1.5 text-sm">
          <option value="">Tüm öncelik</option>
          {["P0", "P1", "P2", "P3"].map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <select value={autoFilter} onChange={(e) => setAutoFilter(e.target.value)} className="rounded border border-gray-200 bg-white px-2 py-1.5 text-sm">
          <option value="">Tüm automation</option>
          <option value="automated">Automated</option>
          <option value="in-progress">In progress</option>
          <option value="not-automated">Not automated</option>
          <option value="out-of-scope">Out of scope</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded border border-gray-200 bg-white px-2 py-1.5 text-sm">
          <option value="">Tüm son durum</option>
          <option value="pass">Pass</option>
          <option value="fail">Fail</option>
          <option value="blocked">Blocked</option>
          <option value="skipped">Skipped</option>
          <option value="never-run">Hiç koşmamış</option>
        </select>
        <button
          onClick={refresh}
          disabled={loading}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "..." : "↻ Refresh"}
        </button>
      </div>

      <div className="mb-2 text-xs text-gray-500">
        {filtered.length} / {cases.length} TC görüntüleniyor
        {error && <span className="ml-2 text-red-600">— {error}</span>}
      </div>

      <div className="overflow-x-auto rounded border border-gray-200 bg-white">
        <table className="w-full">
          <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-500">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Suite</th>
              <th className="px-3 py-2">Prio</th>
              <th className="px-3 py-2">Automation</th>
              <th className="px-3 py-2">Last Run</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2 text-right">Defects</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 250).map((tc) => (
              <tr
                key={tc.id}
                onClick={() => setSelected(tc)}
                className="cursor-pointer border-t border-gray-100 hover:bg-blue-50"
              >
                <td className="px-3 py-1.5 font-mono text-xs">{tc.id}</td>
                <td className="px-3 py-1.5">{tc.title}</td>
                <td className="px-3 py-1.5 text-gray-500">{tc.suite}</td>
                <td className="px-3 py-1.5">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${PRIO_TONE[tc.priority]}`}>
                    {tc.priority}
                  </span>
                </td>
                <td className="px-3 py-1.5">
                  <span className={`rounded px-1.5 py-0.5 text-xs ${AUTO_TONE[tc.automation_status] || "bg-gray-100 text-gray-600"}`}>
                    {tc.automation_status}
                  </span>
                </td>
                <td className="px-3 py-1.5 font-mono text-xs text-gray-500">
                  {tc.last_run || "—"}
                </td>
                <td className="px-3 py-1.5">
                  {tc.last_status ? (
                    <span className={`rounded px-1.5 py-0.5 text-xs ${STATUS_TONE[tc.last_status] || "bg-gray-100"}`}>
                      {tc.last_status}
                    </span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="px-3 py-1.5 text-right tabular-nums">
                  {tc.open_defects_count > 0 ? (
                    <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700">
                      {tc.open_defects_count}
                    </span>
                  ) : (
                    ""
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 250 && (
          <div className="px-3 py-2 text-xs text-gray-400">
            +{filtered.length - 250} more — filtre uygulayın
          </div>
        )}
      </div>

      {selected && <CaseDetailModal tc={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function CaseDetailModal({ tc, onClose }: { tc: TestCase; onClose: () => void }) {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/v1/qa/cases/${tc.id}`)
      .then((r) => r.json())
      .then(setDetail)
      .catch(() => setDetail({ error: "load failed" }))
      .finally(() => setLoading(false));
  }, [tc.id]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-12" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-start justify-between border-b border-gray-200 pb-3">
          <div>
            <h2 className="font-mono text-lg font-semibold">{tc.id}</h2>
            <h3 className="mt-1 text-base">{tc.title}</h3>
          </div>
          <button onClick={onClose} className="rounded px-3 py-1 text-sm hover:bg-gray-100">
            ✕
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-gray-400">Yükleniyor...</div>
        ) : detail?.error ? (
          <div className="py-12 text-center text-red-600">Hata: {detail.error}</div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <DetailRow label="Suite" value={detail.suite} />
              <DetailRow label="Priority" value={detail.priority} />
              <DetailRow label="Type" value={(detail.type || []).join(", ")} />
              <DetailRow label="Status" value={detail.status} />
              <DetailRow label="Owner" value={detail.owner} />
              <DetailRow label="Estimated" value={`${detail.estimated_minutes || "?"} dk`} />
              <DetailRow label="Automation" value={detail.automation?.status} />
              <DetailRow label="Created" value={detail.created} />
            </div>

            {detail.automation?.refs?.length > 0 && (
              <div>
                <div className="mb-1 text-xs font-semibold uppercase text-gray-500">Automation refs</div>
                <ul className="space-y-0.5">
                  {detail.automation.refs.map((r: string) => (
                    <li key={r} className="font-mono text-xs text-blue-600">{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {detail.requirements?.length > 0 && (
              <div>
                <div className="mb-1 text-xs font-semibold uppercase text-gray-500">Requirements</div>
                <div className="flex flex-wrap gap-1">
                  {detail.requirements.map((r: string) => (
                    <span key={r} className="rounded bg-blue-50 px-2 py-0.5 font-mono text-xs text-blue-700">{r}</span>
                  ))}
                </div>
              </div>
            )}

            {detail.pre_conditions?.length > 0 && (
              <div>
                <div className="mb-1 text-xs font-semibold uppercase text-gray-500">Pre-conditions</div>
                <div className="flex flex-wrap gap-1">
                  {detail.pre_conditions.map((r: string) => (
                    <span key={r} className="rounded bg-purple-50 px-2 py-0.5 font-mono text-xs text-purple-700">{r}</span>
                  ))}
                </div>
              </div>
            )}

            <div>
              <div className="mb-2 text-xs font-semibold uppercase text-gray-500">Body</div>
              <pre className="max-h-96 overflow-y-auto rounded bg-gray-50 p-3 text-xs whitespace-pre-wrap font-mono">
                {detail.body || "(boş)"}
              </pre>
            </div>

            <div className="flex gap-2 border-t border-gray-200 pt-3">
              <a
                href={`/qa/cases/${tc.id}/edit`}
                className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                Düzenle
              </a>
              {tc.last_status === "fail" && (
                <a
                  href={`/qa/defects/new?tc=${tc.id}&run=${tc.last_run || ""}`}
                  className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                >
                  Defect aç
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: any }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-gray-500">{label}</div>
      <div className="font-mono">{value || "—"}</div>
    </div>
  );
}
