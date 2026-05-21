"use client";

import { useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { FlowGuideCard } from "@/components/FlowGuideCard";
import { useFetch } from "@/lib/useFetch";
import { apiFetch, ENGINE_BASE } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
} from "@/components/nexus";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

// ── GitHub Actions Entegrasyon Paneli ─────────────────────────────────────────
function GithubActionsPanel({ projectId }: { projectId: string }) {
  const [copied, setCopied] = useState<string | null>(null);

  const triggerUrl = `${API_BASE}/api/v1/cicd/trigger/${projectId}`;

  const yaml = `# .github/workflows/visium-ops.yml
name: Visium Operations — Test Kosumu

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  visium-ops:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Visium testlerini tetikle
        run: |
          curl -s -X POST \\
            -H "Content-Type: application/json" \\
            -H "X-CI-Token: \${{ secrets.VISIUM_CI_TOKEN }}" \\
            -d '{
              "source": "github_actions",
              "branch": "\${{ github.ref_name }}",
              "commit": "\${{ github.sha }}",
              "smoke_only": false
            }' \\
            "${triggerUrl}"`;

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
    });
  }

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden">
      {/* Başlık */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-800">
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-slate-300">
          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
        </svg>
        <span className="text-sm font-semibold text-white">GitHub Actions Entegrasyonu</span>
        <span className="ml-auto text-xs text-slate-500">Trigger URL + YAML şablonu</span>
      </div>

      <div className="p-5 space-y-5">
        {/* Trigger URL */}
        <div>
          <p className="text-xs font-medium text-slate-400 mb-2">
            1. Trigger URL — CI token&apos;ınızı <code className="text-indigo-400">X-CI-Token</code> header&apos;ı ile gönderin
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded-xl bg-slate-800/60 border border-slate-700 px-4 py-2.5 text-xs text-emerald-300 font-mono overflow-x-auto whitespace-nowrap">
              POST {triggerUrl}
            </code>
            <button
              onClick={() => copy(triggerUrl, "url")}
              className="shrink-0 px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition-colors border border-slate-700"
            >
              {copied === "url" ? "✓ Kopyalandı" : "Kopyala"}
            </button>
          </div>
        </div>

        {/* Secrets */}
        <div className="rounded-xl bg-slate-800/40 border border-slate-700/50 px-4 py-3 space-y-1.5">
          <p className="text-xs font-medium text-slate-400 mb-2">
            2. GitHub Secrets — repository ayarlarına ekleyin
          </p>
          {[
            { key: "VISIUM_CI_TOKEN",    value: "Ayarlar → Engine Secret Key",        note: "ENGINE_SECRET_KEY ile aynı" },
            { key: "VISIUM_CI_BASE_URL", value: triggerUrl,                           note: "Trigger endpoint" },
          ].map(({ key, value, note }) => (
            <div key={key} className="flex items-start justify-between gap-4">
              <div>
                <code className="text-xs text-amber-300 font-mono">{key}</code>
                <p className="text-[11px] text-slate-600 mt-0.5">{note}</p>
              </div>
              <code className="text-[11px] text-slate-400 font-mono truncate max-w-[200px]">{value}</code>
            </div>
          ))}
        </div>

        {/* YAML Şablonu */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-slate-400">3. Workflow Dosyası — <code className="text-indigo-400">.github/workflows/visium-ops.yml</code></p>
            <button
              onClick={() => copy(yaml, "yaml")}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              {copied === "yaml" ? "✓ Kopyalandı" : "Tümünü Kopyala"}
            </button>
          </div>
          <pre className="rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 text-[11px] text-slate-300 font-mono overflow-x-auto leading-relaxed whitespace-pre">
            {yaml}
          </pre>
        </div>

        {/* GitLab / Jenkins linkler */}
        <div className="flex gap-2 pt-1">
          {[
            { label: "GitLab CI Webhook", href: "#" },
            { label: "Jenkins Plugin",    href: "#" },
          ].map(({ label, href }) => (
            <a key={label} href={href}
              className="text-xs text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors"
            >
              {label} →
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

type WebhookConfig = {
  auto_run_on_pr: boolean;
  auto_run_on_push: boolean;
  run_browser: string;
  smoke_markers: string;
  notify_pr: boolean;
  github_token: string;
};

type WebhookEvent = {
  id: string;
  source: string;
  event_type: string;
  repo?: string;
  pr_title?: string;
  branch?: string;
  received_at: string;
  processed: boolean;
  run_id?: string;
  risk_level?: string;
};

type CicdEvent = {
  id: string;
  source: "github" | "gitlab" | "jenkins";
  event_type: string;
  project_ref: string;
  received_at: string;
  payload_summary: Record<string, unknown>;
};

const SOURCE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  github:  { bg: "bg-slate-700",        text: "text-white",        label: "GitHub" },
  gitlab:  { bg: "bg-orange-500/20",    text: "text-orange-400",   label: "GitLab" },
  jenkins: { bg: "bg-blue-500/20",      text: "text-blue-400",     label: "Jenkins" },
  generic: { bg: "bg-slate-800",        text: "text-slate-300",    label: "Generic" },
};

const RISK_STYLES: Record<string, string> = {
  high:   "bg-red-500/10 border-red-500/20 text-red-400",
  medium: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  low:    "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
};

function EngineWebhookPanel() {
  const engineBase = typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:5001`
    : "http://localhost:5001";
  const [cfg, setCfg] = useState<WebhookConfig | null>(null);
  const [events, setEvents] = useState<WebhookEvent[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${ENGINE_BASE}/api/webhooks/config`).then(r => r.json()).then(setCfg).catch(() => {});
    fetch(`${ENGINE_BASE}/api/webhooks/events?limit=10`).then(r => r.json()).then(d => setEvents(d.events ?? [])).catch(() => {});
  }, []);

  async function saveConfig() {
    if (!cfg) return;
    setSaving(true);
    try {
      await fetch(`${ENGINE_BASE}/api/webhooks/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally { setSaving(false); }
  }

  function copyUrl(url: string) {
    navigator.clipboard.writeText(url);
    setCopied(url);
    setTimeout(() => setCopied(null), 2000);
  }

  const inputCls = "rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500/50 w-full";

  return (
    <SectionCard
      title="Engine Webhook Konfigürasyonu"
      icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
      right={<span className="text-xs text-slate-500">APScheduler tabanlı · kalıcı</span>}
    >
      <div className="space-y-4">
        <p className="text-xs text-slate-400">PR açıldığında otomatik test analizi + koşu tetikler.</p>

        {/* Webhook URLs */}
        <div className="space-y-2">
          {[
            { label: "GitHub", path: "/api/webhooks/github", note: "PR & push events" },
            { label: "GitLab", path: "/api/webhooks/gitlab", note: "MR & push events" },
            { label: "Generic", path: "/api/webhooks/generic", note: "Herhangi bir CI" },
          ].map(({ label, path, note }) => {
            const full = `${engineBase}${path}`;
            return (
              <div key={path} className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-300 w-14 shrink-0">{label}</span>
                <code className="flex-1 rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-xs font-mono text-slate-300 select-all truncate">{full}</code>
                <button onClick={() => copyUrl(full)} className={`text-xs shrink-0 transition-colors ${copied === full ? "text-emerald-400" : "text-blue-400 hover:text-blue-300"}`}>
                  {copied === full ? "✓" : "Kopyala"}
                </button>
                <span className="text-xs text-slate-500 shrink-0 hidden sm:block">{note}</span>
              </div>
            );
          })}
        </div>

        {/* Config */}
        {cfg && (
          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Ayarlar</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: "auto_run_on_pr" as const, label: "PR açıldığında çalıştır" },
                { key: "auto_run_on_push" as const, label: "Push'ta çalıştır" },
                { key: "notify_pr" as const, label: "PR'a sonuç yorumu yaz" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={(cfg as Record<string, unknown>)[key] as boolean}
                    onChange={e => setCfg({...cfg, [key]: e.target.checked})}
                    className="rounded border-slate-600" />
                  {label}
                </label>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Tarayıcı</label>
                <select className={inputCls} value={cfg.run_browser} onChange={e => setCfg({...cfg, run_browser: e.target.value})}>
                  {["chromium","firefox","webkit"].map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Smoke Markers</label>
                <input className={inputCls} value={cfg.smoke_markers} onChange={e => setCfg({...cfg, smoke_markers: e.target.value})} />
              </div>
              <div className="col-span-2">
                <label className="text-xs text-slate-400 block mb-1">GitHub Token</label>
                <input type="password" className={`${inputCls} font-mono`} placeholder="ghp_xxxx..." value={cfg.github_token} onChange={e => setCfg({...cfg, github_token: e.target.value})} />
              </div>
            </div>
            <button onClick={saveConfig} disabled={saving}
              className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-colors ${saved ? "bg-emerald-600 text-white" : "bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50"}`}>
              {saved ? "✓ Kaydedildi" : saving ? "Kaydediliyor…" : "Kaydet"}
            </button>
          </div>
        )}

        {/* Recent webhook events */}
        {events.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Son Webhook Olayları</h3>
            {events.slice(0, 5).map(ev => {
              const ss = SOURCE_STYLES[ev.source] ?? SOURCE_STYLES.generic;
              return (
                <div key={ev.id} className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium shrink-0 ${ss.bg} ${ss.text}`}>{ev.source}</span>
                    <span className="text-xs text-slate-300 truncate">{ev.pr_title || ev.event_type}</span>
                    {ev.risk_level && (
                      <span className={`rounded-full px-1.5 py-0.5 border text-xs font-medium shrink-0 ${RISK_STYLES[ev.risk_level] ?? RISK_STYLES.low}`}>
                        {ev.risk_level}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {ev.processed && <span className="text-emerald-400 text-xs">✓</span>}
                    <span className="text-xs text-slate-500">{new Date(ev.received_at).toLocaleTimeString("tr-TR")}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </SectionCard>
  );
}

export default function CicdPage() {
  const projectId = useRouteParam("projectId");
  const [filter, setFilter] = useState<string>("all");
  const [triggering, setTriggering] = useState(false);
  const [triggerResult, setTriggerResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const { data, loading, refresh } = useFetch<{ events: CicdEvent[]; total: number }>(
    `/api/v1/cicd/events${filter !== "all" ? `?source=${filter}` : ""}`
  );
  const events = data?.events ?? [];

  const backendBase = typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000";

  async function handleManualTrigger() {
    setTriggering(true);
    setTriggerResult(null);
    try {
      const res = await apiFetch<{ triggered?: boolean; error?: string }>(`/api/v1/cicd/trigger/${projectId}`, {
        method: "POST", json: { source: "manual", tag: "smoke" },
      });
      setTriggerResult({ ok: !!res.triggered, msg: res.triggered ? "Smoke testleri başlatıldı" : `Hata: ${res.error}` });
      refresh();
    } catch (e: unknown) {
      setTriggerResult({ ok: false, msg: `Hata: ${e instanceof Error ? e.message : String(e)}` });
    } finally { setTriggering(false); }
  }

  function copyUrl(url: string) {
    navigator.clipboard.writeText(url);
    setCopied(url);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="cicd-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
        }
        title="CI/CD Entegrasyonu"
        description="GitHub, GitLab ve Jenkins'ten otomatik test tetiklemeleri"
        right={
          <button
            onClick={handleManualTrigger}
            disabled={triggering}
            className="flex items-center gap-2 px-4 py-1.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
          >
            {triggering ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : null}
            {triggering ? "Tetikleniyor…" : "Manuel Tetikle (Smoke)"}
          </button>
        }
      />

      <FlowGuideCard
        projectId={projectId}
        stage="execute"
        title="CI/CD ve otomatik kosu akisi"
        description="Webhook ve pipeline entegrasyonlarını sabitleyin, ardından kalite koşularını otomatik tetikleyip olay akışını izleyin."
        nextLabel="Kosulari ac"
        nextHref={`/p/${projectId}/executions`}
        supportLinks={[
          { label: "Kosular", href: `/p/${projectId}/executions` },
          { label: "Raporlar", href: `/p/${projectId}/reports` },
          { label: "AI Asistan", href: `/p/${projectId}/ai-chat` },
        ]}
      />

      {triggerResult && (
        <div className={`rounded-xl px-4 py-3 text-sm border ${triggerResult.ok ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300" : "bg-red-500/10 border-red-500/20 text-red-300"}`}>
          {triggerResult.msg}
        </div>
      )}

      {/* Webhook URLs */}
      <SectionCard
        title="Webhook URL'leri"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>}
      >
        <div className="space-y-3">
          {[
            { label: "GitHub Actions", path: "/api/v1/cicd/webhook/github", note: "Repo Settings → Webhooks → Content type: application/json" },
            { label: "GitLab CI", path: "/api/v1/cicd/webhook/gitlab", note: "Project Settings → Webhooks → Push/Pipeline events" },
            { label: "Jenkins", path: "/api/v1/cicd/webhook/jenkins", note: "Notification plugin veya Post-build action URL" },
          ].map(({ label, path, note }) => {
            const full = `${backendBase}${path}`;
            return (
              <div key={path} className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-300 w-32 shrink-0">{label}</span>
                  <code className="flex-1 rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-xs font-mono text-slate-300 select-all truncate">{full}</code>
                  <button onClick={() => copyUrl(full)} className={`text-xs shrink-0 transition-colors ${copied === full ? "text-emerald-400" : "text-blue-400 hover:text-blue-300"}`}>
                    {copied === full ? "✓ Kopyalandı" : "Kopyala"}
                  </button>
                </div>
                <p className="text-xs text-slate-500 ml-32">{note}</p>
              </div>
            );
          })}
        </div>
      </SectionCard>

      {/* GitHub Actions Entegrasyon Kılavuzu */}
      <GithubActionsPanel projectId={projectId} />

      {/* Engine Webhook Config */}
      <EngineWebhookPanel />

      {/* Events */}
      <SectionCard
        title="CI/CD Olayları"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h7" /></svg>}
        right={
          <div className="flex items-center gap-1">
            {["all", "github", "gitlab", "jenkins"].map(s => (
              <button key={s} onClick={() => { setFilter(s); refresh(); }}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${filter === s ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}>
                {s === "all" ? "Tümü" : SOURCE_STYLES[s]?.label ?? s}
              </button>
            ))}
            <button onClick={refresh} className="ml-1 text-xs text-slate-500 hover:text-white transition-colors">↻</button>
          </div>
        }
        noPad
      >
        {loading ? (
          <div className="py-16 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-slate-700 border-t-blue-400 rounded-full animate-spin" />
            Yükleniyor…
          </div>
        ) : events.length === 0 ? (
          <div className="p-8">
            <EmptyState icon="🔌" title="CI/CD olayı yok" description="Webhook URL'lerini yukarıdaki adreslere ekleyin" />
          </div>
        ) : (
          events.map(ev => {
            const ss = SOURCE_STYLES[ev.source] ?? SOURCE_STYLES.github;
            return (
              <div key={ev.id} className="flex items-start justify-between px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30 gap-4" data-testid={`cicd-event-${ev.id}`}>
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 rounded px-2 py-0.5 text-xs font-medium shrink-0 ${ss.bg} ${ss.text}`}>{ss.label}</span>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-white">{ev.event_type}</span>
                      {ev.project_ref && <span className="text-xs text-slate-500 font-mono">{ev.project_ref}</span>}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {Object.entries(ev.payload_summary).map(([k, v]) =>
                        v ? (
                          <span key={k} className="text-xs text-slate-500">
                            <span className="font-medium text-slate-400">{k}:</span> {String(v)}
                          </span>
                        ) : null
                      )}
                    </div>
                  </div>
                </div>
                <span className="text-xs text-slate-500 whitespace-nowrap">
                  {new Date(ev.received_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" })}
                </span>
              </div>
            );
          })
        )}
      </SectionCard>
    </div>
  );
}
