"use client";

import dynamic from "next/dynamic";

const FlowDetailEditor = dynamic(() => import("./FlowDetailEditor"), {
  ssr: false,
  loading: () => (
    <div
      className="flex min-h-[50vh] flex-col items-center justify-center gap-3 p-8"
      data-testid="flow-editor-loading"
    >
      <div
        className="h-8 w-8 animate-spin rounded-full border-2 border-slate-800 border-t-accent"
        aria-hidden
      />
      <p className="text-sm text-slate-400">Akış düzenleyici yükleniyor...</p>
    </div>
  ),
});

export default function FlowDetailPage() {
  return <FlowDetailEditor />;
}
