"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  useArchiveManagementCase,
  useManagementCase,
  useManagementCaseVersions,
  useManagementRequirements,
  useUpdateManagementCase,
} from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell, ManagementStat } from "../../_components/ManagementShell";

export default function ManagementCaseDetailPage({
  params,
}: {
  params: { projectId: string; caseId: string };
}) {
  const router = useRouter();
  const testCase = useManagementCase(params.projectId, params.caseId);
  const versions = useManagementCaseVersions(params.projectId, params.caseId);
  const requirements = useManagementRequirements(params.projectId, params.caseId);
  const archiveCase = useArchiveManagementCase(params.projectId);
  const updateCase = useUpdateManagementCase(params.projectId, params.caseId);
  const data = testCase.data;
  const [editOpen, setEditOpen] = useState(false);
  const [form, setForm] = useState({
    title: "",
    objective: "",
    preconditions: "",
    priority: "P2",
    type: "manual",
    status: "active",
    tags: "",
    change_summary: "Manual case update",
  });

  useEffect(() => {
    if (!data) return;
    setForm({
      title: data.title,
      objective: data.objective ?? "",
      preconditions: data.preconditions ?? "",
      priority: data.priority,
      type: data.type,
      status: data.status,
      tags: data.tags.join(", "),
      change_summary: "Manual case update",
    });
  }, [data]);

  const archive = async () => {
    await archiveCase.mutateAsync(params.caseId);
    void testCase.refetch();
  };

  return (
    <ManagementShell
      projectId={params.projectId}
      title={data ? `${data.case_key} · ${data.title}` : `Test Case ${params.caseId}`}
      description="Case metadata, steps, requirement links, run history, defects, attachments, versions ve audit görünümü."
      active="management/repository"
    >
      <div className="mb-4 flex justify-end gap-2">
        <button
          onClick={() => router.push(`/p/${params.projectId}/management/repository`)}
          className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
        >
          Repository
        </button>
        {data && !data.archived ? (
          <>
          <button
            onClick={() => setEditOpen((value) => !value)}
            className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
          >
            {editOpen ? "Edit Kapat" : "Edit"}
          </button>
          <button
            onClick={archive}
            disabled={archiveCase.isPending}
            className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200 hover:bg-rose-500/20 disabled:opacity-40"
          >
            {archiveCase.isPending ? "Archiving..." : "Archive"}
          </button>
          </>
        ) : null}
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Version" value={data ? `v${data.current_version}` : testCase.isLoading ? "..." : "-"} note="current repository" />
        <ManagementStat label="Steps" value={data ? String(data.steps.length) : testCase.isLoading ? "..." : "-"} note={`${data?.steps.filter((step) => step.is_required).length ?? 0} required`} />
        <ManagementStat label="Last Run" value={data?.last_run_status ?? "-"} note={data?.last_run_at ? new Date(data.last_run_at).toLocaleString("tr-TR") : "not run"} />
        <ManagementStat label="Requirements" value={requirements.isLoading ? "..." : String(requirements.data?.length ?? 0)} note="linked coverage" />
      </div>
      {editOpen && data ? (
        <div className="mt-6">
          <ManagementPanel title="Edit Case">
            <form
              className="space-y-3"
              onSubmit={async (event) => {
                event.preventDefault();
                await updateCase.mutateAsync({
                  title: form.title.trim(),
                  objective: form.objective,
                  preconditions: form.preconditions,
                  priority: form.priority,
                  type: form.type,
                  status: form.status,
                  tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
                  change_summary: form.change_summary || "Manual case update",
                });
                await Promise.all([testCase.refetch(), versions.refetch()]);
                setEditOpen(false);
              }}
            >
              <input
                value={form.title}
                onChange={(event) => setForm((value) => ({ ...value, title: event.target.value }))}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
              />
              <div className="grid gap-3 md:grid-cols-3">
                <select
                  value={form.priority}
                  onChange={(event) => setForm((value) => ({ ...value, priority: event.target.value }))}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
                >
                  <option value="P0">P0</option>
                  <option value="P1">P1</option>
                  <option value="P2">P2</option>
                  <option value="P3">P3</option>
                </select>
                <select
                  value={form.type}
                  onChange={(event) => setForm((value) => ({ ...value, type: event.target.value }))}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
                >
                  <option value="manual">Manual</option>
                  <option value="regression">Regression</option>
                  <option value="smoke">Smoke</option>
                  <option value="uat">UAT</option>
                  <option value="exploratory">Exploratory</option>
                </select>
                <select
                  value={form.status}
                  onChange={(event) => setForm((value) => ({ ...value, status: event.target.value }))}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
                >
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="review">Review</option>
                  <option value="deprecated">Deprecated</option>
                </select>
              </div>
              <textarea
                value={form.objective}
                onChange={(event) => setForm((value) => ({ ...value, objective: event.target.value }))}
                rows={2}
                placeholder="Objective"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
              <textarea
                value={form.preconditions}
                onChange={(event) => setForm((value) => ({ ...value, preconditions: event.target.value }))}
                rows={2}
                placeholder="Preconditions"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
              <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                <input
                  value={form.tags}
                  onChange={(event) => setForm((value) => ({ ...value, tags: event.target.value }))}
                  placeholder="tag1, tag2"
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                />
                <input
                  value={form.change_summary}
                  onChange={(event) => setForm((value) => ({ ...value, change_summary: event.target.value }))}
                  placeholder="Change summary"
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                />
                <button
                  disabled={updateCase.isPending || !form.title.trim()}
                  className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-40"
                >
                  {updateCase.isPending ? "Kaydediliyor..." : "Kaydet"}
                </button>
              </div>
            </form>
          </ManagementPanel>
        </div>
      ) : null}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <ManagementPanel title="Overview">
          {testCase.isLoading ? (
            <p className="text-sm text-slate-500">Yükleniyor...</p>
          ) : data ? (
            <div className="space-y-3 text-sm text-slate-300">
              <div className="grid grid-cols-2 gap-3">
                <p><span className="text-slate-500">Priority:</span> {data.priority}</p>
                <p><span className="text-slate-500">Type:</span> {data.type}</p>
                <p><span className="text-slate-500">Status:</span> {data.status}</p>
                <p><span className="text-slate-500">Automation:</span> {data.automation_status}</p>
              </div>
              {data.objective ? <p><span className="text-slate-500">Objective:</span> {data.objective}</p> : null}
              {data.preconditions ? <p><span className="text-slate-500">Preconditions:</span> {data.preconditions}</p> : null}
              {data.tags.length ? (
                <div className="flex flex-wrap gap-2">
                  {data.tags.map((tag) => (
                    <span key={tag} className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">{tag}</span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-rose-300">Test case bulunamadı.</p>
          )}
        </ManagementPanel>
        <ManagementPanel title="Requirement Links">
          {(requirements.data ?? []).length ? (
            <div className="space-y-2">
              {(requirements.data ?? []).map((link) => (
                <div key={link.id} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono text-xs text-slate-500">{link.external_key}</span>
                    <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">
                      {link.coverage_status}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-200">{link.title_snapshot}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Bu case için requirement bağlantısı yok.</p>
          )}
        </ManagementPanel>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <ManagementPanel title="Steps">
          <div className="space-y-2">
            {(data?.steps ?? []).map((step) => (
              <div key={step.id} className="grid gap-3 rounded-lg border border-slate-800 bg-slate-950 p-3 md:grid-cols-[2rem_1fr_1fr]">
                <span className="font-mono text-xs text-slate-500">{step.step_no}</span>
                <p className="text-sm text-slate-200">{step.action}</p>
                <p className="text-sm text-slate-400">{step.expected_result}</p>
              </div>
            ))}
            {data && data.steps.length === 0 ? (
              <p className="text-sm text-slate-500">Bu case için step yok.</p>
            ) : null}
          </div>
        </ManagementPanel>
        <ManagementPanel title="Version History">
          {versions.isLoading ? (
            <p className="text-sm text-slate-500">Versiyonlar yükleniyor...</p>
          ) : versions.data?.length ? (
            <div className="space-y-3">
              {versions.data.map((version) => (
                <div key={version.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">v{version.version_no}</p>
                      <p className="text-xs text-slate-500">{version.change_summary ?? "Version snapshot"}</p>
                    </div>
                    <span className="shrink-0 text-xs text-slate-500">
                      {new Date(version.created_at).toLocaleString("tr-TR")}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(version.changed_fields.length ? version.changed_fields : ["snapshot"]).map((field) => (
                      <span key={field} className="rounded-lg border border-slate-700 px-2 py-0.5 text-xs text-slate-400">
                        {field}
                      </span>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-slate-500">{version.snapshot_size_bytes} bytes</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Henüz versiyon kaydı yok.</p>
          )}
        </ManagementPanel>
      </div>
    </ManagementShell>
  );
}
