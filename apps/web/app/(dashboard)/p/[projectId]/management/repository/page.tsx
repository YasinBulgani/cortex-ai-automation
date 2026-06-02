"use client";

import { useMemo, useState } from "react";
import {
  closestCorners,
  DndContext,
  type DragEndEvent,
  DragOverlay,
  type DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  useDroppable,
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
import {
  useCreateManagementCase,
  useCreateManagementFolder,
  useCreateManagementSuite,
  useCreateRegressionSet,
  useMoveManagementCase,
  useManagementRepository,
  useRegressionSets,
  useSearchSimilarCases,
  type CreateTestCaseInput,
  type RegressionSet,
  type TestCase,
  type TestFolder,
  type TestSuite,
  type SimilarCaseResult,
} from "@/lib/hooks/use-management";
import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

// ── Semantic search panel ─────────────────────────────────────────────────────

function SemanticSearchPanel({ projectId }: { projectId: string }) {
  const [query, setQuery] = useState("");
  const searchMutation = useSearchSimilarCases(projectId);

  const handleSearch = () => {
    if (!query.trim()) return;
    searchMutation.mutate({ query: query.trim(), k: 8, min_score: 0.25 });
  };

  const results: SimilarCaseResult[] = searchMutation.data ?? [];

  const STATUS_STYLES: Record<string, string> = {
    passed: "bg-emerald-500/15 text-emerald-400",
    failed: "bg-rose-500/15 text-rose-400",
    blocked: "bg-amber-500/15 text-amber-400",
    not_run: "bg-slate-700 text-slate-400",
    skipped: "bg-slate-600 text-slate-400",
  };

  return (
    <ManagementPanel title="Semantik Senaryo Arama">
      <div className="space-y-3">
        <p className="text-xs text-slate-400">
          Doğal dilde bir test senaryosu tanımlayın — AI en benzer senaryoları bulur.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
            placeholder='Örn: "kullanıcı şifresini değiştirir ve doğrulama e-postası alır"'
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <button
            onClick={handleSearch}
            disabled={searchMutation.isPending || !query.trim()}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
          >
            {searchMutation.isPending ? (
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 animate-spin rounded-full border border-white/30 border-t-white" />
                Arıyor…
              </span>
            ) : "Ara"}
          </button>
        </div>

        {searchMutation.isError && (
          <p className="text-xs text-rose-400">
            AI Gateway erişilemiyor — semantik arama kullanılamıyor.
          </p>
        )}

        {searchMutation.isSuccess && results.length === 0 && (
          <p className="py-4 text-center text-sm text-slate-500">
            Eşleşen senaryo bulunamadı. Arama terimini değiştirmeyi deneyin.
          </p>
        )}

        {results.length > 0 && (
          <div className="space-y-2">
            {results.map((r) => (
              <div
                key={r.case_id}
                className="flex items-start justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="flex-shrink-0 font-mono text-xs text-slate-500">
                      {r.case_key}
                    </span>
                    {r.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  <p className="mt-0.5 truncate text-sm text-slate-200">{r.title}</p>
                </div>
                <div className="flex flex-shrink-0 flex-col items-end gap-1">
                  <span className="text-xs font-semibold text-teal-400">
                    {(r.score * 100).toFixed(0)}%
                  </span>
                  {r.last_run_status && (
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        STATUS_STYLES[r.last_run_status] ?? "bg-slate-700 text-slate-400"
                      }`}
                    >
                      {r.last_run_status.replace("_", " ")}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </ManagementPanel>
  );
}

// ── Test case authoring studio ────────────────────────────────────────────────

type DraftStep = {
  id: string;
  action: string;
  expected_result: string;
  test_data: string;
  is_required: boolean;
};

type CaseTemplate = {
  id: string;
  label: string;
  type: string;
  priority: string;
  severity: string;
  tags: string[];
  objective: string;
  steps: Omit<DraftStep, "id">[];
};

const CASE_TEMPLATES: CaseTemplate[] = [
  {
    id: "happy-path",
    label: "Happy Path",
    type: "manual",
    priority: "P1",
    severity: "major",
    tags: ["happy-path", "regression"],
    objective: "Ana kullanıcı akışının beklenen şekilde tamamlandığını doğrula.",
    steps: [
      { action: "Kullanıcı ilgili sayfayı açar.", expected_result: "Sayfa hatasız yüklenir.", test_data: "", is_required: true },
      { action: "Zorunlu alanlar geçerli veriyle doldurulur.", expected_result: "Form gönderime hazır hale gelir.", test_data: "", is_required: true },
      { action: "Kaydet veya devam et aksiyonu çalıştırılır.", expected_result: "İşlem başarıyla tamamlanır ve kullanıcıya geri bildirim gösterilir.", test_data: "", is_required: true },
    ],
  },
  {
    id: "negative",
    label: "Negatif Senaryo",
    type: "manual",
    priority: "P1",
    severity: "critical",
    tags: ["negative", "validation"],
    objective: "Geçersiz veri ve hata mesajı davranışlarını doğrula.",
    steps: [
      { action: "Kullanıcı zorunlu alanlardan birini boş bırakır.", expected_result: "Alan bazlı hata mesajı gösterilir.", test_data: "empty required field", is_required: true },
      { action: "Kullanıcı geçersiz formatta veri girer.", expected_result: "Sistem gönderimi engeller.", test_data: "invalid value", is_required: true },
      { action: "Kullanıcı hatayı düzeltir ve tekrar dener.", expected_result: "İşlem geçerli veriyle tamamlanır.", test_data: "valid value", is_required: true },
    ],
  },
  {
    id: "smoke",
    label: "Smoke",
    type: "smoke",
    priority: "P0",
    severity: "critical",
    tags: ["smoke", "release"],
    objective: "Release öncesi kritik akışın minimum kontrollerle çalıştığını doğrula.",
    steps: [
      { action: "Kritik modül açılır.", expected_result: "Modül erişilebilir durumdadır.", test_data: "", is_required: true },
      { action: "Temel işlem tamamlanır.", expected_result: "Kritik fonksiyon hata üretmeden çalışır.", test_data: "", is_required: true },
    ],
  },
];

function makeStep(step?: Partial<DraftStep>): DraftStep {
  return {
    id: `step-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    action: step?.action ?? "",
    expected_result: step?.expected_result ?? "",
    test_data: step?.test_data ?? "",
    is_required: step?.is_required ?? true,
  };
}

function SortableStepEditor({
  step,
  index,
  onChange,
  onRemove,
}: {
  step: DraftStep;
  index: number;
  onChange: (next: DraftStep) => void;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.45 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950/60 p-3 lg:grid-cols-[40px_1fr_1fr_0.8fr_84px]"
    >
      <button
        type="button"
        className="flex h-9 w-9 cursor-grab items-center justify-center rounded-md border border-slate-800 text-xs font-semibold text-slate-400 active:cursor-grabbing"
        title="Adımı sürükle"
        {...attributes}
        {...listeners}
      >
        {index + 1}
      </button>
      <textarea
        value={step.action}
        onChange={(event) => onChange({ ...step, action: event.target.value })}
        placeholder="Aksiyon"
        className="min-h-[72px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
      />
      <textarea
        value={step.expected_result}
        onChange={(event) => onChange({ ...step, expected_result: event.target.value })}
        placeholder="Beklenen sonuç"
        className="min-h-[72px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
      />
      <textarea
        value={step.test_data}
        onChange={(event) => onChange({ ...step, test_data: event.target.value })}
        placeholder="Test data"
        className="min-h-[72px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
      />
      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2 rounded-lg border border-slate-800 px-2 py-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={step.is_required}
            onChange={(event) => onChange({ ...step, is_required: event.target.checked })}
            className="h-4 w-4 accent-teal-500"
          />
          Zorunlu
        </label>
        <button
          type="button"
          onClick={onRemove}
          className="rounded-lg border border-rose-500/30 px-2 py-2 text-xs font-semibold text-rose-200 hover:bg-rose-500/10"
        >
          Sil
        </button>
      </div>
    </div>
  );
}

function TestCaseAuthoringStudio({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const createCase = useCreateManagementCase(projectId);
  const suites = repoQuery.data?.suites ?? [];
  const folders = repoQuery.data?.folders ?? [];
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [preconditions, setPreconditions] = useState("");
  const [suiteId, setSuiteId] = useState("");
  const [folderId, setFolderId] = useState("");
  const [priority, setPriority] = useState("P1");
  const [severity, setSeverity] = useState("major");
  const [type, setType] = useState("manual");
  const [status, setStatus] = useState("draft");
  const [tagsText, setTagsText] = useState("manual, regression");
  const [saveMessage, setSaveMessage] = useState("");
  const [steps, setSteps] = useState<DraftStep[]>([
    makeStep({ action: "Kullanıcı akışı başlatır.", expected_result: "İlk ekran beklenen şekilde açılır." }),
    makeStep({ action: "Ana işlem tamamlanır.", expected_result: "Sistem başarılı işlem sonucunu gösterir." }),
  ]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const selectedFolder = folders.find((folder) => folder.id === folderId);
  const selectedSuiteId = suiteId || selectedFolder?.suite_id || "";
  const coverageScore = [
    title.trim(),
    objective.trim(),
    preconditions.trim(),
    selectedSuiteId,
    tagsText.trim(),
    steps.length >= 2 ? "steps" : "",
    steps.every((step) => step.action.trim() && step.expected_result.trim()) ? "complete-steps" : "",
  ].filter(Boolean).length;
  const isReadyToSave = title.trim() && steps.some((step) => step.action.trim() && step.expected_result.trim());

  const applyTemplate = (template: CaseTemplate) => {
    setObjective(template.objective);
    setPriority(template.priority);
    setSeverity(template.severity);
    setType(template.type);
    setTagsText(template.tags.join(", "));
    setSteps(template.steps.map((step) => makeStep(step)));
    setSaveMessage(`${template.label} taslağı uygulandı.`);
  };

  const updateStep = (stepId: string, next: DraftStep) => {
    setSteps((current) => current.map((step) => (step.id === stepId ? next : step)));
  };

  const removeStep = (stepId: string) => {
    setSteps((current) => current.length <= 1 ? current : current.filter((step) => step.id !== stepId));
  };

  const handleStepDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setSteps((current) => {
      const oldIndex = current.findIndex((step) => step.id === active.id);
      const newIndex = current.findIndex((step) => step.id === over.id);
      if (oldIndex < 0 || newIndex < 0) return current;
      return arrayMove(current, oldIndex, newIndex);
    });
  };

  const handleSave = async () => {
    if (!isReadyToSave) return;
    const tags = tagsText.split(",").map((tag) => tag.trim()).filter(Boolean);
    const payload: CreateTestCaseInput = {
      title: title.trim(),
      objective: objective.trim() || null,
      preconditions: preconditions.trim() || null,
      suite_id: selectedSuiteId || null,
      folder_id: folderId || null,
      priority,
      severity,
      type,
      status,
      source_type: "manual",
      tags,
      steps: steps
        .filter((step) => step.action.trim() || step.expected_result.trim())
        .map((step, index) => ({
          step_no: index + 1,
          action: step.action.trim(),
          expected_result: step.expected_result.trim(),
          test_data: step.test_data.trim() ? { value: step.test_data.trim() } : {},
          is_required: step.is_required,
        })),
    };
    try {
      const created = await createCase.mutateAsync(payload);
      setSaveMessage(`${created.case_key} kaydedildi.`);
      setTitle("");
      setObjective("");
      setPreconditions("");
      setStatus("draft");
      setSteps([makeStep(), makeStep()]);
    } catch {
      setSaveMessage("Senaryo kaydedilemedi. Zorunlu alanları ve suite/folder seçimini kontrol edin.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3 lg:grid-cols-3">
        {CASE_TEMPLATES.map((template) => (
          <button
            key={template.id}
            type="button"
            onClick={() => applyTemplate(template)}
            className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-left hover:border-teal-500/40 hover:bg-teal-500/5"
          >
            <span className="text-sm font-semibold text-white">{template.label}</span>
            <span className="mt-1 block text-xs text-slate-500">{template.tags.join(" · ")}</span>
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-3">
          <div className="grid gap-3 lg:grid-cols-2">
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Senaryo başlığı"
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none lg:col-span-2"
            />
            <textarea
              value={objective}
              onChange={(event) => setObjective(event.target.value)}
              placeholder="Amaç"
              className="min-h-[86px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
            />
            <textarea
              value={preconditions}
              onChange={(event) => setPreconditions(event.target.value)}
              placeholder="Ön koşullar"
              className="min-h-[86px] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
            />
          </div>

          <div className="grid gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3 md:grid-cols-3 xl:grid-cols-6">
            <select value={suiteId} onChange={(event) => setSuiteId(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Suite</option>
              {suites.map((suite) => <option key={suite.id} value={suite.id}>{suite.name}</option>)}
            </select>
            <select value={folderId} onChange={(event) => setFolderId(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Folder</option>
              {folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.path}</option>)}
            </select>
            <select value={priority} onChange={(event) => setPriority(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              {["P0", "P1", "P2", "P3"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <select value={severity} onChange={(event) => setSeverity(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              {["critical", "major", "minor", "trivial"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <select value={type} onChange={(event) => setType(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              {["manual", "regression", "smoke", "uat", "exploratory"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <select value={status} onChange={(event) => setStatus(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              {["draft", "active", "review"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>

          <input
            value={tagsText}
            onChange={(event) => setTagsText(event.target.value)}
            placeholder="Tag'ler: smoke, login, regression"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />

          <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={handleStepDragEnd}>
            <SortableContext items={steps.map((step) => step.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {steps.map((step, index) => (
                  <SortableStepEditor
                    key={step.id}
                    step={step}
                    index={index}
                    onChange={(next) => updateStep(step.id, next)}
                    onRemove={() => removeStep(step.id)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSteps((current) => [...current, makeStep()])}
              className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800"
            >
              Adım Ekle
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={!isReadyToSave || createCase.isPending}
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
            >
              {createCase.isPending ? "Kaydediliyor..." : "Senaryoyu Kaydet"}
            </button>
            {saveMessage && <span className="self-center text-xs text-slate-400">{saveMessage}</span>}
          </div>
        </div>

        <aside className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-white">Canlı Önizleme</h3>
            <span className="rounded-full bg-teal-500/10 px-2 py-1 text-xs text-teal-200">
              {coverageScore}/7 doluluk
            </span>
          </div>
          <div className="mt-4 space-y-3 text-sm">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Başlık</p>
              <p className="mt-1 font-semibold text-white">{title || "Henüz başlık yok"}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {[priority, severity, type, status].map((item) => (
                <span key={item} className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">{item}</span>
              ))}
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Amaç</p>
              <p className="mt-1 text-slate-300">{objective || "Amaç yazılmadı."}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Adımlar</p>
              <ol className="mt-2 space-y-2">
                {steps.map((step, index) => (
                  <li key={step.id} className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                    <p className="text-xs font-semibold text-slate-400">#{index + 1} {step.is_required ? "zorunlu" : "opsiyonel"}</p>
                    <p className="mt-1 text-slate-200">{step.action || "Aksiyon boş"}</p>
                    <p className="mt-1 text-xs text-teal-200">{step.expected_result || "Beklenen sonuç boş"}</p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

// ── Drag/drop folder organizer ────────────────────────────────────────────────

const INBOX_FOLDER_ID = "__inbox__";

function folderDropId(folderId: string) {
  return `folder:${folderId}`;
}

function getCaseFolderId(testCase: TestCase) {
  return testCase.folder_id ?? INBOX_FOLDER_ID;
}

function getFolderColumnLabel(folder: TestFolder | null) {
  if (!folder) return "Inbox";
  return folder.path || folder.name;
}

function SortableCaseCard({
  testCase,
  active,
}: {
  testCase: TestCase;
  active?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: testCase.id,
    data: { kind: "case", folderId: getCaseFolderId(testCase) },
  });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.35 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`group cursor-grab rounded-lg border p-3 shadow-sm transition active:cursor-grabbing ${
        active
          ? "border-teal-400/50 bg-teal-500/10"
          : "border-slate-800 bg-slate-950/70 hover:border-slate-700 hover:bg-slate-900/70"
      }`}
      {...attributes}
      {...listeners}
    >
      <div className="flex items-start gap-2">
        <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
          {testCase.case_key}
        </span>
        <span className="ml-auto rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
          {testCase.priority}
        </span>
      </div>
      <p className="mt-2 line-clamp-2 text-xs font-semibold leading-5 text-slate-100">
        {testCase.title}
      </p>
      <div className="mt-2 flex flex-wrap gap-1">
        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-500">
          {testCase.type}
        </span>
        {testCase.last_run_status && (
          <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-200">
            {testCase.last_run_status}
          </span>
        )}
      </div>
    </div>
  );
}

function FolderDropColumn({
  folder,
  cases,
  children,
}: {
  folder: TestFolder | null;
  cases: TestCase[];
  children: React.ReactNode;
}) {
  const folderId = folder?.id ?? INBOX_FOLDER_ID;
  const { isOver, setNodeRef } = useDroppable({
    id: folderDropId(folderId),
    data: { kind: "folder", folderId, suiteId: folder?.suite_id ?? null },
  });

  return (
    <div
      ref={setNodeRef}
      className={`flex min-h-[320px] flex-col rounded-lg border transition ${
        isOver ? "border-teal-400/60 bg-teal-500/10" : "border-slate-800 bg-slate-950/40"
      }`}
    >
      <div className="border-b border-slate-800 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${folder ? "bg-teal-400" : "bg-slate-500"}`} />
          <h3 className="truncate text-sm font-semibold text-white">{getFolderColumnLabel(folder)}</h3>
          <span className="ml-auto rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
            {cases.length}
          </span>
        </div>
        <p className="mt-1 truncate text-xs text-slate-500">
          {folder ? folder.name : "Folder atanmamış senaryolar"}
        </p>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-2">{children}</div>
    </div>
  );
}

function RepositoryDragDropBoard({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const moveCase = useMoveManagementCase(projectId);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [moveMessage, setMoveMessage] = useState("");
  const folders = repoQuery.data?.folders ?? [];
  const cases = repoQuery.data?.cases.filter((item) => !item.archived).slice(0, 120) ?? [];
  const activeCase = activeId ? cases.find((item) => item.id === activeId) : null;
  const visibleFolders = folders.slice(0, 5);
  const columns = useMemo(
    () => [null, ...visibleFolders].map((folder) => {
      const id = folder?.id ?? INBOX_FOLDER_ID;
      return {
        folder,
        id,
        cases: cases.filter((item) => getCaseFolderId(item) === id),
      };
    }),
    [cases, visibleFolders],
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const resolveTarget = (event: DragEndEvent) => {
    const over = event.over;
    if (!over) return null;
    const direct = over.data.current;
    if (direct?.kind === "folder") {
      return {
        folderId: direct.folderId as string,
        suiteId: direct.suiteId as string | null,
      };
    }
    const overCase = cases.find((item) => item.id === String(over.id));
    if (!overCase) return null;
    const folder = folders.find((item) => item.id === overCase.folder_id) ?? null;
    return {
      folderId: overCase.folder_id ?? INBOX_FOLDER_ID,
      suiteId: folder?.suite_id ?? null,
    };
  };

  const handleDragStart = (event: DragStartEvent) => {
    setMoveMessage("");
    setActiveId(String(event.active.id));
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveId(null);
    const draggedCase = cases.find((item) => item.id === String(event.active.id));
    const target = resolveTarget(event);
    if (!draggedCase || !target) return;
    const nextFolderId = target.folderId === INBOX_FOLDER_ID ? null : target.folderId;
    if ((draggedCase.folder_id ?? null) === nextFolderId) return;

    try {
      await moveCase.mutateAsync({
        caseId: draggedCase.id,
        folder_id: nextFolderId,
        suite_id: target.suiteId,
        change_summary: `Moved to ${target.folderId === INBOX_FOLDER_ID ? "Inbox" : "folder"} by drag and drop`,
      });
      setMoveMessage(`${draggedCase.case_key} taşındı.`);
    } catch {
      setMoveMessage("Taşıma tamamlanamadı. Folder/suite ilişkisini kontrol edin.");
    }
  };

  if (repoQuery.isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
      </div>
    );
  }

  if (cases.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">Sürüklemek için aktif test senaryosu yok.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
        <span>Case kartlarını folder kolonlarına sürükleyerek repository düzenini güncelleyin.</span>
        <span className="rounded-full bg-slate-800 px-2 py-1">
          {moveCase.isPending ? "Taşınıyor..." : moveMessage || `${cases.length} aktif case`}
        </span>
      </div>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="grid gap-3 lg:grid-cols-3 xl:grid-cols-6">
          {columns.map((column) => (
            <SortableContext
              key={column.id}
              items={column.cases.map((item) => item.id)}
              strategy={verticalListSortingStrategy}
            >
              <FolderDropColumn folder={column.folder} cases={column.cases}>
                {column.cases.slice(0, 10).map((testCase) => (
                  <SortableCaseCard key={testCase.id} testCase={testCase} />
                ))}
                {column.cases.length === 0 && (
                  <p className="rounded-lg border border-dashed border-slate-800 px-3 py-8 text-center text-xs text-slate-500">
                    Buraya bırak
                  </p>
                )}
                {column.cases.length > 10 && (
                  <p className="px-2 py-1 text-xs text-slate-500">+{column.cases.length - 10} daha tabloda</p>
                )}
              </FolderDropColumn>
            </SortableContext>
          ))}
        </div>
        <DragOverlay>{activeCase ? <SortableCaseCard testCase={activeCase} active /> : null}</DragOverlay>
      </DndContext>
    </div>
  );
}

// ── Repository hierarchy and set builder ─────────────────────────────────────

function slugifyFolderPath(name: string) {
  return `/${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || name}`;
}

function SuiteTreeCard({
  suite,
  folders,
  cases,
}: {
  suite: TestSuite;
  folders: TestFolder[];
  cases: TestCase[];
}) {
  const suiteFolders = folders.filter((folder) => folder.suite_id === suite.id);
  const suiteCases = cases.filter((testCase) => testCase.suite_id === suite.id);
  const directCases = suiteCases.filter((testCase) => !testCase.folder_id);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60">
      <div className="border-b border-slate-800 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-500/10 text-sm text-teal-200">S</span>
              <h3 className="truncate text-sm font-semibold text-white">{suite.name}</h3>
            </div>
            {suite.description && <p className="mt-1 line-clamp-1 text-xs text-slate-500">{suite.description}</p>}
          </div>
          <span className="rounded-full border border-slate-700 px-2 py-1 text-xs text-slate-400">
            {suiteCases.length} case
          </span>
        </div>
      </div>
      <div className="space-y-2 p-3">
        {suiteFolders.map((folder) => {
          const folderCases = cases.filter((testCase) => testCase.folder_id === folder.id);
          return (
            <div key={folder.id} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="text-slate-500">└</span>
                <span className="truncate text-sm font-medium text-slate-200">{folder.path || folder.name}</span>
                <span className="ml-auto rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">{folderCases.length}</span>
              </div>
              {folderCases.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {folderCases.slice(0, 4).map((testCase) => (
                    <span key={testCase.id} className="rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                      {testCase.case_key}
                    </span>
                  ))}
                  {folderCases.length > 4 && <span className="text-xs text-slate-600">+{folderCases.length - 4}</span>}
                </div>
              )}
            </div>
          );
        })}
        {directCases.length > 0 && (
          <div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-400">
            Suite altında klasörsüz {directCases.length} case var.
          </div>
        )}
        {suiteFolders.length === 0 && directCases.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-800 px-3 py-6 text-center text-xs text-slate-500">
            Bu suite için henüz folder veya case yok.
          </div>
        )}
      </div>
    </div>
  );
}

function RepositoryHierarchyPanel({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const createSuite = useCreateManagementSuite(projectId);
  const createFolder = useCreateManagementFolder(projectId);
  const suites = repoQuery.data?.suites ?? [];
  const folders = repoQuery.data?.folders ?? [];
  const cases = repoQuery.data?.cases ?? [];
  const [suiteName, setSuiteName] = useState("");
  const [folderName, setFolderName] = useState("");
  const [folderSuiteId, setFolderSuiteId] = useState("");
  const [message, setMessage] = useState("");

  const createQuickSuite = async () => {
    if (!suiteName.trim()) return;
    const created = await createSuite.mutateAsync({
      name: suiteName.trim(),
      description: "Management repository suite",
    });
    setFolderSuiteId(created.id);
    setSuiteName("");
    setMessage(`${created.name} suite oluşturuldu.`);
  };

  const createQuickFolder = async () => {
    const suiteId = folderSuiteId || suites[0]?.id;
    if (!suiteId || !folderName.trim()) return;
    const created = await createFolder.mutateAsync({
      suite_id: suiteId,
      name: folderName.trim(),
      path: slugifyFolderPath(folderName.trim()),
    });
    setFolderName("");
    setMessage(`${created.path} folder oluşturuldu.`);
  };

  return (
    <ManagementPanel title="Repository Ağacı">
      <div className="grid gap-4 xl:grid-cols-[0.72fr_1.28fr]">
        <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div>
            <p className="text-sm font-semibold text-white">Hızlı yapı kur</p>
            <p className="mt-1 text-xs text-slate-500">Önce suite, sonra suite altında folder oluştur. Case yazımında bu yapı seçilecek.</p>
          </div>
          <div className="space-y-2">
            <input
              value={suiteName}
              onChange={(event) => setSuiteName(event.target.value)}
              placeholder="Suite adı: Web Checkout Suite"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
            />
            <button
              type="button"
              onClick={createQuickSuite}
              disabled={!suiteName.trim() || createSuite.isPending}
              className="w-full rounded-lg bg-teal-600 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
            >
              {createSuite.isPending ? "Suite oluşturuluyor..." : "Suite Oluştur"}
            </button>
          </div>
          <div className="space-y-2 border-t border-slate-800 pt-3">
            <select
              value={folderSuiteId}
              onChange={(event) => setFolderSuiteId(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
            >
              <option value="">Suite seç</option>
              {suites.map((suite) => <option key={suite.id} value={suite.id}>{suite.name}</option>)}
            </select>
            <input
              value={folderName}
              onChange={(event) => setFolderName(event.target.value)}
              placeholder="Folder adı: Login / Payment / API"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
            />
            <button
              type="button"
              onClick={createQuickFolder}
              disabled={!folderName.trim() || !(folderSuiteId || suites[0]?.id) || createFolder.isPending}
              className="w-full rounded-lg border border-teal-500/40 px-3 py-2 text-sm font-semibold text-teal-100 hover:bg-teal-500/10 disabled:opacity-40"
            >
              {createFolder.isPending ? "Folder oluşturuluyor..." : "Folder Oluştur"}
            </button>
          </div>
          {message && <p className="text-xs text-teal-200">{message}</p>}
          <div className="grid grid-cols-3 gap-2 pt-2">
            <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
              <p className="text-xs text-slate-500">Suite</p>
              <p className="mt-1 text-xl font-bold text-white">{suites.length}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
              <p className="text-xs text-slate-500">Folder</p>
              <p className="mt-1 text-xl font-bold text-white">{folders.length}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
              <p className="text-xs text-slate-500">Case</p>
              <p className="mt-1 text-xl font-bold text-white">{cases.length}</p>
            </div>
          </div>
        </div>

        <div className="grid max-h-[520px] gap-3 overflow-y-auto pr-1 lg:grid-cols-2">
          {repoQuery.isLoading ? (
            <div className="col-span-full flex h-40 items-center justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
            </div>
          ) : suites.length === 0 ? (
            <div className="col-span-full rounded-xl border border-dashed border-slate-800 px-4 py-12 text-center text-sm text-slate-500">
              Henüz suite yok. İlk suite'i oluşturarak repository ağacını başlat.
            </div>
          ) : suites.map((suite) => (
            <SuiteTreeCard key={suite.id} suite={suite} folders={folders} cases={cases} />
          ))}
        </div>
      </div>
    </ManagementPanel>
  );
}

function RegressionSetCommandPanel({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const regressionSets = useRegressionSets(projectId);
  const createSet = useCreateRegressionSet(projectId);
  const suites = repoQuery.data?.suites ?? [];
  const folders = repoQuery.data?.folders ?? [];
  const sets = regressionSets.data ?? [];
  const [name, setName] = useState(`Regression ${new Date().toLocaleDateString("tr-TR")}`);
  const [suiteId, setSuiteId] = useState("");
  const [folderId, setFolderId] = useState("");
  const [setType, setSetType] = useState("regression");
  const [includeLastFailed, setIncludeLastFailed] = useState(true);
  const [includeNotRun, setIncludeNotRun] = useState(true);
  const [message, setMessage] = useState("");
  const visibleFolders = folders.filter((folder) => !suiteId || folder.suite_id === suiteId);

  const createRegressionSet = async () => {
    if (!name.trim()) return;
    const created = await createSet.mutateAsync({
      name: name.trim(),
      set_type: setType,
      description: `${setType} set created from repository command center`,
      filters: {
        suite_ids: suiteId ? [suiteId] : undefined,
        folder_ids: folderId ? [folderId] : undefined,
        include_last_failed: includeLastFailed,
        include_not_run: includeNotRun,
        max_cases: 80,
      },
    });
    setMessage(`${created.name} oluşturuldu.`);
  };

  return (
    <ManagementPanel title="Regresyon / Smoke Seti">
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-3">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Set adı"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-1">
            <select value={setType} onChange={(event) => setSetType(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="regression">Regression Set</option>
              <option value="smoke">Smoke Set</option>
              <option value="release">Release Set</option>
            </select>
            <select value={suiteId} onChange={(event) => { setSuiteId(event.target.value); setFolderId(""); }} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Tüm suite'ler</option>
              {suites.map((suite) => <option key={suite.id} value={suite.id}>{suite.name}</option>)}
            </select>
            <select value={folderId} onChange={(event) => setFolderId(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Tüm folder'lar</option>
              {visibleFolders.map((folder) => <option key={folder.id} value={folder.id}>{folder.path}</option>)}
            </select>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs text-slate-300">
              <input type="checkbox" checked={includeLastFailed} onChange={(event) => setIncludeLastFailed(event.target.checked)} className="h-4 w-4 accent-teal-500" />
              Son başarısızları dahil et
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs text-slate-300">
              <input type="checkbox" checked={includeNotRun} onChange={(event) => setIncludeNotRun(event.target.checked)} className="h-4 w-4 accent-teal-500" />
              Koşulmamışları dahil et
            </label>
          </div>
          <button
            type="button"
            onClick={createRegressionSet}
            disabled={!name.trim() || createSet.isPending}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            {createSet.isPending ? "Set oluşturuluyor..." : "Set Oluştur"}
          </button>
          {message && <p className="text-xs text-indigo-200">{message}</p>}
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-white">Kayıtlı setler</p>
            <span className="rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-400">{sets.length}</span>
          </div>
          <div className="space-y-2">
            {sets.slice(0, 5).map((set: RegressionSet) => (
              <div key={set.id} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-semibold text-slate-100">{set.name}</p>
                  <span className="ml-auto rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">{set.cases.length} case</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{set.set_type}</p>
              </div>
            ))}
            {sets.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-800 px-3 py-10 text-center text-xs text-slate-500">
                Henüz regresyon seti yok.
              </div>
            )}
          </div>
        </div>
      </div>
    </ManagementPanel>
  );
}

// ── Repository table ──────────────────────────────────────────────────────────

function RepositoryTable({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const cases = repoQuery.data?.cases ?? [];
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [lastRunFilter, setLastRunFilter] = useState("all");
  const [sortBy, setSortBy] = useState("updated");

  const types = useMemo(() => Array.from(new Set(cases.map((item) => item.type))).sort(), [cases]);
  const filteredCases = useMemo(() => {
    const search = query.trim().toLowerCase();
    const rows = cases.filter((item) => {
      const matchesSearch = !search
        || item.case_key.toLowerCase().includes(search)
        || item.title.toLowerCase().includes(search)
        || item.tags.some((tag) => tag.toLowerCase().includes(search));
      const matchesStatus = statusFilter === "all" || item.status === statusFilter;
      const matchesType = typeFilter === "all" || item.type === typeFilter;
      const matchesLastRun = lastRunFilter === "all"
        || (lastRunFilter === "never" ? !item.last_run_status : item.last_run_status === lastRunFilter);
      return matchesSearch && matchesStatus && matchesType && matchesLastRun;
    });
    return [...rows].sort((left, right) => {
      if (sortBy === "priority") return String(left.priority).localeCompare(String(right.priority));
      if (sortBy === "last_run") return String(right.last_run_at ?? "").localeCompare(String(left.last_run_at ?? ""));
      if (sortBy === "key") return left.case_key.localeCompare(right.case_key);
      return String(right.updated_at ?? "").localeCompare(String(left.updated_at ?? ""));
    });
  }, [cases, lastRunFilter, query, sortBy, statusFilter, typeFilter]);

  if (repoQuery.isLoading) {
    return (
      <div className="flex h-24 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
      </div>
    );
  }

  const STATUS_CHIP: Record<string, string> = {
    active: "bg-emerald-500/15 text-emerald-400",
    draft: "bg-slate-700 text-slate-400",
    archived: "bg-slate-800 text-slate-500",
  };

  return (
    <div className="space-y-3">
      <div className="grid gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3 lg:grid-cols-[1.4fr_0.8fr_0.8fr_0.8fr_0.8fr]">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Key, başlık veya tag ara"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
        />
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
          <option value="all">Tüm durumlar</option>
          <option value="active">Active</option>
          <option value="draft">Draft</option>
          <option value="review">Review</option>
          <option value="deprecated">Deprecated</option>
        </select>
        <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
          <option value="all">Tüm türler</option>
          {types.map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
        <select value={lastRunFilter} onChange={(event) => setLastRunFilter(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
          <option value="all">Son koşu: tümü</option>
          <option value="never">Hiç koşulmadı</option>
          <option value="passed">Passed</option>
          <option value="failed">Failed</option>
          <option value="blocked">Blocked</option>
        </select>
        <select value={sortBy} onChange={(event) => setSortBy(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
          <option value="updated">Sırala: güncel</option>
          <option value="priority">Sırala: priority</option>
          <option value="last_run">Sırala: son koşu</option>
          <option value="key">Sırala: key</option>
        </select>
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded-full bg-slate-800 px-2 py-1">{filteredCases.length}/{cases.length} case gösteriliyor</span>
        <span className="rounded-full bg-rose-500/10 px-2 py-1 text-rose-200">{filteredCases.filter((item) => item.last_run_status === "failed").length} failed</span>
        <span className="rounded-full bg-amber-500/10 px-2 py-1 text-amber-200">{filteredCases.filter((item) => item.last_run_status === "blocked").length} blocked</span>
        <span className="rounded-full bg-slate-800 px-2 py-1">{filteredCases.filter((item) => !item.last_run_status).length} never run</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-950 text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left">Key</th>
              <th className="px-3 py-2 text-left">Başlık</th>
              <th className="px-3 py-2 text-left">Tür</th>
              <th className="px-3 py-2 text-left">Priority</th>
              <th className="px-3 py-2 text-left">Durum</th>
              <th className="px-3 py-2 text-left">Son Koşu</th>
              <th className="px-3 py-2 text-left">Tags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {filteredCases.slice(0, 100).map((c) => (
              <tr key={c.id} className="hover:bg-slate-900/40">
                <td className="px-3 py-2.5 font-mono text-xs text-slate-400">{c.case_key}</td>
                <td className="max-w-sm px-3 py-2.5 truncate text-slate-200">
                  <a href={`/p/${projectId}/management/cases/${c.id}`} className="hover:text-teal-300">
                    {c.title}
                  </a>
                </td>
                <td className="px-3 py-2.5 text-xs text-slate-400">{c.type}</td>
                <td className="px-3 py-2.5 text-xs text-slate-400">{c.priority}</td>
                <td className="px-3 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${STATUS_CHIP[c.status] ?? "bg-slate-700 text-slate-400"}`}
                  >
                    {c.status}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-xs text-slate-400">
                  {c.last_run_status ?? "—"}
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex max-w-xs flex-wrap gap-1">
                    {c.tags.slice(0, 3).map((tag) => <span key={tag} className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">{tag}</span>)}
                  </div>
                </td>
              </tr>
            ))}
            {filteredCases.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-sm text-slate-500">
                  Filtreye uyan test senaryosu yok.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RepositoryStructurePanel({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const createSuite = useCreateManagementSuite(projectId);
  const createFolder = useCreateManagementFolder(projectId);
  const [suiteName, setSuiteName] = useState("");
  const [suiteDescription, setSuiteDescription] = useState("");
  const [folderName, setFolderName] = useState("");
  const [folderSuiteId, setFolderSuiteId] = useState("");
  const suites = repoQuery.data?.suites ?? [];
  const folders = repoQuery.data?.folders ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ManagementPanel title="Suite Oluştur">
        <form
          className="space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            if (!suiteName.trim()) return;
            await createSuite.mutateAsync({
              name: suiteName.trim(),
              description: suiteDescription.trim(),
            });
            setSuiteName("");
            setSuiteDescription("");
          }}
        >
          <input
            value={suiteName}
            onChange={(event) => setSuiteName(event.target.value)}
            placeholder="Suite adı"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <input
            value={suiteDescription}
            onChange={(event) => setSuiteDescription(event.target.value)}
            placeholder="Açıklama"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <button
            disabled={createSuite.isPending || !suiteName.trim()}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
          >
            {createSuite.isPending ? "Oluşturuluyor..." : "Suite Oluştur"}
          </button>
        </form>
      </ManagementPanel>

      <ManagementPanel title="Folder Oluştur">
        <form
          className="space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            const suiteId = folderSuiteId || suites[0]?.id;
            if (!suiteId || !folderName.trim()) return;
            const name = folderName.trim();
            await createFolder.mutateAsync({
              suite_id: suiteId,
              name,
              path: `/${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || name}`,
            });
            setFolderName("");
          }}
        >
          <select
            value={folderSuiteId}
            onChange={(event) => setFolderSuiteId(event.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
          >
            <option value="">Suite seç</option>
            {suites.map((suite) => (
              <option key={suite.id} value={suite.id}>{suite.name}</option>
            ))}
          </select>
          <input
            value={folderName}
            onChange={(event) => setFolderName(event.target.value)}
            placeholder="Folder adı"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
          />
          <button
            disabled={createFolder.isPending || !folderName.trim() || !(folderSuiteId || suites[0]?.id)}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
          >
            {createFolder.isPending ? "Oluşturuluyor..." : "Folder Oluştur"}
          </button>
        </form>
        <div className="mt-4 space-y-2">
          {folders.slice(0, 6).map((folder) => (
            <div key={folder.id} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300">
              {folder.path}
            </div>
          ))}
        </div>
      </ManagementPanel>
    </div>
  );
}

type RepositorySelection =
  | { kind: "inbox"; id: typeof INBOX_FOLDER_ID }
  | { kind: "suite"; id: string }
  | { kind: "folder"; id: string };

function RepositoryWorkspace({ projectId }: { projectId: string }) {
  const repoQuery = useManagementRepository(projectId);
  const createSuite = useCreateManagementSuite(projectId);
  const createFolder = useCreateManagementFolder(projectId);
  const createCase = useCreateManagementCase(projectId);
  const createSet = useCreateRegressionSet(projectId);
  const regressionSets = useRegressionSets(projectId);
  const suites = repoQuery.data?.suites ?? [];
  const folders = repoQuery.data?.folders ?? [];
  const cases = repoQuery.data?.cases ?? [];
  const [selection, setSelection] = useState<RepositorySelection>({ kind: "inbox", id: INBOX_FOLDER_ID });
  const [selectedCaseIds, setSelectedCaseIds] = useState<Set<string>>(new Set());
  const [suiteName, setSuiteName] = useState("");
  const [folderName, setFolderName] = useState("");
  const [caseTitle, setCaseTitle] = useState("");
  const [setName, setSetName] = useState(`Regression ${new Date().toLocaleDateString("tr-TR")}`);
  const [message, setMessage] = useState("");

  const selectedSuite = selection.kind === "suite"
    ? suites.find((suite) => suite.id === selection.id)
    : selection.kind === "folder"
      ? suites.find((suite) => suite.id === folders.find((folder) => folder.id === selection.id)?.suite_id)
      : null;
  const selectedFolder = selection.kind === "folder" ? folders.find((folder) => folder.id === selection.id) : null;
  const selectedSuiteId = selectedSuite?.id ?? "";
  const selectedFolderId = selectedFolder?.id ?? "";

  const visibleCases = useMemo(() => {
    if (selection.kind === "inbox") return cases.filter((testCase) => !testCase.folder_id && !testCase.archived);
    if (selection.kind === "suite") return cases.filter((testCase) => testCase.suite_id === selection.id && !testCase.archived);
    return cases.filter((testCase) => testCase.folder_id === selection.id && !testCase.archived);
  }, [cases, selection]);

  const activeCount = visibleCases.filter((testCase) => testCase.status === "active").length;
  const failedCount = visibleCases.filter((testCase) => testCase.last_run_status === "failed").length;
  const notRunCount = visibleCases.filter((testCase) => !testCase.last_run_status).length;
  const selectedCases = visibleCases.filter((testCase) => selectedCaseIds.has(testCase.id));

  const selectNode = (next: RepositorySelection) => {
    setSelection(next);
    setSelectedCaseIds(new Set());
    setMessage("");
  };

  const toggleCase = (caseId: string) => {
    setSelectedCaseIds((current) => {
      const next = new Set(current);
      if (next.has(caseId)) next.delete(caseId);
      else next.add(caseId);
      return next;
    });
  };

  const createQuickSuite = async () => {
    if (!suiteName.trim()) return;
    const created = await createSuite.mutateAsync({ name: suiteName.trim(), description: "Repository suite" });
    setSuiteName("");
    setSelection({ kind: "suite", id: created.id });
    setMessage(`${created.name} suite oluşturuldu.`);
  };

  const createQuickFolder = async () => {
    const suiteId = selectedSuiteId || suites[0]?.id;
    if (!suiteId || !folderName.trim()) return;
    const created = await createFolder.mutateAsync({
      suite_id: suiteId,
      name: folderName.trim(),
      path: slugifyFolderPath(folderName.trim()),
    });
    setFolderName("");
    setSelection({ kind: "folder", id: created.id });
    setMessage(`${created.path} folder oluşturuldu.`);
  };

  const createQuickCase = async () => {
    if (!caseTitle.trim()) return;
    const created = await createCase.mutateAsync({
      title: caseTitle.trim(),
      objective: null,
      preconditions: null,
      suite_id: selectedSuiteId || null,
      folder_id: selectedFolderId || null,
      priority: "P1",
      severity: "major",
      type: "manual",
      status: "draft",
      source_type: "manual",
      tags: selection.kind === "inbox" ? ["inbox"] : ["manual"],
      steps: [
        {
          step_no: 1,
          action: "Kullanıcı akışı başlatır.",
          expected_result: "Ekran beklenen şekilde açılır.",
          test_data: {},
          is_required: true,
        },
      ],
    });
    setCaseTitle("");
    setMessage(`${created.case_key} case oluşturuldu.`);
  };

  const createSetFromSelection = async () => {
    if (!setName.trim() || selectedCases.length === 0) return;
    const created = await createSet.mutateAsync({
      name: setName.trim(),
      set_type: "regression",
      description: "Repository workspace seçiminden oluşturuldu.",
      cases: selectedCases.map((testCase, index) => ({
        case_id: testCase.id,
        order_index: index + 1,
        risk_score: testCase.priority === "P0" ? 90 : testCase.priority === "P1" ? 70 : 40,
        reason: "Seçili repository case",
        include_mode: "manual",
      })),
    });
    setSelectedCaseIds(new Set());
    setMessage(`${created.name} set oluşturuldu.`);
  };

  return (
    <div className="grid min-h-[650px] gap-4 xl:grid-cols-[300px_minmax(0,1fr)_340px]" data-testid="repository-workspace">
      <aside className="rounded-xl border border-slate-800 bg-slate-950/55">
        <div className="border-b border-slate-800 px-4 py-3">
          <p className="text-sm font-semibold text-white">Repository</p>
          <p className="mt-1 text-xs text-slate-500">Suite ve folder seç, sadece o kapsamdaki case'leri yönet.</p>
        </div>
        <div className="space-y-2 p-3">
          <button
            type="button"
            onClick={() => selectNode({ kind: "inbox", id: INBOX_FOLDER_ID })}
            className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${
              selection.kind === "inbox" ? "bg-teal-500/15 text-teal-100" : "text-slate-300 hover:bg-slate-900"
            }`}
          >
            <span className="flex h-6 w-6 items-center justify-center rounded bg-slate-800 text-xs">I</span>
            <span className="min-w-0 flex-1 truncate">Inbox</span>
            <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
              {cases.filter((testCase) => !testCase.folder_id && !testCase.archived).length}
            </span>
          </button>
          {suites.map((suite) => {
            const suiteFolders = folders.filter((folder) => folder.suite_id === suite.id);
            const suiteCases = cases.filter((testCase) => testCase.suite_id === suite.id && !testCase.archived);
            return (
              <div key={suite.id} className="rounded-lg border border-slate-800 bg-slate-950/70">
                <button
                  type="button"
                  onClick={() => selectNode({ kind: "suite", id: suite.id })}
                  className={`flex w-full items-center gap-2 rounded-t-lg px-3 py-2 text-left text-sm ${
                    selection.kind === "suite" && selection.id === suite.id ? "bg-teal-500/15 text-teal-100" : "text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded bg-slate-800 text-xs">S</span>
                  <span className="min-w-0 flex-1 truncate">{suite.name}</span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">{suiteCases.length}</span>
                </button>
                <div className="space-y-1 border-t border-slate-800 p-2">
                  {suiteFolders.map((folder) => {
                    const folderCases = cases.filter((testCase) => testCase.folder_id === folder.id && !testCase.archived);
                    return (
                      <button
                        key={folder.id}
                        type="button"
                        onClick={() => selectNode({ kind: "folder", id: folder.id })}
                        className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs ${
                          selection.kind === "folder" && selection.id === folder.id ? "bg-blue-500/15 text-blue-100" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                        }`}
                      >
                        <span className="text-slate-600">-</span>
                        <span className="min-w-0 flex-1 truncate">{folder.path || folder.name}</span>
                        <span>{folderCases.length}</span>
                      </button>
                    );
                  })}
                  {suiteFolders.length === 0 && <p className="px-2 py-3 text-xs text-slate-600">Folder yok</p>}
                </div>
              </div>
            );
          })}
          {repoQuery.isLoading && (
            <div className="flex h-24 items-center justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
            </div>
          )}
        </div>
      </aside>

      <main className="rounded-xl border border-slate-800 bg-slate-950/45">
        <div className="border-b border-slate-800 px-4 py-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">
                {selection.kind === "inbox" ? "Inbox" : selection.kind === "suite" ? "Suite" : "Folder"}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-white">
                {selection.kind === "inbox" ? "Atanmamış Case'ler" : selectedFolder?.path || selectedSuite?.name || "Seçim"}
              </h2>
            </div>
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2">
                <p className="text-xs text-slate-500">Case</p>
                <p className="text-lg font-bold text-white">{visibleCases.length}</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2">
                <p className="text-xs text-slate-500">Aktif</p>
                <p className="text-lg font-bold text-emerald-200">{activeCount}</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2">
                <p className="text-xs text-slate-500">Failed</p>
                <p className="text-lg font-bold text-rose-200">{failedCount}</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2">
                <p className="text-xs text-slate-500">Not Run</p>
                <p className="text-lg font-bold text-slate-200">{notRunCount}</p>
              </div>
            </div>
          </div>
        </div>
        <div className="p-4">
          {visibleCases.length === 0 ? (
            <div className="flex min-h-[360px] items-center justify-center rounded-xl border border-dashed border-slate-800 text-center">
              <div>
                <p className="text-sm font-semibold text-white">Bu alanda case yok</p>
                <p className="mt-1 text-xs text-slate-500">Sağ panelden hızlı case oluşturabilir veya case'leri folder board ile taşıyabilirsin.</p>
              </div>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-slate-800">
              <table className="w-full text-sm">
                <thead className="bg-slate-950 text-xs text-slate-500">
                  <tr>
                    <th className="w-10 px-3 py-2 text-left"></th>
                    <th className="px-3 py-2 text-left">Key</th>
                    <th className="px-3 py-2 text-left">Case</th>
                    <th className="px-3 py-2 text-left">Priority</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-left">Last Run</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {visibleCases.map((testCase) => (
                    <tr key={testCase.id} className="hover:bg-slate-900/55">
                      <td className="px-3 py-3">
                        <input
                          type="checkbox"
                          checked={selectedCaseIds.has(testCase.id)}
                          onChange={() => toggleCase(testCase.id)}
                          className="h-4 w-4 rounded border-slate-700 bg-slate-950 accent-teal-500"
                        />
                      </td>
                      <td className="px-3 py-3 font-mono text-xs text-slate-500">{testCase.case_key}</td>
                      <td className="max-w-xl px-3 py-3">
                        <a href={`/p/${projectId}/management/cases/${testCase.id}`} className="font-medium text-slate-100 hover:text-teal-300">
                          {testCase.title}
                        </a>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {testCase.tags.slice(0, 3).map((tag) => (
                            <span key={tag} className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-500">{tag}</span>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-3 text-xs text-slate-400">{testCase.priority}</td>
                      <td className="px-3 py-3 text-xs text-slate-400">{testCase.status}</td>
                      <td className="px-3 py-3 text-xs text-slate-400">{testCase.last_run_status ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      <aside className="space-y-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/55 p-4">
          <p className="text-sm font-semibold text-white">Hızlı Aksiyonlar</p>
          <p className="mt-1 text-xs text-slate-500">Seçili suite/folder bağlamına göre oluştur.</p>
          <div className="mt-4 space-y-2">
            <input
              value={suiteName}
              onChange={(event) => setSuiteName(event.target.value)}
              placeholder="Yeni suite"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
            />
            <button
              type="button"
              onClick={createQuickSuite}
              disabled={!suiteName.trim() || createSuite.isPending}
              className="w-full rounded-lg bg-teal-600 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-40"
            >
              Suite Oluştur
            </button>
          </div>
          <div className="mt-4 space-y-2 border-t border-slate-800 pt-4">
            <input
              value={folderName}
              onChange={(event) => setFolderName(event.target.value)}
              placeholder={selectedSuite ? `${selectedSuite.name} altında folder` : "Yeni folder"}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
            />
            <button
              type="button"
              onClick={createQuickFolder}
              disabled={!folderName.trim() || !(selectedSuiteId || suites[0]?.id) || createFolder.isPending}
              className="w-full rounded-lg border border-teal-500/40 px-3 py-2 text-sm font-semibold text-teal-100 hover:bg-teal-500/10 disabled:opacity-40"
            >
              Folder Oluştur
            </button>
          </div>
          <div className="mt-4 space-y-2 border-t border-slate-800 pt-4">
            <input
              value={caseTitle}
              onChange={(event) => setCaseTitle(event.target.value)}
              placeholder="Yeni case başlığı"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500/50 focus:outline-none"
            />
            <button
              type="button"
              onClick={createQuickCase}
              disabled={!caseTitle.trim() || createCase.isPending}
              className="w-full rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-40"
            >
              Case Oluştur
            </button>
          </div>
          {message && <p className="mt-3 rounded-lg border border-teal-500/20 bg-teal-500/10 px-3 py-2 text-xs text-teal-100">{message}</p>}
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/55 p-4">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-white">Regresyon Seti</p>
            <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">{selectedCaseIds.size} seçili</span>
          </div>
          <input
            value={setName}
            onChange={(event) => setSetName(event.target.value)}
            placeholder="Set adı"
            className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500/50 focus:outline-none"
          />
          <button
            type="button"
            onClick={createSetFromSelection}
            disabled={selectedCaseIds.size === 0 || !setName.trim() || createSet.isPending}
            className="mt-2 w-full rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            Seçilenlerden Set Oluştur
          </button>
          <div className="mt-3 space-y-2">
            {(regressionSets.data ?? []).slice(0, 3).map((set: RegressionSet) => (
              <div key={set.id} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2">
                <p className="truncate text-xs font-semibold text-slate-200">{set.name}</p>
                <p className="mt-1 text-xs text-slate-500">{set.cases.length} case</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/55 p-4">
          <p className="text-sm font-semibold text-white">İleri Araçlar</p>
          <div className="mt-3 grid gap-2">
            <a href={`/p/${projectId}/management/regression`} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-slate-500">Regression Builder</a>
            <a href={`/p/${projectId}/management/plans`} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-slate-500">Test Plans</a>
            <a href={`/p/${projectId}/management/runs`} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-slate-500">Test Runs</a>
          </div>
        </div>
      </aside>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ManagementRepositoryPage({
  params,
}: {
  params: { projectId: string };
}) {
  const { projectId } = params;
  const repoQuery = useManagementRepository(projectId);

  const totalCases = repoQuery.data?.cases.length ?? 0;
  const totalSuites = repoQuery.data?.suites.length ?? 0;
  const activeCases = repoQuery.data?.cases.filter((c) => c.status === "active").length ?? 0;

  return (
    <ManagementShell
      projectId={projectId}
      title="Test Repository"
      description="Suite, folder, manuel test case, step ve version kayıtlarının yönetildiği kalıcı test hafızası."
      active="management/repository"
    >
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat
          label="Suites"
          value={repoQuery.isLoading ? "…" : String(totalSuites)}
          note="test paketleri"
        />
        <ManagementStat
          label="Test Senaryosu"
          value={repoQuery.isLoading ? "…" : String(totalCases)}
          note={`${activeCases} aktif`}
        />
        <ManagementStat
          label="Toplam Adım"
          value={repoQuery.isLoading ? "…" : String(
            repoQuery.data?.cases.reduce((sum, c) => sum + (c.steps?.length ?? 0), 0) ?? 0,
          )}
          note="tüm senaryolarda"
        />
      </div>

      <div className="mt-6">
        <RepositoryWorkspace projectId={projectId} />
      </div>
    </ManagementShell>
  );
}
