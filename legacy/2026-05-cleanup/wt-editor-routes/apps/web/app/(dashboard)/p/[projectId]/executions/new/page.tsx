"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Scenario = { id: string; title: string; status: string };

export default function NewExecutionPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    apiFetch<Scenario[]>(`/api/v1/tspm/projects/${projectId}/scenarios`).then(setScenarios).catch(() => {});
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  function toggle(id: string) {
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (selected.size === 0) {
      setErr("En az bir senaryo seçin.");
      return;
    }
    setSaving(true);
    try {
      const created = await apiFetch<{ id: string }>(`/api/v1/tspm/projects/${projectId}/executions`, {
        method: "POST",
        json: { name: name.trim() || "Koşu", scenario_ids: Array.from(selected) },
      });
      router.push(`/p/${projectId}/executions/${created.id}`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="new-execution-page">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight" data-testid="new-execution-heading">Yeni execution</h1>
        <p className="text-sm text-slate-400">Koşuda yer alacak senaryoları seçin</p>
      </div>
      <form onSubmit={submit} className="space-y-4" data-testid="new-execution-form">
        <div>
          <label htmlFor="ex-name" className="mb-1 block text-xs text-slate-400">
            Koşu adı
          </label>
          <Input id="ex-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Örn. Sprint 12 regresyon" data-testid="execution-input-name" />
        </div>
        <div className="rounded-lg border border-slate-800" data-testid="execution-scenario-list">
          <div className="border-b border-slate-800 px-3 py-2 text-xs font-medium text-slate-400">Senaryolar</div>
          <ul className="max-h-72 divide-y divide-border overflow-auto">
            {scenarios.map((s) => (
              <li key={s.id} className="flex items-center gap-3 px-3 py-2">
                <input
                  type="checkbox"
                  checked={selected.has(s.id)}
                  onChange={() => toggle(s.id)}
                  aria-label={s.title}
                  data-testid={`execution-check-scenario-${s.id}`}
                />
                <span className="text-sm">{s.title}</span>
                <span className="text-xs text-slate-400">{s.status}</span>
              </li>
            ))}
          </ul>
          {scenarios.length === 0 && <p className="p-4 text-sm text-slate-400" data-testid="execution-empty-scenarios">Önce senaryo oluşturun.</p>}
        </div>
        {err && <p className="text-sm text-red-600" data-testid="execution-alert-error">{err}</p>}
        <div className="flex gap-2">
          <Button type="submit" disabled={saving} data-testid="execution-btn-start">
            {saving ? "…" : "Koşuyu oluştur"}
          </Button>
          <Link href={`/p/${projectId}/executions`}>
            <Button type="button" variant="secondary">
              İptal
            </Button>
          </Link>
        </div>
      </form>
    </div>
  );
}
