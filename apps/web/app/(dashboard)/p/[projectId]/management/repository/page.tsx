"use client";

import { useMemo, useState } from "react";
import {
  useCreateManagementFolder,
  useCreateManagementSuite,
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
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [lastRunFilter, setLastRunFilter] = useState("all");
  const [sortBy, setSortBy] = useState("updated");

  const types = useMemo(() => Array.from(new Set(cases.map((item) => item.type))).sort(), [cases]);
  const filteredCases = useMemo(() => {
    const search = query.trim().toLowerCase();
    const rows = cases.filter((item) => {
      const matchesSearch = !search
        || item.case_key.toLowerCase().includes(search)
        || item.title.toLowerCase().includes(search)
        || item.tags.some((tag) => tag.toLowerCase().includes(search));
      const matchesStatus = statusFilter === "all" || item.status === statusFilter;
      const matchesType = typeFilter === "all" || item.type === typeFilter;
      const matchesLastRun = lastRunFilter === "all"
        || (lastRunFilter === "never" ? !item.last_run_status : item.last_run_status === lastRunFilter);
      return matchesSearch && matchesStatus && matchesType && matchesLastRun;
    });
    return [...rows].sort((left, right) => {
      if (sortBy === "priority") return String(left.priority).localeCompare(String(right.priority));
      if (sortBy === "last_run") return String(right.last_run_at ?? "").localeCompare(String(left.last_run_at ?? ""));
      if (sortBy === "key") return left.case_key.localeCompare(right.case_key);
      return String(right.updated_at ?? "").localeCompare(String(left.updated_at ?? ""));
    });
  }, [cases, lastRunFilter, query, sortBy, statusFilter, typeFilter]);

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
    <div className="space-y-3">
      <div className="grid gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3 lg:grid-cols-[1.4fr_0.8fr_0.8fr_0.8fr_0.8fr]">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Key, başlık veya tag ara"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
        />
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
          <option value="all">Tüm durumlar</option>
          <option value="active">Active</option>
          <option value="draft">Draft</option>
          <option value="review">Review</option>
          <option value="deprecated">Deprecated</option>
        </select>
        <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
          <option value="all">Tüm türler</option>
          {types.map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
        <select value={lastRunFilter} onChange={(event) => setLastRunFilter(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
          <option value="all">Son koşu: tümü</option>
          <option value="never">Hiç koşulmadı</option>
          <option value="passed">Passed</option>
          <option value="failed">Failed</option>
          <option value="blocked">Blocked</option>
        </select>
        <select value={sortBy} onChange={(event) => setSortBy(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
          <option value="updated">Sırala: güncel</option>
          <option value="priority">Sırala: priority</option>
          <option value="last_run">Sırala: son koşu</option>
          <option value="key">Sırala: key</option>
        </select>
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded-full bg-slate-800 px-2 py-1">{filteredCases.length}/{cases.length} case gösteriliyor</span>
        <span className="rounded-full bg-rose-500/10 px-2 py-1 text-rose-200">{filteredCases.filter((item) => item.last_run_status === "failed").length} failed</span>
        <span className="rounded-full bg-amber-500/10 px-2 py-1 text-amber-200">{filteredCases.filter((item) => item.last_run_status === "blocked").length} blocked</span>
        <span className="rounded-full bg-slate-800 px-2 py-1">{filteredCases.filter((item) => !item.last_run_status).length} never run</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-950 text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left">Key</th>
              <th className="px-3 py-2 text-left">Başlık</th>
              <th className="px-3 py-2 text-left">Tür</th>
              <th className="px-3 py-2 text-left">Priority</th>
              <th className="px-3 py-2 text-left">Durum</th>
              <th className="px-3 py-2 text-left">Son Koşu</th>
              <th className="px-3 py-2 text-left">Tags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {filteredCases.slice(0, 100).map((c) => (
              <tr key={c.id} className="hover:bg-slate-900/40">
                <td className="px-3 py-2.5 font-mono text-xs text-slate-400">{c.case_key}</td>
                <td className="max-w-sm px-3 py-2.5 truncate text-slate-200">
                  <a href={`/p/${projectId}/management/cases/${c.id}`} className="hover:text-teal-300">
                    {c.title}
                  </a>
                </td>
                <td className="px-3 py-2.5 text-xs text-slate-400">{c.type}</td>
                <td className="px-3 py-2.5 text-xs text-slate-400">{c.priority}</td>
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
                <td className="px-3 py-2.5">
                  <div className="flex max-w-xs flex-wrap gap-1">
                    {c.tags.slice(0, 3).map((tag) => <span key={tag} className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">{tag}</span>)}
                  </div>
                </td>
              </tr>
            ))}
            {filteredCases.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-sm text-slate-500">
                  Filtreye uyan test senaryosu yok.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RepositoryStructurePanel({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const createSuite = useCreateManagementSuite(projectId);
  const createFolder = useCreateManagementFolder(projectId);
  const [suiteName, setSuiteName] = useState("");
  const [suiteDescription, setSuiteDescription] = useState("");
  const [folderName, setFolderName] = useState("");
  const [folderSuiteId, setFolderSuiteId] = useState("");
  const suites = repoQuery.data?.suites ?? [];
  const folders = repoQuery.data?.folders ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ManagementPanel title="Suite Oluştur">
        <form
          className="space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            if (!suiteName.trim()) return;
            await createSuite.mutateAsync({
              name: suiteName.trim(),
              description: suiteDescription.trim(),
            });
            setSuiteName("");
            setSuiteDescription("");
          }}
        >
          <input
            value={suiteName}
            onChange={(event) => setSuiteName(event.target.value)}
            placeholder="Suite adı"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <input
            value={suiteDescription}
            onChange={(event) => setSuiteDescription(event.target.value)}
            placeholder="Açıklama"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <button
            disabled={createSuite.isPending || !suiteName.trim()}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
          >
            {createSuite.isPending ? "Oluşturuluyor..." : "Suite Oluştur"}
          </button>
        </form>
      </ManagementPanel>

      <ManagementPanel title="Folder Oluştur">
        <form
          className="space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            const suiteId = folderSuiteId || suites[0]?.id;
            if (!suiteId || !folderName.trim()) return;
            const name = folderName.trim();
            await createFolder.mutateAsync({
              suite_id: suiteId,
              name,
              path: `/${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || name}`,
            });
            setFolderName("");
          }}
        >
          <select
            value={folderSuiteId}
            onChange={(event) => setFolderSuiteId(event.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
          >
            <option value="">Suite seç</option>
            {suites.map((suite) => (
              <option key={suite.id} value={suite.id}>{suite.name}</option>
            ))}
          </select>
          <input
            value={folderName}
            onChange={(event) => setFolderName(event.target.value)}
            placeholder="Folder adı"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <button
            disabled={createFolder.isPending || !folderName.trim() || !(folderSuiteId || suites[0]?.id)}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
          >
            {createFolder.isPending ? "Oluşturuluyor..." : "Folder Oluştur"}
          </button>
        </form>
        <div className="mt-4 space-y-2">
          {folders.slice(0, 6).map((folder) => (
            <div key={folder.id} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300">
              {folder.path}
            </div>
          ))}
        </div>
      </ManagementPanel>
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

      <div className="mt-4">
        <RepositoryStructurePanel projectId={projectId} />
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
