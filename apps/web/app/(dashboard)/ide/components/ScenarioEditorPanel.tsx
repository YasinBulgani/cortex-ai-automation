"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

// ── Palette (must match page.tsx UI object) ──────────────────────────

const UI = {
  frame: "#1e1f22",
  toolbar: "#2b2d30",
  panel: "#2b2d30",
  panelAlt: "#25272b",
  editor: "#1e1f22",
  editorGutter: "#1e1f22",
  border: "#393b40",
  subtleBorder: "#303236",
  text: "#dfe1e5",
  textMuted: "#9da0a8",
  textFaint: "#6f737a",
  accent: "#3574f0",
  keyword: "#cf8e6d",
  stringLit: "#6aab73",
  numberLit: "#2aacb8",
  propKey: "#c77dbb",
  tabActive: "#2d5a8e",
};

const STATUS_DOT: Record<string, string> = {
  active: "bg-emerald-400",
  draft: "bg-slate-400",
  archived: "bg-red-400",
};

// ── Inline helpers ───────────────────────────────────────────────────

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
        <code
          dangerouslySetInnerHTML={{
            __html: (() => {
              try {
                return highlightJson(JSON.parse(text));
              } catch {
                return `<span style="color:#f87171">[Geçersiz JSON]</span>\n${text
                  .replace(/&/g, "&amp;")
                  .replace(/</g, "&lt;")
                  .replace(/>/g, "&gt;")}`;
              }
            })(),
          }}
        />
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

// ── Types ────────────────────────────────────────────────────────────

export type ScenarioDetail = {
  id: string;
  title: string;
  description?: string;
  status: string;
  current_version: number;
  steps?: Record<string, unknown>[];
  tags?: string[];
  updated_at?: string | null;
};

export type OpenTab = {
  key: string;
  projectId: string;
  projectName: string;
  scenarioId: string;
  scenarioTitle: string;
};

export type ViewMode = "pretty" | "json";

// ── Props ────────────────────────────────────────────────────────────

export interface ScenarioEditorPanelProps {
  openTabs: OpenTab[];
  activeTabKey: string | null;
  activeTab: OpenTab | null;
  activeDetail: ScenarioDetail | null;
  activeLoading: boolean;
  activeError: string | null;
  viewMode: ViewMode;
  copied: boolean;
  stepsCount: number;
  breadcrumbParts: string[];
  onTabClick: (key: string) => void;
  onTabClose: (key: string) => void;
  onViewModeChange: (mode: ViewMode) => void;
  onCopy: () => void;
  onReload: (projectId: string, scenarioId: string) => void;
}

// ── Component ────────────────────────────────────────────────────────

export function ScenarioEditorPanel({
  openTabs,
  activeTabKey,
  activeTab,
  activeDetail,
  activeLoading,
  activeError,
  viewMode,
  copied,
  stepsCount,
  breadcrumbParts,
  onTabClick,
  onTabClose,
  onViewModeChange,
  onCopy,
  onReload,
}: ScenarioEditorPanelProps) {
  return (
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
                  background: isActive ? UI.tabActive : UI.toolbar,
                  borderRight: `1px solid ${UI.subtleBorder}`,
                  color: isActive ? UI.text : UI.textMuted,
                }}
              >
                <button
                  type="button"
                  onClick={() => onTabClick(tab.key)}
                  className="flex items-center gap-2"
                  data-testid={`scenario-ide-tab-${tab.scenarioId}`}
                >
                  {/* FileIcon inline to avoid cross-component import */}
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
                  </span>
                  <span className="max-w-[220px] truncate">{tab.scenarioTitle}</span>
                </button>
                <button
                  type="button"
                  onClick={() => onTabClose(tab.key)}
                  className="flex h-4 w-4 items-center justify-center rounded opacity-0 transition group-hover:opacity-100"
                  style={{ color: UI.textFaint }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#3c3f41")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  aria-label="Close tab"
                >
                  <svg viewBox="0 0 16 16" className="h-3 w-3">
                    <path
                      d="M4 4l8 8M12 4l-8 8"
                      stroke="currentColor"
                      strokeWidth="1.4"
                      strokeLinecap="round"
                    />
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
                {`// Welcome to Neurex IDE\n// Open a scenario from the Project view on the left\n// Tip: press Shift+Shift for Search Everywhere`}
              </pre>
              <p className="text-[12px]" style={{ color: UI.textFaint }}>
                No file opened. Çift tıklayıp senaryoyu editörde aç.
              </p>
            </div>
          </div>
        ) : activeLoading && !activeDetail ? (
          <div
            className="flex flex-1 items-center justify-center text-[12px]"
            style={{ color: UI.textMuted }}
          >
            <div className="flex items-center gap-2">
              <div
                className="h-3 w-3 animate-spin rounded-full border-2"
                style={{ borderColor: UI.border, borderTopColor: UI.accent }}
              />
              Indexing scenario…
            </div>
          </div>
        ) : activeError ? (
          <div
            className="m-4 rounded px-3 py-2 text-[12px]"
            style={{ background: "#5a1e1e33", border: "1px solid #8b2f2f55", color: "#f0a0a0" }}
          >
            {activeError}
          </div>
        ) : activeDetail ? (
          <div className="flex min-h-0 flex-1 flex-col">
            {/* View mode switcher */}
            <div
              className="flex h-8 shrink-0 items-center gap-3 px-3 text-[11px]"
              style={{
                background: UI.panelAlt,
                borderBottom: `1px solid ${UI.subtleBorder}`,
                color: UI.textMuted,
              }}
            >
              <div
                className="flex items-center gap-0 rounded border"
                style={{ borderColor: UI.border, overflow: "hidden" }}
              >
                <button
                  type="button"
                  onClick={() => onViewModeChange("pretty")}
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
                  onClick={() => onViewModeChange("json")}
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
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    STATUS_DOT[activeDetail.status] ?? "bg-slate-400",
                  )}
                />
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
              <span className="font-mono" style={{ color: UI.text }}>
                {stepsCount}
              </span>

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
                  onClick={() => onReload(activeTab.projectId, activeTab.scenarioId)}
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
                    <p
                      className="mt-2 text-[13px] leading-6"
                      style={{ color: UI.textMuted }}
                    >
                      {activeDetail.description}
                    </p>
                  )}
                  {activeDetail.tags && activeDetail.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {activeDetail.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded px-1.5 py-0.5 text-[10px]"
                          style={{
                            background: UI.panelAlt,
                            border: `1px solid ${UI.border}`,
                            color: UI.textMuted,
                          }}
                        >
                          @{t}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-5">
                    <div
                      className="flex items-center justify-between rounded-t border-b-0 px-3 py-1.5 text-[11px] uppercase tracking-wide"
                      style={{
                        background: UI.panelAlt,
                        border: `1px solid ${UI.border}`,
                        color: UI.textMuted,
                      }}
                    >
                      <span>Steps ({stepsCount})</span>
                      <span className="font-mono" style={{ color: UI.textFaint }}>
                        scenario.gherkin
                      </span>
                    </div>
                    <div
                      className="rounded-b font-mono text-[12.5px] leading-[1.6]"
                      style={{
                        background: UI.editor,
                        border: `1px solid ${UI.border}`,
                        borderTop: 0,
                      }}
                    >
                      {stepsCount === 0 ? (
                        <div className="px-4 py-3" style={{ color: UI.textFaint }}>
                          {"// no steps defined"}
                        </div>
                      ) : (
                        <ol>
                          {activeDetail.steps!.map((step, i) => {
                            const s = step as Record<string, unknown>;
                            const kw =
                              typeof s.keyword === "string" ? s.keyword : "Step";
                            const txt =
                              typeof s.text === "string"
                                ? s.text
                                : JSON.stringify(step);
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
  );
}
