"use client";

import { useEffect, useState } from "react";
import {
  useManagementSettingValue,
  usePatchManagementSetting,
  useKiwiConnection,
  useSaveKiwiConnection,
  useTestKiwiConnection,
  useKiwiPreview,
  useStartKiwiSync,
  useKiwiSyncJobs,
  useWebhookSubscriptions,
  useCreateWebhookSubscription,
  useDeleteWebhookSubscription,
  type CicdWebhookConfig,
  type KiwiProduct,
  type ProjectSsoConfig,
  type WebhookNotification,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api-client";
import { useProjectRole } from "@/lib/hooks/use-management-role";
import { Button } from "@/components/ui/button";

const ENTITY_LABELS: Record<string, string> = {
  suites: "Suite",
  cases: "Case",
  plans: "Plan",
  runs: "Run",
};

const STATUS_BADGE: Record<string, string> = {
  ok: "bg-emerald-500/15 text-emerald-400",
  error: "bg-rose-500/15 text-rose-400",
  unconfigured: "bg-surface-accent text-fg-muted",
};

type IntegrationTab = "kiwi" | "jira" | "cicd" | "sso" | "webhooks";

export default function ManagementIntegrationsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);
  const [activeTab, setActiveTab] = useState<IntegrationTab>("kiwi");

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
    <div className="min-h-[calc(100vh-88px)] bg-surface-base text-fg">
      {/* Header */}
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <h1 className="text-[13px] font-semibold text-fg">Entegrasyonlar</h1>
        <p className="mt-0.5 text-[11px] text-fg-subtle">Dış araçlarla bağlantı ve senkronizasyon</p>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-border bg-surface-raised px-6">
        {([
          { id: "kiwi", label: "Kiwi TCMS" },
          { id: "jira", label: "Jira" },
          { id: "cicd", label: "CI/CD Webhook" },
          { id: "sso", label: "SSO / SAML" },
          { id: "webhooks", label: "Webhook Bildirimleri" },
        ] as { id: IntegrationTab; label: string }[]).map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 border-b-2 px-4 py-3 text-[12px] font-medium transition-colors ${
              activeTab === tab.id
                ? "border-brand text-brand"
                : "border-transparent text-fg-subtle hover:text-fg"
            }`}
          >
            {tab.label}
            {tab.id === "jira" && (
              <span className="rounded-full bg-brand/15 px-1.5 py-0.5 text-[9px] font-bold text-brand">YENİ</span>
            )}
          </button>
        ))}
      </div>

      <div className="mx-auto max-w-2xl p-6 space-y-6">
        {activeTab === "sso" ? (
          <SsoPanel projectId={mpid ?? projectId ?? ""} />
        ) : activeTab === "webhooks" ? (
          <WebhookNotificationsPanel projectId={mpid ?? projectId ?? ""} />
        ) : activeTab === "jira" ? (
          <JiraIntegrationPanel projectId={projectId ?? ""} mpid={mpid ?? ""} />
        ) : activeTab === "cicd" ? (
          <CiCdWebhookPanel projectId={projectId ?? ""} mpid={mpid ?? ""} />
        ) : (<>
        {/* ── Bağlantı ── */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Kiwi TCMS Bağlantısı</h2>
            {connection && (
              <span className={`rounded px-2 py-0.5 text-[10px] ${STATUS_BADGE[connection.status] ?? STATUS_BADGE.unconfigured}`}>
                {connection.status === "ok" ? "Bağlı" : connection.status === "error" ? "Hata" : "Yapılandırılmadı"}
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-9 rounded bg-surface-overlay" />)}
            </div>
          ) : (
            <div className="space-y-3">
              <Field label="Kiwi URL">
                <input
                  value={baseUrl}
                  onChange={e => setBaseUrl(e.target.value)}
                  placeholder="https://kiwi.example.com"
                  className="w-full rounded-md border border-border bg-surface-overlay/30 px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/60"
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Kullanıcı adı">
                  <input
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    placeholder="api-user"
                    className="w-full rounded-md border border-border bg-surface-overlay/30 px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/60"
                  />
                </Field>
                <Field label={isConfigured ? "Token / Parola (değiştirmek için yaz)" : "Token / Parola"}>
                  <input
                    type="password"
                    value={secret}
                    onChange={e => setSecret(e.target.value)}
                    placeholder={isConfigured ? "••••••••" : "API token"}
                    className="w-full rounded-md border border-border bg-surface-overlay/30 px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/60"
                  />
                </Field>
              </div>
              <label className="flex items-center gap-2 text-[12px] text-fg-muted">
                <input type="checkbox" checked={verifySsl} onChange={e => setVerifySsl(e.target.checked)} />
                SSL sertifikasını doğrula
              </label>

              {connection?.last_error && (
                <p className="rounded-md bg-rose-500/10 px-3 py-2 text-[11px] text-rose-300">{connection.last_error}</p>
              )}

              <div className="flex items-center gap-2 pt-1">
                <Button
                  variant="primary"
                  onClick={handleSave}
                  disabled={!canSave || saveConn.isPending}
                >
                  {saveConn.isPending ? "Kaydediliyor…" : "Kaydet"}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleTest}
                  disabled={!isConfigured || testConn.isPending}
                >
                  {testConn.isPending ? "Test ediliyor…" : "Bağlantıyı test et"}
                </Button>
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
            <h2 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Kiwi Product</h2>
            <p className="mb-3 text-[12px] text-fg-muted">Bu Neurex projesine bağlanacak Kiwi ürününü seçin.</p>
            <div className="flex flex-wrap gap-2">
              {products.map(p => (
                <button
                  key={p.id}
                  onClick={() => handleSelectProduct(p.id)}
                  className={`rounded-lg border px-3 py-1.5 text-[12px] transition ${
                    productId === p.id
                      ? "border-teal-500 bg-teal-500/15 text-teal-300"
                      : "border-border text-fg hover:bg-surface-overlay"
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
          <h2 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">İçe Aktarım</h2>
          {productId == null ? (
            <p className="text-[12px] text-fg-subtle">Önce bağlantıyı test edip bir Kiwi Product seçin.</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  onClick={() => preview.mutate()}
                  disabled={preview.isPending}
                >
                  {preview.isPending ? "Hesaplanıyor…" : "Önizleme (dry-run)"}
                </Button>
                <label className="flex items-center gap-2 text-[12px] text-fg-muted">
                  <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
                  Sadece dene (yazma)
                </label>
                <Button
                  variant="primary"
                  onClick={() => startSync.mutate({ dry_run: dryRun })}
                  disabled={startSync.isPending}
                  className="ml-auto"
                >
                  {startSync.isPending ? "Başlatılıyor…" : "Senkronu başlat"}
                </Button>
              </div>

              {preview.data?.ok && (
                <div className="grid grid-cols-4 gap-2">
                  {Object.entries(preview.data.counts).map(([k, v]) => (
                    <div key={k} className="rounded-lg border border-border bg-surface-overlay/30 px-3 py-2 text-center">
                      <div className="text-[18px] font-semibold text-fg">{v}</div>
                      <div className="text-[10px] uppercase tracking-wide text-fg-subtle">{ENTITY_LABELS[k] ?? k}</div>
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
          <h2 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Senkron Geçmişi</h2>
          {!syncJobs?.length ? (
            <p className="text-[12px] text-fg-subtle">Henüz senkron çalıştırılmadı.</p>
          ) : (
            <div className="space-y-2">
              {syncJobs.map(job => (
                <div key={job.id} className="rounded-lg border border-border bg-surface-overlay/30 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <JobStatus status={job.status} />
                      {job.dry_run && <span className="rounded bg-surface-accent px-1.5 py-0.5 text-[9px] text-fg-muted">dry-run</span>}
                      <span className="text-[11px] text-fg-subtle">{new Date(job.created_at).toLocaleString("tr-TR")}</span>
                    </div>
                    <SyncTotals totals={job.totals} />
                  </div>
                  {job.error && <p className="mt-1 text-[11px] text-rose-400">{job.error}</p>}
                </div>
              ))}
            </div>
          )}
        </section>
        </>)}
      </div>
    </div>
  );
}

// ─── SSO / SAML Panel ────────────────────────────────────────────────────────

const DEFAULT_SSO_CONFIG: ProjectSsoConfig = { enabled: false, entityId: "", ssoUrl: "", cert: "" };

function SsoPanel({ projectId }: { projectId: string }) {
  const { data: savedConfig, isLoading } = useManagementSettingValue<ProjectSsoConfig>(
    projectId || undefined,
    "sso_config",
    DEFAULT_SSO_CONFIG,
  );
  const saveSso = usePatchManagementSetting<ProjectSsoConfig>(projectId, "sso_config");
  const [config, setConfig] = useState<ProjectSsoConfig>(DEFAULT_SSO_CONFIG);
  const [toast, setToast] = useState<{ type: "ok" | "error"; msg: string } | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    setConfig(savedConfig);
  }, [savedConfig]);

  const showToast = (type: "ok" | "error", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3500);
  };

  const handleSave = async () => {
    try {
      await saveSso.mutateAsync(config);
      showToast("ok", "SSO yapılandırması kaydedildi.");
    } catch {
      showToast("error", "Kaydedilemedi.");
    }
  };

  const handleTest = async () => {
    if (!config.entityId || !config.ssoUrl) {
      showToast("error", "Entity ID ve SSO URL zorunludur.");
      return;
    }
    setTesting(true);
    try {
      const res = await apiFetch<{ ok: boolean; status_code?: number; message: string }>(
        `/api/v1/test-management/projects/${projectId}/sso-test`,
        {
          method: "POST",
          json: { entity_id: config.entityId, sso_url: config.ssoUrl },
        },
      );
      showToast(res.ok ? "ok" : "error", res.message);
    } catch {
      showToast("error", "SSO URL'e ulaşılamadı — URL'i ve ağ erişimini kontrol edin.");
    } finally {
      setTesting(false);
    }
  };

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-2 focus:ring-brand/15";

  const SSO_PROVIDERS = ["Okta", "Azure AD", "Auth0", "Google Workspace"];

  return (
    <div className="space-y-5">
      {/* Toast */}
      {toast && (
        <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-[12px] ${
          toast.type === "ok"
            ? "border-emerald-500/30 bg-emerald-500/8 text-emerald-400"
            : "border-danger/30 bg-danger-subtle text-danger"
        }`}>
          {toast.type === "ok" ? "✓" : "✗"} {toast.msg}
        </div>
      )}

      <section className="rounded-xl border border-border bg-surface-raised p-5 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div>
            <h3 className="text-[13px] font-semibold text-fg">SSO / SAML Yapılandırması</h3>
            <p className="mt-0.5 text-[11px] text-fg-subtle">Tek oturum açma ile kurumsal kimlik doğrulama</p>
          </div>
          {/* Toggle */}
          <button
            type="button"
            onClick={() => setConfig(c => ({ ...c, enabled: !c.enabled }))}
            disabled={isLoading || saveSso.isPending}
            className={`relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors ${
              config.enabled ? "bg-brand" : "bg-surface-overlay border-border"
            }`}
            role="switch"
            aria-checked={config.enabled}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                config.enabled ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
        </div>

        {/* Fields */}
        <div className={`space-y-4 transition-opacity ${config.enabled ? "opacity-100" : "opacity-50 pointer-events-none"}`}>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">Entity ID</label>
            <input
              value={config.entityId}
              onChange={e => setConfig(c => ({ ...c, entityId: e.target.value }))}
              placeholder="https://yourcompany.com/saml/entity"
              className={inp}
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">SSO URL</label>
            <input
              value={config.ssoUrl}
              onChange={e => setConfig(c => ({ ...c, ssoUrl: e.target.value }))}
              placeholder="https://yourcompany.okta.com/app/saml/sso"
              className={inp}
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">X.509 Sertifikası</label>
            <textarea
              value={config.cert}
              onChange={e => setConfig(c => ({ ...c, cert: e.target.value }))}
              placeholder="-----BEGIN CERTIFICATE-----&#10;MIICpDCCAYwCCQD...&#10;-----END CERTIFICATE-----"
              rows={5}
              className={`${inp} resize-none font-mono text-[11px]`}
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <Button
              type="button"
              variant="outline"
              onClick={handleTest}
              disabled={testing}
            >
              {testing ? "Test ediliyor…" : "Test Et"}
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={handleSave}
              disabled={saveSso.isPending}
            >
              {saveSso.isPending ? "Kaydediliyor…" : "Kaydet"}
            </Button>
          </div>
        </div>
      </section>

      {/* Provider badges */}
      <section className="rounded-xl border border-border bg-surface-raised p-5">
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Desteklenen Sağlayıcılar</h3>
        <div className="flex flex-wrap gap-2">
          {SSO_PROVIDERS.map(p => (
            <span
              key={p}
              className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[12px] font-medium text-fg-muted"
            >
              {p}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}

// ─── Webhook Notifications Panel ──────────────────────────────────────────────

type WebhookEvent =
  | "run.completed"
  | "run.failed"
  | "defect.created"
  | "defect.blocker"
  | "case.failed"
  | "release.signoff";

const WEBHOOK_EVENTS: { id: WebhookEvent; label: string }[] = [
  { id: "run.completed",   label: "Koşum tamamlandı" },
  { id: "run.failed",      label: "Koşum başarısız" },
  { id: "defect.created",  label: "Defekt oluşturuldu" },
  { id: "defect.blocker",  label: "Blocker defekt" },
  { id: "case.failed",     label: "Case başarısız" },
  { id: "release.signoff", label: "Release onayı" },
];

type WebhookEntry = WebhookNotification & { events: WebhookEvent[] };

function WebhookNotificationsPanel({ projectId }: { projectId: string }) {
  const { data: fetchedWebhooks, isLoading } = useWebhookSubscriptions(projectId || undefined);
  const createWebhook = useCreateWebhookSubscription(projectId);
  const deleteWebhook = useDeleteWebhookSubscription(projectId);
  const webhooks: WebhookEntry[] = (fetchedWebhooks ?? []) as WebhookEntry[];
  const [showModal, setShowModal] = useState(false);
  const [toast, setToast] = useState<{ type: "ok" | "error"; msg: string } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const currentRole = useProjectRole(projectId);
  const canEdit = currentRole === "owner" || currentRole === "admin";

  const showToast = (type: "ok" | "error", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3500);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteWebhook.mutateAsync(id);
      setConfirmDelete(null);
      showToast("ok", "Webhook silindi.");
    } catch {
      showToast("error", "Webhook silinemedi.");
    }
  };

  const handleTest = async (w: WebhookEntry) => {
    try {
      const res = await apiFetch<{ ok: boolean; status_code?: number; message: string }>(
        `/api/v1/test-management/projects/${projectId}/webhook-test`,
        {
          method: "POST",
          json: {
            url: w.url,
            payload: {
              event: w.events[0] ?? "run.completed",
              configured_events: w.events,
              timestamp: new Date().toISOString(),
            },
          },
        },
      );
      if (res.ok) {
        showToast("ok", `Test gönderildi → ${w.url.slice(0, 40)}…`);
      } else {
        showToast("error", res.status_code ? `Webhook yanıt vermedi (${res.status_code})` : res.message);
      }
    } catch {
      showToast("error", "Webhook URL'e ulaşılamadı.");
    }
  };

  const handleAdd = async (entry: Omit<WebhookEntry, "id">) => {
    try {
      await createWebhook.mutateAsync({ url: entry.url, events: entry.events });
      setShowModal(false);
      showToast("ok", "Webhook eklendi.");
    } catch {
      showToast("error", "Webhook kaydedilemedi.");
    }
  };

  const isBusy = createWebhook.isPending || deleteWebhook.isPending;

  return (
    <div className="space-y-5">
      {/* Toast */}
      {toast && (
        <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-[12px] ${
          toast.type === "ok"
            ? "border-emerald-500/30 bg-emerald-500/8 text-emerald-400"
            : "border-danger/30 bg-danger-subtle text-danger"
        }`}>
          {toast.type === "ok" ? "✓" : "✗"} {toast.msg}
        </div>
      )}

      <section className="rounded-xl border border-border bg-surface-raised p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div>
            <h3 className="text-[13px] font-semibold text-fg">Webhook Bildirimleri</h3>
            <p className="mt-0.5 text-[11px] text-fg-subtle">Olaylar gerçekleştiğinde dış sistemlere bildirim gönder</p>
          </div>
          {canEdit && (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => setShowModal(true)}
              disabled={isLoading || isBusy}
              className="gap-1.5"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14"/>
              </svg>
              Yeni Webhook
            </Button>
          )}
        </div>

        {/* Webhook list */}
        {webhooks.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-fg-subtle">
            <svg className="h-8 w-8 text-fg-disabled" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
            </svg>
            <p className="text-[13px]">Henüz webhook eklenmedi</p>
            <p className="text-[11px] text-fg-disabled">Yeni Webhook butonuna tıklayın</p>
          </div>
        ) : (
          <div className="space-y-3">
            {webhooks.map(w => (
              <div key={w.id} className="flex items-start gap-3 rounded-xl border border-border bg-surface-overlay px-4 py-3">
                <div className="flex-1 min-w-0 space-y-1">
                  <p className="truncate font-mono text-[12px] text-fg">{w.url}</p>
                  <div className="flex flex-wrap gap-1">
                    {w.events.map(e => (
                      <span key={e} className="rounded bg-brand/10 px-1.5 py-0.5 text-[10px] font-medium text-brand">
                        {e}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleTest(w)}
                    disabled={isBusy}
                  >
                    Test
                  </Button>
                  {canEdit && (confirmDelete === w.id ? (
                    <div className="flex items-center gap-1">
                      <Button
                        type="button"
                        variant="ghost-danger"
                        size="sm"
                        onClick={() => handleDelete(w.id)}
                        disabled={deleteWebhook.isPending}
                        className="border border-danger/30 bg-danger-subtle"
                      >
                        {deleteWebhook.isPending ? "Siliniyor…" : "Sil"}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setConfirmDelete(null)}
                      >
                        İptal
                      </Button>
                    </div>
                  ) : (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setConfirmDelete(w.id)}
                      className="hover:border-danger/30 hover:bg-danger-subtle hover:text-danger"
                    >
                      Sil
                    </Button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Add Webhook Modal */}
      {showModal && (
        <AddWebhookModal
          onClose={() => setShowModal(false)}
          onAdd={handleAdd}
        />
      )}
    </div>
  );
}

// ─── Add Webhook Modal ────────────────────────────────────────────────────────

function AddWebhookModal({
  onClose,
  onAdd,
}: {
  onClose: () => void;
  onAdd: (_entry: Omit<WebhookEntry, "id">) => void | Promise<void>;
}) {
  const [url, setUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<Set<WebhookEvent>>(new Set());
  const [error, setError] = useState("");

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const toggleEvent = (ev: WebhookEvent) => {
    setSelectedEvents(prev => {
      const next = new Set(prev);
      if (next.has(ev)) next.delete(ev);
      else next.add(ev);
      return next;
    });
  };

  const handleAdd = () => {
    if (!url.trim()) { setError("URL zorunludur."); return; }
    try { new URL(url.trim()); } catch { setError("Geçerli bir URL giriniz."); return; }
    if (selectedEvents.size === 0) { setError("En az bir olay seçmelisiniz."); return; }
    void onAdd({ url: url.trim(), events: Array.from(selectedEvents) });
  };

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-2 focus:ring-brand/15";

  return (
    <div
      className="fixed inset-0 z-[300] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-border bg-surface-raised shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h3 className="text-[14px] font-semibold text-fg">Yeni Webhook Ekle</h3>
          <button type="button" onClick={onClose}
            className="rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 p-5">
          {error && (
            <p className="rounded-xl border border-danger/30 bg-danger-subtle px-3 py-2 text-[12px] text-danger">
              {error}
            </p>
          )}
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">Webhook URL *</label>
            <input
              value={url}
              onChange={e => { setUrl(e.target.value); setError(""); }}
              placeholder="https://hooks.slack.com/services/..."
              className={inp}
              autoFocus
            />
          </div>

          <div>
            <label className="mb-2 block text-[11px] font-medium text-fg-muted">Olaylar *</label>
            <div className="space-y-2">
              {WEBHOOK_EVENTS.map(ev => (
                <label key={ev.id} className="flex items-center gap-3 cursor-pointer rounded-lg p-2 hover:bg-surface-overlay transition-colors">
                  <input
                    type="checkbox"
                    checked={selectedEvents.has(ev.id)}
                    onChange={() => toggleEvent(ev.id)}
                    className="h-3.5 w-3.5 rounded border-border accent-brand"
                  />
                  <span className="text-[12px] text-fg">{ev.label}</span>
                  <span className="ml-auto rounded bg-surface-overlay px-1.5 py-0.5 font-mono text-[10px] text-fg-disabled">{ev.id}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-4">
          <Button type="button" variant="outline" onClick={onClose}>
            İptal
          </Button>
          <Button type="button" variant="primary" onClick={handleAdd}>
            Ekle
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── JIRA Integration Panel ───────────────────────────────────────────────────

function JiraIntegrationPanel({ projectId: _projectId, mpid }: { projectId: string; mpid: string }) {
  const [url, setUrl] = useState("");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [projectKey, setProjectKey] = useState("");
  const [status, setStatus] = useState<"idle" | "testing" | "ok" | "error">("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [jiraWarning, setJiraWarning] = useState<string | null>(null);
  const [savedProjectKey, setSavedProjectKey] = useState<string | null>(null);
  const [isConfigured, setIsConfigured] = useState(false);

  // Kayıtlı config'i yükle
  useEffect(() => {
    if (!mpid) return;
    apiFetch<{ configured?: boolean; url?: string; email?: string; project_key?: string }>(`/api/jira/config`)
      .then(data => {
        if (data.url) setUrl(data.url);
        if (data.email) setEmail(data.email);
        if (data.project_key) {
          setProjectKey(data.project_key);
          setSavedProjectKey(data.project_key);
        }
        setIsConfigured(!!data.configured);
      })
      .catch(() => {});
  }, [mpid]);

  const handleTest = async () => {
    // Backend, DB'deki kayıtlı config ile test eder — token gerekmez
    if (!url.trim() || !email.trim()) return;
    setStatus("testing"); setStatusMsg("");
    try {
      const res = await apiFetch<{ ok: boolean; user?: string; message?: string }>("/api/jira/test-connection", {
        method: "POST",
        json: {},
      });
      setStatus(res.ok ? "ok" : "error");
      setStatusMsg(res.message ?? (res.ok ? `Bağlantı başarılı${res.user ? ` (${res.user})` : ""}!` : "Bağlantı başarısız."));
    } catch {
      setStatus("error"); setStatusMsg("Bağlantı kurulamadı.");
    }
  };

  const handleSave = async () => {
    // Jira project_key değişiklik uyarısı
    const trimmedKey = projectKey.trim();
    if (savedProjectKey && trimmedKey && trimmedKey !== savedProjectKey) {
      setJiraWarning("Proje anahtarı değiştiriliyor. Eski defect linkleri güncellenmeyecek.");
    } else {
      setJiraWarning(null);
    }
    setSaving(true);
    try {
      await apiFetch("/api/jira/config", {
        method: "POST",
        // token boşsa backend mevcut token'ı korur
        json: { url: url.trim(), email: email.trim(), token: token.trim(), project_key: trimmedKey },
      });
      setSaved(true); setToken("");
      setIsConfigured(true);
      setSavedProjectKey(trimmedKey || savedProjectKey);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setStatusMsg("Kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  };

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-2 focus:ring-brand/15";

  return (
    <div className="space-y-5">
      {/* Status banner */}
      {status !== "idle" && (
        <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-[12px] ${
          status === "ok" ? "border-emerald-500/30 bg-emerald-500/8 text-emerald-400" :
          status === "error" ? "border-danger/30 bg-danger-subtle text-danger" :
          "border-border bg-surface-overlay text-fg-muted"
        }`}>
          {status === "testing" && (
            <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-6.219-8.56"/>
            </svg>
          )}
          {statusMsg || (status === "testing" ? "Test ediliyor…" : "")}
        </div>
      )}

      {/* Jira project_key change warning */}
      {jiraWarning && (
        <div className="flex items-center justify-between gap-2 rounded-xl border border-amber-500/30 bg-amber-500/8 px-4 py-3 text-[12px] text-amber-400">
          <span>⚠️ {jiraWarning}</span>
          <button type="button" onClick={() => setJiraWarning(null)}
            className="shrink-0 text-amber-400/60 hover:text-amber-400 transition-colors">
            ✕
          </button>
        </div>
      )}

      {/* Jira bağlantı formu */}
      <section className="rounded-xl border border-border bg-surface-raised p-5 space-y-4">
        <div className="flex items-center gap-3 pb-2 border-b border-border">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-surface-overlay">
            <svg className="h-5 w-5 text-blue-400" viewBox="0 0 32 32" fill="currentColor">
              <path d="M15.996 0C7.163 0 0 7.163 0 15.996 0 24.83 7.163 32 15.996 32 24.83 32 32 24.83 32 15.996 32 7.163 24.83 0 15.996 0zm7.594 18.408l-7.594 7.594-7.594-7.594 7.594-7.594 7.594 7.594z"/>
            </svg>
          </div>
          <div>
            <p className="text-[13px] font-semibold text-fg">Jira Bağlantısı</p>
            <p className="text-[11px] text-fg-subtle">Atlassian Jira Cloud veya Server</p>
          </div>
          {saved && (
            <span className="ml-auto rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-400">
              ✓ Kaydedildi
            </span>
          )}
        </div>

        <div>
          <label className="mb-1 block text-[11px] font-medium text-fg-muted">Jira URL *</label>
          <input value={url} onChange={e => setUrl(e.target.value)}
            placeholder="https://yourcompany.atlassian.net"
            className={inp} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">E-posta *</label>
            <input value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com" type="email" className={inp} />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">API Token *</label>
            <input value={token} onChange={e => setToken(e.target.value)}
              placeholder={url ? "Yeni token girin" : "Token giriniz"}
              type="password" className={inp} />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-[11px] font-medium text-fg-muted">Varsayılan Proje Anahtarı</label>
          <input value={projectKey} onChange={e => setProjectKey(e.target.value)}
            placeholder="örn. BUG veya QA" className={inp} />
          <p className="mt-1 text-[11px] text-fg-subtle">Defektleri Jira'ya aktarırken kullanılır.</p>
        </div>

        <div className="flex items-center gap-2 pt-1">
          <Button type="button" variant="outline" onClick={handleTest}
            disabled={(!isConfigured && !token.trim()) || !url.trim() || !email.trim() || status === "testing"}>
            {status === "testing" ? "Test ediliyor…" : "Bağlantıyı Test Et"}
          </Button>
          <Button type="button" variant="primary" onClick={handleSave}
            disabled={saving || !url.trim() || !email.trim()}>
            {saving ? "Kaydediliyor…" : "Kaydet"}
          </Button>
        </div>
      </section>

      {/* Özellikler */}
      <section className="rounded-xl border border-border bg-surface-raised p-5">
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Desteklenen İşlemler</h3>
        <div className="grid gap-2 sm:grid-cols-2">
          {[
            { icon: "🐛", title: "Defekt → Jira Issue", desc: "Koşum sırasında defekt bağlayınca otomatik Jira issue açılır." },
            { icon: "🔗", title: "Issue Bağlama", desc: "Mevcut Jira issue'larını test case'lerinize link edin." },
            { icon: "🔄", title: "Run Sonuçları Senkronizasyonu", desc: "Test koşumu sonuçlarını Jira'daki ilgili issue'lara yansıtın." },
            { icon: "📋", title: "Issue'dan Case Oluştur", desc: "Jira issue'larından otomatik test case taslakları üretin." },
          ].map(f => (
            <div key={f.icon} className="flex gap-3 rounded-lg border border-border bg-surface-overlay p-3">
              <span className="text-lg">{f.icon}</span>
              <div>
                <p className="text-[12px] font-medium text-fg">{f.title}</p>
                <p className="text-[11px] text-fg-subtle">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// ─── CI/CD Webhook Panel ─────────────────────────────────────────────────────────

function CiCdWebhookPanel({ projectId, mpid }: { projectId: string; mpid: string }) {
  const settingsProjectId = mpid || projectId;
  const { data: savedConfig } = useManagementSettingValue<CicdWebhookConfig>(
    settingsProjectId || undefined,
    "cicd_webhook",
    { webhookUrl: "", secret: "", provider: "github" },
  );
  const saveCicd = usePatchManagementSetting<CicdWebhookConfig>(settingsProjectId, "cicd_webhook");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [provider, setProvider] = useState("github");
  const [copied, setCopied] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; status_code?: number; message: string } | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setWebhookUrl(savedConfig.webhookUrl ?? "");
    setWebhookSecret(savedConfig.secret ?? "");
    setProvider(savedConfig.provider ?? "github");
  }, [savedConfig]);

  // Webhook URL'i hesapla (bu projeye gelen hook endpoint'i)
  const inboundUrl = typeof window !== "undefined"
    ? `${window.location.origin}/api/v1/test-management/projects/${projectId}/webhook`
    : "";

  const copyInboundUrl = () => {
    navigator.clipboard.writeText(inboundUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  };

  const testWebhook = async () => {
    if (!webhookUrl.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await apiFetch<{ ok: boolean; status_code?: number; message: string }>(
        `/api/v1/test-management/projects/${projectId}/webhook-test`,
        {
          method: "POST",
          json: {
            url: webhookUrl.trim(),
            secret: webhookSecret.trim() || undefined,
            payload: {
              provider,
              timestamp: new Date().toISOString(),
            },
          },
        },
      );
      setTestResult(result);
    } catch (err: unknown) {
      setTestResult({ ok: false, message: err instanceof Error ? err.message : "Test başarısız" });
    } finally {
      setTesting(false);
    }
  };

  const saveWebhook = async () => {
    await saveCicd.mutateAsync({
      webhookUrl: webhookUrl.trim(),
      secret: webhookSecret.trim() || undefined,
      provider,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-2 focus:ring-brand/15";
  const codeStyle = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 font-mono text-[11px] text-fg-muted break-all";

  return (
    <div className="space-y-5">
      {/* Gelen Webhook — CI/CD sistemi bu URL'i çağırır */}
      <section className="rounded-xl border border-border bg-surface-raised p-5 space-y-4">
        <div className="pb-2 border-b border-border">
          <h3 className="text-[13px] font-semibold text-fg">Gelen Webhook (CI/CD → Neurex)</h3>
          <p className="mt-0.5 text-[11px] text-fg-subtle">
            CI pipeline'ınız tamamlandığında bu URL'e POST isteği gönderin.
          </p>
        </div>

        <div>
          <label className="mb-1 block text-[11px] font-medium text-fg-muted">Webhook Endpoint</label>
          <div className="flex items-center gap-2">
            <div className={codeStyle}>{inboundUrl || "URL yükleniyor…"}</div>
            <Button type="button" variant="outline" onClick={copyInboundUrl} className="shrink-0">
              {copied ? "✓ Kopyalandı" : "Kopyala"}
            </Button>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-[11px] font-medium text-fg-muted">Webhook Secret (opsiyonel)</label>
          <input value={webhookSecret} onChange={e => setWebhookSecret(e.target.value)}
            type="password" placeholder="İmza doğrulaması için gizli anahtar"
            className={inp} />
          <p className="mt-1 text-[11px] text-fg-subtle">X-Webhook-Secret başlığıyla gönderilir.</p>
        </div>

        {/* Örnek payload */}
        <details className="group">
          <summary className="cursor-pointer text-[11px] text-brand hover:text-brand-secondary">
            Örnek payload göster ▸
          </summary>
          <pre className="mt-2 overflow-x-auto rounded-xl border border-border bg-surface-overlay p-3 text-[10px] text-fg-muted">
{`{
  "event": "run.completed",
  "project_id": "${projectId}",
  "run_id": "abc123",
  "branch": "main",
  "commit_sha": "a1b2c3d4",
  "status": "passed",
  "pass_rate": 87.5,
  "failed_count": 2,
  "timestamp": "2026-06-04T20:00:00Z"
}`}
          </pre>
        </details>
      </section>

      {/* Giden Webhook — Neurex → CI/CD sistemi çağırır */}
      <section className="rounded-xl border border-border bg-surface-raised p-5 space-y-4">
        <div className="pb-2 border-b border-border">
          <h3 className="text-[13px] font-semibold text-fg">Giden Webhook (Neurex → CI/CD)</h3>
          <p className="mt-0.5 text-[11px] text-fg-subtle">
            Run tamamlandığında veya release gate karşılandığında çağrılacak URL.
          </p>
        </div>

        <div>
          <label className="mb-1 block text-[11px] font-medium text-fg-muted">Hedef URL</label>
          <input value={webhookUrl} onChange={e => setWebhookUrl(e.target.value)}
            placeholder="https://hooks.example.com/neurex-webhook"
            className={inp} />
        </div>

        <div>
          <label className="mb-1 block text-[11px] font-medium text-fg-muted">Platform</label>
          <select value={provider} onChange={e => setProvider(e.target.value)} className={inp}>
            <option value="github">GitHub Actions</option>
            <option value="gitlab">GitLab CI</option>
            <option value="jenkins">Jenkins</option>
            <option value="azure">Azure DevOps</option>
            <option value="custom">Özel</option>
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Button type="button" variant="outline" onClick={testWebhook}
              disabled={!projectId || !webhookUrl.trim() || testing}>
              {testing ? "Gönderiliyor…" : "Test Gönder"}
            </Button>
            <Button type="button" variant="primary" onClick={saveWebhook}
              disabled={!settingsProjectId || !webhookUrl.trim() || saveCicd.isPending}>
              {saveCicd.isPending ? "Kaydediliyor…" : saved ? "Kaydedildi ✓" : "Webhook Kaydet"}
            </Button>
          </div>
          {testResult && (
            <div className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-[12px] ${
              testResult.ok
                ? "border-emerald-500/30 bg-emerald-500/8 text-emerald-400"
                : "border-danger/30 bg-danger-subtle text-danger"
            }`}>
              {testResult.ok ? "✓" : "✗"}{" "}
              {testResult.message || (testResult.ok ? "Test başarılı" : "Test başarısız")}
              {testResult.status_code && !testResult.ok && ` (HTTP ${testResult.status_code})`}
            </div>
          )}
        </div>
      </section>

      {/* Platform kılavuzu */}
      <section className="rounded-xl border border-border bg-surface-raised p-5">
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
          {provider === "github" ? "GitHub Actions" : provider === "gitlab" ? "GitLab CI" : provider === "jenkins" ? "Jenkins" : provider === "azure" ? "Azure DevOps" : "Özel"} Entegrasyon Kılavuzu
        </h3>
        <div className="rounded-xl border border-border bg-surface-overlay p-3">
          {provider === "github" && (
            <pre className="overflow-x-auto text-[10px] text-fg-muted whitespace-pre-wrap">
{`# .github/workflows/test-report.yml
- name: Neurex'e bildir
  if: always()
  run: |
    curl -X POST "${inboundUrl}" \\
      -H "Content-Type: application/json" \\
      -H "X-Webhook-Secret: \${{ secrets.NEUREX_SECRET }}" \\
      -d '{
        "event": "run.completed",
        "branch": "\${{ github.ref_name }}",
        "commit_sha": "\${{ github.sha }}",
        "status": "\${{ job.status }}"
      }'`}
            </pre>
          )}
          {provider === "gitlab" && (
            <pre className="overflow-x-auto text-[10px] text-fg-muted whitespace-pre-wrap">
{`# .gitlab-ci.yml
notify_neurex:
  stage: .post
  script:
    - curl -X POST "${inboundUrl}"
      -H "X-Webhook-Secret: $NEUREX_SECRET"
      -d "{\\"event\\":\\"run.completed\\",\\"status\\":\\"$CI_JOB_STATUS\\"}"`}
            </pre>
          )}
          {provider === "jenkins" && (
            <pre className="overflow-x-auto text-[10px] text-fg-muted whitespace-pre-wrap">
{`// Jenkinsfile
post {
  always {
    httpRequest(
      url: "${inboundUrl}",
      httpMode: "POST",
      requestBody: """{"event":"run.completed","status":"\${currentBuild.result}"}""",
      customHeaders: [[name: "X-Webhook-Secret", value: NEUREX_SECRET]]
    )
  }
}`}
            </pre>
          )}
          {(provider === "azure" || provider === "custom") && (
            <pre className="overflow-x-auto text-[10px] text-fg-muted whitespace-pre-wrap">
{`curl -X POST "${inboundUrl}" \\
  -H "Content-Type: application/json" \\
  -H "X-Webhook-Secret: YOUR_SECRET" \\
  -d '{"event":"run.completed","status":"passed"}'`}
            </pre>
          )}
        </div>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-[11px] text-fg-subtle">{label}</label>
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
          : "bg-surface-accent text-fg-muted";
  return <span className={`rounded px-2 py-0.5 text-[10px] ${cls}`}>{status}</span>;
}

function SyncTotals({ totals }: { totals: Record<string, { created: number; updated: number; skipped: number; errors: number }> }) {
  const sum = (k: "created" | "updated" | "skipped" | "errors") =>
    Object.values(totals || {}).reduce((acc, t) => acc + (t?.[k] ?? 0), 0);
  return (
    <span className="text-[11px] text-fg-muted">
      <span className="text-emerald-400">+{sum("created")}</span>{" "}
      <span className="text-sky-400">~{sum("updated")}</span>{" "}
      <span className="text-fg-subtle">={sum("skipped")}</span>
      {sum("errors") > 0 && <span className="text-rose-400"> !{sum("errors")}</span>}
    </span>
  );
}
