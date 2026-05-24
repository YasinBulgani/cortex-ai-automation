"use client";

import { useState } from "react";
import {
  useManagementRepository,
  useSearchSimilarCases,
  type SimilarCaseResult,
} from "@/lib/hooks/use-management";
import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

// ── Semantic search panel ─────────────────────────────────────────────────────

function SemanticSearchPanel({ projectId }: { projectId: string }) {
  const [query, setQuery] = useState("");
  const searchMutation = useSearchSimilarCases(projectId);

  const handleSearch = () => {
    if (!query.trim()) return;
    searchMutation.mutate({ query: query.trim(), k: 8, min_score: 0.25 });
  };

  const results: SimilarCaseResult[] = searchMutation.data ?? [];

  const STATUS_STYLES: Record<string, string> = {
    passed: "bg-emerald-500/15 text-emerald-400",
    failed: "bg-rose-500/15 text-rose-400",
    blocked: "bg-amber-500/15 text-amber-400",
    not_run: "bg-slate-700 text-slate-400",
    skipped: "bg-slate-600 text-slate-400",
  };

  return (
    <ManagementPanel title="Semantik Senaryo Arama">
      <div className="space-y-3">
        <p className="text-xs text-slate-400">
          Doğal dilde bir test senaryosu tanımlayın — AI en benzer senaryoları bulur.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
            placeholder='Örn: "kullanıcı şifresini değiştirir ve doğrulama e-postası alır"'
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <button
            onClick={handleSearch}
            disabled={searchMutation.isPending || !query.trim()}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
          >
            {searchMutation.isPending ? (
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 animate-spin rounded-full border border-white/30 border-t-white" />
                Arıyor…
              </span>
            ) : "Ara"}
          </button>
        </div>

        {searchMutation.isError && (
          <p className="text-xs text-rose-400">
            AI Gateway erişilemiyor — semantik arama kullanılamıyor.
          </p>
        )}

        {searchMutation.isSuccess && results.length === 0 && (
          <p className="py-4 text-center text-sm text-slate-500">
            Eşleşen senaryo bulunamadı. Arama terimini değiştirmeyi deneyin.
          </p>
        )}

        {results.length > 0 && (
          <div className="space-y-2">
            {results.map((r) => (
              <div
                key={r.case_id}
                className="flex items-start justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="flex-shrink-0 font-mono text-xs text-slate-500">
                      {r.case_key}
                    </span>
                    {r.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  <p className="mt-0.5 truncate text-sm text-slate-200">{r.title}</p>
                </div>
                <div className="flex flex-shrink-0 flex-col items-end gap-1">
                  <span className="text-xs font-semibold text-teal-400">
                    {(r.score * 100).toFixed(0)}%
                  </span>
                  {r.last_run_status && (
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        STATUS_STYLES[r.last_run_status] ?? "bg-slate-700 text-slate-400"
                      }`}
                    >
                      {r.last_run_status.replace("_", " ")}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </ManagementPanel>
  );
}

// ── Repository table ──────────────────────────────────────────────────────────

function RepositoryTable({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const cases = repoQuery.data?.cases ?? [];
  const suites = repoQuery.data?.suites ?? [];

  if (repoQuery.isLoading) {
    return (
      <div className="flex h-24 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
      </div>
    );
  }

  const STATUS_CHIP: Record<string, string> = {
    active: "bg-emerald-500/15 text-emerald-400",
    draft: "bg-slate-700 text-slate-400",
    archived: "bg-slate-800 text-slate-500",
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-950 text-xs text-slate-500">
          <tr>
            <th className="px-3 py-2 text-left">Key</th>
            <th className="px-3 py-2 text-left">Başlık</th>
            <th className="px-3 py-2 text-left">Tür</th>
            <th className="px-3 py-2 text-left">Durum</th>
            <th className="px-3 py-2 text-left">Son Koşu</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {cases.slice(0, 50).map((c) => (
            <tr key={c.id} className="hover:bg-slate-900/40">
              <td className="px-3 py-2.5 font-mono text-xs text-slate-400">{c.case_key}</td>
              <td className="max-w-xs px-3 py-2.5 truncate text-slate-200">{c.title}</td>
              <td className="px-3 py-2.5 text-xs text-slate-400">{c.type}</td>
              <td className="px-3 py-2.5">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${STATUS_CHIP[c.status] ?? "bg-slate-700 text-slate-400"}`}
                >
                  {c.status}
                </span>
              </td>
              <td className="px-3 py-2.5 text-xs text-slate-400">
                {c.last_run_status ?? "—"}
              </td>
            </tr>
          ))}
          {cases.length === 0 && (
            <tr>
              <td colSpan={5} className="py-8 text-center text-sm text-slate-500">
                Henüz test senaryosu yok.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ManagementRepositoryPage({
  params,
}: {
  params: { projectId: string };
}) {
  const { projectId } = params;
  const repoQuery = useManagementRepository(projectId);

  const totalCases = repoQuery.data?.cases.length ?? 0;
  const totalSuites = repoQuery.data?.suites.length ?? 0;
  const activeCases = repoQuery.data?.cases.filter((c) => c.status === "active").length ?? 0;

  return (
    <ManagementShell
      projectId={projectId}
      title="Test Repository"
      description="Suite, folder, manuel test case, step ve version kayıtlarının yönetildiği kalıcı test hafızası."
      active="management/repository"
    >
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat
          label="Suites"
          value={repoQuery.isLoading ? "…" : String(totalSuites)}
          note="test paketleri"
        />
        <ManagementStat
          label="Test Senaryosu"
          value={repoQuery.isLoading ? "…" : String(totalCases)}
          note={`${activeCases} aktif`}
        />
        <ManagementStat
          label="Toplam Adım"
          value={repoQuery.isLoading ? "…" : String(
            repoQuery.data?.cases.reduce((sum, c) => sum + (c.steps?.length ?? 0), 0) ?? 0,
          )}
          note="tüm senaryolarda"
        />
      </div>

      {/* Semantic search */}
      <div className="mt-6">
        <SemanticSearchPanel projectId={projectId} />
      </div>

      {/* Repository table */}
      <div className="mt-4">
        <ManagementPanel title="Test Senaryoları">
          <RepositoryTable projectId={projectId} />
        </ManagementPanel>
      </div>
    </ManagementShell>
  );
}
