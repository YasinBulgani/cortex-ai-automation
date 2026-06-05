"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useCreateManagementCase, useManagementRepository } from "@/lib/hooks/use-management";
import { useToast } from "@/lib/useToast";
import {
  GherkinEditor,
  parseGherkinToSteps,
  parseGherkinScenarios,
  type GherkinStep,
} from "../_components/GherkinEditor";

// ── Template library ──────────────────────────────────────────────────────────

interface GherkinTemplate {
  label: string;
  description: string;
  content: string;
}

const TEMPLATES: GherkinTemplate[] = [
  {
    label: "Giriş Şablonu",
    description: "Kullanıcı giriş / çıkış akışı",
    content: `Feature: Kullanıcı Girişi

  Scenario: Başarılı giriş
    Given kullanıcı giriş sayfasında
    When geçerli email ve şifre girer
    Then dashboard'a yönlendirilmeli

  Scenario: Hatalı şifre
    Given kullanıcı giriş sayfasında
    When geçersiz şifre girer
    Then hata mesajı gösterilmeli
`,
  },
  {
    label: "CRUD Şablonu",
    description: "Oluştur / Oku / Güncelle / Sil",
    content: `Feature: Kayıt Yönetimi

  Scenario: Yeni kayıt oluştur
    Given kullanıcı form sayfasında
    When gerekli alanları doldurur ve kaydeder
    Then kayıt listesinde görünmeli

  Scenario: Kayıt güncelle
    Given mevcut bir kayıt var
    When kullanıcı düzenler ve kaydeder
    Then güncel veri gösterilmeli

  Scenario: Kayıt sil
    Given mevcut bir kayıt var
    When kullanıcı sil butonuna tıklar
    Then kayıt listeden kaldırılmalı
`,
  },
  {
    label: "Hata Durumu Şablonu",
    description: "Validasyon ve hata senaryoları",
    content: `Feature: Form Validasyonu

  Scenario: Zorunlu alan boş
    Given kullanıcı form sayfasında
    When zorunlu alanı boş bırakır
    And formu gönderir
    Then validasyon hatası gösterilmeli

  Scenario: Geçersiz format
    Given kullanıcı email alanına odaklanmış
    When geçersiz formatta email girer
    Then format hata mesajı görünmeli

  Scenario: Ağ hatası
    Given sunucu yanıt vermiyor
    When kullanıcı formu gönderir
    Then kullanıcı dostu hata mesajı gösterilmeli
`,
  },
];

// ── Initial gherkin ───────────────────────────────────────────────────────────

const INITIAL_GHERKIN = `Feature: Yeni özellik

  Scenario: Başarılı senaryo
    Given kullanıcı giriş yapmış
    When işlemi gerçekleştiriyor
    Then sonuç doğrulanmalı
`;

// ── Page ──────────────────────────────────────────────────────────────────────

export default function GherkinPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid = useManagementProjectId(projectId || undefined);
  const createCase = useCreateManagementCase(mpid || "");
  const repoQ = useManagementRepository(mpid || undefined);
  const toast = useToast();

  const suites = useMemo(() => repoQ.data?.suites ?? [], [repoQ.data]);

  const [featureName, setFeatureName] = useState("");
  const [selectedSuiteId, setSelectedSuiteId] = useState("");
  const [tags, setTags] = useState("");
  const [gherkin, setGherkin] = useState(INITIAL_GHERKIN);
  const [saving, setSaving] = useState(false);
  const [saveProgress, setSaveProgress] = useState<{ done: number; total: number } | null>(null);

  // Live parsed scenarios for multi-scenario support
  const liveScenarios = useMemo(() => parseGherkinScenarios(gherkin), [gherkin]);
  const liveSteps = useMemo(() => parseGherkinToSteps(gherkin), [gherkin]);

  const parsedTags = useMemo(
    () => tags.split(",").map(t => t.trim()).filter(Boolean),
    [tags],
  );

  // Append a template to the current editor content
  function applyTemplate(tpl: GherkinTemplate) {
    // If editor is at initial state, replace. Otherwise append.
    if (gherkin.trim() === INITIAL_GHERKIN.trim()) {
      setGherkin(tpl.content);
    } else {
      setGherkin(prev => prev.trimEnd() + "\n\n" + tpl.content);
    }
  }

  // Save all scenarios as separate cases
  async function handleSaveAll() {
    if (!mpid) {
      toast.error("Proje bulunamadı");
      return;
    }
    const scenarios = liveScenarios.filter(s => s.steps.length > 0);
    if (scenarios.length === 0) {
      toast.error("Kaydedilecek senaryo bulunamadı.");
      return;
    }

    setSaving(true);
    setSaveProgress({ done: 0, total: scenarios.length });

    let successCount = 0;
    try {
      for (let i = 0; i < scenarios.length; i++) {
        const s = scenarios[i];
        const title = scenarios.length === 1
          ? (featureName.trim() || s.name || "BDD/Gherkin Test Case")
          : (featureName.trim() ? `${featureName.trim()} — ${s.name}` : s.name);

        await createCase.mutateAsync({
          title,
          type: "functional",
          status: "draft",
          priority: "P2",
          source_type: "gherkin",
          suite_id: selectedSuiteId || null,
          tags: parsedTags.length > 0 ? parsedTags : undefined,
          custom_fields: { gherkin_source: gherkin, scenario_name: s.name },
          steps: s.steps.map(st => ({
            step_no: st.step_no,
            action: st.action,
            expected_result: st.expected_result,
            notes: null,
            is_required: st.is_required ?? true,
          })),
        });
        successCount++;
        setSaveProgress({ done: i + 1, total: scenarios.length });
      }

      if (scenarios.length === 1) {
        toast.success("Test case olarak kaydedildi");
      } else {
        toast.success(`${successCount} test case oluşturuldu`);
      }
      setFeatureName("");
      setTags("");
      setSelectedSuiteId("");
      setGherkin(INITIAL_GHERKIN);
    } catch {
      toast.error("Kayıt sırasında hata oluştu");
    } finally {
      setSaving(false);
      setSaveProgress(null);
    }
  }

  const multiScenario = liveScenarios.length > 1;
  const totalStepCount = liveScenarios.reduce((n, s) => n + s.steps.length, 0);

  return (
    <div className="min-h-full bg-surface-base px-6 py-6">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Test Tasarımı</p>
          <h1 className="mt-1 text-[20px] font-semibold text-fg">BDD / Gherkin Editörü</h1>
          <p className="mt-1 text-[12px] text-fg-muted">
            Gherkin sözdizimi ile senaryo yazın, test adımlarına dönüştürün ve kaydedin.
          </p>
        </div>
      </div>

      {/* Feature name + suite + tags row */}
      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {/* Feature name */}
        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
            Feature / Test Case Adı
          </label>
          <input
            value={featureName}
            onChange={e => setFeatureName(e.target.value)}
            placeholder="örn. Kullanıcı girişi doğrulaması"
            className="w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
          />
        </div>

        {/* Suite selector */}
        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
            Suite / Klasör <span className="font-normal normal-case text-fg-disabled">(opsiyonel)</span>
          </label>
          <select
            value={selectedSuiteId}
            onChange={e => setSelectedSuiteId(e.target.value)}
            className="w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/15 cursor-pointer"
          >
            <option value="">— Suite seçin —</option>
            {suites.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        {/* Tags */}
        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
            Etiketler <span className="font-normal normal-case text-fg-disabled">(virgülle ayır)</span>
          </label>
          <input
            value={tags}
            onChange={e => setTags(e.target.value)}
            placeholder="örn. login, smoke, regression"
            className="w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
          />
          {parsedTags.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {parsedTags.map(tag => (
                <span
                  key={tag}
                  className="rounded-full border border-brand/25 bg-brand/10 px-1.5 py-0.5 text-[10px] font-medium text-brand"
                >
                  @{tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main layout: editor + right panel */}
      <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
        {/* Left — Editor */}
        <div className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Gherkin Editörü</p>
          <GherkinEditor
            value={gherkin}
            onChange={setGherkin}
            onConvert={steps => {
              void steps; // live preview always on
            }}
          />
          <p className="text-[10px] text-fg-subtle">
            İpucu:{" "}
            <kbd className="rounded border border-border bg-surface-overlay px-1 py-0.5 font-mono text-[9px]">Tab</kbd>{" "}
            otomatik tamamlama,{" "}
            <kbd className="rounded border border-border bg-surface-overlay px-1 py-0.5 font-mono text-[9px]">Enter</kbd>{" "}
            ile kabul edin.
          </p>
        </div>

        {/* Right panel: scenario preview + template library */}
        <div className="space-y-4">

          {/* ── Scenario preview ───────────────────────────────────────── */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
                Senaryo Önizlemesi
              </p>
              {liveScenarios.length > 0 && (
                <span className="rounded-full border border-border bg-surface-overlay px-1.5 py-0.5 text-[9px] text-fg-muted tabular-nums">
                  {liveScenarios.length} senaryo · {totalStepCount} adım
                </span>
              )}
            </div>

            <div className="max-h-[320px] overflow-y-auto rounded-xl border border-border bg-surface-raised p-3 space-y-3">
              {liveScenarios.length === 0 ? (
                <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 text-center">
                  <p className="text-[13px] text-fg-muted">Henüz senaryo bulunamadı</p>
                  <p className="text-[11px] text-fg-subtle">
                    Scenario: satırı ve adımlar yazın.
                  </p>
                </div>
              ) : (
                liveScenarios.map((scenario, si) => (
                  <div key={si} className="space-y-1.5">
                    {liveScenarios.length > 1 && (
                      <div className="flex items-center gap-2">
                        <span className="h-px flex-1 bg-border" />
                        <span className="text-[10px] font-semibold text-blue-400">{scenario.name}</span>
                        <span className="h-px flex-1 bg-border" />
                      </div>
                    )}
                    {scenario.steps.length === 0 ? (
                      <p className="text-[11px] text-fg-disabled px-1">Adım yok</p>
                    ) : (
                      scenario.steps.map(step => (
                        <div
                          key={step.step_no}
                          className="rounded-lg border border-border bg-surface-base p-2.5"
                        >
                          <div className="flex items-start gap-2">
                            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-border bg-surface-overlay text-[9px] font-bold text-fg-subtle tabular-nums">
                              {step.step_no}
                            </span>
                            <div className="min-w-0 flex-1 space-y-0.5">
                              <div className="flex items-center gap-2">
                                <span className="rounded border border-border bg-surface-overlay px-1.5 py-0.5 text-[9px] text-fg-subtle">
                                  Aksiyon
                                </span>
                                <span className="text-[11px] text-fg">{step.action}</span>
                              </div>
                              {step.expected_result && (
                                <div className="flex items-center gap-2">
                                  <span className="rounded border border-emerald-500/20 bg-emerald-500/5 px-1.5 py-0.5 text-[9px] text-emerald-400">
                                    Beklenen
                                  </span>
                                  <span className="text-[11px] text-fg-muted">{step.expected_result}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* ── Template library ───────────────────────────────────────── */}
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Şablon Kütüphanesi</p>
            <div className="space-y-1.5">
              {TEMPLATES.map(tpl => (
                <button
                  key={tpl.label}
                  type="button"
                  onClick={() => applyTemplate(tpl)}
                  className="flex w-full items-center justify-between rounded-lg border border-border bg-surface-raised px-3 py-2.5 text-left transition-colors hover:border-brand/30 hover:bg-brand/5 group"
                >
                  <div className="min-w-0">
                    <p className="text-[12px] font-semibold text-fg group-hover:text-brand">{tpl.label}</p>
                    <p className="text-[10px] text-fg-subtle">{tpl.description}</p>
                  </div>
                  <span className="ml-2 shrink-0 text-[11px] text-fg-disabled group-hover:text-brand">→</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Save area */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <p className={cn(
          "text-[11px]",
          totalStepCount === 0 ? "text-fg-disabled" : "text-fg-muted",
        )}>
          {totalStepCount === 0
            ? "Kaydedilecek adım yok"
            : multiScenario
              ? `${liveScenarios.length} senaryo tespit edildi — ${totalStepCount} toplam adım`
              : `${liveSteps.length} adım kaydedilecek`}
        </p>

        {saveProgress && (
          <span className="text-[11px] text-brand tabular-nums">
            {saveProgress.done}/{saveProgress.total} kaydediliyor…
          </span>
        )}

        <button
          type="button"
          disabled={saving || totalStepCount === 0 || !mpid}
          onClick={() => void handleSaveAll()}
          className="rounded-xl bg-brand px-5 py-2 text-[13px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105 disabled:opacity-40"
        >
          {saving
            ? "Kaydediliyor…"
            : multiScenario
              ? `${liveScenarios.length} Case Oluştur`
              : "Test Case Olarak Kaydet"}
        </button>
      </div>
    </div>
  );
}
