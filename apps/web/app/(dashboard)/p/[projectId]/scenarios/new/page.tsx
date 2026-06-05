"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type Mode = "quick" | "ai" | "pipeline";
type AiTab = "text" | "file" | "url" | "screenshot";

interface Step {
  id: string;
  keyword: string;
  text: string;
}

interface GeneratedScenario {
  title: string;
  description: string;
  feature?: string;
  gherkin?: string;
  tags: string[];
  steps: { keyword: string; text: string }[];
  quality_score?: number;
  selected: boolean;
}

interface PipelineStage {
  id: string;
  title: string;
  status: "pending" | "in_progress" | "complete" | "failed" | "skipped" | "awaiting_input";
  output_summary?: string | null;
}

interface AnalyzeResult {
  manual_tests: { title: string; steps: string[] }[];
  bdd_scenarios: GeneratedScenario[];
  ai_provider?: string | null;
  error?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PIPELINE_STAGES: PipelineStage[] = [
  { id: "analyze",  title: "Analiz",        status: "pending" },
  { id: "design",   title: "Tasarım",        status: "pending" },
  { id: "data",     title: "Test Verisi",    status: "pending" },
  { id: "execute",  title: "Otomasyon Kodu", status: "pending" },
  { id: "observe",  title: "Self-Heal",      status: "pending" },
  { id: "iterate",  title: "İyileştirme",    status: "pending" },
];

const BDD_KEYWORDS = ["Olduğu gibi", "Eğer", "O zaman", "Ve", "Ama", "Senaryo"];
const PRIORITIES = ["P0", "P1", "P2", "P3"];
const PLATFORMS = ["Web", "Mobile iOS", "Mobile Android", "API", "Backend", "Desktop"];
const TAG_SUGGESTIONS = ["smoke", "regression", "critical", "auth", "payment", "ui", "api", "e2e"];

let _stepCounter = 0;
const newStep = (kw = "Eğer", text = ""): Step => ({
  id: `step-${++_stepCounter}-${Math.random().toString(36).slice(2, 7)}`,
  keyword: kw,
  text,
});

// ─── Micro Icons ──────────────────────────────────────────────────────────────

function IcClose() {
  return <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>;
}
function IcPlus() {
  return <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>;
}
function IcTrash() {
  return <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>;
}
function IcSpinner() {
  return <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>;
}
function IcCheck() {
  return <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>;
}
function IcCopy() {
  return <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>;
}
function IcUpload() {
  return <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>;
}
function IcWand() {
  return <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>;
}

// ─── Shared input styles ──────────────────────────────────────────────────────

const INP = "w-full rounded-xl border border-slate-700/60 bg-slate-900/80 px-3 py-2.5 text-[13px] text-slate-100 placeholder-slate-600 outline-none focus:border-teal-500/50 focus:ring-2 focus:ring-teal-500/10 transition-all";
const SEL = "rounded-xl border border-slate-700/60 bg-slate-900/80 px-2.5 py-2 text-[12px] text-slate-300 outline-none focus:border-teal-500/50 transition-all";

// ─── Step Editor ──────────────────────────────────────────────────────────────

function StepRow({ step, onChange, onDelete, isFirst }: {
  step: Step;
  onChange: (s: Step) => void;
  onDelete: () => void;
  isFirst: boolean;
}) {
  return (
    <div className="flex items-start gap-2 group">
      <select
        value={step.keyword}
        onChange={e => onChange({ ...step, keyword: e.target.value })}
        className={cn(SEL, "w-28 shrink-0 mt-0.5")}
      >
        {BDD_KEYWORDS.map(k => <option key={k} value={k}>{k}</option>)}
      </select>
      <textarea
        value={step.text}
        onChange={e => onChange({ ...step, text: e.target.value })}
        placeholder={isFirst ? "kullanıcı giriş sayfasındadır" : "adımı açıkla…"}
        rows={1}
        className={cn(INP, "resize-none flex-1 min-h-[40px]")}
        onInput={e => {
          const el = e.currentTarget;
          el.style.height = "40px";
          el.style.height = el.scrollHeight + "px";
        }}
      />
      <button
        type="button"
        onClick={onDelete}
        className="mt-1.5 invisible group-hover:visible rounded-lg p-1.5 text-slate-600 hover:bg-red-500/10 hover:text-red-400 transition-colors shrink-0"
      >
        <IcTrash />
      </button>
    </div>
  );
}

// ─── Tag Input ────────────────────────────────────────────────────────────────

function TagInput({ tags, onChange }: { tags: string[]; onChange: (t: string[]) => void }) {
  const [input, setInput] = useState("");

  const add = (tag: string) => {
    const t = tag.trim().toLowerCase().replace(/\s+/g, "-");
    if (t && !tags.includes(t)) onChange([...tags, t]);
    setInput("");
  };

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {tags.map(t => (
          <span key={t} className="inline-flex items-center gap-1 rounded-full border border-teal-500/30 bg-teal-500/10 px-2.5 py-1 text-[11px] font-medium text-teal-300">
            #{t}
            <button type="button" onClick={() => onChange(tags.filter(x => x !== t))} className="text-teal-500 hover:text-teal-200">
              <IcClose />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add(input); } }}
          placeholder="etiket ekle…"
          className={cn(INP, "flex-1 h-9")}
        />
        <button type="button" onClick={() => add(input)} className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-[12px] text-slate-300 hover:border-teal-500/40 hover:text-teal-300 transition-colors">
          + Ekle
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {TAG_SUGGESTIONS.filter(t => !tags.includes(t)).map(t => (
          <button key={t} type="button" onClick={() => onChange([...tags, t])}
            className="rounded-full border border-slate-700/40 bg-slate-800/50 px-2 py-0.5 text-[10px] text-slate-500 hover:border-teal-500/30 hover:text-teal-400 transition-colors">
            +{t}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Gherkin Preview ──────────────────────────────────────────────────────────

function GherkinPreview({ title, steps, tags }: { title: string; steps: Step[]; tags: string[] }) {
  const gherkin = `Feature: ${title || "Senaryo Başlığı"}\n\n  Scenario: ${title || "…"}\n${
    steps.map(s => `    ${s.keyword} ${s.text || "…"}`).join("\n")
  }`;

  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(gherkin).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div className="rounded-xl border border-slate-700/60 bg-[#0d1117] overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-teal-500/70" />
          <span className="text-[11px] font-mono text-slate-500">gherkin preview</span>
        </div>
        <div className="flex items-center gap-2">
          {tags.length > 0 && (
            <span className="text-[10px] text-slate-600">{tags.map(t => `@${t}`).join(" ")}</span>
          )}
          <button type="button" onClick={copy}
            className={cn("flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] transition-colors",
              copied ? "text-teal-400" : "text-slate-600 hover:text-slate-300")}>
            {copied ? <IcCheck /> : <IcCopy />}
            {copied ? "Kopyalandı" : "Kopyala"}
          </button>
        </div>
      </div>
      <pre className="p-4 text-[12px] font-mono leading-relaxed text-slate-300 overflow-auto max-h-64">
        <span className="text-blue-400">Feature: </span><span className="text-slate-100">{title || "Senaryo Başlığı"}</span>
        {"\n\n  "}
        <span className="text-blue-400">Scenario: </span><span className="text-slate-100">{title || "…"}</span>
        {"\n"}
        {steps.map((s, i) => (
          <span key={i}>
            {"    "}
            <span className="text-purple-400">{s.keyword} </span>
            <span className="text-slate-200">{s.text || "…"}</span>
            {"\n"}
          </span>
        ))}
      </pre>
    </div>
  );
}

// ─── Generated Scenario Card ──────────────────────────────────────────────────

function GeneratedCard({ sc, idx, onToggle, onEdit }: {
  sc: GeneratedScenario;
  idx: number;
  onToggle: () => void;
  onEdit: (title: string) => void;
}) {
  const [editingTitle, setEditingTitle] = useState(false);
  const [title, setTitle] = useState(sc.title);

  const score = sc.quality_score;
  const scoreColor = score === undefined ? "" : score >= 0.8 ? "text-emerald-400" : score >= 0.5 ? "text-amber-400" : "text-red-400";

  return (
    <div className={cn(
      "rounded-xl border p-4 transition-all",
      sc.selected
        ? "border-teal-500/40 bg-teal-500/5"
        : "border-slate-700/50 bg-slate-900/40 opacity-60"
    )}>
      <div className="flex items-start gap-3">
        <button type="button" onClick={onToggle}
          className={cn(
            "mt-0.5 h-5 w-5 shrink-0 rounded border-2 flex items-center justify-center transition-all",
            sc.selected ? "border-teal-500 bg-teal-500 text-white" : "border-slate-600"
          )}>
          {sc.selected && <IcCheck />}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {editingTitle ? (
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                onBlur={() => { setEditingTitle(false); onEdit(title); }}
                onKeyDown={e => { if (e.key === "Enter") { setEditingTitle(false); onEdit(title); } }}
                autoFocus
                className="flex-1 rounded-lg border border-teal-500/40 bg-slate-900 px-2 py-1 text-[13px] text-slate-100 outline-none"
              />
            ) : (
              <h3
                className="text-[14px] font-semibold text-slate-100 cursor-pointer hover:text-teal-300 transition-colors flex-1"
                onClick={() => setEditingTitle(true)}
              >
                {sc.title}
              </h3>
            )}
            {score !== undefined && (
              <span className={cn("text-[11px] font-mono shrink-0", scoreColor)}>
                {Math.round(score * 100)}%
              </span>
            )}
          </div>
          {sc.feature && (
            <p className="mt-0.5 text-[11px] text-slate-500">Feature: {sc.feature}</p>
          )}
          {sc.description && (
            <p className="mt-1 text-[12px] text-slate-400 line-clamp-2">{sc.description}</p>
          )}
          {sc.steps.length > 0 && (
            <div className="mt-2 space-y-0.5">
              {sc.steps.slice(0, 4).map((s, i) => (
                <p key={i} className="text-[11px] font-mono">
                  <span className="text-purple-400">{s.keyword} </span>
                  <span className="text-slate-400">{s.text}</span>
                </p>
              ))}
              {sc.steps.length > 4 && (
                <p className="text-[10px] text-slate-600">+{sc.steps.length - 4} adım daha</p>
              )}
            </div>
          )}
          {sc.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {sc.tags.map(t => (
                <span key={t} className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                  #{t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Pipeline Stage Card ──────────────────────────────────────────────────────

function StageCard({ stage, idx }: { stage: PipelineStage; idx: number }) {
  const colors = {
    pending:        "border-slate-700 bg-slate-900/40 text-slate-500",
    in_progress:    "border-amber-500/50 bg-amber-500/10 text-amber-200",
    complete:       "border-emerald-500/50 bg-emerald-500/10 text-emerald-200",
    failed:         "border-red-500/50 bg-red-500/10 text-red-300",
    skipped:        "border-slate-700 bg-slate-900/20 text-slate-600",
    awaiting_input: "border-blue-500/50 bg-blue-500/10 text-blue-200",
  };

  const icons = {
    pending:        <span className="h-2 w-2 rounded-full bg-slate-700 inline-block" />,
    in_progress:    <IcSpinner />,
    complete:       <span className="text-emerald-400"><IcCheck /></span>,
    failed:         <span className="text-red-400"><IcClose /></span>,
    skipped:        <span className="text-slate-600">—</span>,
    awaiting_input: <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse inline-block" />,
  };

  const labels = {
    pending: "Bekliyor", in_progress: "Sürüyor", complete: "✓ Tamam",
    failed: "Hata", skipped: "Atlandı", awaiting_input: "Bilgi bek.",
  };

  return (
    <div className={cn("rounded-xl border p-3 flex flex-col gap-1.5", colors[stage.status])}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono opacity-50">{idx + 1}</span>
        <span className="flex items-center gap-1 text-[10px] uppercase tracking-wide">
          {icons[stage.status]}
          <span>{labels[stage.status]}</span>
        </span>
      </div>
      <p className="text-[12px] font-semibold leading-tight">{stage.title}</p>
      {stage.output_summary && (
        <p className="text-[10px] opacity-75 line-clamp-3 leading-relaxed">{stage.output_summary}</p>
      )}
    </div>
  );
}

// ─── MODE 1: Quick Create ─────────────────────────────────────────────────────

function QuickCreate({ projectId }: { projectId: string }) {
  const router = useRouter();
  const qc = useQueryClient();

  const [title, setTitle]         = useState("");
  const [description, setDesc]    = useState("");
  const [gherkin, setGherkin]     = useState(true);
  const [steps, setSteps]         = useState<Step[]>([
    newStep("Olduğu gibi", ""),
    newStep("Eğer", ""),
    newStep("O zaman", ""),
  ]);
  const [tags, setTags]           = useState<string[]>([]);
  const [priority, setPriority]   = useState("P2");
  const [platform, setPlatform]   = useState("");
  const [status, setStatus]       = useState("draft");
  const [saving, setSaving]       = useState(false);
  const [err, setErr]             = useState<string | null>(null);

  const addStep = () => setSteps(s => [...s, newStep("Ve", "")]);
  const updateStep = (id: string, s: Step) => setSteps(steps => steps.map(x => x.id === id ? s : x));
  const deleteStep = (id: string) => setSteps(steps => steps.filter(x => x.id !== id));

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) { setErr("Başlık zorunlu"); return; }
    if (steps.every(s => !s.text.trim())) { setErr("En az bir adım girilmeli"); return; }
    setSaving(true); setErr(null);
    try {
      const apiSteps = steps.filter(s => s.text.trim()).map((s, i) => ({
        order: i, keyword: s.keyword, text: s.text.trim(),
      }));
      const created = await apiFetch<{ id: string }>(
        `/api/v1/tspm/projects/${projectId}/scenarios`,
        { method: "POST", json: {
          title: title.trim(), description: description.trim() || undefined,
          status, steps: apiSteps,
          tags: tags.length ? tags : undefined,
          priority,
          ...(platform && { platform }),
        }},
      );
      qc.invalidateQueries({ queryKey: ["scenarios", "list", projectId] });
      router.push(`/p/${projectId}/scenarios/${created.id}`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Kaydetme hatası");
    } finally { setSaving(false); }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_420px]">
      {/* Sol: Form */}
      <form onSubmit={save} className="space-y-5">
        {/* Başlık */}
        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Başlık *</label>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Kullanıcı başarıyla giriş yapabilmeli…" className={INP} />
        </div>

        {/* Meta satırı */}
        <div className="flex flex-wrap gap-3">
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">Öncelik</label>
            <select value={priority} onChange={e => setPriority(e.target.value)} className={SEL}>
              {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">Durum</label>
            <select value={status} onChange={e => setStatus(e.target.value)} className={SEL}>
              {["draft","active","review","archived"].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">Platform</label>
            <select value={platform} onChange={e => setPlatform(e.target.value)} className={SEL}>
              <option value="">Seçin</option>
              {PLATFORMS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer rounded-xl border border-slate-700/60 bg-slate-900/80 px-3 py-2">
              <div
                onClick={() => setGherkin(v => !v)}
                className={cn("relative h-4 w-8 rounded-full transition-colors cursor-pointer",
                  gherkin ? "bg-teal-500" : "bg-slate-700"
                )}>
                <span className={cn("absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all",
                  gherkin ? "left-4" : "left-0.5"
                )} />
              </div>
              <span className="text-[11px] text-slate-400 select-none">BDD / Gherkin</span>
            </label>
          </div>
        </div>

        {/* Açıklama */}
        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Açıklama</label>
          <textarea value={description} onChange={e => setDesc(e.target.value)} rows={2} placeholder="Opsiyonel açıklama veya kabul kriterleri…" className={cn(INP, "resize-none")} />
        </div>

        {/* Adımlar */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Test Adımları *</label>
            <button type="button" onClick={addStep} className="flex items-center gap-1 rounded-lg border border-slate-700 px-2.5 py-1.5 text-[11px] text-slate-400 hover:border-teal-500/40 hover:text-teal-300 transition-colors">
              <IcPlus /> Adım Ekle
            </button>
          </div>
          <div className="space-y-2">
            {steps.map((s, i) => (
              <StepRow key={s.id} step={s} isFirst={i === 0}
                onChange={updated => updateStep(s.id, updated)}
                onDelete={() => deleteStep(s.id)} />
            ))}
          </div>
        </div>

        {/* Etiketler */}
        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Etiketler</label>
          <TagInput tags={tags} onChange={setTags} />
        </div>

        {err && <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-400">{err}</p>}

        <button type="submit" disabled={saving}
          className="flex items-center gap-2 rounded-xl bg-teal-600 px-6 py-2.5 text-[13px] font-semibold text-white hover:bg-teal-500 disabled:opacity-40 transition-colors shadow-lg shadow-teal-900/20">
          {saving ? <><IcSpinner /> Kaydediliyor…</> : "✓ Kaydet"}
        </button>
      </form>

      {/* Sağ: Preview */}
      <div className="space-y-4 lg:sticky lg:top-6 lg:self-start">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Önizleme</p>
        {gherkin ? (
          <GherkinPreview title={title} steps={steps} tags={tags} />
        ) : (
          <div className="rounded-xl border border-slate-700/60 bg-slate-900/60 p-4 space-y-3">
            <h3 className="text-[15px] font-semibold text-slate-100">{title || "Başlık"}</h3>
            {description && <p className="text-[12px] text-slate-400">{description}</p>}
            <ol className="space-y-1.5">
              {steps.filter(s => s.text).map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-[12px]">
                  <span className="mt-0.5 h-4 w-4 shrink-0 rounded-full border border-slate-700 flex items-center justify-center text-[9px] font-bold text-slate-500">{i+1}</span>
                  <span className="text-slate-300">{s.text}</span>
                </li>
              ))}
            </ol>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tags.map(t => <span key={t} className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">#{t}</span>)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── MODE 2: AI Workshop ──────────────────────────────────────────────────────

function AiWorkshop({ projectId }: { projectId: string }) {
  const router = useRouter();
  const qc = useQueryClient();

  const [aiTab, setAiTab]               = useState<AiTab>("text");
  const [text, setText]                  = useState("");
  const [extra, setExtra]                = useState("");
  const [fileInfo, setFileInfo]          = useState<{ name: string; text: string } | null>(null);
  const [urlInput, setUrlInput]          = useState("");
  const [screenshotB64, setScreenB64]   = useState<string | null>(null);
  const [screenshotName, setScreenName] = useState<string | null>(null);

  const [analyzing, setAnalyzing]       = useState(false);
  const [result, setResult]             = useState<AnalyzeResult | null>(null);
  const [scenarios, setScenarios]       = useState<GeneratedScenario[]>([]);
  const [saving, setSaving]             = useState(false);
  const [saved, setSaved]               = useState(false);
  const [err, setErr]                   = useState<string | null>(null);
  const [progress, setProgress]         = useState("");

  const fileRef = useRef<HTMLInputElement>(null);
  const imgRef  = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    setErr(null); setProgress("Doküman yükleniyor…");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`/api/v1/tspm/projects/${projectId}/wizard/upload-document`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });
      const data = await res.json() as { full_text?: string; preview?: string; filename?: string; error?: string };
      if (!res.ok) throw new Error((data as { detail?: string }).detail ?? "Yükleme hatası");
      setFileInfo({ name: data.filename ?? file.name, text: data.full_text ?? "" });
      setText(data.full_text ?? "");
      setProgress("");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Dosya yükleme başarısız");
      setProgress("");
    }
  };

  const handleImageSelect = (file: File) => {
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = (ev.target?.result as string) ?? "";
      setScreenB64(dataUrl.split(",")[1] ?? "");
      setScreenName(file.name);
    };
    reader.readAsDataURL(file);
  };

  const analyze = useCallback(async () => {
    const payload = aiTab === "screenshot"
      ? { text: text.trim(), images: screenshotB64 ? [screenshotB64] : [], extra_instructions: extra }
      : { text: text.trim(), extra_instructions: extra };

    if (!text.trim() && aiTab !== "screenshot") { setErr("Analiz edilecek metin giriniz"); return; }
    if (aiTab === "screenshot" && !screenshotB64) { setErr("Ekran görüntüsü seçin"); return; }

    setAnalyzing(true); setErr(null); setResult(null); setScenarios([]); setProgress("AI analiz ediyor…");

    try {
      const endpoint = aiTab === "screenshot"
        ? `/api/v1/tspm/projects/${projectId}/wizard/analyze-multimodal`
        : `/api/v1/tspm/projects/${projectId}/wizard/analyze`;

      const res = await apiFetch<AnalyzeResult>(endpoint, { method: "POST", json: payload });
      setResult(res);

      // BDD senaryoları + manual testlerden senaryo listesi oluştur
      const bddScenarios: GeneratedScenario[] = (res.bdd_scenarios ?? []).map(s => ({ ...s, selected: true }));
      const manualScenarios: GeneratedScenario[] = (res.manual_tests ?? []).map(m => ({
        title: m.title,
        description: "",
        tags: ["manuel", "ai-generated"],
        steps: m.steps.map(t => ({ keyword: "Adım", text: t })),
        selected: true,
      }));

      setScenarios([...bddScenarios, ...manualScenarios]);
      setProgress("");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Analiz başarısız");
      setProgress("");
    } finally { setAnalyzing(false); }
  }, [aiTab, text, extra, screenshotB64, projectId]);

  const saveSelected = async () => {
    const toSave = scenarios.filter(s => s.selected);
    if (!toSave.length) { setErr("En az bir senaryo seçin"); return; }
    setSaving(true); setErr(null);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios/save-bdd`, {
        method: "POST",
        json: { scenarios: toSave.map(({ selected: _, ...rest }) => rest) },
      });
      qc.invalidateQueries({ queryKey: ["scenarios", "list", projectId] });
      setSaved(true);
      setTimeout(() => router.push(`/p/${projectId}/scenarios`), 1200);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Kaydetme hatası");
    } finally { setSaving(false); }
  };

  const selectedCount = scenarios.filter(s => s.selected).length;

  const AI_TABS: { id: AiTab; icon: string; label: string }[] = [
    { id: "text",       icon: "📝", label: "Metin / Doküman" },
    { id: "file",       icon: "📄", label: "Dosya Yükle" },
    { id: "url",        icon: "🌐", label: "URL Tara" },
    { id: "screenshot", icon: "🖼️", label: "Ekran Görüntüsü" },
  ];

  return (
    <div className="space-y-6">
      {/* AI Kaynak Sekmeler */}
      <div className="flex gap-2 flex-wrap">
        {AI_TABS.map(t => (
          <button key={t.id} type="button" onClick={() => setAiTab(t.id)}
            className={cn(
              "flex items-center gap-2 rounded-xl border px-4 py-2.5 text-[12px] font-medium transition-all",
              aiTab === t.id
                ? "border-teal-500/50 bg-teal-500/10 text-teal-300 shadow-sm"
                : "border-slate-700/50 bg-slate-900/40 text-slate-400 hover:border-slate-600 hover:text-slate-300"
            )}>
            <span>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {/* Kaynak Input Paneli */}
      <div className="rounded-xl border border-slate-700/60 bg-slate-900/60 p-5 space-y-4">
        {aiTab === "text" && (
          <div>
            <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
              Analiz Dokümanı — Jira metni, AC listesi, user story, spec…
            </label>
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              rows={10}
              placeholder={`Örnek:\n\nKullanıcı hikayesi: Bir kullanıcı olarak...\n\nKabul kriterleri:\n- Kullanıcı geçerli e-posta ve şifre ile giriş yapabilmeli\n- Yanlış şifre girildiğinde hata mesajı gösterilmeli\n- 3 başarısız denemede hesap kilitlenmeli\n\nGiven/When/Then veya serbest metin yapıştırabilirsiniz.`}
              className={cn(INP, "resize-none")}
            />
          </div>
        )}

        {aiTab === "file" && (
          <div
            className="flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed border-slate-700 bg-slate-900/40 p-10 cursor-pointer hover:border-teal-500/40 transition-colors"
            onClick={() => fileRef.current?.click()}
            onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFileUpload(f); }}
            onDragOver={e => e.preventDefault()}
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-teal-400">
              <IcUpload />
            </div>
            {fileInfo ? (
              <div className="text-center">
                <p className="text-[13px] font-medium text-teal-300">{fileInfo.name}</p>
                <p className="text-[11px] text-slate-500">{fileInfo.text.length.toLocaleString()} karakter yüklendi</p>
              </div>
            ) : (
              <div className="text-center">
                <p className="text-[13px] text-slate-300">Dosyayı sürükle veya tıkla</p>
                <p className="text-[11px] text-slate-500 mt-1">PDF, DOCX, TXT, MD — max 20MB</p>
              </div>
            )}
            <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); }} />
          </div>
        )}

        {aiTab === "url" && (
          <div>
            <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
              Web Sayfası URL — Uygulama sayfasını tara, UI bileşenlerini keşfet
            </label>
            <div className="flex gap-2">
              <input value={urlInput} onChange={e => setUrlInput(e.target.value)}
                placeholder="https://app.example.com/login"
                className={cn(INP, "flex-1")} />
              <button type="button"
                onClick={async () => {
                  if (!urlInput.trim()) return;
                  setAnalyzing(true); setErr(null); setProgress("Sayfa taranıyor…");
                  try {
                    const res = await apiFetch<{ content?: string; text?: string; url?: string }>(
                      `/api/v1/tspm/projects/${projectId}/wizard/crawl`,
                      { method: "POST", json: { url: urlInput.trim() } }
                    );
                    const content = res.content ?? res.text ?? "";
                    setText(content.slice(0, 5000));
                    setProgress("");
                  } catch (e: unknown) {
                    setErr(e instanceof Error ? e.message : "URL tarama başarısız");
                    setProgress("");
                  } finally { setAnalyzing(false); }
                }}
                disabled={analyzing}
                className="rounded-xl bg-slate-800 px-4 py-2.5 text-[12px] font-medium text-slate-300 border border-slate-700 hover:border-teal-500/40 hover:text-teal-300 disabled:opacity-40 transition-colors">
                {analyzing ? <IcSpinner /> : "Tara"}
              </button>
            </div>
            {text && (
              <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950 p-3">
                <p className="text-[10px] text-slate-500 mb-1">Çıkarılan içerik (ilk 500 karakter):</p>
                <p className="text-[11px] text-slate-400 line-clamp-4">{text.slice(0, 500)}</p>
              </div>
            )}
          </div>
        )}

        {aiTab === "screenshot" && (
          <div className="space-y-4">
            <div
              className="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-slate-700 bg-slate-900/40 p-8 cursor-pointer hover:border-teal-500/40 transition-colors"
              onClick={() => imgRef.current?.click()}
              onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleImageSelect(f); }}
              onDragOver={e => e.preventDefault()}
            >
              {screenshotB64 ? (
                <div className="text-center">
                  <img src={`data:image/png;base64,${screenshotB64}`} alt="screenshot"
                    className="mx-auto max-h-48 rounded-lg border border-slate-700 object-contain" />
                  <p className="mt-2 text-[11px] text-slate-400">{screenshotName}</p>
                </div>
              ) : (
                <>
                  <span className="text-4xl">🖼️</span>
                  <p className="text-[13px] text-slate-300">Mockup, wireframe veya uygulama ekranı yükle</p>
                  <p className="text-[11px] text-slate-500">PNG, JPG, WEBP</p>
                </>
              )}
              <input ref={imgRef} type="file" accept="image/*" className="hidden"
                onChange={e => { const f = e.target.files?.[0]; if (f) handleImageSelect(f); }} />
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] text-slate-500">Ek açıklama (opsiyonel)</label>
              <textarea value={text} onChange={e => setText(e.target.value)} rows={3}
                placeholder="Bu ekran hangi akışı gösteriyor? Hangi testlere odaklanılsın?"
                className={cn(INP, "resize-none")} />
            </div>
          </div>
        )}

        {/* Ek talimat */}
        <div>
          <label className="mb-1 block text-[10px] text-slate-600">Ek talimat (opsiyonel)</label>
          <input value={extra} onChange={e => setExtra(e.target.value)}
            placeholder="Negatif senaryolara odaklan, edge case'leri dahil et, sadece smoke testler…"
            className={cn(INP, "text-[12px]")} />
        </div>

        {/* Analiz Butonu */}
        <button type="button" onClick={analyze} disabled={analyzing}
          className="flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-teal-600 px-6 py-3 text-[13px] font-semibold text-white hover:from-violet-500 hover:to-teal-500 disabled:opacity-40 transition-all shadow-lg shadow-violet-900/20">
          {analyzing ? <><IcSpinner /> {progress || "Analiz ediliyor…"}</> : <><IcWand /> AI ile Analiz Et & Senaryo Üret</>}
        </button>
      </div>

      {/* Hata */}
      {err && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-400 flex items-start gap-2">
          <span className="mt-0.5 shrink-0">⚠</span> {err}
        </div>
      )}

      {/* Sonuçlar */}
      {scenarios.length > 0 && (
        <div className="space-y-4">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-[15px] font-semibold text-slate-100">
                {scenarios.length} senaryo üretildi
              </h3>
              {result?.ai_provider && (
                <p className="text-[11px] text-slate-500">AI: {result.ai_provider}</p>
              )}
            </div>
            <div className="flex gap-2">
              <button type="button"
                onClick={() => setScenarios(s => s.map(x => ({ ...x, selected: true })))}
                className="rounded-xl border border-slate-700 px-3 py-1.5 text-[11px] text-slate-400 hover:border-teal-500/30 hover:text-teal-300 transition-colors">
                Tümünü Seç
              </button>
              <button type="button"
                onClick={() => setScenarios(s => s.map(x => ({ ...x, selected: false })))}
                className="rounded-xl border border-slate-700 px-3 py-1.5 text-[11px] text-slate-400 hover:text-slate-300 transition-colors">
                Seçimi Kaldır
              </button>
              <button type="button" onClick={saveSelected}
                disabled={saving || selectedCount === 0 || saved}
                className={cn(
                  "flex items-center gap-2 rounded-xl px-5 py-2 text-[12px] font-semibold transition-all",
                  saved
                    ? "bg-emerald-600/20 border border-emerald-500/40 text-emerald-400"
                    : "bg-teal-600 text-white hover:bg-teal-500 disabled:opacity-40 shadow-lg shadow-teal-900/20"
                )}>
                {saved ? <><IcCheck /> Kaydedildi</> : saving ? <><IcSpinner /> Kaydediliyor…</> : `Seçilenleri Kaydet (${selectedCount})`}
              </button>
            </div>
          </div>

          {/* Senaryo grid */}
          <div className="grid gap-3 md:grid-cols-2">
            {scenarios.map((sc, i) => (
              <GeneratedCard
                key={i} sc={sc} idx={i}
                onToggle={() => setScenarios(s => s.map((x, j) => j === i ? { ...x, selected: !x.selected } : x))}
                onEdit={title => setScenarios(s => s.map((x, j) => j === i ? { ...x, title } : x))}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── MODE 3: Pilot Pipeline ───────────────────────────────────────────────────

function PilotPipeline({ projectId }: { projectId: string }) {
  const router = useRouter();

  const [description, setDesc]   = useState("");
  const [title, setTitle]        = useState("");
  const [running, setRunning]    = useState(false);
  const [done, setDone]          = useState(false);
  const [stages, setStages]      = useState<PipelineStage[]>(PIPELINE_STAGES);
  const [err, setErr]            = useState<string | null>(null);
  const [log, setLog]            = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const addLog = (msg: string) => setLog(l => [...l.slice(-19), msg]);

  const runPipeline = async () => {
    if (!title.trim() && !description.trim()) { setErr("Başlık veya açıklama giriniz"); return; }
    setRunning(true); setDone(false); setErr(null);
    setStages(PIPELINE_STAGES.map(s => ({ ...s, status: "pending", output_summary: null })));
    setLog([]);

    try {
      // 1. Oturum oluştur
      addLog("Pilot oturumu başlatılıyor…");
      const session = await apiFetch<{ id: string }>(
        `/api/v1/pilot/sessions`,
        { method: "POST", json: { project_id: projectId, user_id: "current" } }
      );
      setSessionId(session.id);
      addLog(`Oturum: ${session.id.slice(0, 8)}…`);

      // 2. Intent gönder
      addLog("Hedef iletiliyor…");
      await apiFetch(
        `/api/v1/pilot/sessions/${session.id}/converse`,
        { method: "POST", json: { text: `${title ? `"${title}" başlıklı senaryo için ` : ""}${description} — BDD + otomasyon kodu üret` } }
      );

      // 3. Otomatik cevaplar
      const answers = [
        "Doğrudan metin yapıştır",
        description || title,
        "Smoke ve regression testler",
      ];
      let current: Record<string, unknown> = session;
      for (const ans of answers) {
        addLog(`Yanıt: "${ans.slice(0, 40)}…"`);
        current = await apiFetch<Record<string, unknown>>(
          `/api/v1/pilot/sessions/${session.id}/clarify`,
          { method: "POST", json: { answer: ans } }
        );
        if (!current.pending_clarification) break;
      }

      // 4. Aşamaları sırayla çalıştır
      const currentStages = (current.stages as PipelineStage[] | undefined) ?? PIPELINE_STAGES;
      setStages(currentStages);

      while (currentStages.some((s: PipelineStage) => s.status === "pending")) {
        addLog("Sonraki aşama çalıştırılıyor…");
        const next = await apiFetch<{ stages: PipelineStage[] }>(
          `/api/v1/pilot/sessions/${session.id}/execute-stage`,
          { method: "POST" }
        );
        setStages(next.stages);
        const completed = next.stages.find(s => s.status === "complete" || s.status === "failed");
        if (completed) addLog(`${completed.title}: ${completed.status === "complete" ? "✓" : "✗"} ${completed.output_summary?.slice(0, 60) ?? ""}`);
        if (next.stages.every(s => s.status !== "pending" && s.status !== "in_progress")) break;
      }

      setDone(true);
      addLog("Pipeline tamamlandı!");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Pipeline hatası");
      addLog(`Hata: ${e instanceof Error ? e.message : "bilinmeyen"}`);
    } finally { setRunning(false); }
  };

  const allDone = stages.every(s => s.status !== "pending" && s.status !== "in_progress");
  const anyFailed = stages.some(s => s.status === "failed");
  const anyComplete = stages.some(s => s.status === "complete");

  return (
    <div className="space-y-6">
      {/* Info banner */}
      <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 px-5 py-4">
        <div className="flex items-start gap-3">
          <span className="text-xl">🚀</span>
          <div>
            <h3 className="text-[14px] font-semibold text-violet-200">6-Aşamalı Otonom Pipeline</h3>
            <p className="mt-1 text-[12px] text-violet-300/70">
              Açıklamanı gir, AI gereksinim analizi → senaryo tasarımı → test verisi → otomasyon kodu → self-heal → iyileştirme aşamalarını otomatik çalıştırır.
            </p>
          </div>
        </div>
      </div>

      {/* Input */}
      {!running && !done && (
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Senaryo Başlığı</label>
            <input value={title} onChange={e => setTitle(e.target.value)}
              placeholder="Kullanıcı ödeme akışını tamamlayabilmeli"
              className={INP} />
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">Açıklama / Gereksinim *</label>
            <textarea value={description} onChange={e => setDesc(e.target.value)} rows={5}
              placeholder={`Sistemin ne yapması gerektiğini açıklayın.\n\nÖrnek:\n- Kullanıcı kredi kartı bilgilerini girebilmeli\n- 3DS doğrulaması yapılabilmeli\n- Başarılı ödemede onay e-postası gönderilmeli\n- Başarısız ödemede kullanıcıya hata gösterilmeli`}
              className={cn(INP, "resize-none")} />
          </div>
          {err && <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-[13px] text-red-400">{err}</p>}
          <button type="button" onClick={runPipeline}
            className="flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-8 py-3 text-[13px] font-semibold text-white hover:from-violet-500 hover:to-purple-500 transition-all shadow-lg shadow-violet-900/20">
            🚀 Pipeline'ı Başlat
          </button>
        </div>
      )}

      {/* Pipeline görünümü */}
      {(running || done) && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-[14px] font-semibold text-slate-100">
              {running ? "Pipeline çalışıyor…" : allDone && !anyFailed ? "✓ Pipeline tamamlandı!" : "Pipeline bitti (bazı hatalar)"}
            </h3>
            {!running && (
              <button type="button" onClick={() => { setDone(false); setRunning(false); setStages(PIPELINE_STAGES); setLog([]); setErr(null); }}
                className="text-[12px] text-slate-500 hover:text-slate-300 transition-colors">
                Yeniden çalıştır
              </button>
            )}
          </div>

          {/* Stage grid */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {stages.map((s, i) => <StageCard key={s.id} stage={s} idx={i} />)}
          </div>

          {/* Log */}
          <div className="rounded-xl border border-slate-800 bg-[#0a0f1a] p-4 font-mono">
            <p className="text-[10px] text-slate-600 mb-2 uppercase tracking-widest">Çalışma günlüğü</p>
            <div className="space-y-0.5 max-h-40 overflow-y-auto">
              {log.map((l, i) => (
                <p key={i} className="text-[11px] text-slate-400">
                  <span className="text-violet-600 mr-2">{String(i + 1).padStart(2, "0")}.</span>{l}
                </p>
              ))}
              {running && <p className="text-[11px] text-teal-400 animate-pulse">▌</p>}
            </div>
          </div>

          {/* Tamamlandı aksiyonlar */}
          {done && anyComplete && (
            <div className="flex flex-wrap gap-3">
              <button type="button"
                onClick={() => router.push(`/p/${projectId}/scenarios`)}
                className="rounded-xl bg-teal-600 px-5 py-2.5 text-[13px] font-semibold text-white hover:bg-teal-500 transition-colors">
                Senaryoları Görüntüle
              </button>
              {sessionId && (
                <button type="button"
                  onClick={() => router.push(`/p/${projectId}/sifir-bilgi?session=${sessionId}`)}
                  className="rounded-xl border border-violet-500/40 bg-violet-500/10 px-5 py-2.5 text-[13px] font-medium text-violet-300 hover:bg-violet-500/20 transition-colors">
                  Pipeline Detayı →
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function NewScenarioPage() {
  const router    = useRouter();
  const projectId = useRouteParam("projectId") ?? "";
  const [mode, setMode] = useState<Mode>("quick");

  const MODES: { id: Mode; icon: string; label: string; desc: string; color: string }[] = [
    {
      id: "quick",
      icon: "✏️",
      label: "Hızlı Oluştur",
      desc: "Manuel senaryo yaz, BDD adımları düzenle",
      color: "teal",
    },
    {
      id: "ai",
      icon: "🤖",
      label: "AI Yardımıyla",
      desc: "Metin, dosya, URL veya ekran görüntüsünden senaryo üret",
      color: "violet",
    },
    {
      id: "pipeline",
      icon: "🚀",
      label: "Otonom Pipeline",
      desc: "6-aşamalı AI pipeline — analiz → senaryo → otomasyon kodu",
      color: "purple",
    },
  ];

  const modeStyle = {
    quick:    { active: "border-teal-500/60 bg-teal-500/8 shadow-teal-900/20",    icon: "bg-teal-500/15 text-teal-300",   bar: "bg-teal-500" },
    ai:       { active: "border-violet-500/60 bg-violet-500/8 shadow-violet-900/20", icon: "bg-violet-500/15 text-violet-300", bar: "bg-violet-500" },
    pipeline: { active: "border-purple-500/60 bg-purple-500/8 shadow-purple-900/20", icon: "bg-purple-500/15 text-purple-300", bar: "bg-purple-500" },
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-6">

      {/* Başlık */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-bold tracking-tight text-slate-100">Yeni Senaryo</h1>
          <p className="mt-1 text-[13px] text-slate-500">Hızlı oluştur, AI destekli üret veya tam otonom pipeline çalıştır</p>
        </div>
        <button type="button" onClick={() => router.back()}
          className="rounded-xl border border-slate-700/60 px-4 py-2 text-[12px] text-slate-400 hover:border-slate-600 hover:text-slate-300 transition-colors">
          ← Geri
        </button>
      </div>

      {/* Mod seçici */}
      <div className="grid gap-3 sm:grid-cols-3">
        {MODES.map(m => {
          const isActive = mode === m.id;
          const style = modeStyle[m.id];
          return (
            <button key={m.id} type="button" onClick={() => setMode(m.id)}
              className={cn(
                "relative flex flex-col gap-3 overflow-hidden rounded-2xl border p-5 text-left transition-all duration-200",
                isActive
                  ? `${style.active} shadow-xl`
                  : "border-slate-700/40 bg-slate-900/40 hover:border-slate-600/60 hover:bg-slate-900/60"
              )}>
              {isActive && <div className={cn("absolute bottom-0 left-0 right-0 h-0.5", style.bar)} />}
              <span className={cn("flex h-9 w-9 items-center justify-center rounded-xl text-lg", isActive ? style.icon : "bg-slate-800 text-slate-500")}>
                {m.icon}
              </span>
              <div>
                <p className={cn("text-[14px] font-semibold", isActive ? "text-slate-100" : "text-slate-400")}>{m.label}</p>
                <p className="mt-0.5 text-[11px] text-slate-500 leading-relaxed">{m.desc}</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Divider */}
      <div className="border-t border-slate-800" />

      {/* Aktif mod içeriği */}
      <div>
        {mode === "quick"    && <QuickCreate    projectId={projectId} />}
        {mode === "ai"       && <AiWorkshop     projectId={projectId} />}
        {mode === "pipeline" && <PilotPipeline  projectId={projectId} />}
      </div>
    </div>
  );
}
