"use client";

import { useMemo, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import {
  type Widget,
  type WidgetType,
  useCustomDashboard,
} from "@/lib/useCustomDashboard";
import {
  useExecutionSummary,
  useManagementRuns,
  useManagementDefects,
} from "@/lib/hooks/use-management";
import { useFlakyTrends } from "@/lib/hooks/use-api-testing";
import { useLlmTraceStats } from "@/lib/hooks/use-ai-metrics";

type LiveData = {
  passRate: number | null;
  executionCount: number | null;
  flakyDelta: number | null;
  aiCostUsd: number | null;
  testCoverage: number | null;
  recentRuns: Array<{ name: string; status: string; relTime: string }>;
  openIncidents: number | null;
};

const WIDGET_LIBRARY: { type: WidgetType; label: string; defaultSize: { w: number; h: number } }[] = [
  { type: "pass-rate", label: "Pass Rate", defaultSize: { w: 1, h: 1 } },
  { type: "execution-count", label: "Koşum Sayısı", defaultSize: { w: 1, h: 1 } },
  { type: "flaky-trend", label: "Flaky Trend", defaultSize: { w: 2, h: 1 } },
  { type: "failure-density", label: "Hata Yoğunluğu", defaultSize: { w: 2, h: 2 } },
  { type: "ai-cost", label: "AI Maliyet", defaultSize: { w: 1, h: 1 } },
  { type: "test-coverage", label: "Test Kapsama", defaultSize: { w: 1, h: 1 } },
  { type: "recent-runs", label: "Son Koşumlar", defaultSize: { w: 2, h: 2 } },
  { type: "active-incidents", label: "Aktif Olaylar", defaultSize: { w: 1, h: 1 } },
  { type: "custom-text", label: "Özel Metin", defaultSize: { w: 1, h: 1 } },
];

function WidgetCard({
  widget,
  onRemove,
  onUpdate,
  live,
}: {
  widget: Widget;
  onRemove: () => void;
  onUpdate: (patch: Partial<Widget>) => void;
  live: LiveData;
}) {
  const renderBody = () => {
    switch (widget.type) {
      case "pass-rate":
        return live.passRate === null ? (
          <div className="text-3xl font-bold text-slate-600 animate-pulse">—</div>
        ) : (
          <div className={`text-3xl font-bold ${live.passRate >= 80 ? "text-emerald-400" : live.passRate >= 60 ? "text-amber-400" : "text-red-400"}`}>
            {live.passRate.toFixed(1)}%
          </div>
        );
      case "execution-count":
        return live.executionCount === null ? (
          <div className="text-3xl font-bold text-slate-600 animate-pulse">—</div>
        ) : (
          <div className="text-3xl font-bold text-sky-400">{live.executionCount}</div>
        );
      case "flaky-trend":
        return (
          <div className="text-xs text-slate-400">
            {live.flakyDelta === null ? (
              <p className="animate-pulse">Yükleniyor…</p>
            ) : (
              <p>
                Flaky test trendi:{" "}
                <span className={live.flakyDelta <= 0 ? "text-emerald-400" : "text-red-400"}>
                  {live.flakyDelta > 0 ? "↑" : "↓"} {Math.abs(live.flakyDelta)}%
                </span>{" "}
                (son 7 gün)
              </p>
            )}
          </div>
        );
      case "failure-density":
        return (
          <div className="text-xs text-slate-400">
            <p>Hata yoğunluk haritası</p>
            {live.passRate !== null && (
              <p className="mt-1 text-[10px]">Başarısızlık oranı: {(100 - live.passRate).toFixed(1)}%</p>
            )}
          </div>
        );
      case "ai-cost":
        return live.aiCostUsd === null ? (
          <div className="text-xl font-bold text-slate-600 animate-pulse">—</div>
        ) : (
          <div className="text-xl font-bold text-amber-400">${live.aiCostUsd.toFixed(2)}</div>
        );
      case "test-coverage":
        return live.testCoverage === null ? (
          <div className="text-3xl font-bold text-slate-600 animate-pulse">—</div>
        ) : (
          <div className={`text-3xl font-bold ${live.testCoverage >= 80 ? "text-indigo-400" : live.testCoverage >= 60 ? "text-amber-400" : "text-red-400"}`}>
            {live.testCoverage.toFixed(0)}%
          </div>
        );
      case "recent-runs":
        return live.recentRuns.length === 0 ? (
          <p className="text-xs text-slate-600 animate-pulse">Yükleniyor…</p>
        ) : (
          <ul className="text-xs text-slate-400 space-y-1">
            {live.recentRuns.slice(0, 4).map((r, i) => (
              <li key={i} className="truncate">
                <span className={r.status === "passed" ? "text-emerald-400" : r.status === "failed" ? "text-red-400" : "text-slate-500"}>
                  {r.status === "passed" ? "✓" : r.status === "failed" ? "✗" : "○"}
                </span>{" "}
                {r.name} — <span className="text-slate-500">{r.relTime}</span>
              </li>
            ))}
          </ul>
        );
      case "active-incidents":
        return live.openIncidents === null ? (
          <div className="text-2xl font-bold text-slate-600 animate-pulse">—</div>
        ) : (
          <div className={`text-2xl font-bold ${live.openIncidents === 0 ? "text-emerald-400" : "text-red-400"}`}>
            {live.openIncidents}
          </div>
        );
      case "custom-text":
        return (
          <textarea
            className="h-full w-full resize-none border-0 bg-transparent text-xs text-slate-300 focus:outline-none"
            placeholder="Notlarınızı buraya yazın…"
            value={String(widget.config?.text ?? "")}
            onChange={(e) =>
              onUpdate({ config: { ...widget.config, text: e.target.value } })
            }
          />
        );
      default:
        return <div className="text-xs text-slate-500">Bilinmeyen widget</div>;
    }
  };

  return (
    <div
      className="relative rounded-xl border border-slate-800 bg-slate-900/50 p-4"
      style={{ gridColumn: `span ${widget.w}`, gridRow: `span ${widget.h}` }}
      data-testid={`widget-${widget.id}`}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {widget.title}
        </h3>
        <button
          type="button"
          onClick={onRemove}
          className="text-slate-600 hover:text-red-400"
          aria-label="Widget'ı kaldır"
          data-testid={`widget-remove-${widget.id}`}
        >
          ×
        </button>
      </div>
      <div className="mt-2 min-h-[40px]">{renderBody()}</div>
    </div>
  );
}

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "az önce";
  if (mins < 60) return `${mins}dk önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}sa önce`;
  return `${Math.floor(hrs / 24)}g önce`;
}

export default function CustomDashboardsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);
  const {
    dashboards,
    active,
    activeId,
    setActiveId,
    createDashboard,
    deleteDashboard,
    renameDashboard,
    addWidget,
    removeWidget,
    updateWidget,
  } = useCustomDashboard(projectId ?? "", mpid);

  const { data: summary }  = useExecutionSummary(mpid || undefined);
  const { data: runs }     = useManagementRuns(mpid || undefined);
  const { data: defects }  = useManagementDefects(mpid || undefined);
  const { data: flaky }    = useFlakyTrends(mpid || undefined, 7);
  const { data: aiStats }  = useLlmTraceStats(mpid || undefined);

  const live = useMemo<LiveData>(() => {
    const openDefects = (defects ?? []).filter(
      (d) => !["closed", "resolved", "fixed", "done"].includes(d.status.toLowerCase()),
    ).length;

    const recentRuns = (runs ?? [])
      .slice(0, 4)
      .map((r) => ({
        name: r.name,
        status: r.status,
        relTime: relativeTime(r.created_at ?? r.started_at ?? new Date().toISOString()),
      }));

    const flakyDelta = flaky && flaky.length >= 2
      ? Math.round(flaky[flaky.length - 1].flaky_count - flaky[0].flaky_count)
      : null;

    return {
      passRate: summary?.pass_rate_pct ?? null,
      executionCount: runs?.length ?? null,
      flakyDelta,
      aiCostUsd: (aiStats as { total_cost_usd?: number } | undefined)?.total_cost_usd ?? null,
      testCoverage: (summary as { requirement_coverage_pct?: number } | undefined)?.requirement_coverage_pct ?? null,
      recentRuns,
      openIncidents: defects ? openDefects : null,
    };
  }, [summary, runs, defects, flaky, aiStats]);

  const [newName, setNewName] = useState("");
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");

  const handleCreate = () => {
    const name = newName.trim();
    if (!name) return;
    createDashboard(name);
    setNewName("");
  };

  const handleRename = () => {
    if (!active) return;
    const name = renameValue.trim();
    if (!name) {
      setRenaming(false);
      return;
    }
    renameDashboard(active.id, name);
    setRenaming(false);
  };

  return (
    <div
      className="flex h-full flex-col bg-slate-950 text-slate-100"
      data-testid="custom-dashboards-page"
    >
      {/* Header */}
      <div className="border-b border-slate-800 px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              📊 Özel Dashboard'lar
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Kendi metriklerini ve widget'larını düzenle. Backend ile senkronize edilir, offline cache korunur.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              placeholder="Yeni dashboard adı…"
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
              data-testid="dashboard-new-name-input"
            />
            <button
              type="button"
              onClick={handleCreate}
              disabled={!newName.trim()}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
              data-testid="dashboard-create-btn"
            >
              + Oluştur
            </button>
          </div>
        </div>

        {dashboards.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2" data-testid="dashboard-tabs">
            {dashboards.map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => setActiveId(d.id)}
                className={`rounded-lg px-3 py-1 text-xs ${
                  activeId === d.id
                    ? "bg-indigo-600 text-white"
                    : "border border-slate-700 text-slate-400 hover:bg-slate-800"
                }`}
                data-testid={`dashboard-tab-${d.id}`}
              >
                {d.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Empty state */}
      {dashboards.length === 0 && (
        <div
          className="flex flex-1 items-center justify-center"
          data-testid="dashboard-empty"
        >
          <div className="text-center">
            <div className="text-5xl">📊</div>
            <h2 className="mt-3 text-lg font-semibold">Henüz dashboard yok</h2>
            <p className="mt-1 text-sm text-slate-500">
              Yukarıdan bir isim girip "Oluştur"a bas.
            </p>
          </div>
        </div>
      )}

      {/* Active dashboard */}
      {active && (
        <div className="flex-1 overflow-auto p-6">
          <div className="mb-4 flex items-center justify-between">
            {renaming ? (
              <div className="flex items-center gap-2">
                <input
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleRename()}
                  className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm"
                  autoFocus
                  data-testid="dashboard-rename-input"
                />
                <button
                  type="button"
                  onClick={handleRename}
                  className="rounded bg-indigo-600 px-3 py-1 text-xs text-white"
                >
                  ✓
                </button>
                <button
                  type="button"
                  onClick={() => setRenaming(false)}
                  className="rounded border border-slate-700 px-3 py-1 text-xs text-slate-400"
                >
                  ×
                </button>
              </div>
            ) : (
              <h2
                className="text-base font-semibold cursor-pointer hover:underline"
                onClick={() => {
                  setRenameValue(active.name);
                  setRenaming(true);
                }}
                data-testid="dashboard-name"
              >
                {active.name}
              </h2>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowAddPanel((v) => !v)}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs hover:bg-slate-800"
                data-testid="dashboard-add-widget-btn"
              >
                + Widget Ekle
              </button>
              <button
                type="button"
                onClick={() => {
                  if (confirm(`"${active.name}" dashboard silinsin mi?`)) {
                    deleteDashboard(active.id);
                  }
                }}
                className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10"
                data-testid="dashboard-delete-btn"
              >
                Sil
              </button>
            </div>
          </div>

          {showAddPanel && (
            <div
              className="mb-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4"
              data-testid="widget-library"
            >
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                Widget Kütüphanesi
              </h3>
              <div className="flex flex-wrap gap-2">
                {WIDGET_LIBRARY.map((lib) => (
                  <button
                    key={lib.type}
                    type="button"
                    onClick={() => {
                      addWidget(active.id, {
                        type: lib.type,
                        title: lib.label,
                        x: 0,
                        y: 0,
                        w: lib.defaultSize.w,
                        h: lib.defaultSize.h,
                      });
                      setShowAddPanel(false);
                    }}
                    className="rounded-lg border border-slate-700 px-3 py-2 text-xs hover:bg-slate-800"
                    data-testid={`widget-add-${lib.type}`}
                  >
                    + {lib.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {active.widgets.length === 0 ? (
            <div
              className="rounded-xl border border-dashed border-slate-700 p-12 text-center"
              data-testid="dashboard-no-widgets"
            >
              <p className="text-sm text-slate-500">
                Henüz widget yok. "+ Widget Ekle" ile kütüphaneden seç.
              </p>
            </div>
          ) : (
            <div
              className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
              data-testid="dashboard-grid"
            >
              {active.widgets.map((w) => (
                <WidgetCard
                  key={w.id}
                  widget={w}
                  onRemove={() => removeWidget(active.id, w.id)}
                  onUpdate={(patch) => updateWidget(active.id, w.id, patch)}
                  live={live}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
