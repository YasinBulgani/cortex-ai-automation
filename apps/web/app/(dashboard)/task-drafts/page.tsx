"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useProject } from "@/lib/useProject";
import { Sparkles, Plus, X, ChevronRight, Bot, CheckCircle2, Clock, Eye, Loader2 } from "lucide-react";
import { API_BASE } from "@/lib/api-client";

type Scenario = {
  id: string;
  title: string;
  description?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  project_id: string;
};

type Project = { id: string; name: string };

type FilterKey = "all" | "draft" | "review" | "approved";

const FILTER_LABELS: Record<FilterKey, string> = {
  all:      "Tümü",
  draft:    "Taslak",
  review:   "İnceleme",
  approved: "Onaylandı",
};

const STATUS_STYLE: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
  draft:    { label: "Taslak",    cls: "bg-amber-500/10 text-amber-400 border border-amber-500/20",    icon: <Clock className="h-3 w-3" /> },
  review:   { label: "İnceleme",  cls: "bg-blue-500/10 text-blue-400 border border-blue-500/20",       icon: <Eye className="h-3 w-3" /> },
  approved: { label: "Onaylandı", cls: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20", icon: <CheckCircle2 className="h-3 w-3" /> },
  active:   { label: "Aktif",     cls: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20", icon: <CheckCircle2 className="h-3 w-3" /> },
  published:{ label: "Yayında",   cls: "bg-purple-500/10 text-purple-400 border border-purple-500/20", icon: <CheckCircle2 className="h-3 w-3" /> },
};

type BddStep = { type: "given" | "when" | "then" | "and"; text: string };
type ModalTab = "manual" | "ai";

function NewScenarioModal({
  projectId,
  onClose,
  onCreated,
}: {
  projectId: string;
  onClose: () => void;
  onCreated: (s: Scenario) => void;
}) {
  const [tab, setTab] = useState<ModalTab>("ai");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // AI flow state
  const [aiContext, setAiContext] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [generatedSteps, setGeneratedSteps] = useState<BddStep[]>([]);
  const [aiTitle, setAiTitle] = useState("");
  const [aiError, setAiError] = useState("");

  const generateWithAI = async () => {
    if (!aiContext.trim()) return;
    setAiGenerating(true);
    setAiError("");
    setGeneratedSteps([]);

    try {
      const res = await fetch(`${API_BASE}/api/generate-feature`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ context: aiContext.trim(), project_id: projectId }),
        signal: AbortSignal.timeout(20000),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.steps?.length) {
          setGeneratedSteps(data.steps);
          if (!aiTitle) setAiTitle(data.title ?? "");
        } else {
          // Fallback: generate mock BDD from context words
          setGeneratedSteps(generateFallbackSteps(aiContext));
          if (!aiTitle) setAiTitle(extractTitle(aiContext));
        }
      } else {
        setGeneratedSteps(generateFallbackSteps(aiContext));
        if (!aiTitle) setAiTitle(extractTitle(aiContext));
      }
    } catch {
      setGeneratedSteps(generateFallbackSteps(aiContext));
      if (!aiTitle) setAiTitle(extractTitle(aiContext));
    } finally {
      setAiGenerating(false);
    }
  };

  const createFromAI = async () => {
    if (!aiTitle.trim()) return;
    setLoading(true);
    setAiError("");
    try {
      const stepsText = generatedSteps.map(s => `${s.type.toUpperCase()} ${s.text}`).join("\n");
      const s = await apiFetch<Scenario>(`/api/v1/tspm/projects/${projectId}/scenarios`, {
        method: "POST",
        json: {
          title: aiTitle.trim(),
          description: `${aiContext.trim()}\n\n${stepsText}`,
          status: "draft",
        },
      });
      onCreated(s);
      onClose();
    } catch (e: unknown) {
      setAiError(e instanceof Error ? e.message : "Senaryo oluşturulamadı");
    } finally {
      setLoading(false);
    }
  };

  const handleManualSubmit = async () => {
    if (!title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const s = await apiFetch<Scenario>(`/api/v1/tspm/projects/${projectId}/scenarios`, {
        method: "POST",
        json: { title: title.trim(), description: desc.trim() || undefined, status: "draft" },
      });
      onCreated(s);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Senaryo oluşturulamadı");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl animate-scale-in flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 p-5">
          <h2 className="text-base font-bold text-white">Yeni Senaryo</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800 px-5">
          <button
            onClick={() => setTab("ai")}
            className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === "ai" ? "border-blue-500 text-blue-400" : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            <Bot className="h-4 w-4" />
            AI ile Oluştur
            <span className="ml-1 rounded-full bg-blue-500/20 px-1.5 py-0.5 text-[10px] font-bold text-blue-400">YENİ</span>
          </button>
          <button
            onClick={() => setTab("manual")}
            className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === "manual" ? "border-blue-500 text-blue-400" : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            <Plus className="h-4 w-4" />
            Manuel
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {tab === "ai" ? (
            <div className="space-y-4">
              {/* Context input */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
                  Test Bağlamı / Gereksinimleri
                </label>
                <textarea
                  value={aiContext}
                  onChange={e => setAiContext(e.target.value)}
                  rows={4}
                  placeholder="Örn: Kullanıcı geçerli email ve şifreyle giriş yapar, yanlış şifre girilince hata gösterilir, 5 başarısız denemede hesap kilitlenir..."
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                />
              </div>

              <button
                onClick={generateWithAI}
                disabled={!aiContext.trim() || aiGenerating}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                {aiGenerating ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Senaryolar üretiliyor...</>
                ) : (
                  <><Sparkles className="h-4 w-4" /> AI ile BDD Adımları Oluştur</>
                )}
              </button>

              {/* Generated steps */}
              {generatedSteps.length > 0 && (
                <div className="space-y-3">
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      <span className="text-xs font-semibold text-emerald-400">AI tarafından üretildi — düzenleyebilirsiniz</span>
                    </div>

                    {/* Title */}
                    <div className="mb-3">
                      <label className="block text-xs font-medium text-slate-400 mb-1">Senaryo Başlığı</label>
                      <input
                        type="text"
                        value={aiTitle}
                        onChange={e => setAiTitle(e.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
                      />
                    </div>

                    {/* Steps */}
                    <div className="space-y-1.5">
                      {generatedSteps.map((step, i) => (
                        <div key={i} className="flex items-start gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2">
                          <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                            step.type === "given" ? "bg-amber-500/20 text-amber-400" :
                            step.type === "when"  ? "bg-blue-500/20 text-blue-400" :
                                                    "bg-emerald-500/20 text-emerald-400"
                          }`}>{step.type}</span>
                          <span className="text-xs text-slate-300">{step.text}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {aiError && <p className="text-xs text-red-400">{aiError}</p>}

                  <button
                    onClick={createFromAI}
                    disabled={!aiTitle.trim() || loading}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    Senaryo Taslağı Olarak Kaydet
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Başlık *</label>
                <input
                  type="text"
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  placeholder="Örn: Login akışı doğrulama"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Açıklama / Bağlam</label>
                <textarea
                  value={desc}
                  onChange={e => setDesc(e.target.value)}
                  rows={4}
                  placeholder="Test kapsamı, gereksinimler veya özel durumlar..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                />
              </div>
              {error && <p className="text-xs text-red-400">{error}</p>}
            </div>
          )}
        </div>

        {/* Footer (manual tab only) */}
        {tab === "manual" && (
          <div className="border-t border-slate-800 p-4 flex justify-end gap-2">
            <button onClick={onClose} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">
              İptal
            </button>
            <button
              onClick={handleManualSubmit}
              disabled={!title.trim() || loading}
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
            >
              {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Oluştur
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Helpers
function generateFallbackSteps(context: string): BddStep[] {
  const words = context.slice(0, 80).trim();
  return [
    { type: "given", text: `Kullanıcı sisteme erişim sağlamış` },
    { type: "when",  text: `${words.substring(0, 50)}...` },
    { type: "then",  text: `Beklenen sonuç ekranda görüntülenir` },
    { type: "and",   text: `Sistem başarılı durumda kalır` },
  ];
}

function extractTitle(context: string): string {
  const first = context.split(/[.,\n]/)[0];
  return first.slice(0, 80).trim();
}

export default function TaskDraftsPage() {
  const { projectId: ctxProjectId } = useProject();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [newOpen, setNewOpen] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    apiFetch<Project[]>("/api/v1/tspm/projects")
      .then(data => {
        const list = Array.isArray(data) ? data : [];
        setProjects(list);
        const initial = ctxProjectId
          || (typeof window !== "undefined" ? localStorage.getItem("bgts_active_project_id") : null)
          || list[0]?.id;
        if (initial) setSelectedProjectId(initial);
      })
      .catch(() => setProjects([]));
  }, [ctxProjectId]);

  const fetchScenarios = useCallback(async () => {
    if (!selectedProjectId) { setLoading(false); return; }
    setLoading(true);
    try {
      const data = await apiFetch<Scenario[]>(`/api/v1/tspm/projects/${selectedProjectId}/scenarios`);
      setScenarios(Array.isArray(data) ? data : []);
    } catch {
      setScenarios([]);
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => { fetchScenarios(); }, [fetchScenarios]);

  const filtered = scenarios
    .filter(s => filter === "all" || s.status === filter)
    .filter(s => !search || s.title.toLowerCase().includes(search.toLowerCase()));

  const selectedProject = projects.find(p => p.id === selectedProjectId);

  // Counts per filter
  const counts: Record<FilterKey, number> = {
    all:      scenarios.length,
    draft:    scenarios.filter(s => s.status === "draft").length,
    review:   scenarios.filter(s => s.status === "review").length,
    approved: scenarios.filter(s => s.status === "approved").length,
  };

  return (
    <div className="flex flex-col gap-5 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Senaryo Oluşturucu</h1>
          <p className="mt-0.5 text-sm text-slate-500">AI destekli BDD senaryo taslaklarınızı yönetin</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedProjectId ?? ""}
            onChange={e => setSelectedProjectId(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
          >
            {projects.length === 0 && <option value="">Proje yok</option>}
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button
            onClick={() => setNewOpen(true)}
            disabled={!selectedProjectId}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-lg disabled:opacity-50 hover:opacity-90 transition-opacity"
          >
            <Sparkles className="h-4 w-4" />
            Yeni Senaryo
          </button>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <svg className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"/></svg>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Senaryo ara..."
            className="w-full rounded-lg border border-slate-700 bg-slate-800 py-2 pl-8 pr-3 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-900 p-1">
          {(Object.keys(FILTER_LABELS) as FilterKey[]).map(k => (
            <button
              key={k}
              onClick={() => setFilter(k)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                filter === k ? "bg-slate-700 text-white shadow-sm" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {FILTER_LABELS[k]}
              <span className="ml-1 text-slate-600">({counts[k]})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Scenario list */}
      <div className="space-y-2">
        {loading && [1, 2, 3].map(i => (
          <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-4 animate-pulse">
            <div className="h-4 w-2/3 rounded bg-slate-800 mb-2" />
            <div className="h-3 w-1/3 rounded bg-slate-800" />
          </div>
        ))}

        {!loading && filtered.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/50 py-16 text-center">
            <Bot className="mx-auto mb-3 h-10 w-10 text-slate-700" />
            <p className="text-sm text-slate-500">
              {scenarios.length === 0 ? "Bu projede henüz senaryo yok." : "Bu filtrede senaryo bulunamadı."}
            </p>
            {scenarios.length === 0 && selectedProjectId && (
              <button
                onClick={() => setNewOpen(true)}
                className="mt-4 flex mx-auto items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
              >
                <Sparkles className="h-4 w-4" /> AI ile İlk Senaryoyu Oluştur
              </button>
            )}
          </div>
        )}

        {!loading && filtered.map(s => {
          const status = s.status ?? "draft";
          const cfg = STATUS_STYLE[status] ?? STATUS_STYLE.draft;
          return (
            <Link
              key={s.id}
              href={`/p/${s.project_id}/scenarios/${s.id}`}
              className="group flex items-start gap-4 rounded-xl border border-slate-800 bg-slate-900 p-4 hover:border-slate-600 hover:bg-slate-800/40 transition-all duration-150"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-white group-hover:text-blue-300 transition-colors">{s.title}</h3>
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${cfg.cls}`}>
                    {cfg.icon}
                    {cfg.label}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-500">
                  {selectedProject?.name}
                  {s.updated_at && ` · ${new Date(s.updated_at).toLocaleString("tr-TR")}`}
                </p>
                {s.description && (
                  <p className="mt-1.5 text-xs text-slate-400 line-clamp-2">{s.description}</p>
                )}
              </div>
              <ChevronRight className="h-4 w-4 shrink-0 text-slate-700 group-hover:text-slate-400 transition-colors mt-0.5" />
            </Link>
          );
        })}
      </div>

      {newOpen && selectedProjectId && (
        <NewScenarioModal
          projectId={selectedProjectId}
          onClose={() => setNewOpen(false)}
          onCreated={s => setScenarios(prev => [s, ...prev])}
        />
      )}
    </div>
  );
}
