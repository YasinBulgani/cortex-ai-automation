"use client";

export interface Feature {
  name: string;
  content?: string;
  path: string;
  updated_at?: string | null;
}

export interface FeatureFileListProps {
  features: Feature[];
  selected: Feature | null;
  deleting: string | null;
  onSelect: (feature: Feature) => void;
  onDelete: (path: string) => void;
}

export function FeatureFileList({
  features,
  selected,
  deleting,
  onSelect,
  onDelete,
}: FeatureFileListProps) {
  return (
    <aside
      className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden"
      data-testid="automation-file-list"
    >
      <div className="border-b border-slate-800 px-3 py-2.5">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">
          Feature Dosyaları ({features.length})
        </span>
      </div>
      <ul className="divide-y divide-border">
        {features.map((feature) => {
          const isActive = selected?.path === feature.path;
          return (
            <li key={feature.path}>
              <div
                className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer transition-colors ${
                  isActive
                    ? "bg-blue-500/10 text-white"
                    : "hover:bg-black/[0.03] dark:hover:bg-white/[0.05] text-white"
                }`}
                onClick={() => onSelect(feature)}
                data-testid={`automation-file-item-${feature.path.replaceAll(
                  "/",
                  "_"
                )}`}
              >
                <svg
                  className="h-4 w-4 shrink-0 text-slate-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{feature.name}</p>
                  {feature.updated_at && (
                    <p className="text-xs text-slate-400">{feature.updated_at}</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(feature.path);
                  }}
                  disabled={deleting === feature.path}
                  className="shrink-0 rounded p-1 text-slate-400 opacity-0 group-hover:opacity-100 hover:text-red-600 disabled:opacity-50 transition-opacity"
                  aria-label={`${feature.name} sil`}
                  data-testid={`automation-delete-${feature.path.replaceAll(
                    "/",
                    "_"
                  )}`}
                >
                  {deleting === feature.path ? (
                    <svg
                      className="h-3.5 w-3.5 animate-spin"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="h-3.5 w-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  )}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
