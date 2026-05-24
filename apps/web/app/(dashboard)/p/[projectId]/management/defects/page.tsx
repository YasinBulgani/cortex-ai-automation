import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementDefectsPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="Defects" description="Failed veya blocked manuel run sonuçlarından Jira, Azure DevOps, GitHub ya da internal defect bağlantıları." active="management/defects">
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat label="Open Defects" value="23" note="8 linked to failed cases" />
        <ManagementStat label="Critical" value="3" note="release gate blocker" />
        <ManagementStat label="Retest Queue" value="12" note="fix sonrası bekliyor" />
      </div>
      <ManagementPanel title="Sync Decision">
        <p className="text-sm leading-6 text-slate-300">
          MVP'de defect link + status snapshot tutulur. Two-way Jira/Azure sync Faz 2'de açılır; bug closed olduğunda otomatik status değiştirmek yerine retest önerisi üretir.
        </p>
      </ManagementPanel>
    </ManagementShell>
  );
}
