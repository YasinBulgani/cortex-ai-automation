"use client";

import { useRouter } from "next/navigation";
import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

type FormErrors = { title?: boolean };

import { useCreateManagementCase, useManagementRepository, useManagementProjectTags } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { SharedStepPicker } from "../../_components/SharedStepPicker";
import { Button } from "@/components/ui/button";

function SortableStepCard({ id, children }: { id: string; children: React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <div className="flex items-start gap-2">
        <button {...listeners} className="mt-2 cursor-grab text-fg-subtle hover:text-fg p-1" title="Sürükle" aria-label="Adımı sürükle" type="button">
          <span aria-hidden="true">⠿</span>
        </button>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}


type DraftStep = {
  id: string;
  action: string;
  expected_result: string;
  test_data: string;
  notes: string;
  is_required: boolean;
};

export default function NewManagementCasePage({ params }: { params: { projectId: string } }) {
  const router = useRouter();
  const createCase = useCreateManagementCase(params.projectId);
  const mpid = useManagementProjectId(params.projectId || undefined);
  const repository = useManagementRepository(mpid || undefined);

  const { data: membersRaw } = useQuery({
    queryKey: ["management", "members", params.projectId],
    queryFn: () =>
      apiFetch<Array<{ user_id: string; email: string; full_name?: string }>>(
        `/api/v1/organizations/projects/${params.projectId}/members`
      ).then(d => (Array.isArray(d) ? d : [])),
    enabled: !!params.projectId,
    staleTime: 5 * 60 * 1000,
  });
  const members = useMemo(() => membersRaw ?? [], [membersRaw]);
  const { data: existingTags = [] } = useManagementProjectTags(mpid || undefined);

  const [showStepPicker, setShowStepPicker] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [title, setTitle] = useState("");
  const [suiteId, setSuiteId] = useState("");
  const [folderId, setFolderId] = useState("");
  const [priority, setPriority] = useState("P2");
  const [severity, setSeverity] = useState("major");
  const [type, setType] = useState("functional");
  const [automationStatus, setAutomationStatus] = useState("manual");
  const [status, setStatus] = useState("draft");
  const [objective, setObjective] = useState("");
  const [preconditions, setPreconditions] = useState("");
  const [testData, setTestData] = useState("");
  const [component, setComponent] = useState("");
  const [platform, setPlatform] = useState("");
  const [riskArea, setRiskArea] = useState("");
  const [tags, setTags] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [steps, setSteps] = useState<DraftStep[]>([
    { id: crypto.randomUUID(), action: "", expected_result: "", test_data: "", notes: "", is_required: true },
  ]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      setSteps(prev => {
        const oldIdx = prev.findIndex(s => s.id === active.id);
        const newIdx = prev.findIndex(s => s.id === over!.id);
        return arrayMove(prev, oldIdx, newIdx).map((s, i) => ({ ...s, step_no: i + 1 }));
      });
    }
  };
  const [formError, setFormError] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});

  const addStep = () => {
    setSteps((current) => [...current, { id: crypto.randomUUID(), action: "", expected_result: "", test_data: "", notes: "", is_required: true }]);
  };

  const insertSharedSteps = (sharedItems: import("@/lib/hooks/use-management").SharedStepItem[]) => {
    const newSteps: DraftStep[] = sharedItems.map(s => ({
      id: crypto.randomUUID(),
      action: s.action,
      expected_result: s.expected_result ?? "",
      test_data: "",
      notes: s.notes ?? "",
      is_required: s.is_required,
    }));
    setSteps(curr => [...curr.filter(s => s.action || s.expected_result), ...newSteps]);
  };

  const updateStep = (index: number, patch: Partial<DraftStep>) => {
    setSteps((current) =>
      current.map((step, stepIndex) => stepIndex === index ? { ...step, ...patch } : step),
    );
  };

  const removeStep = (index: number) => {
    setSteps((current) => current.filter((_, stepIndex) => stepIndex !== index));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError("");
    setErrors({});
    const cleanSteps = steps
      .map((step, index) => ({
        step_no: index + 1,
        action: step.action.trim(),
        expected_result: step.expected_result.trim(),
        test_data: step.test_data.trim() ? { value: step.test_data.trim() } : {},
        notes: step.notes.trim() || null,
        is_required: step.is_required,
      }))
      .filter((step) => step.action && step.expected_result);

    if (!title || title.trim().length === 0) {
      setErrors({ title: true });
      setFormError("Başlık boş bırakılamaz");
      return;
    }
    if (title.trim().length > 500) {
      setErrors({ title: true });
      setFormError("Başlık en fazla 500 karakter olabilir");
      return;
    }
    if (cleanSteps.length === 0) {
      setFormError("En az bir action + expected result adımı girilmeli.");
      return;
    }

    try {
      const created = await createCase.mutateAsync({
        title: title.trim(),
        suite_id: suiteId || null,
        folder_id: folderId || null,
        priority,
        severity,
        type,
        automation_status: automationStatus,
        objective: objective.trim(),
        preconditions: preconditions.trim(),
        test_data: testData.trim() ? { value: testData.trim() } : {},
        status,
        owner_id: ownerId || null,
        tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
        custom_fields: {
          component: component.trim(),
          platform: platform.trim(),
          risk_area: riskArea.trim(),
        },
        steps: cleanSteps,
      });
      router.push(`/p/${params.projectId}/management/cases/${created.id}`);
    } catch {
      setFormError("Kaydetme başarısız. Lütfen tekrar deneyin.");
    }
  };

  const TEMPLATES = [
    {
      label: "Login",
      icon: "🔐",
      title: "Login — Geçerli Kimlik Bilgileriyle Oturum Açma",
      type: "functional",
      priority: "P1",
      objective: "Kullanıcının geçerli e-posta ve şifresiyle başarıyla oturum açabildiğini doğrula.",
      preconditions: "Kullanıcı hesabı aktif ve onaylanmış olmalı. Uygulama login sayfasında olunmalı.",
      steps: [
        { action: "Geçerli bir e-posta adresi gir", expected_result: "E-posta alanı dolduruldu" },
        { action: "Geçerli şifreyi gir", expected_result: "Şifre alanı dolduruldu" },
        { action: "Giriş Yap butonuna tıkla", expected_result: "Dashboard sayfasına yönlendirildi, kullanıcı adı gösterildi" },
      ],
    },
    {
      label: "CRUD",
      icon: "✏️",
      title: "CRUD — [Varlık] Oluştur, Oku, Güncelle, Sil",
      type: "functional",
      priority: "P2",
      objective: "Temel CRUD operasyonlarının doğru çalıştığını doğrula.",
      preconditions: "Kullanıcı oturum açmış olmalı ve ilgili modüle erişim yetkisi bulunmalı.",
      steps: [
        { action: "Yeni varlık oluşturma formunu aç", expected_result: "Form boş olarak açıldı" },
        { action: "Zorunlu alanları doldur ve Kaydet butonuna tıkla", expected_result: "Varlık başarıyla oluşturuldu, listede görünüyor" },
        { action: "Oluşturulan varlığı seç ve düzenleme moduna geç", expected_result: "Düzenleme formu eski değerlerle açıldı" },
        { action: "Bir alanı değiştir ve kaydet", expected_result: "Değişiklik kaydedildi, listede güncellendi" },
        { action: "Varlığı sil (onay gerekiyorsa onayla)", expected_result: "Varlık listeden kaldırıldı" },
      ],
    },
    {
      label: "Dosya Yükleme",
      icon: "📎",
      title: "Dosya Yükleme — Desteklenen Format",
      type: "functional",
      priority: "P2",
      objective: "Desteklenen formattaki dosyaların başarıyla yüklenebildiğini doğrula.",
      preconditions: "Kullanıcı oturum açmış ve dosya yükleme sayfasında olmalı.",
      steps: [
        { action: "Dosya seç butonuna tıkla", expected_result: "Dosya tarayıcısı açıldı" },
        { action: "Desteklenen formatta (ör. PDF, JPG) bir dosya seç", expected_result: "Dosya adı önizleme alanında gösteriliyor" },
        { action: "Yükle butonuna tıkla", expected_result: "Yükleme çubuğu gösterildi, başarı mesajı gösterildi" },
        { action: "Yüklenen dosyanın listede göründüğünü kontrol et", expected_result: "Dosya listede doğru ad ve boyutla görünüyor" },
      ],
    },
    {
      label: "UI Navigasyon",
      icon: "🧭",
      title: "UI Navigasyon — Menü ve Sayfa Geçişleri",
      type: "ui",
      priority: "P3",
      objective: "Tüm menü öğelerinin doğru sayfalara yönlendirdiğini doğrula.",
      preconditions: "Kullanıcı oturum açmış olmalı ve ana sayfada bulunmalı.",
      steps: [
        { action: "Üst menüdeki her bir öğeye tıkla", expected_result: "İlgili sayfaya yönlendirildi, URL doğru" },
        { action: "Tarayıcı geri butonuna tıkla", expected_result: "Önceki sayfaya dönüldü" },
        { action: "Breadcrumb linklerine tıkla", expected_result: "İlgili üst sayfaya yönlendirildi" },
      ],
    },
    {
      label: "Hata Mesajı",
      icon: "⚠️",
      title: "Hata Yönetimi — Geçersiz Giriş Doğrulaması",
      type: "negative",
      priority: "P2",
      objective: "Geçersiz giriş durumlarında anlamlı hata mesajlarının gösterildiğini doğrula.",
      preconditions: "Form/giriş sayfası açık olmalı.",
      steps: [
        { action: "Zorunlu alanları boş bırak ve formu gönder", expected_result: "Her zorunlu alan için hata mesajı gösterildi" },
        { action: "Geçersiz format gir (ör. e-posta yerine metin)", expected_result: "Format hatası mesajı gösterildi" },
        { action: "Maksimum izin verilen uzunluğu aşan değer gir", expected_result: "Uzunluk hatası mesajı gösterildi" },
        { action: "Hata mesajı görünürken formu düzelt ve yeniden gönder", expected_result: "Hata mesajları kayboldu, form başarıyla gönderildi" },
      ],
    },
  ];

  function applyTemplate(tpl: typeof TEMPLATES[0]) {
    setTitle(tpl.title);
    setType(tpl.type);
    setPriority(tpl.priority);
    setObjective(tpl.objective);
    setPreconditions(tpl.preconditions);
    setSteps(tpl.steps.map(s => ({
      id: crypto.randomUUID(),
      action: s.action,
      expected_result: s.expected_result,
      test_data: "",
      notes: "",
      is_required: true,
    })));
    setShowTemplates(false);
  }

  return (
    <div className="min-h-full bg-surface-base px-5 py-5 space-y-5">
      {/* Template picker */}
      <div className="rounded-xl border border-border bg-surface-raised px-4 py-3">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-semibold text-fg">Şablondan Başla</p>
          <button
            type="button"
            onClick={() => setShowTemplates(v => !v)}
            className="text-[11px] text-brand hover:underline"
          >
            {showTemplates ? "Gizle" : "Şablonları Göster"}
          </button>
        </div>
        {showTemplates && (
          <div className="mt-3 flex flex-wrap gap-2">
            {TEMPLATES.map(tpl => (
              <button
                key={tpl.label}
                type="button"
                onClick={() => applyTemplate(tpl)}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg-muted hover:border-brand/40 hover:text-fg transition-colors"
              >
                <span>{tpl.icon}</span>
                <span>{tpl.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <section className="rounded-xl border border-border bg-surface-raised p-5">
        <form onSubmit={submit} className="space-y-5">
          {formError ? (
            <div role="alert" id="form-error-msg" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {formError}
            </div>
          ) : null}
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1" htmlFor="case-title">
              <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                Title<span className="text-red-400 ml-0.5" aria-hidden="true">*</span>
              </span>
              <input
                id="case-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={500}
                required
                aria-required="true"
                aria-describedby={errors.title ? "title-error" : formError ? "form-error-msg" : undefined}
                aria-invalid={errors.title ? "true" : undefined}
                className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
                placeholder="Login valid credentials"
              />
              <div className="flex items-center justify-between mt-1">
                {errors.title ? <p id="title-error" role="alert" className="text-[12px] text-red-400">Başlık zorunludur.</p> : <span />}
                <span className={`text-xs ${title.length >= 480 ? "text-amber-400" : "text-fg-subtle"}`} aria-live="polite">{title.length}/500</span>
              </div>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Suite</span>
                <select
                  value={suiteId}
                  onChange={(event) => {
                    setSuiteId(event.target.value);
                    setFolderId("");
                  }}
                  className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
                >
                  <option value="">Suite seç</option>
                  {(repository.data?.suites ?? []).map((suite) => <option key={suite.id} value={suite.id}>{suite.name}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Folder</span>
                <select
                  value={folderId}
                  onChange={(event) => setFolderId(event.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
                >
                  <option value="">Folder seç</option>
                  {(repository.data?.folders ?? []).filter((folder) => !suiteId || folder.suite_id === suiteId).map((folder) => <option key={folder.id} value={folder.id}>{folder.path}</option>)}
                </select>
              </label>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Priority</span>
                <select
                  value={priority}
                  onChange={(event) => setPriority(event.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
                >
                  {["P0", "P1", "P2", "P3"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Severity</span>
                <select
                  value={severity}
                  onChange={(event) => setSeverity(event.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
                >
                  {["blocker", "critical", "major", "minor"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Type</span>
                <select
                  value={type}
                  onChange={(event) => setType(event.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
                >
                  {["functional", "smoke", "regression", "uat", "exploratory"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Status</span>
                <select
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
                >
                  {["draft", "review", "active"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
          </div>
          <div className="grid gap-4 md:grid-cols-5">
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Sahip</span>
              <select value={ownerId} onChange={(event) => setOwnerId(event.target.value)} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none">
                <option value="">— Atanmamış —</option>
                {members.map(m => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.full_name?.trim() || m.email}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Automation</span>
              <select value={automationStatus} onChange={(event) => setAutomationStatus(event.target.value)} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none">
                {["manual", "candidate", "automated", "deprecated"].map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Component</span>
              <input value={component} onChange={(event) => setComponent(event.target.value)} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none" placeholder="Auth" />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Platform</span>
              <input value={platform} onChange={(event) => setPlatform(event.target.value)} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none" placeholder="Web / iOS / Android" />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Risk Area</span>
              <input value={riskArea} onChange={(event) => setRiskArea(event.target.value)} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none" placeholder="Payment, Session" />
            </label>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Objective</span>
              <textarea
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
                maxLength={2000}
                rows={3}
                className="w-full resize-none rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
              />
              <span className={`text-xs ${objective.length >= 1900 ? "text-amber-400" : "text-fg-subtle"}`}>{objective.length}/2000</span>
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Preconditions</span>
              <textarea
                value={preconditions}
                onChange={(event) => setPreconditions(event.target.value)}
                maxLength={2000}
                rows={3}
                className="w-full resize-none rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
              />
              <span className={`text-xs ${preconditions.length >= 1900 ? "text-amber-400" : "text-fg-subtle"}`}>{preconditions.length}/2000</span>
            </label>
          </div>
          <label className="block space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Test Data</span>
            <textarea
              value={testData}
              onChange={(event) => setTestData(event.target.value)}
              maxLength={2000}
              rows={3}
              className="w-full resize-none rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
              placeholder="Kullanıcı, rol, veri seti, fixture veya özel inputlar"
            />
            <span className={`text-xs ${testData.length >= 1900 ? "text-amber-400" : "text-fg-subtle"}`}>{testData.length}/2000</span>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Tags</span>
            {existingTags.length > 0 && (
              <datalist id="case-tags-list">
                {existingTags.map(tag => <option key={tag} value={tag} />)}
              </datalist>
            )}
            <input
              list={existingTags.length > 0 ? "case-tags-list" : undefined}
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none"
              placeholder="login, smoke, auth"
            />
          </label>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-fg">Steps</h2>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowStepPicker(true)}
                  className="border-brand/30 text-brand hover:bg-brand-soft"
                >
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                  </svg>
                  Şablondan Ekle
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addStep}
                >
                  Adım Ekle
                </Button>
              </div>
            </div>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
                {steps.map((step, index) => (
                  <SortableStepCard key={step.id} id={step.id}>
                    <div className="grid gap-3 rounded-lg border border-border bg-surface-overlay p-3 md:grid-cols-[2rem_1fr_1fr_auto]">
                      <div className="pt-2 text-center font-mono text-xs text-fg-subtle">{index + 1}</div>
                      <div className="space-y-2">
                        <textarea value={step.action} onChange={(event) => updateStep(index, { action: event.target.value })} rows={2} aria-label={`Adım ${index + 1} — action`} className="w-full resize-none rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none" placeholder="Action" />
                        <input value={step.test_data} onChange={(event) => updateStep(index, { test_data: event.target.value })} aria-label={`Adım ${index + 1} — test data`} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-xs text-fg focus:border-teal-500/50 focus:outline-none" placeholder="Step test data" />
                      </div>
                      <div className="space-y-2">
                        <textarea value={step.expected_result} onChange={(event) => updateStep(index, { expected_result: event.target.value })} rows={2} aria-label={`Adım ${index + 1} — expected result`} className="w-full resize-none rounded-lg border border-border bg-surface-overlay px-3 py-2 text-sm text-fg focus:border-teal-500/50 focus:outline-none" placeholder="Expected result / validation" />
                        <input value={step.notes} onChange={(event) => updateStep(index, { notes: event.target.value })} aria-label={`Adım ${index + 1} — notlar`} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-xs text-fg focus:border-teal-500/50 focus:outline-none" placeholder="Notes" />
                      </div>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-xs text-fg-muted">
                          <input type="checkbox" checked={step.is_required} onChange={(event) => updateStep(index, { is_required: event.target.checked })} aria-label={`Adım ${index + 1} zorunlu mu`} />
                          Required
                        </label>
                        <Button
                          type="button"
                          variant="ghost-danger"
                          size="sm"
                          onClick={() => removeStep(index)}
                        >
                          Remove
                        </Button>
                      </div>
                    </div>
                  </SortableStepCard>
                ))}
              </SortableContext>
            </DndContext>
          </div>
          <div className="sticky bottom-0 z-10 border-t border-border bg-surface-base px-6 py-3 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
            >
              İptal
            </Button>
            <Button
              type="submit"
              disabled={!title.trim() || createCase.isPending}
            >
              {createCase.isPending ? "Kaydediliyor..." : "Kaydet"}
            </Button>
          </div>
        </form>
      </section>

      {showStepPicker && mpid && (
        <SharedStepPicker
          projectId={mpid}
          onInsert={insertSharedSteps}
          onClose={() => setShowStepPicker(false)}
        />
      )}
    </div>
  );
}
