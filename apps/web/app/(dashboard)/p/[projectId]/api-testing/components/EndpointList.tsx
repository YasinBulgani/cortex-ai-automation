"use client";

import { EmptyState } from "@/components/nexus/EmptyState";
import { useApiEndpoints, type ApiEndpoint } from "@/lib/hooks/use-api-testing";

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  POST: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  PUT: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  PATCH: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  DELETE: "bg-red-500/15 text-red-400 border-red-500/30",
};

function Badge({ text, className }: { text: string; className?: string }) {
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

export interface EndpointListProps {
  projectId: string;
  specId?: string;
  selectedId?: string;
  riskFilter?: string;
  onSelect: (ep: ApiEndpoint) => void;
}

export function EndpointList({
  projectId,
  specId,
  selectedId,
  riskFilter: _riskFilter,
  onSelect,
}: EndpointListProps) {
  const { data: endpoints = [], isLoading } = useApiEndpoints(projectId, {
    spec_id: specId,
  });

  if (isLoading)
    return <div className="p-4 text-sm text-slate-500">Yükleniyor...</div>;
  if (endpoints.length === 0)
    return (
      <EmptyState title="Endpoint yok" description="Bir API spec import edin" />
    );

  return (
    <div className="max-h-[420px] overflow-y-auto">
      <table className="w-full text-xs" data-testid="endpoint-table">
        <thead className="sticky top-0 bg-slate-900 z-10">
          <tr className="border-b border-slate-800 text-left text-slate-500">
            <th className="p-2 w-16">Method</th>
            <th className="p-2">Path</th>
            <th className="p-2 w-16 text-center">Test</th>
          </tr>
        </thead>
        <tbody>
          {endpoints.map((ep) => (
            <tr
              key={ep.id}
              onClick={() => onSelect(ep)}
              className={`cursor-pointer border-b border-slate-800/50 transition-colors ${
                selectedId === ep.id
                  ? "bg-blue-500/10"
                  : "hover:bg-slate-800/50"
              }`}
            >
              <td className="p-2">
                <Badge text={ep.method} className={METHOD_COLORS[ep.method]} />
              </td>
              <td className="p-2 font-mono text-slate-300 truncate max-w-xs">
                {ep.path}
              </td>
              <td className="p-2 text-center text-slate-400">
                {ep.test_case_count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
