"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useProject } from "@/lib/useProject";

type FlowCategory = "all" | "indexing" | "analysis" | "automation" | "review" | "test" | "custom";

type FlowTemplate = {
  id: string;
  name: string;
  description: string;
  category: Exclude<FlowCategory, "all">;
  agentType: string;
  isBuiltin: boolean;
  tags: string[];
  graph?: unknown;
};

type Project = { id: string; name: string };

const CATEGORY_LABELS: Record<FlowCategory, string> = {
  all:        "Tüm Kategoriler",
  indexing:   "İndeksleme",
  analysis:   "Analiz",
  automation: "Otomasyon",
  review:     "İnceleme",
  test:       "Test",
  custom:     "Özel",
};

const TEMPLATES: FlowTemplate[] = [
  { id: "f1", name: "Senaryo Üreticisi",        description: "Gereksinimlerden otomatik BDD/Gherkin test senaryosu üretir. Proje bağlamını okur.",  category: "automation", agentType: "Scenario Gen",  isBuiltin: true,  tags: ["bdd", "gherkin", "ai"] },
  { id: "f2", name: "Regresyon Analizi",        description: "Son kod değişikliklerini analiz ederek etkilenen senaryoları tespit eder ve önceliklendirir.", category: "analysis",   agentType: "AI Analyzer",   isBuiltin: true,  tags: ["regression", "impact"] },
  { id: "f3", name: "Self-Healing Runner",      description: "Kırık locator'ları otomatik düzelterek testlerin çalışmaya devam etmesini sağlar.",   category: "automation", agentType: "Healer",        isBuiltin: true,  tags: ["self-healing", "locator"] },
  { id: "f4", name: "API Sözleşme Doğrulama",   description: "OpenAPI spec'e göre API endpoint'lerini test eder, yanıt şemalarını doğrular.",       category: "test",       agentType: "API Tester",    isBuiltin: true,  tags: ["api", "openapi", "contract"] },
  { id: "f5", name: "Görsel Regresyon",         description: "Sayfa ekran görüntülerini karşılaştırır, görsel değişiklikleri raporlar.",              category: "review",     agentType: "Visual Diff",   isBuiltin: true,  tags: ["visual", "screenshot"] },
  { id: "f6", name: "DSL Katalog İndeksleme",   description: "DSL tanımlarını indeksler, semantic arama için vektör veritabanına yükler.",             category: "indexing",   agentType: "DSL Indexer",   isBuiltin: true,  tags: ["dsl", "indexing", "vector"] },
  { id: "f7", name: "Erişilebilirlik Taraması", description: "WCAG 2.1 AA standartlarına göre sayfa erişilebilirliğini analiz eder.",                  category: "test",       agentType: "A11y Scanner",  isBuiltin: false, tags: ["wcag", "a11y"] },
  { id: "f8", name: "Güvenlik Testi",           description: "OWASP Top 10 kategorilerine göre temel güvenlik açıklarını tarar.",                       category: "test",       agentType: "Security Scan", isBuiltin: false, tags: ["security", "owasp"] },
];

const CATEGORY_KEYS: FlowCategory[] = ["all", "indexing", "analysis", "automation", "review", "test", "custom"];

function UseTemplateModal({ template, projects, defaultProjectId, onClose }: {
  template: FlowTemplate;
  projects: Project[];
  defaultProjectId: string | null;
  onClose: () => void;
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<string>(defaultProjectId || projects[0]?.id || "");
  const [name, setName] = useState(template.name);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    if (!projectId || !name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const flow = await apiFetch<{ id: string }>(`/api/v1/tspm/projects/${projectId}/flows`, {
        method: "POST",
        json: { name: name.trim(), template_id: template.id, agent_type: template.agentType, tags: template.tags },
      });
      router.push(`/p/${projectId}/flows/${flow.id}`);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Akış oluşturulamadı");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl animate-scale-in">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Şablonu Kullan</h2>
            <p className="text-xs text-slate-500 mt-0.5">{template.name}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Proje *</label>
            <select
              value={projectId}
              onChange={e => setProjectId(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            >
              {projects.length === 0 && <option value="">Proje yok</option>}
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Akış Adı *</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">
            İptal
          </button>
          <button
            onClick={handleCreate}
            disabled={!projectId || !name.trim() || loading}
            className="rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
          >
            {loading ? "Oluşturuluyor..." : "Akışı Oluştur"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function FlowDesignerPage() {
  const { projectId: ctxProjectId } = useProject();
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeCategory, setActiveCategory] = useState<FlowCategory>("all");
  const [search, setSearch] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<FlowTemplate | null>(null);

  useEffect(() => {
    apiFetch<Project[]>("/api/v1/tspm/projects")
      .then(d => setProjects(Array.isArray(d) ? d : []))
      .catch(() => setProjects([]));
  }, []);

  const filtered = TEMPLATES.filter(t => {
    const catMatch = activeCategory === "all" || t.category === activeCategory;
    const searchMatch = !search || t.name.toLowerCase().includes(search.toLowerCase()) || t.description.toLowerCase().includes(search.toLowerCase());
    return catMatch && searchMatch;
  });

  const grouped = CATEGORY_KEYS
    .filter(k => k !== "all")
    .map(cat => ({ cat, items: filtered.filter(t => t.category === cat) }))
    .filter(g => g.items.length > 0);

  return (
    <div className="flex flex-col gap-6 p-6">

      {/* Başlık */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Akış Tasarımcısı</h1>
          <p className="mt-0.5 text-sm text-slate-500">Projeleriniz için akış şablonlarına göz atın ve özelleştirin</p>
        </div>
        <button className="flex items-center gap-2 rounded-xl border border-dashed border-violet-500/40 bg-violet-500/5 px-4 py-2.5 text-sm font-medium text-violet-300 hover:bg-violet-500/10 transition-colors">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
          Özel Akış Tasarla
        </button>
      </div>

      {/* Arama + kategori filtresi */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48">
          <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Şablon ara..."
            className="w-full rounded-xl border border-slate-700 bg-slate-900 py-2 pl-9 pr-4 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
        </div>
        <div className="flex flex-wrap gap-1">
          {CATEGORY_KEYS.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                activeCategory === cat
                  ? "bg-violet-500/10 text-violet-200 border border-violet-500/30"
                  : "border border-slate-700 text-slate-400 hover:text-white hover:border-slate-600"
              }`}
            >
              {CATEGORY_LABELS[cat]}
            </button>
          ))}
        </div>
      </div>

      {/* Şablon grupları */}
      {activeCategory === "all" ? (
        <div className="space-y-8">
          {grouped.map(({ cat, items }) => (
            <div key={cat}>
              <div className="mb-3 flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-300">{CATEGORY_LABELS[cat]}</h2>
                <span className="text-xs text-slate-600">({items.length})</span>
              </div>
              <TemplateGrid items={items} onUse={setSelectedTemplate} />
            </div>
          ))}
          {grouped.length === 0 && <EmptyState />}
        </div>
      ) : (
        filtered.length > 0 ? <TemplateGrid items={filtered} onUse={setSelectedTemplate} /> : <EmptyState />
      )}

      {selectedTemplate && (
        <UseTemplateModal
          template={selectedTemplate}
          projects={projects}
          defaultProjectId={ctxProjectId}
          onClose={() => setSelectedTemplate(null)}
        />
      )}
    </div>
  );
}

function TemplateGrid({ items, onUse }: { items: FlowTemplate[]; onUse: (t: FlowTemplate) => void }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {items.map(t => (
        <div key={t.id} className="group flex flex-col rounded-xl border border-slate-800 bg-slate-900 p-4 hover:border-slate-700 transition-colors">
          <div className="mb-3 flex items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-white">{t.name}</h3>
              <p className="mt-0.5 text-xs text-slate-500">Agent Tipi: {t.agentType}</p>
            </div>
            {t.isBuiltin && (
              <span className="shrink-0 rounded-full border border-slate-700 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                Yerleşik
              </span>
            )}
          </div>
          <p className="flex-1 text-xs text-slate-400 leading-relaxed">{t.description}</p>
          <div className="mt-3 flex flex-wrap gap-1">
            {t.tags.map(tag => (
              <span key={tag} className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-500">#{tag}</span>
            ))}
          </div>
          <div className="mt-4 flex gap-2">
            <button className="flex-1 rounded-lg border border-slate-700 py-1.5 text-xs text-slate-400 hover:text-white hover:border-slate-500 transition-colors">
              Detaylar
            </button>
            <button
              onClick={() => onUse(t)}
              className="flex-1 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 py-1.5 text-xs font-semibold text-white hover:opacity-90 transition-opacity"
            >
              Şablonu Kullan
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 py-16 text-center">
      <p className="text-sm text-slate-500">Bu kategoride şablon bulunamadı.</p>
    </div>
  );
}
