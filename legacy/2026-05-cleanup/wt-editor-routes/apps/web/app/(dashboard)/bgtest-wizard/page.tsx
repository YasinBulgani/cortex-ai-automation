"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

/* ─── Types ──────────────────────────────────────────────────────── */
type Project = { id: string; name: string; description?: string };
type GlobalStats = {
  total_projects: number;
  total_scenarios: number;
  total_executions: number;
  avg_pass_rate: number;
};
type RecentExecution = {
  id: string;
  name: string;
  status: string;
  project_name?: string;
  project_id: string;
  passed_count: number;
  failed_count: number;
  scenario_total: number;
  created_at: string | null;
};
type ServiceStatus = { name: string; url: string; status: "up" | "down" | "checking" };

const statusColor: Record<string, string> = {
  completed: "bg-emerald-500/10 text-emerald-400 border-green-300 ",
  running:   "bg-blue-500/10 text-blue-400 border-blue-300 ",
  failed:    "bg-red-500/10 text-red-400 border-red-300 ",
  pending:   "bg-amber-500/10 text-amber-400 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-400",
};

const WIZARD_STEPS = [
  { id: 1, icon: "📁", title: "Proje Oluştur",   desc: "Yeni bir test projesi tanımla",                       page: null },
  { id: 2, icon: "📝", title: "Senaryo Ekle",     desc: "BDD / manuel test senaryoları yaz",                  page: "scenarios" },
  { id: 3, icon: "▶️", title: "Koşu Başlat",     desc: "Senaryoları çalıştır ve sonuçları kaydet",           page: "executions" },
  { id: 4, icon: "📊", title: "Analitik İncele",  desc: "Pass rate, trend ve flaky testleri gör",             page: "analytics" },
  { id: 5, icon: "🤖", title: "AI Sihirbazı",     desc: "Önceliklendirme, anomali ve assertion önerileri",    page: "flaky" },
  { id: 6, icon: "🔔", title: "Entegrasyon Kur",  desc: "Slack/Teams bildirimleri ve n8n akışları",           page: "integrations" },
];

const QUICK_LINKS = [
  { icon: "📋", label: "Senaryolar",     key: "scenarios" },
  { icon: "⚡", label: "Koşular",        key: "executions" },
  { icon: "📈", label: "Analitik",       key: "analytics" },
  { icon: "🧪", label: "API Testleri",   key: "api-tests" },
  { icon: "🔀", label: "Regresyon",      key: "regression" },
  { icon: "🎯", label: "Test Verileri",  key: "test-data" },
  { icon: "📷", label: "Görsel Test",    key: "visual" },
  { icon: "🎬", label: "Kaydedici",      key: "recorder" },
  { icon: "🔗", label: "Entegrasyonlar", key: "integrations" },
  { icon: "📄", label: "Raporlar",       key: "reports" },
  { icon: "🗂",  label: "Gereksinimler", key: "requirements" },
  { icon: "⏰", label: "Zamanlayıcı",   key: "schedules" },
];

/* ═══════════════════════════════════════════════════════════════════ */
export default function BgtestWizardPage() {
  /* ── Shared state ─────────────────────────────────────────────── */
  const [projects,        setProjects]        = useState<Project[]>([]);
  const [stats,           setStats]           = useState<GlobalStats | null>(null);
  const [recents,         setRecents]         = useState<RecentExecution[]>([]);
  const [services,        setServices]        = useState<ServiceStatus[]>([
    { name: "FastAPI Backend", url: "http://localhost:8000/health", status: "checking" },
    { name: "Flask Engine",    url: "http://localhost:5001/health", status: "checking" },
    { name: "Next.js UI",      url: "http://localhost:3000",        status: "checking" },
  ]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [newProjectName,  setNewProjectName]  = useState("");
  const [newProjectDesc,  setNewProjectDesc]  = useState("");
  const [creating,        setCreating]        = useState(false);
  const [createErr,       setCreateErr]       = useState<string | null>(null);
  const [loading,         setLoading]         = useState(true);
  const [activeStep,      setActiveStep]      = useState(1);

  /* ── Load ─────────────────────────────────────────────────────── */
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ps, gs] = await Promise.allSettled([
        apiFetch<Project[]>("/api/v1/tspm/projects"),
        apiFetch<GlobalStats>("/api/v1/tspm/dashboard/global"),
      ]);
      const projectList = ps.status === "fulfilled" ? ps.value : [];
      setProjects(projectList);
      if (gs.status === "fulfilled") setStats(gs.value);

      if (projectList.length > 0) {
        const first = projectList[0].id;
        setSelectedProject((prev) => prev || first);
        const execs = await apiFetch<RecentExecution[]>(
          `/api/v1/tspm/projects/${first}/executions`
        ).catch(() => [] as RecentExecution[]);
        setRecents(
          execs.slice(0, 5).map((e) => ({ ...e, project_name: projectList[0].name }))
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  /* ping services */
  useEffect(() => {
    const svcs = [
      { url: "http://localhost:8000/health", idx: 0 },
      { url: "http://localhost:5001/health", idx: 1 },
      { url: "http://localhost:3000",        idx: 2 },
    ];
    svcs.forEach(({ url, idx }) => {
      fetch(url, { signal: AbortSignal.timeout(3000) })
        .then((r) => setServices((p) => { const n=[...p]; n[idx]={...n[idx], status: r.ok?"up":"down"}; return n; }))
        .catch(()  => setServices((p) => { const n=[...p]; n[idx]={...n[idx], status: "down"};           return n; }));
    });
  }, []);

  /* ── Create project ───────────────────────────────────────────── */
  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    setCreating(true); setCreateErr(null);
    try {
      const proj = await apiFetch<Project>("/api/v1/tspm/projects", {
        method: "POST",
        json: { name: newProjectName.trim(), description: newProjectDesc.trim() },
      });
      setNewProjectName(""); setNewProjectDesc("");
      await load();
      setSelectedProject(proj.id);
      setActiveStep(2);
    } catch (err) {
      setCreateErr(err instanceof Error ? err.message : "Proje oluşturulamadı");
    } finally {
      setCreating(false);
    }
  }

  const proj = projects.find((p) => p.id === selectedProject);

  /* ═══════════════════════════════════════════════════════════════ */
  return (
    <div className="mx-auto max-w-6xl space-y-6" data-testid="bgtest-wizard-page">

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            <span className="mr-2">💡</span>Visium Sihirbazı
          </h1>
          <p className="text-sm text-slate-400">Tüm test süreçlerini uçtan uca tek ekrandan yönetin</p>
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={load}>Yenile</Button>
      </div>

      {/* Servis durumu */}
      <section className="grid gap-3 sm:grid-cols-3">
        {services.map((svc) => (
          <div key={svc.name} className="flex items-center gap-3 rounded-lg border border-slate-800 p-3">
            <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${
              svc.status==="up" ? "bg-green-500" : svc.status==="down" ? "bg-red-500" : "bg-yellow-400 animate-pulse"
            }`} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{svc.name}</p>
              <p className={`text-xs ${svc.status==="up"?"text-green-600":svc.status==="down"?"text-red-500":"text-slate-400"}`}>
                {svc.status==="up"?"Çalışıyor":svc.status==="down"?"Erişilemiyor":"Kontrol ediliyor…"}
              </p>
            </div>
          </div>
        ))}
      </section>

      {/* Global istatistikler */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Toplam Proje",      value: loading?"—":stats?.total_projects??0,   icon:"📁" },
          { label: "Toplam Senaryo",    value: loading?"—":stats?.total_scenarios??0,  icon:"📝" },
          { label: "Toplam Koşu",       value: loading?"—":stats?.total_executions??0, icon:"▶️" },
          { label: "Ort. Başarı Oranı", value: loading?"—":`${Math.round(stats?.avg_pass_rate??0)}%`, icon:"📊" },
        ].map((c) => (
          <div key={c.label} className="rounded-lg border border-slate-800 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-400">{c.label}</p>
              <span className="text-lg">{c.icon}</span>
            </div>
            <p className="mt-1 text-2xl font-bold tabular-nums">{c.value}</p>
          </div>
        ))}
      </section>

      {/* Proje seçici + hızlı linkler / son koşular + yeni proje */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="space-y-4">
          <div className="rounded-lg border border-slate-800 p-4 space-y-3">
            <h2 className="text-sm font-semibold">Aktif Proje</h2>
            {projects.length === 0 ? (
              <p className="text-sm text-slate-400">Henüz proje yok.</p>
            ) : (
              <div className="flex flex-col gap-1.5">
                {projects.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setSelectedProject(p.id)}
                    className={`flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors
                      ${selectedProject===p.id
                        ?"bg-blue-500/10 font-medium text-blue-400 ring-1 ring-blue-500/40"
                        :"hover:bg-black/[0.03] dark:hover:bg-white/[0.04]"}`}
                  >
                    <span className={`h-2 w-2 rounded-full shrink-0 ${selectedProject===p.id?"bg-blue-600":"bg-border"}`} />
                    {p.name}
                  </button>
                ))}
              </div>
            )}
          </div>
          {proj && (
            <div className="rounded-lg border border-slate-800 p-4 space-y-3">
              <h2 className="text-sm font-semibold">
                <span className="text-blue-400">{proj.name}</span> — Hızlı Erişim
              </h2>
              <div className="grid grid-cols-3 gap-2">
                {QUICK_LINKS.map((ql) => (
                  <Link
                    key={ql.key}
                    href={`/p/${proj.id}/${ql.key}`}
                    className="flex flex-col items-center gap-1 rounded-lg border border-slate-800 p-2 text-center hover:bg-blue-500/5 hover:border-blue-500/40 transition-colors"
                  >
                    <span className="text-xl">{ql.icon}</span>
                    <span className="text-[11px] text-slate-400">{ql.label}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="space-y-4">
          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <div className="border-b border-slate-800 bg-slate-900/40 bg-slate-800/30 px-4 py-2.5 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Son Koşular</h2>
              {proj && <Link href={`/p/${proj.id}/executions`} className="text-xs text-blue-400 hover:underline">Tümünü gör →</Link>}
            </div>
            {loading ? (
              <div className="p-4 space-y-2">
                {[1,2,3].map((i) => <div key={i} className="h-10 animate-pulse rounded bg-black/[0.04] bg-slate-800" />)}
              </div>
            ) : recents.length === 0 ? (
              <p className="p-6 text-center text-sm text-slate-400">Henüz koşu yok.</p>
            ) : (
              <div className="divide-y divide-border">
                {recents.map((r) => (
                  <div key={r.id} className="flex items-center justify-between px-4 py-3 gap-3">
                    <div className="min-w-0">
                      <Link href={`/p/${r.project_id}/executions/${r.id}`} className="block truncate text-sm font-medium hover:underline">
                        {r.name || "Koşu"}
                      </Link>
                      <p className="text-xs text-slate-400 tabular-nums">✅ {r.passed_count} / ❌ {r.failed_count} · {r.scenario_total} sn</p>
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <Badge className={`text-[10px] border ${statusColor[r.status]??"bg-slate-800 text-slate-300"}`}>{r.status}</Badge>
                      <span className="text-[10px] text-slate-400">{r.created_at?new Date(r.created_at).toLocaleDateString("tr-TR"):"—"}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-slate-800 p-4 space-y-3">
            <h2 className="text-sm font-semibold">Yeni Proje Oluştur</h2>
            <form onSubmit={handleCreateProject} className="space-y-2">
              <Input placeholder="Proje adı" value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} required />
              <Input placeholder="Açıklama (isteğe bağlı)" value={newProjectDesc} onChange={(e) => setNewProjectDesc(e.target.value)} />
              {createErr && <p className="text-xs text-red-600">{createErr}</p>}
              <Button type="submit" disabled={creating} className="w-full">{creating?"Oluşturuluyor…":"Proje Oluştur"}</Button>
            </form>
          </div>
        </section>
      </div>

      {/* Adım rehberi */}
      <section className="rounded-lg border border-slate-800 overflow-hidden">
        <div className="border-b border-slate-800 bg-slate-900/40 bg-slate-800/30 px-5 py-3">
          <h2 className="text-sm font-semibold">Uçtan Uca Adım Rehberi</h2>
          <p className="text-xs text-slate-400 mt-0.5">Adımları sırayla takip ederek ilk test sürecinizi tamamlayın</p>
        </div>
        <div className="grid gap-0 divide-y divide-border md:grid-cols-3 md:divide-y-0 md:divide-x">
          {WIZARD_STEPS.map((step) => {
            const isActive = activeStep === step.id;
            const isDone   = activeStep > step.id;
            const href = step.page && proj ? `/p/${proj.id}/${step.page}` : step.page === null && step.id === 1 ? "/projects" : null;
            return (
              <div
                key={step.id}
                onClick={() => setActiveStep(step.id)}
                className={`flex flex-col gap-2 p-4 cursor-pointer transition-colors hover:bg-slate-800/20 
                  ${isActive?"bg-blue-500/5 ring-inset ring-1 ring-blue-500/30":""}
                  ${isDone?"opacity-60":""}`}
              >
                <div className="flex items-center gap-2">
                  <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold
                    ${isDone?"bg-green-500 text-white":isActive?"bg-blue-600 text-white":"bg-border text-slate-400"}`}>
                    {isDone?"✓":step.id}
                  </span>
                  <span className="text-lg">{step.icon}</span>
                  <span className="text-sm font-medium">{step.title}</span>
                </div>
                <p className="text-xs text-slate-400 pl-8">{step.desc}</p>
                {href && (
                  <Link href={href} className="mt-1 ml-8 text-xs font-medium text-blue-400 hover:underline" onClick={(e) => e.stopPropagation()}>
                    Git →
                  </Link>
                )}
              </div>
            );
          })}
        </div>
        <div className="border-t border-slate-800 px-5 py-3 flex items-center gap-3">
          <div className="flex-1 rounded-full bg-border h-1.5 overflow-hidden">
            <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width:`${((activeStep-1)/(WIZARD_STEPS.length-1))*100}%` }} />
          </div>
          <span className="text-xs text-slate-400 shrink-0">Adım {activeStep} / {WIZARD_STEPS.length}</span>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" size="sm" disabled={activeStep<=1} onClick={() => setActiveStep((s) => s-1)}>‹ Geri</Button>
            <Button type="button" size="sm" disabled={activeStep>=WIZARD_STEPS.length} onClick={() => setActiveStep((s) => s+1)}>İleri ›</Button>
          </div>
        </div>
      </section>

      {/* Admin kısayolları */}
      <section className="grid gap-3 sm:grid-cols-3">
        {[
          { icon:"👥", label:"Kullanıcı Yönetimi", href:"/admin/users",    desc:"Kullanıcı ekle / deaktif et" },
          { icon:"📋", label:"Denetim Günlüğü",   href:"/admin/audit",    desc:"Tüm platform aktivitesi" },
          { icon:"🤖", label:"AI Ayarları",        href:"/admin/settings", desc:"LLM sağlayıcı seç" },
        ].map((item) => (
          <Link key={item.href} href={item.href}
            className="flex items-start gap-3 rounded-lg border border-slate-800 p-4 hover:bg-blue-500/5 hover:border-blue-500/40 transition-colors">
            <span className="text-2xl">{item.icon}</span>
            <div>
              <p className="text-sm font-medium">{item.label}</p>
              <p className="text-xs text-slate-400">{item.desc}</p>
            </div>
          </Link>
        ))}
      </section>

    </div>
  );
}
