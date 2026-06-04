"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  useCreateManagementSuite,
  useCreateManagementFolder,
  useCreateManagementPlan,
  useCreateManagementCycle,
  useCreateManagementRun,
  useManagementRepository,
  useManagementPlans,
  useManagementCycles,
  type TestSuite,
  type TestFolder,
  type TestPlan,
  type TestCycle,
} from "@/lib/hooks/use-management";

// ─── Types ────────────────────────────────────────────────────────────────────

type WizardStep = "suite" | "folder" | "plan" | "cycle" | "run" | "done";

interface FolderDraft {
  id: string;
  name: string;
  parentId: string | null;
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function IcSuite()  { return <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/></svg>; }
function IcFolder() { return <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}><path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>; }
function IcPlan()   { return <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>; }
function IcCycle()  { return <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}><path strokeLinecap="round" strokeLinejoin="round" d="M1 4v6h6M23 20v-6h-6"/><path strokeLinecap="round" strokeLinejoin="round" d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/></svg>; }
function IcPlay()   { return <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}><circle cx="12" cy="12" r="9"/><path strokeLinecap="round" strokeLinejoin="round" d="M10 8l6 4-6 4V8z"/></svg>; }
function IcCheck()  { return <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>; }
function IcPlus()   { return <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>; }
function IcTrash()  { return <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>; }

// ─── Step Config ──────────────────────────────────────────────────────────────

const STEPS: { id: WizardStep; label: string; Icon: () => JSX.Element; desc: string }[] = [
  { id: "suite",  label: "Test Suite",    Icon: IcSuite,  desc: "Test case'lerinizi gruplayacak suite oluşturun" },
  { id: "folder", label: "Klasör",        Icon: IcFolder, desc: "Suite içinde klasör hiyerarşisi kurun" },
  { id: "plan",   label: "Test Planı",    Icon: IcPlan,   desc: "Hangi testlerin ne zaman çalışacağını planlayın" },
  { id: "cycle",  label: "Test Döngüsü",  Icon: IcCycle,  desc: "Plana bağlı test cycle'ı oluşturun" },
  { id: "run",    label: "Run Başlat",    Icon: IcPlay,   desc: "Cycle üzerinden test koşumunu başlatın" },
];

// ─── Step Indicator ───────────────────────────────────────────────────────────

function StepIndicator({ current, done }: { current: WizardStep; done: Set<WizardStep> }) {
  const idx = STEPS.findIndex(s => s.id === current);
  return (
    <div className="flex items-center gap-0">
      {STEPS.map((step, i) => {
        const isDone    = done.has(step.id);
        const isActive  = step.id === current;
        const isReached = i <= idx;
        return (
          <div key={step.id} className="flex items-center">
            <div className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-[12px] font-semibold transition-all",
              isDone
                ? "border-emerald-500 bg-emerald-500 text-white"
                : isActive
                  ? "border-brand bg-brand text-brand-fg shadow-sm shadow-brand/20"
                  : isReached
                    ? "border-brand/40 bg-brand-soft text-brand"
                    : "border-border bg-surface-overlay text-fg-subtle",
            )}>
              {isDone ? <IcCheck/> : <span>{i + 1}</span>}
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn(
                "h-0.5 w-10 transition-all",
                i < idx ? "bg-brand" : "bg-border",
              )}/>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Tree Preview ─────────────────────────────────────────────────────────────

function TreePreview({
  suite, folders, planName, cycleName,
}: {
  suite: string; folders: FolderDraft[]; planName: string; cycleName: string;
}) {
  if (!suite) return null;
  return (
    <div className="rounded-xl border border-border bg-surface-raised p-4 font-mono text-[12px]">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Oluşturulacak Yapı</p>
      <div className="space-y-1">
        {/* Suite */}
        <div className="flex items-center gap-2 text-brand">
          <IcSuite/>
          <span className="font-semibold">{suite}</span>
          <span className="text-[10px] text-fg-subtle">(suite)</span>
        </div>
        {/* Folders */}
        {folders.map(f => (
          <div key={f.id} className="flex items-center gap-2 pl-6 text-fg-muted">
            <span className="text-fg-subtle">└─</span>
            <IcFolder/>
            <span>{f.name}</span>
            {f.parentId && (
              <span className="text-[10px] text-fg-subtle">
                (alt: {folders.find(x => x.id === f.parentId)?.name ?? "?"})
              </span>
            )}
          </div>
        ))}
        {/* Plan */}
        {planName && (
          <div className="mt-2 flex items-center gap-2 text-violet-400">
            <IcPlan/>
            <span className="font-semibold">{planName}</span>
            <span className="text-[10px] text-fg-subtle">(plan)</span>
          </div>
        )}
        {/* Cycle */}
        {cycleName && (
          <div className="flex items-center gap-2 pl-6 text-cyan-400">
            <span className="text-fg-subtle">└─</span>
            <IcCycle/>
            <span>{cycleName}</span>
            <span className="text-[10px] text-fg-subtle">(cycle)</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Wizard ─────────────────────────────────────────────────────────────

export function QuickSetupWizard({ projectId, mpid }: { projectId: string; mpid: string }) {
  const router = useRouter();

  // Hooks
  const createSuite  = useCreateManagementSuite(mpid);
  const createFolder = useCreateManagementFolder(mpid);
  const createPlan   = useCreateManagementPlan(mpid);
  const createCycle  = useCreateManagementCycle(mpid);
  const createRun    = useCreateManagementRun(mpid);
  const repoQ        = useManagementRepository(mpid || undefined);
  const plansQ       = useManagementPlans(mpid || undefined);
  const cyclesQ      = useManagementCycles(mpid || undefined);

  // Wizard state
  const [step,      setStep]      = useState<WizardStep>("suite");
  const [done,      setDone]      = useState<Set<WizardStep>>(new Set());
  const [busy,      setBusy]      = useState(false);
  const [error,     setError]     = useState("");

  // Step data
  const [suiteName,    setSuiteName]    = useState("");
  const [createdSuite, setCreatedSuite] = useState<TestSuite | null>(null);
  const [folders,      setFolders]      = useState<FolderDraft[]>([]);
  const [newFolder,    setNewFolder]    = useState("");
  const [folderParent, setFolderParent] = useState<string>("root");
  const [planName,     setPlanName]     = useState("");
  const [planType,     setPlanType]     = useState("regression");
  const [releaseTag,   setReleaseTag]   = useState("");
  const [createdPlan,  setCreatedPlan]  = useState<TestPlan | null>(null);
  const [cycleName,    setCycleName]    = useState("");
  const [cycleEnv,     setCycleEnv]     = useState("");
  const [createdCycle, setCreatedCycle] = useState<TestCycle | null>(null);
  const [runName,      setRunName]      = useState("");

  const markDone = (s: WizardStep) => setDone(p => new Set([...p, s]));

  // ── Step 1: Suite ──────────────────────────────────────────────────────────

  const handleCreateSuite = async () => {
    if (!suiteName.trim()) return;
    setBusy(true); setError("");
    try {
      const s = await createSuite.mutateAsync({ name: suiteName.trim() });
      setCreatedSuite(s);
      markDone("suite");
      setStep("folder");
    } catch { setError("Suite oluşturulamadı."); }
    finally { setBusy(false); }
  };

  // ── Step 2: Folders ────────────────────────────────────────────────────────

  const addFolderDraft = () => {
    if (!newFolder.trim()) return;
    setFolders(p => [...p, {
      id: `f-${Math.random().toString(36).slice(2, 7)}`,
      name: newFolder.trim(),
      parentId: folderParent === "root" ? null : folderParent,
    }]);
    setNewFolder("");
  };

  const handleCreateFolders = async () => {
    if (!createdSuite) return;
    setBusy(true); setError("");
    try {
      for (const f of folders) {
        await createFolder.mutateAsync({
          suite_id: createdSuite.id,
          name: f.name,
          path: `/${f.name.toLowerCase().replace(/\s+/g, "-")}`,
          parent_id: null, // flat hierarchy for simplicity
        });
      }
      markDone("folder");
      setStep("plan");
    } catch { setError("Klasör oluşturulamadı."); }
    finally { setBusy(false); }
  };

  // ── Step 3: Plan ───────────────────────────────────────────────────────────

  const handleCreatePlan = async () => {
    if (!planName.trim()) return;
    setBusy(true); setError("");
    try {
      const p = await createPlan.mutateAsync({
        name: planName.trim(),
        plan_type: planType,
        release_name: releaseTag.trim() || null,
      });
      setCreatedPlan(p);
      markDone("plan");
      setStep("cycle");
    } catch { setError("Plan oluşturulamadı."); }
    finally { setBusy(false); }
  };

  // ── Step 4: Cycle ──────────────────────────────────────────────────────────

  const handleCreateCycle = async () => {
    if (!createdPlan || !cycleName.trim()) return;
    setBusy(true); setError("");
    try {
      const c = await createCycle.mutateAsync({
        plan_id: createdPlan.id,
        name: cycleName.trim(),
        environment: cycleEnv.trim() || null,
      });
      setCreatedCycle(c);
      markDone("cycle");
      setStep("run");
    } catch { setError("Cycle oluşturulamadı."); }
    finally { setBusy(false); }
  };

  // ── Step 5: Run ────────────────────────────────────────────────────────────

  const handleStartRun = async () => {
    if (!createdCycle || !runName.trim()) return;
    setBusy(true); setError("");
    try {
      const run = await createRun.mutateAsync({
        cycle_id: createdCycle.id,
        name: runName.trim(),
        case_ids: [],
      });
      markDone("run");
      setStep("done");
      router.push(`/p/${projectId}/management/runs/${run.id}/execute`);
    } catch { setError("Run başlatılamadı."); }
    finally { setBusy(false); }
  };

  // ─── Render ─────────────────────────────────────────────────────────────────

  const currentIdx = STEPS.findIndex(s => s.id === step);

  const INP = "w-full rounded-xl border border-border bg-surface-base px-3 py-2.5 text-[13px] text-fg placeholder-fg-subtle outline-none transition-colors focus:border-brand/50";
  const SEL = "w-full rounded-xl border border-border bg-surface-base px-3 py-2.5 text-[13px] text-fg outline-none focus:border-brand/50";

  return (
    <div className="rounded-2xl border border-border bg-surface-raised shadow-sm overflow-hidden">

      {/* Header */}
      <div className="border-b border-border bg-surface-base px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-brand">Hızlı Kurulum</p>
            <h2 className="mt-1 text-[18px] font-semibold text-fg">Test yapısını oluştur</h2>
            <p className="mt-0.5 text-[12px] text-fg-muted">
              Suite → Klasör → Plan → Döngü → Run — adım adım ilerleyin
            </p>
          </div>
          <StepIndicator current={step} done={done}/>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-0 lg:grid-cols-3">

        {/* Left: Step list */}
        <div className="border-b border-border bg-surface-raised p-4 lg:border-b-0 lg:border-r">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Adımlar</p>
          <div className="space-y-1">
            {STEPS.map((s, i) => {
              const isDone   = done.has(s.id);
              const isActive = s.id === step;
              return (
                <button key={s.id} type="button"
                  onClick={() => { if (isDone || i <= currentIdx) setStep(s.id); }}
                  disabled={!isDone && i > currentIdx}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
                    isActive
                      ? "bg-brand-soft border border-brand/20 text-brand"
                      : isDone
                        ? "bg-emerald-500/5 border border-emerald-500/20 text-emerald-500 hover:bg-emerald-500/10"
                        : i <= currentIdx
                          ? "hover:bg-surface-overlay text-fg-muted"
                          : "opacity-40 cursor-not-allowed text-fg-subtle",
                  )}>
                  <span className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
                    isActive ? "bg-brand text-brand-fg"
                    : isDone ? "bg-emerald-500 text-white"
                    : "bg-surface-overlay text-fg-subtle",
                  )}>
                    {isDone ? <IcCheck/> : <s.Icon/>}
                  </span>
                  <div className="min-w-0">
                    <p className="text-[12px] font-semibold leading-tight">{s.label}</p>
                    <p className="mt-0.5 truncate text-[10px] opacity-70">{s.desc}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Active step form */}
        <div className="col-span-2 p-6">

          {step === "done" ? (
            /* Done state */
            <div className="flex flex-col items-center justify-center py-12 text-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-500">
                <IcCheck/>
              </div>
              <div>
                <h3 className="text-[16px] font-semibold text-fg">Yapı hazır!</h3>
                <p className="mt-1 text-[12px] text-fg-muted">Suite, klasörler, plan ve döngünüz oluşturuldu. Run başlatıldı.</p>
              </div>
              <div className="flex gap-2 mt-2">
                <button onClick={() => router.push(`/p/${projectId}/management/repository`)}
                  className="rounded-xl border border-border px-4 py-2 text-[12px] font-medium text-fg-muted hover:text-fg">
                  Repository'e Git
                </button>
                <button onClick={() => router.push(`/p/${projectId}/management/plans`)}
                  className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105">
                  Planları Gör
                </button>
              </div>
            </div>

          ) : (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

              {/* Form panel */}
              <div className="space-y-4">

                {/* STEP 1: Suite */}
                {step === "suite" && (
                  <div className="space-y-3">
                    <div>
                      <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Suite Adı *</label>
                      <input autoFocus value={suiteName} onChange={e => setSuiteName(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleCreateSuite()}
                        placeholder="örn. Login Testleri, Ödeme Akışı…"
                        className={INP}/>
                      <p className="mt-1.5 text-[11px] text-fg-subtle">
                        Suite, test case'lerinizi organize ettiğiniz ana gruptur.
                      </p>
                    </div>
                    {/* Existing suites */}
                    {(repoQ.data?.suites ?? []).length > 0 && (
                      <div className="rounded-xl border border-border bg-surface-base p-3">
                        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Mevcut Suite'ler</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(repoQ.data?.suites ?? []).map(s => (
                            <button key={s.id} type="button" onClick={() => { setCreatedSuite(s); markDone("suite"); setStep("folder"); }}
                              className="rounded-lg border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:border-brand/30 hover:text-brand transition-colors">
                              {s.name}
                            </button>
                          ))}
                        </div>
                        <p className="mt-2 text-[10px] text-fg-subtle">Mevcut bir suite'i seçerek devam edebilirsiniz.</p>
                      </div>
                    )}
                  </div>
                )}

                {/* STEP 2: Folders */}
                {step === "folder" && (
                  <div className="space-y-3">
                    <p className="text-[12px] text-fg-muted">
                      <span className="font-semibold text-brand">{createdSuite?.name}</span> suite'ine klasörler ekleyin.
                      Klasörler isteğe bağlıdır, atlayabilirsiniz.
                    </p>
                    <div className="flex gap-2">
                      <div className="flex-1 space-y-2">
                        <input value={newFolder} onChange={e => setNewFolder(e.target.value)}
                          onKeyDown={e => e.key === "Enter" && addFolderDraft()}
                          placeholder="Klasör adı…"
                          className={INP}/>
                        {folders.length > 0 && (
                          <div>
                            <label className="mb-1 block text-[11px] text-fg-subtle">Üst klasör (opsiyonel)</label>
                            <select value={folderParent} onChange={e => setFolderParent(e.target.value)} className={SEL}>
                              <option value="root">— Ana dizin</option>
                              {folders.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                            </select>
                          </div>
                        )}
                      </div>
                      <button type="button" onClick={addFolderDraft} disabled={!newFolder.trim()}
                        className="mt-0 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand text-brand-fg hover:brightness-105 disabled:opacity-40">
                        <IcPlus/>
                      </button>
                    </div>
                    {folders.length > 0 && (
                      <div className="rounded-xl border border-border bg-surface-base p-3 space-y-1.5">
                        {folders.map(f => (
                          <div key={f.id} className="flex items-center gap-2 rounded-lg px-2 py-1.5">
                            {f.parentId && <span className="text-fg-subtle text-[11px] pl-3">└─</span>}
                            <span className="flex h-5 w-5 items-center justify-center text-fg-subtle"><IcFolder/></span>
                            <span className="flex-1 text-[12px] text-fg">{f.name}</span>
                            {f.parentId && (
                              <span className="text-[10px] text-fg-subtle">
                                alt: {folders.find(x => x.id === f.parentId)?.name}
                              </span>
                            )}
                            <button onClick={() => setFolders(p => p.filter(x => x.id !== f.id))}
                              className="text-fg-subtle hover:text-red-400 transition-colors"><IcTrash/></button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* STEP 3: Plan */}
                {step === "plan" && (
                  <div className="space-y-3">
                    <p className="text-[12px] text-fg-muted">Testlerinizi organize edecek bir plan oluşturun.</p>
                    <div>
                      <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Plan Adı *</label>
                      <input autoFocus value={planName} onChange={e => setPlanName(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleCreatePlan()}
                        placeholder="örn. Sprint 1, Release 2.4, UAT…"
                        className={INP}/>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Plan Tipi</label>
                        <select value={planType} onChange={e => setPlanType(e.target.value)} className={SEL}>
                          <option value="regression">Regresyon</option>
                          <option value="sprint">Sprint</option>
                          <option value="release">Release</option>
                          <option value="smoke">Smoke</option>
                          <option value="uat">UAT</option>
                        </select>
                      </div>
                      <div>
                        <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Release Tag</label>
                        <input value={releaseTag} onChange={e => setReleaseTag(e.target.value)}
                          placeholder="v2.4.0 (opsiyonel)" className={INP}/>
                      </div>
                    </div>
                    {/* Existing plans shortcut */}
                    {(plansQ.data ?? []).length > 0 && (
                      <div className="rounded-xl border border-border bg-surface-base p-3">
                        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Mevcut Planlar</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(plansQ.data ?? []).slice(0, 5).map(p => (
                            <button key={p.id} type="button"
                              onClick={() => { setCreatedPlan(p); markDone("plan"); setStep("cycle"); }}
                              className="rounded-lg border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:border-brand/30 hover:text-brand transition-colors">
                              {p.name}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* STEP 4: Cycle */}
                {step === "cycle" && (
                  <div className="space-y-3">
                    <p className="text-[12px] text-fg-muted">
                      <span className="font-semibold text-brand">{createdPlan?.name}</span> planına bir test döngüsü bağlayın.
                    </p>
                    <div>
                      <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Döngü Adı *</label>
                      <input autoFocus value={cycleName} onChange={e => setCycleName(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleCreateCycle()}
                        placeholder="örn. Sprint 1 - Döngü 1, Staging Test…"
                        className={INP}/>
                    </div>
                    <div>
                      <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Test Ortamı</label>
                      <input value={cycleEnv} onChange={e => setCycleEnv(e.target.value)}
                        placeholder="staging, production, dev… (opsiyonel)"
                        className={INP}/>
                    </div>
                    {(cyclesQ.data ?? []).length > 0 && (
                      <div className="rounded-xl border border-border bg-surface-base p-3">
                        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Mevcut Döngüler</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(cyclesQ.data ?? []).slice(0, 5).map(c => (
                            <button key={c.id} type="button"
                              onClick={() => { setCreatedCycle(c); markDone("cycle"); setStep("run"); }}
                              className="rounded-lg border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:border-brand/30 hover:text-brand transition-colors">
                              {c.name}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* STEP 5: Run */}
                {step === "run" && (
                  <div className="space-y-3">
                    <p className="text-[12px] text-fg-muted">
                      <span className="font-semibold text-brand">{createdCycle?.name}</span> döngüsü için test koşumu başlatın.
                    </p>
                    <div>
                      <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Run Adı *</label>
                      <input autoFocus value={runName} onChange={e => setRunName(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleStartRun()}
                        placeholder="örn. Sprint 1 Run, Login Tests…"
                        className={INP}/>
                    </div>
                    <div className="rounded-xl border border-border bg-surface-base p-3">
                      <p className="text-[11px] text-fg-subtle">
                        Run başlatıldığında execute sayfasına yönlendirileceksiniz.
                        Test case'lerini repository'den ekleyebilirsiniz.
                      </p>
                    </div>
                  </div>
                )}

                {/* Error */}
                {error && (
                  <p className="rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-[12px] text-red-400">{error}</p>
                )}

                {/* Action buttons */}
                <div className="flex items-center gap-2 pt-2">
                  {step !== "suite" && (
                    <button type="button"
                      onClick={() => { const i = STEPS.findIndex(s => s.id === step); if (i > 0) setStep(STEPS[i - 1].id); }}
                      className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors">
                      Geri
                    </button>
                  )}

                  {step === "suite" && (
                    <button type="button" onClick={handleCreateSuite}
                      disabled={!suiteName.trim() || busy}
                      className="rounded-xl bg-brand px-5 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-40 transition-all shadow-sm">
                      {busy ? "Oluşturuluyor…" : "Suite Oluştur →"}
                    </button>
                  )}

                  {step === "folder" && (
                    <>
                      <button type="button" onClick={() => { markDone("folder"); setStep("plan"); }}
                        className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg">
                        Klasör Eklemeden Devam
                      </button>
                      {folders.length > 0 && (
                        <button type="button" onClick={handleCreateFolders} disabled={busy}
                          className="rounded-xl bg-brand px-5 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-40 shadow-sm">
                          {busy ? "Oluşturuluyor…" : `${folders.length} Klasör Oluştur →`}
                        </button>
                      )}
                    </>
                  )}

                  {step === "plan" && (
                    <button type="button" onClick={handleCreatePlan}
                      disabled={!planName.trim() || busy}
                      className="rounded-xl bg-brand px-5 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-40 shadow-sm">
                      {busy ? "Oluşturuluyor…" : "Plan Oluştur →"}
                    </button>
                  )}

                  {step === "cycle" && (
                    <button type="button" onClick={handleCreateCycle}
                      disabled={!cycleName.trim() || busy}
                      className="rounded-xl bg-brand px-5 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-40 shadow-sm">
                      {busy ? "Oluşturuluyor…" : "Döngü Oluştur →"}
                    </button>
                  )}

                  {step === "run" && (
                    <button type="button" onClick={handleStartRun}
                      disabled={!runName.trim() || busy}
                      className="rounded-xl bg-emerald-600 px-5 py-2 text-[12px] font-semibold text-white hover:bg-emerald-500 disabled:opacity-40 shadow-sm">
                      {busy ? "Başlatılıyor…" : "Run Başlat →"}
                    </button>
                  )}
                </div>
              </div>

              {/* Tree preview panel */}
              <div className="space-y-4">
                <TreePreview
                  suite={createdSuite?.name ?? suiteName}
                  folders={folders}
                  planName={createdPlan?.name ?? planName}
                  cycleName={createdCycle?.name ?? cycleName}
                />

                {/* Context info */}
                <div className="rounded-xl border border-border bg-surface-base p-4 space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Oluşturulanlar</p>
                  {done.has("suite") && createdSuite && (
                    <div className="flex items-center gap-2 text-[12px]">
                      <span className="flex h-4 w-4 items-center justify-center text-emerald-500"><IcCheck/></span>
                      <span className="text-fg-muted">Suite:</span>
                      <span className="font-medium text-fg">{createdSuite.name}</span>
                    </div>
                  )}
                  {done.has("folder") && folders.length > 0 && (
                    <div className="flex items-center gap-2 text-[12px]">
                      <span className="flex h-4 w-4 items-center justify-center text-emerald-500"><IcCheck/></span>
                      <span className="text-fg-muted">Klasörler:</span>
                      <span className="font-medium text-fg">{folders.length} adet</span>
                    </div>
                  )}
                  {done.has("plan") && createdPlan && (
                    <div className="flex items-center gap-2 text-[12px]">
                      <span className="flex h-4 w-4 items-center justify-center text-emerald-500"><IcCheck/></span>
                      <span className="text-fg-muted">Plan:</span>
                      <span className="font-medium text-fg">{createdPlan.name}</span>
                    </div>
                  )}
                  {done.has("cycle") && createdCycle && (
                    <div className="flex items-center gap-2 text-[12px]">
                      <span className="flex h-4 w-4 items-center justify-center text-emerald-500"><IcCheck/></span>
                      <span className="text-fg-muted">Döngü:</span>
                      <span className="font-medium text-fg">{createdCycle.name}</span>
                    </div>
                  )}
                  {!done.size && (
                    <p className="text-[11px] text-fg-subtle">Adımları tamamladıkça burada görünür.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
