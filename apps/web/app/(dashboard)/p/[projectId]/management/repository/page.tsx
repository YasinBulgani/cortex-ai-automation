import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

const cases = [
  ["CRM-TC-1001", "Login valid credentials", "Smoke", "Ready", "Passed"],
  ["CRM-TC-1002", "Password reset email", "Functional", "Ready", "Blocked"],
  ["CRM-TC-1003", "Checkout card declined", "Regression", "Review", "Failed"],
];

export default function ManagementRepositoryPage({ params }: { params: { projectId: string } }) {
  return (
    <ManagementShell projectId={params.projectId} title="Test Repository" description="Suite, folder, manuel test case, step ve version kayıtlarının yönetildiği kalıcı test hafızası." active="management/repository">
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat label="Suites" value="12" note="4 aktif ürün modülü" />
        <ManagementStat label="Ready Cases" value="286" note="55 draft/review" />
        <ManagementStat label="Versioned Updates" value="41" note="son 7 gün" />
      </div>
      <ManagementPanel title="Repository Preview">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="py-2">Key</th><th>Title</th><th>Type</th><th>Status</th><th>Last Run</th></tr>
            </thead>
            <tbody>
              {cases.map((row) => (
                <tr key={row[0]} className="border-t border-slate-800 text-slate-300">
                  {row.map((cell) => <td key={cell} className="py-3 pr-4">{cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
