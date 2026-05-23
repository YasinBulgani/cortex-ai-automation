import RunWizard from "./_RunWizard";

export const metadata = { title: "Manuel Koşum — qa/" };
export const dynamic = "force-dynamic";

export default function RunPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6 border-b border-gray-200 pb-4">
        <h1 className="text-xl font-semibold">Manuel Test Koşumu</h1>
        <p className="mt-1 text-sm text-gray-500">
          Plan seç, TC'leri adım adım pass/fail kaydet, run YAML otomatik üretilir.
        </p>
      </header>
      <RunWizard />
    </main>
  );
}
