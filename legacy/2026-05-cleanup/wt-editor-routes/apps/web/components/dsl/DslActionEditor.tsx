"use client";

/**
 * DSL Action Editor
 * ------------------
 * packages/dsl/catalog/*.yaml altındaki cümlecikleri tarayıcı üzerinden
 * oluşturmak, güncellemek, silmek ya da deprecated işaretlemek için form.
 *
 * Kaydetme akışı iki modda çalışır:
 *   - Doğrudan commit: yetkili kullanıcı → YAML'e yazılır + git commit.
 *   - PR modu        : yetkili kullanıcı → branch aç + commit + PR.
 *   - Review modu    : "Öner" → pending proposal (admin onayında uygulanır).
 *
 * Bu bileşen, backend doğrulamasından bağımsız olarak en temel kuralları UI
 * katmanında tekrar kontrol eder — böylece kullanıcı "gönder → 400 döner"
 * yaşamaz. Backend nihai otoritedir.
 */

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  useDslAction,
  useDslEditorConfig,
  useDslCreateAction,
  useDslDeleteAction,
  useDslUpdateAction,
  type DslAction,
  type DslApplyResponse,
  type DslEditOptions,
  type DslGitMode,
  type DslParameter,
} from "@/lib/hooks/use-dsl";
import { ApiError } from "@/lib/api-client";

const INPUT =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";
const LABEL = "block text-xs font-medium uppercase tracking-wider text-slate-500";
const BTN =
  "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-40";
const BTN_PRIMARY = `${BTN} border-transparent bg-blue-600 text-white hover:bg-blue-500`;
const BTN_GHOST = `${BTN} border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800`;
const BTN_DANGER = `${BTN} border-transparent bg-rose-600 text-white hover:bg-rose-500`;

const PARAM_TYPES = [
  "string",
  "int",
  "float",
  "bool",
  "locator",
  "url",
  "duration_ms",
  "json",
] as const;

const CATEGORIES = [
  "ui",
  "api",
  "assert",
  "bgts",
  "mobile",
  "uncategorized",
] as const;

const ID_PATTERN = /^[a-z][a-z0-9_]*$/;
const CATEGORY_PATTERN = /^[a-z][a-z0-9_.]*$/;

// ── Form state modeli ──────────────────────────────────────────────────────

type FormParameter = DslParameter & { _key: string };

interface FormState {
  id: string;
  category: string;
  description: string;
  aliasesTr: string[];
  aliasesEn: string[];
  parameters: FormParameter[];
  tags: string[];
  since: string;
  notes: string;
  examples: string[];
  deprecatedReplacement: string;
  deprecatedReason: string;
  implementations: DslAction["implementations"];
}

function emptyForm(): FormState {
  return {
    id: "",
    category: "",
    description: "",
    aliasesTr: [""],
    aliasesEn: [""],
    parameters: [],
    tags: [],
    since: new Date().toISOString().slice(0, 10),
    notes: "",
    examples: [],
    deprecatedReplacement: "",
    deprecatedReason: "",
    implementations: {},
  };
}

function actionToForm(a: DslAction): FormState {
  const depObj = typeof a.deprecated === "object" && a.deprecated ? a.deprecated : null;
  return {
    id: a.id,
    category: a.category,
    description: a.description,
    aliasesTr: a.aliases?.tr?.length ? [...a.aliases.tr] : [""],
    aliasesEn: a.aliases?.en?.length ? [...a.aliases.en] : [""],
    parameters: (a.parameters ?? []).map((p, i) => ({ ...p, _key: `p${i}-${p.name}` })),
    tags: a.tags ?? [],
    since: a.since ?? new Date().toISOString().slice(0, 10),
    notes: a.notes ?? "",
    examples: a.examples ?? [],
    deprecatedReplacement: depObj?.replacement ?? "",
    deprecatedReason: depObj?.reason ?? "",
    implementations: a.implementations ?? {},
  };
}

function formToPayload(form: FormState): Partial<DslAction> & { id: string; category: string } {
  const aliasesTr = form.aliasesTr.map((s) => s.trim()).filter(Boolean);
  const aliasesEn = form.aliasesEn.map((s) => s.trim()).filter(Boolean);
  const aliases: Record<string, string[]> = {};
  if (aliasesTr.length) aliases.tr = aliasesTr;
  if (aliasesEn.length) aliases.en = aliasesEn;

  const payload: Partial<DslAction> & { id: string; category: string } = {
    id: form.id.trim(),
    category: form.category.trim(),
    description: form.description.trim(),
    aliases,
    parameters: form.parameters.map(({ _key: _, ...p }) => ({
      ...p,
      name: p.name.trim(),
      type: p.type,
      required: p.required ?? true,
    })) as DslParameter[],
    implementations: form.implementations,
    tags: form.tags.filter(Boolean),
    since: form.since || undefined,
    notes: form.notes.trim() || undefined,
    examples: form.examples.filter(Boolean),
  };

  if (form.deprecatedReplacement.trim()) {
    payload.deprecated = {
      replacement: form.deprecatedReplacement.trim(),
      ...(form.deprecatedReason.trim() ? { reason: form.deprecatedReason.trim() } : {}),
    };
  }

  return payload;
}

function validateForm(form: FormState, mode: "create" | "edit"): string[] {
  const errors: string[] = [];
  if (!form.id.trim()) errors.push("ID zorunlu.");
  else if (!ID_PATTERN.test(form.id.trim()))
    errors.push("ID snake_case olmalı: a-z, 0-9, _ (örn. click_on_button).");
  if (!form.category.trim()) errors.push("Kategori zorunlu.");
  else if (!CATEGORY_PATTERN.test(form.category.trim()))
    errors.push("Kategori formatı yanlış (örn. ui.click, bgts.approval).");
  if (!form.description.trim() || form.description.trim().length < 5)
    errors.push("Açıklama en az 5 karakter olmalı.");
  const trFilled = form.aliasesTr.filter((s) => s.trim()).length;
  const enFilled = form.aliasesEn.filter((s) => s.trim()).length;
  if (trFilled + enFilled === 0) errors.push("En az bir TR veya EN alias ekleyin.");
  for (const p of form.parameters) {
    if (!p.name.trim()) errors.push("Parametre adı boş olamaz.");
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(p.name.trim()))
      errors.push(`Parametre adı geçersiz: ${p.name || "(boş)"}`);
  }
  if (mode === "create" && Object.keys(form.implementations).length === 0)
    errors.push("En az bir implementation tanımlayın (python / java / typescript).");
  return errors;
}

// ── Alt UI parçaları ───────────────────────────────────────────────────────

function StringList({
  values,
  onChange,
  placeholder,
  addLabel,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  addLabel: string;
}) {
  return (
    <div className="space-y-2">
      {values.map((v, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <input
            type="text"
            value={v}
            onChange={(e) => {
              const next = [...values];
              next[idx] = e.target.value;
              onChange(next);
            }}
            placeholder={placeholder}
            className={INPUT}
          />
          <button
            type="button"
            onClick={() => onChange(values.filter((_, i) => i !== idx))}
            className={BTN_GHOST}
            aria-label="Sil"
          >
            ×
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...values, ""])}
        className={BTN_GHOST}
      >
        + {addLabel}
      </button>
    </div>
  );
}

function ParametersEditor({
  params,
  onChange,
}: {
  params: FormParameter[];
  onChange: (next: FormParameter[]) => void;
}) {
  const add = () =>
    onChange([
      ...params,
      {
        _key: `p${Date.now()}`,
        name: "",
        type: "string",
        required: true,
        description: "",
      },
    ]);
  return (
    <div className="space-y-2">
      {params.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-700 p-3 text-xs text-slate-500">
          Parametre yok.
        </div>
      )}
      {params.map((p, idx) => (
        <div
          key={p._key}
          className="grid grid-cols-1 gap-2 rounded-lg border border-slate-800 bg-slate-900/40 p-3 sm:grid-cols-[1fr_120px_auto_1fr_auto]"
        >
          <input
            className={INPUT}
            value={p.name}
            placeholder="name"
            onChange={(e) => {
              const next = [...params];
              next[idx] = { ...p, name: e.target.value };
              onChange(next);
            }}
          />
          <select
            className={INPUT}
            value={p.type}
            aria-label="Parametre tipi"
            title="Parametre tipi"
            onChange={(e) => {
              const next = [...params];
              next[idx] = { ...p, type: e.target.value };
              onChange(next);
            }}
          >
            {PARAM_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <input
              type="checkbox"
              checked={p.required ?? true}
              aria-label="Parametre zorunlu mu?"
              title="Parametre zorunlu mu?"
              onChange={(e) => {
                const next = [...params];
                next[idx] = { ...p, required: e.target.checked };
                onChange(next);
              }}
            />
            zorunlu
          </label>
          <input
            className={INPUT}
            value={p.description ?? ""}
            placeholder="açıklama"
            onChange={(e) => {
              const next = [...params];
              next[idx] = { ...p, description: e.target.value };
              onChange(next);
            }}
          />
          <button
            type="button"
            onClick={() => onChange(params.filter((_, i) => i !== idx))}
            className={BTN_GHOST}
            aria-label="Parametreyi sil"
          >
            ×
          </button>
        </div>
      ))}
      <button type="button" onClick={add} className={BTN_GHOST}>
        + Parametre
      </button>
    </div>
  );
}

function ImplementationsEditor({
  impls,
  onChange,
}: {
  impls: DslAction["implementations"];
  onChange: (next: DslAction["implementations"]) => void;
}) {
  const langs: Array<"python" | "typescript" | "java"> = ["python", "typescript", "java"];
  return (
    <div className="space-y-3">
      {langs.map((lang) => {
        const impl = impls?.[lang];
        const active = !!impl;
        return (
          <div key={lang} className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
            <div className="mb-2 flex items-center justify-between">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={active}
                  aria-label={`${lang} implementation aktif`}
                  title={`${lang} implementation aktif`}
                  onChange={(e) => {
                    const next = { ...(impls ?? {}) };
                    if (e.target.checked) {
                      next[lang] = impl ?? { source_file: "" };
                    } else {
                      delete next[lang];
                    }
                    onChange(next);
                  }}
                />
                <span className="text-sm font-medium text-slate-200">{lang}</span>
              </label>
            </div>
            {active && (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <input
                  className={INPUT}
                  value={impl?.source_file ?? ""}
                  placeholder="source_file (engine/steps/... .py)"
                  onChange={(e) => {
                    const next = { ...(impls ?? {}) };
                    next[lang] = { ...(impl ?? {}), source_file: e.target.value };
                    onChange(next);
                  }}
                />
                <input
                  className={INPUT}
                  value={impl?.function ?? impl?.method ?? ""}
                  placeholder={lang === "java" ? "method" : "function"}
                  onChange={(e) => {
                    const next = { ...(impls ?? {}) };
                    const field = lang === "java" ? "method" : "function";
                    next[lang] = { ...(impl ?? { source_file: "" }), [field]: e.target.value };
                    onChange(next);
                  }}
                />
                {lang === "java" && (
                  <input
                    className={INPUT}
                    value={impl?.class ?? ""}
                    placeholder="class (stepdefinitions.ClickSteps)"
                    onChange={(e) => {
                      const next = { ...(impls ?? {}) };
                      next[lang] = { ...(impl ?? { source_file: "" }), class: e.target.value };
                      onChange(next);
                    }}
                  />
                )}
                <input
                  className={INPUT}
                  value={impl?.pattern ?? ""}
                  placeholder="pattern (opsiyonel — alias'tan türetilir)"
                  onChange={(e) => {
                    const next = { ...(impls ?? {}) };
                    next[lang] = { ...(impl ?? { source_file: "" }), pattern: e.target.value };
                    onChange(next);
                  }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Ana bileşen ────────────────────────────────────────────────────────────

export function DslActionEditor({
  actionId,
  mode,
  onSaved,
}: {
  actionId?: string;
  mode: "create" | "edit";
  onSaved?: (res: DslApplyResponse) => void;
}) {
  const router = useRouter();
  const existing = useDslAction(mode === "edit" ? actionId : undefined);
  const cfg = useDslEditorConfig();

  const createMut = useDslCreateAction();
  const updateMut = useDslUpdateAction();
  const deleteMut = useDslDeleteAction();

  const [form, setForm] = useState<FormState>(() => emptyForm());
  const [gitMode, setGitMode] = useState<DslGitMode | "auto">("auto");
  const [requireReview, setRequireReview] = useState(false);
  const [commitMessage, setCommitMessage] = useState("");
  const [applyResult, setApplyResult] = useState<DslApplyResponse | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (mode === "edit" && existing.data) {
      setForm(actionToForm(existing.data));
    } else if (mode === "create") {
      setForm(emptyForm());
    }
  }, [mode, existing.data]);

  const errors = useMemo(() => validateForm(form, mode), [form, mode]);
  const busy = createMut.isPending || updateMut.isPending || deleteMut.isPending;

  const effectiveGitMode = gitMode === "auto" ? cfg.data?.git_mode : gitMode;

  function buildOptions(): DslEditOptions {
    return {
      require_review: requireReview,
      git_mode: gitMode === "auto" ? undefined : gitMode,
      commit_message: commitMessage.trim() || undefined,
    };
  }

  function handleError(err: unknown): string {
    if (err instanceof ApiError) {
      if (typeof err.body === "object" && err.body && "detail" in err.body) {
        const detail = (err.body as { detail: unknown }).detail;
        if (typeof detail === "string") return detail;
        if (typeof detail === "object") return JSON.stringify(detail, null, 2);
      }
      return err.message;
    }
    return err instanceof Error ? err.message : String(err);
  }

  async function onSubmit() {
    if (errors.length > 0) return;
    const payload = formToPayload(form);
    setApplyResult(null);
    try {
      const res =
        mode === "create"
          ? await createMut.mutateAsync({ action: payload, options: buildOptions() })
          : await updateMut.mutateAsync({
              actionId: form.id,
              action: payload,
              options: buildOptions(),
            });
      setApplyResult(res);
      onSaved?.(res);
    } catch (err) {
      setApplyResult({
        proposal_id: "",
        status: "error",
        mode: "disabled",
        action_id: form.id,
        file_paths: [],
        branch: null,
        commit_sha: null,
        pr_url: null,
      });
      alert(`Kaydetme hatası:\n\n${handleError(err)}`);
    }
  }

  async function onDelete() {
    if (!form.id) return;
    try {
      const res = await deleteMut.mutateAsync({
        actionId: form.id,
        options: buildOptions(),
      });
      setApplyResult(res);
      setShowDeleteConfirm(false);
      if (res.status === "merged") {
        setTimeout(() => router.push("/dsl-catalog"), 800);
      }
    } catch (err) {
      alert(`Silme hatası:\n\n${handleError(err)}`);
    }
  }

  if (mode === "edit" && existing.isLoading) {
    return <div className="p-6 text-slate-400">Yükleniyor…</div>;
  }
  if (mode === "edit" && existing.error) {
    return (
      <div className="p-6 text-rose-400">
        Cümlecik yüklenemedi: {existing.error.message}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-5 p-4 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">
            {mode === "create" ? "Yeni DSL Cümleciği" : `Düzenle: ${form.id}`}
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Değişiklikler{" "}
            <code className="font-mono text-slate-400">packages/dsl/catalog/</code>{" "}
            altındaki YAML dosyasına yazılır.
          </p>
        </div>
        <button type="button" onClick={() => router.back()} className={BTN_GHOST}>
          ← Geri
        </button>
      </header>

      <GitStatusBanner
        enabled={cfg.data?.git_enabled ?? false}
        mode={effectiveGitMode}
        requireReview={requireReview}
      />

      {errors.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200">
          <div className="mb-1 font-semibold">Form hataları:</div>
          <ul className="list-inside list-disc space-y-0.5">
            {errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_360px]">
        {/* SOL — Form */}
        <div className="space-y-5">
          <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <h2 className="text-sm font-semibold text-slate-200">Kimlik</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL}>ID</label>
                <input
                  className={INPUT}
                  value={form.id}
                  disabled={mode === "edit"}
                  placeholder="click_on_button"
                  onChange={(e) => setForm({ ...form, id: e.target.value })}
                />
              </div>
              <div>
                <label className={LABEL}>Kategori</label>
                <input
                  className={INPUT}
                  value={form.category}
                  list="dsl-category-suggestions"
                  placeholder="ui.click"
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                />
                <datalist id="dsl-category-suggestions">
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c} />
                  ))}
                </datalist>
              </div>
            </div>
            <div>
              <label className={LABEL}>Açıklama</label>
              <textarea
                className={`${INPUT} min-h-[64px]`}
                value={form.description}
                placeholder="Cümleciğin ne yaptığının kısa açıklaması"
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
          </section>

          <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <h2 className="text-sm font-semibold text-slate-200">Alias'lar</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className={LABEL}>Türkçe</label>
                <StringList
                  values={form.aliasesTr}
                  onChange={(v) => setForm({ ...form, aliasesTr: v })}
                  placeholder={'kullanıcı "{selector}" tıklar'}
                  addLabel="TR alias"
                />
              </div>
              <div>
                <label className={LABEL}>İngilizce</label>
                <StringList
                  values={form.aliasesEn}
                  onChange={(v) => setForm({ ...form, aliasesEn: v })}
                  placeholder="I click on {selector}"
                  addLabel="EN alias"
                />
              </div>
            </div>
          </section>

          <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <h2 className="text-sm font-semibold text-slate-200">Parametreler</h2>
            <ParametersEditor
              params={form.parameters}
              onChange={(v) => setForm({ ...form, parameters: v })}
            />
          </section>

          <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <h2 className="text-sm font-semibold text-slate-200">Implementation'lar</h2>
            <ImplementationsEditor
              impls={form.implementations}
              onChange={(v) => setForm({ ...form, implementations: v })}
            />
          </section>

          <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <h2 className="text-sm font-semibold text-slate-200">Meta</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL} htmlFor="dsl-editor-since">
                  Tarih (since)
                </label>
                <input
                  id="dsl-editor-since"
                  type="date"
                  className={INPUT}
                  value={form.since}
                  aria-label="Ekleme tarihi"
                  title="Ekleme tarihi (YYYY-MM-DD)"
                  onChange={(e) => setForm({ ...form, since: e.target.value })}
                />
              </div>
              <div>
                <label className={LABEL}>Etiketler (virgülle)</label>
                <input
                  className={INPUT}
                  value={form.tags.join(", ")}
                  placeholder="ui, smoke, click"
                  onChange={(e) =>
                    setForm({
                      ...form,
                      tags: e.target.value
                        .split(",")
                        .map((s) => s.trim().toLowerCase())
                        .filter(Boolean),
                    })
                  }
                />
              </div>
            </div>
            <div>
              <label className={LABEL} htmlFor="dsl-editor-notes">
                Notlar
              </label>
              <textarea
                id="dsl-editor-notes"
                className={`${INPUT} min-h-[60px]`}
                value={form.notes}
                placeholder="Ek notlar, bilinmesi gerekenler (opsiyonel)"
                aria-label="Notlar"
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <div>
              <label className={LABEL}>Örnekler (her satıra bir)</label>
              <textarea
                className={`${INPUT} min-h-[80px] font-mono text-xs`}
                value={form.examples.join("\n")}
                onChange={(e) =>
                  setForm({
                    ...form,
                    examples: e.target.value.split("\n").filter(Boolean),
                  })
                }
                placeholder={"When kullanıcı \"login\" butonuna tıklar"}
              />
            </div>
          </section>

          {mode === "edit" && (
            <section className="space-y-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
              <h2 className="text-sm font-semibold text-amber-200">
                Deprecate (opsiyonel)
              </h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className={LABEL}>Yerine (replacement)</label>
                  <input
                    className={INPUT}
                    value={form.deprecatedReplacement}
                    placeholder="click_on_element"
                    onChange={(e) =>
                      setForm({ ...form, deprecatedReplacement: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className={LABEL}>Sebep</label>
                  <input
                    className={INPUT}
                    value={form.deprecatedReason}
                    placeholder="Yeni sürümde birleştirildi"
                    onChange={(e) =>
                      setForm({ ...form, deprecatedReason: e.target.value })
                    }
                  />
                </div>
              </div>
            </section>
          )}
        </div>

        {/* SAĞ — Kaydet paneli */}
        <aside className="h-fit space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4 lg:sticky lg:top-4">
          <h2 className="text-sm font-semibold text-slate-200">Kaydet</h2>

          <div>
            <label className={LABEL} htmlFor="dsl-editor-git-mode">
              Git modu
            </label>
            <select
              id="dsl-editor-git-mode"
              className={INPUT}
              value={gitMode}
              aria-label="Git kaydetme modu"
              onChange={(e) => setGitMode(e.target.value as DslGitMode | "auto")}
            >
              <option value="auto">
                Otomatik ({cfg.data?.git_mode ?? "direct_commit"})
              </option>
              <option value="direct_commit">Doğrudan commit</option>
              <option value="pr">Pull Request</option>
            </select>
          </div>

          <label className="flex items-start gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={requireReview}
              onChange={(e) => setRequireReview(e.target.checked)}
              aria-label="Sadece öner — YAML'e yazma, admin onayı bekle"
              title="Sadece öner — YAML'e yazma, admin onayı bekle"
              className="mt-0.5"
            />
            <span>
              <strong>Sadece öner</strong> — YAML'e yazılmaz, admin onayı bekler.
            </span>
          </label>

          <div>
            <label className={LABEL}>Commit mesajı (opsiyonel)</label>
            <textarea
              className={`${INPUT} min-h-[70px] font-mono text-xs`}
              value={commitMessage}
              placeholder="Varsayılan: dsl: add <id> (via UI)"
              onChange={(e) => setCommitMessage(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2 pt-2">
            <button
              type="button"
              onClick={onSubmit}
              disabled={errors.length > 0 || busy}
              className={BTN_PRIMARY}
              data-testid="dsl-editor-save"
            >
              {busy
                ? "Gönderiliyor…"
                : requireReview
                ? "Öner (Pending)"
                : mode === "create"
                ? "Oluştur"
                : "Güncelle"}
            </button>
            {mode === "edit" && (
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={busy}
                className={BTN_DANGER}
              >
                Sil
              </button>
            )}
          </div>

          {applyResult && <ApplyResultView result={applyResult} />}
        </aside>
      </div>

      {showDeleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setShowDeleteConfirm(false)}
        >
          <div
            className="w-full max-w-md rounded-xl border border-rose-500/30 bg-slate-950 p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-2 text-base font-semibold text-white">
              Bu cümleciği silmek istediğinizden emin misiniz?
            </h3>
            <p className="mb-4 text-sm text-slate-400">
              <code className="text-rose-300">{form.id}</code> katalogtan silinir
              ve git commit olarak kaydedilir.
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                className={BTN_GHOST}
                onClick={() => setShowDeleteConfirm(false)}
              >
                Vazgeç
              </button>
              <button
                type="button"
                className={BTN_DANGER}
                onClick={onDelete}
                disabled={deleteMut.isPending}
              >
                {deleteMut.isPending ? "Siliniyor…" : "Evet, sil"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function GitStatusBanner({
  enabled,
  mode,
  requireReview,
}: {
  enabled: boolean;
  mode?: string;
  requireReview: boolean;
}) {
  if (requireReview) {
    return (
      <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 px-3 py-2 text-xs text-violet-200">
        ✉ Önerin <strong>pending</strong> olarak kaydedilecek — admin onayından
        sonra YAML'e ve git'e işlenir.
      </div>
    );
  }
  if (!enabled) {
    return (
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-200">
        ⚠ DSL_GIT_ENABLED=false — Değişiklikler sadece YAML dosyasına yazılır, git
        commit atılmaz.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-200">
      ✓ Git aktif — mod: <span className="font-mono">{mode ?? "?"}</span>. Kaydet
      basıldığında YAML yazılacak ve commit atılacak.
    </div>
  );
}

function ApplyResultView({ result }: { result: DslApplyResponse }) {
  const color =
    result.status === "merged"
      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-200"
      : result.status === "pending"
      ? "border-blue-500/30 bg-blue-500/5 text-blue-200"
      : "border-rose-500/30 bg-rose-500/5 text-rose-200";
  return (
    <div className={`mt-3 rounded-lg border p-3 text-xs ${color}`}>
      <div className="mb-1 font-semibold">
        {result.status === "merged"
          ? "Kaydedildi."
          : result.status === "pending"
          ? "Pending proposal oluşturuldu."
          : "Hata."}
      </div>
      <ul className="space-y-1 font-mono">
        <li>mode: {result.mode}</li>
        {result.proposal_id && <li>proposal: {result.proposal_id}</li>}
        {result.commit_sha && <li>commit: {result.commit_sha.slice(0, 10)}</li>}
        {result.branch && <li>branch: {result.branch}</li>}
        {result.pr_url && (
          <li>
            PR:{" "}
            <a
              href={result.pr_url}
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              {result.pr_url}
            </a>
          </li>
        )}
        {result.file_paths.length > 0 && (
          <li>files: {result.file_paths.length}</li>
        )}
      </ul>
    </div>
  );
}
