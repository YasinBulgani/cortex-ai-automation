"use client";

import { useState, useMemo } from "react";
import {
  useManagementRequirements,
  useRequirementTraceability,
  useRequirementCatalog,
  useCreateRequirementCatalogItem,
  useCreateManagementRequirement,
  useBulkCreateRequirements,
  useGenerateTestCases,
  type RequirementTraceabilityRow,
  type Requirement,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

// ── Constants ──────────────────────────────────────────────────────────────────

const LAST_RUN_DOT: Record<string, string> = {
  passed: "bg-emerald-500",
  failed: "bg-red-500",
  blocked: "bg-amber-500",
  skipped: "bg-slate-500",
  not_run: "bg-slate-600",
};

const PRIORITY_COLORS: Record<string, string> = {
  P0: "text-red-400 border-red-500/30 bg-red-500/10",
  P1: "text-orange-400 border-orange-500/30 bg-orange-500/10",
  P2: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  P3: "text-slate-400 border-slate-500/30 bg-slate-500/10",
};

const STATUS_COLORS: Record<string, string> = {
  open: "text-blue-400 border-blue-500/30 bg-blue-500/10",
  in_progress: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  done: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  deferred: "text-slate-400 border-slate-500/30 bg-slate-500/10",
  draft: "text-slate-400 border-slate-500/30 bg-slate-500/10",
  approved: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  rejected: "text-red-400 border-red-500/30 bg-red-500/10",
};

const COVERAGE_COLORS: Record<string, string> = {
  covered: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  partially_covered: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  not_covered: "text-slate-400 border-slate-500/30 bg-slate-500/10",
  out_of_scope: "text-purple-400 border-purple-500/30 bg-purple-500/10",
};

const MODULE_OPTIONS = [
  "Kimlik Doğrulama",
  "Ödeme",
  "Kullanıcı Yönetimi",
  "Raporlama",
  "Entegrasyon",
  "Diğer",
];

const EXTERNAL_SOURCES = ["jira", "confluence", "notion", "github", "linear", "manual"];

const PAGE_SIZE = 20;

type ViewTab = "traceability" | "catalog";

// ── Form fields ────────────────────────────────────────────────────────────────

interface NewReqFields {
  external_key: string;
  external_source: string;
  title: string;
  description: string;
  module: string;
  priority: string;
  status: string;
  coverage_status: string;
}

const EMPTY_FIELDS: NewReqFields = {
  external_key: "",
  external_source: "manual",
  title: "",
  description: "",
  module: "",
  priority: "P2",
  status: "open",
  coverage_status: "not_covered",
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function Badge({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium ${colorClass}`}>
      {label}
    </span>
  );
}

function CoverageBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 rounded-full bg-white/[0.06] overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-[11px] text-fg-subtle">{pct.toFixed(0)}%</span>
    </div>
  );
}

function DonutChart({
  covered,
  partial,
  notCovered,
  outOfScope,
}: {
  covered: number;
  partial: number;
  notCovered: number;
  outOfScope: number;
}) {
  const total = covered + partial + notCovered + outOfScope;
  if (total === 0) return null;

  const size = 120;
  const cx = size / 2;
  const cy = size / 2;
  const r = 44;
  const strokeWidth = 18;
  const circumference = 2 * Math.PI * r;

  const segments = [
    { value: covered, color: "#10b981", label: "Kapsandı" },
    { value: partial, color: "#f59e0b", label: "Kısmi" },
    { value: notCovered, color: "#475569", label: "Kapsamdışı" },
    { value: outOfScope, color: "#a855f7", label: "Kapsam Dışı" },
  ];

  let cumulativeAngle = -90;
  const paths = segments.map((seg, i) => {
    if (seg.value === 0) return null;
    const angle = (seg.value / total) * 360;
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + angle;
    cumulativeAngle = endAngle;

    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;

    const x1 = cx + r * Math.cos(startRad);
    const y1 = cy + r * Math.sin(startRad);
    const x2 = cx + r * Math.cos(endRad);
    const y2 = cy + r * Math.sin(endRad);

    const largeArc = angle > 180 ? 1 : 0;
    const d = `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;

    return (
      <path
        key={i}
        d={d}
        fill="none"
        stroke={seg.color}
        strokeWidth={strokeWidth}
        strokeLinecap="butt"
      />
    );
  });

  const pct = total > 0 ? Math.round((covered / total) * 100) : 0;

  return (
    <div className="flex items-center gap-5">
      <div className="relative shrink-0">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={strokeWidth} />
          {paths}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[18px] font-bold text-fg">{pct}%</span>
          <span className="text-[9px] text-fg-subtle">kapsandı</span>
        </div>
      </div>
      <div className="space-y-1.5">
        {segments.map((seg) => (
          seg.value > 0 && (
            <div key={seg.label} className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-sm shrink-0" style={{ backgroundColor: seg.color }} />
              <span className="text-[11px] text-fg-muted">{seg.label}</span>
              <span className="text-[11px] font-medium text-fg ml-auto pl-4">{seg.value}</span>
            </div>
          )
        ))}
        <div className="flex items-center gap-2 border-t border-border pt-1.5 mt-1">
          <span className="text-[10px] text-fg-subtle">Toplam</span>
          <span className="text-[11px] font-medium text-fg ml-auto pl-4">{total}</span>
        </div>
      </div>
    </div>
  );
}

function TraceRow({ row }: { row: RequirementTraceabilityRow }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr
        className="border-b border-border hover:bg-white/[0.04] cursor-pointer transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-fg-subtle">{open ? "▼" : "▶"}</span>
            <span className="text-[11px] font-mono text-fg-muted">{row.external_key}</span>
          </div>
        </td>
        <td className="px-4 py-3">
          <span className="text-[13px] text-fg">{row.title}</span>
        </td>
        <td className="px-4 py-3">
          <Badge
            label={row.status}
            colorClass={STATUS_COLORS[row.status] ?? "text-fg-muted border-border bg-surface-overlay"}
          />
        </td>
        <td className="px-4 py-3">
          <Badge
            label={row.priority || "—"}
            colorClass={PRIORITY_COLORS[row.priority] ?? "text-fg-muted border-border bg-surface-overlay"}
          />
        </td>
        <td className="px-4 py-3">
          <CoverageBar pct={row.coverage_pct} />
        </td>
        <td className="px-4 py-3">
          <span className="text-[11px] text-fg-muted">{row.cases.length}</span>
        </td>
      </tr>
      {open && row.cases.length > 0 && (
        <tr className="border-b border-border">
          <td colSpan={6} className="px-8 py-3 bg-surface-overlay">
            <div className="space-y-2">
              {row.cases.map((c) => {
                const dot = LAST_RUN_DOT[c.last_run_status ?? "not_run"] ?? "bg-slate-600";
                return (
                  <div key={c.case_id} className="flex items-center gap-3">
                    <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dot}`} />
                    <span className="text-[11px] font-mono text-fg-subtle w-24 shrink-0">{c.case_key}</span>
                    <span className="text-[11px] text-fg flex-1 truncate">{c.title}</span>
                    <Badge
                      label={c.coverage_status}
                      colorClass={
                        COVERAGE_COLORS[c.coverage_status] ??
                        "text-fg-muted border-border bg-surface-overlay"
                      }
                    />
                    <span className="text-[10px] text-fg-subtle w-16 text-right">
                      {c.last_run_status ?? "not_run"}
                    </span>
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

function CatalogDetailPanel({
  req,
  onClose,
}: {
  req: Requirement;
  onClose: () => void;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-border px-5 py-4 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-fg-muted">{req.external_key}</span>
          <span className="text-[10px] text-fg-subtle">·</span>
          <span className="text-[11px] text-fg-subtle">{req.external_source}</span>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-fg-subtle hover:bg-white/[0.06] hover:text-fg transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        <h3 className="text-[14px] font-semibold text-fg leading-snug">{req.title}</h3>

        <div className="flex flex-wrap gap-1.5">
          <Badge
            label={req.priority}
            colorClass={PRIORITY_COLORS[req.priority] ?? "text-fg-muted border-border bg-surface-overlay"}
          />
          <Badge
            label={req.status}
            colorClass={STATUS_COLORS[req.status] ?? "text-fg-muted border-border bg-surface-overlay"}
          />
        </div>

        {req.description && (
          <div className="space-y-1">
            <p className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">Açıklama</p>
            <p className="text-[12px] text-fg-muted leading-relaxed">{req.description}</p>
          </div>
        )}

        {req.tags.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">Etiketler</p>
            <div className="flex flex-wrap gap-1">
              {req.tags.map((tag) => (
                <span key={tag} className="rounded bg-white/[0.06] px-2 py-0.5 text-[11px] text-fg-muted">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {req.acceptance_criteria.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
              Kabul Kriterleri
            </p>
            <div className="space-y-1">
              {req.acceptance_criteria.map((ac, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-emerald-500 text-[10px] mt-0.5">✓</span>
                  <span className="text-[12px] text-fg-muted">
                    {typeof ac === "string" ? ac : JSON.stringify(ac)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-1.5 border-t border-border pt-3">
          <p className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">Meta</p>
          <div className="space-y-1 text-[11px]">
            <div className="flex justify-between">
              <span className="text-fg-subtle">Versiyon</span>
              <span className="text-fg-muted">v{req.version_no}</span>
            </div>
            {req.url && (
              <div className="flex justify-between">
                <span className="text-fg-subtle">URL</span>
                <a
                  href={req.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-brand truncate max-w-[160px] hover:underline"
                >
                  {req.url}
                </a>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-fg-subtle">Oluşturuldu</span>
              <span className="text-fg-muted">{new Date(req.created_at).toLocaleDateString("tr-TR")}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-fg-subtle">Güncellendi</span>
              <span className="text-fg-muted">{new Date(req.updated_at).toLocaleDateString("tr-TR")}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3 p-6">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 rounded-lg border border-border p-4">
          <div className="h-4 w-4 animate-pulse rounded bg-white/[0.08]" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-3/4 animate-pulse rounded bg-white/[0.08]" />
            <div className="h-2 w-1/2 animate-pulse rounded bg-white/[0.05]" />
          </div>
          <div className="h-5 w-16 animate-pulse rounded-full bg-white/[0.06]" />
        </div>
      ))}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ManagementRequirementsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const {
    data: traceRows,
    isLoading: traceLoading,
    isError: traceError,
    refetch: traceRefetch,
  } = useRequirementTraceability(mpid || undefined);
  const {
    data: catalog,
    isLoading: catalogLoading,
    isError: catalogError,
    refetch: catalogRefetch,
  } = useRequirementCatalog(mpid || undefined);
  const {
    data: managementReqs,
  } = useManagementRequirements(mpid || undefined);

  const createCatalogItem = useCreateRequirementCatalogItem(mpid || "");
  const createManagementReq = useCreateManagementRequirement(mpid || "");
  const generateCases = useGenerateTestCases(mpid || "");
  const bulkCreateReqs = useBulkCreateRequirements(mpid || "");
  const [csvImportMsg, setCsvImportMsg] = useState<string | null>(null);

  const [genForReq, setGenForReq] = useState<string | null>(null);
  const [genResult, setGenResult] = useState<{ req: Requirement; cases: import("@/lib/hooks/use-management").GeneratedCase[] } | null>(null);

  // ── View state ─────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<ViewTab>("traceability");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [coverageFilter, setCoverageFilter] = useState("all");
  const [tracePage, setTracePage] = useState(0);
  const [catalogPage, setCatalogPage] = useState(0);
  const [selectedReq, setSelectedReq] = useState<Requirement | null>(null);

  // ── Modal state ────────────────────────────────────────────────────────────
  const [showModal, setShowModal] = useState(false);
  const [fields, setFields] = useState<NewReqFields>(EMPTY_FIELDS);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [toastError, setToastError] = useState(false);

  // ── Derived data ───────────────────────────────────────────────────────────
  const rows = traceRows ?? [];
  const catalogItems = catalog ?? [];

  const coveredCount = rows.filter((r) => r.coverage_pct >= 80).length;
  const partialCount = rows.filter((r) => r.coverage_pct > 0 && r.coverage_pct < 80).length;
  const notCoveredCount = rows.filter((r) => r.coverage_pct === 0).length;
  const outOfScopeCount = 0; // traceability doesn't expose this yet; catalog below

  // Catalog-based coverage summary for summary cards
  const catCovered = catalogItems.filter(
    (r: Requirement) => (r as unknown as { coverage_status?: string }).coverage_status === "covered"
  ).length;
  const catPartial = catalogItems.filter(
    (r: Requirement) =>
      (r as unknown as { coverage_status?: string }).coverage_status === "partially_covered"
  ).length;
  const catNotCovered = catalogItems.filter(
    (r: Requirement) =>
      (r as unknown as { coverage_status?: string }).coverage_status === "not_covered" ||
      !(r as unknown as { coverage_status?: string }).coverage_status
  ).length;
  const catOutOfScope = catalogItems.filter(
    (r: Requirement) =>
      (r as unknown as { coverage_status?: string }).coverage_status === "out_of_scope"
  ).length;

  const totalForDonut = catCovered + catPartial + catNotCovered + catOutOfScope;
  const useTraceForDonut = totalForDonut === 0;

  const filteredRows = useMemo(() => {
    return rows.filter((r) => {
      const q = search.toLowerCase();
      const matchSearch =
        !search ||
        r.title?.toLowerCase().includes(q) ||
        r.external_key?.toLowerCase().includes(q);
      const matchStatus = statusFilter === "all" || r.status === statusFilter;
      const matchPriority = priorityFilter === "all" || r.priority === priorityFilter;
      return matchSearch && matchStatus && matchPriority;
    });
  }, [rows, search, statusFilter, priorityFilter]);

  const tracePageCount = Math.ceil(filteredRows.length / PAGE_SIZE);
  const pagedTraceRows = filteredRows.slice(tracePage * PAGE_SIZE, (tracePage + 1) * PAGE_SIZE);

  const filteredCatalog = useMemo(() => {
    return catalogItems.filter((r: Requirement) => {
      const q = search.toLowerCase();
      const matchSearch =
        !search ||
        r.title?.toLowerCase().includes(q) ||
        r.external_key?.toLowerCase().includes(q) ||
        r.description?.toLowerCase().includes(q);
      const matchStatus = statusFilter === "all" || r.status === statusFilter;
      const matchPriority = priorityFilter === "all" || r.priority === priorityFilter;
      const rCoverage = (r as unknown as { coverage_status?: string }).coverage_status ?? "";
      const matchCoverage = coverageFilter === "all" || rCoverage === coverageFilter;
      return matchSearch && matchStatus && matchPriority && matchCoverage;
    });
  }, [catalogItems, search, statusFilter, priorityFilter, coverageFilter]);

  const catalogPageCount = Math.ceil(filteredCatalog.length / PAGE_SIZE);
  const pagedCatalog = filteredCatalog.slice(catalogPage * PAGE_SIZE, (catalogPage + 1) * PAGE_SIZE);

  // ── Helpers ────────────────────────────────────────────────────────────────
  function showToast(msg: string, error = false) {
    setToastMsg(msg);
    setToastError(error);
    setTimeout(() => setToastMsg(null), 3500);
  }

  function handleFieldChange(key: keyof NewReqFields, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  function handleCloseModal() {
    setShowModal(false);
    setFields(EMPTY_FIELDS);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fields.external_key.trim() || !fields.title.trim()) return;
    try {
      await createCatalogItem.mutateAsync({
        external_key: fields.external_key.trim(),
        external_source: fields.external_source,
        title: fields.title.trim(),
        description: fields.description.trim() || null,
        priority: fields.priority,
        status: fields.status,
        tags: fields.module ? [fields.module] : [],
      });
      showToast("Gereksinim oluşturuldu.");
      handleCloseModal();
    } catch {
      showToast("Gereksinim kaydedilemedi. Tekrar deneyin.", true);
      handleCloseModal();
    }
  }

  function resetFilters() {
    setSearch("");
    setStatusFilter("all");
    setPriorityFilter("all");
    setCoverageFilter("all");
    setTracePage(0);
    setCatalogPage(0);
  }

  // ── Coverage summary card values ───────────────────────────────────────────
  const summaryCardData = useTraceForDonut
    ? {
        covered: coveredCount,
        partial: partialCount,
        notCovered: notCoveredCount,
        outOfScope: outOfScopeCount,
      }
    : { covered: catCovered, partial: catPartial, notCovered: catNotCovered, outOfScope: catOutOfScope };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-[calc(100vh-88px)] bg-surface-base text-fg flex flex-col">
      {/* ── Header ── */}
      <div className="border-b border-border bg-surface-raised px-6 py-4 space-y-4 shrink-0">
        {/* Title row */}
        <div className="flex items-center justify-between">
          <h1 className="text-[13px] font-semibold text-fg">Gereksinim Kapsamı</h1>
          <div className="flex items-center gap-3">
            {/* Tab switcher */}
            <div className="flex items-center gap-1 rounded-md border border-border p-0.5">
              {(["traceability", "catalog"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setActiveTab(tab);
                    setTracePage(0);
                    setCatalogPage(0);
                    setSelectedReq(null);
                  }}
                  className={[
                    "rounded px-3 py-1.5 text-[11px] font-medium transition-colors",
                    activeTab === tab
                      ? "bg-white/[0.08] text-fg"
                      : "text-fg-subtle hover:text-fg-muted",
                  ].join(" ")}
                >
                  {tab === "traceability" ? "Traceability Matrix" : "Gereksinim Kataloğu"}
                </button>
              ))}
            </div>
            {/* CSV import button */}
            <label className="flex cursor-pointer items-center gap-1.5 rounded border border-border px-3 py-1.5 text-[11px] font-medium text-fg-muted transition-colors hover:border-brand/40 hover:text-fg">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
              </svg>
              CSV İçe Aktar
              <input type="file" accept=".csv,.tsv" className="hidden" onChange={async e => {
                const file = e.target.files?.[0];
                if (!file) return;
                const text = await file.text();
                const lines = text.split("\n").filter(l => l.trim());
                const headers = lines[0].split(/[,\t]/).map(h => h.trim().toLowerCase());
                const items = lines.slice(1).map(line => {
                  const cells = line.split(/[,\t]/);
                  const obj: Record<string, string> = {};
                  headers.forEach((h, i) => { obj[h] = (cells[i] ?? "").trim().replace(/^"|"$/g, ""); });
                  return obj;
                }).filter(o => o.title || o.name || o["external_key"]);
                const reqs = items.map(o => ({
                  external_source: o["source"] || "csv_import",
                  external_key: o["external_key"] || o["key"] || o["id"] || `CSV-${Math.random().toString(36).slice(2,7)}`,
                  title: o["title"] || o["name"] || o["requirement"] || "İsimsiz Gereksinim",
                  description: o["description"] || o["desc"] || undefined,
                  priority: o["priority"] || "medium",
                  status: o["status"] || "open",
                  tags: o["tags"] ? o["tags"].split(";").map((t: string) => t.trim()) : [],
                }));
                if (reqs.length === 0) { setCsvImportMsg("Uygun satır bulunamadı"); return; }
                const res = await bulkCreateReqs.mutateAsync(reqs);
                setCsvImportMsg(`${res.created} gereksinim içe aktarıldı`);
                setTimeout(() => setCsvImportMsg(null), 5000);
                e.target.value = "";
              }}/>
            </label>

            {/* New requirement button */}
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-1.5 rounded border border-brand/40 bg-brand/10 px-3 py-1.5 text-[11px] font-medium text-brand-fg transition-colors hover:bg-brand/20 hover:border-brand/60"
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Yeni Gereksinim
            </button>
          </div>
        </div>

        {/* Coverage summary cards + donut */}
        <div className="flex items-start gap-4">
          {/* Summary cards */}
          <div className="grid grid-cols-4 gap-3 flex-1">
            {[
              {
                label: "Kapsandı",
                value: summaryCardData.covered,
                color: "border-emerald-500/30 bg-emerald-500/10",
                textColor: "text-emerald-400",
                dot: "bg-emerald-500",
              },
              {
                label: "Kısmi",
                value: summaryCardData.partial,
                color: "border-amber-500/30 bg-amber-500/10",
                textColor: "text-amber-400",
                dot: "bg-amber-500",
              },
              {
                label: "Kapsamdışı",
                value: summaryCardData.notCovered,
                color: "border-slate-500/30 bg-surface-overlay",
                textColor: "text-fg-muted",
                dot: "bg-slate-500",
              },
              {
                label: "Kapsam Dışı",
                value: summaryCardData.outOfScope,
                color: "border-purple-500/30 bg-purple-500/10",
                textColor: "text-purple-400",
                dot: "bg-purple-500",
              },
            ].map((card) => (
              <div
                key={card.label}
                className={`rounded-lg border px-4 py-3 space-y-1 ${card.color}`}
              >
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${card.dot}`} />
                  <span className="text-[10px] font-medium text-fg-subtle uppercase tracking-wider">
                    {card.label}
                  </span>
                </div>
                <p className={`text-[22px] font-bold ${card.textColor}`}>{card.value}</p>
              </div>
            ))}
          </div>

          {/* Donut chart */}
          <div className="rounded-lg border border-border bg-surface-overlay px-5 py-3 shrink-0">
            <DonutChart
              covered={summaryCardData.covered}
              partial={summaryCardData.partial}
              notCovered={summaryCardData.notCovered}
              outOfScope={summaryCardData.outOfScope}
            />
          </div>
        </div>

        {/* Search + Filters */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <svg
              className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-fg-subtle"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setTracePage(0);
                setCatalogPage(0);
              }}
              placeholder="Başlık veya external key ara..."
              className="w-full rounded border border-border bg-surface-base pl-8 pr-3 py-1.5 text-[12px] text-fg placeholder-fg-subtle outline-none focus:border-brand/50"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setTracePage(0);
              setCatalogPage(0);
            }}
            className="rounded border border-border bg-surface-raised px-2 py-1.5 text-[12px] text-fg-muted outline-none focus:border-brand/50"
          >
            <option value="all">Tüm Durumlar</option>
            <option value="open">open</option>
            <option value="in_progress">in_progress</option>
            <option value="done">done</option>
            <option value="deferred">deferred</option>
            <option value="draft">draft</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
          </select>
          <select
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value);
              setTracePage(0);
              setCatalogPage(0);
            }}
            className="rounded border border-border bg-surface-raised px-2 py-1.5 text-[12px] text-fg-muted outline-none focus:border-brand/50"
          >
            <option value="all">Tüm Öncelikler</option>
            {["P0", "P1", "P2", "P3"].map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          {activeTab === "catalog" && (
            <select
              value={coverageFilter}
              onChange={(e) => {
                setCoverageFilter(e.target.value);
                setCatalogPage(0);
              }}
              className="rounded border border-border bg-surface-raised px-2 py-1.5 text-[12px] text-fg-muted outline-none focus:border-brand/50"
            >
              <option value="all">Tüm Kapsam</option>
              <option value="covered">covered</option>
              <option value="partially_covered">partially_covered</option>
              <option value="not_covered">not_covered</option>
              <option value="out_of_scope">out_of_scope</option>
            </select>
          )}
        </div>
      </div>

      {/* ── Content ── */}
      <div className="flex flex-1 min-h-0">
        {/* Main panel */}
        <div className={`flex flex-col flex-1 min-w-0 ${selectedReq ? "border-r border-border" : ""}`}>
          {/* Traceability tab */}
          {activeTab === "traceability" &&
            (traceLoading ? (
              <LoadingSkeleton />
            ) : traceError ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <p className="text-sm text-red-400">Gereksinimler yüklenemedi</p>
                <button
                  onClick={() => traceRefetch()}
                  className="text-xs text-fg-subtle hover:text-fg-muted"
                >
                  Tekrar Dene
                </button>
              </div>
            ) : filteredRows.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
                <div className="rounded-full bg-white/[0.04] p-4">
                  <svg className="h-8 w-8 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                </div>
                {search || statusFilter !== "all" || priorityFilter !== "all" ? (
                  <>
                    <p className="text-sm text-fg-muted">Kriterlere uyan gereksinim bulunamadı</p>
                    <button onClick={resetFilters} className="text-xs text-fg-subtle hover:text-fg-muted">
                      Filtreleri Temizle
                    </button>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-fg">Henüz gereksinim bağlantısı yok</p>
                    <p className="text-xs text-fg-muted max-w-xs">
                      Test case&apos;lerinizi gereksinimlerle ilişkilendirdiğinizde kapsam matrisi burada görünecek.
                    </p>
                  </>
                )}
              </div>
            ) : (
              <>
                <div className="overflow-x-auto flex-1">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b border-border bg-surface-raised sticky top-0 z-10">
                        {["Req. Key", "Başlık", "Durum", "Öncelik", "Kapsam", "Case Sayısı"].map((h) => (
                          <th
                            key={h}
                            className="px-4 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {pagedTraceRows.map((row) => (
                        <TraceRow key={row.requirement_id} row={row} />
                      ))}
                    </tbody>
                  </table>
                </div>
                {tracePageCount > 1 && (
                  <div className="flex items-center justify-between border-t border-border bg-surface-raised px-6 py-3 shrink-0">
                    <span className="text-[11px] text-fg-subtle">
                      {filteredRows.length} sonuç — Sayfa {tracePage + 1} / {tracePageCount}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setTracePage((p) => Math.max(0, p - 1))}
                        disabled={tracePage === 0}
                        className="rounded px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg disabled:opacity-30"
                      >
                        ← Önceki
                      </button>
                      <button
                        onClick={() => setTracePage((p) => Math.min(tracePageCount - 1, p + 1))}
                        disabled={tracePage >= tracePageCount - 1}
                        className="rounded px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg disabled:opacity-30"
                      >
                        Sonraki →
                      </button>
                    </div>
                  </div>
                )}
              </>
            ))}

          {/* Catalog tab */}
          {activeTab === "catalog" &&
            (catalogLoading ? (
              <LoadingSkeleton />
            ) : catalogError ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <p className="text-sm text-red-400">Gereksinimler yüklenemedi</p>
                <button onClick={() => catalogRefetch()} className="text-xs text-fg-subtle hover:text-fg-muted">
                  Tekrar Dene
                </button>
              </div>
            ) : filteredCatalog.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
                <div className="rounded-full bg-white/[0.04] p-4">
                  <svg className="h-8 w-8 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                </div>
                {search || statusFilter !== "all" || priorityFilter !== "all" || coverageFilter !== "all" ? (
                  <>
                    <p className="text-sm text-fg-muted">Kriterlere uyan gereksinim bulunamadı</p>
                    <button onClick={resetFilters} className="text-xs text-fg-subtle hover:text-fg-muted">
                      Filtreleri Temizle
                    </button>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-fg">Gereksinim kataloğu boş</p>
                    <p className="text-xs text-fg-muted max-w-xs">
                      İlk gereksinimi oluşturmak için yukarıdaki butonu kullanın.
                    </p>
                    <button
                      onClick={() => setShowModal(true)}
                      className="mt-1 rounded border border-brand/40 bg-brand/10 px-3 py-1.5 text-[11px] text-brand-fg hover:bg-brand/20"
                    >
                      Gereksinim Ekle
                    </button>
                  </>
                )}
              </div>
            ) : (
              <>
                <div className="overflow-x-auto flex-1">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b border-border bg-surface-raised sticky top-0 z-10">
                        {["External Key", "Kaynak", "Başlık", "Öncelik", "Durum", "Etiketler"].map((h) => (
                          <th
                            key={h}
                            className="px-4 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {pagedCatalog.map((req: Requirement) => (
                        <tr
                          key={req.id}
                          onClick={() => setSelectedReq(selectedReq?.id === req.id ? null : req)}
                          className={[
                            "border-b border-border hover:bg-white/[0.04] transition-colors cursor-pointer",
                            selectedReq?.id === req.id ? "bg-brand/5 border-l-2 border-l-brand" : "",
                          ].join(" ")}
                        >
                          <td className="px-4 py-3">
                            <span className="text-[11px] font-mono text-fg-muted">{req.external_key}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[11px] text-fg-subtle">{req.external_source}</span>
                          </td>
                          <td className="px-4 py-3 max-w-[280px]">
                            <span className="text-[13px] text-fg truncate block">{req.title}</span>
                            {req.description && (
                              <span className="text-[11px] text-fg-subtle truncate block mt-0.5">
                                {req.description}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <Badge
                              label={req.priority}
                              colorClass={
                                PRIORITY_COLORS[req.priority] ??
                                "text-fg-muted border-border bg-surface-overlay"
                              }
                            />
                          </td>
                          <td className="px-4 py-3">
                            <Badge
                              label={req.status}
                              colorClass={
                                STATUS_COLORS[req.status] ??
                                "text-fg-muted border-border bg-surface-overlay"
                              }
                            />
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {req.tags.slice(0, 2).map((tag) => (
                                <span
                                  key={tag}
                                  className="rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-fg-subtle"
                                >
                                  {tag}
                                </span>
                              ))}
                              {req.tags.length > 2 && (
                                <span className="text-[10px] text-fg-subtle">+{req.tags.length - 2}</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                            <button type="button"
                              disabled={genForReq === req.id}
                              onClick={async () => {
                                setGenForReq(req.id);
                                try {
                                  const res = await generateCases.mutateAsync({
                                    prompt: `${req.title}${req.description ? ": " + req.description : ""}`,
                                    count: 3, save: false,
                                  });
                                  setGenResult({ req, cases: res.cases });
                                } finally {
                                  setGenForReq(null);
                                }
                              }}
                              className="rounded-lg border border-teal-500/25 bg-teal-500/5 px-2 py-1 text-[10px] text-teal-400 hover:bg-teal-500/15 disabled:opacity-40 transition-colors whitespace-nowrap">
                              {genForReq === req.id ? "Üretiliyor…" : "✦ Case Üret"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {catalogPageCount > 1 && (
                  <div className="flex items-center justify-between border-t border-border bg-surface-raised px-6 py-3 shrink-0">
                    <span className="text-[11px] text-fg-subtle">
                      {filteredCatalog.length} sonuç — Sayfa {catalogPage + 1} / {catalogPageCount}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setCatalogPage((p) => Math.max(0, p - 1))}
                        disabled={catalogPage === 0}
                        className="rounded px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg disabled:opacity-30"
                      >
                        ← Önceki
                      </button>
                      <button
                        onClick={() => setCatalogPage((p) => Math.min(catalogPageCount - 1, p + 1))}
                        disabled={catalogPage >= catalogPageCount - 1}
                        className="rounded px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg disabled:opacity-30"
                      >
                        Sonraki →
                      </button>
                    </div>
                  </div>
                )}
              </>
            ))}
        </div>

        {/* Catalog detail side panel (inline) */}
        {activeTab === "catalog" && selectedReq && (
          <div className="w-[340px] shrink-0 border-l border-border bg-surface-raised overflow-hidden flex flex-col">
            <CatalogDetailPanel req={selectedReq} onClose={() => setSelectedReq(null)} />
          </div>
        )}
      </div>

      {/* ── New Requirement Modal ── */}
      {showModal && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={handleCloseModal}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              className="relative w-full max-w-lg rounded-xl border border-border bg-surface-raised shadow-2xl flex flex-col max-h-[90vh]"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal header */}
              <div className="flex items-center justify-between border-b border-border px-6 py-4 shrink-0">
                <h2 className="text-[14px] font-semibold text-fg">Yeni Gereksinim</h2>
                <button
                  onClick={handleCloseModal}
                  className="rounded p-1 text-fg-subtle hover:bg-white/[0.06] hover:text-fg transition-colors"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="flex flex-col overflow-hidden">
                <div className="overflow-y-auto px-6 py-5 space-y-4">
                  {/* External Key + Source row */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-medium text-fg-muted">
                        External Key <span className="text-red-400">*</span>
                      </label>
                      <input
                        type="text"
                        value={fields.external_key}
                        onChange={(e) => handleFieldChange("external_key", e.target.value)}
                        placeholder="REQ-001"
                        required
                        className="w-full rounded border border-border bg-surface-base px-3 py-2 text-[12px] text-fg placeholder-fg-subtle outline-none focus:border-brand/50 transition-colors"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-medium text-fg-muted">External Source</label>
                      <select
                        value={fields.external_source}
                        onChange={(e) => handleFieldChange("external_source", e.target.value)}
                        className="w-full rounded border border-border bg-surface-base px-3 py-2 text-[12px] text-fg outline-none focus:border-brand/50 transition-colors"
                      >
                        {EXTERNAL_SOURCES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Title */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium text-fg-muted">
                      Başlık <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={fields.title}
                      onChange={(e) => handleFieldChange("title", e.target.value)}
                      placeholder="Gereksinim başlığı..."
                      required
                      className="w-full rounded border border-border bg-surface-base px-3 py-2 text-[12px] text-fg placeholder-fg-subtle outline-none focus:border-brand/50 transition-colors"
                    />
                  </div>

                  {/* Description */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium text-fg-muted">Açıklama</label>
                    <textarea
                      value={fields.description}
                      onChange={(e) => handleFieldChange("description", e.target.value)}
                      placeholder="İsteğe bağlı açıklama..."
                      rows={3}
                      className="w-full resize-none rounded border border-border bg-surface-base px-3 py-2 text-[12px] text-fg placeholder-fg-subtle outline-none focus:border-brand/50 transition-colors"
                    />
                  </div>

                  {/* Module */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium text-fg-muted">Modül / Etiket</label>
                    <select
                      value={fields.module}
                      onChange={(e) => handleFieldChange("module", e.target.value)}
                      className="w-full rounded border border-border bg-surface-base px-3 py-2 text-[12px] text-fg outline-none focus:border-brand/50 transition-colors"
                    >
                      <option value="">Seçiniz...</option>
                      {MODULE_OPTIONS.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>

                  {/* Priority + Status */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-medium text-fg-muted">Öncelik</label>
                      <select
                        value={fields.priority}
                        onChange={(e) => handleFieldChange("priority", e.target.value)}
                        className="w-full rounded border border-border bg-surface-base px-3 py-2 text-[12px] text-fg outline-none focus:border-brand/50 transition-colors"
                      >
                        {["P0", "P1", "P2", "P3"].map((p) => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-medium text-fg-muted">Durum</label>
                      <select
                        value={fields.status}
                        onChange={(e) => handleFieldChange("status", e.target.value)}
                        className="w-full rounded border border-border bg-surface-base px-3 py-2 text-[12px] text-fg outline-none focus:border-brand/50 transition-colors"
                      >
                        <option value="open">open</option>
                        <option value="in_progress">in_progress</option>
                        <option value="done">done</option>
                        <option value="deferred">deferred</option>
                        <option value="draft">draft</option>
                        <option value="approved">approved</option>
                      </select>
                    </div>
                  </div>

                  {/* Coverage Status */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium text-fg-muted">Kapsam Durumu</label>
                    <select
                      value={fields.coverage_status}
                      onChange={(e) => handleFieldChange("coverage_status", e.target.value)}
                      className="w-full rounded border border-border bg-surface-base px-3 py-2 text-[12px] text-fg outline-none focus:border-brand/50 transition-colors"
                    >
                      <option value="covered">covered</option>
                      <option value="partially_covered">partially_covered</option>
                      <option value="not_covered">not_covered</option>
                      <option value="out_of_scope">out_of_scope</option>
                    </select>
                  </div>
                </div>

                {/* Modal footer */}
                <div className="flex items-center justify-end gap-2 border-t border-border px-6 py-4 shrink-0">
                  <button
                    type="button"
                    onClick={handleCloseModal}
                    className="rounded px-4 py-2 text-[12px] text-fg-muted hover:bg-white/[0.06] hover:text-fg transition-colors"
                  >
                    İptal
                  </button>
                  <button
                    type="submit"
                    disabled={
                      createCatalogItem.isPending ||
                      !fields.external_key.trim() ||
                      !fields.title.trim()
                    }
                    className="rounded border border-brand/40 bg-brand/10 px-4 py-2 text-[12px] font-medium text-brand-fg transition-colors hover:bg-brand/20 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {createCatalogItem.isPending ? "Kaydediliyor..." : "Oluştur"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}

      {/* ── Toast ── */}
      {csvImportMsg && (
        <div className="fixed bottom-16 right-6 z-[60] rounded-lg border border-emerald-500/30 bg-surface-raised px-4 py-3 text-[12px] text-emerald-400 shadow-xl">
          ✓ {csvImportMsg}
        </div>
      )}

      {toastMsg && (
        <div
          className={[
            "fixed bottom-6 right-6 z-[60] rounded-lg border px-4 py-3 text-[12px] shadow-xl",
            toastError
              ? "border-red-500/30 bg-surface-raised text-red-400"
              : "border-border bg-surface-raised text-fg",
          ].join(" ")}
        >
          {toastMsg}
        </div>
      )}

      {/* AI Generated Cases Modal */}
      {genResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-xl border border-border bg-surface-raised shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div>
                <h3 className="text-[14px] font-semibold text-fg">AI ile Üretilen Test Case&apos;leri</h3>
                <p className="mt-0.5 text-[11px] text-fg-subtle truncate max-w-md">{genResult.req.title}</p>
              </div>
              <button type="button" onClick={() => setGenResult(null)}
                className="rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg">✕</button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-5 space-y-3">
              {genResult.cases.map((gc, i) => (
                <div key={i} className="rounded-xl border border-border bg-surface-overlay p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[13px] font-medium text-fg">{gc.title}</p>
                      {gc.objective && <p className="mt-0.5 text-[11px] text-fg-muted">{gc.objective}</p>}
                      <div className="mt-1.5 flex gap-1.5">
                        <span className="rounded border border-border px-1.5 py-0.5 text-[10px] text-fg-subtle">{gc.priority}</span>
                        {gc.tags.slice(0, 3).map(t => (
                          <span key={t} className="rounded bg-surface-accent px-1.5 py-0.5 text-[10px] text-fg-subtle">{t}</span>
                        ))}
                        <span className="text-[10px] text-fg-subtle">{gc.steps.length} adım</span>
                      </div>
                    </div>
                    <button type="button"
                      onClick={async () => {
                        await generateCases.mutateAsync({
                          prompt: gc.title,
                          count: 1,
                          save: true,
                        });
                        setGenResult(null);
                      }}
                      className="shrink-0 rounded-lg bg-brand px-2.5 py-1.5 text-[11px] font-semibold text-brand-fg hover:brightness-105 transition-colors">
                      Kaydet
                    </button>
                  </div>
                  {gc.steps.length > 0 && (
                    <div className="mt-3 space-y-1 border-t border-border pt-3">
                      {gc.steps.slice(0, 3).map(s => (
                        <div key={s.step_no} className="flex items-start gap-2 text-[11px]">
                          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-surface-accent font-mono text-[9px] text-fg-subtle">{s.step_no}</span>
                          <span className="text-fg-muted">{s.action}</span>
                        </div>
                      ))}
                      {gc.steps.length > 3 && <p className="text-[10px] text-fg-subtle">+{gc.steps.length - 3} adım daha</p>}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="border-t border-border px-5 py-3 flex justify-end">
              <button type="button" onClick={() => setGenResult(null)}
                className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors">
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
