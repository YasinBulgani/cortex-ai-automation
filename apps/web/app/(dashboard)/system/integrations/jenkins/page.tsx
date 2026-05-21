"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
  StatusBadge,
} from "@/components/nexus";

type Connection = {
  id: string;
  name: string;
  base_url: string;
  username: string;
  last_status: string;
  last_error: string;
  last_tested_at: string | null;
  created_at: string;
};

type TestResult = { ok: boolean; error?: string; version?: string; node_name?: string };
type TriggerResult = { ok: boolean; error?: string; queue_url?: string; job?: string };
type LastBuild = {
  ok: boolean;
  exists?: boolean;
  number?: number;
  result?: string | null;
  building?: boolean;
  url?: string;
  error?: string;
};

const PREFIX = "/api/v1/cicd/jenkins";

export default function JenkinsIntegrationPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  // create form
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // per-connection action state
  const [actionResult, setActionResult] = useState<Record<string, TestResult | TriggerResult | LastBuild>>({});
  const [jobInputs, setJobInputs] = useState<Record<string, string>>({});

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<{ connections: Connection[] }>(`${PREFIX}/connections`);
      setConnections(data.connections || []);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Bağlantılar yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiFetch(`${PREFIX}/connections`, {
        method: "POST",
        json: { name, base_url: baseUrl, username, token },
      });
      setName("");
      setBaseUrl("");
      setUsername("");
      setToken("");
      await reload();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Bağlantı eklenemedi");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTest(id: string) {
    const res = await apiFetch<TestResult>(`${PREFIX}/connections/${id}/test`, { method: "POST" });
    setActionResult((s) => ({ ...s, [id]: res }));
    await reload();
  }

  async function handleDelete(id: string) {
    if (!confirm("Bu bağlantıyı silmek istediğinize emin misiniz?")) return;
    await apiFetch(`${PREFIX}/connections/${id}`, { method: "DELETE" });
    await reload();
  }

  async function handleTrigger(id: string) {
    const job = (jobInputs[id] || "").trim();
    if (!job) return;
    const res = await apiFetch<TriggerResult>(`${PREFIX}/connections/${id}/build`, {
      method: "POST",
      json: { job_name: job, parameters: {} },
    });
    setActionResult((s) => ({ ...s, [id]: res }));
  }

  async function handleLastBuild(id: string) {
    const job = (jobInputs[id] || "").trim();
    if (!job) return;
    const res = await apiFetch<LastBuild>(
      `${PREFIX}/connections/${id}/jobs/${encodeURIComponent(job)}/last-build`,
    );
    setActionResult((s) => ({ ...s, [id]: res }));
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Jenkins Entegrasyonu"
        description="Jenkins controller'ınızı bağlayın, job tetikleyin, son build durumunu izleyin."
      />

      <SectionCard title="Yeni bağlantı ekle">
        <form onSubmit={handleCreate} className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <input
            className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
            placeholder="Bağlantı adı (örn. Prod Jenkins)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
            placeholder="https://jenkins.example.com"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            required
          />
          <input
            className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
            placeholder="Kullanıcı adı"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
            type="password"
            placeholder="API token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            required
          />
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={submitting}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Kaydediliyor..." : "Bağlantıyı kaydet"}
            </button>
          </div>
        </form>
        <p className="mt-3 text-xs text-neutral-400">
          API token'ı Jenkins → kullanıcı profili → Configure → API Token bölümünden alabilirsiniz.
          Token sunucuda Fernet ile şifrelenir.
        </p>
      </SectionCard>

      <SectionCard title="Kayıtlı bağlantılar">
        {error && <p className="text-sm text-red-400">{error}</p>}
        {loading ? (
          <p className="text-sm text-neutral-400">Yükleniyor...</p>
        ) : connections.length === 0 ? (
          <EmptyState title="Henüz bağlantı yok" description="Yukarıdan ilk Jenkins bağlantınızı ekleyin." />
        ) : (
          <div className="space-y-4">
            {connections.map((c) => {
              const res = actionResult[c.id];
              return (
                <div key={c.id} className="rounded border border-neutral-700 p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium">{c.name}</h3>
                        <StatusBadge
                          status={
                            c.last_status === "ok"
                              ? "connected"
                              : c.last_status === "error"
                                ? "error"
                                : "disconnected"
                          }
                          label={c.last_status}
                        />
                      </div>
                      <p className="text-sm text-neutral-400">
                        {c.base_url} · kullanıcı: {c.username}
                      </p>
                      {c.last_error && (
                        <p className="mt-1 text-xs text-red-400">Son hata: {c.last_error}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleTest(c.id)}
                        className="rounded border border-neutral-600 px-3 py-1 text-sm hover:bg-neutral-800"
                      >
                        Bağlantıyı test et
                      </button>
                      <button
                        onClick={() => handleDelete(c.id)}
                        className="rounded border border-red-600 px-3 py-1 text-sm text-red-400 hover:bg-red-900/30"
                      >
                        Sil
                      </button>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <input
                      className="flex-1 min-w-[200px] rounded border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm"
                      placeholder="Job adı (örn. neurex-regression)"
                      value={jobInputs[c.id] || ""}
                      onChange={(e) => setJobInputs((s) => ({ ...s, [c.id]: e.target.value }))}
                    />
                    <button
                      onClick={() => handleTrigger(c.id)}
                      className="rounded bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700"
                    >
                      Build tetikle
                    </button>
                    <button
                      onClick={() => handleLastBuild(c.id)}
                      className="rounded border border-neutral-600 px-3 py-1.5 text-sm hover:bg-neutral-800"
                    >
                      Son build durumu
                    </button>
                  </div>

                  {res && (
                    <pre className="mt-3 max-h-48 overflow-auto rounded bg-neutral-950 p-2 text-xs text-neutral-300">
                      {JSON.stringify(res, null, 2)}
                    </pre>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
