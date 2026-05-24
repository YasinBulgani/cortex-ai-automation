import InsightsView from "./_InsightsView";

export const metadata = { title: "Insights — qa/" };
export const dynamic = "force-dynamic";

export default function InsightsPage() {
  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-6 border-b border-gray-200 pb-4">
        <h1 className="text-xl font-semibold">QA Insights</h1>
        <p className="mt-1 text-sm text-gray-500">
          Velocity, trend, owner breakdown, top failing TC&apos;ler. `/api/v1/qa/insights` veri kaynağı.
        </p>
      </header>
      <InsightsView />
    </main>
  );
}
