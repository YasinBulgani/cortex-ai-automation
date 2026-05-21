"use client";
import React, { useState } from "react";

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
  maxHeight?: string;
}

export function CodeBlock({
  code, language = "text", filename, showLineNumbers = true, maxHeight = "400px",
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const lines = code.split("\n");

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900/60">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">{language}</span>
          {filename && (
            <>
              <span className="text-slate-700">·</span>
              <span className="text-xs text-slate-500">{filename}</span>
            </>
          )}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors px-2 py-1 rounded hover:bg-slate-800"
        >
          {copied ? (
            <>
              <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-emerald-400">Kopyalandı</span>
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Kopyala
            </>
          )}
        </button>
      </div>

      {/* Code */}
      <div className="overflow-auto" style={{ maxHeight }}>
        <pre className="text-sm font-mono text-slate-300 p-4 m-0">
          {showLineNumbers ? (
            <table className="w-full border-collapse">
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i} className="hover:bg-slate-900/60">
                    <td className="pr-4 text-slate-600 text-right select-none w-8 text-xs align-top pt-0.5">
                      {i + 1}
                    </td>
                    <td className="whitespace-pre">{line}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <code>{code}</code>
          )}
        </pre>
      </div>
    </div>
  );
}
