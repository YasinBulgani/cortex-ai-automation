"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal, ModalContent, ModalFooter, ModalHeader, ModalTitle } from "@/components/ui/modal";
import { useFetch, useMutate } from "@/lib/useFetch";
import { apiFetch } from "@/lib/api";

type Workflow = {
  id: string;
  name: string;
  description?: string;
  n8n_workflow_id: string;
  trigger_on: string;
  is_active: boolean;
  webhook_path?: string;
  last_triggered_at: string | null;
  created_at: string;
};

type Execution = { id: string; status: string; started_at: string; finished_at: string | null; error?: string };

const triggerLabels: Record<string, string> = {
  manual: "Manuel",
  schedule: "Zamanlı",
  "execution.complete": "Koşu tamamlandı",
  "scenario.create": "Senaryo oluşturuldu",
  "test.fail": "Test başarısız",
};

export default function WorkflowsPage() {
  const projectId = useRouteParam("projectId");
  const [createOpen, setCreateOpen] = useState(false);
  const [historyWf, setHistoryWf] = useState<Workflow | null>(null);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", n8n_workflow_id: "", webhook_path: "", trigger_on: "manual", description: "" });

  const { data, loading, refresh } = useFetch<Workflow[]>(
    `/api/v1/tspm/projects/${projectId}/workflows`
  );
  const workflows = data ?? [];

  const { data: executions, loading: execLoading } = useFetch<Execution[]>(
    historyWf ? `/api/v1/tspm/projects/${projectId}/workflows/${historyWf.id}/executions` : null
  );

  const { mutate: createWf, loading: creating } = useMutate(
    `/api/v1/tspm/projects/${projectId}/workflows`,
    { onSuccess: () => { setCreateOpen(false); setForm({ name: "", n8n_workflow_id: "", webhook_path: "", trigger_on: "manual", description: "" }); refresh(); } }
  );

  async function handleToggle(wf: Workflow) {
    await apiFetch(`/api/v1/tspm/projects/${projectId}/workflows/${wf.id}`, {
      method: "PUT",
      json: { is_active: !wf.is_active },
    });
    refresh();
  }

  async function handleDelete(id: string) {
    if (!confirm("Bu workflow silinsin mi?")) return;
    await apiFetch(`/api/v1/tspm/projects/${projectId}/workflows/${id}`, { method: "DELETE" });
    refresh();
  }

  async function handleTrigger(wf: Workflow) {
    setTriggering(wf.id);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/workflows/${wf.id}/trigger`, {
        method: "POST",
        json: { triggered_by: "manual" },
      });
      refresh();
    } finally {
      setTriggering(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-testid="workflows-page">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold" data-testid="workflows-heading">n8n Workflows</h1>
          <p className="text-sm text-slate-400">Otomasyon workflow'larını yönetin ve tetikleyin</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} data-testid="workflows-btn-new">
          + Workflow Bağla
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg border border-slate-800 bg-muted/10" />
          ))}
        </div>
      ) : workflows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-800 p-12 text-center text-slate-400">
          Henüz bağlı workflow yok. n8n'inizdeki workflow ID'sini ekleyerek başlayın.
        </div>
      ) : (
        <div className="grid gap-3">
          {workflows.map((wf) => (
            <div
              key={wf.id}
              className="flex items-center justify-between rounded-lg border border-slate-800 p-4 shadow-2xl"
              data-testid={`workflows-card-${wf.id}`}
            >
              <div className="flex items-center gap-4">
                <button
                  onClick={() => handleToggle(wf)}
                  title={wf.is_active ? "Pasifleştir" : "Aktifleştir"}
                  className={`h-3 w-3 rounded-full transition-colors ${wf.is_active ? "bg-green-500 hover:bg-green-600" : "bg-gray-400 hover:bg-gray-500"}`}
                />
                <div>
                  <h3 className="font-medium">{wf.name}</h3>
                  <p className="text-xs text-slate-400">
                    n8n ID: {wf.n8n_workflow_id} · Tetik: {triggerLabels[wf.trigger_on] ?? wf.trigger_on}
                    {wf.last_triggered_at && ` · Son: ${new Date(wf.last_triggered_at).toLocaleString("tr-TR")}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setHistoryWf(wf)}
                >
                  Geçmiş
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleTrigger(wf)}
                  disabled={triggering === wf.id}
                  data-testid={`workflows-btn-trigger-${wf.id}`}
                >
                  {triggering === wf.id ? "Tetikleniyor…" : "Tetikle"}
                </Button>
                <button
                  onClick={() => handleDelete(wf.id)}
                  className="text-xs text-red-500 hover:text-red-700 px-2"
                >
                  Sil
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Yeni workflow modalı */}
      <Modal open={createOpen} onOpenChange={setCreateOpen}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Workflow Bağla</ModalTitle>
          </ModalHeader>
          <div className="space-y-3">
            <Input placeholder="Workflow adı" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input placeholder="n8n Workflow ID" value={form.n8n_workflow_id} onChange={(e) => setForm({ ...form, n8n_workflow_id: e.target.value })} />
            <Input placeholder="Webhook URL (opsiyonel)" value={form.webhook_path} onChange={(e) => setForm({ ...form, webhook_path: e.target.value })} />
            <Input placeholder="Açıklama" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <select
              value={form.trigger_on}
              onChange={(e) => setForm({ ...form, trigger_on: e.target.value })}
              className="flex h-9 w-full rounded border border-slate-800 bg-slate-900 px-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(triggerLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <ModalFooter>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>İptal</Button>
            <Button onClick={() => createWf(form)} disabled={creating || !form.name || !form.n8n_workflow_id}>
              {creating ? "Kaydediliyor…" : "Bağla"}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Execution geçmişi modalı */}
      <Modal open={!!historyWf} onOpenChange={() => setHistoryWf(null)}>
        <ModalContent className="max-w-2xl">
          <ModalHeader>
            <ModalTitle>{historyWf?.name} — Tetikleme Geçmişi</ModalTitle>
          </ModalHeader>
          {execLoading ? (
            <div className="py-4 text-center text-sm text-slate-400">Yükleniyor…</div>
          ) : (executions ?? []).length === 0 ? (
            <div className="py-4 text-center text-sm text-slate-400">Henüz tetikleme yapılmamış</div>
          ) : (
            <div className="max-h-80 overflow-y-auto space-y-2">
              {(executions ?? []).map((e) => (
                <div key={e.id} className="flex items-center justify-between rounded border border-slate-800 px-3 py-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${e.status === "success" ? "bg-green-500" : e.status === "running" ? "bg-blue-500" : "bg-red-500"}`} />
                    <span>{new Date(e.started_at).toLocaleString("tr-TR")}</span>
                    {e.error && <span className="text-xs text-red-500">{e.error}</span>}
                  </div>
                  <span className="text-xs text-slate-400">
                    {e.finished_at ? `${Math.round((new Date(e.finished_at).getTime() - new Date(e.started_at).getTime()) / 1000)}s` : "devam ediyor"}
                  </span>
                </div>
              ))}
            </div>
          )}
          <ModalFooter>
            <Button variant="secondary" onClick={() => setHistoryWf(null)}>Kapat</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </div>
  );
}
