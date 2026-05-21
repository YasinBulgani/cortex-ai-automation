"use client";

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
  StatCard,
  MetricRow,
} from "@/components/nexus";

type Integration = {
  id: string;
  provider: string;
  config: Record<string, string>;
  is_active: boolean;
  last_sync_at: string | null;
};

type Form = { provider: string; base_url: string; api_token: string; project_key: string };
const emptyForm: Form = { provider: "jira", base_url: "", api_token: "", project_key: "" };

const PROVIDERS: Record<string, { label: string; icon: string; color: string }> = {
  jira:            { label: "Jira",              icon: "J",  color: "bg-blue-500/10 border-blue-500/20 text-blue-400" },
  azure_devops:    { label: "Azure DevOps",       icon: "Az", color: "bg-sky-500/10 border-sky-500/20 text-sky-400" },
  testRail:        { label: "TestRail",           icon: "TR", color: "bg-teal-500/10 border-teal-500/20 text-teal-400" },
  slack:           { label: "Slack",              icon: "S",  color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" },
  microsoft_teams: { label: "Microsoft Teams",    icon: "T",  color: "bg-violet-500/10 border-violet-500/20 text-violet-400" },
};

const WEBHOOK_PROVIDERS = new Set(["slack", "microsoft_teams"]);

const inputCls = "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

export default function IntegrationsPage() {
  const projectId = useRouteParam("projectId");
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [form, setForm] = useState<Form>(emptyForm);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<Integration[]>(`/api/v1/tspm/projects/${projectId}/integrations`)
      .then(setIntegrations).catch((err) => console.warn("[integrations]:", err));
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const config = WEBHOOK_PROVIDERS.has(form.provider)
        ? { webhook_url: form.base_url }
        : { base_url: form.base_url, api_token: form.api_token, project_key: form.project_key };
      await apiFetch(`/api/v1/tspm/projects/${projectId}/integrations`, {
        method: "POST", json: { provider: form.provider, config },
      });
      setForm(emptyForm);
      setShowForm(false);
      load();
    } finally { setLoading(false); }
  }

  async function testNotification(id: string) {
    setTesting(id);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/integrations/${id}/test-notification`, { method: "POST" });
      alert("Test bildirimi gönderildi!");
    } catch { alert("Bildirim gönderilemedi. Webhook URL'si doğru mu?"); }
    finally { setTesting(null); }
  }

  async function toggleActive(integ: Integration) {
    await apiFetch(`/api/v1/tspm/projects/${projectId}/integrations/${integ.id}`, {
      method: "PUT", json: { is_active: !integ.is_active },
    });
    load();
  }

  async function sync(id: string) {
    await apiFetch(`/api/v1/tspm/projects/${projectId}/integrations/${id}/sync`, { method: "POST" });
    load();
  }

  async function handleDelete(id: string) {
    await apiFetch(`/api/v1/tspm/projects/${projectId}/integrations/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="integrations-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        }
        title="Entegrasyonlar"
        description="Dış araçlarla bağlantı yönetimi"
        right={
          <button onClick={() => setShowForm(f => !f)}
            className="flex items-center gap-2 px-4 py-1.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            Yeni Entegrasyon
          </button>
        }
      />

      {/* Stats */}
      <MetricRow cols={3}>
        <StatCard label="Toplam" value={integrations.length} color="slate" />
        <StatCard label="Aktif" value={integrations.filter(i => i.is_active).length} color="emerald" />
        <StatCard
          label="Pasif"
          value={integrations.filter(i => !i.is_active).length}
          color={integrations.filter(i => !i.is_active).length > 0 ? "amber" : "slate"}
        />
      </MetricRow>

      {/* Create form */}
      {showForm && (
        <SectionCard title="Yeni Entegrasyon" icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>}>
          <form onSubmit={handleCreate} className="space-y-3" data-testid="integrations-form">
            <div className="grid gap-3 sm:grid-cols-2">
              <select value={form.provider} onChange={e => setForm({...form, provider: e.target.value})}
                data-testid="integrations-select-provider"
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50">
                {Object.entries(PROVIDERS).map(([key, { label }]) => <option key={key} value={key}>{label}</option>)}
              </select>
              {WEBHOOK_PROVIDERS.has(form.provider) ? (
                <input placeholder="Webhook URL" value={form.base_url} onChange={e => setForm({...form, base_url: e.target.value})}
                  required data-testid="integrations-input-webhook-url" className={inputCls} />
              ) : (
                <>
                  <input placeholder="Base URL" value={form.base_url} onChange={e => setForm({...form, base_url: e.target.value})}
                    required data-testid="integrations-input-base-url" className={inputCls} />
                  <input type="password" placeholder="API Token" value={form.api_token} onChange={e => setForm({...form, api_token: e.target.value})}
                    required data-testid="integrations-input-api-token" className={`${inputCls} font-mono`} />
                  <input placeholder="Proje Anahtarı (ör. NEUREX-SVC)" value={form.project_key} onChange={e => setForm({...form, project_key: e.target.value})}
                    required data-testid="integrations-input-project-key" className={inputCls} />
                </>
              )}
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={loading} data-testid="integrations-btn-create"
                className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50">
                {loading ? "Ekleniyor…" : "Ekle"}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">İptal</button>
            </div>
          </form>
        </SectionCard>
      )}

      {/* Integrations list */}
      <SectionCard
        title="Bağlı Entegrasyonlar"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>}
        right={<span className="text-xs text-slate-500">{integrations.length} entegrasyon</span>}
        noPad
      >
        {integrations.length === 0 ? (
          <div className="p-8">
            <EmptyState icon="🔌" title="Entegrasyon yok" description="Jira, Azure DevOps, Slack ve diğer araçları bağlayın"
              action={<button onClick={() => setShowForm(true)} className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors">Entegrasyon Ekle</button>} />
          </div>
        ) : (
          integrations.map(integ => {
            const prov = PROVIDERS[integ.provider] ?? { label: integ.provider, icon: "?", color: "bg-slate-800 border-slate-700 text-slate-300" };
            return (
              <div key={integ.id} className="flex items-center justify-between px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30 group">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg border flex items-center justify-center text-xs font-bold ${prov.color}`}>
                    {prov.icon}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{prov.label}</p>
                    <p className="text-xs text-slate-500">
                      {integ.last_sync_at
                        ? `Son sync: ${new Date(integ.last_sync_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" })}`
                        : "Hiç sync yapılmadı"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => toggleActive(integ)}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium cursor-pointer transition-all ${
                      integ.is_active ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${integ.is_active ? "bg-emerald-400" : "bg-slate-500"}`} />
                    {integ.is_active ? "Aktif" : "Pasif"}
                  </button>
                  {WEBHOOK_PROVIDERS.has(integ.provider) ? (
                    <button onClick={() => testNotification(integ.id)} disabled={testing === integ.id}
                      className="text-xs px-2 py-1 rounded-lg text-blue-400 hover:bg-blue-500/10 transition-colors disabled:opacity-50 opacity-0 group-hover:opacity-100">
                      Test
                    </button>
                  ) : (
                    <button onClick={() => sync(integ.id)}
                      className="text-xs px-2 py-1 rounded-lg text-slate-400 hover:bg-slate-700 transition-colors opacity-0 group-hover:opacity-100">
                      Sync
                    </button>
                  )}
                  <button onClick={() => handleDelete(integ.id)}
                    className="text-xs px-2 py-1 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100">
                    Sil
                  </button>
                </div>
              </div>
            );
          })
        )}
      </SectionCard>
    </div>
  );
}
