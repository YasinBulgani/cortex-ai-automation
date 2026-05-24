import DefectForm from "./_DefectForm";

export const metadata = { title: "Defect Aç — qa/" };
export const dynamic = "force-dynamic";

export default function NewDefectPage({ searchParams }: { searchParams: { tc?: string; run?: string } }) {
  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <header className="mb-6 border-b border-gray-200 pb-4">
        <h1 className="text-xl font-semibold">Yeni Defect Aç</h1>
        <p className="mt-1 text-sm text-gray-500">
          Form gönderilince GitHub Issue oluşturulur (qa-defect label). Issue kapanınca CI bot
          <code className="ml-1 rounded bg-gray-100 px-1 text-xs">qa/defects/GH-*.md</code> mirror üretir.
        </p>
      </header>
      <DefectForm initialTc={searchParams.tc || ""} initialRun={searchParams.run || ""} />
    </main>
  );
}
