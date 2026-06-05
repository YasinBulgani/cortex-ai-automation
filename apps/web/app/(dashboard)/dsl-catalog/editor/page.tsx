"use client";

/**
 * DSL Editor — /dsl-catalog/editor
 * ----------------------------------
 * DSL cümleciklerini ham YAML olarak düzenlemeye izin veren kod editörü.
 *
 * - projectId query param varsa: ilgili action'ın YAML kaynağını yükler.
 * - projectId yoksa: boş editör açılır (yeni YAML girişi).
 * - Save: YAML içeriğini parse ederek action günceller veya oluşturur.
 * - Cancel: önceki sayfaya döner.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  useDslAction,
  useDslCreateAction,
  useDslUpdateAction,
  type DslAction,
  type DslApplyResponse,
} from "@/lib/hooks/use-dsl";
import { ApiError } from "@/lib/api-client";

// ── Stil sabitleri (diğer DSL bileşenleriyle aynı) ────────────────────────

const BTN =
  "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-40";
const BTN_PRIMARY = `${BTN} border-transparent bg-blue-600 text-white hover:bg-blue-500`;
const BTN_GHOST = `${BTN} border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800`;

// ── Yardımcı: DslAction → YAML dizesi (salt görüntüleme/düzenleme için) ──

function actionToYaml(action: DslAction): string {
  // Gerçek bir YAML kütüphanesi olmadan güvenli bir temsil üretiyoruz.
  // Backend "source_yaml" alanı doldurulmuşsa onu kullan.
  if (action.source_yaml) return action.source_yaml;

  const lines: string[] = [];
  lines.push(`id: ${action.id}`);
  lines.push(`category: ${action.category}`);
  lines.push(`description: "${action.description.replace(/"/g, '\\"')}"`);

  if (action.aliases && Object.keys(action.aliases).length > 0) {
    lines.push("aliases:");
    for (const [lang, alias_list] of Object.entries(action.aliases)) {
      lines.push(`  ${lang}:`);
      for (const a of alias_list) {
        lines.push(`    - "${a.replace(/"/g, '\\"')}"`);
      }
    }
  }

  if (action.parameters && action.parameters.length > 0) {
    lines.push("parameters:");
    for (const p of action.parameters) {
      lines.push(`  - name: ${p.name}`);
      lines.push(`    type: ${p.type}`);
      if (p.required !== undefined) lines.push(`    required: ${p.required}`);
      if (p.description) lines.push(`    description: "${p.description}"`);
    }
  }

  if (action.implementations && Object.keys(action.implementations).length > 0) {
    lines.push("implementations:");
    for (const [lang, impl] of Object.entries(action.implementations)) {
      lines.push(`  ${lang}:`);
      lines.push(`    source_file: ${impl.source_file}`);
      if (impl.function) lines.push(`    function: ${impl.function}`);
      if (impl.method) lines.push(`    method: ${impl.method}`);
      if (impl.class) lines.push(`    class: ${impl.class}`);
      if (impl.pattern) lines.push(`    pattern: "${impl.pattern}"`);
    }
  }

  if (action.tags && action.tags.length > 0) {
    lines.push(`tags: [${action.tags.join(", ")}]`);
  }

  if (action.since) lines.push(`since: ${action.since}`);
  if (action.notes) lines.push(`notes: "${action.notes.replace(/"/g, '\\"')}"`);

  if (action.examples && action.examples.length > 0) {
    lines.push("examples:");
    for (const ex of action.examples) {
      lines.push(`  - "${ex.replace(/"/g, '\\"')}"`);
    }
  }

  return lines.join("\n");
}

// ── YAML'den minimal action payload çıkarma (temel alan parse'ı) ────────

function yamlGetField(yaml: string, field: string): string {
  const re = new RegExp(`^${field}:\\s*(.+)$`, "m");
  const match = yaml.match(re);
  return match ? match[1].trim().replace(/^["']|["']$/g, "") : "";
}

function parseYamlToPayload(
  yaml: string,
): Partial<DslAction> & { id: string; category: string } {
  const id = yamlGetField(yaml, "id");
  const category = yamlGetField(yaml, "category");
  const description = yamlGetField(yaml, "description");
  return { id, category, description };
}

// ── ApplyResult banner ────────────────────────────────────────────────────

function ApplyResultBanner({ result }: { result: DslApplyResponse }) {
  const color =
    result.status === "merged"
      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-200"
      : result.status === "pending"
      ? "border-blue-500/30 bg-blue-500/5 text-blue-200"
      : "border-rose-500/30 bg-rose-500/5 text-rose-200";

  return (
    <div className={`rounded-lg border p-3 text-xs ${color}`}>
      <div className="mb-1 font-semibold">
        {result.status === "merged"
          ? "Kaydedildi."
          : result.status === "pending"
          ? "Pending proposal oluşturuldu."
          : "Hata oluştu."}
      </div>
      <ul className="space-y-0.5 font-mono">
        {result.action_id && <li>action: {result.action_id}</li>}
        {result.mode && <li>mode: {result.mode}</li>}
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
          <li>files: {result.file_paths.join(", ")}</li>
        )}
      </ul>
    </div>
  );
}

// ── Ana sayfa bileşeni ────────────────────────────────────────────────────

export default function DslEditorPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const actionId = searchParams.get("projectId") ?? searchParams.get("actionId") ?? undefined;

  const existingQuery = useDslAction(actionId);
  const createMut = useDslCreateAction();
  const updateMut = useDslUpdateAction();

  const [yamlContent, setYamlContent] = useState<string>("");
  const [isDirty, setIsDirty] = useState(false);
  const [applyResult, setApplyResult] = useState<DslApplyResponse | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // action yüklendiğinde YAML içeriğini doldur
  useEffect(() => {
    if (existingQuery.data && !isDirty) {
      setYamlContent(actionToYaml(existingQuery.data));
    }
  }, [existingQuery.data, isDirty]);

  const handleChange = useCallback((value: string) => {
    setYamlContent(value);
    setIsDirty(true);
    setApplyResult(null);
    setSaveError(null);
  }, []);

  function handleTabKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key !== "Tab") return;
    e.preventDefault();
    const el = e.currentTarget;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const newValue =
      yamlContent.substring(0, start) + "  " + yamlContent.substring(end);
    setYamlContent(newValue);
    setIsDirty(true);
    // İmleci sekme sonrasına taşı
    requestAnimationFrame(() => {
      el.selectionStart = el.selectionEnd = start + 2;
    });
  }

  function extractErrorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      if (typeof err.body === "object" && err.body && "detail" in err.body) {
        const detail = (err.body as { detail: unknown }).detail;
        if (typeof detail === "string") return detail;
        if (typeof detail === "object")
          return JSON.stringify(detail, null, 2);
      }
      return err.message;
    }
    return err instanceof Error ? err.message : String(err);
  }

  async function handleSave() {
    setSaveError(null);
    setApplyResult(null);

    const trimmed = yamlContent.trim();
    if (!trimmed) {
      setSaveError("YAML içeriği boş olamaz.");
      return;
    }

    const payload = parseYamlToPayload(trimmed);

    if (!payload.id) {
      setSaveError("YAML'de 'id:' alanı bulunamadı. Lütfen kontrol edin.");
      return;
    }
    if (!payload.category) {
      setSaveError("YAML'de 'category:' alanı bulunamadı.");
      return;
    }

    try {
      const res = actionId
        ? await updateMut.mutateAsync({
            actionId,
            action: payload,
          })
        : await createMut.mutateAsync({ action: payload as DslAction & { id: string; category: string } });

      setApplyResult(res);
      setIsDirty(false);

      if (res.status === "merged") {
        setTimeout(() => router.push("/dsl-catalog"), 1200);
      }
    } catch (err) {
      setSaveError(extractErrorMessage(err));
    }
  }

  const busy = createMut.isPending || updateMut.isPending;
  const isLoading = !!actionId && existingQuery.isLoading;
  const loadError = existingQuery.error;

  const mode: "create" | "edit" = actionId ? "edit" : "create";
  const lineCount = yamlContent.split("\n").length;

  return (
    <div className="flex h-full flex-col gap-4 p-4 sm:p-6">
      {/* Başlık */}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">DSL Editor</h1>
          <p className="mt-1 text-xs text-slate-500">
            {mode === "edit" && actionId ? (
              <>
                Düzenleniyor:{" "}
                <code className="font-mono text-slate-300">{actionId}</code>
              </>
            ) : (
              "Yeni DSL cümleciği — YAML formatında girin."
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => router.back()}
            className={BTN_GHOST}
          >
            ← Geri
          </button>
          <a
            href="/dsl-catalog/editor/new"
            className={BTN_GHOST}
          >
            + Form Editörü
          </a>
        </div>
      </header>

      {/* Yükleniyor durumu */}
      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-500 border-t-blue-400" />
          Cümlecik yükleniyor…
        </div>
      )}

      {/* Yükleme hatası */}
      {loadError && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs text-rose-300">
          Cümlecik yüklenemedi:{" "}
          <span className="font-mono">{loadError.message}</span>
        </div>
      )}

      {/* Ana içerik */}
      {!isLoading && !loadError && (
        <div className="flex flex-1 flex-col gap-4 lg:flex-row">
          {/* Editör alanı */}
          <div className="relative flex flex-1 flex-col">
            {/* Araç çubuğu */}
            <div className="flex items-center justify-between rounded-t-xl border border-b-0 border-slate-800 bg-slate-900 px-3 py-2">
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  YAML
                </span>
                {isDirty && (
                  <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-xs text-amber-400">
                    Kaydedilmedi
                  </span>
                )}
              </div>
              <span className="text-xs text-slate-600">
                {lineCount} satır
              </span>
            </div>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={yamlContent}
              onChange={(e) => handleChange(e.target.value)}
              onKeyDown={handleTabKey}
              spellCheck={false}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              placeholder={`id: my_action\ncategory: ui\ndescription: "Bir şeye tıklar"\naliases:\n  tr:\n    - "kullanıcı {selector} tıklar"\n  en:\n    - "I click on {selector}"\nparameters:\n  - name: selector\n    type: locator\n    required: true\nimplementations:\n  python:\n    source_file: engine/steps/ui/click.py\n    function: click_on_element`}
              className="min-h-[420px] flex-1 resize-none rounded-b-xl border border-slate-800 bg-[#0d1117] p-4 font-mono text-sm leading-relaxed text-slate-100 placeholder-slate-700 outline-none focus:border-blue-500/40 focus:ring-0"
              data-testid="dsl-yaml-editor"
            />
          </div>

          {/* Sağ panel — kaydetme ve bilgi */}
          <aside className="flex w-full flex-col gap-4 lg:w-72 lg:flex-shrink-0">
            {/* Kaydet paneli */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
              <h2 className="mb-3 text-sm font-semibold text-slate-200">
                Kaydet
              </h2>

              {saveError && (
                <div className="mb-3 rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs text-rose-300">
                  {saveError}
                </div>
              )}

              {applyResult && (
                <div className="mb-3">
                  <ApplyResultBanner result={applyResult} />
                </div>
              )}

              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={busy || !yamlContent.trim()}
                  className={BTN_PRIMARY}
                  data-testid="dsl-yaml-save"
                >
                  {busy
                    ? "Kaydediliyor…"
                    : mode === "edit"
                    ? "Güncelle"
                    : "Oluştur"}
                </button>
                <button
                  type="button"
                  onClick={() => router.back()}
                  disabled={busy}
                  className={BTN_GHOST}
                >
                  İptal
                </button>
              </div>

              {mode === "edit" && actionId && (
                <div className="mt-4 border-t border-slate-800 pt-3">
                  <a
                    href={`/dsl-catalog/editor/${actionId}`}
                    className="block text-center text-xs text-slate-500 hover:text-slate-300"
                  >
                    Form editörüne geç →
                  </a>
                </div>
              )}
            </div>

            {/* İpuçları */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
              <h2 className="mb-2 text-sm font-semibold text-slate-200">
                YAML Formatı
              </h2>
              <ul className="space-y-1.5 text-xs text-slate-500">
                <li>
                  <code className="text-slate-400">id:</code> — zorunlu,
                  snake_case
                </li>
                <li>
                  <code className="text-slate-400">category:</code> — zorunlu
                  (ui, api, bgts…)
                </li>
                <li>
                  <code className="text-slate-400">description:</code> — kısa
                  açıklama
                </li>
                <li>
                  <code className="text-slate-400">aliases.tr / .en:</code> —
                  Gherkin kalıpları
                </li>
                <li>
                  <code className="text-slate-400">parameters:</code> — name,
                  type, required
                </li>
                <li>
                  <code className="text-slate-400">implementations:</code> —
                  python / typescript / java
                </li>
                <li className="pt-1 text-slate-600">
                  Tab tuşu 2 boşluk ekler.
                </li>
              </ul>
            </div>

            {/* Var olan cümleciklere hızlı erişim */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
              <h2 className="mb-2 text-sm font-semibold text-slate-200">
                Hızlı Erişim
              </h2>
              <div className="flex flex-col gap-1.5 text-xs">
                <a
                  href="/dsl-catalog"
                  className="text-slate-500 hover:text-slate-300"
                >
                  ← DSL Sözlüğü
                </a>
                <a
                  href="/dsl-catalog/editor/new"
                  className="text-slate-500 hover:text-slate-300"
                >
                  + Yeni cümlecik (form)
                </a>
                <a
                  href="/dsl-catalog/review"
                  className="text-slate-500 hover:text-slate-300"
                >
                  Öneri İncele
                </a>
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
