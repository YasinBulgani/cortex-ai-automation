import EditForm from "./_EditForm";

export const metadata = { title: "TC Düzenle — qa/" };
export const dynamic = "force-dynamic";

export default function EditPage({ params }: { params: { id: string } }) {
  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6 border-b border-gray-200 pb-4">
        <h1 className="text-xl font-semibold">
          TC Düzenle: <code className="font-mono text-base text-gray-600">{params.id}</code>
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Frontmatter form + body markdown editör. Save → backend filesystem write + git commit (PR).
        </p>
      </header>
      <EditForm tcId={params.id} />
    </main>
  );
}
