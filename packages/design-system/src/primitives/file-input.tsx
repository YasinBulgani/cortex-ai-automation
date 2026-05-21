"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

export interface FileInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange" | "value"> {
  /** Tek dosya yerine birden fazla */
  multiple?: boolean;
  /** Accept MIME tipi veya uzantı listesi */
  accept?: string;
  /** Maks boyut (byte) */
  maxSize?: number;
  /** Geçersiz / kabul sonrası callback */
  onFilesChange?: (files: File[]) => void;
  /** Reject sebebi (dosya başına) */
  onFilesRejected?: (rejections: Array<{ file: File; reason: string }>) => void;
  /** Görsel — kompakt buton veya geniş drop zone */
  variant?: "button" | "dropzone";
  /** Açıklama metni (dropzone'da görünür) */
  hint?: React.ReactNode;
  invalid?: boolean;
}

export const FileInput = React.forwardRef<HTMLInputElement, FileInputProps>(
  function FileInput(
    {
      multiple,
      accept,
      maxSize,
      onFilesChange,
      onFilesRejected,
      variant = "button",
      hint,
      invalid,
      disabled,
      className,
      id,
      ...rest
    },
    forwardedRef,
  ) {
    const reactId = React.useId();
    const inputId = id ?? reactId;
    const innerRef = React.useRef<HTMLInputElement | null>(null);
    const [isDragging, setIsDragging] = React.useState(false);
    const [fileList, setFileList] = React.useState<File[]>([]);

    React.useImperativeHandle(forwardedRef, () => innerRef.current as HTMLInputElement);

    const acceptList = accept ? accept.split(",").map(s => s.trim().toLowerCase()) : [];

    const matchesAccept = (file: File): boolean => {
      if (acceptList.length === 0) return true;
      const name = file.name.toLowerCase();
      const type = file.type.toLowerCase();
      return acceptList.some(pattern => {
        if (pattern.startsWith(".")) return name.endsWith(pattern);
        if (pattern.endsWith("/*")) return type.startsWith(pattern.slice(0, -1));
        return type === pattern;
      });
    };

    const accept_files = (files: FileList | File[]) => {
      const arr = Array.from(files);
      const accepted: File[] = [];
      const rejected: Array<{ file: File; reason: string }> = [];

      for (const f of arr) {
        if (maxSize && f.size > maxSize) {
          rejected.push({ file: f, reason: `Dosya çok büyük (${humanSize(f.size)} > ${humanSize(maxSize)})` });
          continue;
        }
        if (!matchesAccept(f)) {
          rejected.push({ file: f, reason: `Bu tip desteklenmiyor (${f.type || f.name})` });
          continue;
        }
        accepted.push(f);
      }

      if (!multiple && accepted.length > 1) {
        rejected.push(...accepted.slice(1).map(f => ({ file: f, reason: "Tek dosya seçilebilir" })));
        accepted.length = 1;
      }

      setFileList(accepted);
      onFilesChange?.(accepted);
      if (rejected.length) onFilesRejected?.(rejected);
    };

    const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) accept_files(e.target.files);
    };

    const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      if (e.dataTransfer.files) accept_files(e.dataTransfer.files);
    };

    const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!disabled) setIsDragging(true);
    };

    const onDragLeave = () => setIsDragging(false);

    const openPicker = () => innerRef.current?.click();

    const hiddenInput = (
      <input
        ref={innerRef}
        id={inputId}
        type="file"
        multiple={multiple}
        accept={accept}
        disabled={disabled}
        onChange={onChange}
        className="sr-only"
        {...rest}
      />
    );

    if (variant === "button") {
      return (
        <>
          {hiddenInput}
          <label
            htmlFor={inputId}
            className={cn(
              "inline-flex h-9 cursor-pointer items-center gap-2 rounded border border-border bg-surface-overlay px-3 text-sm text-fg transition-colors hover:bg-surface-accent",
              "disabled:cursor-not-allowed disabled:opacity-50",
              invalid && "border-danger",
              focusRing,
              className,
            )}
          >
            <span aria-hidden>📎</span>
            <span>{fileList.length > 0 ? `${fileList.length} dosya` : "Dosya seç"}</span>
          </label>
        </>
      );
    }

    // dropzone
    return (
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={openPicker}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openPicker(); } }}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        aria-invalid={invalid || undefined}
        className={cn(
          "flex w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center text-sm transition-colors",
          isDragging
            ? "border-brand-primary bg-brand-soft/30"
            : invalid
              ? "border-danger bg-danger-subtle/30"
              : "border-border bg-surface-base hover:bg-surface-overlay",
          disabled && "cursor-not-allowed opacity-50",
          focusRing,
          className,
        )}
        data-testid="file-dropzone"
      >
        {hiddenInput}
        <span aria-hidden className="text-2xl">⬆</span>
        <div>
          <strong className="text-fg">Dosya bırak</strong>
          <span className="text-fg-muted"> ya da tıklayıp seç</span>
        </div>
        {hint && <div className="text-xs text-fg-subtle">{hint}</div>}
        {fileList.length > 0 && (
          <div className="mt-2 text-xs text-fg-muted">
            {fileList.length === 1 ? fileList[0].name : `${fileList.length} dosya seçildi`}
          </div>
        )}
      </div>
    );
  },
);

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}
