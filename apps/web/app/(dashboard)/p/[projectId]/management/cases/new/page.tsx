import { ManagementPanel, ManagementShell } from "../../_components/ManagementShell";

export default function NewManagementCasePage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="New Test Case" description="Manuel test case oluşturma formunun veri sözleşmesi ve MVP iskeleti." active="management/repository">
      <ManagementPanel title="Required Fields">
        <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
          <p>Title, suite, priority, type ve status alanları zorunlu.</p>
          <p>Her case en az bir action + expected result step'i taşımalı.</p>
          <p>Save sonrası `test_case_versions` initial snapshot oluşur.</p>
          <p>Case key proje prefix'i ile otomatik üretilebilir.</p>
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
