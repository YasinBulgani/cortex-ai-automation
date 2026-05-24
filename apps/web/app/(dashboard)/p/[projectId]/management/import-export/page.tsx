import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementImportExportPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="Import / Export" description="Excel/CSV staging, satır bazlı validation, duplicate/conflict preview ve repository export akışı." active="management/import-export">
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat label="Import Jobs" value="6" note="2 preview bekliyor" />
        <ManagementStat label="Conflict Rows" value="18" note="otomatik merge yok" />
        <ManagementStat label="Exports" value="14" note="son 30 gün" />
      </div>
      <ManagementPanel title="Import Guardrails">
        <ul className="space-y-2 text-sm text-slate-300">
          <li>Import önce staging'e yazar, doğrudan repository'ye yazmaz.</li>
          <li>Row status: new, duplicate_candidate, conflict, invalid, ready.</li>
          <li>Commit sonrası case version snapshot ve rollback referansı oluşur.</li>
        </ul>
      </ManagementPanel>
    </ManagementShell>
  );
}
