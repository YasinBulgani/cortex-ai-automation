import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementPlansPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="Test Plans" description="Release, sprint, regression ve UAT planları için case seçimi, cycle ve kapsam yönetimi." active="management/plans">
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat label="Active Plans" value="4" note="2 regression, 1 smoke, 1 UAT" />
        <ManagementStat label="Planned Cases" value="254" note="Sprint 12 toplam" />
        <ManagementStat label="Ready to Run" value="91%" note="case status ready" />
      </div>
      <ManagementPanel title="Plan Builder Contract">
        <p className="text-sm leading-6 text-slate-300">
          Plan oluşturma akışı repository filtrelerinden case seçer, cycle bilgisiyle ortam/build snapshot'ı alır ve run oluştururken her case için `case_version_no` değerini sabitler.
        </p>
      </ManagementPanel>
    </ManagementShell>
  );
}
