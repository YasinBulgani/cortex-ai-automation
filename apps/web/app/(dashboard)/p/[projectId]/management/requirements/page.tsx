"use client";

import { useState } from "react";
import {
  useRequirementTraceability,
  useRequirementCatalog,
  useCreateRequirementCatalogItem,
  useManagementRequirements,
  useCreateManagementRequirement,
  useManagementCases,
  type Requirement,
  type TraceabilityRow,
} from "@/lib/hooks/use-management";
import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

// ── Constants ─────────────────────────────────────────────────────────────────

const RUN_STATUS_STYLES: Record<string, string> = {
  passed:   "bg-emerald-500/15 text-emerald-400",
  failed:   "bg-rose-500/15 text-rose-400",
  blocked:  "bg-amber-500/15 text-amber-400",
  not_run:  "bg-slate-700 text-slate-400",
  skipped:  "bg-slate-600 text-slate-400",
};

const COVERAGE_STYLES: Record<string, string> = {
  covered:     "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400",
  partial:     "bg-amber-500/10 border border-amber-500/20 text-amber-400",
  not_covered: "bg-rose-500/10 border border-rose-500/20 text-rose-400",
};

// ── Traceability matrix row ───────────────────────────────────────────────────

function MatrixRow({ row }: { row: TraceabilityRow }) {
  const [expanded, setExpanded] = useState(false);

  const overallCoverage = row.covered
    ? row.cases.every((c) => c.coverage_status === "covered")
      ? "covered"
      : "partial"
    : "not_covered";

  return (
    <>
      <tr
        className="cursor-pointer hover:bg-slate-900/60"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-2">
            <svg
              className={`h-3.5 w-3.5 text-slate-500 flex-shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            <span className="font-mono text-xs text-slate-400">{row.requirement_key}</span>
            {row.stale && (
              <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-xs text-amber-400" title="Kaynak güncellendi — test case yenilenmeli">
                stale
              </span>
            )}
          </div>
        </td>
        <td className="max-w-xs px-3 py-2.5 truncate text-sm text-slate-200">{row.title}</td>
        <td className="px-3 py-2.5 text-xs text-slate-500">{row.source}</td>
        <td className="px-3 py-2.5">
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${COVERAGE_STYLES[overallCoverage] ?? ""}`}>
            {overallCoverage.replace("_", " ")}
          </span>
        </td>
        <td className="px-3 py-2.5 text-xs text-slate-400">{row.cases.length}</td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={5} className="bg-slate-950/60 px-6 pb-4 pt-2">
            {row.cases.length === 0 ? (
              <p className="text-xs text-slate-500">Bu requirement için bağlı test case yok.</p>
            ) : (
              <div className="space-y-1.5">
                {row.cases.map((c) => (
                  <div
                    key={c.case_id}
                    className="flex items-center gap-3 rounded-lg bg-slate-900 px-3 py-2 text-sm"
                  >
                    {c.case_key && (
                      <span className="w-20 flex-shrink-0 font-mono text-xs text-slate-500">
                        {c.case_key}
                      </span>
                    )}
                    <span className="flex-1 text-slate-200">{c.title}</span>
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        RUN_STATUS_STYLES[c.last_run_status ?? "not_run"] ?? "bg-slate-700 text-slate-400"
                      }`}
                    >
                      {c.last_run_status ?? "not run"}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        COVERAGE_STYLES[c.coverage_status] ?? ""
                      }`}
                    >
                      {c.coverage_status.replace("_", " ")}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

// ── Link form ─────────────────────────────────────────────────────────────────

function LinkRequirementForm({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    requirement_id: "",
    case_id: "",
    external_key: "",
    title_snapshot: "",
    url: "",
    external_source: "internal",
    coverage_status: "covered",
  });
  const mutation = useCreateManagementRequirement(projectId);
  const cases = useManagementCases(projectId);
  const catalog = useRequirementCatalog(projectId);

  const selectRequirement = (requirementId: string) => {
    const requirement = (catalog.data ?? []).find((item) => item.id === requirementId);
    setForm((current) => ({
      ...current,
      requirement_id: requirementId,
      external_source: requirement?.external_source ?? current.external_source,
      external_key: requirement?.external_key ?? current.external_key,
      title_snapshot: requirement?.title ?? current.title_snapshot,
      url: requirement?.url ?? current.url,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await mutation.mutateAsync({
      ...form,
      requirement_id: form.requirement_id || null,
      case_id: form.case_id,
      external_key: form.external_key,
      title_snapshot: form.title_snapshot,
    });
    setForm({ requirement_id: "", case_id: "", external_key: "", title_snapshot: "", url: "", external_source: "internal", coverage_status: "covered" });
    setOpen(false);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500"
      >
        + Requirement Bağla
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border border-slate-800 bg-slate-900 p-4">
      <p className="text-sm font-semibold text-white">Requirement Bağlantısı Ekle</p>
      <select
        value={form.requirement_id}
        onChange={(e) => selectRequirement(e.target.value)}
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
      >
        <option value="">Katalogdan seç veya yeni key gir</option>
        {(catalog.data ?? []).map((requirement) => (
          <option key={requirement.id} value={requirement.id}>
            {requirement.external_key} - {requirement.title}
          </option>
        ))}
      </select>
      <select
        required
        value={form.case_id}
        onChange={(e) => setForm((f) => ({ ...f, case_id: e.target.value }))}
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
      >
        <option value="">Test case seç</option>
        {(cases.data ?? []).map((testCase) => (
          <option key={testCase.id} value={testCase.id}>
            {testCase.case_key} - {testCase.title}
          </option>
        ))}
      </select>
      {[
        ["external_key", "External Key (ör. REQ-001)", "required"],
        ["title_snapshot", "Requirement başlığı", "required"],
        ["url", "URL (opsiyonel)", ""],
        ["external_source", "Kaynak (ör. jira, internal)", ""],
      ].map(([field, placeholder, req]) => (
        <input
          key={field}
          type="text"
          placeholder={placeholder}
          required={!!req}
          value={(form as Record<string, string>)[field] ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
        />
      ))}
      <select
        value={form.coverage_status}
        onChange={(e) => setForm((f) => ({ ...f, coverage_status: e.target.value }))}
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
      >
        <option value="covered">Covered</option>
        <option value="partial">Partial</option>
        <option value="not_covered">Not Covered</option>
      </select>
      <div className="flex gap-3">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
        >
          {mutation.isPending ? "Kaydediliyor…" : "Kaydet"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800"
        >
          İptal
        </button>
      </div>
    </form>
  );
}

function RequirementCatalogForm({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    external_key: "",
    title: "",
    description: "",
    external_source: "internal",
    priority: "medium",
    status: "active",
    url: "",
    tags: "",
  });
  const mutation = useCreateRequirementCatalogItem(projectId);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    await mutation.mutateAsync({
      external_source: form.external_source,
      external_key: form.external_key,
      title: form.title,
      description: form.description || null,
      priority: form.priority,
      status: form.status,
      url: form.url || null,
      tags: form.tags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
    });
    setForm({ external_key: "", title: "", description: "", external_source: "internal", priority: "medium", status: "active", url: "", tags: "" });
    setOpen(false);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800"
      >
        + Requirement Oluştur
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4 md:grid-cols-2">
      <input
        required
        placeholder="REQ-001"
        value={form.external_key}
        onChange={(e) => setForm((value) => ({ ...value, external_key: e.target.value }))}
        className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
      />
      <input
        required
        placeholder="Requirement başlığı"
        value={form.title}
        onChange={(e) => setForm((value) => ({ ...value, title: e.target.value }))}
        className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
      />
      <textarea
        placeholder="Açıklama / kabul notları"
        value={form.description}
        onChange={(e) => setForm((value) => ({ ...value, description: e.target.value }))}
        className="min-h-24 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none md:col-span-2"
      />
      {[
        ["external_source", "Kaynak"],
        ["priority", "Priority"],
        ["status", "Status"],
        ["url", "URL"],
        ["tags", "Virgülle tag"],
      ].map(([field, placeholder]) => (
        <input
          key={field}
          placeholder={placeholder}
          value={(form as Record<string, string>)[field] ?? ""}
          onChange={(e) => setForm((value) => ({ ...value, [field]: e.target.value }))}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
        />
      ))}
      <div className="flex gap-3 md:col-span-2">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
        >
          {mutation.isPending ? "Kaydediliyor…" : "Kataloğa Ekle"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800"
        >
          İptal
        </button>
      </div>
    </form>
  );
}

function CatalogRow({ requirement }: { requirement: Requirement }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-teal-300">{requirement.external_key}</p>
          <p className="mt-1 text-sm font-semibold text-white">{requirement.title}</p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="rounded-full bg-slate-800 px-2 py-1 text-slate-300">{requirement.priority}</span>
          <span className="rounded-full bg-slate-800 px-2 py-1 text-slate-300">{requirement.status}</span>
        </div>
      </div>
      {requirement.description && (
        <p className="mt-2 line-clamp-2 text-xs text-slate-500">{requirement.description}</p>
      )}
      {requirement.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {requirement.tags.map((tag) => (
            <span key={tag} className="rounded bg-slate-800 px-1.5 py-0.5 text-[11px] text-slate-400">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ManagementRequirementsPage({
  params,
}: {
  params: { projectId: string };
}) {
  const { projectId } = params;
  const matrixQuery = useRequirementTraceability(projectId);
  const catalogQuery = useRequirementCatalog(projectId);
  const linkQuery = useManagementRequirements(projectId);
  const [filterCoverage, setFilterCoverage] = useState<"all" | "covered" | "not_covered" | "stale">("all");
  const [search, setSearch] = useState("");

  const rows = matrixQuery.data ?? [];

  const filtered = rows.filter((r) => {
    if (search && !r.requirement_key.toLowerCase().includes(search.toLowerCase())
        && !r.title.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterCoverage === "covered" && !r.covered) return false;
    if (filterCoverage === "not_covered" && r.covered) return false;
    if (filterCoverage === "stale" && !r.stale) return false;
    return true;
  });

  const totalReqs   = rows.length;
  const coveredReqs = rows.filter((r) => r.covered).length;
  const staleReqs   = rows.filter((r) => r.stale).length;
  const linkedCases = new Set((linkQuery.data ?? []).map((link) => link.case_id)).size;
  const coveragePct = totalReqs > 0 ? ((coveredReqs / totalReqs) * 100).toFixed(1) : "—";

  return (
    <ManagementShell
      projectId={projectId}
      title="Requirement Coverage"
      description="Requirement → test case → run result zincirini canlı traceability matrisi olarak takip edin."
      active="management/requirements"
    >
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat
          label="Requirements"
          value={matrixQuery.isLoading ? "…" : String(totalReqs)}
          note={`${catalogQuery.data?.length ?? 0} catalog item`}
        />
        <ManagementStat
          label="Covered"
          value={matrixQuery.isLoading ? "…" : `${coveragePct}%`}
          note={`${coveredReqs} / ${totalReqs} requirement`}
        />
        <ManagementStat
          label="Stale"
          value={matrixQuery.isLoading ? "…" : String(staleReqs)}
          note="source updated after last run"
        />
        <ManagementStat
          label="Linked Cases"
          value={linkQuery.isLoading ? "…" : String(linkedCases)}
          note={`${linkQuery.data?.length ?? 0} trace links`}
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <ManagementPanel title="Requirement Catalog">
          <div className="mb-4 flex flex-wrap gap-3">
            <RequirementCatalogForm projectId={projectId} />
            <LinkRequirementForm projectId={projectId} />
          </div>
          {catalogQuery.isLoading ? (
            <div className="flex h-20 items-center justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
            </div>
          ) : (catalogQuery.data ?? []).length === 0 ? (
            <p className="py-4 text-sm text-slate-500">
              Katalog boş. Requirement oluşturduğunuzda coverage matrisi artık test case bağlantısı olmadan da uncovered scope gösterecek.
            </p>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {(catalogQuery.data ?? []).slice(0, 6).map((requirement) => (
                <CatalogRow key={requirement.id} requirement={requirement} />
              ))}
            </div>
          )}
        </ManagementPanel>

        <ManagementPanel title="Coverage Rules">
          <div className="space-y-3 text-sm text-slate-400">
            <p>Requirement katalogda durur; test case bağlantısı ayrı izlenir.</p>
            <p>Bağlantısız katalog kaydı release raporunda uncovered requirement olarak görünür.</p>
            <p>Kaynak güncellenirse son koşum tarihi eski kalan case satırı stale işaretlenir.</p>
          </div>
        </ManagementPanel>
      </div>

      {/* Matrix */}
      <div className="mt-4">
        <ManagementPanel title="Traceability Matrix">
          {/* Filter row */}
          <div className="mb-4 flex flex-wrap gap-3">
            <input
              type="text"
              placeholder="Requirement ara…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 min-w-40 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
            />
            {(["all", "covered", "not_covered", "stale"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilterCoverage(f)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  filterCoverage === f
                    ? "bg-teal-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
              >
                {f === "all" ? "Tümü" : f === "not_covered" ? "Kapsanmamış" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>

          {/* Table */}
          {matrixQuery.isLoading ? (
            <div className="flex h-24 items-center justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">
              {rows.length === 0 ? "Henüz requirement bağlantısı yok." : "Filtreyle eşleşen requirement bulunamadı."}
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-800">
              <table className="w-full text-sm">
                <thead className="bg-slate-950 text-xs text-slate-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Key</th>
                    <th className="px-3 py-2 text-left">Başlık</th>
                    <th className="px-3 py-2 text-left">Kaynak</th>
                    <th className="px-3 py-2 text-left">Coverage</th>
                    <th className="px-3 py-2 text-left">Cases</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filtered.map((row) => (
                    <MatrixRow key={row.requirement_key} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ManagementPanel>
      </div>
    </ManagementShell>
  );
}
