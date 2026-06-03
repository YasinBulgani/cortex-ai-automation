"use client";

import { useState, useMemo } from "react";
import {
  useRequirementTraceability,
  useRequirementCatalog,
  type RequirementTraceabilityRow,
  type Requirement,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const LAST_RUN_DOT: Record<string, string> = {
  passed:  "bg-emerald-500",
  failed:  "bg-red-500",
  blocked: "bg-amber-500",
  skipped: "bg-slate-500",
  not_run: "bg-slate-600",
};

type ViewTab = "traceability" | "catalog";

const PAGE_SIZE = 20;

function CoverageBar({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-20 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className={`h-full rounded-full ${pct >= 80 ? "bg-emerald-500" : pct >= 40 ? "bg-blue-500" : "bg-red-500"}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-[11px] text-slate-500">{pct.toFixed(0)}%</span>
    </div>
  );
}

function TraceRow({ row }: { row: RequirementTraceabilityRow }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr
        className="border-b border-white/[0.04] hover:bg-white/[0.04] cursor-pointer transition-colors"
        onClick={() => setOpen(v => !v)}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-slate-600">{open ? "▼" : "▶"}</span>
            <span className="text-[11px] font-mono text-slate-400">{row.external_key}</span>
          </div>
        </td>
        <td className="px-4 py-3">
          <span className="text-[13px] text-slate-200">{row.title}</span>
        </td>
        <td className="px-4 py-3">
          <span className="text-[11px] text-slate-400">{row.status}</span>
        </td>
        <td className="px-4 py-3">
          <CoverageBar pct={row.coverage_pct} />
        </td>
        <td className="px-4 py-3">
          <span className="text-[11px] text-slate-400">{row.cases.length}</span>
        </td>
      </tr>
      {open && row.cases.length > 0 && (
        <tr className="border-b border-white/[0.04]">
          <td colSpan={5} className="px-8 py-3 bg-white/[0.02]">
            <div className="space-y-1.5">
              {row.cases.map(c => {
                const dot = LAST_RUN_DOT[c.last_run_status ?? "not_run"] ?? "bg-slate-600";
                return (
                  <div key={c.case_id} className="flex items-center gap-3">
                    <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dot}`} />
                    <span className="text-[11px] font-mono text-slate-500 w-20 shrink-0">{c.case_key}</span>
                    <span className="text-[11px] text-slate-300 flex-1 truncate">{c.title}</span>
                    <span className="text-[10px] text-slate-500">{c.last_run_status ?? "not_run"}</span>
                  </div>
                );
              })}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function ManagementRequirementsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: traceRows, isLoading: traceLoading, isError: traceError, refetch: traceRefetch } = useRequirementTraceability(mpid || undefined);
  const { data: catalog, isLoading: catalogLoading, isError: catalogError, refetch: catalogRefetch } = useRequirementCatalog(mpid || undefined);

  const [activeTab, setActiveTab] = useState<ViewTab>("traceability");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [tracePage, setTracePage] = useState(0);
  const [catalogPage, setCatalogPage] = useState(0);

  const rows     = traceRows ?? [];
  const covered  = rows.filter(r => r.covered).length;
  const total    = rows.length;
  const coverPct = total > 0 ? Math.round((covered / total) * 100) : 0;

  const filteredRows = useMemo(() => {
    return rows.filter(r => {
      const q = search.toLowerCase();
      const matchSearch = !search || (
        r.title?.toLowerCase().includes(q) ||
        r.status?.toLowerCase().includes(q) ||
        r.external_key?.toLowerCase().includes(q)
      );
      const matchStatus = statusFilter === "all" || r.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [rows, search, statusFilter]);

  const tracePageCount = Math.ceil(filteredRows.length / PAGE_SIZE);
  const pagedTraceRows = filteredRows.slice(tracePage * PAGE_SIZE, (tracePage + 1) * PAGE_SIZE);

  const filteredCatalog = useMemo(() => {
    return (catalog ?? []).filter((r: Requirement) => {
      const q = search.toLowerCase();
      const matchSearch = !search || (
        r.title?.toLowerCase().includes(q) ||
        r.description?.toLowerCase().includes(q) ||
        r.status?.toLowerCase().includes(q) ||
        r.external_key?.toLowerCase().includes(q)
      );
      const matchStatus = statusFilter === "all" || r.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [catalog, search, statusFilter]);

  const catalogPageCount = Math.ceil(filteredCatalog.length / PAGE_SIZE);
  const pagedCatalog = filteredCatalog.slice(catalogPage * PAGE_SIZE, (catalogPage + 1) * PAGE_SIZE);

  return (
    <div className="min-h-[calc(100vh-88px)] bg-[#0a0f1e] text-slate-200">
      {/* Header */}
      <div className="border-b border-white/[0.06] bg-[#0d1221] px-6 py-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-[13px] font-semibold text-slate-200">Gereksinim Kapsamı</h1>
            <span className="rounded-full border border-white/[0.08] px-2 py-0.5 text-[10px] text-slate-400">
              {coverPct}% kapsandı
            </span>
          </div>
          {/* View tabs */}
          <div className="flex items-center gap-1 rounded-md border border-white/[0.06] p-0.5">
            {(["traceability", "catalog"] as const).map(tab => (
              <button
                key={tab}
                onClick={() => { setActiveTab(tab); setTracePage(0); setCatalogPage(0); }}
                className={[
                  "rounded px-3 py-1.5 text-[11px] font-medium transition-colors",
                  activeTab === tab ? "bg-white/[0.08] text-slate-200" : "text-slate-500 hover:text-slate-300",
                ].join(" ")}
              >
                {tab === "traceability" ? "Traceability Matrix" : "Gereksinim Kataloğu"}
              </button>
            ))}
          </div>
        </div>
        {/* Search + Status filter bar */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={search}
            onChange={e => { setSearch(e.target.value); setTracePage(0); setCatalogPage(0); }}
            placeholder="Ara: başlık, açıklama, durum, anahtar..."
            className="flex-1 rounded border border-white/[0.08] bg-[#0a0f1e] px-3 py-1.5 text-[12px] text-slate-300 placeholder-slate-600 outline-none focus:border-blue-500/50"
          />
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setTracePage(0); setCatalogPage(0); }}
            className="rounded border border-white/[0.08] bg-[#0d1221] px-2 py-1.5 text-[12px] text-slate-400 outline-none focus:border-blue-500/50"
          >
            <option value="all">Tüm Durumlar</option>
            <option value="draft">Taslak</option>
            <option value="approved">Onaylandı</option>
            <option value="rejected">Reddedildi</option>
          </select>
        </div>
      </div>

      {/* Traceability view */}
      {activeTab === "traceability" && (
        traceLoading ? (
          <div className="space-y-3 p-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 rounded-lg border border-white/[0.06] p-4">
                <div className="h-4 w-4 animate-pulse rounded bg-white/[0.08]" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-3/4 animate-pulse rounded bg-white/[0.08]" />
                  <div className="h-2 w-1/2 animate-pulse rounded bg-white/[0.05]" />
                </div>
                <div className="h-5 w-16 animate-pulse rounded-full bg-white/[0.06]" />
              </div>
            ))}
          </div>
        ) : traceError ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <p className="text-sm text-red-400">Gereksinimler yüklenemedi</p>
            <button onClick={() => traceRefetch()} className="text-xs text-slate-500 hover:text-slate-300">
              Tekrar Dene
            </button>
          </div>
        ) : filteredRows.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <div className="rounded-full bg-white/[0.04] p-4">
              <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            {(search || statusFilter !== "all") ? (
              <>
                <p className="text-sm text-slate-400">Arama kriterlerine uyan gereksinim bulunamadı</p>
                <button
                  onClick={() => { setSearch(""); setStatusFilter("all"); setTracePage(0); setCatalogPage(0); }}
                  className="text-xs text-slate-600 hover:text-slate-400"
                >
                  Filtreleri Temizle
                </button>
              </>
            ) : (
              <>
                <p className="text-sm font-medium text-slate-300">Henüz gereksinim bağlantısı yok</p>
                <p className="text-xs text-slate-500 max-w-xs">Test case&apos;lerinizi gereksinimlerle ilişkilendirdiğinizde kapsam matrisi burada görünecek.</p>
              </>
            )}
          </div>
        ) : (
          <>
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-white/[0.06] bg-[#0d1221]">
                  {["Req. Key", "Başlık", "Durum", "Kapsam", "Case Sayısı"].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider text-slate-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pagedTraceRows.map(row => <TraceRow key={row.requirement_id} row={row} />)}
              </tbody>
            </table>
            {tracePageCount > 1 && (
              <div className="flex items-center justify-between border-t border-white/[0.06] bg-[#0d1221] px-6 py-3">
                <span className="text-[11px] text-slate-500">
                  {filteredRows.length} sonuç — Sayfa {tracePage + 1} / {tracePageCount}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setTracePage(p => Math.max(0, p - 1))}
                    disabled={tracePage === 0}
                    className="rounded px-2.5 py-1 text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-30"
                  >
                    ← Önceki
                  </button>
                  <button
                    onClick={() => setTracePage(p => Math.min(tracePageCount - 1, p + 1))}
                    disabled={tracePage >= tracePageCount - 1}
                    className="rounded px-2.5 py-1 text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-30"
                  >
                    Sonraki →
                  </button>
                </div>
              </div>
            )}
          </>
        )
      )}

      {/* Catalog view */}
      {activeTab === "catalog" && (
        catalogLoading ? (
          <div className="space-y-3 p-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 rounded-lg border border-white/[0.06] p-4">
                <div className="h-4 w-4 animate-pulse rounded bg-white/[0.08]" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-3/4 animate-pulse rounded bg-white/[0.08]" />
                  <div className="h-2 w-1/2 animate-pulse rounded bg-white/[0.05]" />
                </div>
                <div className="h-5 w-16 animate-pulse rounded-full bg-white/[0.06]" />
              </div>
            ))}
          </div>
        ) : catalogError ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <p className="text-sm text-red-400">Gereksinimler yüklenemedi</p>
            <button onClick={() => catalogRefetch()} className="text-xs text-slate-500 hover:text-slate-300">
              Tekrar Dene
            </button>
          </div>
        ) : filteredCatalog.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <div className="rounded-full bg-white/[0.04] p-4">
              <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            {(search || statusFilter !== "all") ? (
              <>
                <p className="text-sm text-slate-400">Arama kriterlerine uyan gereksinim bulunamadı</p>
                <button
                  onClick={() => { setSearch(""); setStatusFilter("all"); setTracePage(0); setCatalogPage(0); }}
                  className="text-xs text-slate-600 hover:text-slate-400"
                >
                  Filtreleri Temizle
                </button>
              </>
            ) : (
              <>
                <p className="text-sm font-medium text-slate-300">Gereksinim kataloğu boş</p>
                <p className="text-xs text-slate-500 max-w-xs">İlk gereksinimi oluşturmak için yukarıdaki butonu kullanın.</p>
              </>
            )}
          </div>
        ) : (
          <>
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-white/[0.06] bg-[#0d1221]">
                  {["External Key", "Başlık", "Öncelik", "Durum", "Etiketler"].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider text-slate-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pagedCatalog.map((req: Requirement) => (
                  <tr key={req.id} className="border-b border-white/[0.04] hover:bg-white/[0.04] transition-colors">
                    <td className="px-4 py-3">
                      <span className="text-[11px] font-mono text-slate-400">{req.external_key}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[13px] text-slate-200">{req.title}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] text-slate-400">{req.priority}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] text-slate-400">{req.status}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {req.tags.slice(0, 3).map(tag => (
                          <span key={tag} className="rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-slate-500">{tag}</span>
                        ))}
                        {req.tags.length > 3 && (
                          <span className="text-[10px] text-slate-600">+{req.tags.length - 3}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {catalogPageCount > 1 && (
              <div className="flex items-center justify-between border-t border-white/[0.06] bg-[#0d1221] px-6 py-3">
                <span className="text-[11px] text-slate-500">
                  {filteredCatalog.length} sonuç — Sayfa {catalogPage + 1} / {catalogPageCount}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setCatalogPage(p => Math.max(0, p - 1))}
                    disabled={catalogPage === 0}
                    className="rounded px-2.5 py-1 text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-30"
                  >
                    ← Önceki
                  </button>
                  <button
                    onClick={() => setCatalogPage(p => Math.min(catalogPageCount - 1, p + 1))}
                    disabled={catalogPage >= catalogPageCount - 1}
                    className="rounded px-2.5 py-1 text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-30"
                  >
                    Sonraki →
                  </button>
                </div>
              </div>
            )}
          </>
        )
      )}
    </div>
  );
}
