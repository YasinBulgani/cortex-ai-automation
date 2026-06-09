"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

type Plan = {
  id: string;
  title: string;
  milestone: string;
  scope: {
    include?: Array<{ suite?: string; priorities?: string[]; cases?: string[]; tags?: string[] }>;
    exclude?: Array<{ tags?: string[]; cases?: string[] }>;
  };
};

type TestCaseListItem = {
  id: string;
  title: string;
  suite: string;
  priority: "P0" | "P1" | "P2" | "P3";
  automation_status: string;
};

type Step = "pick-plan" | "env" | "execute" | "review" | "done";

type Result = {
  tc: string;
  tc_commit: string;
  status: "pass" | "fail" | "blocked" | "skipped" | "untested";
  note?: string;
  evidence?: string;
  defect?: string;
};

export default function RunWizard() {
  const [step, setStep] = useState<Step>("pick-plan");
  const [plans, setPlans] = useState<Plan[]>([]);
  const [chosenPlan, setChosenPlan] = useState<Plan | null>(null);
  const [scoped, setScoped] = useState<TestCaseListItem[]>([]);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [env, setEnv] = useState({ branch: "main", commit: "HEAD", browser: "chromium", env: "staging", url: "" });
  const [results, setResults] = useState<Record<string, Result>>({});
  const [currentIdx, setCurrentIdx] = useState(0);
  const [savedRunId, setSavedRunId] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Plan[]>("/api/v1/qa/plans")
      .then(setPlans)
      .catch(() => setPlans([]));
  }, []);

  async function selectPlan(p: Plan) {
    setChosenPlan(p);
    // Plan scope'una göre TC'leri filtrele
    const all = await apiFetch<{ items: TestCaseListItem[] }>("/api/v1/qa/cases?limit=1000");
    const matches = all.items.filter((tc) => {
      for (const inc of p.scope?.include || []) {
        let ok = true;
        if (inc.suite && tc.suite !== inc.suite) ok = false;
        if (inc.priorities && !inc.priorities.includes(tc.priority)) ok = false;
        if (inc.cases && !inc.cases.includes(tc.id)) ok = false;
        if (ok && (inc.suite || inc.priorities || inc.cases)) return true;
      }
      return false;
    });
    setScoped(matches);
    setStep("env");
  }

  function startExecution() {
    const init: Record<string, Result> = {};
    for (const tc of scoped) {
      init[tc.id] = { tc: tc.id, tc_commit: env.commit || "unknown", status: "untested" };
    }
    setResults(init);
    setCurrentIdx(0);
    setStep("execute");
  }

  function recordResult(status: Result["status"], note = "", evidence = "") {
    const tc = scoped[currentIdx];
    if (!tc) return;
    setResults((prev) => ({
      ...prev,
      [tc.id]: { ...prev[tc.id], status, ...(note && { note }), ...(evidence && { evidence }) },
    }));
    if (currentIdx + 1 < scoped.length) {
      setCurrentIdx(currentIdx + 1);
    } else {
      setStep("review");
    }
  }

  async function saveRun() {
    if (!chosenPlan || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const run = await apiFetch<{ id: string }>("/api/v1/qa/runs", {
        method: "POST",
        json: {
          plan: chosenPlan.id,
          executor: "@web-ui",
          environment: env,
          results: Object.values(results),
        },
      });
      setSavedRunId(run.id);
      setStep("done");
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Bilinmeyen hata");
    } finally {
      setSaving(false);
    }
  }

  if (step === "pick-plan") {
    return (
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-fg-subtle">1. Plan seç</h2>
        {plans.length === 0 ? (
          <div className="rounded border border-dashed border-border bg-surface p-6 text-center text-fg-subtle">
            Plan yok. qa/plans/'a YAML ekleyin.
          </div>
        ) : (
          <ul className="space-y-2">
            {plans.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => selectPlan(p)}
                  className="w-full rounded border border-border bg-surface-raised p-4 text-left transition hover:border-blue-400 hover:shadow"
                >
                  <div className="font-mono text-sm text-fg-subtle">{p.id}</div>
                  <div className="mt-1 font-medium">{p.title}</div>
                  <div className="mt-1 text-xs text-fg-subtle">milestone: {p.milestone}</div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (step === "env") {
    return (
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-fg-subtle">2. Ortam bilgisi</h2>
        <div className="space-y-3 rounded border border-border bg-surface-raised p-5">
          <p className="text-sm text-fg-muted">
            Plan: <strong>{chosenPlan?.title}</strong> · <code className="text-xs">{chosenPlan?.id}</code>
          </p>
          <p className="text-sm">
            Kapsama giren TC: <strong>{scoped.length}</strong>
          </p>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Branch" value={env.branch} onChange={(v) => setEnv({ ...env, branch: v })} />
            <Field label="Commit" value={env.commit} onChange={(v) => setEnv({ ...env, commit: v })} />
            <Field label="Browser" value={env.browser} onChange={(v) => setEnv({ ...env, browser: v })} />
            <Field label="Env" value={env.env} onChange={(v) => setEnv({ ...env, env: v })} />
            <Field label="URL (opsiyonel)" value={env.url} onChange={(v) => setEnv({ ...env, url: v })} />
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={startExecution}
            disabled={scoped.length === 0}
            className="mt-2"
          >
            Koşumu başlat ({scoped.length} TC)
          </Button>
        </div>
      </div>
    );
  }

  if (step === "execute") {
    const tc = scoped[currentIdx];
    if (!tc) return <div>?</div>;
    const current = results[tc.id];
    return (
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-fg-subtle">
            3. Koşum [{currentIdx + 1} / {scoped.length}]
          </h2>
          <div className="text-xs text-fg-subtle">
            Plan: <code>{chosenPlan?.id}</code>
          </div>
        </div>
        <TCExecutor tc={tc} current={current} onRecord={recordResult} />
        <div className="mt-3 flex items-center justify-between text-xs text-fg-subtle">
          <Button
            variant="outline"
            size="sm"
            disabled={currentIdx === 0}
            onClick={() => setCurrentIdx(currentIdx - 1)}
          >
            ← Önceki
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setStep("review")}
          >
            Tümünü gözden geçir →
          </Button>
        </div>
      </div>
    );
  }

  if (step === "review") {
    const counts = { pass: 0, fail: 0, blocked: 0, skipped: 0, untested: 0 };
    for (const r of Object.values(results)) counts[r.status]++;
    return (
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-fg-subtle">4. Gözden geçir + kaydet</h2>
        <div className="mb-4 rounded border border-border bg-surface-raised p-4">
          <div className="grid grid-cols-5 gap-3 text-center text-sm">
            <Stat label="Pass" count={counts.pass} tone="green" />
            <Stat label="Fail" count={counts.fail} tone="red" />
            <Stat label="Blocked" count={counts.blocked} tone="amber" />
            <Stat label="Skipped" count={counts.skipped} tone="gray" />
            <Stat label="Untested" count={counts.untested} tone="gray" />
          </div>
        </div>
        <table className="w-full rounded border border-border bg-surface-raised text-sm">
          <thead className="bg-surface text-left text-xs uppercase text-fg-subtle">
            <tr>
              <th className="px-3 py-2">TC</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Not</th>
            </tr>
          </thead>
          <tbody>
            {Object.values(results).map((r) => (
              <tr key={r.tc} className="border-t border-border">
                <td className="px-3 py-1.5 font-mono text-xs">{r.tc}</td>
                <td className="px-3 py-1.5">
                  <StatusPill s={r.status} />
                </td>
                <td className="px-3 py-1.5 text-xs text-fg-subtle">{r.note || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {saveError && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            Kaydetme hatası: {saveError}
          </div>
        )}
        <div className="mt-4 flex gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={saveRun}
            disabled={saving}
            className="bg-green-600 text-white hover:bg-green-700"
          >
            {saving ? "Kaydediliyor..." : "✓ Run YAML olarak kaydet"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => setStep("execute")}>
            ← Koşuma geri dön
          </Button>
        </div>
      </div>
    );
  }

  // done
  return (
    <div className="rounded border border-green-200 bg-green-50 p-6 text-center">
      <div className="text-2xl">✓</div>
      <h2 className="mt-2 text-lg font-semibold text-green-800">Run kaydedildi</h2>
      <p className="mt-1 text-sm text-green-700">
        Run ID: <code className="font-mono">{savedRunId}</code>
      </p>
      <p className="mt-2 text-xs text-green-600">
        Dosya: <code>qa/runs/{savedRunId?.slice(3, 7)}/{savedRunId?.slice(8, 10)}/{savedRunId}.yml</code>
      </p>
      <div className="mt-4 flex justify-center gap-2">
        <a href="/qa" className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          Dashboard'a dön
        </a>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setStep("pick-plan");
            setChosenPlan(null);
            setResults({});
            setCurrentIdx(0);
            setSavedRunId(null);
          }}
        >
          Yeni koşum
        </Button>
      </div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="text-sm">
      <span className="block text-xs uppercase tracking-wider text-fg-subtle">{label}</span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 w-full rounded border border-border bg-surface-raised px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
      />
    </label>
  );
}

function Stat({ label, count, tone }: { label: string; count: number; tone: "green" | "red" | "amber" | "gray" }) {
  const colors: Record<string, string> = {
    green: "text-green-600",
    red: "text-red-600",
    amber: "text-amber-600",
    gray: "text-fg-subtle",
  };
  return (
    <div>
      <div className={`text-2xl font-semibold ${colors[tone]}`}>{count}</div>
      <div className="text-xs uppercase tracking-wider text-fg-subtle">{label}</div>
    </div>
  );
}

function StatusPill({ s }: { s: string }) {
  const tone =
    s === "pass" ? "bg-green-100 text-green-700"
    : s === "fail" ? "bg-red-100 text-red-700"
    : s === "blocked" ? "bg-amber-100 text-amber-700"
    : s === "skipped" ? "bg-surface-overlay text-fg-subtle"
    : "bg-surface-overlay text-fg-subtle";
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${tone}`}>{s}</span>;
}

function TCExecutor({
  tc,
  current,
  onRecord,
}: {
  tc: TestCaseListItem;
  current: Result | undefined;
  onRecord: (status: Result["status"], note?: string, evidence?: string) => void;
}) {
  const [body, setBody] = useState<string>("");
  const [note, setNote] = useState("");
  const [evidence, setEvidence] = useState("");

  useEffect(() => {
    setNote(current?.note || "");
    setEvidence(current?.evidence || "");
    apiFetch<{ body?: string }>(`/api/v1/qa/cases/${tc.id}`)
      .then((d) => setBody(d.body || ""))
      .catch(() => setBody("(yüklenemedi)"));
  }, [tc.id, current]);

  return (
    <div className="rounded border border-border bg-surface-raised p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <div>
          <div className="font-mono text-xs text-fg-subtle">{tc.id}</div>
          <h3 className="text-lg font-medium">{tc.title}</h3>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="rounded bg-blue-100 px-2 py-0.5 text-blue-700">{tc.suite}</span>
          <span className="rounded bg-amber-100 px-2 py-0.5 font-semibold text-amber-700">{tc.priority}</span>
        </div>
      </div>

      <details className="mb-4 rounded bg-surface p-3" open>
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-fg-subtle">
          TC içerik
        </summary>
        <pre className="mt-2 max-h-80 overflow-y-auto whitespace-pre-wrap text-xs font-mono text-fg">
          {body || "Yükleniyor..."}
        </pre>
      </details>

      <div className="mb-3 grid grid-cols-2 gap-2">
        <label className="text-xs">
          <span className="block text-fg-subtle">Not (opsiyonel)</span>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="ne oldu?"
            className="mt-0.5 w-full rounded border border-border px-2 py-1 text-sm"
          />
        </label>
        <label className="text-xs">
          <span className="block text-fg-subtle">Kanıt yolu (opsiyonel)</span>
          <input
            type="text"
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
            placeholder="evidence/screenshot.png"
            className="mt-0.5 w-full rounded border border-border px-2 py-1 text-sm"
          />
        </label>
      </div>

      <div className="flex gap-2">
        <button onClick={() => onRecord("pass", note, evidence)} className="flex-1 rounded bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700">
          ✓ Pass
        </button>
        <button onClick={() => onRecord("fail", note, evidence)} className="flex-1 rounded bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700">
          ✗ Fail
        </button>
        <button onClick={() => onRecord("blocked", note, evidence)} className="flex-1 rounded bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700">
          ⊘ Blocked
        </button>
        <button onClick={() => onRecord("skipped", note, evidence)} className="flex-1 rounded bg-gray-500 px-3 py-2 text-sm font-medium text-white hover:bg-gray-600">
          ↪ Skip
        </button>
      </div>
    </div>
  );
}
