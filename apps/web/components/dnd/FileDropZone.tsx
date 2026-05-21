"use client";

import { useCallback, useState } from "react";

interface FileDropZoneProps {
  onFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  maxSizeMB?: number;
  className?: string;
  children?: React.ReactNode;
}

export function FileDropZone({
  onFiles,
  accept,
  multiple = true,
  maxSizeMB = 50,
  className,
  children,
}: FileDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      setError(null);

      const droppedFiles = Array.from(e.dataTransfer.files);
      if (droppedFiles.length === 0) return;

      const filtered = multiple ? droppedFiles : [droppedFiles[0]];

      const oversized = filtered.find((f) => f.size > maxSizeMB * 1024 * 1024);
      if (oversized) {
        setError(`"${oversized.name}" dosyası ${maxSizeMB}MB sınırını aşıyor.`);
        return;
      }

      onFiles(filtered);
    },
    [onFiles, multiple, maxSizeMB]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        onFiles(Array.from(e.target.files));
      }
    },
    [onFiles]
  );

  return (
    <div className={className}>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`relative flex min-h-[200px] flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200 ${
          isDragOver
            ? "border-blue-500 bg-blue-500/5 scale-[1.01] shadow-lg"
            : "border-slate-800 hover:border-blue-500/50 hover:bg-black/[0.01] "
        }`}
        data-testid="file-drop-zone"
      >
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleInputChange}
          className="absolute inset-0 cursor-pointer opacity-0"
          title="Dosya seçin"
          aria-label="Dosya seçin"
          data-testid="file-drop-input"
        />

        {children || (
          <>
            <div
              className={`mb-4 rounded-full p-3 transition-colors ${
                isDragOver ? "bg-blue-500/10 text-blue-400" : "bg-black/[0.04] text-slate-400 dark:bg-white/[0.06]"
              }`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-8 w-8">
                <path
                  fillRule="evenodd"
                  d="M11.47 2.47a.75.75 0 011.06 0l4.5 4.5a.75.75 0 01-1.06 1.06l-3.22-3.22V16.5a.75.75 0 01-1.5 0V4.81L8.03 8.03a.75.75 0 01-1.06-1.06l4.5-4.5zM3 15.75a.75.75 0 01.75.75v2.25a1.5 1.5 0 001.5 1.5h13.5a1.5 1.5 0 001.5-1.5V16.5a.75.75 0 011.5 0v2.25a3 3 0 01-3 3H5.25a3 3 0 01-3-3V16.5a.75.75 0 01.75-.75z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-white">
              {isDragOver ? "Dosyayı bırakın" : "Dosyaları sürükleyip bırakın"}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              veya dosya seçmek için tıklayın (maks. {maxSizeMB}MB)
            </p>
          </>
        )}
      </div>
      {error && (
        <p className="mt-2 text-sm text-red-600" data-testid="file-drop-error">
          {error}
        </p>
      )}
    </div>
  );
}
