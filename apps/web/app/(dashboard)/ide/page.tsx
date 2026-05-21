"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";

type Project = { id: string; name: string; description?: string; archived?: boolean };

type Scenario = {
  id: string;
  title: string;
  status: string;
  current_version: number;
  updated_at?: string | null;
  tags?: string[];
};

type ScenarioDetail = {
  id: string;
  title: string;
  description?: string;
  status: string;
  current_version: number;
  steps?: Record<string, unknown>[];
  tags?: string[];
  updated_at?: string | null;
};

type OpenTab = {
  key: string;
  projectId: string;
  projectName: string;
  scenarioId: string;
  scenarioTitle: string;
};

type ProjectScenariosState = {
  loading: boolean;
  error: string | null;
  items: Scenario[] | null;
};

type ViewMode = "pretty" | "json";

/* IntelliJ Darcula-esque palette */
const UI = {
  frame: "#1e1f22",
  toolbar: "#2b2d30",
  toolbarBorder: "#1e1f22",
  panel: "#2b2d30",
  panelAlt: "#25272b",
  editor: "#1e1f22",
  editorGutter: "#1e1f22",
  rowHover: "#2e436e33",
  selected: "#2e436eaa",
  tabActive: "#1e1f22",
  tabInactive: "#2b2d30",
  border: "#393b40",
  subtleBorder: "#303236",
  text: "#dfe1e5",
  textMuted: "#9da0a8",
  textFaint: "#6f737a",
  accent: "#3574f0",
  accentSoft: "#3574f033",
  keyword: "#cf8e6d",
  stringLit: "#6aab73",
  numberLit: "#2aacb8",
  propKey: "#c77dbb",
};

const STATUS_DOT: Record<string, string> = {
  active: "bg-emerald-400",
  draft: "bg-slate-400",
  archived: "bg-red-400",
};

function tabKey(projectId: string, scenarioId: string) {
  return `${projectId}::${scenarioId}`;
}

/* Monochrome scenario "file" icon — IntelliJ "feature file" feel */
function FileIcon({ status }: { status?: string }) {
  return (
    <span className="relative inline-flex h-3.5 w-3.5 shrink-0 items-center justify-center">
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5">
        <path
          d="M3 1.5a.5.5 0 01.5-.5h6.3l3.2 3.2v9.8a.5.5 0 01-.5.5h-9a.5.5 0 01-.5-.5V1.5z"
          fill="#4b6eaf"
          fillOpacity="0.18"
          stroke="#6897bb"
          strokeWidth="0.9"
        />
        <path d="M9.8 1v3.2H13" fill="none" stroke="#6897bb" strokeWidth="0.9" />
      </svg>
      {status && (
        <span
          className={cn(
            "absolute -right-0.5 -bottom-0.5 h-1.5 w-1.5 rounded-full ring-1 ring-[#1e1f22]",
            STATUS_DOT[status] ?? "bg-slate-500",
          )}
        />
      )}
    </span>
  );
}

/* IntelliJ module/folder icon */
function FolderIcon({ open }: { open: boolean }) {
  return open ? (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0">
      <path
        d="M1.5 3.5A.5.5 0 012 3h3.3l1.2 1.2H14a.5.5 0 01.5.5V6h-13V3.5z"
        fill="#afb1b3"
        fillOpacity="0.25"
        stroke="#afb1b3"
        strokeWidth="0.8"
      />
      <path
        d="M1.5 6h13l-1 6.7a.5.5 0 01-.5.43H3a.5.5 0 01-.5-.43L1.5 6z"
        fill="#afb1b3"
        fillOpacity="0.28"
        stroke="#afb1b3"
        strokeWidth="0.8"
      />
    </svg>
  ) : (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0">
      <path
        d="M1.5 4.3A.8.8 0 012.3 3.5h3l1.3 1.3h6.9a.8.8 0 01.8.8v6.8a.8.8 0 01-.8.8H2.3a.8.8 0 01-.8-.8V4.3z"
        fill="#afb1b3"
        fillOpacity="0.2"
        stroke="#afb1b3"
        strokeWidth="0.9"
      />
    </svg>
  );
}

function Chevron({ expanded }: { expanded: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={cn(
        "h-3 w-3 shrink-0 transition-transform duration-100",
        expanded ? "rotate-90" : "",
      )}
      style={{ color: UI.textFaint }}
    >
      <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function highlightJson(value: unknown) {
  const raw = JSON.stringify(value, null, 2) ?? "";
  const esc = raw.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c] as string));
  return esc.replace(
    /("(?:\\.|[^"\\])*")(\s*:)?|(\b-?\d+(?:\.\d+)?\b)|(\btrue\b|\bfalse\b|\bnull\b)/g,
    (_m, str: string | undefined, colon: string | undefined, num: string | undefined, kw: string | undefined) => {
      if (str) {
        const color = colon ? UI.propKey : UI.stringLit;
        return `<span style="color:${color}">${str}</span>${colon ?? ""}`;
      }
      if (num) return `<span style="color:${UI.numberLit}">${num}</span>`;
      if (kw) return `<span style="color:${UI.keyword}">${kw}</span>`;
      return "";
    },
  );
}

function CodeBlock({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div
      className="flex overflow-auto font-mono text-[12.5px] leading-[1.55]"
      style={{ background: UI.editor, color: UI.text }}
    >
      <pre
        aria-hidden
        className="select-none border-r px-3 py-3 text-right"
        style={{ borderColor: UI.subtleBorder, color: UI.textFaint, background: UI.editorGutter }}
      >
        {lines.map((_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </pre>
      <pre className="min-w-0 flex-1 px-4 py-3 whitespace-pre">
        <code dangerouslySetInnerHTML={{
          __html: (() => {
            try { return highlightJson(JSON.parse(text)); }
            catch { return `<span style="color:#f87171">[Geçersiz JSON]</span>\n${text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}`; }
          })()
        }} />
      </pre>
    </div>
  );
}

function Breadcrumb({ parts }: { parts: string[] }) {
  return (
    <div
      className="flex items-center gap-1 overflow-hidden px-3 py-1 text-[11px]"
      style={{ background: UI.frame, color: UI.textMuted, borderBottom: `1px solid ${UI.subtleBorder}` }}
    >
      {parts.map((p, i) => (
        <span key={i} className="flex items-center gap-1 truncate">
          {i > 0 && (
            <svg viewBox="0 0 16 16" className="h-2.5 w-2.5 shrink-0" style={{ color: UI.textFaint }}>
              <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
          )}
          <span className="truncate">{p}</span>
        </span>
      ))}
    </div>
  );
}

export default function ScenarioIdePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [scenariosByProject, setScenariosByProject] = useState<Record<string, ProjectScenariosState>>({});

  const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
  const [activeTabKey, setActiveTabKey] = useState<string | null>(null);

  const [detailCache, setDetailCache] = useState<Record<string, ScenarioDetail>>({});
  const [detailLoading, setDetailLoading] = useState<Record<string, boolean>>({});
  const [detailError, setDetailError] = useState<Record<string, string | null>>({});

  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("pretty");
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);

  const detailAbortRef = useRef<AbortController | null>(null);

  const router = useRouter();
  const { toast } = useToast();

  useEffect(() => {
    let cancelled = false;
    setProjectsLoading(true);
    apiFetch<Project[]>("/api/v1/tspm/projects")
      .then((data) => {
        if (cancelled) return;
        setProjects(data);
        setProjectsError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setProjectsError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setProjectsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadScenariosForProject = useCallback(async (projectId: string) => {
    setScenariosByProject((prev) => ({
      ...prev,
      [projectId]: { loading: true, error: null, items: prev[projectId]?.items ?? null },
    }));
    try {
      const data = await apiFetch<Scenario[]>(`/api/v1/tspm/projects/${projectId}/scenarios`);
      setScenariosByProject((prev) => ({ ...prev, [projectId]: { loading: false, error: null, items: data } }));
    } catch (err: unknown) {
      setScenariosByProject((prev) => ({
        ...prev,
        [projectId]: {
          loading: false,
          error: err instanceof Error ? err.message : "Senaryolar yüklenemedi",
          items: prev[projectId]?.items ?? null,
        },
      }));
    }
  }, []);

  const toggleProject = useCallback(
    (projectId: string) => {
      setExpanded((prev) => {
        const next = new Set(prev);
        if (next.has(projectId)) next.delete(projectId);
        else {
          next.add(projectId);
          const current = scenariosByProject[projectId];
          if (!current?.items && !current?.loading) void loadScenariosForProject(projectId);
        }
        return next;
      });
    },
    [loadScenariosForProject, scenariosByProject],
  );

  const expandAll = useCallback(() => {
    setExpanded(new Set(projects.map((p) => p.id)));
    projects.forEach((p) => {
      if (!scenariosByProject[p.id]?.items && !scenariosByProject[p.id]?.loading) {
        void loadScenariosForProject(p.id);
      }
    });
  }, [projects, scenariosByProject, loadScenariosForProject]);

  const collapseAll = useCallback(() => setExpanded(new Set()), []);

  const loadDetail = useCallback(async (projectId: string, scenarioId: string) => {
    const key = tabKey(projectId, scenarioId);
    detailAbortRef.current?.abort();
    const controller = new AbortController();
    detailAbortRef.current = controller;
    setDetailLoading((prev) => ({ ...prev, [key]: true }));
    setDetailError((prev) => ({ ...prev, [key]: null }));
    try {
      const data = await apiFetch<ScenarioDetail>(
        `/api/v1/tspm/projects/${projectId}/scenarios/${scenarioId}`,
        { signal: controller.signal },
      );
      setDetailCache((prev) => ({ ...prev, [key]: data }));
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      setDetailError((prev) => ({
        ...prev,
        [key]: err instanceof Error ? err.message : "Senaryo detayı yüklenemedi",
      }));
    } finally {
      if (!controller.signal.aborted) setDetailLoading((prev) => ({ ...prev, [key]: false }));
    }
  }, []);

  const openScenario = useCallback(
    (project: Project, scenario: Scenario) => {
      const key = tabKey(project.id, scenario.id);
      setOpenTabs((prev) => {
        if (prev.some((t) => t.key === key)) return prev;
        return [
          ...prev,
          {
            key,
            projectId: project.id,
            projectName: project.name,
            scenarioId: scenario.id,
            scenarioTitle: scenario.title,
          },
        ];
      });
      setActiveTabKey(key);
      if (!detailCache[key]) void loadDetail(project.id, scenario.id);
    },
    [detailCache, loadDetail],
  );

  const closeTab = useCallback(
    (key: string) => {
      setOpenTabs((prev) => {
        const next = prev.filter((t) => t.key !== key);
        if (activeTabKey === key) {
          const fallback = next[next.length - 1] ?? null;
          setActiveTabKey(fallback?.key ?? null);
        }
        return next;
      });
    },
    [activeTabKey],
  );

  const activeTab = useMemo(() => openTabs.find((t) => t.key === activeTabKey) ?? null, [openTabs, activeTabKey]);
  const activeDetail = activeTab ? detailCache[activeTab.key] : null;
  const activeLoading = activeTab ? !!detailLoading[activeTab.key] : false;
  const activeError = activeTab ? detailError[activeTab.key] ?? null : null;

  const filteredProjects = useMemo(() => {
    if (!search.trim()) return projects;
    const q = search.trim().toLowerCase();
    return projects.filter((p) => {
      if (p.name.toLowerCase().includes(q)) return true;
      const scenarios = scenariosByProject[p.id]?.items ?? [];
      return scenarios.some((s) => s.title.toLowerCase().includes(q));
    });
  }, [projects, scenariosByProject, search]);

  const totalLoadedScenarios = useMemo(
    () => Object.values(scenariosByProject).reduce((acc, s) => acc + (s.items?.length ?? 0), 0),
    [scenariosByProject],
  );

  const onCopy = () => {
    if (!activeDetail) return;
    try {
      navigator.clipboard?.writeText(JSON.stringify(activeDetail, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* ignore */
    }
  };

  const handleRun = useCallback(async () => {
    if (!activeTab) return;
    setRunning(true);
    try {
      const created = await apiFetch<{ id: string }>(
        `/api/v1/tspm/projects/${activeTab.projectId}/executions`,
        {
          method: "POST",
          json: {
            name: `${activeTab.scenarioTitle} — IDE Run`,
            scenario_ids: [activeTab.scenarioId],
          },
        },
      );
      router.push(`/p/${activeTab.projectId}/executions/${created.id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Execution oluşturulamadı";
      toast(message, "error");
      setRunning(false);
    }
  }, [activeTab, router, toast]);

  const stepsCount = activeDetail?.steps?.length ?? 0;
  const breadcrumbParts = activeTab
    ? [activeTab.projectName, "scenarios", `${activeTab.scenarioTitle}.json`]
    : [];

  return (
    <div
      className="flex min-h-screen flex-col overflow-hidden"
      style={{ background: UI.frame, color: UI.text }}
      data-testid="scenario-ide-page"
    >
      {/* Title bar */}
      <div
        className="flex h-8 items-center gap-3 px-3 text-[12px]"
        style={{ background: UI.toolbar, borderBottom: `1px solid ${UI.toolbarBorder}` }}
      >
        <div className="flex items-center gap-2">
          <div className="flex h-4 w-4 items-center justify-center rounded-sm" style={{ background: "#f2c55c" }}>
            <span className="text-[10px] font-bold text-[#1e1f22]">V</span>
          </div>
          <span className="font-medium" style={{ color: UI.text }}>Neurex IDE</span>
          <span style={{ color: UI.textFaint }}>—</span>
          <span style={{ color: UI.textMuted }}>
            {activeTab ? `${activeTab.projectName} › ${activeTab.scenarioTitle}` : "Senaryo Çalışma Alanı"}
          </span>
        </div>
        <div className="ml-auto flex items-center gap-1 text-[11px]" style={{ color: UI.textFaint }}>
          <span>File</span>
          <span>Edit</span>
          <span>View</span>
          <span>Navigate</span>
          <span>Run</span>
          <span>Tools</span>
        </div>
      </div>

      {/* Toolbar */}
      <div
        className="flex h-9 items-center gap-2 px-2 text-[11px]"
        style={{ background: UI.toolbar, borderBottom: `1px solid ${UI.subtleBorder}`, color: UI.textMuted }}
      >
        <button
          type="button"
          onClick={() => void handleRun()}
          disabled={!activeTab || running}
          className="flex items-center gap-1 rounded px-2 py-1 transition-colors disabled:opacity-40"
          style={{ background: "transparent" }}
          onMouseEnter={(e) => ((e.currentTarget.style.background = "#3c3f41"))}
          onMouseLeave={(e) => ((e.currentTarget.style.background = "transparent"))}
        >
          {running ? (
            <div
              className="h-3.5 w-3.5 animate-spin rounded-full border-2"
              style={{ borderColor: "#3c3f41", borderTopColor: "#6aab73" }}
            />
          ) : (
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" style={{ color: "#6aab73" }}>
              <path d="M4 3l8 5-8 5V3z" fill="currentColor" />
            </svg>
          )}
          {running ? "Running…" : "Run"}
        </button>
        <button
          type="button"
          className="flex items-center gap-1 rounded px-2 py-1 transition-colors"
          onMouseEnter={(e) => ((e.currentTarget.style.background = "#3c3f41"))}
          onMouseLeave={(e) => ((e.currentTarget.style.background = "transparent"))}
        >
          <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" style={{ color: "#e8725c" }}>
            <circle cx="8" cy="8" r="4" fill="currentColor" />
          </svg>
          Debug
        </button>
        <div className="mx-1 h-5 w-px" style={{ background: UI.border }} />
        <div className="flex items-center gap-1 rounded px-2 py-0.5" style={{ background: UI.panelAlt, border: `1px solid ${UI.border}` }}>
          <svg viewBox="0 0 16 16" className="h-3 w-3" style={{ color: "#f2c55c" }}>
            <path d="M8 1L9.9 5.7 15 6.2l-3.9 3.3L12.3 15 8 12.3 3.7 15l1.2-5.5L1 6.2l5.1-.5z" fill="currentColor" />
          </svg>
          <span style={{ color: UI.text }}>
            {activeTab ? activeTab.scenarioTitle.slice(0, 28) : "scenario"}
          </span>
          <svg viewBox="0 0 16 16" className="h-3 w-3" style={{ color: UI.textFaint }}>
            <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        </div>
        <div className="mx-1 h-5 w-px" style={{ background: UI.border }} />
        <span>Branch: </span>
        <span style={{ color: UI.text }}>fix/followup-sprint</span>
        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-1 rounded px-2 py-1" style={{ background: UI.panelAlt, border: `1px solid ${UI.border}` }}>
            <svg viewBox="0 0 16 16" className="h-3 w-3" style={{ color: UI.textFaint }}>
              <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
              <path d="M10 10l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search Everywhere"
              className="w-48 bg-transparent text-[11px] outline-none"
              style={{ color: UI.text }}
              data-testid="scenario-ide-search"
            />
            <span className="rounded px-1 text-[10px]" style={{ background: UI.panel, color: UI.textFaint, border: `1px solid ${UI.border}` }}>
              Double ⇧
            </span>
          </div>
        </div>
      </div>

      {/* Body: activity bar + left panel + editor */}
      <div className="flex min-h-0 flex-1">
        {/* Activity bar (left) */}
        <div
          className="flex w-10 shrink-0 flex-col items-center py-2"
          style={{ background: UI.toolbar, borderRight: `1px solid ${UI.subtleBorder}` }}
        >
          {[
            { label: "Project", active: true, icon: (
              <svg viewBox="0 0 16 16" className="h-4 w-4"><path d="M2 3h5l1.2 1.2H14V13a1 1 0 01-1 1H3a1 1 0 01-1-1V3z" fill="none" stroke="currentColor" strokeWidth="1.3" /></svg>
            )},
            { label: "Structure", icon: (
              <svg viewBox="0 0 16 16" className="h-4 w-4"><path d="M3 3h10M3 7h10M3 11h6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
            )},
            { label: "Commit", icon: (
              <svg viewBox="0 0 16 16" className="h-4 w-4"><circle cx="8" cy="8" r="2.5" fill="none" stroke="currentColor" strokeWidth="1.4" /><path d="M2 8h3.5M10.5 8H14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
            )},
            { label: "Problems", icon: (
              <svg viewBox="0 0 16 16" className="h-4 w-4"><path d="M8 2l7 12H1L8 2z" fill="none" stroke="currentColor" strokeWidth="1.3" /><path d="M8 7v3M8 12v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
            )},
          ].map((item) => (
            <button
              key={item.label}
              type="button"
              title={item.label}
              className="mb-1 flex h-8 w-8 items-center justify-center rounded transition-colors"
              style={{
                background: item.active ? UI.accentSoft : "transparent",
                color: item.active ? UI.text : UI.textFaint,
                borderLeft: item.active ? `2px solid ${UI.accent}` : "2px solid transparent",
              }}
            >
              {item.icon}
            </button>
          ))}

          <div className="mt-auto flex flex-col items-center gap-1">
            <button type="button" title="Terminal" className="flex h-8 w-8 items-center justify-center rounded" style={{ color: UI.textFaint }}>
              <svg viewBox="0 0 16 16" className="h-4 w-4"><path d="M3 5l3 3-3 3M8 11h5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" /></svg>
            </button>
            <button type="button" title="Settings" className="flex h-8 w-8 items-center justify-center rounded" style={{ color: UI.textFaint }}>
              <svg viewBox="0 0 16 16" className="h-4 w-4"><circle cx="8" cy="8" r="2" fill="none" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.5 1.5M11.5 11.5L13 13M3 13l1.5-1.5M11.5 4.5L13 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
            </button>
          </div>
        </div>

        {/* Project tool window */}
        <aside
          className="flex w-[300px] shrink-0 flex-col"
          style={{ background: UI.panel, borderRight: `1px solid ${UI.subtleBorder}` }}
          data-testid="scenario-ide-explorer"
        >
          {/* Tool window header */}
          <div
            className="flex h-7 items-center gap-2 px-2 text-[11px] uppercase tracking-wide"
            style={{ background: UI.toolbar, borderBottom: `1px solid ${UI.subtleBorder}`, color: UI.textMuted }}
          >
            <span style={{ color: UI.text, fontWeight: 600 }}>Project</span>
            <span>Files</span>
            <span>Scenarios</span>
            <div className="ml-auto flex items-center gap-1">
              <button
                type="button"
                onClick={expandAll}
                title="Expand All"
                className="flex h-5 w-5 items-center justify-center rounded"
                style={{ color: UI.textFaint }}
                data-testid="scenario-ide-expand-all"
              >
                <svg viewBox="0 0 16 16" className="h-3.5 w-3.5"><path d="M4 4h8M4 8h8M4 12h8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
              </button>
              <button
                type="button"
                onClick={collapseAll}
                title="Collapse All"
                className="flex h-5 w-5 items-center justify-center rounded"
                style={{ color: UI.textFaint }}
                data-testid="scenario-ide-collapse-all"
              >
                <svg viewBox="0 0 16 16" className="h-3.5 w-3.5"><path d="M3 8h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
              </button>
            </div>
          </div>

          {/* Tree */}
          <div className="flex-1 overflow-y-auto py-1 text-[12.5px]" style={{ fontFamily: "ui-sans-serif, system-ui" }}>
            {projectsLoading ? (
              <div className="flex items-center gap-2 px-3 py-2 text-[11px]" style={{ color: UI.textFaint }}>
                <div className="h-3 w-3 animate-spin rounded-full border-2" style={{ borderColor: UI.border, borderTopColor: UI.accent }} />
                Indexing projects...
              </div>
            ) : projectsError ? (
              <div className="mx-2 rounded px-2 py-1 text-[11px]" style={{ background: "#5a1e1e33", color: "#f08e8e", border: "1px solid #8b2f2f55" }}>
                {projectsError}
              </div>
            ) : filteredProjects.length === 0 ? (
              <div className="px-3 py-2 text-[11px]" style={{ color: UI.textFaint }}>Hiç proje yok.</div>
            ) : (
              <ul className="flex flex-col">
                {/* Root */}
                <li>
                  <div className="flex items-center gap-1.5 px-2 py-0.5" style={{ color: UI.text }}>
                    <Chevron expanded />
                    <FolderIcon open />
                    <span className="font-medium">visium-workspace</span>
                    <span className="ml-2 text-[10px]" style={{ color: UI.textFaint }}>
                      {projects.length} modules
                    </span>
                  </div>
                  <ul className="flex flex-col">
                    {filteredProjects.map((project) => {
                      const isOpen = expanded.has(project.id);
                      const state = scenariosByProject[project.id];
                      const scenarios = state?.items ?? [];
                      const q = search.trim().toLowerCase();
                      const filteredScenarios = q
                        ? scenarios.filter((s) => s.title.toLowerCase().includes(q))
                        : scenarios;
                      return (
                        <li key={project.id}>
                          <button
                            type="button"
                            onClick={() => toggleProject(project.id)}
                            className="flex w-full items-center gap-1.5 pl-5 pr-2 py-0.5 text-left transition-colors"
                            style={{ color: UI.text }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = UI.rowHover)}
                            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                            data-testid={`scenario-ide-project-${project.id}`}
                          >
                            <Chevron expanded={isOpen} />
                            <FolderIcon open={isOpen} />
                            <span className="truncate">{project.name}</span>
                            <span className="ml-auto text-[10px]" style={{ color: UI.textFaint }}>
                              {state?.items ? scenarios.length : state?.loading ? "…" : ""}
                            </span>
                          </button>

                          {isOpen && (
                            <div className="flex flex-col">
                              {state?.loading && !state.items ? (
                                <div className="flex items-center gap-2 pl-12 pr-2 py-1 text-[11px]" style={{ color: UI.textFaint }}>
                                  <div className="h-3 w-3 animate-spin rounded-full border-2" style={{ borderColor: UI.border, borderTopColor: UI.accent }} />
                                  Loading…
                                </div>
                              ) : state?.error ? (
                                <div className="flex flex-col gap-1 pl-12 pr-2 py-1 text-[11px]" style={{ color: "#f08e8e" }}>
                                  <span>{state.error}</span>
                                  <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); void loadScenariosForProject(project.id); }}
                                    className="self-start rounded px-1.5 py-0.5 text-[10px]"
                                    style={{ background: "#5a1e1e33", border: "1px solid #8b2f2f55", color: "#f0a0a0" }}
                                  >
                                    Retry
                                  </button>
                                </div>
                              ) : filteredScenarios.length === 0 ? (
                                <div className="pl-12 pr-2 py-1 text-[11px]" style={{ color: UI.textFaint }}>
                                  {q ? "no matches" : "empty"}
                                </div>
                              ) : (
                                <>
                                  {/* scenarios folder header */}
                                  <div className="flex items-center gap-1.5 pl-9 pr-2 py-0.5" style={{ color: UI.textMuted }}>
                                    <Chevron expanded />
                                    <FolderIcon open />
                                    <span>scenarios</span>
                                  </div>
                                  {filteredScenarios.map((scenario) => {
                                    const key = tabKey(project.id, scenario.id);
                                    const isActive = key === activeTabKey;
                                    return (
                                      <button
                                        key={scenario.id}
                                        type="button"
                                        onClick={() => openScenario(project, scenario)}
                                        className="flex items-center gap-1.5 pl-[52px] pr-2 py-0.5 text-left transition-colors"
                                        style={{
                                          background: isActive ? UI.selected : "transparent",
                                          color: isActive ? UI.text : UI.text,
                                        }}
                                        onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = UI.rowHover; }}
                                        onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
                                        title={scenario.title}
                                        data-testid={`scenario-ide-scenario-${scenario.id}`}
                                      >
                                        <FileIcon status={scenario.status} />
                                        <span className="truncate">{scenario.title}</span>
                                        <span className="ml-auto font-mono text-[10px]" style={{ color: UI.textFaint }}>
                                          v{scenario.current_version}
                                        </span>
                                      </button>
                                    );
                                  })}
                                </>
                              )}
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </li>
              </ul>
            )}
          </div>
        </aside>

        {/* Editor area */}
        <section className="flex min-w-0 flex-1 flex-col" style={{ background: UI.editor }}>
          {/* Editor tabs */}
          <div
            className="flex h-8 shrink-0 items-stretch overflow-x-auto"
            style={{ background: UI.toolbar, borderBottom: `1px solid ${UI.subtleBorder}` }}
            data-testid="scenario-ide-tabs"
          >
            {openTabs.length === 0 ? (
              <div className="flex items-center px-3 text-[11px]" style={{ color: UI.textFaint }}>
                No open files — double-click a scenario in the Project view
              </div>
            ) : (
              openTabs.map((tab) => {
                const isActive = tab.key === activeTabKey;
                return (
                  <div
                    key={tab.key}
                    className="group relative flex shrink-0 items-center gap-2 border-r px-3 text-[12px]"
                    style={{
                      background: isActive ? UI.tabActive : UI.tabInactive,
                      borderRight: `1px solid ${UI.subtleBorder}`,
                      color: isActive ? UI.text : UI.textMuted,
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setActiveTabKey(tab.key)}
                      className="flex items-center gap-2"
                      data-testid={`scenario-ide-tab-${tab.scenarioId}`}
                    >
                      <FileIcon status="draft" />
                      <span className="max-w-[220px] truncate">{tab.scenarioTitle}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => closeTab(tab.key)}
                      className="flex h-4 w-4 items-center justify-center rounded opacity-0 transition group-hover:opacity-100"
                      style={{ color: UI.textFaint }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "#3c3f41")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      aria-label="Close tab"
                    >
                      <svg viewBox="0 0 16 16" className="h-3 w-3">
                        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                      </svg>
                    </button>
                    {isActive && (
                      <span className="absolute inset-x-0 bottom-0 h-[2px]" style={{ background: UI.accent }} />
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Breadcrumb */}
          {activeTab && <Breadcrumb parts={breadcrumbParts} />}

          {/* Editor content */}
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {!activeTab ? (
              <div className="flex flex-1 items-center justify-center p-8">
                <div className="max-w-md text-center">
                  <pre
                    className="mx-auto mb-4 rounded px-4 py-3 text-left font-mono text-[12px]"
                    style={{ background: UI.panelAlt, border: `1px solid ${UI.border}`, color: UI.textMuted }}
                  >
{`// Welcome to Neurex IDE
// Open a scenario from the Project view on the left
// Tip: press Shift+Shift for Search Everywhere`}
                  </pre>
                  <p className="text-[12px]" style={{ color: UI.textFaint }}>
                    No file opened. Çift tıklayıp senaryoyu editörde aç.
                  </p>
                </div>
              </div>
            ) : activeLoading && !activeDetail ? (
              <div className="flex flex-1 items-center justify-center text-[12px]" style={{ color: UI.textMuted }}>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 animate-spin rounded-full border-2" style={{ borderColor: UI.border, borderTopColor: UI.accent }} />
                  Indexing scenario…
                </div>
              </div>
            ) : activeError ? (
              <div className="m-4 rounded px-3 py-2 text-[12px]" style={{ background: "#5a1e1e33", border: "1px solid #8b2f2f55", color: "#f0a0a0" }}>
                {activeError}
              </div>
            ) : activeDetail ? (
              <div className="flex min-h-0 flex-1 flex-col">
                {/* View mode switcher */}
                <div
                  className="flex h-8 shrink-0 items-center gap-3 px-3 text-[11px]"
                  style={{ background: UI.panelAlt, borderBottom: `1px solid ${UI.subtleBorder}`, color: UI.textMuted }}
                >
                  <div className="flex items-center gap-0 rounded border" style={{ borderColor: UI.border, overflow: "hidden" }}>
                    <button
                      type="button"
                      onClick={() => setViewMode("pretty")}
                      className="px-2 py-1"
                      style={{
                        background: viewMode === "pretty" ? UI.panel : "transparent",
                        color: viewMode === "pretty" ? UI.text : UI.textMuted,
                      }}
                    >
                      Pretty
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewMode("json")}
                      className="px-2 py-1"
                      style={{
                        background: viewMode === "json" ? UI.panel : "transparent",
                        color: viewMode === "json" ? UI.text : UI.textMuted,
                      }}
                    >
                      JSON
                    </button>
                  </div>

                  <span>Status:</span>
                  <span
                    className="inline-flex items-center gap-1 rounded px-1.5 py-0.5"
                    style={{ background: UI.panel, border: `1px solid ${UI.border}`, color: UI.text }}
                  >
                    <span className={cn("h-1.5 w-1.5 rounded-full", STATUS_DOT[activeDetail.status] ?? "bg-slate-400")} />
                    {activeDetail.status}
                  </span>
                  <span>Version:</span>
                  <span
                    className="rounded px-1.5 py-0.5 font-mono"
                    style={{ background: UI.panel, border: `1px solid ${UI.border}`, color: UI.text }}
                  >
                    v{activeDetail.current_version}
                  </span>
                  <span>Steps:</span>
                  <span className="font-mono" style={{ color: UI.text }}>{stepsCount}</span>

                  <div className="ml-auto flex items-center gap-2">
                    <button
                      type="button"
                      onClick={onCopy}
                      className="rounded px-2 py-1"
                      style={{ background: UI.panel, border: `1px solid ${UI.border}`, color: UI.text }}
                    >
                      {copied ? "✓ Copied" : "Copy"}
                    </button>
                    <button
                      type="button"
                      onClick={() => loadDetail(activeTab.projectId, activeTab.scenarioId)}
                      className="rounded px-2 py-1"
                      style={{ background: UI.panel, border: `1px solid ${UI.border}`, color: UI.text }}
                      data-testid="scenario-ide-refresh"
                    >
                      Reload
                    </button>
                    <Link
                      href={`/p/${activeTab.projectId}/scenarios/${activeTab.scenarioId}`}
                      className="rounded px-2 py-1"
                      style={{ background: UI.accent, color: "white" }}
                      data-testid="scenario-ide-open-full"
                    >
                      Open Full Editor
                    </Link>
                  </div>
                </div>

                {/* Content */}
                <div className="flex min-h-0 flex-1 overflow-auto">
                  {viewMode === "json" ? (
                    <div className="flex-1">
                      <CodeBlock text={JSON.stringify(activeDetail, null, 2)} />
                    </div>
                  ) : (
                    <div className="flex-1 overflow-auto px-5 py-4">
                      <h1 className="text-[18px] font-semibold" style={{ color: UI.text }}>
                        {activeDetail.title}
                      </h1>
                      {activeDetail.description && (
                        <p className="mt-2 text-[13px] leading-6" style={{ color: UI.textMuted }}>
                          {activeDetail.description}
                        </p>
                      )}
                      {activeDetail.tags && activeDetail.tags.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {activeDetail.tags.map((t) => (
                            <span
                              key={t}
                              className="rounded px-1.5 py-0.5 text-[10px]"
                              style={{ background: UI.panelAlt, border: `1px solid ${UI.border}`, color: UI.textMuted }}
                            >
                              @{t}
                            </span>
                          ))}
                        </div>
                      )}

                      <div className="mt-5">
                        <div
                          className="flex items-center justify-between rounded-t border-b-0 px-3 py-1.5 text-[11px] uppercase tracking-wide"
                          style={{ background: UI.panelAlt, border: `1px solid ${UI.border}`, color: UI.textMuted }}
                        >
                          <span>Steps ({stepsCount})</span>
                          <span className="font-mono" style={{ color: UI.textFaint }}>scenario.gherkin</span>
                        </div>
                        <div
                          className="rounded-b font-mono text-[12.5px] leading-[1.6]"
                          style={{ background: UI.editor, border: `1px solid ${UI.border}`, borderTop: 0 }}
                        >
                          {stepsCount === 0 ? (
                            <div className="px-4 py-3" style={{ color: UI.textFaint }}>{"// no steps defined"}</div>
                          ) : (
                            <ol>
                              {activeDetail.steps!.map((step, i) => {
                                const s = step as Record<string, unknown>;
                                const kw = typeof s.keyword === "string" ? s.keyword : "Step";
                                const txt = typeof s.text === "string" ? s.text : JSON.stringify(step);
                                return (
                                  <li
                                    key={i}
                                    className="flex gap-0 border-b last:border-b-0"
                                    style={{ borderColor: UI.subtleBorder }}
                                  >
                                    <span
                                      className="shrink-0 select-none border-r px-3 py-1.5 text-right"
                                      style={{
                                        minWidth: 44,
                                        color: UI.textFaint,
                                        background: UI.editorGutter,
                                        borderColor: UI.subtleBorder,
                                      }}
                                    >
                                      {String(i + 1).padStart(2, "0")}
                                    </span>
                                    <div className="flex min-w-0 flex-1 items-start gap-2 px-3 py-1.5">
                                      <span style={{ color: UI.keyword }}>{kw}</span>
                                      <span style={{ color: UI.text }}>{txt}</span>
                                    </div>
                                  </li>
                                );
                              })}
                            </ol>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </section>
      </div>

      {/* Status bar */}
      <div
        className="flex h-6 shrink-0 items-center gap-3 px-3 text-[11px]"
        style={{ background: UI.toolbar, borderTop: `1px solid ${UI.subtleBorder}`, color: UI.textMuted }}
      >
        <span className="inline-flex items-center gap-1">
          <svg viewBox="0 0 16 16" className="h-3 w-3" style={{ color: UI.textFaint }}>
            <path d="M2 4h12v8H2z" fill="none" stroke="currentColor" strokeWidth="1.3" />
            <path d="M2 7h12" stroke="currentColor" strokeWidth="1.3" />
          </svg>
          {projects.length} modules
        </span>
        <span>·</span>
        <span>{totalLoadedScenarios} scenarios indexed</span>
        <span>·</span>
        <span>
          {openTabs.length} open file{openTabs.length === 1 ? "" : "s"}
        </span>
        <div className="ml-auto flex items-center gap-3">
          {activeDetail && (
            <>
              <span className="font-mono">{stepsCount} steps</span>
              <span>·</span>
            </>
          )}
          <span>UTF-8</span>
          <span>·</span>
          <span>LF</span>
          <span>·</span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Ready
          </span>
        </div>
      </div>
    </div>
  );
}
