"use client";

import { useEffect, useState } from "react";
import {
  useKiwiConnection,
  useSaveKiwiConnection,
  useTestKiwiConnection,
  useKiwiPreview,
  useStartKiwiSync,
  useKiwiSyncJobs,
  type KiwiProduct,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const ENTITY_LABELS: Record<string, string> = {
  suites: "Suite",
  cases: "Case",
  plans: "Plan",
  runs: "Run",
};

const STATUS_BADGE: Record<string, string> = {
  ok: "bg-emerald-500/15 text-emerald-400",
  error: "bg-rose-500/15 text-rose-400",
  unconfigured: "bg-white/[0.06] text-slate-400",
};

export default function ManagementIntegrationsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: connection, isLoading } = useKiwiConnection(mpid || undefined);
  const saveConn = useSaveKiwiConnection(mpid || "");
  const testConn = useTestKiwiConnection(mpid || "");
  const preview = useKiwiPreview(mpid || "");
  const startSync = useStartKiwiSync(mpid || "");
  const { data: syncJobs } = useKiwiSyncJobs(mpid || undefined);

  const [baseUrl, setBaseUrl] = useState("");
  const [username, setUsername] = useState("");
  const [secret, setSecret] = useState("");
  const [verifySsl, setVerifySsl] = useState(true);
  const [productId, setProductId] = useState<number | null>(null);
  const [products, setProducts] = useState<KiwiProduct[]>([]);
  const [dryRun, setDryRun] = useState(false);

  // Prefill the form from the stored connection once it loads.
  useEffect(() => {
    if (connection) {
      setBaseUrl(connection.base_url);
      setUsername(connection.username);
      setVerifySsl(connection.verify_ssl);
      setProductId(connection.kiwi_product_id ?? null);
    }
  }, [connection]);

  const canSave = !!mpid && baseUrl.trim() !== "" && username.trim() !== "";
  const isConfigured = !!connection?.has_secret;

  const handleSave = async () => {
    if (!canSave) return;
    await saveConn.mutateAsync({
      base_url: baseUrl.trim(),
      username: username.trim(),
      secret: secret.trim() || undefined, // blank keeps the stored secret
      kiwi_product_id: productId,
      verify_ssl: verifySsl,
    });
    setSecret("");
  };

  const handleTest = async () => {
    const result = await testConn.mutateAsync();
    if (result.ok) setProducts(result.products);
  };

  const handleSelectProduct = async (id: number) => {
    setProductId(id);
    if (canSave) {
      await saveConn.mutateAsync({
        base_url: baseUrl.trim(),
        username: username.trim(),
        secret: secret.trim() || undefined,
        kiwi_product_id: id,
        verify_ssl: verifySsl,
      });
    }
  };

  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg text-slate-200">
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <h1 className="text-[13px] font-semibold text-slate-200">Entegrasyonlar</h1>
        <p className="mt-0.5 text-[11px] text-slate-500">Kiwi TCMS&apos;ten test verisi içe aktarımı</p>
      </div>

      <div className="mx-auto max-w-2xl p-6 space-y-6">
        {/* ── Bağlantı ── */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Kiwi TCMS Bağlantısı</h2>
            {connection && (
              <span className={`rounded px-2 py-0.5 text-[10px] ${STATUS_BADGE[connection.status] ?? STATUS_BADGE.unconfigured}`}>
                {connection.status === "ok" ? "Bağlı" : connection.status === "error" ? "Hata" : "Yapılandırılmadı"}
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-9 rounded bg-white/[0.04]" />)}
            </div>
          ) : (
            <div className="space-y-3">
              <Field label="Kiwi URL">
                <input
                  value={baseUrl}
                  onChange={e => setBaseUrl(e.target.value)}
                  placeholder="https://kiwi.example.com"
                  className="w-full rounded-md border border-border bg-white/[0.02] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/60"
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Kullanıcı adı">
                  <input
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    placeholder="api-user"
                    className="w-full rounded-md border border-border bg-white/[0.02] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/60"
                  />
                </Field>
                <Field label={isConfigured ? "Token / Parola (değiştirmek için yaz)" : "Token / Parola"}>
                  <input
                    type="password"
                    value={secret}
                    onChange={e => setSecret(e.target.value)}
                    placeholder={isConfigured ? "••••••••" : "API token"}
                    className="w-full rounded-md border border-border bg-white/[0.02] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/60"
                  />
                </Field>
              </div>
              <label className="flex items-center gap-2 text-[12px] text-slate-400">
                <input type="checkbox" checked={verifySsl} onChange={e => setVerifySsl(e.target.checked)} />
                SSL sertifikasını doğrula
              </label>

              {connection?.last_error && (
                <p className="rounded-md bg-rose-500/10 px-3 py-2 text-[11px] text-rose-300">{connection.last_error}</p>
              )}

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={handleSave}
                  disabled={!canSave || saveConn.isPending}
                  className="rounded-lg bg-teal-600 px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-teal-500 disabled:opacity-40"
                >
                  {saveConn.isPending ? "Kaydediliyor…" : "Kaydet"}
                </button>
                <button
                  onClick={handleTest}
                  disabled={!isConfigured || testConn.isPending}
                  className="rounded-lg border border-border px-4 py-2 text-[13px] font-medium text-slate-300 transition hover:bg-white/[0.04] disabled:opacity-40"
                >
                  {testConn.isPending ? "Test ediliyor…" : "Bağlantıyı test et"}
                </button>
                {testConn.data?.ok && (
                  <span className="text-[11px] text-emerald-400">{testConn.data.product_count} ürün bulundu</span>
                )}
                {testConn.data && !testConn.data.ok && (
                  <span className="text-[11px] text-rose-400">{testConn.data.error}</span>
                )}
              </div>
            </div>
          )}
        </section>

        {/* ── Ürün seçimi ── */}
        {products.length > 0 && (
          <section className="rounded-xl border border-border bg-surface-raised p-5">
            <h2 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-slate-500">Kiwi Product</h2>
            <p className="mb-3 text-[12px] text-slate-400">Bu Neurex projesine bağlanacak Kiwi ürününü seçin.</p>
            <div className="flex flex-wrap gap-2">
              {products.map(p => (
                <button
                  key={p.id}
                  onClick={() => handleSelectProduct(p.id)}
                  className={`rounded-lg border px-3 py-1.5 text-[12px] transition ${
                    productId === p.id
                      ? "border-teal-500 bg-teal-500/15 text-teal-300"
                      : "border-border text-slate-300 hover:bg-white/[0.04]"
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </section>
        )}

        {/* ── Senkron ── */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-slate-500">İçe Aktarım</h2>
          {productId == null ? (
            <p className="text-[12px] text-slate-500">Önce bağlantıyı test edip bir Kiwi Product seçin.</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => preview.mutate()}
                  disabled={preview.isPending}
                  className="rounded-lg border border-border px-4 py-2 text-[13px] font-medium text-slate-300 transition hover:bg-white/[0.04] disabled:opacity-40"
                >
                  {preview.isPending ? "Hesaplanıyor…" : "Önizleme (dry-run)"}
                </button>
                <label className="flex items-center gap-2 text-[12px] text-slate-400">
                  <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
                  Sadece dene (yazma)
                </label>
                <button
                  onClick={() => startSync.mutate({ dry_run: dryRun })}
                  disabled={startSync.isPending}
                  className="ml-auto rounded-lg bg-teal-600 px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-teal-500 disabled:opacity-40"
                >
                  {startSync.isPending ? "Başlatılıyor…" : "Senkronu başlat"}
                </button>
              </div>

              {preview.data?.ok && (
                <div className="grid grid-cols-4 gap-2">
                  {Object.entries(preview.data.counts).map(([k, v]) => (
                    <div key={k} className="rounded-lg border border-border bg-white/[0.02] px-3 py-2 text-center">
                      <div className="text-[18px] font-semibold text-slate-200">{v}</div>
                      <div className="text-[10px] uppercase tracking-wide text-slate-500">{ENTITY_LABELS[k] ?? k}</div>
                    </div>
                  ))}
                </div>
              )}
              {preview.data && !preview.data.ok && (
                <p className="text-[11px] text-rose-400">{preview.data.error}</p>
              )}
            </div>
          )}
        </section>

        {/* ── Job geçmişi ── */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-slate-500">Senkron Geçmişi</h2>
          {!syncJobs?.length ? (
            <p className="text-[12px] text-slate-500">Henüz senkron çalıştırılmadı.</p>
          ) : (
            <div className="space-y-2">
              {syncJobs.map(job => (
                <div key={job.id} className="rounded-lg border border-border bg-white/[0.02] px-3 py-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <JobStatus status={job.status} />
                      {job.dry_run && <span className="rounded bg-white/[0.06] px-1.5 py-0.5 text-[9px] text-slate-400">dry-run</span>}
                      <span className="text-[11px] text-slate-500">{new Date(job.created_at).toLocaleString("tr-TR")}</span>
                    </div>
                    <SyncTotals totals={job.totals} />
                  </div>
                  {job.error && <p className="mt-1 text-[11px] text-rose-400">{job.error}</p>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-[11px] text-slate-500">{label}</label>
      {children}
    </div>
  );
}

function JobStatus({ status }: { status: string }) {
  const cls =
    status === "succeeded"
      ? "bg-emerald-500/15 text-emerald-400"
      : status === "failed"
        ? "bg-rose-500/15 text-rose-400"
        : status === "running"
          ? "bg-amber-500/15 text-amber-400"
          : "bg-white/[0.06] text-slate-400";
  return <span className={`rounded px-2 py-0.5 text-[10px] ${cls}`}>{status}</span>;
}

function SyncTotals({ totals }: { totals: Record<string, { created: number; updated: number; skipped: number; errors: number }> }) {
  const sum = (k: "created" | "updated" | "skipped" | "errors") =>
    Object.values(totals || {}).reduce((acc, t) => acc + (t?.[k] ?? 0), 0);
  return (
    <span className="text-[11px] text-slate-400">
      <span className="text-emerald-400">+{sum("created")}</span>{" "}
      <span className="text-sky-400">~{sum("updated")}</span>{" "}
      <span className="text-slate-500">={sum("skipped")}</span>
      {sum("errors") > 0 && <span className="text-rose-400"> !{sum("errors")}</span>}
    </span>
  );
}
