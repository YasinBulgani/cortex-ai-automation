"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor,
  useSensor, useSensors, DragEndEvent, DragStartEvent, DragOverlay,
} from "@dnd-kit/core";
import {
  arrayMove, SortableContext, sortableKeyboardCoordinates,
  verticalListSortingStrategy, useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { FlowGuideCard } from "@/components/FlowGuideCard";
import {
  PageHeader,
  SectionCard,
  EmptyState,
  StatCard,
  MetricRow,
} from "@/components/nexus";
import { ServiceTestingGuide } from "@/components/ServiceTestingGuide";
import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";

type Collection = { id: string; name: string; base_url: string };
type ApiRequest = { id: string; name: string; method: string; path: string };
type RunResult = {
  name: string;
  status_code: number;
  passed: boolean;
  duration_ms: number;
  response_body?: string;
  error?: string;
};
type Run = { id: string; collection_id: string; results: RunResult[]; created_at: string | null };

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
  POST: "bg-blue-500/10 border-blue-500/20 text-blue-400",
  PUT: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  DELETE: "bg-red-500/10 border-red-500/20 text-red-400",
  PATCH: "bg-violet-500/10 border-violet-500/20 text-violet-400",
};

function statusCodeColor(code: number): string {
  if (code >= 500) return "bg-red-500/10 border-red-500/20 text-red-400";
  if (code >= 400) return "bg-amber-500/10 border-amber-500/20 text-amber-400";
  if (code >= 200) return "bg-emerald-500/10 border-emerald-500/20 text-emerald-400";
  return "bg-slate-800 border-slate-700 text-slate-400";
}

function SortableRequestRow({ request }: { request: ApiRequest }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: request.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };
  return (
    <tr ref={setNodeRef} style={style} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
      <td className="w-10 px-4 py-3">
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab text-slate-600 hover:text-slate-400 active:cursor-grabbing"
          aria-label="Sırala"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
          </svg>
        </button>
      </td>
      <td className="px-4 py-3 text-sm font-medium text-white">{request.name}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-bold font-mono ${METHOD_COLORS[request.method] ?? ""}`}>
          {request.method}
        </span>
      </td>
      <td className="px-4 py-3 font-mono text-xs text-slate-400">{request.path}</td>
    </tr>
  );
}

export default function ApiTestsPage() {
  const projectId = useRouteParam("projectId");
  const basePath = `/api/v1/tspm/projects/${projectId}/api-tests`;

  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [requests, setRequests] = useState<ApiRequest[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [runResults, setRunResults] = useState<RunResult[] | null>(null);
  const [running, setRunning] = useState(false);

  const [newCol, setNewCol] = useState({ name: "", base_url: "" });
  const [showColForm, setShowColForm] = useState(false);

  const [workspaceMode, setWorkspaceMode] = useState<"setup" | "run" | "results">("setup");
  const [showReqForm, setShowReqForm] = useState(false);
  const [newReq, setNewReq] = useState({ name: "", method: "GET", path: "", body: "", assertions: "" });
  const [activeRequest, setActiveRequest] = useState<ApiRequest | null>(null);

  const latestRun = runs.length > 0 ? runs[0] : null;

  const stageCards = [
    { id: "setup" as const, label: "1. Kurulum", title: "Koleksiyon ve İstekleri Ayarla", meta: `${requests.length} istek` },
    { id: "run" as const, label: "2. Çalıştır", title: "Koleksiyonu Çalıştır", meta: running ? "Çalışıyor…" : "Hazır" },
    { id: "results" as const, label: "3. Sonuçlar", title: "Koşu Sonuçlarını İncele", meta: runResults ? `${runResults.filter(r => r.passed).length}/${runResults.length}` : "—" },
  ];

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragStart(event: DragStartEvent) {
    const req = requests.find(r => r.id === event.active.id);
    setActiveRequest(req ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveRequest(null);
    const { active, over } = event;
    if (over && active.id !== over.id) {
      setRequests(prev => {
        const oldIndex = prev.findIndex(r => r.id === active.id);
        const newIndex = prev.findIndex(r => r.id === over.id);
        return arrayMove(prev, oldIndex, newIndex);
      });
    }
  }

  const loadCollections = useCallback(() => {
    apiFetch<Collection[]>(`${basePath}/collections`).then(setCollections).catch(() => {});
  }, [basePath]);

  const loadRequests = useCallback((cid: string) => {
    apiFetch<ApiRequest[]>(`${basePath}/collections/${cid}/requests`).then(setRequests).catch(() => {});
  }, [basePath]);

  const loadRuns = useCallback(() => {
    apiFetch<Run[]>(`${basePath}/runs`).then(setRuns).catch(() => {});
  }, [basePath]);

  async function createRequest() {
    if (!selectedId || !newReq.name.trim()) return;
    await apiFetch(`${basePath}/collections/${selectedId}/requests`, { method: "POST", json: newReq });
    setNewReq({ name: "", method: "GET", path: "", body: "", assertions: "" });
    setShowReqForm(false);
    loadRequests(selectedId);
  }

  useEffect(() => { loadCollections(); loadRuns(); }, [loadCollections, loadRuns]);
  useEffect(() => { if (selectedId) { loadRequests(selectedId); setRunResults(null); } }, [selectedId, loadRequests]);

  async function createCollection() {
    if (!newCol.name.trim()) return;
    await apiFetch(`${basePath}/collections`, { method: "POST", json: newCol });
    setNewCol({ name: "", base_url: "" });
    setShowColForm(false);
    loadCollections();
  }

  async function runCollection() {
    if (!selectedId) return;
    setRunning(true);
    setRunResults(null);
    try {
      const res = await apiFetch<{ results: RunResult[] }>(`${basePath}/collections/${selectedId}/run`, { method: "POST" });
      setRunResults(res.results);
      loadRuns();
    } finally {
      setRunning(false);
    }
  }

  const selected = collections.find((c) => c.id === selectedId);
  const runPassCount = runResults?.filter((r) => r.passed).length ?? 0;
  const runFailCount = runResults ? runResults.length - runPassCount : 0;
  const inputCls = "rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="api-tests-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        }
        title="API Testleri"
        description="HTTP koleksiyonları oluşturun ve çalıştırın"
      />
      <FlowGuideCard projectId={projectId} stage="execute" />
      <ServiceTestingGuide projectId={projectId} stage="run" />

      {/* Stats */}
      <MetricRow cols={4}>
        <StatCard label="Koleksiyon" value={collections.length} color="slate" />
        <StatCard label="Seçili İstek" value={selected ? requests.length : "—"} color={selected ? "blue" : "slate"} />
        <StatCard label="Toplam Koşu" value={runs.length} color={runs.length > 0 ? "violet" : "slate"} />
        <StatCard
          label="Son Koşu"
          value={latestRun ? `${latestRun.results.filter(r => r.passed).length}/${latestRun.results.length}` : "—"}
          color={latestRun && latestRun.results.every(r => r.passed) ? "emerald" : latestRun ? "amber" : "slate"}
          sub={latestRun ? "geçti" : undefined}
        />
      </MetricRow>

      <div className="grid gap-3 md:grid-cols-3">
        {stageCards.map(card => {
          const active = workspaceMode === card.id;
          return (
            <button
              key={card.id}
              type="button"
              onClick={() => setWorkspaceMode(card.id)}
              className={`rounded-2xl border px-4 py-4 text-left transition-colors ${
                active
                  ? "border-blue-500/40 bg-blue-500/10"
                  : "border-slate-800 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-900/70"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${
                  active ? "bg-blue-500/20 text-blue-200" : "bg-slate-800 text-slate-400"
                }`}>
                  {card.label}
                </span>
                <span className="text-[11px] text-slate-500">{card.meta}</span>
              </div>
              <p className="mt-3 text-sm font-semibold text-white">{card.title}</p>
            </button>
          );
        })}
      </div>

      <div className="flex gap-4 flex-1 min-h-0" style={{ height: "calc(100vh - 200px)" }}>
        <div className="w-60 shrink-0 flex flex-col rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider">Koleksiyonlar</h2>
            <button onClick={() => setShowColForm((f) => !f)} className="text-xs text-blue-400 hover:text-blue-300 transition-colors">+ Yeni</button>
          </div>

          {showColForm && (
            <div className="border-b border-slate-800 p-3 space-y-2">
              <input placeholder="İsim" value={newCol.name} onChange={(e) => setNewCol({ ...newCol, name: e.target.value })} className={`${inputCls} w-full text-xs`} />
              <input placeholder="Base URL" value={newCol.base_url} onChange={(e) => setNewCol({ ...newCol, base_url: e.target.value })} className={`${inputCls} w-full text-xs`} />
              <button onClick={createCollection} className="w-full px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors">Oluştur</button>
            </div>
          )}

          <div className="flex-1 overflow-auto">
            {collections.length === 0 && !showColForm ? (
              <div className="p-4"><EmptyState icon="🧰" title="Koleksiyon yok" description="İlk koleksiyonu oluşturun" action={<button onClick={() => setShowColForm(true)} className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-500 transition-colors">Koleksiyon Oluştur</button>} /></div>
            ) : (
              collections.map((c) => (
                <button key={c.id} onClick={() => setSelectedId(c.id)} className={`flex w-full flex-col gap-0.5 border-b border-slate-800 px-4 py-3 text-left transition-all hover:bg-slate-800/50 ${selectedId === c.id ? "bg-blue-500/10 border-l-2 border-l-blue-500" : ""}`}>
                  <span className="text-sm font-medium text-white">{c.name}</span>
                  <span className="text-xs text-slate-500 truncate">{c.base_url || "—"}</span>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="flex-1 min-w-0 flex flex-col gap-4 overflow-auto">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center rounded-xl border border-slate-700 bg-slate-900/40">
              <EmptyState icon="📡" title="Koleksiyon seçin" description="Soldan bir API koleksiyonu seçin" />
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white">{selected.name}</h2>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">{selected.base_url || "Base URL yok"}</p>
                </div>
                <button onClick={runCollection} disabled={running || requests.length === 0} className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-xl transition-colors disabled:opacity-50" data-testid="api-tests-btn-run">
                  {running ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : "▶"}
                  {running ? "Çalışıyor…" : "Çalıştır"}
                </button>
              </div>

              {workspaceMode === "setup" && (
                <>
                  <SectionCard
                    title="Kurulum Rehberi"
                    icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
                  >
                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">1. Kaynak</p>
                        <p className="mt-2 text-sm text-white">Spec import et veya ilk koleksiyonu elle kur.</p>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">2. Istekler</p>
                        <p className="mt-2 text-sm text-white">Path, body ve assertionlari netlestir.</p>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">3. Sonraki Adim</p>
                        <p className="mt-2 text-sm text-white">Kosu moduna gecip koleksiyonu tek tikla calistir.</p>
                      </div>
                    </div>
                  </SectionCard>

                  {showReqForm && (
                    <SectionCard
                      title="Yeni Istek"
                      icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>}
                    >
                      <div className="space-y-3">
                        <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
                          <input placeholder="Istek adi" value={newReq.name} onChange={e => setNewReq({...newReq, name: e.target.value})}
                            className={inputCls} />
                          <select value={newReq.method} onChange={e => setNewReq({...newReq, method: e.target.value})}
                            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50">
                            {["GET","POST","PUT","DELETE","PATCH"].map(m => <option key={m}>{m}</option>)}
                          </select>
                          <input placeholder="/endpoint" value={newReq.path} onChange={e => setNewReq({...newReq, path: e.target.value})}
                            className={`${inputCls} font-mono`} />
                        </div>
                        <textarea placeholder="Body (JSON) — opsiyonel" value={newReq.body} onChange={e => setNewReq({...newReq, body: e.target.value})}
                          rows={3} className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 resize-none" />
                        <textarea placeholder="Assertions (JSON dizisi) — opsiyonel" value={newReq.assertions} onChange={e => setNewReq({...newReq, assertions: e.target.value})}
                          rows={2} className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 resize-none" />
                        <div className="flex gap-2">
                          <button onClick={createRequest}
                            className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors">Kaydet</button>
                          <button onClick={() => setShowReqForm(false)}
                            className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">Iptal</button>
                        </div>
                      </div>
                    </SectionCard>
                  )}
                </>
              )}

              {(workspaceMode === "setup" || workspaceMode === "run") && (
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
                  <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
                    <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
                      <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3" />
                      </svg>
                      <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                        {workspaceMode === "setup" ? "Istekler" : "Kosuya Girecek Istekler"}
                      </h3>
                      <span className="ml-auto text-xs text-slate-500">{requests.length} istek</span>
                    </div>
                    {requests.length === 0 ? (
                      <div className="p-6">
                        <EmptyState
                          icon="📡"
                          title="Henuz istek yok"
                          description="Koleksiyona ilk istegi ekleyin veya Chain Builder ile bu akis icin zincir tasarlayin."
                          action={
                            <div className="flex flex-wrap items-center justify-center gap-2">
                              <button
                                onClick={() => {
                                  setWorkspaceMode("setup");
                                  setShowReqForm(true);
                                }}
                                className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-500 transition-colors"
                              >
                                Ilk Istegi Ekle
                              </button>
                              <Link
                                href={`/p/${projectId}/chain-builder`}
                                className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
                              >
                                Chain Builder
                              </Link>
                            </div>
                          }
                        />
                      </div>
                    ) : (
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-800">
                            <th className="w-10 px-4 py-2.5" />
                            <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Isim</th>
                            <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Method</th>
                            <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Path</th>
                          </tr>
                        </thead>
                        <SortableContext items={requests.map(r => r.id)} strategy={verticalListSortingStrategy}>
                          <tbody>
                            {requests.map(r => <SortableRequestRow key={r.id} request={r} />)}
                          </tbody>
                        </SortableContext>
                      </table>
                    )}
                  </div>

                  <DragOverlay>
                    {activeRequest && (
                      <div className="flex items-center gap-3 rounded-xl border border-blue-500/30 bg-slate-800 px-4 py-3 shadow-xl">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-bold font-mono ${METHOD_COLORS[activeRequest.method] ?? ""}`}>
                          {activeRequest.method}
                        </span>
                        <span className="text-sm font-medium text-white">{activeRequest.name}</span>
                        <span className="font-mono text-xs text-slate-400">{activeRequest.path}</span>
                      </div>
                    )}
                  </DragOverlay>
                </DndContext>
              )}

              {workspaceMode === "run" && (
                <SectionCard
                  title="Kosu Kontrolu"
                  icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /></svg>}
                >
                  <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                      <p className="text-sm font-semibold text-white">Tek yapman gereken son kontrol ve kosu.</p>
                      <ul className="mt-3 space-y-2 text-sm text-slate-400">
                        <li>• Koleksiyon secili: <span className="text-slate-200">{selected.name}</span></li>
                        <li>• Kosuya girecek istek: <span className="text-slate-200">{requests.length}</span></li>
                        <li>• Base URL: <span className="font-mono text-slate-300">{selected.base_url || "tanimsiz"}</span></li>
                      </ul>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Sonraki Adim</p>
                      <p className="mt-2 text-sm text-slate-300">Calistirdiktan sonra sonuc moduna gecip cevaplari okuyacagiz.</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          onClick={runCollection}
                          disabled={running || requests.length === 0}
                          className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                        >
                          {running ? "Calisiyor…" : "Koleksiyonu Calistir"}
                        </button>
                        <button
                          onClick={() => setWorkspaceMode("results")}
                          className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500 hover:text-white"
                        >
                          Sonuclar
                        </button>
                      </div>
                    </div>
                  </div>
                </SectionCard>
              )}

              {runResults && (
                <SectionCard title="Koşu Sonuçları" right={<div className="flex gap-2 text-xs"><span className="text-emerald-400">{runPassCount} geçti</span><span className="text-red-400">{runFailCount} başarısız</span></div>} noPad>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-800">
                        <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">İstek</th>
                        <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Durum</th>
                        <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Sonuç</th>
                        <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-right">Süre</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runResults.map((r, i) => (
                        <tr key={i} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                          <td className="px-4 py-3 text-sm font-medium text-white">{r.name}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-bold font-mono ${statusCodeColor(r.status_code)}`}>{r.status_code || "ERR"}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${r.passed ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border-red-500/20 text-red-400"}`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${r.passed ? "bg-emerald-400" : "bg-red-400"}`} />
                              {r.passed ? "Geçti" : "Başarısız"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm tabular-nums text-slate-400 text-right">{r.duration_ms ? `${Math.round(r.duration_ms)} ms` : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </SectionCard>
              )}

              {runs.length > 0 && (
                <SectionCard title="Son Koşular" noPad>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-800">
                        <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">ID</th>
                        <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tarih</th>
                        <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-slate-400">Sonuc</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runs.slice(0, 5).map((run) => {
                        const total = run.results?.length ?? 0;
                        const passed = run.results?.filter((r) => r.passed).length ?? 0;
                        return (
                          <tr key={run.id} onClick={() => setRunResults(run.results)} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30 cursor-pointer">
                            <td className="px-4 py-3 font-mono text-xs text-slate-500">{run.id.slice(0, 8)}…</td>
                            <td className="px-4 py-3 text-xs text-slate-400">{run.created_at ? new Date(run.created_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—"}</td>
                            <td className="px-4 py-3 text-right">
                              <span className={`text-xs font-medium ${passed === total && total > 0 ? "text-emerald-400" : "text-amber-400"}`}>{passed}/{total} geçti</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </SectionCard>
              )}
            </>
          )}
        </div>
      </div>
      <PageFeedbackWidget />

    </div>
  );
}
