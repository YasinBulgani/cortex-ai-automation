"use client";

export default function ProjectSectionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div
      className="flex min-h-[40vh] flex-col items-center justify-center gap-4 p-8"
      data-testid="project-error"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-red-500/20 bg-red-500/10">
        <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-white">Bu bölüm yüklenemedi</h2>
      <p className="max-w-md text-center text-sm text-slate-400">{error.message}</p>
      <button
        type="button"
        onClick={() => reset()}
        className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
        data-testid="project-error-btn-retry"
      >
        Tekrar dene
      </button>
    </div>
  );
}
