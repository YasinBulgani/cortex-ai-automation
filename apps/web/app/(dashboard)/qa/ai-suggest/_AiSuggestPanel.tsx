"use client";

import { useEffect, useState } from "react";

const SUITES = [
  "auth", "projects", "scenarios", "executions", "approvals", "rbac",
  "flows", "integrations", "api-tests", "reports", "admin", "billing",
  "notifications", "schedules", "imports", "regression", "requirements",
  "members", "dashboard", "bdd", "ai", "mobile", "a11y", "performance",
  "security", "synthetic-data", "engine", "visual-regression", "recorder",
  "datasim", "infrastructure", "qa-engine", "runs",
];

type Draft = { file_name: string; tc_id: string; title: string; priority: string };
type Response = {
  provider: string;
  drafts: Draft[];
  dry_run: boolean;
  prompt_preview?: string;
  stdout?: string;
  stderr?: string;
  exit_code: number;
};

export default function AiSuggestPanel() {
  const [form, setForm] = useState({
    suite: "auth",
    source: "requirement" as "requirement" | "brief",
    requirement: "",
    brief: "",
    max_cases: 3,
    dry_run: true,
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<Response | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reqOptions, setReqOptions] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/v1/qa/requirements")
      .then((r) => r.json())
      .then((items) => setReqOptions(items.map((r: any) => r.id).sort()))
      .catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const body: any = {
        suite: form.suite,
        max_cases: form.max_cases,
        dry_run: form.dry_run,
      };
      if (form.source === "requirement" && form.requirement) body.requirement = form.requirement;
      if (form.source === "brief" && form.brief) body.brief = form.brief;

      const res = await fetch("/api/v1/qa/ai-suggest", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submit} className="space-y-4 rounded border border-gray-200 bg-white p-5">
        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Suite *</span>
            <select
              value={form.suite}
              onChange={(e) => setForm({ ...form, suite: e.target.value })}
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
            >
              {SUITES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Max cases (1-10)</span>
            <input
              type="number"
              min={1}
              max={10}
              value={form.max_cases}
              onChange={(e) => setForm({ ...form, max_cases: parseInt(e.target.value) || 3 })}
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
            />
          </label>
        </div>

        <div className="flex gap-3 text-sm">
          <label className="flex items-center gap-1">
            <input type="radio" checked={form.source === "requirement"} onChange={() => setForm({ ...form, source: "requirement" })} />
            <span>Requirement ID'den</span>
          </label>
          <label className="flex items-center gap-1">
            <input type="radio" checked={form.source === "brief"} onChange={() => setForm({ ...form, source: "brief" })} />
            <span>Kısa brief'ten</span>
          </label>
        </div>

        {form.source === "requirement" ? (
          <label className="block text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Requirement</span>
            <input
              list="req-list"
              value={form.requirement}
              onChange={(e) => setForm({ ...form, requirement: e.target.value })}
              placeholder="REQ-AUTH-001"
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 font-mono text-sm"
            />
            <datalist id="req-list">
              {reqOptions.map((id) => <option key={id} value={id} />)}
            </datalist>
          </label>
        ) : (
          <label className="block text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Brief</span>
            <textarea
              value={form.brief}
              onChange={(e) => setForm({ ...form, brief: e.target.value })}
              rows={4}
              placeholder="Test the new MFA fallback flow with backup codes..."
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
            />
          </label>
        )}

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.dry_run}
            onChange={(e) => setForm({ ...form, dry_run: e.target.checked })}
          />
          <span>Dry-run (LLM çağırma, sadece prompt'u göster)</span>
        </label>

        {error && <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        <div className="flex items-center justify-between border-t border-gray-100 pt-3">
          <span className="text-xs text-gray-500">
            {form.dry_run ? "🟡 Dry-run — LLM çağrılmaz" : "🤖 Live — LLM çağrısı yapılacak (cost budget'a sayılır)"}
          </span>
          <button
            type="submit"
            disabled={submitting || (form.source === "requirement" && !form.requirement) || (form.source === "brief" && !form.brief)}
            className="rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
          >
            {submitting ? "Üretiliyor..." : "AI ile üret"}
          </button>
        </div>
      </form>

      {result && <ResultView r={result} suite={form.suite} />}
    </div>
  );
}

function ResultView({ r, suite }: { r: Response; suite: string }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 rounded border border-blue-200 bg-blue-50 p-3">
        <span className="text-2xl">{r.dry_run ? "🟡" : r.exit_code === 0 ? "✓" : "✗"}</span>
        <div className="flex-1">
          <div className="font-semibold">
            {r.dry_run ? "Dry-run tamamlandı" : r.exit_code === 0 ? `${r.drafts.length} draft üretildi` : "Çağrı başarısız"}
          </div>
          <div className="text-xs text-gray-600">
            Provider: <code>{r.provider}</code> · Exit: {r.exit_code}
          </div>
        </div>
      </div>

      {r.drafts.length > 0 && (
        <section className="rounded border border-gray-200 bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Üretilen draft'lar
          </h3>
          <ul className="space-y-2">
            {r.drafts.map((d) => (
              <li key={d.file_name} className="flex items-center justify-between rounded bg-gray-50 p-3">
                <div>
                  <div className="font-mono text-xs text-gray-500">{d.tc_id}</div>
                  <div className="text-sm font-medium">{d.title}</div>
                  <div className="text-xs text-gray-400">{d.file_name}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded px-2 py-0.5 text-xs font-semibold ${
                    d.priority === "P0" ? "bg-red-100 text-red-700"
                    : d.priority === "P1" ? "bg-amber-100 text-amber-700"
                    : "bg-blue-100 text-blue-700"
                  }`}>
                    {d.priority}
                  </span>
                  <a
                    href={`/qa/cases/${d.tc_id}/edit`}
                    className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
                  >
                    Düzenle / Review
                  </a>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-gray-500">
            💡 Promote için CLI: <code>cd qa && npm run tc-promote -- --suite={suite}</code>
          </p>
        </section>
      )}

      {r.prompt_preview && (
        <details className="rounded border border-gray-200 bg-white p-3">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-gray-500">
            Prompt önizleme (son 2KB)
          </summary>
          <pre className="mt-2 max-h-96 overflow-y-auto whitespace-pre-wrap rounded bg-gray-50 p-3 text-xs">
            {r.prompt_preview}
          </pre>
        </details>
      )}

      {r.stderr && (
        <details className="rounded border border-amber-200 bg-amber-50 p-3">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-amber-700">
            stderr (varsa)
          </summary>
          <pre className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap text-xs">{r.stderr}</pre>
        </details>
      )}
    </div>
  );
}
