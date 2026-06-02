"use client";

import { cn } from "@/lib/utils";

// ── Palette (must match page.tsx UI object) ──────────────────────────

const UI = {
  frame: "#1e1f22",
  toolbar: "#2b2d30",
  panel: "#2b2d30",
  panelAlt: "#25272b",
  editor: "#1e1f22",
  rowHover: "#2e436e33",
  selected: "#2e436eaa",
  tabActive: "#1e1f22",
  border: "#393b40",
  subtleBorder: "#303236",
  text: "#dfe1e5",
  textMuted: "#9da0a8",
  textFaint: "#6f737a",
  accent: "#3574f0",
  accentSoft: "#3574f033",
};

const STATUS_DOT: Record<string, string> = {
  active: "bg-emerald-400",
  draft: "bg-slate-400",
  archived: "bg-red-400",
};

// ── Shared icon sub-components ───────────────────────────────────────

export function FileIcon({ status }: { status?: string }) {
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

export function FolderIcon({ open }: { open: boolean }) {
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

export function Chevron({ expanded }: { expanded: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={cn("h-3 w-3 shrink-0 transition-transform duration-100", expanded ? "rotate-90" : "")}
      style={{ color: UI.textFaint }}
    >
      <path
        d="M6 4l4 4-4 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ── Types ────────────────────────────────────────────────────────────

export type Scenario = {
  id: string;
  title: string;
  status: string;
  current_version: number;
  updated_at?: string | null;
  tags?: string[];
};

export type Project = { id: string; name: string; description?: string; archived?: boolean };

export type ProjectScenariosState = {
  loading: boolean;
  error: string | null;
  items: Scenario[] | null;
};

// ── Props ────────────────────────────────────────────────────────────

export interface ProjectFileTreeProps {
  projects: Project[];
  projectsLoading: boolean;
  projectsError: string | null;
  scenariosByProject: Record<string, ProjectScenariosState>;
  expanded: Set<string>;
  activeTabKey: string | null;
  search: string;
  filteredProjects: Project[];
  totalLoadedScenarios: number;
  onToggleProject: (projectId: string) => void;
  onOpenScenario: (project: Project, scenario: Scenario) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onRetryLoadScenarios: (projectId: string) => void;
}

// ── Helpers ──────────────────────────────────────────────────────────

function tabKey(projectId: string, scenarioId: string) {
  return `${projectId}::${scenarioId}`;
}

// ── Component ────────────────────────────────────────────────────────

export function ProjectFileTree({
  projects,
  projectsLoading,
  projectsError,
  scenariosByProject,
  expanded,
  activeTabKey,
  search,
  filteredProjects,
  totalLoadedScenarios,
  onToggleProject,
  onOpenScenario,
  onExpandAll,
  onCollapseAll,
  onRetryLoadScenarios,
}: ProjectFileTreeProps) {
  return (
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
            onClick={onExpandAll}
            title="Expand All"
            className="flex h-5 w-5 items-center justify-center rounded"
            style={{ color: UI.textFaint }}
            data-testid="scenario-ide-expand-all"
          >
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5">
              <path d="M4 4h8M4 8h8M4 12h8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
          </button>
          <button
            type="button"
            onClick={onCollapseAll}
            title="Collapse All"
            className="flex h-5 w-5 items-center justify-center rounded"
            style={{ color: UI.textFaint }}
            data-testid="scenario-ide-collapse-all"
          >
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5">
              <path d="M3 8h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tree */}
      <div
        className="flex-1 overflow-y-auto py-1 text-[12.5px]"
        style={{ fontFamily: "ui-sans-serif, system-ui" }}
      >
        {projectsLoading ? (
          <div className="flex items-center gap-2 px-3 py-2 text-[11px]" style={{ color: UI.textFaint }}>
            <div
              className="h-3 w-3 animate-spin rounded-full border-2"
              style={{ borderColor: UI.border, borderTopColor: UI.accent }}
            />
            Indexing projects...
          </div>
        ) : projectsError ? (
          <div
            className="mx-2 rounded px-2 py-1 text-[11px]"
            style={{ background: "#5a1e1e33", color: "#f08e8e", border: "1px solid #8b2f2f55" }}
          >
            {projectsError}
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="px-3 py-2 text-[11px]" style={{ color: UI.textFaint }}>
            Hiç proje yok.
          </div>
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
                        onClick={() => onToggleProject(project.id)}
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
                            <div
                              className="flex items-center gap-2 pl-12 pr-2 py-1 text-[11px]"
                              style={{ color: UI.textFaint }}
                            >
                              <div
                                className="h-3 w-3 animate-spin rounded-full border-2"
                                style={{ borderColor: UI.border, borderTopColor: UI.accent }}
                              />
                              Loading…
                            </div>
                          ) : state?.error ? (
                            <div
                              className="flex flex-col gap-1 pl-12 pr-2 py-1 text-[11px]"
                              style={{ color: "#f08e8e" }}
                            >
                              <span>{state.error}</span>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onRetryLoadScenarios(project.id);
                                }}
                                className="self-start rounded px-1.5 py-0.5 text-[10px]"
                                style={{
                                  background: "#5a1e1e33",
                                  border: "1px solid #8b2f2f55",
                                  color: "#f0a0a0",
                                }}
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
                              <div
                                className="flex items-center gap-1.5 pl-9 pr-2 py-0.5"
                                style={{ color: UI.textMuted }}
                              >
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
                                    onClick={() => onOpenScenario(project, scenario)}
                                    className="flex items-center gap-1.5 pl-[52px] pr-2 py-0.5 text-left transition-colors"
                                    style={{
                                      background: isActive ? UI.selected : "transparent",
                                      color: UI.text,
                                    }}
                                    onMouseEnter={(e) => {
                                      if (!isActive) e.currentTarget.style.background = UI.rowHover;
                                    }}
                                    onMouseLeave={(e) => {
                                      if (!isActive) e.currentTarget.style.background = "transparent";
                                    }}
                                    title={scenario.title}
                                    data-testid={`scenario-ide-scenario-${scenario.id}`}
                                  >
                                    <FileIcon status={scenario.status} />
                                    <span className="truncate">{scenario.title}</span>
                                    <span
                                      className="ml-auto font-mono text-[10px]"
                                      style={{ color: UI.textFaint }}
                                    >
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

      {/* Status bar summary */}
      <div
        className="flex h-6 shrink-0 items-center gap-2 px-3 text-[10px]"
        style={{ background: UI.toolbar, borderTop: `1px solid ${UI.subtleBorder}`, color: UI.textFaint }}
      >
        <span>{projects.length} modules</span>
        <span>·</span>
        <span>{totalLoadedScenarios} scenarios</span>
      </div>
    </aside>
  );
}
