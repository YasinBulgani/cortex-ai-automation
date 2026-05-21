"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { useToast } from "@/components/ui/toast";

// ─── Types ───────────────────────────────────────────────────────────────────

type Feature = {
  name: string;
  content?: string;
  path: string;
  updated_at?: string | null;
};

type FeatureTreeItem = {
  type: "file" | "folder";
  name: string;
  path: string;
  modified?: string;
  children?: FeatureTreeItem[];
};

type CreateFeatureForm = {
  name: string;
  content: string;
};

type AutomationKind = "web" | "mobile" | "api" | "llm" | "regression";

type AutomationCapability = {
  kind: AutomationKind;
  label: string;
  description: string;
  provenance: "real" | "simulated" | "fallback" | "stub";
  required_fields: string[];
  route_hint?: string | null;
};

type AutomationRun = {
  id: string;
  project_id: string;
  kind: AutomationKind;
  name: string;
  status: "queued" | "running" | "passed" | "failed" | "cancelled";
  trigger: string;
  target?: string | null;
  device?: string | null;
  environment?: string | null;
  provenance: "real" | "simulated" | "fallback" | "stub";
  metrics?: Record<string, unknown>;
  created_at: string;
  next_action?: { href?: string; label?: string } | null;
};

type AutomationRunList = {
  items: AutomationRun[];
  total: number;
};

// ─── Constants ───────────────────────────────────────────────────────────────

const PROXY = "/api/v1/automation/proxy/api/features";
const BRAIN_CAPABILITIES = "/api/v1/automation/brain/capabilities";
const BRAIN_RUNS = "/api/v1/automation/runs";

const GHERKIN_PLACEHOLDER = `Feature: Örnek özellik
  Senaryo olarak kullanıcı

  Scenario: Kullanıcı başarıyla giriş yapar
    Given kullanıcı login sayfasındadır
    When kullanıcı e-posta ve şifre girer
    And "Giriş Yap" butonuna tıklar
    Then anasayfaya yönlendirilir`;

function ensureFeatureFilename(name: string): string {
  const trimmed = name.trim().replace(/^\/+/, "");
  if (!trimmed) return "";
  return trimmed.endsWith(".feature") ? trimmed : `${trimmed}.feature`;
}

function flattenFeatureTree(items: FeatureTreeItem[]): Feature[] {
  const result: Feature[] = [];

  for (const item of items) {
    if (item.type === "file") {
      result.push({
        name: item.name,
        path: item.path,
        updated_at: item.modified ?? null,
      });
      continue;
    }

    if (item.children?.length) {
      result.push(...flattenFeatureTree(item.children));
    }
  }

  return result;
}

// ─── Create Modal ─────────────────────────────────────────────────────────────

function CreateFeatureModal({
  onClose,
  onCreated,
  initial,
}: {
  onClose: () => void;
  onCreated: () => void;
  initial?: CreateFeatureForm;
}) {
  const [form, setForm] = useState<CreateFeatureForm>(initial ?? { name: "", content: "" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const filename = ensureFeatureFilename(form.name);
    if (!filename) return;
    setErr(null);
    setSaving(true);
    try {
      await apiFetch(`${PROXY}/${filename}`, {
        method: "PUT",
        json: { content: form.content.trim() },
      });
      onCreated();
      onClose();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata oluştu");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      data-testid="automation-create-modal"
    >
      <div className="w-full max-w-xl rounded-lg border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Yeni Feature Dosyası</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded opacity-70 hover:opacity-100 focus:outline-none"
            aria-label="Kapat"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" data-testid="automation-create-form">
          <div className="space-y-1">
            <label className="text-xs text-slate-400">Dosya adı *</label>
            <Input
              ref={nameRef}
              placeholder="ör. login.feature"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              data-testid="automation-input-name"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-slate-400">Gherkin içeriği</label>
            <textarea
              placeholder={GHERKIN_PLACEHOLDER}
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              rows={10}
              className="flex w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 font-mono text-xs text-white placeholder:text-slate-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent resize-y"
              data-testid="automation-textarea-content"
            />
          </div>
          {err && (
            <p className="text-sm text-red-600" data-testid="automation-create-error">
              {err}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              İptal
            </Button>
            <Button
              type="submit"
              disabled={saving}
              data-testid="automation-btn-save"
            >
              {saving ? "Kaydediliyor…" : "Oluştur"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AutomationPage() {
  const projectId = useRouteParam("projectId");
  const router = useRouter();
  const { confirm } = useConfirm();
  const { toast } = useToast();

  const [features, setFeatures] = useState<Feature[]>([]);
  const [selected, setSelected] = useState<Feature | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [templateSeed, setTemplateSeed] = useState<CreateFeatureForm | undefined>(undefined);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<AutomationCapability[]>([]);
  const [brainRuns, setBrainRuns] = useState<AutomationRun[]>([]);
  const [brainLoading, setBrainLoading] = useState(true);
  const [startingKind, setStartingKind] = useState<AutomationKind | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<FeatureTreeItem[]>(PROXY);
      setFeatures(flattenFeatureTree(data ?? []));
    } catch {
      setFeatures([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (feature: Feature) => {
    // Fetch fresh detail in case content is not included in list response
    setEditMode(false);
    setSaveErr(null);
    try {
      const detail = await apiFetch<{ name: string; content: string }>(`${PROXY}/${feature.path}`);
      setSelected({ ...feature, content: detail.content });
    } catch {
      setSelected(feature);
    }
  }, []);

  const loadBrain = useCallback(async () => {
    if (!projectId) return;
    setBrainLoading(true);
    try {
      const [caps, runs] = await Promise.all([
        apiFetch<AutomationCapability[]>(BRAIN_CAPABILITIES),
        apiFetch<AutomationRunList>(`${BRAIN_RUNS}?project_id=${encodeURIComponent(projectId.toString())}&limit=8`),
      ]);
      setCapabilities(caps);
      setBrainRuns(runs.items ?? []);
    } catch {
      setCapabilities([]);
      setBrainRuns([]);
    } finally {
      setBrainLoading(false);
    }
  }, [projectId]);

  async function handleSaveEdit() {
    if (!selected) return;
    setSaving(true);
    setSaveErr(null);
    try {
      await apiFetch(`${PROXY}/${selected.path}`, {
        method: "PUT",
        json: { content: editContent },
      });
      setSelected({ ...selected, content: editContent });
      setEditMode(false);
      await load();
    } catch (e: unknown) {
      setSaveErr(e instanceof Error ? e.message : "Kaydetme hatası");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    void loadBrain();
  }, [loadBrain]);

  // Auto-select first item when list loads
  useEffect(() => {
    if (!loading && features.length > 0 && !selected) {
      void loadDetail(features[0]);
    }
    if (!loading && features.length === 0) {
      setSelected(null);
    }
  }, [loading, features, selected, loadDetail]);

  async function handleDelete(path: string) {
    // Kullanıcı kazara tıkladıysa geri dönebilsin — onay modalı.
    const ok = await confirm({
      title: "Feature dosyasını sil",
      message: `\"${path}\" dosyası engine diskinden silinecek. Bu işlem geri alınamaz. Devam edilsin mi?`,
      confirmLabel: "Sil",
      cancelLabel: "Vazgeç",
      variant: "danger",
    });
    if (!ok) return;

    setDeleting(path);
    try {
      await apiFetch(`${PROXY}/${path}`, { method: "DELETE" });
      if (selected?.path === path) setSelected(null);
      toast(`${path} silindi.`, "success");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Silme hatası", "error");
    } finally {
      setDeleting(null);
    }
  }

  // Seçili feature için doğrudan koşum başlat. /executions/new sayfası
  // bu query paramı alır ve formu önceden doldurur. Frontend tek sayfa davranışı.
  function handleRunSelected() {
    if (!selected) return;
    router.push(`/p/${projectId}/executions/new?feature=${encodeURIComponent(selected.path)}`);
  }

  async function startBrainRun(kind: AutomationKind) {
    setStartingKind(kind);
    const canExecuteNow = (kind === "web" && Boolean(selected?.path)) || kind === "mobile" || kind === "regression";
    try {
      const run = await apiFetch<AutomationRun>(BRAIN_RUNS, {
        method: "POST",
        json: {
          project_id: projectId.toString(),
          kind,
          name: `${capabilities.find((cap) => cap.kind === kind)?.label ?? kind} merkezi koşum`,
          target: kind === "web" ? selected?.path ?? null : null,
          trigger: "manual",
          environment: "local",
          execute_now: canExecuteNow,
          device: null,
          metadata: {
            source_page: "automation_center",
            ...(kind === "mobile"
              ? {
                  mobile_prompt: "Uygulamayı aç, ana ekranın görünür olduğunu doğrula ve temel smoke kontrolünü tamamla.",
                  parallel: 2,
                  platform: "both",
                  mode: "simulation",
                }
              : {}),
            ...(kind === "regression"
              ? {
                  extra_instructions: "E2E smoke, kritik kullanıcı akışları ve son hata risklerini öne çıkar.",
                }
              : {}),
          },
        },
      });
      toast(
        run.metrics?.external_run_id || run.metrics?.external_session_ids || run.metrics?.suggested_set_count
          ? `${run.name} gerçek runner üzerinde başladı.`
          : `${run.name} oluşturuldu.`,
        "success",
      );
      await loadBrain();
      if (!run.metrics?.external_run_id && !run.metrics?.external_session_ids && !run.metrics?.suggested_set_count && run.next_action?.href) {
        router.push(run.next_action.href);
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : "Koşum başlatılamadı", "error");
    } finally {
      setStartingKind(null);
    }
  }

  async function cancelBrainRun(runId: string) {
    try {
      await apiFetch(`${BRAIN_RUNS}/${runId}/cancel`, { method: "POST" });
      await loadBrain();
      toast("Koşum iptal edildi.", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "İptal edilemedi", "error");
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6" data-testid="automation-page">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-500/10 text-xl">⚙️</span>
            <div>
              <h1
                className="text-2xl font-semibold tracking-tight text-white"
                data-testid="automation-heading"
              >
                Otomasyon
              </h1>
              <p className="text-sm text-slate-400">
                Gherkin feature dosyalarını yönet ve Playwright testleri çalıştır
              </p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link href={`/p/${projectId}/scenarios/generate`}>
            <Button
              type="button"
              variant="secondary"
              data-testid="automation-btn-ai-generate"
            >
              ✨ AI ile Oluştur
            </Button>
          </Link>
          <Button
            type="button"
            onClick={() => setShowCreate(true)}
            data-testid="automation-btn-new"
          >
            + Yeni Feature
          </Button>
          <Link href={`/p/${projectId}/runs`}>
            <Button
              type="button"
              variant="secondary"
              data-testid="automation-btn-run"
            >
              ▶️ Koşulara Git
            </Button>
          </Link>
        </div>
      </div>

      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4" data-testid="automation-brain-panel">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300/80">Automation Brain</p>
            <h2 className="mt-1 text-lg font-semibold text-white">Tek otomasyon merkezi</h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">
              Web, mobile, API, LLM ve regresyon koşumlarını aynı run sözleşmesiyle başlatır ve izler.
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={() => void loadBrain()} disabled={brainLoading}>
            {brainLoading ? "Yükleniyor…" : "Yenile"}
          </Button>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-5">
          {capabilities.map((cap) => (
            <button
              key={cap.kind}
              type="button"
              onClick={() => void startBrainRun(cap.kind)}
              disabled={startingKind !== null}
              className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-left transition hover:border-violet-400/40 hover:bg-violet-500/5 disabled:cursor-not-allowed disabled:opacity-60"
              data-testid={`automation-brain-start-${cap.kind}`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-white">{cap.label}</p>
                <span className="rounded border border-slate-700 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">
                  {cap.provenance}
                </span>
              </div>
              <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-400">{cap.description}</p>
              <p className="mt-3 text-xs font-semibold text-violet-200">
                {startingKind === cap.kind
                  ? "Başlatılıyor…"
                  : cap.kind === "web" && selected?.path
                    ? "Seçili feature ile çalıştır"
                    : cap.kind === "mobile"
                      ? "2 cihazla çalıştır"
                      : cap.kind === "regression"
                        ? "AI öneri üret"
                    : "Run oluştur"}
              </p>
            </button>
          ))}
          {!brainLoading && capabilities.length === 0 && (
            <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-sm text-slate-400 md:col-span-5">
              Automation Brain API şu an yanıt vermiyor.
            </div>
          )}
        </div>

        <div className="mt-4 overflow-hidden rounded-lg border border-slate-800">
          <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/50 px-3 py-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Son merkezi koşumlar</span>
            <span className="text-xs text-slate-500">{brainRuns.length} kayıt</span>
          </div>
          {brainRuns.length === 0 ? (
            <div className="px-3 py-4 text-sm text-slate-400">
              Henüz merkezi run yok. Yukarıdan bir otomasyon tipi seçerek ilk kaydı oluştur.
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {brainRuns.map((run) => (
                <div key={run.id} className="flex flex-wrap items-center gap-3 px-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-medium text-white">{run.name}</p>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">{run.kind}</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">{run.status}</span>
                      {run.metrics?.external_run_id || run.metrics?.external_session_ids || run.metrics?.suggested_set_count ? (
                        <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] uppercase text-emerald-300">real</span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 truncate font-mono text-[11px] text-slate-500">
                      {run.id}{run.metrics?.external_run_id ? ` · suite:${String(run.metrics.external_run_id)}` : ""}{run.metrics?.external_session_ids ? ` · mobile:${Array.isArray(run.metrics.external_session_ids) ? run.metrics.external_session_ids.length : 1}` : ""}{run.metrics?.suggested_set_count ? ` · öneri:${String(run.metrics.suggested_set_count)}` : ""}{run.target ? ` · ${run.target}` : ""}
                    </p>
                  </div>
                  {run.next_action?.href && (
                    <button
                      type="button"
                      onClick={() => router.push(run.next_action?.href ?? `/p/${projectId}/automation`)}
                      className="rounded border border-slate-700 px-2.5 py-1 text-xs text-slate-300 hover:border-slate-500 hover:text-white"
                    >
                      Aç
                    </button>
                  )}
                  {run.status !== "cancelled" && run.status !== "passed" && run.status !== "failed" && (
                    <button
                      type="button"
                      onClick={() => void cancelBrainRun(run.id)}
                      className="rounded border border-red-500/30 px-2.5 py-1 text-xs text-red-300 hover:bg-red-500/10"
                    >
                      İptal
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Body: two-column layout */}
      {loading ? (
        <div
          className="py-16 text-center text-sm text-slate-400"
          data-testid="automation-loading"
        >
          Yükleniyor…
        </div>
      ) : features.length === 0 ? (
        <div className="grid gap-4 lg:grid-cols-3">
          {/* Sol: Boş state + ana CTA */}
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-8 text-center lg:col-span-2" data-testid="automation-empty">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-violet-400/30 bg-violet-500/10 text-3xl">📄</div>
            <h2 className="text-xl font-semibold text-white">Henüz feature dosyası yok</h2>
            <p className="mt-2 text-sm text-slate-400">
              Gherkin formatında (Given/When/Then) test senaryoları yaz, Playwright otomatik koşturur.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
              <Button
                type="button"
                onClick={() => setShowCreate(true)}
                data-testid="automation-btn-empty-new"
              >
                + Boş Feature Oluştur
              </Button>
              <Link href={`/p/${projectId}/scenarios/generate`}>
                <Button type="button" variant="secondary">
                  ✨ AI'a Yazdır
                </Button>
              </Link>
            </div>
            <div className="mt-6 rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-left">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 mb-2">📝 Örnek Gherkin</p>
              <pre className="text-xs font-mono text-slate-300 leading-5 overflow-x-auto">
{`Feature: Kullanıcı Girişi
  Scenario: Başarılı login
    Given kullanıcı login sayfasındadır
    When e-posta ve şifre girer
    And "Giriş Yap" butonuna tıklar
    Then anasayfaya yönlendirilir`}
              </pre>
            </div>
          </div>

          {/* Sağ: 3 hızlı şablon + ipuçları */}
          <div className="space-y-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-300/80">Hızlı Şablonlar</p>
              <div className="mt-3 space-y-2">
                <button
                  type="button"
                  onClick={() => { setTemplateSeed({ name: "login.feature", content: `Feature: Kullanıcı Girişi\n\n  Scenario: Başarılı login\n    Given kullanıcı login sayfasındadır\n    When e-posta ve şifre girer\n    And "Giriş Yap" butonuna tıklar\n    Then anasayfaya yönlendirilir` }); setShowCreate(true); }}
                  className="block w-full rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-left transition hover:border-violet-400/40 hover:bg-violet-500/5"
                >
                  <p className="text-sm font-semibold text-white">🔐 Login Akışı</p>
                  <p className="mt-1 text-xs text-slate-400">Kimlik doğrulama senaryosu</p>
                </button>
                <button
                  type="button"
                  onClick={() => { setTemplateSeed({ name: "checkout.feature", content: `Feature: Sepete Ekleme ve Ödeme\n\n  Scenario: Ürün satın alma\n    Given kullanıcı ürün listesindedir\n    When ürün sepete eklenir\n    And ödeme bilgileri girilir\n    Then sipariş tamamlanır` }); setShowCreate(true); }}
                  className="block w-full rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-left transition hover:border-violet-400/40 hover:bg-violet-500/5"
                >
                  <p className="text-sm font-semibold text-white">🛒 E-Ticaret Checkout</p>
                  <p className="mt-1 text-xs text-slate-400">Sepet + ödeme akışı</p>
                </button>
                <button
                  type="button"
                  onClick={() => { setTemplateSeed({ name: "search.feature", content: `Feature: Arama ve Filtreleme\n\n  Scenario: Ürün arama\n    Given kullanıcı ana sayfadadır\n    When arama kutusuna "laptop" yazar\n    And aramayı başlatır\n    Then sonuçlar listelenir` }); setShowCreate(true); }}
                  className="block w-full rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-left transition hover:border-violet-400/40 hover:bg-violet-500/5"
                >
                  <p className="text-sm font-semibold text-white">🔍 Arama / Filtre</p>
                  <p className="mt-1 text-xs text-slate-400">Arama akışı</p>
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-blue-400/20 bg-blue-500/5 p-4 text-xs text-blue-100/90">
              <p className="font-semibold">💡 İpucu</p>
              <p className="mt-1 leading-5 text-blue-100/70">
                Senaryoların ortak adımlarını <Link href={`/p/${projectId.toString()}/scenarios`} className="underline">Senaryolar</Link> sayfasında yönet, otomasyona dönüştür.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
          {/* Left panel: file list */}
          <aside
            className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden"
            data-testid="automation-file-list"
          >
            <div className="border-b border-slate-800 px-3 py-2.5">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                Feature Dosyaları ({features.length})
              </span>
            </div>
            <ul className="divide-y divide-border">
              {features.map((feature) => {
                const isActive = selected?.path === feature.path;
                return (
                  <li key={feature.path}>
                    <div
                      className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer transition-colors ${
                        isActive
                          ? "bg-blue-500/10 text-white"
                          : "hover:bg-black/[0.03] dark:hover:bg-white/[0.05] text-white"
                      }`}
                      onClick={() => loadDetail(feature)}
                      data-testid={`automation-file-item-${feature.path.replaceAll("/", "_")}`}
                    >
                      <svg
                        className="h-4 w-4 shrink-0 text-slate-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{feature.name}</p>
                        {feature.updated_at && (
                          <p className="text-xs text-slate-400">{feature.updated_at}</p>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(feature.path);
                        }}
                        disabled={deleting === feature.path}
                        className="shrink-0 rounded p-1 text-slate-400 opacity-0 group-hover:opacity-100 hover:text-red-600 disabled:opacity-50 transition-opacity"
                        aria-label={`${feature.name} sil`}
                        data-testid={`automation-delete-${feature.path.replaceAll("/", "_")}`}
                      >
                        {deleting === feature.path ? (
                          <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                        ) : (
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </aside>

          {/* Right panel: content viewer */}
          <div
            className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden"
            data-testid="automation-content-panel"
          >
            {selected ? (
              <>
                <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <svg
                      className="h-4 w-4 text-slate-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <span
                      className="text-sm font-medium"
                      data-testid="automation-selected-name"
                    >
                      {selected.name}
                    </span>
                    {selected.path && (
                      <span className="text-xs text-slate-400 font-mono">{selected.path}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {selected.updated_at && !editMode && (
                      <span className="text-xs text-slate-400">
                        Son güncelleme: {selected.updated_at}
                      </span>
                    )}
                    {!editMode ? (
                      <>
                        <button
                          type="button"
                          onClick={handleRunSelected}
                          className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-200 hover:border-emerald-400/50 hover:bg-emerald-500/20 transition-colors"
                          data-testid="automation-btn-run-selected"
                          title="Seçili feature için yeni bir koşum başlat"
                        >
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          Çalıştır
                        </button>
                        <button
                          type="button"
                          onClick={() => { setEditContent(selected.content ?? ""); setEditMode(true); setSaveErr(null); }}
                          className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
                          data-testid="automation-btn-edit"
                        >
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                          Düzenle
                        </button>
                      </>
                    ) : (
                      <div className="flex items-center gap-2">
                        {saveErr && <span className="text-xs text-red-400">{saveErr}</span>}
                        <button
                          type="button"
                          onClick={() => { setEditMode(false); setSaveErr(null); }}
                          disabled={saving}
                          className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                        >
                          İptal
                        </button>
                        <button
                          type="button"
                          onClick={handleSaveEdit}
                          disabled={saving}
                          className="rounded-lg bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50"
                          data-testid="automation-btn-save-edit"
                        >
                          {saving ? "Kaydediliyor…" : "Kaydet"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                <div className="overflow-auto p-4" data-testid="automation-content-viewer">
                  {editMode ? (
                    <textarea
                      value={editContent}
                      onChange={e => setEditContent(e.target.value)}
                      className="w-full font-mono text-xs text-white bg-slate-950 border border-slate-700 rounded-lg p-3 focus:outline-none focus:border-blue-500 resize-none leading-relaxed"
                      style={{ minHeight: 400 }}
                      data-testid="automation-textarea-edit"
                      autoFocus
                    />
                  ) : (
                    <pre className="font-mono text-xs text-white leading-relaxed whitespace-pre-wrap break-words">
                      {selected.content || (
                        <span className="text-slate-400 italic">İçerik yok.</span>
                      )}
                    </pre>
                  )}
                </div>
              </>
            ) : (
              <div
                className="flex h-64 items-center justify-center"
                data-testid="automation-no-selection"
              >
                <p className="text-sm text-slate-400">Görüntülemek için bir dosya seçin.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <CreateFeatureModal
          onClose={() => { setShowCreate(false); setTemplateSeed(undefined); }}
          onCreated={load}
          initial={templateSeed}
        />
      )}
    </div>
  );
}
