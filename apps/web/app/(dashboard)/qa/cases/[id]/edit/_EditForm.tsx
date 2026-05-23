"use client";

import { useEffect, useState } from "react";

type TC = {
  id: string;
  title: string;
  suite: string;
  priority: "P0" | "P1" | "P2" | "P3";
  type: string[];
  status: "draft" | "active" | "deprecated";
  owner: string;
  estimated_minutes?: number;
  automation: { status: string; refs?: string[]; reason?: string };
  requirements?: string[];
  pre_conditions?: string[];
  tags?: string[];
  body?: string;
};

const ALL_TYPES = ["functional", "smoke", "regression", "integration", "api", "ui", "perf", "security", "a11y", "exploratory"];

export default function EditForm({ tcId }: { tcId: string }) {
  const [tc, setTc] = useState<TC | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`/api/v1/qa/cases/${tcId}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => setTc(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [tcId]);

  async function save() {
    if (!tc) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/qa/cases/${tcId}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title: tc.title,
          priority: tc.priority,
          type: tc.type,
          status: tc.status,
          owner: tc.owner,
          estimated_minutes: tc.estimated_minutes,
          automation: tc.automation,
          requirements: tc.requirements,
          pre_conditions: tc.pre_conditions,
          tags: tc.tags,
          body: tc.body,
        }),
      });
      if (!res.ok) throw new Error(`Save failed: HTTP ${res.status}`);
      const updated = await res.json();
      setTc(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="py-12 text-center text-gray-400">Yükleniyor...</div>;
  if (error && !tc) return <div className="rounded border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>;
  if (!tc) return null;

  return (
    <div className="space-y-6">
      <section className="rounded border border-gray-200 bg-white p-5">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Metadata</h2>

        <div className="grid grid-cols-2 gap-3">
          <label className="col-span-2 text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Title</span>
            <input
              type="text"
              value={tc.title}
              onChange={(e) => setTc({ ...tc, title: e.target.value })}
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </label>

          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Priority</span>
            <select
              value={tc.priority}
              onChange={(e) => setTc({ ...tc, priority: e.target.value as any })}
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
            >
              {["P0", "P1", "P2", "P3"].map((p) => <option key={p}>{p}</option>)}
            </select>
          </label>

          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Status</span>
            <select
              value={tc.status}
              onChange={(e) => setTc({ ...tc, status: e.target.value as any })}
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
            >
              <option value="draft">draft</option>
              <option value="active">active</option>
              <option value="deprecated">deprecated</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Owner</span>
            <input
              type="text"
              value={tc.owner}
              onChange={(e) => setTc({ ...tc, owner: e.target.value })}
              placeholder="@username"
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm font-mono"
            />
          </label>

          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Estimated (dk)</span>
            <input
              type="number"
              value={tc.estimated_minutes || ""}
              onChange={(e) => setTc({ ...tc, estimated_minutes: parseInt(e.target.value) || undefined })}
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
            />
          </label>

          <div className="col-span-2 text-sm">
            <span className="mb-1 block text-xs uppercase tracking-wider text-gray-500">Type</span>
            <div className="flex flex-wrap gap-1">
              {ALL_TYPES.map((t) => {
                const checked = (tc.type || []).includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => {
                      const newTypes = checked
                        ? tc.type.filter((x) => x !== t)
                        : [...(tc.type || []), t];
                      setTc({ ...tc, type: newTypes });
                    }}
                    className={`rounded border px-2 py-0.5 text-xs ${
                      checked
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-gray-200 bg-white text-gray-500 hover:bg-gray-50"
                    }`}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded border border-gray-200 bg-white p-5">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Automation</h2>
        <div className="space-y-2">
          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wider text-gray-500">Status</span>
            <select
              value={tc.automation.status}
              onChange={(e) => setTc({ ...tc, automation: { ...tc.automation, status: e.target.value } })}
              className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
            >
              <option value="not-automated">not-automated</option>
              <option value="in-progress">in-progress</option>
              <option value="automated">automated</option>
              <option value="out-of-scope">out-of-scope</option>
            </select>
          </label>

          {tc.automation.status === "automated" && (
            <ListField
              label="Refs (one per line)"
              value={(tc.automation.refs || []).join("\n")}
              onChange={(v) =>
                setTc({
                  ...tc,
                  automation: { ...tc.automation, refs: v.split("\n").map((s) => s.trim()).filter(Boolean) },
                })
              }
              placeholder="e2e/bdd/features/auth/login.feature:12"
              rows={3}
            />
          )}

          {tc.automation.status === "out-of-scope" && (
            <label className="text-sm">
              <span className="block text-xs uppercase tracking-wider text-gray-500">Reason</span>
              <input
                type="text"
                value={tc.automation.reason || ""}
                onChange={(e) => setTc({ ...tc, automation: { ...tc.automation, reason: e.target.value } })}
                className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 text-sm"
              />
            </label>
          )}
        </div>
      </section>

      <section className="rounded border border-gray-200 bg-white p-5">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Links</h2>
        <ListField
          label="Requirements (REQ-*)"
          value={(tc.requirements || []).join(", ")}
          onChange={(v) =>
            setTc({ ...tc, requirements: v.split(/[,\s]+/).map((s) => s.trim()).filter(Boolean) })
          }
          placeholder="REQ-AUTH-001, REQ-AUTH-002"
          rows={1}
        />
        <ListField
          label="Pre-conditions (PRE-*)"
          value={(tc.pre_conditions || []).join(", ")}
          onChange={(v) =>
            setTc({ ...tc, pre_conditions: v.split(/[,\s]+/).map((s) => s.trim()).filter(Boolean) })
          }
          placeholder="PRE-001, PRE-002"
          rows={1}
        />
        <ListField
          label="Tags"
          value={(tc.tags || []).join(", ")}
          onChange={(v) =>
            setTc({ ...tc, tags: v.split(/[,\s]+/).map((s) => s.trim()).filter(Boolean) })
          }
          placeholder="smoke, mobile-only"
          rows={1}
        />
      </section>

      <section className="rounded border border-gray-200 bg-white p-5">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Body (Markdown)
        </h2>
        <textarea
          value={tc.body || ""}
          onChange={(e) => setTc({ ...tc, body: e.target.value })}
          rows={24}
          className="w-full rounded border border-gray-200 bg-gray-50 p-3 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <p className="mt-2 text-xs text-gray-500">
          Adımlar tablosu, önkoşul, notlar — markdown formatında. Live preview yok (henüz).
        </p>
      </section>

      <div className="sticky bottom-0 -mx-6 border-t border-gray-200 bg-white px-6 py-3 shadow">
        <div className="flex items-center justify-between">
          <a href="/qa" className="text-sm text-gray-500 hover:underline">
            ← İptal et, dashboard'a dön
          </a>
          <div className="flex items-center gap-3">
            {error && <span className="text-sm text-red-600">{error}</span>}
            {saved && <span className="text-sm text-green-600">✓ Kaydedildi</span>}
            <button
              onClick={save}
              disabled={saving}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Kaydediliyor..." : "Kaydet"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ListField({
  label,
  value,
  onChange,
  placeholder,
  rows = 1,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <label className="mb-2 block text-sm">
      <span className="block text-xs uppercase tracking-wider text-gray-500">{label}</span>
      {rows > 1 ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
          className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 font-mono text-xs"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="mt-0.5 w-full rounded border border-gray-200 px-2 py-1 font-mono text-sm"
        />
      )}
    </label>
  );
}
