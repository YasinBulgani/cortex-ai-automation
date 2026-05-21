"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import {
  type Widget,
  type WidgetType,
  useCustomDashboard,
} from "@/lib/useCustomDashboard";

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
}: {
  widget: Widget;
  onRemove: () => void;
  onUpdate: (patch: Partial<Widget>) => void;
}) {
  const renderBody = () => {
    switch (widget.type) {
      case "pass-rate":
        return <div className="text-3xl font-bold text-emerald-400">98.7%</div>;
      case "execution-count":
        return <div className="text-3xl font-bold text-sky-400">147</div>;
      case "flaky-trend":
        return (
          <div className="text-xs text-slate-400">
            <p>Flaky test trend: ↓ %12 (son 7 gün)</p>
            <p className="mt-1 text-[10px]">Grafik için backend metrics endpoint'i.</p>
          </div>
        );
      case "failure-density":
        return (
          <div className="text-xs text-slate-400">
            <p>Hata yoğunluk haritası</p>
            <p className="mt-1 text-[10px]">Modül × test türü matrix.</p>
          </div>
        );
      case "ai-cost":
        return <div className="text-xl font-bold text-amber-400">$42.18</div>;
      case "test-coverage":
        return <div className="text-3xl font-bold text-indigo-400">87%</div>;
      case "recent-runs":
        return (
          <ul className="text-xs text-slate-400 space-y-1">
            <li>✓ Login flow — 2dk önce</li>
            <li>✗ Payment edge — 5dk önce</li>
            <li>✓ Logout — 7dk önce</li>
          </ul>
        );
      case "active-incidents":
        return <div className="text-2xl font-bold text-red-400">0</div>;
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

export default function CustomDashboardsPage() {
  const projectId = useRouteParam("projectId");
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
  } = useCustomDashboard(projectId);

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
              Kendi metriklerini ve widget'larını düzenle. localStorage'da saklanır.
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
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
