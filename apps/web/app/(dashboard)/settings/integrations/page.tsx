"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2, XCircle, Loader2, ExternalLink, Trash2,
  Settings, Zap, RefreshCw, Eye, EyeOff,
} from "lucide-react";

// ── Jira Logo SVG ─────────────────────────────────────────────────────────────
function JiraLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M11.571 11.513H0a5.218 5.218 0 005.232 5.215l2.357.004v2.31A5.218 5.218 0 0012.8 24V12.518a1.005 1.005 0 00-1.229-.005zM20.066 3.003h-11.6a5.218 5.218 0 005.232 5.215l2.357.004v2.31A5.218 5.218 0 0021.295 15.74V4.232a1.005 1.005 0 00-1.229-.005v-.003l-.001-.001.001.003z" />
    </svg>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface JiraStatus {
  configured: boolean;
  url: string;
  email: string;
  project_key: string;
}

interface JiraConfig {
  configured: boolean;
  url: string;
  email: string;
  project_key: string;
  token_hint: string;
}

interface TestResult {
  ok: boolean;
  user?: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────
function useJiraConfig() {
  return useQuery<JiraConfig>({
    queryKey: ["jira-config"],
    queryFn: async () => {
      const r = await fetch("/api/jira/config", { credentials: "include" });
      if (!r.ok) throw new Error("Config alınamadı");
      return r.json();
    },
    staleTime: 30_000,
  });
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function IntegrationsPage() {
  const qc = useQueryClient();
  const { data: config, isLoading } = useJiraConfig();

  const [form, setForm] = useState({ url: "", email: "", token: "", project_key: "" });
  const [showToken, setShowToken] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [editing, setEditing] = useState(false);

  // Populate form when config loaded
  const handleEdit = () => {
    setForm({
      url: config?.url ?? "",
      email: config?.email ?? "",
      token: "",
      project_key: config?.project_key ?? "",
    });
    setEditing(true);
    setTestResult(null);
  };

  const saveMut = useMutation({
    mutationFn: async () => {
      const r = await fetch("/api/jira/config", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!r.ok) {
        const d = await r.json() as { detail?: string };
        throw new Error(d.detail ?? "Kaydetme hatası");
      }
      return r.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jira-config"] });
      setEditing(false);
      setTestResult(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async () => {
      const r = await fetch("/api/jira/config", {
        method: "DELETE",
        credentials: "include",
      });
      if (!r.ok) throw new Error("Silme hatası");
      return r.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jira-config"] });
      setEditing(false);
      setTestResult(null);
    },
  });

  const handleTest = async () => {
    setTestLoading(true);
    setTestResult(null);
    try {
      const r = await fetch("/api/jira/test-connection", {
        method: "POST",
        credentials: "include",
      });
      const d = await r.json() as TestResult & { detail?: string };
      if (!r.ok) setTestResult({ ok: false, user: d.detail ?? "Bağlantı başarısız" });
      else setTestResult(d);
    } catch {
      setTestResult({ ok: false, user: "Sunucuya ulaşılamadı" });
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Zap className="h-5 w-5 text-violet-400" />
          Entegrasyonlar
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Harici servislerle bağlantı kurarak test süreçlerini otomatikleştirin.
        </p>
      </div>

      {/* Jira Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        {/* Card Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600/20 border border-blue-500/30">
              <JiraLogo className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <h2 className="text-[15px] font-bold text-white">Jira</h2>
              <p className="text-[12px] text-slate-500">Atlassian Jira Cloud & Server</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-slate-600" />
            ) : config?.configured ? (
              <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 text-[11px] font-semibold text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" /> Bağlı
              </span>
            ) : (
              <span className="flex items-center gap-1.5 rounded-full bg-slate-700/50 border border-slate-700 px-3 py-1 text-[11px] font-semibold text-slate-500">
                <XCircle className="h-3.5 w-3.5" /> Bağlı Değil
              </span>
            )}
          </div>
        </div>

        {/* Card Body */}
        <div className="px-6 py-5 space-y-5">

          {/* Connected summary */}
          {config?.configured && !editing && (
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600 mb-1">Jira URL</p>
                  <a href={config.url} target="_blank" rel="noreferrer"
                    className="text-[13px] text-blue-400 hover:underline flex items-center gap-1 truncate">
                    {config.url} <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600 mb-1">E-posta</p>
                  <p className="text-[13px] text-slate-300">{config.email}</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600 mb-1">API Token</p>
                  <p className="text-[13px] text-slate-500 font-mono">{config.token_hint || "***"}</p>
                </div>
                {config.project_key && (
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600 mb-1">Varsayılan Proje</p>
                    <p className="text-[13px] text-slate-300 font-mono">{config.project_key}</p>
                  </div>
                )}
              </div>

              {/* Test result */}
              {testResult && (
                <div className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-[12px] font-medium ${
                  testResult.ok
                    ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                    : "bg-red-500/10 border border-red-500/20 text-red-400"
                }`}>
                  {testResult.ok
                    ? <><CheckCircle2 className="h-4 w-4" /> Bağlantı başarılı — {testResult.user}</>
                    : <><XCircle className="h-4 w-4" /> {testResult.user}</>
                  }
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={handleTest} disabled={testLoading}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-[12px] font-medium text-slate-300 hover:border-slate-600 hover:text-white disabled:opacity-40 transition-colors">
                  {testLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  Bağlantıyı Test Et
                </button>
                <button type="button" onClick={handleEdit}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-[12px] font-medium text-slate-300 hover:border-blue-500/40 hover:text-blue-300 transition-colors">
                  <Settings className="h-3.5 w-3.5" /> Düzenle
                </button>
                <button type="button" onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
                  className="ml-auto flex items-center gap-1.5 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-[12px] font-medium text-red-400 hover:border-red-500/40 hover:bg-red-500/10 disabled:opacity-40 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" /> Bağlantıyı Kaldır
                </button>
              </div>
            </div>
          )}

          {/* Setup / Edit form */}
          {(!config?.configured || editing) && (
            <div className="space-y-4">
              <p className="text-[12px] text-slate-500">
                Atlassian hesabınızla bağlantı kurarak Jira issue'larından otomatik test senaryoları oluşturabilirsiniz.
              </p>

              {/* URL */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                  Jira URL <span className="text-red-400">*</span>
                </label>
                <input
                  value={form.url}
                  onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
                  placeholder="https://your-org.atlassian.net"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none focus:ring-2 focus:ring-blue-500/10"
                />
              </div>

              {/* Email */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                  Atlassian E-posta <span className="text-red-400">*</span>
                </label>
                <input
                  type="email"
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  placeholder="you@company.com"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none focus:ring-2 focus:ring-blue-500/10"
                />
              </div>

              {/* API Token */}
              <div>
                <label className="mb-1.5 flex items-center justify-between text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                  API Token <span className="text-red-400">*</span>
                  <a
                    href="https://id.atlassian.com/manage-profile/security/api-tokens"
                    target="_blank" rel="noreferrer"
                    className="normal-case text-[11px] font-normal text-blue-400 hover:underline flex items-center gap-1"
                  >
                    Token oluştur <ExternalLink className="h-3 w-3" />
                  </a>
                </label>
                <div className="relative">
                  <input
                    type={showToken ? "text" : "password"}
                    value={form.token}
                    onChange={e => setForm(f => ({ ...f, token: e.target.value }))}
                    placeholder={config?.configured ? "Değiştirmek için yeni token girin" : "ATATT3xFfGF0..."}
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 pr-10 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none focus:ring-2 focus:ring-blue-500/10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(s => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400 transition-colors"
                  >
                    {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Default project key */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                  Varsayılan Proje <span className="text-slate-700">(opsiyonel)</span>
                </label>
                <input
                  value={form.project_key}
                  onChange={e => setForm(f => ({ ...f, project_key: e.target.value.toUpperCase() }))}
                  placeholder="PROJ"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-[13px] text-white font-mono placeholder-slate-600 focus:border-blue-500/60 focus:outline-none focus:ring-2 focus:ring-blue-500/10"
                />
              </div>

              {/* Error */}
              {saveMut.isError && (
                <div className="rounded-xl border border-red-500/30 bg-red-500/8 px-4 py-3 text-[12px] text-red-400">
                  {(saveMut.error as Error).message}
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-2 pt-1">
                {editing && (
                  <button type="button" onClick={() => setEditing(false)}
                    className="rounded-xl border border-slate-700 px-4 py-2.5 text-[13px] text-slate-400 hover:text-white transition-colors">
                    İptal
                  </button>
                )}
                <button
                  type="button"
                  disabled={saveMut.isPending || !form.url || !form.email || (!form.token && !config?.configured)}
                  onClick={() => saveMut.mutate()}
                  className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-2.5 text-[13px] font-semibold text-white disabled:opacity-40 hover:from-blue-500 hover:to-indigo-500 transition-all shadow-lg shadow-blue-900/20"
                >
                  {saveMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  {saveMut.isPending ? "Kaydediliyor…" : editing ? "Güncelle" : "Bağlan & Kaydet"}
                </button>
              </div>
            </div>
          )}

          {/* How it works */}
          {!editing && !config?.configured && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-600">Nasıl Çalışır?</p>
              <div className="space-y-1.5">
                {[
                  "Jira projenizden PBI, Story, Epic veya Bug seçin",
                  "AI issue'yu analiz ederek BDD test senaryoları üretir",
                  "Senaryoları düzenleyip Senaryo Oluşturucu'ya kaydedin",
                ].map((step, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <span className="shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-[10px] font-bold text-slate-500">{i + 1}</span>
                    <p className="text-[12px] text-slate-400">{step}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Future integrations placeholder */}
      <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/20 px-6 py-8 text-center">
        <p className="text-[13px] font-medium text-slate-600">Yakında: GitHub, GitLab, Slack, Linear…</p>
        <p className="text-[11px] text-slate-700 mt-1">Daha fazla entegrasyon yolda</p>
      </div>
    </div>
  );
}
