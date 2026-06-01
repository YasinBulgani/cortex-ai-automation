"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";

const PER_PAGE = 50;

type AuditEvent = {
  id: string;
  ts: string;
  actor_email: string | null;
  actor_name: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  ip: string | null;
  seq: number | null;
};

const ACTION_BADGE: Record<string, string> = {
  create: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
  update: "border-blue-500/20 bg-blue-500/10 text-blue-400",
  delete: "border-red-500/20 bg-red-500/10 text-red-400",
  login: "border-violet-500/20 bg-violet-500/10 text-violet-400",
  logout: "border-slate-600 bg-slate-800/50 text-slate-400",
  mfa: "border-amber-500/20 bg-amber-500/10 text-amber-400",
  security: "border-orange-500/20 bg-orange-500/10 text-orange-400",
};

function badgeClass(action: string): string {
  const prefix = action.split(".")[0];
  return ACTION_BADGE[prefix] ?? ACTION_BADGE[action] ?? "border-slate-700 bg-slate-800 text-slate-300";
}

// ── Export helper ─────────────────────────────────────────────────────────────

async function triggerExport(
  format: "json" | "csv",
  params: Record<string, string>,
) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v),
  ).toString();
  const url = `/api/v1/audit/export/${format}${qs ? `?${qs}` : ""}`;
  // Use fetch with credentials; trigger download via blob
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(msg);
  }
  const blob = await res.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  const today = new Date().toISOString().slice(0, 10);
  link.download = `cortex_audit_${today}.${format}`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AuditLogPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Filter state
  const [filterAction, setFilterAction] = useState("");
  const [filterResource, setFilterResource] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  function buildParams() {
    const p: Record<string, string> = {};
    if (filterAction) p.action = filterAction;
    if (filterResource) p.resource_type = filterResource;
    if (dateFrom) p.date_from = new Date(dateFrom).toISOString();
    if (dateTo) p.date_to = new Date(dateTo + "T23:59:59").toISOString();
    return p;
  }

  useEffect(() => {
    setLoading(true);
    const p = buildParams();
    const qs = new URLSearchParams({
      page: String(page),
      per_page: String(PER_PAGE),
      ...p,
    }).toString();
    apiFetch<AuditEvent[]>(`/api/v1/audit/events?${qs}`)
      .then((data) => {
        setEvents(data);
        setHasMore(data.length === PER_PAGE);
      })
      .catch((err) => console.warn("[audit]:", err))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filterAction, filterResource, dateFrom, dateTo]);

  async function handleExport(format: "json" | "csv") {
    setExporting(true);
    setExportError(null);
    try {
      await triggerExport(format, buildParams());
    } catch (e: unknown) {
      setExportError(e instanceof Error ? e.message : String(e));
    } finally {
      setExporting(false);
    }
  }

  function handleFilterApply() {
    setPage(1);
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="audit-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        }
        title="Denetim Günlüğü"
        description="Platform üzerindeki tüm işlemler — SOC 2 / DPA kanıt dışa aktarımı"
        data-testid="audit-heading"
      />

      {/* ── Filter + Export Bar ── */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">İşlem filtresi</label>
          <input
            type="text"
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            placeholder="ör: user.login"
            className="h-8 rounded-lg border border-slate-700 bg-slate-800 px-3 text-xs text-slate-200 placeholder:text-slate-600 focus:border-violet-500 focus:outline-none w-36"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Kaynak türü</label>
          <input
            type="text"
            value={filterResource}
            onChange={(e) => setFilterResource(e.target.value)}
            placeholder="ör: user"
            className="h-8 rounded-lg border border-slate-700 bg-slate-800 px-3 text-xs text-slate-200 placeholder:text-slate-600 focus:border-violet-500 focus:outline-none w-28"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Başlangıç tarihi</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-8 rounded-lg border border-slate-700 bg-slate-800 px-3 text-xs text-slate-200 focus:border-violet-500 focus:outline-none"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Bitiş tarihi</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-8 rounded-lg border border-slate-700 bg-slate-800 px-3 text-xs text-slate-200 focus:border-violet-500 focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={handleFilterApply}
          className="h-8 rounded-lg bg-violet-600 px-4 text-xs font-medium text-white hover:bg-violet-500 transition-colors"
        >
          Filtrele
        </button>

        <div className="ml-auto flex gap-2">
          <button
            type="button"
            disabled={exporting}
            onClick={() => handleExport("json")}
            title="JSON olarak dışa aktar (SOC 2 kanıtı)"
            className="flex items-center gap-1.5 h-8 rounded-lg border border-slate-700 px-3 text-xs text-slate-300 hover:border-violet-500 hover:text-white transition-colors disabled:opacity-40"
            data-testid="export-json-btn"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {exporting ? "…" : "JSON"}
          </button>
          <button
            type="button"
            disabled={exporting}
            onClick={() => handleExport("csv")}
            title="CSV olarak dışa aktar (SOC 2 kanıtı)"
            className="flex items-center gap-1.5 h-8 rounded-lg border border-slate-700 px-3 text-xs text-slate-300 hover:border-violet-500 hover:text-white transition-colors disabled:opacity-40"
            data-testid="export-csv-btn"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {exporting ? "…" : "CSV"}
          </button>
        </div>
      </div>

      {exportError && (
        <p className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-xs text-red-400">
          Dışa aktarma hatası: {exportError}
        </p>
      )}

      {/* ── Table ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <span className="text-xs text-slate-500">Sayfa {page} · {events.length} kayıt</span>
          {loading && <span className="text-xs text-slate-500 animate-pulse">Yükleniyor…</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-sm" data-testid="audit-table">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs text-slate-500">
                <th className="px-5 py-3 font-medium">Sıra #</th>
                <th className="px-5 py-3 font-medium">Zaman</th>
                <th className="px-5 py-3 font-medium">Kullanıcı</th>
                <th className="px-5 py-3 font-medium">İşlem</th>
                <th className="px-5 py-3 font-medium">Kaynak</th>
                <th className="px-5 py-3 font-medium">IP</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr
                  key={e.id}
                  className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 transition-colors"
                  data-testid={`audit-row-${e.id}`}
                >
                  <td className="px-5 py-3 font-mono text-xs text-slate-600">
                    {e.seq ?? "—"}
                  </td>
                  <td className="px-5 py-3 text-slate-400 whitespace-nowrap font-mono text-xs">
                    {new Date(e.ts).toLocaleString("tr-TR")}
                  </td>
                  <td className="px-5 py-3 text-white">
                    {e.actor_name || e.actor_email || (
                      <span className="text-slate-500">Sistem</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${badgeClass(e.action)}`}>
                      {e.action}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-400">
                    {e.resource_type}
                    {e.resource_id ? (
                      <span className="ml-1 font-mono text-xs text-slate-600">
                        {e.resource_id.slice(0, 8)}&hellip;
                      </span>
                    ) : null}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-600">
                    {e.ip ?? "—"}
                  </td>
                </tr>
              ))}
              {!loading && events.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-sm text-slate-500">
                    Kayıt bulunamadı
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Pagination ── */}
      <div className="flex items-center justify-center gap-3">
        <button
          type="button"
          disabled={page <= 1 || loading}
          onClick={() => setPage(page - 1)}
          className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition-colors disabled:opacity-40"
          data-testid="audit-btn-prev"
        >
          ‹ Önceki
        </button>
        <span className="text-xs text-slate-500">Sayfa {page}</span>
        <button
          type="button"
          disabled={!hasMore || loading}
          onClick={() => setPage(page + 1)}
          className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition-colors disabled:opacity-40"
          data-testid="audit-btn-next"
        >
          Sonraki ›
        </button>
      </div>

      {/* ── SOC 2 Info Box ── */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/20 p-4 text-xs text-slate-500">
        <p className="font-medium text-slate-400 mb-1">SOC 2 / KVKK Kanıt Dışa Aktarımı</p>
        <p>
          JSON ve CSV dışa aktarımları tamper-evident hash zinciri alanlarını (<code className="text-slate-400">seq</code>,{" "}
          <code className="text-slate-400">prev_hash</code>, <code className="text-slate-400">hash</code>) içerir.
          Denetçilere teslim öncesinde tarih aralığı filtrelerini kullanın.
          Daha fazla bilgi için <code className="text-slate-400">docs/compliance/SOC2-controls-mapping.md</code> dosyasına bakın.
        </p>
      </div>
    </div>
  );
}
