"use client";

export interface Feature {
  name: string;
  content?: string;
  path: string;
  updated_at?: string | null;
}

export interface FeatureContentViewerProps {
  selected: Feature | null;
  editMode: boolean;
  editContent: string;
  saving: boolean;
  saveErr: string | null;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onEditContentChange: (value: string) => void;
  onRunSelected: () => void;
}

export function FeatureContentViewer({
  selected,
  editMode,
  editContent,
  saving,
  saveErr,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onEditContentChange,
  onRunSelected,
}: FeatureContentViewerProps) {
  return (
    <div
      className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden"
      data-testid="automation-content-panel"
    >
      {selected ? (
        <>
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2.5">
            <div className="flex items-center gap-2">
              <svg
                className="h-4 w-4 text-slate-400"
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
              <span
                className="text-sm font-medium"
                data-testid="automation-selected-name"
              >
                {selected.name}
              </span>
              {selected.path && (
                <span className="text-xs text-slate-400 font-mono">
                  {selected.path}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {selected.updated_at && !editMode && (
                <span className="text-xs text-slate-400">
                  Son güncelleme: {selected.updated_at}
                </span>
              )}
              {!editMode ? (
                <>
                  <button
                    type="button"
                    onClick={onRunSelected}
                    className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-200 hover:border-emerald-400/50 hover:bg-emerald-500/20 transition-colors"
                    data-testid="automation-btn-run-selected"
                    title="Seçili feature için yeni bir koşum başlat"
                  >
                    <svg
                      className="h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    Çalıştır
                  </button>
                  <button
                    type="button"
                    onClick={onStartEdit}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
                    data-testid="automation-btn-edit"
                  >
                    <svg
                      className="h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                    Düzenle
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-2">
                  {saveErr && (
                    <span className="text-xs text-red-400">{saveErr}</span>
                  )}
                  <button
                    type="button"
                    onClick={onCancelEdit}
                    disabled={saving}
                    className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                  >
                    İptal
                  </button>
                  <button
                    type="button"
                    onClick={onSaveEdit}
                    disabled={saving}
                    className="rounded-lg bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50"
                    data-testid="automation-btn-save-edit"
                  >
                    {saving ? "Kaydediliyor…" : "Kaydet"}
                  </button>
                </div>
              )}
            </div>
          </div>
          <div
            className="overflow-auto p-4"
            data-testid="automation-content-viewer"
          >
            {editMode ? (
              <textarea
                value={editContent}
                onChange={(e) => onEditContentChange(e.target.value)}
                className="w-full font-mono text-xs text-white bg-slate-950 border border-slate-700 rounded-lg p-3 focus:outline-none focus:border-blue-500 resize-none leading-relaxed"
                style={{ minHeight: 400 }}
                data-testid="automation-textarea-edit"
                autoFocus
              />
            ) : (
              <pre className="font-mono text-xs text-white leading-relaxed whitespace-pre-wrap break-words">
                {selected.content || (
                  <span className="text-slate-400 italic">İçerik yok.</span>
                )}
              </pre>
            )}
          </div>
        </>
      ) : (
        <div
          className="flex h-64 items-center justify-center"
          data-testid="automation-no-selection"
        >
          <p className="text-sm text-slate-400">
            Görüntülemek için bir dosya seçin.
          </p>
        </div>
      )}
    </div>
  );
}
