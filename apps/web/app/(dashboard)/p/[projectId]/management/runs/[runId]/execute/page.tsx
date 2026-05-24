import { ManagementPanel, ManagementShell, ManagementStat } from "../../../_components/ManagementShell";

export default function ManagementRunExecutePage({ params }: { params: { projectId: string; runId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title={`Execute Run ${params.runId}`} description="Tester odaklı adım adım koşum, actual result, evidence ve defect linkleme ekranı." active="management/runs">
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Assigned" value="24" note="bu tester" />
        <ManagementStat label="Done" value="15" note="terminal status" />
        <ManagementStat label="Failed" value="3" note="defect bekliyor" />
        <ManagementStat label="Evidence" value="18" note="upload/link" />
      </div>
      <ManagementPanel title="Execution Contract">
        <ul className="space-y-2 text-sm text-slate-300">
          <li>Run case `case_version_no` ile sabitlenmiş snapshot üzerinden koşulur.</li>
          <li>Step status değişimi `test_run_step_results` tablosuna yazılır.</li>
          <li>Case final status aggregation servis tarafından hesaplanır.</li>
        </ul>
      </ManagementPanel>
    </ManagementShell>
  );
}
