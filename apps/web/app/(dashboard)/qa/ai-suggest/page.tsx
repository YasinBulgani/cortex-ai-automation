import AiSuggestPanel from "./_AiSuggestPanel";

export const metadata = { title: "AI Suggest — qa/" };
export const dynamic = "force-dynamic";

export default function AiSuggestPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6 border-b border-border pb-4">
        <h1 className="text-xl font-semibold">AI Suggest — TC draft üreteci</h1>
        <p className="mt-1 text-sm text-fg-subtle">
          REQ veya kısa brief ver, AI 3-10 TC taslağı üretsin. Draft'lar{" "}
          <code className="rounded bg-surface-overlay px-1 text-xs">_draft/</code> klasöründe izole,
          insan review sonrası promote edilebilir.
        </p>
        <p className="mt-1 text-xs text-amber-700">
          Cost rails: $5/gün hard cap. Dry-run modu LLM çağırmaz, sadece prompt'u gösterir.
        </p>
      </header>
      <AiSuggestPanel />
    </main>
  );
}
