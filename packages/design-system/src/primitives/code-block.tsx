"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { useCopyToClipboard } from "../hooks/use-copy-to-clipboard";

export interface CodeBlockProps extends Omit<React.HTMLAttributes<HTMLPreElement>, "title"> {
  /** Kod içeriği (string olarak verilirse copy-button çalışır) */
  code: string;
  /** Dil ipucu (sadece visual badge; syntax highlight için kullanılmıyor) */
  language?: string;
  /** Başlık (dosya adı vb.) */
  title?: React.ReactNode;
  /** Copy butonu (default true) */
  showCopy?: boolean;
  /** Line numbers göster */
  showLineNumbers?: boolean;
  /** Max yükseklik (overflow auto-scroll) */
  maxHeight?: string;
}

export function CodeBlock({
  code,
  language,
  title,
  showCopy = true,
  showLineNumbers,
  maxHeight = "24rem",
  className,
  ...rest
}: CodeBlockProps) {
  const { copied, copy } = useCopyToClipboard(2000);
  const lines = code.split("\n");

  return (
    <div className={cn("rounded-lg border border-border bg-surface-base overflow-hidden", className)}>
      {(title || language || showCopy) && (
        <div className="flex items-center justify-between gap-3 border-b border-border bg-surface-overlay/50 px-3 py-1.5 text-xs">
          <div className="flex items-center gap-2 min-w-0">
            {title && <span className="font-medium text-fg truncate">{title}</span>}
            {language && (
              <span className="rounded bg-surface-overlay px-1.5 py-0.5 text-[10px] uppercase text-fg-muted">
                {language}
              </span>
            )}
          </div>
          {showCopy && (
            <button
              type="button"
              onClick={() => copy(code)}
              className={cn(
                "shrink-0 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-fg-muted hover:text-fg hover:bg-surface-overlay transition-colors",
              )}
              aria-label={copied ? "Kopyalandı" : "Kopyala"}
              data-testid="code-block-copy"
            >
              {copied ? "✓ Kopyalandı" : "📋 Kopyala"}
            </button>
          )}
        </div>
      )}
      <pre
        className="overflow-auto p-3 text-xs leading-relaxed"
        style={{ maxHeight }}
        {...rest}
      >
        {showLineNumbers ? (
          <code className="block">
            {lines.map((line, i) => (
              <span key={i} className="flex">
                <span
                  aria-hidden
                  className="inline-block w-8 shrink-0 select-none pr-3 text-right text-fg-subtle"
                >
                  {i + 1}
                </span>
                <span className="flex-1">{line || " "}</span>
              </span>
            ))}
          </code>
        ) : (
          <code>{code}</code>
        )}
      </pre>
    </div>
  );
}
