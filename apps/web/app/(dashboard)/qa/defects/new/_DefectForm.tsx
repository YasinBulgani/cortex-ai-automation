"use client";

import { useEffect, useState } from "react";

export default function DefectForm({ initialTc, initialRun }: { initialTc: string; initialRun: string }) {
  const [form, setForm] = useState({
    tc_id: initialTc,
    run_id: initialRun,
    title: "",
    severity: "S2",
    reproduce: "",
    expected: "",
    actual: "",
    environment: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ issue_number?: number; issue_url?: string; dry_run?: boolean; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tcOptions, setTcOptions] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/v1/qa/cases?limit=500")
      .then((r) => r.json())
      .then((d) => setTcOptions(d.items.map((t: any) => t.id)))
      .catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/v1/qa/defects/open-issue", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <div className="rounded border border-green-200 bg-green-50 p-6">
        <div className="mb-2 text-2xl">{result.dry_run ? "🟡" : "✓"}</div>
        <h2 className="text-lg font-semibold text-green-800">
          {result.dry_run ? "Dry-run modu — Issue açılmadı" : "Issue oluşturuldu"}
        </h2>
        <p className="mt-2 text-sm text-green-700">{result.message}</p>
        {result.issue_url && (
          <a href={result.issue_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-blue-600 underline">
            #{result.issue_number} açılıyor →
          </a>
        )}
        <div className="mt-4 flex gap-2">
          <a href="/qa" className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white">Dashboard</a>
          <button onClick={() => { setResult(null); setForm({ ...form, title: "", reproduce: "", expected: "", actual: "" }); }} className="rounded border border-gray-200 px-4 py-2 text-sm">
            Yeni defect
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded border border-gray-200 bg-white p-5">
      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">
          <span className="block text-xs uppercase tracking-wider text-gray-500">İlgili TC *</span>
          <input
            list="tc-list"
            value={form.tc_id}
            onChange={(e) => setForm({ ...form, tc_id: e.target.value })}
            placeholder="TC-AUTH-001"
            required
            className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
          <datalist id="tc-list">
            {tcOptions.map((id) => <option key={id} value={id} />)}
          </datalist>
        </label>
        <label className="text-sm">
          <span className="block text-xs uppercase tracking-wider text-gray-500">Bulunduğu Run</span>
          <input
            type="text"
            value={form.run_id}
            onChange={(e) => setForm({ ...form, run_id: e.target.value })}
            placeholder="TR-2026-..."
            className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 font-mono text-sm"
          />
        </label>
      </div>

      <label className="block text-sm">
        <span className="block text-xs uppercase tracking-wider text-gray-500">Başlık *</span>
        <input
          type="text"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="Login token user.id boş döner"
          required
          className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
      </label>

      <label className="block text-sm">
        <span className="block text-xs uppercase tracking-wider text-gray-500">Severity *</span>
        <select
          value={form.severity}
          onChange={(e) => setForm({ ...form, severity: e.target.value })}
          className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
        >
          <option value="S1">S1 — Kritik (release stopper)</option>
          <option value="S2">S2 — Büyük (feature broken)</option>
          <option value="S3">S3 — Orta (workaround var)</option>
          <option value="S4">S4 — Küçük (kozmetik)</option>
        </select>
      </label>

      <label className="block text-sm">
        <span className="block text-xs uppercase tracking-wider text-gray-500">Tekrar üretme adımları *</span>
        <textarea
          value={form.reproduce}
          onChange={(e) => setForm({ ...form, reproduce: e.target.value })}
          required
          rows={4}
          placeholder="1. Login sayfasına git&#10;2. ...&#10;3. ..."
          className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 font-mono text-xs"
        />
      </label>

      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">
          <span className="block text-xs uppercase tracking-wider text-gray-500">Beklenen *</span>
          <textarea
            value={form.expected}
            onChange={(e) => setForm({ ...form, expected: e.target.value })}
            required
            rows={3}
            placeholder="HTTP 200, user.id dolu"
            className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 font-mono text-xs"
          />
        </label>
        <label className="text-sm">
          <span className="block text-xs uppercase tracking-wider text-gray-500">Gerçekleşen *</span>
          <textarea
            value={form.actual}
            onChange={(e) => setForm({ ...form, actual: e.target.value })}
            required
            rows={3}
            placeholder="HTTP 200, ama user.id null döndü"
            className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 font-mono text-xs"
          />
        </label>
      </div>

      <label className="block text-sm">
        <span className="block text-xs uppercase tracking-wider text-gray-500">Ortam</span>
        <input
          type="text"
          value={form.environment}
          onChange={(e) => setForm({ ...form, environment: e.target.value })}
          placeholder="staging, chromium 120, commit abc1234"
          className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
        />
      </label>

      {error && <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="flex items-center justify-between border-t border-gray-100 pt-4">
        <a href="/qa" className="text-sm text-gray-500 hover:underline">← İptal</a>
        <button
          type="submit"
          disabled={submitting}
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
        >
          {submitting ? "Açılıyor..." : "Defect aç"}
        </button>
      </div>
    </form>
  );
}
