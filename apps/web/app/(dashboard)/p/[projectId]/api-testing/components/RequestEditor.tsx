"use client";

import { useState } from "react";
import { useExecuteSingle } from "@/lib/hooks/use-api-testing";

function statusCodeColor(code: number): string {
  if (code >= 500) return "text-red-400";
  if (code >= 400) return "text-amber-400";
  if (code >= 200) return "text-emerald-400";
  return "text-slate-400";
}

export interface RequestEditorProps {
  projectId: string;
}

export function RequestEditor({ projectId }: RequestEditorProps) {
  const [method, setMethod] = useState("GET");
  const [url, setUrl] = useState("");
  const [headersText, setHeadersText] = useState(
    '{"Content-Type": "application/json"}'
  );
  const [bodyText, setBodyText] = useState("");
  const [tab, setTab] = useState<"headers" | "body" | "assertions">("headers");
  const [assertionsText, setAssertionsText] = useState(
    '[{"type":"status_code","expected":200}]'
  );

  const executeMut = useExecuteSingle(projectId);
  const result = executeMut.data;

  const handleSend = () => {
    let headers: Record<string, string> = {};
    let body: unknown = undefined;
    let assertions: Record<string, unknown>[] = [];
    try {
      headers = JSON.parse(headersText || "{}");
    } catch {
      /* skip */
    }
    try {
      body = bodyText ? JSON.parse(bodyText) : undefined;
    } catch {
      body = bodyText;
    }
    try {
      assertions = JSON.parse(assertionsText || "[]");
    } catch {
      /* skip */
    }

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
            <option key={m} value={m}>
              {m}
            </option>
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
              tab === t
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-slate-500 hover:text-slate-300"
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

      {/* Response Viewer */}
      {result && (
        <ResponseViewer result={result} />
      )}
    </div>
  );
}

// ── Inline ResponseViewer (used within RequestEditor) ──────────────────────
export interface ExecuteResult {
  status_code?: number;
  total_ms: number;
  response_size_bytes: number;
  passed: boolean;
  assertion_results: Array<{ passed: boolean }>;
  body?: unknown;
}

export interface ResponseViewerProps {
  result: ExecuteResult;
}

export function ResponseViewer({ result }: ResponseViewerProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
      <div className="flex items-center gap-3 border-b border-slate-800 px-4 py-2">
        <span
          className={`text-sm font-bold ${statusCodeColor(result.status_code ?? 0)}`}
        >
          {result.status_code ?? "ERR"}
        </span>
        <span className="text-xs text-slate-500">
          {result.total_ms.toFixed(0)}ms
        </span>
        <span className="text-xs text-slate-500">
          {result.response_size_bytes}B
        </span>
        {result.assertion_results.length > 0 && (
          <span
            className={`text-xs font-medium ${
              result.passed ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {result.assertion_results.filter((a) => a.passed).length}/
            {result.assertion_results.length} passed
          </span>
        )}
      </div>
    </div>
  );
}
