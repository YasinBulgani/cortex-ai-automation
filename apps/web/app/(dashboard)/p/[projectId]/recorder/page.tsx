"use client";

import { useState, useEffect } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
  StatCard,
  MetricRow,
  CodeBlock,
} from "@/components/nexus";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const PROXY = "/api/v1/automation/proxy";

type RecordingSession = {
  id: string;
  url: string;
  status: "recording" | "completed" | "error";
  action_count: number;
  created_at: string;
};

type SavedSession = {
  file: string;
  path: string;
  name: string;
  domain: string;
  action_count: number;
  started_at: string;
};

type GeneratedCode = {
  code: string;
  format: string;
};

type TabId = "record" | "sessions" | "generate";

const TABS: TabId[] = ["record", "sessions", "generate"];

const TAB_LABELS: Record<TabId, string> = {
  record: "Kayıt",
  sessions: "Oturumlar",
  generate: "Kod Üret",
};

const FORMAT_LABELS: Record<string, { label: string }> = {
  cucumber: { label: "Cucumber" },
  playwright: { label: "Playwright" },
  selenium: { label: "Selenium" },
  cypress: { label: "Cypress" },
};

export default function RecorderPage() {
  const projectId = useRouteParam("projectId");
  const [url, setUrl] = useState("");
  const [recording, setRecording] = useState(false);
  const [activeSessions, setActiveSessions] = useState<RecordingSession[]>([]);
  const [savedSessions, setSavedSessions] = useState<SavedSession[]>([]);
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<GeneratedCode | null>(null);
  const [generating, setGenerating] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState("cucumber");
  const [activeTab, setActiveTab] = useState<TabId>("record");

  async function loadSavedSessions() {
    setLoadingSaved(true);
    try {
      const res = await apiFetch<{ ok: boolean; sessions: SavedSession[] }>(`${PROXY}/api/recorder/sessions`);
      setSavedSessions(res.sessions ?? []);
    } catch {
      setSavedSessions([]);
    } finally {
      setLoadingSaved(false);
    }
  }

  useEffect(() => { loadSavedSessions(); }, []);

  async function startRecording() {
    if (!url.trim()) return;
    setRecording(true);
    try {
      const res = await apiFetch<{ session_id: string; ok: boolean }>(
        `${PROXY}/api/recorder/start`,
        { method: "POST", json: { url } },
      );
      if (res.ok) {
        setActiveSessions(prev => [
          { id: res.session_id, url, status: "recording", action_count: 0, created_at: new Date().toISOString() },
          ...prev,
        ]);
      }
    } catch {
      alert("Kayıt başlatılamadı. Engine çalışıyor mu?");
    } finally {
      setRecording(false);
    }
  }

  async function stopRecording(session: RecordingSession) {
    try {
      const res = await apiFetch<{ ok: boolean; action_count: number }>(`${PROXY}/api/recorder/${session.id}/stop`, { method: "POST" });
      setActiveSessions(prev => prev.map(s => (s.id === session.id ? { ...s, status: "completed" as const, action_count: res.action_count } : s)));
      loadSavedSessions();
    } catch {
      alert("Kayıt durdurulamadı");
    }
  }

  async function deleteSession(file: string) {
    if (!confirm("Bu oturum silinsin mi?")) return;
    await apiFetch(`${PROXY}/api/recorder/sessions/${file}`, { method: "DELETE" });
    loadSavedSessions();
  }

  async function generateCode(file: string) {
    setGenerating(true);
    try {
      const res = await apiFetch<{ ok: boolean; code: string; format: string }>(
        `${PROXY}/api/recorder/sessions/${file}/generate`,
        { method: "POST", json: { format: selectedFormat } },
      );
      if (res.ok) {
        setGeneratedCode({ code: res.code, format: res.format ?? selectedFormat });
        setActiveTab("generate");
      }
    } catch {
      alert("Kod üretilemedi");
    } finally {
      setGenerating(false);
    }
  }

  const inputCls = "flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="recorder-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        }
        title="Test Kaydedici"
        description="Tarayıcı etkileşimlerini kaydedin ve test kodu üretin"
        badge={
          activeSessions.some(s => s.status === "recording") ? (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
              Kayıt
            </span>
          ) : undefined
        }
      />

      {/* Stats */}
      <MetricRow cols={3}>
        <StatCard
          label="Aktif Kayıt"
          value={activeSessions.filter(s => s.status === "recording").length}
          color={activeSessions.filter(s => s.status === "recording").length > 0 ? "red" : "slate"}
        />
        <StatCard label="Kaydedilmiş" value={savedSessions.length} color={savedSessions.length > 0 ? "emerald" : "slate"} />
        <StatCard
          label="Toplam Aksiyon"
          value={savedSessions.reduce((acc, s) => acc + (s.action_count ?? 0), 0)}
          color="blue"
        />
      </MetricRow>

      {/* Tab nav */}
      <Tabs variant="pill" value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
        <TabsList>
          {TABS.map(tab => (
            <TabsTrigger
              key={tab}
              value={tab}
              disabled={tab === "generate" && savedSessions.length === 0}
            >
              {TAB_LABELS[tab]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Record tab */}
      {activeTab === "record" && (
        <>
          <SectionCard title="Yeni Kayıt Başlat">
            <div className="flex gap-3">
              <input
                className={inputCls}
                type="url"
                placeholder="https://example.com"
                value={url}
                onChange={e => setUrl(e.target.value)}
                onKeyDown={e => e.key === "Enter" && startRecording()}
                data-testid="recorder-url-input"
              />
              <button
                onClick={startRecording}
                disabled={recording || !url.trim()}
                data-testid="recorder-btn-start"
                className="px-5 py-2.5 text-sm font-medium bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-all"
              >
                {recording ? "Başlatılıyor…" : "Kaydı Başlat"}
              </button>
            </div>
          </SectionCard>

          {activeSessions.length > 0 && (
            <SectionCard title="Aktif Oturumlar" right={<span className="text-xs text-slate-500">{activeSessions.length} oturum</span>} noPad>
              {activeSessions.map(s => (
                <div key={s.id} className="flex items-center justify-between px-4 py-3 border-b border-slate-800 last:border-0" data-testid={`recorder-session-${s.id}`}>
                  <div>
                    <p className="text-sm font-medium text-white">{s.url}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{s.id.slice(0, 8)} · {s.action_count} aksiyon</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${s.status === "recording" ? "bg-red-500/10 border-red-500/20 text-red-400" : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${s.status === "recording" ? "bg-red-400 animate-pulse" : "bg-emerald-400"}`} />
                      {s.status === "recording" ? "Kayıt Devam Ediyor" : "Tamamlandı"}
                    </span>
                    {s.status === "recording" && (
                      <button onClick={() => stopRecording(s)} data-testid={`recorder-btn-stop-${s.id}`} className="px-3 py-1.5 text-xs font-medium text-slate-300 border border-slate-700 rounded-lg hover:border-slate-500 transition-all">
                        Durdur
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </SectionCard>
          )}
        </>
      )}

      {/* Sessions tab */}
      {activeTab === "sessions" && (
        <SectionCard
          title="Kaydedilmiş Oturumlar"
          right={<button onClick={loadSavedSessions} className="text-xs text-slate-400 hover:text-white transition-colors">Yenile</button>}
          noPad
        >
          {loadingSaved ? (
            <div className="py-16 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-slate-700 border-t-blue-400 rounded-full animate-spin" />
              Yükleniyor…
            </div>
          ) : savedSessions.length === 0 ? (
            <div className="p-8">
              <EmptyState icon="📂" title="Kaydedilmiş oturum yok" description="Bir tarayıcı oturumu kaydedin" />
            </div>
          ) : (
            savedSessions.map(s => (
              <div key={s.file} className="flex items-center justify-between px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30 group">
                <div>
                  <p className="text-sm font-medium text-white">{s.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {s.domain} · {s.action_count} aksiyon · {new Date(s.started_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" })}
                  </p>
                </div>
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <select
                    value={selectedFormat}
                    onChange={e => setSelectedFormat(e.target.value)}
                    className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                  >
                    {Object.entries(FORMAT_LABELS).map(([key, { label }]) => (
                      <option key={key} value={key}>{label}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => generateCode(s.file)}
                    disabled={generating}
                    data-testid={`recorder-btn-generate-${s.file}`}
                    className="px-3 py-1.5 text-xs font-medium text-blue-400 border border-blue-500/30 rounded-lg hover:border-blue-500/60 hover:bg-blue-500/10 transition-all disabled:opacity-50"
                  >
                    {generating ? "Üretiliyor…" : "Kod Üret"}
                  </button>
                  <button
                    onClick={() => deleteSession(s.file)}
                    data-testid={`recorder-btn-delete-${s.file}`}
                    className="px-3 py-1.5 text-xs font-medium text-red-400 border border-red-500/30 rounded-lg hover:border-red-500/60 hover:bg-red-500/10 transition-all"
                  >
                    Sil
                  </button>
                </div>
              </div>
            ))
          )}
        </SectionCard>
      )}

      {/* Generate tab */}
      {activeTab === "generate" && (
        <SectionCard title="Üretilen Kod">
          {generatedCode?.code ? (
            <CodeBlock
              code={generatedCode.code}
              language={FORMAT_LABELS[generatedCode.format]?.label ?? generatedCode.format}
              maxHeight="400px"
            />
          ) : (
            <div className="p-8">
              <EmptyState icon="💻" title="Henüz kod üretilmedi" description="Oturumlar sekmesinden bir oturum seçip Kod Üret butonuna tıklayın" />
            </div>
          )}
        </SectionCard>
      )}
    </div>
  );
}
