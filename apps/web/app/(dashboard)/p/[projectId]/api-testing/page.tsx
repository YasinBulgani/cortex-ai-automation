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
  useApiTestingStats,
  useImportSpec,
  useAiGenerate,
  useExecuteSingle,
  type ApiEndpoint,
  type ApiTestCase,
} from "@/lib/hooks/use-api-testing";
import {
  statusCodeColor,
  TEST_TYPE_COLORS,
  STATUS_COLORS,
  RISK_COLORS,
  METHOD_COLORS,
} from "./_components/constants";
import { Badge } from "./_components/Badge";

/* ── Stats Cards ─────────────────────────────────────────────────────── */
function StatsGrid({ projectId }: { projectId: string }) {
  const { data: stats } = useApiTestingStats(projectId);
  if (!stats) return null;

  const cards = [
    { label: "API Spec", value: stats.specs, icon: "📄" },
    { label: "Endpoint", value: stats.endpoints, icon: "🔗" },
    { label: "Test Case", value: stats.test_cases, icon: "🧪" },
    { label: "AI Generated", value: stats.ai_generated, icon: "🤖" },
    { label: "Chain", value: stats.chains, icon: "⛓" },
    { label: "Pass Rate", value: `${stats.last_run.pass_rate}%`, icon: "✅" },
  ];

  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-center">
          <div className="text-lg">{c.icon}</div>
          <div className="text-xl font-bold text-white">{c.value}</div>
          <div className="text-[10px] text-slate-500">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

/* ── Spec Import Panel (URL + File Upload + Paste) ──────────────────── */
function SpecImportPanel({ projectId }: { projectId: string }) {
  const [url, setUrl] = useState("");
  const [rawContent, setRawContent] = useState("");
  const [importMode, setImportMode] = useState<"url" | "file" | "paste">("url");
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState("");
  const importSpec = useImportSpec(projectId);

  const handleImportUrl = () => {
    if (!url.trim()) return;
    importSpec.mutate({ source_url: url.trim() });
    setUrl("");
  };

  const handleImportContent = () => {
    if (!rawContent.trim()) return;
    importSpec.mutate({ content: rawContent.trim(), name: fileName || undefined });
    setRawContent("");
    setFileName("");
  };

  const handleFile = (file: File) => {
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setRawContent(text);
      setImportMode("paste");
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith(".json") || file.name.endsWith(".yaml") || file.name.endsWith(".yml"))) {
      handleFile(file);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="space-y-3">
      {/* Mode Tabs */}
      <div className="flex gap-1">
        {([
          { key: "url" as const, label: "URL" },
          { key: "file" as const, label: "Dosya Yükle" },
          { key: "paste" as const, label: "Yapistir" },
        ]).map((m) => (
          <button
            key={m.key}
            onClick={() => setImportMode(m.key)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              importMode === m.key
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* URL Mode */}
      {importMode === "url" && (
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleImportUrl()}
            placeholder="OpenAPI/Swagger URL (orn: https://api.example.com/openapi.json)"
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/60"
            data-testid="spec-import-url"
          />
          <button
            onClick={handleImportUrl}
            disabled={importSpec.isPending || !url.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors whitespace-nowrap"
            data-testid="spec-import-btn"
          >
            {importSpec.isPending ? "Yükleniyor..." : "Import"}
          </button>
        </div>
      )}

      {/* File Upload Mode */}
      {importMode === "file" && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
            dragOver
              ? "border-blue-500 bg-blue-500/10"
              : "border-slate-700 bg-slate-800/30 hover:border-slate-600"
          }`}
        >
          <div className="text-2xl mb-2">📄</div>
          <p className="text-sm text-slate-400 mb-2">
            JSON veya YAML dosyasini surukleyin
          </p>
          <label className="inline-flex cursor-pointer rounded-lg bg-slate-700 px-4 py-2 text-xs font-medium text-white hover:bg-slate-600 transition-colors">
            Dosya Sec
            <input
              type="file"
              accept=".json,.yaml,.yml"
              onChange={handleFileInput}
              className="hidden"
            />
          </label>
          <p className="text-[10px] text-slate-600 mt-2">.json, .yaml, .yml</p>
        </div>
      )}

      {/* Paste Mode */}
      {importMode === "paste" && (
        <div className="space-y-2">
          {fileName && (
            <div className="flex items-center gap-2 text-xs text-blue-400">
              <span>📄</span> {fileName}
            </div>
          )}
          <textarea
            value={rawContent}
            onChange={(e) => setRawContent(e.target.value)}
            rows={8}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500/60"
            placeholder={'{\n  "openapi": "3.0.3",\n  "info": { "title": "My API", "version": "1.0" },\n  "paths": { ... }\n}'}
          />
          <button
            onClick={handleImportContent}
            disabled={importSpec.isPending || !rawContent.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {importSpec.isPending ? "Yükleniyor..." : "Import Et"}
          </button>
        </div>
      )}

      {/* Status */}
      {importSpec.isSuccess && (
        <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-2 text-xs text-emerald-300">
          Spec basariyla import edildi!
        </div>
      )}
      {importSpec.error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-2 text-xs text-red-300">
          {importSpec.error instanceof Error ? importSpec.error.message : "Import hatasi"}
        </div>
      )}
    </div>
  );
}

/* ── Endpoint Table ──────────────────────────────────────────────────── */
function EndpointTable({
  projectId,
  specId,
  onSelect,
  selectedId,
  riskFilter: _riskFilter,
}: {
  projectId: string;
  specId?: string;
  onSelect: (ep: ApiEndpoint) => void;
  selectedId?: string;
  riskFilter?: string;
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

/* ── AI Generate Panel ───────────────────────────────────────────────── */
function AiGeneratePanel({
  projectId,
  specId,
  endpointIds,
}: {
  projectId: string;
  specId?: string;
  endpointIds?: string[];
}) {
  const generate = useAiGenerate(projectId);
  const [mode, setMode] = useState("test_generation");

  const handleGenerate = () => {
    generate.mutate({
      mode,
      spec_id: specId,
      endpoint_ids: endpointIds,
      regulations: ["BDDK", "KVKK"],
      test_types: ["positive", "negative", "boundary", "security", "compliance"],
      max_tests_per_endpoint: 6,
    });
  };

  return (
    <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-lg">🤖</span>
        <h3 className="text-sm font-semibold text-blue-300">AI Test Uretimi</h3>
      </div>

      <div className="flex gap-2 flex-wrap">
        {[
          { value: "test_generation", label: "Test Case" },
          { value: "security_audit", label: "Guvenlik Denetimi" },
          { value: "chain_builder", label: "Chain Oluştur" },
        ].map((m) => (
          <button
            key={m.value}
            onClick={() => setMode(m.value)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              mode === m.value
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <button
        onClick={handleGenerate}
        disabled={generate.isPending}
        className="w-full rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-2 text-sm font-semibold text-white hover:from-blue-500 hover:to-purple-500 disabled:opacity-50 transition-all"
        data-testid="ai-generate-btn"
      >
        {generate.isPending ? (
          <span className="flex items-center justify-center gap-2">
            <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
            AI Üretiyor...
          </span>
        ) : (
          `${endpointIds?.length ?? "Tüm"} endpoint için ${mode === "test_generation" ? "test üret" : mode === "security_audit" ? "guvenlik tara" : "chain oluştur"}`
        )}
      </button>

      {generate.data && (
        <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-xs text-emerald-300">
          <strong>{generate.data.generated_count}</strong> test case üretildi
          ({generate.data.ai_model}, {generate.data.duration_ms}ms)
          {generate.data.warnings.length > 0 && (
            <div className="mt-1 text-amber-400">
              Uyarilar: {generate.data.warnings.join("; ")}
            </div>
          )}
        </div>
      )}

      {generate.error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-300">
          Hata: {generate.error instanceof Error ? generate.error.message : String(generate.error)}
        </div>
      )}
    </div>
  );
}

/* ── Test Case Edit Modal ────────────────────────────────────────────── */
function TestCaseEditModal({
  tc,
  onClose,
  onSend,
}: {
  tc: ApiTestCase;
  onClose: () => void;
  onSend: (method: string, url: string, headers: Record<string, string>, body: unknown, assertions: Record<string, unknown>[]) => void;
}) {
  const [title, setTitle] = useState(tc.title);
  const [method, setMethod] = useState(tc.request_method);
  const [path, setPath] = useState(tc.request_path);
  const [headersText, setHeadersText] = useState(JSON.stringify(tc.request_headers || {}, null, 2));
  const [bodyText, setBodyText] = useState(tc.request_body ? JSON.stringify(tc.request_body, null, 2) : "");
  const [assertionsText, setAssertionsText] = useState(JSON.stringify(tc.assertions || [], null, 2));
  const [editTab, setEditTab] = useState<"request" | "assertions" | "info">("request");

  const handleQuickRun = () => {
    let headers: Record<string, string> = {};
    let body: unknown = undefined;
    let assertions: Record<string, unknown>[] = [];
    try { headers = JSON.parse(headersText || "{}"); } catch { /* skip */ }
    try { body = bodyText ? JSON.parse(bodyText) : undefined; } catch { body = bodyText; }
    try { assertions = JSON.parse(assertionsText || "[]"); } catch { /* skip */ }
    onSend(method, path, headers, body, assertions);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <div className="flex items-center gap-2">
            <Badge text={tc.test_type} className={TEST_TYPE_COLORS[tc.test_type] ?? ""} />
            <Badge text={tc.priority} className={tc.priority === "P0" ? "bg-red-500/15 text-red-400" : "bg-slate-700 text-slate-400"} />
            {tc.ai_generated && <span className="text-[10px] text-blue-400 font-medium">AI Generated</span>}
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors text-lg">&times;</button>
        </div>

        {/* Title */}
        <div className="px-5 pt-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-sm text-white font-medium focus:outline-none focus:border-blue-500/60"
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-5 pt-3 border-b border-slate-800">
          {(["request", "assertions", "info"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setEditTab(t)}
              className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors ${
                editTab === t ? "border-blue-500 text-blue-400" : "border-transparent text-slate-500 hover:text-slate-300"
              }`}
            >
              {t === "request" ? "Request" : t === "assertions" ? "Assertions" : "Bilgi"}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-5 max-h-[400px] overflow-y-auto">
          {editTab === "request" && (
            <div className="space-y-3">
              <div className="flex gap-2">
                <select
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-white"
                >
                  {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                <input
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500/60"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Headers</label>
                <textarea
                  value={headersText}
                  onChange={(e) => setHeadersText(e.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 font-mono focus:outline-none focus:border-blue-500/60"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Body</label>
                <textarea
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  rows={4}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 font-mono focus:outline-none focus:border-blue-500/60"
                />
              </div>
            </div>
          )}

          {editTab === "assertions" && (
            <div className="space-y-2">
              <textarea
                value={assertionsText}
                onChange={(e) => setAssertionsText(e.target.value)}
                rows={10}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 font-mono focus:outline-none focus:border-blue-500/60"
                placeholder='[{"type":"status_code","expected":200}]'
              />
              <p className="text-[10px] text-slate-600">
                Tipler: status_code, json_path, header, response_time, schema, regex, exists
              </p>
            </div>
          )}

          {editTab === "info" && (
            <div className="space-y-3 text-xs">
              {tc.description && <p className="text-slate-400">{tc.description}</p>}
              {tc.ai_reasoning && (
                <div className="rounded-lg bg-blue-500/5 border border-blue-500/20 p-3 text-blue-300">
                  <span className="font-semibold block mb-1">AI Mantigi:</span>
                  {tc.ai_reasoning}
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                {tc.owasp_category && (
                  <div>
                    <span className="text-slate-500 block mb-1">OWASP</span>
                    <Badge text={tc.owasp_category} className="bg-purple-500/15 text-purple-400 border-purple-500/30" />
                  </div>
                )}
                {tc.regulation && (
                  <div>
                    <span className="text-slate-500 block mb-1">Regulasyon</span>
                    <Badge text={tc.regulation} className="bg-blue-500/15 text-blue-400 border-blue-500/30" />
                  </div>
                )}
              </div>
              <div className="flex gap-4 text-slate-500 font-mono">
                <span>Koşu: {tc.run_count}</span>
                <span>Gecen: {tc.pass_count}</span>
                <span>Kalan: {tc.fail_count}</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-slate-800 px-5 py-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 transition-colors"
          >
            Kapat
          </button>
          <button
            onClick={handleQuickRun}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 transition-colors"
          >
            Çalıştır
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Test Case List ──────────────────────────────────────────────────── */
function TestCaseList({ projectId, endpointId }: { projectId: string; endpointId?: string }) {
  const { data: testCases = [], isLoading } = useApiTestCases(projectId, { endpoint_id: endpointId });
  const execute = useExecuteTestCases(projectId);
  const executeSingle = useExecuteSingle(projectId);
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingTc, setEditingTc] = useState<ApiTestCase | null>(null);

  const testTypes = [...new Set(testCases.map((tc) => tc.test_type))];
  const statuses = [...new Set(testCases.map((tc) => tc.last_run_status))];
  const filtered = testCases.filter((tc) =>
    (!typeFilter || tc.test_type === typeFilter) &&
    (!statusFilter || tc.last_run_status === statusFilter)
  );

  function handleRunSingle(tc: ApiTestCase) {
    executeSingle.mutate({
      method: tc.request_method,
      url: tc.request_path,
      headers: tc.request_headers ?? {},
      body: tc.request_body,
      assertions: tc.assertions ?? [],
    });
  }

  function handleModalRun(method: string, url: string, headers: Record<string, string>, body: unknown, assertions: Record<string, unknown>[]) {
    executeSingle.mutate({ method, url, headers, body, assertions });
    setEditingTc(null);
  }

  if (isLoading) return <div className="p-4 text-sm text-slate-500">Yukleniyor...</div>;
  if (testCases.length === 0) return <EmptyState title="Test case yok" description="AI ile test üretimi yapin" />;

  const handleRunAll = () => execute.mutate({ test_case_ids: testCases.map((tc) => tc.id) });

  return (
    <div className="space-y-2">
      {/* Filters + Actions */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{filtered.length}/{testCases.length} test case</span>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-[10px] text-slate-300"
          >
            <option value="">Tüm tipler</option>
            {testTypes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-[10px] text-slate-300"
          >
            <option value="">Tüm durumlar</option>
            {statuses.map((s) => <option key={s} value={s!}>{s}</option>)}
          </select>
        </div>
        <button
          onClick={handleRunAll}
          disabled={execute.isPending}
          data-testid="run-tests-btn"
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {execute.isPending ? "Çalışiyor..." : `${filtered.length} Testi Çalıştır`}
        </button>
      </div>

      {execute.data && (
        <div className="rounded-lg bg-slate-800 border border-slate-700 p-3 text-xs flex gap-4">
          <span className="text-emerald-400">Geçen: {execute.data.passed}</span>
          <span className="text-red-400">Kalan: {execute.data.failed}</span>
          <span className="text-slate-400">{execute.data.duration_ms}ms</span>
        </div>
      )}

      <div className="max-h-[400px] overflow-y-auto space-y-1">
        {filtered.map((tc) => (
          <div key={tc.id} className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
            <button
              onClick={() => setExpandedId(expandedId === tc.id ? null : tc.id)}
              className="w-full flex items-center gap-2 p-2.5 text-left hover:bg-slate-800/50 transition-colors"
            >
              <Badge text={tc.test_type} className={TEST_TYPE_COLORS[tc.test_type] ?? ""} />
              <Badge text={tc.priority} className={tc.priority === "P0" ? "bg-red-500/15 text-red-400" : tc.priority === "P1" ? "bg-orange-500/15 text-orange-400" : "bg-slate-700 text-slate-400"} />
              <span className="flex-1 text-xs text-slate-300 truncate">{tc.title}</span>
              {tc.last_run_status && (
                <span className={`text-[10px] font-medium ${STATUS_COLORS[tc.last_run_status] ?? ""}`}>
                  {tc.last_run_status}
                </span>
              )}
              {tc.ai_generated && <span className="text-[10px] text-blue-400">AI</span>}
              <Badge text={`${tc.request_method} ${tc.request_path}`} className={METHOD_COLORS[tc.request_method] ?? ""} />
            </button>

            {expandedId === tc.id && (
              <div className="border-t border-slate-800 p-3 space-y-2 text-xs">
                {tc.description && <p className="text-slate-400">{tc.description}</p>}
                {tc.ai_reasoning && (
                  <div className="rounded bg-blue-500/5 border border-blue-500/20 p-2 text-blue-300">
                    <span className="font-semibold">AI Mantigi:</span> {tc.ai_reasoning}
                  </div>
                )}
                <div className="flex gap-1 flex-wrap">
                  {tc.owasp_category && <Badge text={`OWASP ${tc.owasp_category}`} className="bg-purple-500/15 text-purple-400 border-purple-500/30" />}
                  {tc.regulation && <Badge text={tc.regulation} className="bg-blue-500/15 text-blue-400 border-blue-500/30" />}
                </div>
                <div className="font-mono text-slate-500">
                  {tc.assertions.length} assertion
                  {tc.run_count > 0 && ` | ${tc.pass_count}/${tc.run_count} başarılı`}
                </div>
                {/* Action Buttons */}
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRunSingle(tc); }}
                    className="rounded-lg bg-emerald-600/80 px-3 py-1 text-[10px] font-semibold text-white hover:bg-emerald-500 transition-colors"
                  >
                    Çalıştır
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditingTc(tc); }}
                    className="rounded-lg bg-blue-600/80 px-3 py-1 text-[10px] font-semibold text-white hover:bg-blue-500 transition-colors"
                  >
                    Düzenle / Detay
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Edit Modal */}
      {editingTc && (
        <TestCaseEditModal
          tc={editingTc}
          onClose={() => setEditingTc(null)}
          onSend={handleModalRun}
        />
      )}
    </div>
  );
}

/* ── Request Builder (Postman-style) ─────────────────────────────────── */
function RequestBuilder({ projectId }: { projectId: string }) {
  const [method, setMethod] = useState("GET");
  const [url, setUrl] = useState("");
  const [headersText, setHeadersText] = useState('{"Content-Type": "application/json"}');
  const [bodyText, setBodyText] = useState("");
  const [tab, setTab] = useState<"headers" | "body" | "assertions">("headers");
  const [assertionsText, setAssertionsText] = useState('[{"type":"status_code","expected":200}]');

  const executeMut = useExecuteSingle(projectId);
  const result = executeMut.data;

  const handleSend = () => {
    let headers: Record<string, string> = {};
    let body: unknown = undefined;
    let assertions: Record<string, unknown>[] = [];
    try { headers = JSON.parse(headersText || "{}"); } catch { /* skip */ }
    try { body = bodyText ? JSON.parse(bodyText) : undefined; } catch { body = bodyText; }
    try { assertions = JSON.parse(assertionsText || "[]"); } catch { /* skip */ }

    executeMut.mutate({ method, url, headers, body, assertions });
  };

  return (
    <div className="space-y-3">
      {/* URL Bar */}
      <div className="flex gap-2">
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-semibold text-white"
          data-testid="request-method"
        >
          {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="https://api.example.com/v1/endpoint"
          className="flex-1 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-sm text-white font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500/60"
          data-testid="request-url"
        />
        <button
          onClick={handleSend}
          disabled={executeMut.isPending || !url.trim()}
          className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-bold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          data-testid="request-send"
        >
          {executeMut.isPending ? "..." : "Send"}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-800">
        {(["headers", "body", "assertions"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors ${
              tab === t ? "border-blue-500 text-blue-400" : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            {t === "headers" ? "Headers" : t === "body" ? "Body" : "Assertions"}
          </button>
        ))}
      </div>

      {tab === "headers" && (
        <textarea
          value={headersText}
          onChange={(e) => setHeadersText(e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500/60"
          placeholder='{"Authorization": "Bearer {{token}}"}'
        />
      )}
      {tab === "body" && (
        <textarea
          value={bodyText}
          onChange={(e) => setBodyText(e.target.value)}
          rows={5}
          className="w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500/60"
          placeholder='{"email": "test@test.com", "password": "test"}'
        />
      )}
      {tab === "assertions" && (
        <textarea
          value={assertionsText}
          onChange={(e) => setAssertionsText(e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500/60"
          placeholder='[{"type":"status_code","expected":200},{"type":"json_path","path":"$.token","operator":"exists"}]'
        />
      )}

      {/* Response */}
      {result && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
          <div className="flex items-center gap-3 border-b border-slate-800 px-4 py-2">
            <span className={`text-sm font-bold ${statusCodeColor(result.status_code ?? 0)}`}>
              {result.status_code ?? "ERR"}
            </span>
            <span className="text-xs text-slate-500">{result.total_ms.toFixed(0)}ms</span>
            <span className="text-xs text-slate-500">{result.response_size_bytes}B</span>
            {result.assertion_results.length > 0 && (
              <span className={`text-xs font-medium ${result.passed ? "text-emerald-400" : "text-red-400"}`}>
                {result.assertion_results.filter((a) => a.passed).length}/{result.assertion_results.length} passed
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ApiTestingPage() {
  const projectId = useRouteParam("projectId");
  const { data: specs = [] } = useApiSpecs(projectId);
  const [selectedSpec, setSelectedSpec] = useState<string | undefined>();
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null);
  const [tab, setTab] = useState<"endpoints" | "test-cases" | "request">("endpoints");
  const activeTab = tab;
  const [riskFilter, setRiskFilter] = useState<string>("");

  useEffect(() => {
    if (specs.length > 0 && !selectedSpec) setSelectedSpec(specs[0].id);
  }, [specs, selectedSpec]);

  return (
    <div className="mx-auto max-w-6xl space-y-4" data-testid="api-testing-page">
      <PageHeader
        title="API Testing Intelligence"
        description="AI destekli servis test otomasyonu — Spec import, test üretimi, guvenlik taramasi"
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

      {/* Tab Content */}
      {activeTab === "endpoints" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Endpoint List (2/3) */}
          <div className="lg:col-span-2">
            <SectionCard
              title="Endpoint Envanteri"
              right={
                <div className="flex gap-1">
                  {["", "critical", "high", "medium", "low"].map((r) => (
                    <button
                      key={r}
                      onClick={() => setRiskFilter(r)}
                      className={`rounded px-2 py-1 text-[10px] font-medium transition-colors ${
                        riskFilter === r
                          ? "bg-blue-600 text-white"
                          : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                      }`}
                    >
                      {r || "Tumu"}
                    </button>
                  ))}
                </div>
              }
            >
              <EndpointTable
                projectId={projectId}
                specId={selectedSpec}
                riskFilter={riskFilter}
                onSelect={setSelectedEndpoint}
                selectedId={selectedEndpoint?.id}
              />
            </SectionCard>
          </div>

          {/* AI Panel (1/3) */}
          <div className="space-y-4">
            <AiGeneratePanel
              projectId={projectId}
              specId={selectedSpec}
              endpointIds={selectedEndpoint ? [selectedEndpoint.id] : undefined}
            />
            {selectedEndpoint && (
              <SectionCard title="Seçili Endpoint">
                <div className="space-y-2 text-xs">
                  <p className="text-slate-400 font-mono text-[10px]">{selectedEndpoint.method} {selectedEndpoint.path}</p>
                  {selectedEndpoint.summary && <p className="text-slate-300">{selectedEndpoint.summary}</p>}
                  <div className="flex gap-1 flex-wrap">
                    <Badge text={selectedEndpoint.risk_level} className={RISK_COLORS[selectedEndpoint.risk_level]} />
                    {selectedEndpoint.has_pii && <Badge text="PII" className="bg-red-500/10 text-red-400 border-red-500/30" />}
                    {selectedEndpoint.has_financial && <Badge text="Finansal" className="bg-amber-500/10 text-amber-400 border-amber-500/30" />}
                    {selectedEndpoint.compliance_tags.map((t) => (
                      <Badge key={t} text={t} className="bg-purple-500/10 text-purple-400 border-purple-500/30" />
                    ))}
                  </div>
                  {selectedEndpoint.parameters.length > 0 && (
                    <div>
                      <span className="text-slate-500 font-semibold">Parametreler:</span>
                      {selectedEndpoint.parameters.map((p: any, i: number) => (
                        <div key={i} className="ml-2 text-slate-400">
                          <code>{p.name}</code> ({p.in}) {p.required && <span className="text-red-400">*</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </SectionCard>
            )}
          </div>
        </div>
      )}

      {activeTab === "request" && (
        <SectionCard title="Request Builder">
          <RequestBuilder projectId={projectId} />
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
