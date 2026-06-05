"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useProject } from "@/lib/useProject";
import { Sparkles, Plus, X, ChevronRight, Bot, CheckCircle2, Clock, Eye, Loader2, FileText, Globe, Image, Wand2, Check, ExternalLink, Search, Settings, AlertCircle } from "lucide-react";
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

interface JiraIssue {
  key: string;
  summary: string;
  description: string;
  issue_type: string;
  status: string;
  priority: string;
  assignee: string | null;
  labels: string[];
  url: string;
}
type AiSource = "text" | "file" | "url" | "jira";

interface AiGenScenario {
  title: string;
  description: string;
  tags: string[];
  steps: { keyword: string; text: string }[];
  selected: boolean;
}

const BDD_KW_COLORS: Record<string, string> = {
  given: "bg-amber-500/20 text-amber-300",
  when:  "bg-blue-500/20 text-blue-300",
  then:  "bg-emerald-500/20 text-emerald-300",
  and:   "bg-slate-700 text-slate-400",
};

const PRIORITIES = ["P0", "P1", "P2", "P3"];
const BDD_TYPES: BddStep["type"][] = ["given", "when", "then", "and"];

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

  // ── AI tab state ──
  const [aiSource, setAiSource]       = useState<AiSource>("text");
  const [aiContext, setAiContext]      = useState("");
  const [aiExtra, setAiExtra]         = useState("");
  const [aiUrl, setAiUrl]             = useState("");
  const [fileInfo, setFileInfo]        = useState<string | null>(null);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiProgress, setAiProgress]   = useState("");
  const [aiScenarios, setAiScenarios] = useState<AiGenScenario[]>([]);
  const [aiError, setAiError]         = useState("");
  const [saving, setSaving]            = useState(false);
  const [saved, setSaved]              = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // ── Jira state ──
  const [jiraStatus, setJiraStatus]         = useState<"idle" | "checking" | "ok" | "error">("idle");
  const [jiraConfigured, setJiraConfigured] = useState(false);
  const [jiraProjects, setJiraProjects]     = useState<{ key: string; name: string }[]>([]);
  const [jiraSelProject, setJiraSelProject] = useState("");
  const [jiraIssues, setJiraIssues]         = useState<JiraIssue[]>([]);
  const [jiraSearch, setJiraSearch]         = useState("");
  const [jiraIssueType, setJiraIssueType]   = useState("");   // "" = tümü
  const [jiraLoading, setJiraLoading]       = useState(false);
  const [jiraSelIssue, setJiraSelIssue]     = useState<JiraIssue | null>(null);
  const [jiraErr, setJiraErr]               = useState("");
  const [jiraSetupOpen, setJiraSetupOpen]   = useState(false);
  const [jiraUrl, setJiraUrl]               = useState("");
  const [jiraEmail, setJiraEmail]           = useState("");
  const [jiraToken, setJiraToken]           = useState("");
  const [jiraSaving, setJiraSaving]         = useState(false);

  // ── Manual tab state ──
  const [title, setTitle]     = useState("");
  const [desc, setDesc]       = useState("");
  const [priority, setPriority] = useState("P1");
  const [tags, setTags]       = useState("");
  const [manSteps, setManSteps] = useState<BddStep[]>([
    { type: "given", text: "" },
    { type: "when",  text: "" },
    { type: "then",  text: "" },
  ]);
  const [manError, setManError] = useState("");
  const [manLoading, setManLoading] = useState(false);

  // close on Escape
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  // ── AI: file upload ──
  const handleFileUpload = async (file: File) => {
    setAiError(""); setAiProgress("Dosya yükleniyor…");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`/api/v1/tspm/projects/${projectId}/wizard/upload-document`, {
        method: "POST", body: fd, credentials: "include",
      });
      const data = await res.json() as { full_text?: string; filename?: string; word_count?: number };
      if (!res.ok) throw new Error((data as { detail?: string }).detail ?? "Yükleme hatası");
      setFileInfo(`${data.filename ?? file.name} · ${(data.word_count ?? 0).toLocaleString()} kelime`);
      setAiContext(data.full_text ?? "");
      setAiProgress("");
    } catch (e: unknown) {
      setAiError(e instanceof Error ? e.message : "Dosya yükleme başarısız");
      setAiProgress("");
    }
  };

  // ── AI: crawl URL ──
  const crawlUrl = async () => {
    if (!aiUrl.trim()) return;
    setAiGenerating(true); setAiError(""); setAiProgress("Sayfa taranıyor…");
    try {
      const res = await apiFetch<{ content?: string; text?: string }>(
        `/api/v1/tspm/projects/${projectId}/wizard/crawl`,
        { method: "POST", json: { url: aiUrl.trim() } }
      );
      setAiContext((res.content ?? res.text ?? "").slice(0, 5000));
      setAiProgress("");
    } catch (e: unknown) {
      setAiError(e instanceof Error ? e.message : "URL tarama başarısız");
      setAiProgress("");
    } finally { setAiGenerating(false); }
  };

  // ── Jira: check config ──
  const checkJiraStatus = async () => {
    setJiraStatus("checking"); setJiraErr("");
    try {
      const res = await fetch("/api/jira/status", { credentials: "include" });
      if (!res.ok) throw new Error("Jira durumu alınamadı");
      const data = await res.json() as { configured: boolean; url?: string; email?: string };
      setJiraConfigured(data.configured);
      if (data.configured) {
        setJiraStatus("ok");
        // Projeleri yükle
        const pRes = await fetch("/api/jira/projects", { credentials: "include" });
        if (pRes.ok) {
          const projects = await pRes.json() as { key: string; name: string }[];
          setJiraProjects(Array.isArray(projects) ? projects : []);
        }
      } else {
        setJiraStatus("error");
        setJiraUrl(data.url ?? "");
        setJiraEmail(data.email ?? "");
      }
    } catch {
      setJiraStatus("error");
      setJiraConfigured(false);
    }
  };

  // ── Jira: save config ──
  const saveJiraConfig = async () => {
    if (!jiraUrl.trim() || !jiraEmail.trim() || !jiraToken.trim()) {
      setJiraErr("URL, e-posta ve token zorunludur"); return;
    }
    setJiraSaving(true); setJiraErr("");
    try {
      const res = await fetch("/api/jira/config", {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: jiraUrl.trim(), email: jiraEmail.trim(), token: jiraToken.trim(), project_key: "" }),
      });
      if (!res.ok) { const d = await res.json() as { detail?: string }; throw new Error(d.detail ?? "Kaydetme hatası"); }
      setJiraSetupOpen(false);
      checkJiraStatus();
    } catch (e: unknown) {
      setJiraErr(e instanceof Error ? e.message : "Bağlantı kurulamadı");
    } finally { setJiraSaving(false); }
  };

  // ── Jira: load issues ──
  const loadJiraIssues = async (projectKey: string, search = "", issueType = jiraIssueType) => {
    if (!projectKey) return;
    setJiraLoading(true); setJiraErr(""); setJiraIssues([]);
    try {
      const qs = new URLSearchParams({ max_results: "40" });
      if (search.trim()) qs.set("search", search.trim());
      if (issueType.trim()) qs.set("issue_type", issueType.trim());
      const res = await fetch(`/api/jira/projects/${projectKey}/issues?${qs}`, { credentials: "include" });
      if (!res.ok) { const d = await res.json() as { detail?: string }; throw new Error(d.detail ?? "Issue'lar yüklenemedi"); }
      const data = await res.json() as JiraIssue[];
      setJiraIssues(Array.isArray(data) ? data : []);
    } catch (e: unknown) {
      setJiraErr(e instanceof Error ? e.message : "Jira hatası");
    } finally { setJiraLoading(false); }
  };

  // ── Jira: select issue → extract cases ──
  const extractFromJiraIssue = async (issue: JiraIssue) => {
    setJiraSelIssue(issue);
    // Jira payload'ı ingestion webhook'una gönder
    const jiraPayload = {
      issue: {
        key: issue.key,
        fields: { summary: issue.summary, description: issue.description },
      },
    };
    // İngestion ile gereksinimleri parse et
    try {
      await apiFetch(
        `/api/v1/ingestion/jira/webhook?project_id=${projectId}`,
        { method: "POST", json: jiraPayload }
      );
    } catch { /* ingestion hata verse de devam et */ }

    // AI analiz için contexti hazırla
    const context = `Issue: ${issue.key}\nBaşlık: ${issue.summary}\n\n${issue.description}`;
    setAiContext(context);
    setAiSource("text");
    // Otomatik analiz başlat
    setAiGenerating(true); setAiError(""); setAiScenarios([]); setAiProgress("Jira issue analiz ediliyor…");
    try {
      const res = await apiFetch<{ bdd_scenarios?: AiGenScenario[]; manual_tests?: { title: string; steps: string[] }[] }>(
        `/api/v1/tspm/projects/${projectId}/wizard/analyze`,
        { method: "POST", json: { text: context, extra_instructions: `Jira issue ${issue.key} için test senaryoları üret. Issue tipi: ${issue.issue_type}. Etiketler: ${issue.labels.join(", ")}` } }
      );
      const bdd = (res.bdd_scenarios ?? []).map(s => ({ ...s, selected: true }));
      const manual = (res.manual_tests ?? []).map(m => ({
        title: m.title, description: "", tags: [issue.key.toLowerCase(), "jira"],
        steps: m.steps.map(t => ({ keyword: "Adım", text: t })), selected: true,
      }));
      setAiScenarios([...bdd, ...manual]);
      setAiProgress("");
    } catch {
      // Fallback: basit senaryo
      setAiScenarios([{
        title: `${issue.key}: ${issue.summary}`,
        description: issue.description.slice(0, 200),
        tags: [issue.key.toLowerCase(), "jira"],
        steps: [
          { keyword: "Given", text: "kullanıcı sisteme erişim sağlamıştır" },
          { keyword: "When", text: issue.summary },
          { keyword: "Then", text: "beklenen sonuç doğrulanır" },
        ],
        selected: true,
      }]);
      setAiProgress("");
    } finally { setAiGenerating(false); }
  };

  // ── AI: generate ──
  const generateWithAI = async () => {
    const text = aiContext.trim();
    if (!text) { setAiError("Analiz edilecek metin giriniz"); return; }
    setAiGenerating(true); setAiError(""); setAiScenarios([]); setAiProgress("AI analiz ediyor…");

    try {
      // Try powerful wizard/analyze first, fallback to generate-bdd
      let bddScenarios: AiGenScenario[] = [];
      try {
        const res = await apiFetch<{ bdd_scenarios?: AiGenScenario[]; manual_tests?: { title: string; steps: string[] }[] }>(
          `/api/v1/tspm/projects/${projectId}/wizard/analyze`,
          { method: "POST", json: { text, extra_instructions: aiExtra.trim() || undefined } }
        );
        bddScenarios = (res.bdd_scenarios ?? []).map(s => ({ ...s, selected: true }));
        // Also add manual_tests as scenarios
        if (res.manual_tests?.length) {
          const manuals: AiGenScenario[] = res.manual_tests.map(m => ({
            title: m.title, description: "", tags: ["manual"],
            steps: m.steps.map(t => ({ keyword: "Adım", text: t })),
            selected: true,
          }));
          bddScenarios = [...bddScenarios, ...manuals];
        }
      } catch {
        // fallback to generate-bdd
        const res2 = await apiFetch<{ scenarios: AiGenScenario[] }>(
          `/api/v1/tspm/projects/${projectId}/scenarios/generate-bdd`,
          { method: "POST", json: { analysis_text: text, extra_instructions: aiExtra.trim() || undefined } }
        );
        bddScenarios = (res2.scenarios ?? []).map(s => ({ ...s, selected: true }));
      }

      if (bddScenarios.length === 0) {
        // Last fallback: mock from context
        bddScenarios = [{
          title: extractTitle(text),
          description: text.slice(0, 200),
          tags: ["ai-generated"],
          steps: generateFallbackSteps(text).map(s => ({ keyword: s.type.toUpperCase(), text: s.text })),
          selected: true,
        }];
      }
      setAiScenarios(bddScenarios);
      setAiProgress("");
    } catch (e: unknown) {
      setAiError(e instanceof Error ? e.message : "AI analiz başarısız");
      setAiProgress("");
    } finally { setAiGenerating(false); }
  };

  // ── AI: save selected ──
  const saveSelected = async () => {
    const toSave = aiScenarios.filter(s => s.selected);
    if (!toSave.length) { setAiError("En az bir senaryo seçin"); return; }
    setSaving(true); setAiError("");
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios/save-bdd`, {
        method: "POST",
        json: { scenarios: toSave.map(({ selected: _, ...rest }) => rest) },
      });
      setSaved(true);
      // Return first created scenario info so list updates
      const first = toSave[0];
      onCreated({ id: `ai-${Date.now()}`, title: first.title, description: first.description, status: "draft", project_id: projectId });
      setTimeout(onClose, 800);
    } catch (e: unknown) {
      setAiError(e instanceof Error ? e.message : "Kaydetme hatası");
    } finally { setSaving(false); }
  };

  // ── Manual: submit ──
  const handleManualSubmit = async () => {
    if (!title.trim()) { setManError("Başlık zorunlu"); return; }
    setManLoading(true); setManError("");
    try {
      const stepsText = manSteps.filter(s => s.text.trim()).map(s => `${s.type.toUpperCase()} ${s.text}`).join("\n");
      const s = await apiFetch<Scenario>(`/api/v1/tspm/projects/${projectId}/scenarios`, {
        method: "POST",
        json: {
          title: title.trim(),
          description: [desc.trim(), stepsText].filter(Boolean).join("\n\n") || undefined,
          status: "draft",
          priority,
          tags: tags.split(",").map(t => t.trim()).filter(Boolean),
        },
      });
      onCreated(s);
      onClose();
    } catch (e: unknown) {
      setManError(e instanceof Error ? e.message : "Oluşturulamadı");
    } finally { setManLoading(false); }
  };

  const selectedCount = aiScenarios.filter(s => s.selected).length;

  const AI_SOURCES: { id: AiSource; icon: React.ReactNode; label: string }[] = [
    { id: "text", icon: <FileText className="h-3.5 w-3.5" />, label: "Metin" },
    { id: "file", icon: <FileText className="h-3.5 w-3.5" />, label: "Dosya" },
    { id: "url",  icon: <Globe className="h-3.5 w-3.5" />,    label: "URL" },
    { id: "jira", icon: (
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M11.571 11.513H0a5.218 5.218 0 005.232 5.215l2.357.004v2.31A5.218 5.218 0 0012.8 24V12.518a1.005 1.005 0 00-1.229-.005zM20.066 3.003h-11.6a5.218 5.218 0 005.232 5.215l2.357.004v2.31A5.218 5.218 0 0021.295 15.74V4.232a1.005 1.005 0 00-1.229-.005v-.003l-.001-.001.001.003z"/>
        </svg>
      ), label: "Jira" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-3xl rounded-2xl border border-slate-700/80 bg-[#0d1117] shadow-2xl flex flex-col" style={{ maxHeight: "92vh" }}>

        {/* ── Header ── */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-blue-600 shadow-lg">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <h2 className="text-[15px] font-bold text-white leading-tight">Yeni Senaryo</h2>
              <p className="text-[11px] text-slate-500 leading-none">AI destekli veya manuel oluştur</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-800 hover:text-white transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ── Tabs ── */}
        <div className="flex border-b border-slate-800 px-2">
          <button onClick={() => setTab("ai")}
            className={`flex items-center gap-2 px-5 py-3.5 text-[13px] font-semibold border-b-2 transition-all ${
              tab === "ai"
                ? "border-violet-500 text-violet-300"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}>
            <Bot className="h-4 w-4" />
            AI ile Oluştur
            <span className="rounded-full bg-violet-500/20 px-1.5 py-0.5 text-[9px] font-black text-violet-400 tracking-wide">YENİ</span>
          </button>
          <button onClick={() => setTab("manual")}
            className={`flex items-center gap-2 px-5 py-3.5 text-[13px] font-semibold border-b-2 transition-all ${
              tab === "manual"
                ? "border-blue-500 text-blue-300"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}>
            <Plus className="h-4 w-4" />
            Manuel
          </button>
        </div>

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto">

          {/* ══ AI TAB ══════════════════════════════════════════════ */}
          {tab === "ai" && (
            <div className="p-6 space-y-5">

              {/* Source selector */}
              <div className="flex gap-2">
                {AI_SOURCES.map(src => (
                  <button key={src.id} type="button" onClick={() => {
                    setAiSource(src.id);
                    if (src.id === "jira" && jiraStatus === "idle") checkJiraStatus();
                  }}
                    className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-all ${
                      aiSource === src.id
                        ? "border-violet-500/60 bg-violet-500/10 text-violet-300"
                        : "border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-300"
                    }`}>
                    {src.icon} {src.label}
                  </button>
                ))}
              </div>

              {/* Text input */}
              {aiSource === "text" && (
                <div>
                  <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                    Gereksinim / Kabul Kriterleri / User Story
                  </label>
                  <textarea
                    value={aiContext}
                    onChange={e => setAiContext(e.target.value)}
                    rows={6}
                    autoFocus
                    placeholder={`Örn:
Kullanıcı geçerli email ve şifreyle giriş yapabilmeli.
Yanlış şifre girilince anlamlı hata mesajı gösterilmeli.
5 başarısız denemede hesap 30 dakika kilitlenmeli.
"Beni hatırla" seçilince 30 gün oturum açık kalmalı.`}
                    className="w-full rounded-xl border border-slate-700/80 bg-slate-900 px-4 py-3 text-[13px] text-white placeholder-slate-600 focus:border-violet-500/60 focus:outline-none focus:ring-2 focus:ring-violet-500/10 resize-none leading-relaxed"
                  />
                </div>
              )}

              {/* File upload */}
              {aiSource === "file" && (
                <div
                  onClick={() => fileRef.current?.click()}
                  onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFileUpload(f); }}
                  onDragOver={e => e.preventDefault()}
                  className="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-slate-700 bg-slate-900/50 p-10 cursor-pointer hover:border-violet-500/40 transition-colors"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-violet-400">
                    <Image className="h-5 w-5" />
                  </div>
                  {fileInfo ? (
                    <div className="text-center">
                      <p className="text-[13px] font-medium text-violet-300">{fileInfo}</p>
                      <p className="text-[11px] text-slate-500 mt-1">Yüklendi — analiz hazır</p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <p className="text-[13px] text-slate-300">Dosyayı sürükle veya tıkla</p>
                      <p className="text-[11px] text-slate-500 mt-1">PDF, DOCX, TXT, MD</p>
                    </div>
                  )}
                  {aiProgress && <p className="text-[11px] text-violet-400 animate-pulse">{aiProgress}</p>}
                  <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); }} />
                </div>
              )}

              {/* URL */}
              {aiSource === "url" && (
                <div>
                  <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Web Sayfası URL</label>
                  <div className="flex gap-2">
                    <input value={aiUrl} onChange={e => setAiUrl(e.target.value)}
                      placeholder="https://app.example.com/login"
                      className="flex-1 rounded-xl border border-slate-700/80 bg-slate-900 px-4 py-2.5 text-[13px] text-white placeholder-slate-600 focus:border-violet-500/60 focus:outline-none" />
                    <button type="button" onClick={crawlUrl} disabled={aiGenerating || !aiUrl.trim()}
                      className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-[12px] font-medium text-slate-300 hover:border-violet-500/40 hover:text-violet-300 disabled:opacity-40 transition-colors">
                      {aiGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : "Tara"}
                    </button>
                  </div>
                  {aiContext && (
                    <p className="mt-2 text-[11px] text-slate-500 line-clamp-2">{aiContext.slice(0, 200)}…</p>
                  )}
                </div>
              )}

              {/* ── JIRA PANEL ── */}
              {aiSource === "jira" && (
                <div className="space-y-4">
                  {jiraStatus === "checking" && (
                    <div className="flex items-center justify-center gap-2 py-8 text-slate-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-[13px]">Jira bağlantısı kontrol ediliyor…</span>
                    </div>
                  )}

                  {/* Yapılandırılmamış → Setup formu */}
                  {(jiraStatus === "error" || (jiraStatus !== "checking" && !jiraConfigured)) && (
                    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-4">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
                        <div>
                          <p className="text-[13px] font-semibold text-amber-300">Jira bağlantısı yapılandırılmamış</p>
                          <p className="text-[11px] text-amber-300/70 mt-0.5">Atlassian hesap bilgilerinizi girerek bağlanın.</p>
                        </div>
                      </div>

                      {!jiraSetupOpen ? (
                        <div className="flex gap-2">
                          <Link href="/settings/integrations" target="_blank"
                            className="flex items-center gap-2 rounded-xl bg-blue-600/20 border border-blue-500/40 px-4 py-2.5 text-[12px] font-semibold text-blue-300 hover:bg-blue-600/30 transition-colors">
                            <ExternalLink className="h-3.5 w-3.5" /> Settings'te Ayarla
                          </Link>
                          <button type="button" onClick={() => setJiraSetupOpen(true)}
                            className="flex items-center gap-2 rounded-xl bg-amber-600/20 border border-amber-500/40 px-4 py-2.5 text-[12px] font-semibold text-amber-300 hover:bg-amber-600/30 transition-colors">
                            <Settings className="h-3.5 w-3.5" /> Hızlı Kur
                          </button>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div>
                            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">Jira URL</label>
                            <input value={jiraUrl} onChange={e => setJiraUrl(e.target.value)}
                              placeholder="https://your-org.atlassian.net"
                              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none" />
                          </div>
                          <div>
                            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">E-posta</label>
                            <input value={jiraEmail} onChange={e => setJiraEmail(e.target.value)}
                              placeholder="you@company.com" type="email"
                              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none" />
                          </div>
                          <div>
                            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                              API Token
                              <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" rel="noreferrer"
                                className="ml-2 normal-case text-blue-400 hover:underline">Token oluştur ↗</a>
                            </label>
                            <input value={jiraToken} onChange={e => setJiraToken(e.target.value)}
                              placeholder="ATATT3xFfGF0..." type="password"
                              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none" />
                          </div>
                          {jiraErr && <p className="text-[12px] text-red-400">{jiraErr}</p>}
                          <div className="flex gap-2">
                            <button type="button" onClick={saveJiraConfig} disabled={jiraSaving}
                              className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-2.5 text-[12px] font-semibold text-white disabled:opacity-40 hover:opacity-90 transition-opacity">
                              {jiraSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                              {jiraSaving ? "Bağlanıyor…" : "Bağlan & Kaydet"}
                            </button>
                            <button type="button" onClick={() => setJiraSetupOpen(false)}
                              className="rounded-xl border border-slate-700 px-4 py-2.5 text-[12px] text-slate-400 hover:text-white transition-colors">
                              İptal
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Yapılandırılmış → Proje + Issue seçici */}
                  {jiraStatus === "ok" && jiraConfigured && (
                    <div className="space-y-4">
                      {/* Proje seçici */}
                      <div>
                        <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Jira Projesi</label>
                        <div className="flex gap-2">
                          <select value={jiraSelProject}
                            onChange={e => {
                              setJiraSelProject(e.target.value);
                              setJiraIssues([]);
                              setJiraSelIssue(null);
                              if (e.target.value) loadJiraIssues(e.target.value);
                            }}
                            className="flex-1 rounded-xl border border-slate-700/80 bg-slate-900 px-3 py-2.5 text-[13px] text-slate-300 outline-none focus:border-blue-500/60">
                            <option value="">Proje seçin…</option>
                            {jiraProjects.map(p => (
                              <option key={p.key} value={p.key}>{p.name} ({p.key})</option>
                            ))}
                          </select>
                          <button type="button" onClick={() => loadJiraIssues(jiraSelProject, jiraSearch)}
                            disabled={!jiraSelProject || jiraLoading}
                            className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-slate-400 hover:border-slate-600 hover:text-white disabled:opacity-40 transition-colors">
                            {jiraLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>}
                          </button>
                        </div>
                      </div>

                      {/* Issue tipi + arama */}
                      {jiraSelProject && (
                        <div className="space-y-2">
                          {/* Issue type filtresi */}
                          <div className="flex gap-1.5 flex-wrap">
                            {["", "Story", "Epic", "Task", "Bug"].map(t => (
                              <button key={t} type="button"
                                onClick={() => {
                                  setJiraIssueType(t);
                                  loadJiraIssues(jiraSelProject, jiraSearch, t);
                                }}
                                className={`rounded-lg border px-3 py-1 text-[11px] font-semibold transition-all ${
                                  jiraIssueType === t
                                    ? t === "Bug"   ? "border-red-500/60 bg-red-500/10 text-red-300"
                                    : t === "Epic"  ? "border-purple-500/60 bg-purple-500/10 text-purple-300"
                                    : t === "Story" ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-300"
                                    : t === "Task"  ? "border-blue-500/60 bg-blue-500/10 text-blue-300"
                                    : "border-violet-500/60 bg-violet-500/10 text-violet-300"
                                    : "border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-300"
                                }`}>
                                {t === "" ? "Tümü" : t}
                              </button>
                            ))}
                          </div>
                          {/* Arama */}
                          <div className="flex gap-2">
                            <div className="relative flex-1">
                              <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
                              <input value={jiraSearch}
                                onChange={e => setJiraSearch(e.target.value)}
                                onKeyDown={e => { if (e.key === "Enter") loadJiraIssues(jiraSelProject, jiraSearch); }}
                                placeholder="Issue ara (başlık, açıklama…)"
                                className="w-full rounded-xl border border-slate-700/80 bg-slate-900 py-2.5 pl-9 pr-3 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none" />
                            </div>
                            <button type="button" onClick={() => loadJiraIssues(jiraSelProject, jiraSearch)}
                              disabled={jiraLoading}
                              className="rounded-xl bg-slate-800 border border-slate-700 px-4 text-[12px] font-medium text-slate-300 hover:border-slate-600 disabled:opacity-40 transition-colors">
                              Ara
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Issue listesi */}
                      {jiraErr && (
                        <p className="text-[12px] text-red-400 flex items-center gap-1.5">
                          <AlertCircle className="h-3.5 w-3.5 shrink-0" /> {jiraErr}
                        </p>
                      )}

                      {jiraLoading && (
                        <div className="space-y-2">
                          {[1,2,3].map(i => (
                            <div key={i} className="h-16 rounded-xl border border-slate-800 bg-slate-900/50 animate-pulse" style={{ opacity: Math.max(0.3, 1 - i * 0.25) }} />
                          ))}
                        </div>
                      )}

                      {!jiraLoading && jiraIssues.length > 0 && (
                        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                          <p className="text-[10px] text-slate-600 uppercase tracking-widest">{jiraIssues.length} issue bulundu — birini seçin</p>
                          {jiraIssues.map(issue => (
                            <button key={issue.key} type="button"
                              onClick={() => extractFromJiraIssue(issue)}
                              disabled={aiGenerating}
                              className={`w-full text-left rounded-xl border p-3.5 transition-all disabled:opacity-60 ${
                                jiraSelIssue?.key === issue.key
                                  ? "border-blue-500/60 bg-blue-500/8"
                                  : "border-slate-700/60 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-800/40"
                              }`}>
                              <div className="flex items-start gap-3">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="font-mono text-[11px] font-bold text-blue-400 shrink-0">{issue.key}</span>
                                    {issue.issue_type && (
                                      <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[9px] uppercase font-semibold text-slate-400">{issue.issue_type}</span>
                                    )}
                                    {issue.priority && (
                                      <span className={`text-[9px] font-bold uppercase ${
                                        issue.priority.toLowerCase().includes("high") || issue.priority.toLowerCase().includes("critical") ? "text-red-400" :
                                        issue.priority.toLowerCase().includes("medium") ? "text-amber-400" : "text-slate-500"
                                      }`}>{issue.priority}</span>
                                    )}
                                    <span className="text-[9px] rounded-full border border-slate-700 px-1.5 py-0.5 text-slate-500">{issue.status}</span>
                                  </div>
                                  <p className="mt-1 text-[13px] font-medium text-slate-200 leading-snug">{issue.summary}</p>
                                  {issue.description && (
                                    <p className="mt-0.5 text-[11px] text-slate-500 line-clamp-2">{issue.description.slice(0, 120)}</p>
                                  )}
                                  {issue.labels.length > 0 && (
                                    <div className="mt-1.5 flex flex-wrap gap-1">
                                      {issue.labels.map(l => (
                                        <span key={l} className="rounded-full bg-slate-800 px-2 py-0.5 text-[9px] text-slate-500">#{l}</span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                                <div className="shrink-0 flex flex-col items-end gap-1">
                                  {jiraSelIssue?.key === issue.key && aiGenerating ? (
                                    <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                                  ) : (
                                    <div className="flex items-center gap-1 rounded-lg border border-blue-500/30 bg-blue-500/8 px-2.5 py-1 text-[11px] text-blue-400">
                                      <Wand2 className="h-3 w-3" /> Üret
                                    </div>
                                  )}
                                  <a href={issue.url} target="_blank" rel="noreferrer"
                                    onClick={e => e.stopPropagation()}
                                    className="text-[10px] text-slate-600 hover:text-slate-400 flex items-center gap-0.5 transition-colors">
                                    <ExternalLink className="h-2.5 w-2.5" /> Jira'da aç
                                  </a>
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      )}

                      {!jiraLoading && jiraSelProject && jiraIssues.length === 0 && !jiraErr && (
                        <div className="rounded-xl border border-dashed border-slate-700 py-8 text-center">
                          <p className="text-[12px] text-slate-500">Issue bulunamadı — farklı bir arama deneyin</p>
                        </div>
                      )}

                      {aiGenerating && jiraSelIssue && (
                        <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 px-4 py-3 flex items-center gap-3">
                          <Loader2 className="h-4 w-4 animate-spin text-violet-400 shrink-0" />
                          <div>
                            <p className="text-[12px] font-semibold text-violet-300">{aiProgress || "Analiz ediliyor…"}</p>
                            <p className="text-[11px] text-violet-300/60">{jiraSelIssue.key}: {jiraSelIssue.summary.slice(0, 60)}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Extra instructions */}
              {aiSource !== "file" && aiSource !== "jira" && (
                <div>
                  <input value={aiExtra} onChange={e => setAiExtra(e.target.value)}
                    placeholder="Ek talimat: negatif senaryolara odaklan, edge case ekle, sadece smoke…"
                    className="w-full rounded-xl border border-slate-700/60 bg-slate-900 px-4 py-2.5 text-[12px] text-slate-300 placeholder-slate-600 focus:border-violet-500/40 focus:outline-none" />
                </div>
              )}

              {/* Generate button — Jira'da gizle (otomatik tetikleniyor) */}
              {aiSource !== "jira" && <button type="button" onClick={generateWithAI}
                disabled={aiGenerating || (!aiContext.trim() && aiSource !== "file") || (aiSource === "file" && !aiContext.trim())}
                className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 py-3 text-[13px] font-semibold text-white disabled:opacity-40 hover:from-violet-500 hover:to-blue-500 transition-all shadow-lg shadow-violet-900/20">
                {aiGenerating
                  ? <><Loader2 className="h-4 w-4 animate-spin" /> {aiProgress || "Analiz ediliyor…"}</>
                  : <><Wand2 className="h-4 w-4" /> AI ile Senaryo Üret</>}
              </button>}

              {aiError && (
                <div className="rounded-xl border border-red-500/30 bg-red-500/8 px-4 py-3 text-[12px] text-red-400 flex items-start gap-2">
                  <span className="shrink-0 mt-0.5">⚠</span> {aiError}
                </div>
              )}

              {/* Generated scenarios */}
              {aiScenarios.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[12px] font-semibold text-slate-300">
                      <span className="text-violet-400">{aiScenarios.length}</span> senaryo üretildi
                    </p>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => setAiScenarios(s => s.map(x => ({ ...x, selected: true })))}
                        className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors">Tümünü seç</button>
                      <span className="text-slate-700">·</span>
                      <button type="button" onClick={() => setAiScenarios(s => s.map(x => ({ ...x, selected: false })))}
                        className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors">Seçimi kaldır</button>
                    </div>
                  </div>

                  <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                    {aiScenarios.map((sc, i) => (
                      <div key={i}
                        className={`rounded-xl border p-3 transition-all cursor-pointer ${
                          sc.selected
                            ? "border-violet-500/40 bg-violet-500/5"
                            : "border-slate-700/50 bg-slate-900/30 opacity-60"
                        }`}
                        onClick={() => setAiScenarios(s => s.map((x, j) => j === i ? { ...x, selected: !x.selected } : x))}>
                        <div className="flex items-start gap-3">
                          <div className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-all ${
                            sc.selected ? "border-violet-500 bg-violet-500 text-white" : "border-slate-600"
                          }`}>
                            {sc.selected && <Check className="h-3 w-3" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <input
                              type="text"
                              value={sc.title}
                              onClick={e => e.stopPropagation()}
                              onChange={e => setAiScenarios(s => s.map((x, j) => j === i ? { ...x, title: e.target.value } : x))}
                              className="w-full bg-transparent text-[13px] font-medium text-white outline-none focus:text-violet-200 transition-colors"
                            />
                            {sc.steps.length > 0 && (
                              <div className="mt-1.5 space-y-0.5">
                                {sc.steps.slice(0, 3).map((s, k) => (
                                  <p key={k} className="text-[11px] font-mono">
                                    <span className="text-purple-400">{s.keyword} </span>
                                    <span className="text-slate-400 line-clamp-1">{s.text}</span>
                                  </p>
                                ))}
                                {sc.steps.length > 3 && (
                                  <p className="text-[10px] text-slate-600">+{sc.steps.length - 3} adım</p>
                                )}
                              </div>
                            )}
                            {sc.tags.length > 0 && (
                              <div className="mt-1.5 flex flex-wrap gap-1">
                                {sc.tags.map(t => (
                                  <span key={t} className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">#{t}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══ MANUAL TAB ══════════════════════════════════════════ */}
          {tab === "manual" && (
            <div className="p-6 space-y-5">
              {/* Title */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                  Başlık <span className="text-red-400">*</span>
                </label>
                <input type="text" value={title} onChange={e => setTitle(e.target.value)} autoFocus
                  placeholder="Örn: Login akışı doğrulama"
                  className="w-full rounded-xl border border-slate-700/80 bg-slate-900 px-4 py-2.5 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none focus:ring-2 focus:ring-blue-500/10" />
              </div>

              {/* Priority + Tags */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Öncelik</label>
                  <div className="flex gap-1.5">
                    {PRIORITIES.map(p => (
                      <button key={p} type="button" onClick={() => setPriority(p)}
                        className={`flex-1 rounded-lg border py-2 text-[11px] font-bold transition-all ${
                          priority === p
                            ? p === "P0" ? "border-red-500/60 bg-red-500/10 text-red-300"
                              : p === "P1" ? "border-orange-500/60 bg-orange-500/10 text-orange-300"
                              : p === "P2" ? "border-blue-500/60 bg-blue-500/10 text-blue-300"
                              : "border-slate-500/60 bg-slate-700 text-slate-300"
                            : "border-slate-700 text-slate-600 hover:border-slate-600 hover:text-slate-400"
                        }`}>{p}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Etiketler</label>
                  <input value={tags} onChange={e => setTags(e.target.value)}
                    placeholder="smoke, login, regression…"
                    className="w-full rounded-xl border border-slate-700/80 bg-slate-900 px-3 py-2.5 text-[12px] text-slate-300 placeholder-slate-600 focus:border-blue-500/60 focus:outline-none" />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Açıklama / Bağlam</label>
                <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={3}
                  placeholder="Test kapsamı, gereksinimler veya özel durumlar…"
                  className="w-full resize-none rounded-xl border border-slate-700/80 bg-slate-900 px-4 py-3 text-[13px] text-white placeholder-slate-600 focus:border-blue-500/60 focus:outline-none" />
              </div>

              {/* BDD Steps */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">BDD Adımları</label>
                  <button type="button"
                    onClick={() => setManSteps(s => [...s, { type: "and", text: "" }])}
                    className="flex items-center gap-1 rounded-lg border border-slate-700 px-2 py-1 text-[11px] text-slate-500 hover:border-slate-600 hover:text-slate-300 transition-colors">
                    <Plus className="h-3 w-3" /> Adım
                  </button>
                </div>
                <div className="space-y-2">
                  {manSteps.map((s, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <select value={s.type} onChange={e => setManSteps(prev => prev.map((x, j) => j === i ? { ...x, type: e.target.value as BddStep["type"] } : x))}
                        className="w-20 shrink-0 rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-[11px] text-slate-400 outline-none focus:border-blue-500/60">
                        {BDD_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                      <input value={s.text} onChange={e => setManSteps(prev => prev.map((x, j) => j === i ? { ...x, text: e.target.value } : x))}
                        placeholder={i === 0 ? "kullanıcı sisteme girmiştir" : i === 1 ? "giriş formunu doldurur" : "kullanıcı ana sayfayı görür"}
                        className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-[12px] text-white placeholder-slate-600 outline-none focus:border-blue-500/60" />
                      {manSteps.length > 1 && (
                        <button type="button" onClick={() => setManSteps(prev => prev.filter((_, j) => j !== i))}
                          className="shrink-0 rounded-lg p-1.5 text-slate-700 hover:bg-slate-800 hover:text-red-400 transition-colors">
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                {/* Live mini preview */}
                {(title || manSteps.some(s => s.text)) && (
                  <div className="mt-3 rounded-xl border border-slate-800 bg-[#0a0f1a] px-4 py-3 font-mono">
                    <p className="text-[10px] text-slate-600 mb-1.5">Preview</p>
                    {title && <p className="text-[11px]"><span className="text-blue-400">Scenario: </span><span className="text-slate-300">{title}</span></p>}
                    {manSteps.filter(s => s.text).map((s, i) => (
                      <p key={i} className="text-[11px]">
                        <span className={`inline-block w-12 text-right mr-2 ${BDD_KW_COLORS[s.type]?.split(" ")[1] ?? "text-slate-500"}`}>{s.type}</span>
                        <span className="text-slate-400">{s.text}</span>
                      </p>
                    ))}
                  </div>
                )}
              </div>

              {manError && <p className="text-[12px] text-red-400">{manError}</p>}
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="border-t border-slate-800 px-6 py-4 flex items-center justify-between gap-3">
          <button onClick={onClose}
            className="rounded-xl border border-slate-700 px-4 py-2 text-[13px] text-slate-400 hover:border-slate-600 hover:text-white transition-colors">
            İptal
          </button>

          {tab === "ai" ? (
            <button type="button" onClick={saveSelected}
              disabled={saving || selectedCount === 0 || saved}
              className={`flex items-center gap-2 rounded-xl px-5 py-2 text-[13px] font-semibold transition-all ${
                saved
                  ? "bg-emerald-600/20 border border-emerald-500/40 text-emerald-400"
                  : selectedCount > 0
                    ? "bg-gradient-to-r from-violet-600 to-blue-600 text-white hover:from-violet-500 hover:to-blue-500 shadow-lg shadow-violet-900/20"
                    : "bg-slate-800 text-slate-600 cursor-not-allowed"
              }`}>
              {saved
                ? <><CheckCircle2 className="h-4 w-4" /> Kaydedildi</>
                : saving
                  ? <><Loader2 className="h-4 w-4 animate-spin" /> Kaydediliyor…</>
                  : <><Plus className="h-4 w-4" /> {selectedCount > 0 ? `${selectedCount} Senaryo Kaydet` : "Senaryo Seçin"}</>}
            </button>
          ) : (
            <button type="button" onClick={handleManualSubmit}
              disabled={!title.trim() || manLoading}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2 text-[13px] font-semibold text-white disabled:opacity-40 hover:from-blue-500 hover:to-indigo-500 transition-all shadow-lg shadow-blue-900/20">
              {manLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Oluştur
            </button>
          )}
        </div>
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
        const lsId = (() => {
          if (typeof window === "undefined") return null;
          try {
            const raw = localStorage.getItem("bgts_active_project");
            if (!raw) return null;
            const parsed = JSON.parse(raw) as { id?: unknown } | null;
            const id = parsed && typeof parsed.id === "string" ? parsed.id.trim() : "";
            return id || null;
          } catch { return null; }
        })();
        const initial = ctxProjectId || lsId || list[0]?.id;
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
