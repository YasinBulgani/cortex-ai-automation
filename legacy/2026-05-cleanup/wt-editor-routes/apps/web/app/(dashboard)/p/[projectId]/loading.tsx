export default function ProjectSectionLoading() {
  return (
    <div
      className="flex min-h-[40vh] items-center justify-center p-8"
      data-testid="project-loading"
    >
      <div className="flex flex-col items-center gap-3">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-slate-700 border-t-blue-500"
          aria-hidden
        />
        <p className="text-sm text-slate-400">Proje yükleniyor...</p>
      </div>
    </div>
  );
}
