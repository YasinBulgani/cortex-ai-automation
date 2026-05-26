"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useCreateManagementCase, useManagementRepository } from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell } from "../../_components/ManagementShell";

type DraftStep = {
  action: string;
  expected_result: string;
  test_data: string;
  notes: string;
  is_required: boolean;
};

export default function NewManagementCasePage({ params }: { params: { projectId: string } }) {
  const router = useRouter();
  const createCase = useCreateManagementCase(params.projectId);
  const repository = useManagementRepository(params.projectId);
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
  const [steps, setSteps] = useState<DraftStep[]>([
    { action: "", expected_result: "", test_data: "", notes: "", is_required: true },
  ]);
  const [formError, setFormError] = useState("");

  const addStep = () => {
    setSteps((current) => [...current, { action: "", expected_result: "", test_data: "", notes: "", is_required: true }]);
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

    if (!title.trim()) {
      setFormError("Başlık zorunlu.");
      return;
    }
    if (cleanSteps.length === 0) {
      setFormError("En az bir action + expected result adımı girilmeli.");
      return;
    }

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
      tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      custom_fields: {
        component: component.trim(),
        platform: platform.trim(),
        risk_area: riskArea.trim(),
      },
      steps: cleanSteps,
    });
    router.push(`/p/${params.projectId}/management/cases/${created.id}`);
  };

  return (
    <ManagementShell
      projectId={params.projectId}
      title="New Test Case"
      description="Manuel test case, step ve initial version snapshot kaydını oluşturun."
      active="management/repository"
    >
      <ManagementPanel title="Case Form">
        <form onSubmit={submit} className="space-y-5">
          {formError ? (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {formError}
            </div>
          ) : null}
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Title</span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                placeholder="Login valid credentials"
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Suite</span>
                <select
                  value={suiteId}
                  onChange={(event) => {
                    setSuiteId(event.target.value);
                    setFolderId("");
                  }}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  <option value="">Suite seç</option>
                  {(repository.data?.suites ?? []).map((suite) => <option key={suite.id} value={suite.id}>{suite.name}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Folder</span>
                <select
                  value={folderId}
                  onChange={(event) => setFolderId(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  <option value="">Folder seç</option>
                  {(repository.data?.folders ?? []).filter((folder) => !suiteId || folder.suite_id === suiteId).map((folder) => <option key={folder.id} value={folder.id}>{folder.path}</option>)}
                </select>
              </label>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Priority</span>
                <select
                  value={priority}
                  onChange={(event) => setPriority(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  {["P0", "P1", "P2", "P3"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Severity</span>
                <select
                  value={severity}
                  onChange={(event) => setSeverity(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  {["blocker", "critical", "major", "minor"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Type</span>
                <select
                  value={type}
                  onChange={(event) => setType(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  {["functional", "smoke", "regression", "uat", "exploratory"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</span>
                <select
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  {["draft", "review", "active"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Automation</span>
              <select value={automationStatus} onChange={(event) => setAutomationStatus(event.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
                {["manual", "candidate", "automated", "deprecated"].map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Component</span>
              <input value={component} onChange={(event) => setComponent(event.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Auth" />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Platform</span>
              <input value={platform} onChange={(event) => setPlatform(event.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Web / iOS / Android" />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Risk Area</span>
              <input value={riskArea} onChange={(event) => setRiskArea(event.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Payment, Session" />
            </label>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Objective</span>
              <textarea
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
                rows={3}
                className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Preconditions</span>
              <textarea
                value={preconditions}
                onChange={(event) => setPreconditions(event.target.value)}
                rows={3}
                className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
              />
            </label>
          </div>
          <label className="block space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Test Data</span>
            <textarea
              value={testData}
              onChange={(event) => setTestData(event.target.value)}
              rows={3}
              className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
              placeholder="Kullanıcı, rol, veri seti, fixture veya özel inputlar"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Tags</span>
            <input
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
              placeholder="login, smoke, auth"
            />
          </label>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Steps</h2>
              <button
                type="button"
                onClick={addStep}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
              >
                Add Step
              </button>
            </div>
            {steps.map((step, index) => (
              <div key={index} className="grid gap-3 rounded-lg border border-slate-800 bg-slate-950 p-3 md:grid-cols-[2rem_1fr_1fr_auto]">
                <div className="pt-2 text-center font-mono text-xs text-slate-500">{index + 1}</div>
                <div className="space-y-2">
                  <textarea value={step.action} onChange={(event) => updateStep(index, { action: event.target.value })} rows={2} className="w-full resize-none rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Action" />
                  <input value={step.test_data} onChange={(event) => updateStep(index, { test_data: event.target.value })} className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-teal-500/50 focus:outline-none" placeholder="Step test data" />
                </div>
                <div className="space-y-2">
                  <textarea value={step.expected_result} onChange={(event) => updateStep(index, { expected_result: event.target.value })} rows={2} className="w-full resize-none rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Expected result / validation" />
                  <input value={step.notes} onChange={(event) => updateStep(index, { notes: event.target.value })} className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-teal-500/50 focus:outline-none" placeholder="Notes" />
                </div>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-xs text-slate-400">
                    <input type="checkbox" checked={step.is_required} onChange={(event) => updateStep(index, { is_required: event.target.checked })} />
                    Required
                  </label>
                <button
                  type="button"
                  onClick={() => removeStep(index)}
                  className="rounded-lg border border-slate-800 px-3 py-2 text-xs text-slate-500 hover:bg-slate-800 hover:text-slate-200"
                >
                  Remove
                </button>
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={createCase.isPending}
              className="rounded-lg bg-teal-500 px-5 py-2 text-sm font-semibold text-slate-950 hover:bg-teal-400 disabled:opacity-40"
            >
              {createCase.isPending ? "Saving..." : "Save Test Case"}
            </button>
          </div>
        </form>
      </ManagementPanel>
    </ManagementShell>
  );
}
