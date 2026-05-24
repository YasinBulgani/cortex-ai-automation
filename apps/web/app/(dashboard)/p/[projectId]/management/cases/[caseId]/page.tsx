import { ManagementPanel, ManagementShell, ManagementStat } from "../../_components/ManagementShell";

export default function ManagementCaseDetailPage({ params }: { params: { projectId: string; caseId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title={`Test Case ${params.caseId}`} description="Case metadata, steps, requirement links, run history, defects, attachments, versions ve audit görünümü." active="management/repository">
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Version" value="v4" note="current repository" />
        <ManagementStat label="Steps" value="7" note="6 required" />
        <ManagementStat label="Last Run" value="Failed" note="Sprint 12" />
        <ManagementStat label="Links" value="3" note="2 req, 1 defect" />
      </div>
      <ManagementPanel title="Detail Tabs">
        <p className="text-sm leading-6 text-slate-300">
          Overview, Steps, Requirements, Runs, Defects, Attachments, Versions ve Audit tabları aynı case kaydını farklı operasyon sorularına göre gösterir.
        </p>
      </ManagementPanel>
    </ManagementShell>
  );
}
