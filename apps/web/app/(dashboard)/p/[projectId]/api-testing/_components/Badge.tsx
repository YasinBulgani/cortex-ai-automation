"use client";

/** Reusable colored badge pill for test types, status, risk, HTTP method, etc. */
export function Badge({ text, className }: { text: string; className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${
        className ?? "bg-slate-800 text-slate-400 border-slate-700"
      }`}
    >
      {text}
    </span>
  );
}
