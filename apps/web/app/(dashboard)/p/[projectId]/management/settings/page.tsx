"use client";

import { useMemo } from "react";

import { useManagementAuditEvents, useManagementSettings } from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

function toNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export default function ManagementSettingsPage({ params }: { params: { projectId: string } }) {
  const settings = useManagementSettings(params.projectId);
  const auditEvents = useManagementAuditEvents(params.projectId, 25);
  const policy = settings.data;
  const usage = policy?.custom_field_usage;
  const workflowCount = useMemo(
    () => Object.values(policy?.workflow_statuses ?? {}).reduce((sum, items) => sum + items.length, 0),
    [policy?.workflow_statuses],
  );

  return (
    <ManagementShell
      projectId={params.projectId}
      title="Management Settings"
      description="Status policy, custom fields, evidence retention, aggregation rules ve audit sınırları."
      active="management/settings"
    >
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Permissions" value={policy ? String(policy.permissions.length) : "-"} note="read/write/execute/admin/audit" />
        <ManagementStat label="Workflow States" value={workflowCount ? String(workflowCount) : "-"} note="case/run/plan/import" />
        <ManagementStat label="Custom Fields" value={usage ? String(usage.defined_fields.length) : "-"} note={`${usage?.cases_with_custom_fields ?? 0} case kullanıyor`} />
        <ManagementStat label="Evidence" value={usage ? String(usage.evidence_count) : "-"} note="DB linked artifacts" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <ManagementPanel title="Effective Policy">
          {settings.isLoading ? (
            <p className="text-sm text-slate-400">Policy yükleniyor...</p>
          ) : (
            <div className="space-y-5">
              <section>
                <h3 className="mb-2 text-sm font-semibold text-white">Workflow Statuses</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  {Object.entries(policy?.workflow_statuses ?? {}).map(([name, states]) => (
                    <div key={name} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-500">{name}</p>
                      <p className="mt-2 text-sm text-slate-200">{states.join(" -> ")}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section>
                <h3 className="mb-2 text-sm font-semibold text-white">Evidence Retention</h3>
                <div className="grid gap-3 md:grid-cols-4">
                  {Object.entries(policy?.evidence_retention_days ?? {}).map(([name, days]) => (
                    <div key={name} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-500">{name.replaceAll("_", " ")}</p>
                      <p className="mt-2 text-lg font-semibold text-white">{days} gün</p>
                    </div>
                  ))}
                </div>
              </section>

              <section>
                <h3 className="mb-2 text-sm font-semibold text-white">Aggregation Rules</h3>
                <div className="space-y-2">
                  {Object.entries(policy?.aggregation_policy ?? {}).map(([name, value]) => (
                    <div key={name} className="flex flex-col gap-1 rounded-lg border border-slate-800 bg-slate-950/50 p-3 md:flex-row md:items-center md:justify-between">
                      <span className="text-xs uppercase tracking-wide text-slate-500">{name.replaceAll("_", " ")}</span>
                      <span className="text-sm text-slate-200">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
        </ManagementPanel>

        <ManagementPanel title="Audit Trail">
          {auditEvents.isLoading ? (
            <p className="text-sm text-slate-400">Audit kayıtları yükleniyor...</p>
          ) : auditEvents.data?.length ? (
            <div className="space-y-3">
              {auditEvents.data.map((event) => (
                <div key={event.id} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">{event.action}</p>
                      <p className="text-xs text-slate-500">
                        {event.entity_type}
                        {event.entity_id ? ` / ${event.entity_id.slice(0, 8)}` : ""}
                      </p>
                    </div>
                    <span className="shrink-0 text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</span>
                  </div>
                  {Object.keys(event.payload ?? {}).length > 0 ? (
                    <pre className="mt-3 max-h-28 overflow-auto rounded-lg bg-slate-950 p-2 text-xs text-slate-300">
                      {JSON.stringify(event.payload, null, 2)}
                    </pre>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">Henüz audit kaydı yok.</p>
          )}
        </ManagementPanel>
      </div>

      <ManagementPanel title="Custom Field Usage">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Total Cases</p>
            <p className="mt-2 text-lg font-semibold text-white">{usage?.case_count ?? 0}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Cases With Fields</p>
            <p className="mt-2 text-lg font-semibold text-white">{usage?.cases_with_custom_fields ?? 0}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Usage Ratio</p>
            <p className="mt-2 text-lg font-semibold text-white">
              {usage?.case_count ? Math.round((toNumber(usage.cases_with_custom_fields) / usage.case_count) * 100) : 0}%
            </p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(usage?.defined_fields.length ? usage.defined_fields : ["No custom fields"]).map((field) => (
            <span key={field} className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-300">
              {field}
            </span>
          ))}
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
