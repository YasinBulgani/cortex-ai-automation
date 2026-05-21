export default function NotFound() {
  return (
    <main
      className="flex min-h-screen items-center justify-center bg-slate-950"
      role="main"
      aria-labelledby="nf-title"
    >
      <div className="flex flex-col items-center gap-4 text-center">
        <div
          className="flex h-16 w-16 items-center justify-center rounded-full border border-slate-800 bg-slate-900 text-slate-500"
          aria-hidden="true"
        >
          <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <p className="text-2xl font-bold text-white">404</p>
          <h1 id="nf-title" className="mt-1 text-sm text-slate-400">
            Sayfa bulunamadı
          </h1>
        </div>
        <a
          href="/"
          className="mt-2 rounded-xl border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
        >
          Ana sayfaya dön
        </a>
      </div>
    </main>
  );
}
