import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementSettingsPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="Management Settings" description="Status policy, custom fields, evidence retention, aggregation rules ve role boundaries." active="management/settings">
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Permissions" value="4" note="read/write/execute/admin" />
        <ManagementStat label="Custom Fields" value="8" note="schema governed" />
        <ManagementStat label="Retention" value="Active" note="evidence policy" />
        <ManagementStat label="Aggregation" value="Default" note="Faz 2 configurable" />
      </div>
      <ManagementPanel title="Default Retention">
        <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
          <p>Screenshot: 180 gün</p>
          <p>Log: 90 gün</p>
          <p>Video: 30 gün</p>
          <p>Critical failed evidence: 365 gün</p>
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
