import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementRunsPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="Test Runs" description="Tester assignment, adım bazlı execution, actual result, evidence ve defect link akışları." active="management/runs">
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Not Run" value="42" note="atanmış bekliyor" />
        <ManagementStat label="Passed" value="186" note="son cycle" />
        <ManagementStat label="Failed" value="19" note="3 critical" />
        <ManagementStat label="Blocked" value="7" note="2 SLA aşımı" />
      </div>
      <ManagementPanel title="Execution Rules">
        <ul className="space-y-2 text-sm text-slate-300">
          <li>Run case, test case'in başladığı andaki versiyonunu koşar.</li>
          <li>Failed veya blocked sonuçta actual result zorunlu olur.</li>
          <li>Evidence case'e değil run result'a bağlanır.</li>
        </ul>
      </ManagementPanel>
    </ManagementShell>
  );
}
