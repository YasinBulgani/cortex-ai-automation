import { ManagementPanel, ManagementShell, ManagementStat } from "./_components/ManagementShell";

export default function ManagementDashboardPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell
      projectId={params.projectId}
      title="Management Dashboard"
      description="Manuel test repository, aktif run, blocked/failed risk ve tester workload durumunu tek ekranda izleyin."
      active="management"
    >
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Manual Cases" value="341" note="24 yeni case bu hafta" />
        <ManagementStat label="Active Runs" value="9" note="3 run tester bekliyor" />
        <ManagementStat label="Pass Rate" value="88.1%" note="Sprint 12 regression" />
        <ManagementStat label="Blocked" value="7" note="2 kritik blocker" />
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <ManagementPanel title="Release Readiness">
          <div className="space-y-3 text-sm">
            {[
              ["Execution progress", "74%", "bg-teal-500"],
              ["Requirement coverage", "76%", "bg-emerald-500"],
              ["Critical fail gate", "3 open", "bg-rose-500"],
              ["Blocked aging", "2 over SLA", "bg-amber-500"],
            ].map(([label, value, color]) => (
              <div key={label} className="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2">
                <span className="text-slate-300">{label}</span>
                <span className={`rounded-full px-2 py-1 text-xs font-semibold text-white ${color}`}>{value}</span>
              </div>
            ))}
          </div>
        </ManagementPanel>
        <ManagementPanel title="Next Build Tasks">
          <ul className="space-y-2 text-sm text-slate-300">
            <li>Dashboard metrikleri typed Management hook'larıyla canlı veriye bağlanacak.</li>
            <li>Run execute ekranı step result akışıyla etkileşimli hale getirilecek.</li>
            <li>Evidence upload artifacts domain'e bağlanacak.</li>
            <li>Import staging için conflict preview ve commit adımı açılacak.</li>
          </ul>
        </ManagementPanel>
      </div>
    </ManagementShell>
  );
}
