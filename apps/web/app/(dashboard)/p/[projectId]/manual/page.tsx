"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { useRouteParam } from "@/lib/use-route-param";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  StatusBadge,
  EmptyState,
  StatCard,
  MetricRow,
  ToolbarActions,
  FilterBar,
} from "@/components/nexus";

type Priority = "low" | "medium" | "high" | "critical";
type TestStatus = "pending" | "passed" | "failed" | "blocked";
type StepStatus = "pending" | "passed" | "failed" | "blocked";

type ManualTestStep = {
  id: string; action: string; expected: string; step_order: number; status: StepStatus;
};
type ManualTest = {
  id: string; title: string; description: string; priority: Priority;
  status: TestStatus; steps: ManualTestStep[]; created_at?: string | null;
};
type CreateTestForm = {
  title: string;
  description: string;
  priority: Priority;
  requirementKey: string;
  component: string;
  owner: string;
  tags: string;
  riskLevel: "low" | "medium" | "high";
  testType: "functional" | "regression" | "smoke" | "negative" | "exploratory";
  estimatedMinutes: string;
  preconditions: string;
  testData: string;
  automationNotes: string;
  environment: string;
};
type CreateStepForm = { action: string; expected: string };
type DraftManualStep = { id: string; action: string; expected: string };
type CoverageKey = "positive" | "negative" | "permission" | "edge" | "data" | "rollback";

const PROXY = "/api/v1/automation/proxy/api/manual-tests";
const emptyForm: CreateTestForm = {
  title: "",
  description: "",
  priority: "medium",
  requirementKey: "",
  component: "",
  owner: "",
  tags: "",
  riskLevel: "medium",
  testType: "functional",
  estimatedMinutes: "",
  preconditions: "",
  testData: "",
  automationNotes: "",
  environment: "",
};
const emptyStep: CreateStepForm = { action: "", expected: "" };

const PRIORITY_BADGE: Record<Priority, string> = {
  critical: "bg-red-500/10 border border-red-500/20 text-red-400",
  high:     "bg-orange-500/10 border border-orange-500/20 text-orange-400",
  medium:   "bg-blue-500/10 border border-blue-500/20 text-blue-400",
  low:      "bg-slate-800 border border-slate-700 text-slate-400",
};
const PRIORITY_LABELS: Record<Priority, string> = {
  critical: "Kritik", high: "Yüksek", medium: "Orta", low: "Düşük",
};

const STATUS_TOGGLE_COLORS: Record<TestStatus | StepStatus, string> = {
  pending: "text-slate-400 border-slate-700 hover:border-slate-500",
  passed:  "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
  failed:  "text-red-400 border-red-500/30 bg-red-500/5",
  blocked: "text-amber-400 border-amber-500/30 bg-amber-500/5",
};

const MANUAL_TEMPLATES: Array<{ id: string; label: string; priority: Priority; description: string; steps: Omit<DraftManualStep, "id">[] }> = [
  {
    id: "happy",
    label: "Happy Path",
    priority: "medium",
    description: "Ana kullanıcı akışının beklenen şekilde tamamlandığını doğrula.",
    steps: [
      { action: "Kullanıcı ilgili ekranı açar.", expected: "Ekran hatasız yüklenir." },
      { action: "Geçerli test verisi ile zorunlu alanları doldurur.", expected: "Form gönderime hazır hale gelir." },
      { action: "Ana aksiyonu çalıştırır.", expected: "Başarı mesajı ve beklenen sonuç gösterilir." },
    ],
  },
  {
    id: "negative",
    label: "Negatif Akış",
    priority: "high",
    description: "Geçersiz veri ve hata mesajı davranışlarını doğrula.",
    steps: [
      { action: "Kullanıcı zorunlu alanı boş bırakır.", expected: "Alan bazlı hata mesajı gösterilir." },
      { action: "Kullanıcı geçersiz formatta veri girer.", expected: "Sistem işlemi engeller." },
      { action: "Kullanıcı veriyi düzeltip tekrar dener.", expected: "İşlem başarılı şekilde tamamlanır." },
    ],
  },
  {
    id: "smoke",
    label: "Smoke",
    priority: "critical",
    description: "Release öncesi kritik fonksiyonun minimum kontrollerle çalıştığını doğrula.",
    steps: [
      { action: "Kritik modüle erişilir.", expected: "Modül erişilebilir ve hata üretmez." },
      { action: "Temel işlem çalıştırılır.", expected: "İşlem başarılı olur." },
    ],
  },
];

const REUSABLE_STEPS: Array<{ label: string; action: string; expected: string }> = [
  { label: "Login", action: "Kullanıcı geçerli bilgilerle giriş yapar.", expected: "Kullanıcı oturum açmış olarak yönlendirilir." },
  { label: "Yetki Kontrolü", action: "Kullanıcı yetkisiz bir aksiyonu dener.", expected: "Sistem işlemi engeller ve uygun uyarıyı gösterir." },
  { label: "Kaydet", action: "Kullanıcı formu kaydeder.", expected: "Kayıt başarılı olur ve liste/görüntü güncellenir." },
  { label: "Hata Mesajı", action: "Kullanıcı geçersiz veri girip işlemi gönderir.", expected: "Alan bazlı doğrulama mesajı görünür." },
  { label: "Logout", action: "Kullanıcı çıkış yapar.", expected: "Oturum sonlanır ve giriş ekranına dönülür." },
];

const COVERAGE_ITEMS: Array<{ key: CoverageKey; label: string }> = [
  { key: "positive", label: "Pozitif akış" },
  { key: "negative", label: "Negatif akış" },
  { key: "permission", label: "Yetki/rol" },
  { key: "edge", label: "Edge case" },
  { key: "data", label: "Veri doğrulama" },
  { key: "rollback", label: "Geri alma/iptal" },
];

const TEST_TYPE_LABELS: Record<CreateTestForm["testType"], string> = {
  functional: "Fonksiyonel",
  regression: "Regresyon",
  smoke: "Smoke",
  negative: "Negatif",
  exploratory: "Keşif",
};

const RISK_LABELS: Record<CreateTestForm["riskLevel"], string> = {
  low: "Düşük risk",
  medium: "Orta risk",
  high: "Yüksek risk",
};

function makeDraftStep(step?: Partial<DraftManualStep>): DraftManualStep {
  return {
    id: `draft-step-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    action: step?.action ?? "",
    expected: step?.expected ?? "",
  };
}

function DraftStepRow({
  step,
  index,
  onChange,
  onRemove,
}: {
  step: DraftManualStep;
  index: number;
  onChange: (next: DraftManualStep) => void;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.45 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="grid gap-2 rounded-lg border border-slate-700 bg-slate-900/60 p-3 lg:grid-cols-[44px_1fr_1fr_72px]">
      <button
        type="button"
        title="Adımı sürükle"
        className="flex h-10 w-10 cursor-grab items-center justify-center rounded-lg border border-slate-700 text-xs font-semibold text-slate-400 active:cursor-grabbing"
        {...attributes}
        {...listeners}
      >
        {index + 1}
      </button>
      <textarea
        value={step.action}
        onChange={(event) => onChange({ ...step, action: event.target.value })}
        placeholder="Aksiyon"
        rows={2}
        className="min-h-[70px] rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
      />
      <textarea
        value={step.expected}
        onChange={(event) => onChange({ ...step, expected: event.target.value })}
        placeholder="Beklenen sonuç"
        rows={2}
        className="min-h-[70px] rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
      />
      <button
        type="button"
        onClick={onRemove}
        className="h-10 rounded-lg border border-red-500/30 px-3 text-xs font-medium text-red-300 hover:bg-red-500/10"
      >
        Sil
      </button>
    </div>
  );
}

function getMetadataValue(description: string, label: string) {
  const line = description.split("\n").find((item) => item.toLowerCase().startsWith(`${label.toLowerCase()}:`));
  return line?.split(":").slice(1).join(":").trim() ?? "";
}

function downloadCsv(test: ManualTest) {
  const steps = (test.steps ?? []).slice().sort((a, b) => a.step_order - b.step_order);
  const rows = [
    ["Test", "Priority", "Status", "Step", "Action", "Expected", "Step Status"],
    ...steps.map((step) => [
      test.title,
      PRIORITY_LABELS[test.priority],
      test.status,
      String(step.step_order),
      step.action,
      step.expected,
      step.status,
    ]),
  ];
  const csv = rows
    .map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(","))
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${test.title.toLowerCase().replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "manual-test"}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/* ── Step Row ─────────────────────────────────────────────────────────────── */
function StepRow({ step, testId, onUpdate }: { step: ManualTestStep; testId: string; onUpdate: () => void }) {
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function changeStatus(s: StepStatus) {
    // clicking active status resets to pending
    const next: StepStatus = s === step.status ? "pending" : s;
    setUpdating(true);
    try {
      await apiFetch(`${PROXY}/${testId}/steps/${step.id}`, { method: "PUT", json: { status: next } });
      onUpdate();
    } finally { setUpdating(false); }
  }

  async function deleteStep() {
    setDeleting(true);
    try {
      await apiFetch(`${PROXY}/${testId}/steps/${step.id}`, { method: "DELETE" });
      onUpdate();
    } finally { setDeleting(false); }
  }

  return (
    <div
      className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-800 hover:border-slate-700 transition-colors"
      data-testid={`manual-step-${step.id}`}
    >
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-700 text-xs font-semibold text-slate-300">
        {step.step_order}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">{step.action}</p>
        {step.expected && <p className="text-xs text-slate-500 mt-0.5">→ {step.expected}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {(["passed", "failed", "blocked"] as StepStatus[]).map(s => (
          <button
            key={s}
            onClick={() => changeStatus(s)}
            disabled={updating || deleting}
            title={s === step.status ? "Geri al (bekliyor)" : s === "passed" ? "Geçti" : s === "failed" ? "Başarısız" : "Engellendi"}
            className={`px-2 py-0.5 text-xs rounded-lg border transition-all disabled:opacity-50 ${
              step.status === s ? STATUS_TOGGLE_COLORS[s] : "text-slate-600 border-slate-700 hover:border-slate-600 hover:text-slate-400"
            }`}
            data-testid={`manual-step-status-${step.id}`}
          >
            {s === "passed" ? "✓" : s === "failed" ? "✗" : "⊘"}
          </button>
        ))}
        <button
          onClick={deleteStep}
          disabled={deleting || updating}
          title="Adımı sil"
          className="ml-1 p-1 rounded text-slate-600 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all disabled:opacity-50"
          data-testid={`manual-step-delete-${step.id}`}
        >
          {deleting
            ? <div className="w-3 h-3 border border-slate-500 border-t-red-400 rounded-full animate-spin" />
            : <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
          }
        </button>
      </div>
    </div>
  );
}

/* ── Test Card ────────────────────────────────────────────────────────────── */
function TestCard({
  test, projectId, onDelete, onRefresh, onClone,
}: { test: ManualTest; projectId: string; onDelete: () => void; onRefresh: () => void; onClone: (test: ManualTest) => void }) {
  const [open, setOpen] = useState(false);
  const [stepForm, setStepForm] = useState<CreateStepForm>(emptyStep);
  const [addingStep, setAddingStep] = useState(false);
  const [showStepForm, setShowStepForm] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  async function handleAddStep(e: React.FormEvent) {
    e.preventDefault();
    if (!stepForm.action.trim()) return;
    setAddingStep(true);
    try {
      await apiFetch(`${PROXY}/${test.id}/steps`, {
        method: "POST",
        json: { action: stepForm.action.trim(), expected: stepForm.expected.trim(), step_order: (test.steps?.length ?? 0) + 1 },
      });
      setStepForm(emptyStep); setShowStepForm(false); onRefresh();
    } finally { setAddingStep(false); }
  }

  async function changeTestStatus(s: TestStatus) {
    if (s === test.status) return;
    setUpdatingStatus(true);
    try {
      await apiFetch(`${PROXY}/${test.id}`, { method: "PUT", json: { status: s } });
      onRefresh();
    } finally { setUpdatingStatus(false); }
  }

  const steps = (test.steps ?? []).slice().sort((a, b) => a.step_order - b.step_order);
  const passedSteps = steps.filter(s => s.status === "passed").length;
  const progress = steps.length > 0 ? Math.round((passedSteps / steps.length) * 100) : 0;
  const requirement = getMetadataValue(test.description ?? "", "Requirement");
  const owner = getMetadataValue(test.description ?? "", "Owner");
  const component = getMetadataValue(test.description ?? "", "Component");
  const risk = getMetadataValue(test.description ?? "", "Risk");

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden hover:border-slate-600 transition-colors" data-testid={`manual-test-card-${test.id}`}>
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3 p-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-white">{test.title}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_BADGE[test.priority]}`}>
              {PRIORITY_LABELS[test.priority]}
            </span>
            <StatusBadge status={test.status} size="xs" />
          </div>
          {test.description && (
            <p className="text-xs text-slate-500 line-clamp-1">{test.description}</p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            {requirement && <span className="rounded border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-blue-200">{requirement}</span>}
            {component && <span className="rounded border border-slate-700 px-2 py-0.5">{component}</span>}
            {owner && <span className="rounded border border-slate-700 px-2 py-0.5">{owner}</span>}
            {risk && <span className="rounded border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-amber-200">{risk}</span>}
          </div>
          <div className="text-xs text-slate-600 mt-2">
            {steps.length > 0 && <span>{passedSteps}/{steps.length} adım tamamlandı</span>}
            {test.created_at && (
              <span className="ml-2">{new Date(test.created_at).toLocaleDateString("tr-TR")}</span>
            )}
          </div>
          {steps.length > 0 && (
            <div className="mt-2 h-1.5 max-w-sm overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-emerald-400" style={{ width: `${progress}%` }} />
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {/* Status toggle buttons */}
          {(["passed", "failed", "blocked"] as TestStatus[]).map(s => (
            <button
              key={s}
              onClick={() => changeTestStatus(s)}
              disabled={updatingStatus}
              title={s === "passed" ? "Geçti" : s === "failed" ? "Başarısız" : "Engellendi"}
              className={`p-1.5 rounded-lg border text-xs transition-all disabled:opacity-50 ${
                test.status === s ? STATUS_TOGGLE_COLORS[s] : "text-slate-600 border-slate-700 hover:border-slate-600 hover:text-slate-400"
              }`}
              data-testid={`manual-test-status-${test.id}`}
            >
              {s === "passed" ? "✓" : s === "failed" ? "✗" : "⊘"}
            </button>
          ))}

          <button
            onClick={() => setOpen(v => !v)}
            className="px-2.5 py-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 rounded-lg transition-all"
            data-testid={`manual-test-expand-${test.id}`}
          >
            {open ? "Kapat" : `Adımlar (${steps.length})`}
          </button>

          <button
            onClick={() => onClone(test)}
            className="px-2.5 py-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 rounded-lg transition-all"
            title="Bu testi kopyala"
          >
            Kopyala
          </button>

          <button
            onClick={() => downloadCsv(test)}
            className="px-2.5 py-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 rounded-lg transition-all"
            title="CSV dışa aktar"
          >
            CSV
          </button>

          <button
            onClick={onDelete}
            className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 border border-slate-700 hover:border-red-500/30 transition-all"
            title="Sil"
            data-testid={`manual-test-delete-${test.id}`}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Steps */}
      {open && (
        <div className="border-t border-slate-800 px-4 pb-4 pt-3 space-y-2">
          {steps.length === 0 && (
            <p className="text-xs text-slate-500" data-testid={`manual-test-no-steps-${test.id}`}>
              Henüz adım eklenmedi
            </p>
          )}
          {steps.map(step => (
            <StepRow key={step.id} step={step} testId={test.id} onUpdate={onRefresh} />
          ))}

          {!showStepForm ? (
            <button
              onClick={() => setShowStepForm(true)}
              className="text-xs text-slate-400 hover:text-white border border-dashed border-slate-700 hover:border-slate-500 rounded-lg px-3 py-2 w-full transition-all"
              data-testid={`manual-test-add-step-btn-${test.id}`}
            >
              + Adım Ekle
            </button>
          ) : (
            <form
              onSubmit={handleAddStep}
              className="space-y-2 rounded-lg border border-slate-700 bg-slate-800/50 p-3"
              data-testid={`manual-test-step-form-${test.id}`}
            >
              <input
                placeholder="Eylem (ör. Login butonuna tıkla)"
                value={stepForm.action}
                onChange={e => setStepForm({ ...stepForm, action: e.target.value })}
                required
                className="w-full px-3 py-1.5 text-sm bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500"
                data-testid={`manual-step-input-action-${test.id}`}
              />
              <input
                placeholder="Beklenen sonuç (ör. Anasayfa açılır)"
                value={stepForm.expected}
                onChange={e => setStepForm({ ...stepForm, expected: e.target.value })}
                className="w-full px-3 py-1.5 text-sm bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500"
                data-testid={`manual-step-input-expected-${test.id}`}
              />
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={addingStep}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors disabled:opacity-50"
                  data-testid={`manual-step-submit-${test.id}`}
                >
                  {addingStep ? "Ekleniyor..." : "Kaydet"}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowStepForm(false); setStepForm(emptyStep); }}
                  className="px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors"
                >
                  İptal
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────────── */
export default function ManualPage() {
  const projectId = useRouteParam("projectId");
  const queryClient = useQueryClient();
  const manualQK = ["manual-tests", "list"] as const;

  const [form, setForm] = useState<CreateTestForm>(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [coverage, setCoverage] = useState<Record<CoverageKey, boolean>>({
    positive: true,
    negative: false,
    permission: false,
    edge: false,
    data: false,
    rollback: false,
  });
  const [draftSteps, setDraftSteps] = useState<DraftManualStep[]>([
    makeDraftStep({ action: "Kullanıcı akışı başlatır.", expected: "İlk ekran beklenen şekilde açılır." }),
    makeDraftStep({ action: "Ana işlem tamamlanır.", expected: "Sistem beklenen sonucu gösterir." }),
  ]);
  const createSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const { data: tests = [], isLoading: loading } = useQuery<ManualTest[]>({
    queryKey: manualQK,
    queryFn: () => apiFetch<ManualTest[]>(PROXY),
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });

  const createMut = useMutation({
    mutationFn: async (body: { form: CreateTestForm; steps: DraftManualStep[]; coverage: Record<CoverageKey, boolean> }) => {
      const details = [
        body.form.description.trim(),
        body.form.requirementKey.trim() ? `Requirement: ${body.form.requirementKey.trim()}` : "",
        body.form.component.trim() ? `Component: ${body.form.component.trim()}` : "",
        body.form.owner.trim() ? `Owner: ${body.form.owner.trim()}` : "",
        body.form.tags.trim() ? `Tags: ${body.form.tags.trim()}` : "",
        `Risk: ${RISK_LABELS[body.form.riskLevel]}`,
        `Test type: ${TEST_TYPE_LABELS[body.form.testType]}`,
        body.form.estimatedMinutes.trim() ? `Estimated duration: ${body.form.estimatedMinutes.trim()} dk` : "",
        body.form.environment.trim() ? `Environment: ${body.form.environment.trim()}` : "",
        body.form.preconditions.trim() ? `Ön koşullar: ${body.form.preconditions.trim()}` : "",
        body.form.testData.trim() ? `Test data: ${body.form.testData.trim()}` : "",
        body.form.automationNotes.trim() ? `Otomasyon notları: ${body.form.automationNotes.trim()}` : "",
        `Coverage: ${COVERAGE_ITEMS.filter((item) => body.coverage[item.key]).map((item) => item.label).join(", ") || "Belirtilmedi"}`,
      ].filter(Boolean).join("\n\n");
      const created = await apiFetch<ManualTest>(PROXY, {
        method: "POST",
        json: { title: body.form.title.trim(), description: details, priority: body.form.priority },
      });
      const validSteps = body.steps.filter((step) => step.action.trim());
      if (created?.id && validSteps.length > 0) {
        await Promise.all(validSteps.map((step, index) =>
          apiFetch(`${PROXY}/${created.id}/steps`, {
            method: "POST",
            json: {
              action: step.action.trim(),
              expected: step.expected.trim(),
              step_order: index + 1,
            },
          }),
        ));
      }
      return created;
    },
    onSuccess: () => {
      setForm(emptyForm);
      setCoverage({
        positive: true,
        negative: false,
        permission: false,
        edge: false,
        data: false,
        rollback: false,
      });
      setDraftSteps([
        makeDraftStep({ action: "Kullanıcı akışı başlatır.", expected: "İlk ekran beklenen şekilde açılır." }),
        makeDraftStep({ action: "Ana işlem tamamlanır.", expected: "Sistem beklenen sonucu gösterir." }),
      ]);
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: manualQK });
    },
    onError: (e: unknown) => setErr(e instanceof Error ? e.message : "Hata oluştu"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => apiFetch(`${PROXY}/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: manualQK }),
  });

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setErr(null);
    createMut.mutate({
      form,
      steps: draftSteps,
      coverage,
    });
  }

  function applyTemplate(templateId: string) {
    const template = MANUAL_TEMPLATES.find((item) => item.id === templateId);
    if (!template) return;
    setForm((current) => ({
      ...current,
      description: current.description || template.description,
      priority: template.priority,
    }));
    setDraftSteps(template.steps.map((step) => makeDraftStep(step)));
  }

  function updateDraftStep(stepId: string, next: DraftManualStep) {
    setDraftSteps((current) => current.map((step) => (step.id === stepId ? next : step)));
  }

  function removeDraftStep(stepId: string) {
    setDraftSteps((current) => current.length <= 1 ? current : current.filter((step) => step.id !== stepId));
  }

  function handleDraftStepDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setDraftSteps((current) => {
      const oldIndex = current.findIndex((step) => step.id === active.id);
      const newIndex = current.findIndex((step) => step.id === over.id);
      if (oldIndex < 0 || newIndex < 0) return current;
      return arrayMove(current, oldIndex, newIndex);
    });
  }

  function generateSuggestedSteps() {
    const subject = form.title.trim() || "Kullanıcı akışı";
    const base = [
      makeDraftStep({
        action: `${subject} için gerekli ekran veya başlangıç durumu hazırlanır.`,
        expected: "Kullanıcı beklenen başlangıç durumunu görür.",
      }),
      makeDraftStep({
        action: "Kullanıcı geçerli test verisi ile ana işlemi tamamlar.",
        expected: "Sistem işlemi hata üretmeden tamamlar.",
      }),
      makeDraftStep({
        action: "Kullanıcı sonucu, bildirimleri ve kayıt/listedeki değişikliği kontrol eder.",
        expected: "Sonuç iş kuralına uygun şekilde görünür.",
      }),
    ];
    if (form.preconditions.trim()) {
      base.unshift(makeDraftStep({
        action: "Ön koşullar doğrulanır.",
        expected: form.preconditions.trim(),
      }));
    }
    setDraftSteps(base);
  }

  function addReusableStep(label: string) {
    const item = REUSABLE_STEPS.find((step) => step.label === label);
    if (!item) return;
    setDraftSteps((current) => [...current, makeDraftStep(item)]);
  }

  function cloneTest(test: ManualTest) {
    setForm((current) => ({
      ...current,
      title: `${test.title} - kopya`,
      description: test.description?.split("\n").filter((line) => !line.includes(":")).join("\n").trim() || test.description || "",
      priority: test.priority,
      requirementKey: getMetadataValue(test.description ?? "", "Requirement"),
      component: getMetadataValue(test.description ?? "", "Component"),
      owner: getMetadataValue(test.description ?? "", "Owner"),
      tags: getMetadataValue(test.description ?? "", "Tags"),
      environment: getMetadataValue(test.description ?? "", "Environment"),
    }));
    setDraftSteps((test.steps ?? []).slice().sort((a, b) => a.step_order - b.step_order).map((step) => makeDraftStep({
      action: step.action,
      expected: step.expected,
    })));
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function importStepsFromDescription() {
    const lines = form.description
      .split(/\n+/)
      .map((line) => line.replace(/^[-*\d.\s]+/, "").trim())
      .filter(Boolean);
    if (lines.length === 0) return;
    setDraftSteps(lines.map((line) => makeDraftStep({
      action: line,
      expected: "Beklenen sonuç doğrulanır.",
    })));
  }

  function handleDelete(id: string) {
    deleteMut.mutate(id);
  }

  const creating = createMut.isPending;

  function refresh() {
    queryClient.invalidateQueries({ queryKey: manualQK });
  }

  const filtered = tests.filter(t => {
    const ms = !statusFilter || t.status === statusFilter;
    const mp = !priorityFilter || t.priority === priorityFilter;
    return ms && mp;
  });

  /* stats */
  const total = tests.length;
  const passed = tests.filter(t => t.status === "passed").length;
  const failed = tests.filter(t => t.status === "failed").length;
  const blocked = tests.filter(t => t.status === "blocked").length;
  const completedStepCount = draftSteps.filter((step) => step.action.trim() && step.expected.trim()).length;
  const coverageCount = COVERAGE_ITEMS.filter((item) => coverage[item.key]).length;
  const estimatedMinutes = Number(form.estimatedMinutes);
  const qualityItems = [
    Boolean(form.title.trim()),
    Boolean(form.description.trim()),
    Boolean(form.requirementKey.trim()),
    Boolean(form.component.trim()),
    Boolean(form.owner.trim()),
    Boolean(form.preconditions.trim()),
    Boolean(form.testData.trim()),
    draftSteps.length >= 3,
    completedStepCount === draftSteps.length,
    Boolean(form.automationNotes.trim()),
    coverageCount >= 2,
    Number.isFinite(estimatedMinutes) && estimatedMinutes > 0,
  ];
  const qualityScore = Math.round((qualityItems.filter(Boolean).length / qualityItems.length) * 100);
  const automationReady = Boolean(form.title.trim()) && draftSteps.length >= 2 && completedStepCount === draftSteps.length && Boolean(form.testData.trim());
  const totalSteps = tests.reduce((sum, test) => sum + (test.steps?.length ?? 0), 0);
  const automationCandidates = tests.filter((test) => (test.steps?.length ?? 0) >= 3 && test.description?.includes("Test data:")).length;

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="manual-tests-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
        }
        title="Manuel Testler"
        description="Manuel test senaryolarını yaz, adımları yönet ve otomasyona çevir"
        right={
          <ToolbarActions>
            <Link
              href={`/p/${projectId}/manual-to-automation`}
              className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-sm font-medium text-slate-300 transition-all hover:border-violet-500/50 hover:text-violet-300"
              data-testid="manual-tests-btn-to-automation"
            >
              <svg className="h-3.5 w-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Otomasyona Çevir
            </Link>
            <button
              onClick={() => setShowForm(v => !v)}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
              data-testid="manual-tests-btn-new"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {showForm ? "İptal" : "Yeni Test"}
            </button>
          </ToolbarActions>
        }
      />

      {/* Stats row */}
      <MetricRow cols={4} className="mb-5">
        <StatCard label="Toplam" value={total} color="slate" />
        <StatCard label="Geçti" value={passed} color="emerald" />
        <StatCard label="Başarısız" value={failed} color={failed > 0 ? "red" : "slate"} />
        <StatCard label="Engellendi" value={blocked} color={blocked > 0 ? "amber" : "slate"} />
      </MetricRow>
      <div className="mb-5 grid gap-3 md:grid-cols-3">
        <SectionCard className="p-4">
          <p className="text-xs text-slate-500">Toplam Adım</p>
          <p className="mt-1 text-2xl font-bold text-white">{totalSteps}</p>
        </SectionCard>
        <SectionCard className="p-4">
          <p className="text-xs text-slate-500">Otomasyon Adayı</p>
          <p className="mt-1 text-2xl font-bold text-violet-200">{automationCandidates}</p>
        </SectionCard>
        <SectionCard className="p-4">
          <p className="text-xs text-slate-500">Ortalama Adım</p>
          <p className="mt-1 text-2xl font-bold text-blue-200">{total > 0 ? Math.round(totalSteps / total) : 0}</p>
        </SectionCard>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="mb-5 rounded-xl border border-slate-700 bg-slate-900/50 p-4 shadow-2xl">
          <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Yeni Manuel Test</h2>
              <p className="mt-1 text-xs text-slate-500">Template seç, adımları sırala, tek seferde test olarak kaydet.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={generateSuggestedSteps}
                className="rounded-lg border border-violet-500/40 bg-violet-500/10 px-3 py-2 text-xs font-semibold text-violet-200 hover:bg-violet-500/20"
              >
                AI Adım Üret
              </button>
              {MANUAL_TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => applyTemplate(template.id)}
                  className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-blue-500/50 hover:text-white"
                >
                  {template.label}
                </button>
              ))}
            </div>
          </div>
          <form onSubmit={handleCreate} className="space-y-3" data-testid="manual-tests-create-form">
            <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
              <div className="space-y-3">
                <input
                  placeholder="Test başlığı *"
                  value={form.title}
                  onChange={e => setForm({ ...form, title: e.target.value })}
                  required
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white placeholder-slate-500 transition-colors focus:border-blue-500 focus:outline-none"
                  data-testid="manual-tests-input-title"
                />
                <textarea
                  placeholder="Amaç / kapsam / notlar"
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  rows={3}
                  className="w-full resize-none rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white placeholder-slate-500 transition-colors focus:border-blue-500 focus:outline-none"
                  data-testid="manual-tests-input-desc"
                />
                <div className="grid gap-3 md:grid-cols-2">
                  <input
                    value={form.requirementKey}
                    onChange={e => setForm({ ...form, requirementKey: e.target.value })}
                    placeholder="Requirement / Jira key"
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                  <input
                    value={form.testData}
                    onChange={e => setForm({ ...form, testData: e.target.value })}
                    placeholder="Test data: user=qa, role=admin"
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <input
                    value={form.component}
                    onChange={e => setForm({ ...form, component: e.target.value })}
                    placeholder="Modül / component"
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                  <input
                    value={form.owner}
                    onChange={e => setForm({ ...form, owner: e.target.value })}
                    placeholder="Sorumlu tester"
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                  <input
                    value={form.environment}
                    onChange={e => setForm({ ...form, environment: e.target.value })}
                    placeholder="Ortam: staging, prod-like"
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-[1fr_160px_160px_140px]">
                  <input
                    value={form.tags}
                    onChange={e => setForm({ ...form, tags: e.target.value })}
                    placeholder="Etiketler: login, payment, mobile"
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                  <select
                    value={form.testType}
                    onChange={e => setForm({ ...form, testType: e.target.value as CreateTestForm["testType"] })}
                    className="cursor-pointer rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-300 focus:border-blue-500 focus:outline-none"
                  >
                    {Object.entries(TEST_TYPE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                  <select
                    value={form.riskLevel}
                    onChange={e => setForm({ ...form, riskLevel: e.target.value as CreateTestForm["riskLevel"] })}
                    className="cursor-pointer rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-300 focus:border-blue-500 focus:outline-none"
                  >
                    {Object.entries(RISK_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                  <input
                    value={form.estimatedMinutes}
                    onChange={e => setForm({ ...form, estimatedMinutes: e.target.value.replace(/[^\d]/g, "") })}
                    placeholder="Süre dk"
                    inputMode="numeric"
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <textarea
                    value={form.preconditions}
                    onChange={e => setForm({ ...form, preconditions: e.target.value })}
                    placeholder="Ön koşullar"
                    rows={2}
                    className="resize-none rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                  <textarea
                    value={form.automationNotes}
                    onChange={e => setForm({ ...form, automationNotes: e.target.value })}
                    placeholder="Otomasyon notları: selector, data setup, mock ihtiyacı"
                    rows={2}
                    className="resize-none rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-[180px_1fr]">
                  <div>
                    <label className="mb-1 block text-xs text-slate-400">Öncelik</label>
                    <select
                      value={form.priority}
                      onChange={e => setForm({ ...form, priority: e.target.value as Priority })}
                      className="w-full cursor-pointer rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-300 focus:border-blue-500 focus:outline-none"
                      data-testid="manual-tests-select-priority"
                    >
                      <option value="low">Düşük</option>
                      <option value="medium">Orta</option>
                      <option value="high">Yüksek</option>
                      <option value="critical">Kritik</option>
                    </select>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-xs text-slate-500">Reusable step</p>
                      {REUSABLE_STEPS.map((step) => (
                        <button
                          key={step.label}
                          type="button"
                          onClick={() => addReusableStep(step.label)}
                          className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-blue-500/50 hover:text-white"
                        >
                          {step.label}
                        </button>
                      ))}
                      <button
                        type="button"
                        onClick={importStepsFromDescription}
                        className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-blue-500/50 hover:text-white"
                      >
                        Açıklamadan Adım
                      </button>
                    </div>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">Coverage Matrisi</p>
                      <p className="text-xs text-slate-500">Senaryonun kapsadığı test açılarını işaretle.</p>
                    </div>
                    <span className="rounded-full border border-slate-700 px-2 py-1 text-xs text-slate-400">
                      {coverageCount}/{COVERAGE_ITEMS.length}
                    </span>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {COVERAGE_ITEMS.map((item) => (
                      <label
                        key={item.key}
                        className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-all ${
                          coverage[item.key]
                            ? "border-blue-500/40 bg-blue-500/10 text-blue-100"
                            : "border-slate-700 bg-slate-900/70 text-slate-400 hover:border-slate-500"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={coverage[item.key]}
                          onChange={(event) => setCoverage((current) => ({ ...current, [item.key]: event.target.checked }))}
                          className="h-4 w-4 rounded border-slate-600 bg-slate-900"
                        />
                        {item.label}
                      </label>
                    ))}
                  </div>
                </div>

                <DndContext sensors={createSensors} collisionDetection={closestCenter} onDragEnd={handleDraftStepDragEnd}>
                  <SortableContext items={draftSteps.map((step) => step.id)} strategy={verticalListSortingStrategy}>
                    <div className="space-y-2">
                      {draftSteps.map((step, index) => (
                        <DraftStepRow
                          key={step.id}
                          step={step}
                          index={index}
                          onChange={(next) => updateDraftStep(step.id, next)}
                          onRemove={() => removeDraftStep(step.id)}
                        />
                      ))}
                    </div>
                  </SortableContext>
                </DndContext>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setDraftSteps((current) => [...current, makeDraftStep()])}
                    className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800 hover:text-white"
                  >
                    Adım Ekle
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
                    data-testid="manual-tests-btn-create"
                  >
                    {creating ? "Oluşturuluyor..." : "Testi Oluştur"}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setShowForm(false); setForm(emptyForm); setErr(null); }}
                    className="px-3 py-2 text-sm text-slate-400 transition-colors hover:text-white"
                  >
                    İptal
                  </button>
                </div>
                {err && <p className="text-sm text-red-400" data-testid="manual-tests-alert-error">{err}</p>}
              </div>

              <aside className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-white">Canlı Önizleme</h3>
                  <span className={`rounded-full px-2 py-1 text-xs font-semibold ${PRIORITY_BADGE[form.priority]}`}>
                    {PRIORITY_LABELS[form.priority]}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                    <p className="text-xs text-slate-500">Kalite Skoru</p>
                    <p className={`mt-1 text-2xl font-bold ${qualityScore >= 75 ? "text-emerald-300" : qualityScore >= 50 ? "text-amber-300" : "text-red-300"}`}>
                      {qualityScore}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                    <p className="text-xs text-slate-500">Otomasyon</p>
                    <p className={`mt-2 text-xs font-semibold ${automationReady ? "text-emerald-300" : "text-amber-300"}`}>
                      {automationReady ? "Hazır" : "Eksikler var"}
                    </p>
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                    <p className="text-xs text-slate-500">Tip</p>
                    <p className="mt-1 text-xs font-semibold text-slate-200">{TEST_TYPE_LABELS[form.testType]}</p>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                    <p className="text-xs text-slate-500">Risk</p>
                    <p className={`mt-1 text-xs font-semibold ${form.riskLevel === "high" ? "text-amber-200" : form.riskLevel === "low" ? "text-emerald-200" : "text-blue-200"}`}>
                      {RISK_LABELS[form.riskLevel]}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                    <p className="text-xs text-slate-500">Coverage</p>
                    <p className="mt-1 text-xs font-semibold text-slate-200">{coverageCount}/{COVERAGE_ITEMS.length}</p>
                  </div>
                </div>
                <div className="mt-4 space-y-3">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Başlık</p>
                    <p className="mt-1 text-sm font-semibold text-white">{form.title || "Henüz başlık yok"}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {form.requirementKey && <span className="rounded bg-blue-500/10 px-2 py-1 text-xs text-blue-200">{form.requirementKey}</span>}
                    {form.component && <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">{form.component}</span>}
                    {form.owner && <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">{form.owner}</span>}
                    {form.environment && <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">{form.environment}</span>}
                    {form.testData && <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">test data</span>}
                    {form.preconditions && <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">precondition</span>}
                  </div>
                  {form.tags && (
                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500">Etiketler</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {form.tags.split(",").map((tag) => tag.trim()).filter(Boolean).map((tag) => (
                          <span key={tag} className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300">{tag}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Açıklama</p>
                    <p className="mt-1 text-sm leading-6 text-slate-300">{form.description || "Açıklama yazılmadı."}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Hazırlık Kontrolü</p>
                    <ul className="mt-2 space-y-1 text-xs text-slate-400">
                      <li className={form.title.trim() ? "text-emerald-300" : ""}>Başlık</li>
                      <li className={form.requirementKey.trim() ? "text-emerald-300" : ""}>Requirement bağlantısı</li>
                      <li className={form.owner.trim() ? "text-emerald-300" : ""}>Sorumlu tester</li>
                      <li className={draftSteps.length >= 3 ? "text-emerald-300" : ""}>En az 3 adım</li>
                      <li className={completedStepCount === draftSteps.length ? "text-emerald-300" : ""}>Her adımda beklenen sonuç</li>
                      <li className={form.testData.trim() ? "text-emerald-300" : ""}>Test data</li>
                      <li className={form.automationNotes.trim() ? "text-emerald-300" : ""}>Otomasyon notu</li>
                      <li className={coverageCount >= 2 ? "text-emerald-300" : ""}>En az 2 coverage alanı</li>
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Coverage</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {COVERAGE_ITEMS.filter((item) => coverage[item.key]).map((item) => (
                        <span key={item.key} className="rounded bg-blue-500/10 px-2 py-1 text-xs text-blue-200">{item.label}</span>
                      ))}
                      {coverageCount === 0 && <span className="text-xs text-slate-500">Coverage seçilmedi.</span>}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Adımlar</p>
                    <ol className="mt-2 space-y-2">
                      {draftSteps.map((step, index) => (
                        <li key={step.id} className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                          <p className="text-xs font-semibold text-slate-500">#{index + 1}</p>
                          <p className="mt-1 text-sm text-slate-200">{step.action || "Aksiyon boş"}</p>
                          <p className="mt-1 text-xs text-blue-200">{step.expected || "Beklenen sonuç boş"}</p>
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              </aside>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4">
        <FilterBar
          filters={[
            {
              key: "status",
              label: "Tüm Durumlar",
              value: statusFilter,
              onChange: setStatusFilter,
              options: [
                { label: "Bekliyor", value: "pending" },
                { label: "Geçti", value: "passed" },
                { label: "Başarısız", value: "failed" },
                { label: "Engellendi", value: "blocked" },
              ],
            },
            {
              key: "priority",
              label: "Tüm Öncelikler",
              value: priorityFilter,
              onChange: setPriorityFilter,
              options: [
                { label: "Kritik", value: "critical" },
                { label: "Yüksek", value: "high" },
                { label: "Orta", value: "medium" },
                { label: "Düşük", value: "low" },
              ],
            },
          ]}
          right={<span className="text-xs text-slate-500">{filtered.length} test</span>}
        />
      </div>

      {/* Test list */}
      {loading ? (
        <div className="py-16 text-center text-slate-500 text-sm flex items-center justify-center gap-2" data-testid="manual-tests-loading">
          <div className="w-4 h-4 border-2 border-slate-700 border-t-blue-400 rounded-full animate-spin" />
          Yükleniyor...
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon="✍️"
          title="Henüz manuel test yok"
          description="İlk manuel testinizi oluşturun veya filtrelerinizi değiştirin"
          action={
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors"
              data-testid="manual-tests-btn-empty-new"
            >
              İlk Testi Oluştur
            </button>
          }
        />
      ) : (
        <div className="space-y-3" data-testid="manual-tests-list">
          {filtered.map(test => (
            <TestCard
              key={test.id}
              test={test}
              projectId={projectId}
              onDelete={() => handleDelete(test.id)}
              onRefresh={refresh}
              onClone={cloneTest}
            />
          ))}
        </div>
      )}
    </div>
  );
}
