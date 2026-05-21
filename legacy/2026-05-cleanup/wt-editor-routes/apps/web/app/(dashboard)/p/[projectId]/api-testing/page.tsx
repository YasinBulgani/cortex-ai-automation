"use client";

import { useEffect, useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import {
  useApiSpecs,
  useApiEndpoints,
  useApiTestCases,
  useExecuteTestCases,
  type ApiEndpoint,
} from "@/lib/hooks/use-api-testing";

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  POST: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  PUT: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  PATCH: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  DELETE: "bg-red-500/15 text-red-400 border-red-500/30",
};

function Badge({ text, className }: { text: string; className?: string }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${className ?? "bg-slate-800 text-slate-400 border-slate-700"}`}>
      {text}
    </span>
  );
}

function EndpointTable({
  projectId,
  specId,
  onSelect,
  selectedId,
}: {
  projectId: string;
  specId?: string;
  onSelect: (ep: ApiEndpoint) => void;
  selectedId?: string;
}) {
  const { data: endpoints = [], isLoading } = useApiEndpoints(projectId, { spec_id: specId });

  if (isLoading) return <div className="p-4 text-sm text-slate-500">Yükleniyor...</div>;
  if (endpoints.length === 0) return <EmptyState title="Endpoint yok" description="Bir API spec import edin" />;

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
                selectedId === ep.id ? "bg-blue-500/10" : "hover:bg-slate-800/50"
              }`}
            >
              <td className="p-2">
                <Badge text={ep.method} className={METHOD_COLORS[ep.method]} />
              </td>
              <td className="p-2 font-mono text-slate-300 truncate max-w-xs">{ep.path}</td>
              <td className="p-2 text-center text-slate-400">{ep.test_case_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TestCaseList({ projectId, endpointId }: { projectId: string; endpointId?: string }) {
  const { data: testCases = [], isLoading } = useApiTestCases(projectId, { endpoint_id: endpointId });
  const execute = useExecuteTestCases(projectId);

  if (isLoading) return <div className="p-4 text-sm text-slate-500">Yükleniyor...</div>;
  if (testCases.length === 0) return <EmptyState title="Test case yok" description="AI ile test üretimi yapın" />;

  const handleRunAll = () => execute.mutate({ test_case_ids: testCases.map((tc) => tc.id) });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">{testCases.length} test case</span>
        <button
          onClick={handleRunAll}
          disabled={execute.isPending}
          data-testid="run-tests-btn"
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {execute.isPending ? "Çalışıyor..." : "Tümünü Çalıştır"}
        </button>
      </div>

      {execute.data && (
        <div className="rounded-lg bg-slate-800 border border-slate-700 p-3 text-xs flex gap-4">
          <span className="text-emerald-400">Geçen: {execute.data.passed}</span>
          <span className="text-red-400">Kalan: {execute.data.failed}</span>
          <span className="text-slate-400">{execute.data.duration_ms}ms</span>
        </div>
      )}

      <div className="max-h-[350px] overflow-y-auto space-y-1">
        {testCases.map((tc) => (
          <div key={tc.id} className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/30 p-2.5">
            <Badge text={tc.test_type} />
            <Badge text={tc.request_method} className={METHOD_COLORS[tc.request_method]} />
            <span className="flex-1 text-xs text-slate-300 truncate">{tc.title}</span>
            {tc.last_run_status && (
              <span className={`text-[10px] font-medium ${tc.last_run_status === "passed" ? "text-emerald-400" : "text-red-400"}`}>
                {tc.last_run_status}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ApiTestingPage() {
  const projectId = useRouteParam("projectId");
  const { data: specs = [] } = useApiSpecs(projectId);
  const [selectedSpec, setSelectedSpec] = useState<string | undefined>();
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null);
  const [tab, setTab] = useState<"endpoints" | "test-cases">("endpoints");

  useEffect(() => {
    if (specs.length > 0 && !selectedSpec) setSelectedSpec(specs[0].id);
  }, [specs, selectedSpec]);

  return (
    <div className="mx-auto max-w-6xl space-y-4" data-testid="api-testing-page">
      <PageHeader
        title="API Testing"
        description="Spec import, endpoint envanteri ve test koşumu"
      />

      {/* Spec selector */}
      {specs.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {specs.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedSpec(s.id)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                selectedSpec === s.id
                  ? "border-blue-500/50 bg-blue-500/10 text-blue-300"
                  : "border-slate-700 bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              {s.name} ({s.endpoint_count} ep)
            </button>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-800">
        {([
          { key: "endpoints" as const, label: "Endpoints", icon: "🔗" },
          { key: "test-cases" as const, label: "Test Cases", icon: "🧪" },
        ]).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            <span>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {tab === "endpoints" && (
        <SectionCard title="Endpoint Envanteri">
          <EndpointTable
            projectId={projectId}
            specId={selectedSpec}
            onSelect={setSelectedEndpoint}
            selectedId={selectedEndpoint?.id}
          />
        </SectionCard>
      )}

      {tab === "test-cases" && (
        <SectionCard title="Test Cases">
          <TestCaseList projectId={projectId} endpointId={selectedEndpoint?.id} />
        </SectionCard>
      )}
    </div>
  );
}
