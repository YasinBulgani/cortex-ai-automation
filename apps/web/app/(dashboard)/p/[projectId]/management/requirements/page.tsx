import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementRequirementsPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="Requirement Coverage" description="Requirement -> test case -> run result -> defect zincirini canlı coverage matrisi olarak takip edin." active="management/requirements">
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat label="Requirements" value="128" note="Jira + internal snapshot" />
        <ManagementStat label="Covered" value="76.5%" note="98 linked requirement" />
        <ManagementStat label="Stale" value="11" note="source updated after case" />
      </div>
      <ManagementPanel title="Coverage Data Contract">
        <p className="text-sm leading-6 text-slate-300">
          Requirement linkleri external key, title snapshot, URL ve source_updated_at ile saklanır; böylece hem dış sistem referansı hem rapor snapshot'ı korunur.
        </p>
      </ManagementPanel>
    </ManagementShell>
  );
}
