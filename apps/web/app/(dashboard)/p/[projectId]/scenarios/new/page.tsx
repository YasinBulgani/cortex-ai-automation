"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type AC = { id: string; text: string; kind: string };
type IngestedRequirement = {
  id: string;
  title: string;
  body: string;
  source: string;
  source_ref: string | null;
  acceptance_criteria: AC[];
};

type PipelineStage = {
  id: string;
  title: string;
  status: "pending" | "in_progress" | "complete" | "failed" | "skipped" | "awaiting_input";
  output_summary?: string | null;
};

const PIPELINE_STAGES: PipelineStage[] = [
  { id: "analyze", title: "Analiz / Gereksinim", status: "pending" },
  { id: "design", title: "Senaryo Tasarımı", status: "pending" },
  { id: "data", title: "Test Verisi", status: "pending" },
  { id: "execute", title: "Otomasyon Kodu", status: "pending" },
  { id: "observe", title: "Gözlem & Self-Heal", status: "pending" },
  { id: "iterate", title: "İyileştirme", status: "pending" },
];

export default function NewScenarioPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  // useSearchParams test ortamında mock'lanmamış olabilir — defensive call
  let initialSource: string | null = null;
  try {
    const sp = useSearchParams();
    initialSource = sp?.get("source") ?? null;
  } catch {
    initialSource = null;
  }

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [stepText, setStepText] = useState("Adım 1: …");
  const [err, setErr] = useState<string | null>(null);

  // Jira import state
  const [showJira, setShowJira] = useState(initialSource === "jira");

  // Listeden ?source=pilot ile geldiyse otomatik aç (tek seferlik effect)
  useEffect(() => {
    if (initialSource === "pilot") {
      setShowPilot(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSource]);
  const [jiraKey, setJiraKey] = useState("");
  const [jiraDesc, setJiraDesc] = useState("");
  const [jiraLoading, setJiraLoading] = useState(false);
  const [importedAcs, setImportedAcs] = useState<AC[]>([]);
  const [sourceLabel, setSourceLabel] = useState<string | null>(null);

  // Pilot pipeline state
  const [showPilot, setShowPilot] = useState(false);
  const [stages, setStages] = useState<PipelineStage[]>(PIPELINE_STAGES);
  const [pilotRunning, setPilotRunning] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const steps = [{ order: 0, text: stepText }];
      const created = await apiFetch<{ id: string }>(`/api/v1/tspm/projects/${projectId}/scenarios`, {
        method: "POST",
        json: { title, description, status: "draft", steps },
      });
      router.push(`/p/${projectId}/scenarios/${created.id}`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    }
  }

  async function importFromJira() {
    if (!jiraKey.trim() && !jiraDesc.trim()) {
      setErr("Jira issue key veya açıklama girin");
      return;
    }
    setJiraLoading(true);
    setErr(null);
    try {
      // Use the ingestion endpoint — accepts Jira-shaped payload OR raw text
      const payload = jiraDesc.trim()
        ? {
            issue: {
              key: jiraKey.trim() || "MANUAL",
              fields: { summary: jiraKey.trim() || "Imported", description: jiraDesc.trim() },
            },
          }
        : { issue: { key: jiraKey.trim(), fields: { summary: jiraKey.trim() } } };

      const req = await apiFetch<IngestedRequirement>(
        `/api/v1/ingestion/jira/webhook?project_id=${encodeURIComponent(projectId ?? "")}`,
        { method: "POST", json: payload }
      );

      // Pre-fill form
      setTitle(req.title);
      setDescription(req.body);
      setImportedAcs(req.acceptance_criteria);
      setSourceLabel(`${req.source.toUpperCase()} ${req.source_ref ?? ""}`.trim());
      if (req.acceptance_criteria.length > 0) {
        setStepText(`Adım 1: ${req.acceptance_criteria[0].text}`);
      }
      setShowJira(false);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Jira içe aktarma başarısız");
    } finally {
      setJiraLoading(false);
    }
  }

  async function runPilotPipeline() {
    if (!title.trim() && !description.trim()) {
      setErr("Önce başlık veya açıklama girin (veya Jira'dan içe aktarın)");
      return;
    }
    setShowPilot(true);
    setPilotRunning(true);
    setErr(null);
    setStages(PIPELINE_STAGES.map((s) => ({ ...s, status: "pending", output_summary: null })));

    try {
      // 1. Pilot session başlat
      const session = await apiFetch<any>(`/api/v1/pilot/sessions`, {
        method: "POST",
        json: { project_id: projectId, user_id: "current" },
      });

      // 2. Intent ver
      await apiFetch(`/api/v1/pilot/sessions/${session.id}/converse`, {
        method: "POST",
        json: { text: "Bu gereksinimden senaryo üret ve otomasyon kodu hazırla" },
      });

      // 3. Cevapları otomatik gönder
      const answers = ["Doğrudan metin yapıştır", description || title, "Smoke (kritik akışlar)"];
      let current: any = session;
      for (const ans of answers) {
        current = await apiFetch(`/api/v1/pilot/sessions/${session.id}/clarify`, {
          method: "POST",
          json: { answer: ans },
        });
        if (!current.pending_clarification) break;
      }

      // 4. Stage'leri tek tek koş — her birinde UI güncelle
      while (current.stages.some((s: PipelineStage) => s.status === "pending")) {
        current = await apiFetch<any>(`/api/v1/pilot/sessions/${session.id}/execute-stage`, {
          method: "POST",
        });
        setStages(
          current.stages.map((s: PipelineStage) => ({
            id: s.id,
            title: s.title,
            status: s.status,
            output_summary: s.output_summary ?? null,
          }))
        );
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Pipeline çalıştırılamadı");
    } finally {
      setPilotRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-2" data-testid="new-scenario-page">
      {/* Üst panel — Jira içe aktar + 9 ajanlı Sıfır Bilgi pipeline yönlendirmesi */}
      <div className="grid gap-3 sm:grid-cols-2">
        <button
          onClick={() => setShowJira((v) => !v)}
          data-testid="action-jira-import"
          className="flex items-start gap-3 rounded-xl border border-blue-700/30 bg-blue-950/20 px-4 py-3 text-left hover:border-blue-500/50 transition"
        >
          <span className="text-2xl">📥</span>
          <div>
            <h3 className="text-sm font-semibold text-blue-200">Jira / Doküman içe aktar</h3>
            <p className="text-xs text-blue-300/70">Issue key veya yapıştırılmış metinden gereksinimi parse et + AC çıkar.</p>
          </div>
        </button>
        <a
          href={`/p/${projectId}/sifir-bilgi`}
          data-testid="action-sifir-bilgi"
          className="flex items-start gap-3 rounded-xl border border-violet-700/30 bg-violet-950/20 px-4 py-3 text-left hover:border-violet-500/50 transition"
        >
          <span className="text-2xl">🤖</span>
          <div>
            <h3 className="text-sm font-semibold text-violet-200">Sıfır Bilgi — 9 Ajanlı Pipeline</h3>
            <p className="text-xs text-violet-300/70">Analyst → Explorer → Locator → Scenario → Coder → Runner → Healer → Reviewer → Reporter (canlı SSE).</p>
          </div>
        </a>
      </div>

      {/* Jira modal */}
      {showJira && (
        <div data-testid="jira-import-panel" className="rounded-xl border border-blue-500/30 bg-slate-900/60 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-blue-200">Jira / Doküman'dan içe aktar</h3>
            <button onClick={() => setShowJira(false)} className="text-xs text-slate-400 hover:text-white">Kapat</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-slate-400">Jira Issue Key</label>
              <Input
                value={jiraKey}
                onChange={(e) => setJiraKey(e.target.value)}
                placeholder="NEUREX-123"
                data-testid="jira-key-input"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs text-slate-400">Açıklama / Acceptance Criteria (opsiyonel)</label>
              <textarea
                value={jiraDesc}
                onChange={(e) => setJiraDesc(e.target.value)}
                placeholder="Bullet list, given/when/then veya serbest metin yapıştırın..."
                className="min-h-[90px] w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
                data-testid="jira-desc-input"
              />
            </div>
          </div>
          <Button
            onClick={importFromJira}
            disabled={jiraLoading}
            data-testid="jira-import-submit"
            className="bg-blue-600 hover:bg-blue-500"
          >
            {jiraLoading ? "İçe aktarılıyor..." : "İçe Aktar"}
          </Button>
        </div>
      )}

      {/* Pilot pipeline progress */}
      {showPilot && (
        <div
          data-testid="pilot-pipeline-panel"
          className="rounded-xl border border-violet-500/30 bg-slate-900/60 p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-violet-200">🧭 Pipeline — Analiz → Otomasyon</h3>
            <button onClick={() => setShowPilot(false)} className="text-xs text-slate-400 hover:text-white">
              Gizle
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            {stages.map((s, idx) => (
              <div
                key={s.id + idx}
                data-testid={`pipeline-stage-${s.id}`}
                className={`rounded-lg border px-2.5 py-2 text-xs ${stageClass(s.status)}`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono opacity-60">{idx + 1}.</span>
                  <span className="text-[10px] uppercase tracking-wide opacity-75">{statusLabel(s.status)}</span>
                </div>
                <div className="mt-1 font-semibold">{s.title}</div>
                {s.output_summary && (
                  <p className="mt-1 text-[11px] opacity-85 line-clamp-2">{s.output_summary}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ana form + önizleme */}
      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight" data-testid="new-scenario-heading">Yeni senaryo</h1>
          <p className="text-sm text-slate-400">
            Tek sayfa form{sourceLabel ? ` · Kaynak: ${sourceLabel}` : ""}
          </p>
          <form onSubmit={submit} className="mt-6 space-y-4" data-testid="scenario-form">
            <div>
              <label htmlFor="sc-title" className="mb-1 block text-xs text-slate-400">Başlık</label>
              <Input id="sc-title" value={title} onChange={(e) => setTitle(e.target.value)} required data-testid="scenario-title" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Açıklama</label>
              <textarea
                data-testid="scenario-description"
                className="min-h-[100px] w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">İlk adım</label>
              <textarea
                className="min-h-[80px] w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
                value={stepText}
                onChange={(e) => setStepText(e.target.value)}
              />
            </div>

            {importedAcs.length > 0 && (
              <div data-testid="imported-acs" className="rounded-lg border border-emerald-700/30 bg-emerald-950/20 p-3">
                <p className="text-xs font-semibold text-emerald-200 mb-2">
                  ✓ {importedAcs.length} Acceptance Criteria içe aktarıldı
                </p>
                <ul className="space-y-1 text-xs text-emerald-100/80">
                  {importedAcs.slice(0, 5).map((ac) => (
                    <li key={ac.id} className="flex items-start gap-2">
                      <span className="rounded bg-emerald-800/40 px-1.5 py-0.5 text-[10px] uppercase">{ac.kind}</span>
                      <span>{ac.text}</span>
                    </li>
                  ))}
                  {importedAcs.length > 5 && (
                    <li className="text-emerald-300/60">+{importedAcs.length - 5} daha…</li>
                  )}
                </ul>
              </div>
            )}

            {err && <p className="text-sm text-red-500" data-testid="validation-error">{err}</p>}
            <Button type="submit" data-testid="scenario-save-btn">Kaydet</Button>
          </form>
        </div>

        <div className="rounded-lg border border-slate-800 p-4 lg:sticky lg:top-6 lg:self-start">
          <h2 className="text-sm font-medium">Önizleme</h2>
          <p className="mt-2 text-lg font-medium">{title || "Başlık"}</p>
          <p className="mt-1 text-sm text-slate-400 whitespace-pre-line">{description || "Açıklama"}</p>
          <pre className="mt-4 overflow-auto rounded bg-black/[0.03] p-3 text-xs dark:bg-white/[0.06]">
            {JSON.stringify([{ order: 0, text: stepText }], null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}

function stageClass(status: PipelineStage["status"]): string {
  switch (status) {
    case "in_progress":
      return "border-amber-500/50 bg-amber-500/10 text-amber-200";
    case "complete":
      return "border-emerald-500/50 bg-emerald-500/10 text-emerald-200";
    case "failed":
      return "border-red-500/50 bg-red-500/10 text-red-200";
    case "skipped":
      return "border-slate-800 bg-slate-900/20 text-slate-600";
    case "awaiting_input":
      return "border-blue-500/50 bg-blue-500/10 text-blue-200";
    default:
      return "border-slate-700 bg-slate-900/40 text-slate-400";
  }
}

function statusLabel(status: PipelineStage["status"]): string {
  return (
    {
      pending: "Bekliyor",
      in_progress: "Sürüyor",
      complete: "Tamam",
      failed: "Hata",
      skipped: "Atlandı",
      awaiting_input: "Bilgi bek.",
    } as Record<string, string>
  )[status] ?? status;
}
