"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { ProjectFileTree } from "./components/ProjectFileTree";
import { ScenarioEditorPanel } from "./components/ScenarioEditorPanel";

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

function tabKey(projectId: string, scenarioId: string) {
  return `${projectId}::${scenarioId}`;
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

        {/* Project tool window — extracted to ProjectFileTree */}
        <ProjectFileTree
          projects={projects}
          projectsLoading={projectsLoading}
          projectsError={projectsError}
          scenariosByProject={scenariosByProject}
          expanded={expanded}
          activeTabKey={activeTabKey}
          search={search}
          filteredProjects={filteredProjects}
          totalLoadedScenarios={totalLoadedScenarios}
          onToggleProject={toggleProject}
          onOpenScenario={openScenario}
          onExpandAll={expandAll}
          onCollapseAll={collapseAll}
          onRetryLoadScenarios={(id) => void loadScenariosForProject(id)}
        />
        {/* LEGACY aside removed — ProjectFileTree verified */}

        {/* Editor area — extracted to ScenarioEditorPanel */}
        <ScenarioEditorPanel
          openTabs={openTabs}
          activeTabKey={activeTabKey}
          activeTab={activeTab}
          activeDetail={activeDetail}
          activeLoading={activeLoading}
          activeError={activeError}
          viewMode={viewMode}
          copied={copied}
          stepsCount={stepsCount}
          breadcrumbParts={breadcrumbParts}
          onTabClick={setActiveTabKey}
          onTabClose={closeTab}
          onViewModeChange={setViewMode}
          onCopy={onCopy}
          onReload={loadDetail}
        />
        {/* LEGACY section kept below for reference — remove after verifying ScenarioEditorPanel renders correctly */}
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
