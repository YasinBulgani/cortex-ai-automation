import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementReportsPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="Management Reports" description="Execution summary, coverage matrix, tester workload ve release GO/NO-GO raporları." active="management/reports">
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Progress" value="74%" note="terminal / total" />
        <ManagementStat label="Pass Rate" value="88%" note="passed / executed" />
        <ManagementStat label="Coverage" value="76%" note="covered / total" />
        <ManagementStat label="Readiness" value="Caution" note="critical fail var" />
      </div>
      <ManagementPanel title="Report Formulas">
        <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
          <p>Progress = terminal run cases / total assigned run cases.</p>
          <p>Pass Rate = passed / passed+failed+blocked+skipped.</p>
          <p>Coverage = covered linked requirements / total linked requirements.</p>
          <p>GO/NO-GO = critical fail, blocked, coverage ve progress eşikleri.</p>
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
