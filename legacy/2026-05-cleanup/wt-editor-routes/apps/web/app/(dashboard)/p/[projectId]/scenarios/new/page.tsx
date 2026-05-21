"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function NewScenarioPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [stepText, setStepText] = useState("Adım 1: …");
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const steps = [{ order: 0, text: stepText }];
      const created = await apiFetch<{ id: string }>(`/api/v1/tspm/projects/${projectId}/scenarios`, {
        method: "POST",
        json: { title, description, status: "draft", steps },
      });
      router.push(`/p/${projectId}/scenarios/${created.id}`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-2" data-testid="new-scenario-page">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight" data-testid="new-scenario-heading">Yeni senaryo</h1>
        <p className="text-sm text-slate-400">Tek sayfa form</p>
        <form onSubmit={submit} className="mt-6 space-y-4" data-testid="scenario-form">
          <div>
            <label htmlFor="sc-title" className="mb-1 block text-xs text-slate-400">
              Başlık
            </label>
            <Input id="sc-title" value={title} onChange={(e) => setTitle(e.target.value)} required data-testid="scenario-form-input-title" />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">Açıklama</label>
            <textarea
              className="min-h-[100px] w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">İlk adım</label>
            <textarea
              className="min-h-[80px] w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
              value={stepText}
              onChange={(e) => setStepText(e.target.value)}
            />
          </div>
          {err && <p className="text-sm text-red-600" data-testid="scenario-form-error">{err}</p>}
          <Button type="submit" data-testid="scenario-form-btn-save">Kaydet</Button>
        </form>
      </div>
      <div className="rounded-lg border border-slate-800 p-4 lg:sticky lg:top-6 lg:self-start">
        <h2 className="text-sm font-medium">Önizleme</h2>
        <p className="mt-2 text-lg font-medium">{title || "Başlık"}</p>
        <p className="mt-1 text-sm text-slate-400">{description || "Açıklama"}</p>
        <pre className="mt-4 overflow-auto rounded bg-black/[0.03] p-3 text-xs dark:bg-white/[0.06]">
          {JSON.stringify([{ order: 0, text: stepText }], null, 2)}
        </pre>
      </div>
    </div>
  );
}
