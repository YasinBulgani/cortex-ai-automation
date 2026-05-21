"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { BookText, GitBranch, Layers3, RefreshCw, Save, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import {
  addPromptVersion,
  archivePrompt,
  getPrompt,
  listPromptRollouts,
  listPrompts,
  listPromptVersions,
  resolvePrompt,
  upsertPrompt,
  upsertPromptRollout,
  type PromptEnv,
  type PromptOut,
  type PromptVersionOut,
  type ResolvedPrompt,
  type RolloutOut,
} from "@/lib/prompts-api";

const inputCls =
  "w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition-colors focus:border-blue-500/50";
const textareaCls =
  "w-full min-h-[120px] rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition-colors focus:border-blue-500/50";

function fmtDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminPromptsPage() {
  const [prompts, setPrompts] = useState<PromptOut[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selectedPrompt, setSelectedPrompt] = useState<PromptOut | null>(null);
  const [versions, setVersions] = useState<PromptVersionOut[]>([]);
  const [rollouts, setRollouts] = useState<RolloutOut[]>([]);
  const [resolved, setResolved] = useState<ResolvedPrompt | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [description, setDescription] = useState("");
  const [taskType, setTaskType] = useState("");
  const [versionSystemPrompt, setVersionSystemPrompt] = useState("");
  const [versionUserTemplate, setVersionUserTemplate] = useState("");
  const [versionModelHint, setVersionModelHint] = useState("");
  const [versionTemperature, setVersionTemperature] = useState("");
  const [versionMaxTokens, setVersionMaxTokens] = useState("");
  const [versionNotes, setVersionNotes] = useState("");
  const [rolloutEnv, setRolloutEnv] = useState<PromptEnv>("prod");
  const [rolloutActiveVersion, setRolloutActiveVersion] = useState("");
  const [rolloutCanaryVersion, setRolloutCanaryVersion] = useState("");
  const [rolloutCanaryPct, setRolloutCanaryPct] = useState("0");
  const [resolveEnv, setResolveEnv] = useState<PromptEnv>("prod");
  const [resolveTenant, setResolveTenant] = useState("");

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const items = await listPrompts(true);
      setPrompts(items);
      setError(null);
      if (!selectedId && items[0]) {
        setSelectedId(items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prompt listesi yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  const loadDetail = useCallback(
    async (promptId: string) => {
      if (!promptId) return;
      setDetailLoading(true);
      try {
        const [prompt, promptVersions, promptRollouts] = await Promise.all([
          getPrompt(promptId),
          listPromptVersions(promptId),
          listPromptRollouts(promptId),
        ]);
        setSelectedPrompt(prompt);
        setVersions(promptVersions);
        setRollouts(promptRollouts);
        setDescription(prompt.description ?? "");
        setTaskType(prompt.task_type ?? "");
        setVersionSystemPrompt("");
        setVersionUserTemplate("");
        setVersionModelHint("");
        setVersionTemperature("");
        setVersionMaxTokens("");
        setVersionNotes("");
        setResolved(null);
        setMessage(null);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Prompt detayı yüklenemedi.");
      } finally {
        setDetailLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (selectedId) void loadDetail(selectedId);
  }, [loadDetail, selectedId]);

  const activeRollout = useMemo(
    () => rollouts.find((item) => item.env === rolloutEnv) ?? null,
    [rolloutEnv, rollouts],
  );

  useEffect(() => {
    if (!activeRollout) {
      setRolloutActiveVersion(selectedPrompt?.latest_version ? String(selectedPrompt.latest_version) : "");
      setRolloutCanaryVersion("");
      setRolloutCanaryPct("0");
      return;
    }
    setRolloutActiveVersion(String(activeRollout.active_version));
    setRolloutCanaryVersion(activeRollout.canary_version ? String(activeRollout.canary_version) : "");
    setRolloutCanaryPct(String(activeRollout.canary_pct));
  }, [activeRollout, selectedPrompt]);

  async function handleMetaSave() {
    if (!selectedId) return;
    try {
      const prompt = await upsertPrompt(selectedId, {
        description,
        task_type: taskType.trim() || null,
      });
      setSelectedPrompt(prompt);
      setPrompts((prev) => prev.map((item) => (item.id === prompt.id ? prompt : item)));
      setMessage("Prompt metadatası güncellendi.");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prompt kaydedilemedi.");
    }
  }

  async function handleArchiveToggle() {
    if (!selectedPrompt) return;
    try {
      await archivePrompt(selectedPrompt.id, !selectedPrompt.archived);
      await loadList();
      await loadDetail(selectedPrompt.id);
      setMessage(selectedPrompt.archived ? "Prompt tekrar aktif edildi." : "Prompt arşivlendi.");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Arşiv işlemi başarısız.");
    }
  }

  async function handleVersionCreate() {
    if (!selectedId || !versionSystemPrompt.trim()) {
      setError("Yeni versiyon için system prompt gerekli.");
      return;
    }
    try {
      await addPromptVersion(selectedId, {
        system_prompt: versionSystemPrompt,
        user_template: versionUserTemplate,
        model_hint: versionModelHint.trim() || null,
        temperature: versionTemperature.trim() ? Number(versionTemperature) : null,
        max_tokens: versionMaxTokens.trim() ? Number(versionMaxTokens) : null,
        notes: versionNotes.trim() || null,
      });
      await loadDetail(selectedId);
      await loadList();
      setMessage("Yeni prompt versiyonu eklendi.");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Versiyon eklenemedi.");
    }
  }

  async function handleRolloutSave() {
    if (!selectedId || !rolloutActiveVersion.trim()) {
      setError("Active version gerekli.");
      return;
    }
    try {
      await upsertPromptRollout(selectedId, rolloutEnv, {
        active_version: Number(rolloutActiveVersion),
        canary_version: rolloutCanaryVersion.trim() ? Number(rolloutCanaryVersion) : null,
        canary_pct: Number(rolloutCanaryPct || "0"),
      });
      await loadDetail(selectedId);
      setMessage(`${rolloutEnv} rollout güncellendi.`);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollout güncellenemedi.");
    }
  }

  async function handleResolvePreview() {
    if (!selectedId) return;
    try {
      const next = await resolvePrompt(selectedId, resolveEnv, resolveTenant);
      setResolved(next);
      setMessage("Resolve preview güncellendi.");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resolve preview alınamadı.");
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="admin-prompts-page">
      <PageHeader
        icon={<BookText className="h-5 w-5" />}
        title="Prompt Registry"
        description="Merkezi prompt metadata, versiyon, rollout ve resolve görünümü"
        right={
          <button
            type="button"
            onClick={() => void loadList()}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 transition hover:border-slate-600"
          >
            <RefreshCw className="h-4 w-4" />
            Yenile
          </button>
        }
      />

      {message && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{message}</div>}
      {error && <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.45fr]">
        <SectionCard title="Prompt Listesi" subtitle={`${prompts.length} kayıt`}>
          <div className="space-y-3">
            {loading ? (
              <div className="text-sm text-slate-400">Yükleniyor…</div>
            ) : prompts.length === 0 ? (
              <div className="text-sm text-slate-500">Prompt bulunamadı.</div>
            ) : (
              prompts.map((prompt) => {
                const active = prompt.id === selectedId;
                return (
                  <button
                    key={prompt.id}
                    type="button"
                    onClick={() => setSelectedId(prompt.id)}
                    className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                      active
                        ? "border-blue-500/40 bg-blue-500/10"
                        : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-mono text-xs text-slate-400">{prompt.id}</p>
                        <p className="mt-1 truncate text-sm font-semibold text-white">{prompt.task_type || "task_type yok"}</p>
                      </div>
                      <span
                        className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                          prompt.archived
                            ? "border-amber-500/20 bg-amber-500/10 text-amber-300"
                            : "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                        }`}
                      >
                        {prompt.archived ? "Arşiv" : "Aktif"}
                      </span>
                    </div>
                    <p className="mt-2 line-clamp-2 text-xs text-slate-400">{prompt.description || "Açıklama yok."}</p>
                    <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                      <span>v{prompt.latest_version ?? "-"}</span>
                      <span>{fmtDate(prompt.updated_at)}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </SectionCard>

        <div className="space-y-4">
          <SectionCard
            title="Prompt Metadata"
            subtitle={selectedPrompt ? `${selectedPrompt.id} · son güncelleme ${fmtDate(selectedPrompt.updated_at)}` : "Prompt seçin"}
          >
            {!selectedPrompt ? (
              <p className="text-sm text-slate-500">Prompt seçimi bekleniyor.</p>
            ) : (
              <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                <div className="space-y-3">
                  <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                    <p className="text-xs text-slate-500">Prompt ID</p>
                    <p className="mt-1 font-mono text-sm text-slate-100">{selectedPrompt.id}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                    <p className="text-xs text-slate-500">Latest Version</p>
                    <p className="mt-1 text-sm font-semibold text-white">{selectedPrompt.latest_version ?? "-"}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                    <p className="text-xs text-slate-500">Created By</p>
                    <p className="mt-1 text-sm text-slate-200">{selectedPrompt.created_by || "-"}</p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-slate-400">Task Type</label>
                    <input value={taskType} onChange={(event) => setTaskType(event.target.value)} className={inputCls} placeholder="analyze_document" />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-slate-400">Açıklama</label>
                    <textarea value={description} onChange={(event) => setDescription(event.target.value)} className={textareaCls} placeholder="Prompt amacı ve sınırları" />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void handleMetaSave()}
                      disabled={detailLoading}
                      className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
                    >
                      <Save className="h-4 w-4" />
                      Kaydet
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleArchiveToggle()}
                      disabled={detailLoading}
                      className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition hover:border-slate-600 disabled:opacity-50"
                    >
                      {selectedPrompt.archived ? "Arşivden Çıkar" : "Arşivle"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </SectionCard>

          <div className="grid gap-4 xl:grid-cols-2">
            <SectionCard title="Versiyonlar" subtitle={`${versions.length} kayıt`}>
              <div className="max-h-[460px] space-y-3 overflow-auto pr-1">
                {versions.length === 0 ? (
                  <p className="text-sm text-slate-500">Versiyon bulunamadı.</p>
                ) : (
                  versions.map((version) => (
                    <div key={`${version.prompt_id}-${version.version}`} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[11px] font-semibold text-blue-300">
                          v{version.version}
                        </span>
                        <span className="text-[11px] text-slate-500">{fmtDate(version.created_at)}</span>
                      </div>
                      <p className="mt-3 line-clamp-4 whitespace-pre-wrap text-xs text-slate-300">{version.system_prompt || "System prompt boş."}</p>
                      <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
                        <span>model: {version.model_hint || "-"}</span>
                        <span>temp: {version.temperature ?? "-"}</span>
                        <span>max: {version.max_tokens ?? "-"}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            <SectionCard title="Yeni Versiyon" subtitle="Monotonik versiyon ekler">
              <div className="space-y-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-400">System Prompt</label>
                  <textarea value={versionSystemPrompt} onChange={(event) => setVersionSystemPrompt(event.target.value)} className={`${textareaCls} min-h-[180px]`} />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-400">User Template</label>
                  <textarea value={versionUserTemplate} onChange={(event) => setVersionUserTemplate(event.target.value)} className={textareaCls} />
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <input value={versionModelHint} onChange={(event) => setVersionModelHint(event.target.value)} className={inputCls} placeholder="model hint" />
                  <input value={versionTemperature} onChange={(event) => setVersionTemperature(event.target.value)} className={inputCls} placeholder="temperature" />
                  <input value={versionMaxTokens} onChange={(event) => setVersionMaxTokens(event.target.value)} className={inputCls} placeholder="max tokens" />
                </div>
                <textarea value={versionNotes} onChange={(event) => setVersionNotes(event.target.value)} className={textareaCls} placeholder="Notlar" />
                <button
                  type="button"
                  onClick={() => void handleVersionCreate()}
                  disabled={!selectedPrompt}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  <Layers3 className="h-4 w-4" />
                  Versiyon Ekle
                </button>
              </div>
            </SectionCard>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <SectionCard title="Rollouts" subtitle={`${rollouts.length} environment`}>
              <div className="space-y-3">
                {rollouts.length === 0 ? (
                  <p className="text-sm text-slate-500">Rollout bulunamadı.</p>
                ) : (
                  rollouts.map((rollout) => (
                    <div key={`${rollout.prompt_id}-${rollout.env}`} className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="rounded-full border border-violet-500/20 bg-violet-500/10 px-2 py-0.5 text-[11px] font-semibold text-violet-300">
                          {rollout.env}
                        </span>
                        <span className="text-[11px] text-slate-500">{fmtDate(rollout.updated_at)}</span>
                      </div>
                      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-slate-300">
                        <div>active: <span className="font-semibold text-white">v{rollout.active_version}</span></div>
                        <div>canary: <span className="font-semibold text-white">{rollout.canary_version ? `v${rollout.canary_version}` : "-"}</span></div>
                        <div>pct: <span className="font-semibold text-white">%{rollout.canary_pct}</span></div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            <SectionCard title="Rollout Güncelle" subtitle="Active / canary versiyonunu değiştir">
              <div className="space-y-3">
                <div className="grid gap-3 md:grid-cols-3">
                  <select value={rolloutEnv} onChange={(event) => setRolloutEnv(event.target.value as PromptEnv)} className={inputCls}>
                    <option value="prod">prod</option>
                    <option value="staging">staging</option>
                    <option value="dev">dev</option>
                  </select>
                  <input value={rolloutActiveVersion} onChange={(event) => setRolloutActiveVersion(event.target.value)} className={inputCls} placeholder="active version" />
                  <input value={rolloutCanaryVersion} onChange={(event) => setRolloutCanaryVersion(event.target.value)} className={inputCls} placeholder="canary version" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-400">Canary Yüzdesi</label>
                  <input value={rolloutCanaryPct} onChange={(event) => setRolloutCanaryPct(event.target.value)} className={inputCls} placeholder="0" />
                </div>
                <button
                  type="button"
                  onClick={() => void handleRolloutSave()}
                  disabled={!selectedPrompt}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  <GitBranch className="h-4 w-4" />
                  Rollout Kaydet
                </button>
              </div>
            </SectionCard>
          </div>

          <SectionCard title="Resolve Preview" subtitle="Runtime’da hangi versiyonun çözüldüğünü gör">
            <div className="grid gap-4 xl:grid-cols-[0.7fr_1.3fr]">
              <div className="space-y-3">
                <select value={resolveEnv} onChange={(event) => setResolveEnv(event.target.value as PromptEnv)} className={inputCls}>
                  <option value="prod">prod</option>
                  <option value="staging">staging</option>
                  <option value="dev">dev</option>
                </select>
                <input value={resolveTenant} onChange={(event) => setResolveTenant(event.target.value)} className={inputCls} placeholder="tenant override (opsiyonel)" />
                <button
                  type="button"
                  onClick={() => void handleResolvePreview()}
                  disabled={!selectedPrompt}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  <ShieldCheck className="h-4 w-4" />
                  Resolve Et
                </button>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                {!resolved ? (
                  <p className="text-sm text-slate-500">Henüz resolve preview alınmadı.</p>
                ) : (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2 text-xs">
                      <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-emerald-300">
                        resolved v{resolved.version}
                      </span>
                      <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-slate-300">
                        reason: {resolved.decision_reason}
                      </span>
                    </div>
                    <div className="grid gap-2 md:grid-cols-3 text-xs text-slate-300">
                      <div>active: <span className="font-semibold text-white">v{resolved.active_version}</span></div>
                      <div>canary: <span className="font-semibold text-white">{resolved.canary_version ? `v${resolved.canary_version}` : "-"}</span></div>
                      <div>pct: <span className="font-semibold text-white">%{resolved.canary_pct}</span></div>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                      <p className="mb-2 text-xs font-medium text-slate-500">System Prompt</p>
                      <pre className="whitespace-pre-wrap text-xs text-slate-300">{resolved.system_prompt || "-"}</pre>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
