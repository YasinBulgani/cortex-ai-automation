"use client";

import { useCallback, useEffect, useState } from "react";

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
type CreateTestForm = { title: string; description: string; priority: Priority };
type CreateStepForm = { action: string; expected: string };

const PROXY = "/api/v1/automation/proxy/api/manual-tests";
const emptyForm: CreateTestForm = { title: "", description: "", priority: "medium" };
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
  test, projectId, onDelete, onRefresh,
}: { test: ManualTest; projectId: string; onDelete: () => void; onRefresh: () => void }) {
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
          <div className="text-xs text-slate-600 mt-1">
            {steps.length > 0 && <span>{passedSteps}/{steps.length} adım tamamlandı</span>}
            {test.created_at && (
              <span className="ml-2">{new Date(test.created_at).toLocaleDateString("tr-TR")}</span>
            )}
          </div>
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
  const [tests, setTests] = useState<ManualTest[]>([]);
  const [form, setForm] = useState<CreateTestForm>(emptyForm);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<ManualTest[]>(PROXY);
      setTests(data ?? []);
    } catch { setTests([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setErr(null); setCreating(true);
    try {
      await apiFetch(PROXY, {
        method: "POST",
        json: { title: form.title.trim(), description: form.description.trim(), priority: form.priority },
      });
      setForm(emptyForm); setShowForm(false); load();
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : "Hata oluştu"); }
    finally { setCreating(false); }
  }

  async function handleDelete(id: string) {
    await apiFetch(`${PROXY}/${id}`, { method: "DELETE" });
    load();
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

      {/* Create form */}
      {showForm && (
        <div className="mb-4 rounded-xl border border-slate-700 bg-slate-900/40 p-4">
          <h2 className="text-sm font-semibold text-white mb-3">Yeni Manuel Test</h2>
          <form onSubmit={handleCreate} className="space-y-3" data-testid="manual-tests-create-form">
            <input
              placeholder="Test başlığı *"
              value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })}
              required
              className="w-full px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500 transition-colors"
              data-testid="manual-tests-input-title"
            />
            <textarea
              placeholder="Açıklama (isteğe bağlı)"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500 resize-none transition-colors"
              data-testid="manual-tests-input-desc"
            />
            <div className="flex gap-3 items-end">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Öncelik</label>
                <select
                  value={form.priority}
                  onChange={e => setForm({ ...form, priority: e.target.value as Priority })}
                  className="px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-slate-300 focus:outline-none focus:border-slate-500 cursor-pointer"
                  data-testid="manual-tests-select-priority"
                >
                  <option value="low">Düşük</option>
                  <option value="medium">Orta</option>
                  <option value="high">Yüksek</option>
                  <option value="critical">Kritik</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={creating}
                className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
                data-testid="manual-tests-btn-create"
              >
                {creating ? "Oluşturuluyor..." : "Testi Oluştur"}
              </button>
              <button
                type="button"
                onClick={() => { setShowForm(false); setForm(emptyForm); setErr(null); }}
                className="px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                İptal
              </button>
            </div>
            {err && <p className="text-sm text-red-400" data-testid="manual-tests-alert-error">{err}</p>}
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
              onRefresh={load}
            />
          ))}
        </div>
      )}
    </div>
  );
}
