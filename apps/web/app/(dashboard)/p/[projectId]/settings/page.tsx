"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { useNotifPrefs, useUpdateNotifPrefs, type NotifPrefs } from "@/lib/hooks/use-profile";
import { ConfirmDialog } from "@/components/ConfirmDialog";

// ── Types ──────────────────────────────────────────────────────────────────────

type Project = {
  id: string;
  name: string;
  description: string;
  base_url: string;
};

type FeatureFlag = {
  key: string;
  enabled: boolean;
  description: string | null;
};

type WebhookNotification = {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
};

type Tab = "general" | "notifications" | "webhooks" | "feature-flags";

// ── Helpers ────────────────────────────────────────────────────────────────────

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active
          ? "bg-blue-600 text-white"
          : "text-slate-400 hover:text-white hover:bg-slate-800"
      }`}
    >
      {children}
    </button>
  );
}

function SectionBox({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
      <div>
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {description && <p className="mt-1 text-sm text-slate-400">{description}</p>}
      </div>
      {children}
    </div>
  );
}

// ── General Tab ────────────────────────────────────────────────────────────────

function GeneralTab({ projectId }: { projectId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", description: "", base_url: "" });
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: project, isLoading: loading } = useQuery<Project>({
    queryKey: ["projects", "detail", projectId],
    queryFn: () => apiFetch<Project>(`/api/v1/tspm/projects/${projectId}`),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (project) {
      setForm({
        name: project.name ?? "",
        description: project.description ?? "",
        base_url: project.base_url ?? "",
      });
    }
  }, [project]);

  const saveMut = useMutation({
    mutationFn: () =>
      apiFetch<Project>(`/api/v1/tspm/projects/${projectId}`, {
        method: "PUT",
        json: { name: form.name, description: form.description, base_url: form.base_url },
      }),
    onSuccess: (updated) => {
      setSaveMsg({ ok: true, text: "Proje ayarlari kaydedildi." });
      queryClient.setQueryData(["projects", "detail", projectId], updated);
      queryClient.invalidateQueries({ queryKey: ["projects", "list"] });
    },
    onError: () => setSaveMsg({ ok: false, text: "Kaydetme basarisiz. Lutfen tekrar deneyin." }),
  });

  const deleteMut = useMutation({
    mutationFn: () => apiFetch(`/api/v1/tspm/projects/${projectId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", "list"] });
      router.push("/portfolio");
    },
  });

  if (loading) {
    return <div className="py-8 text-sm text-slate-400">Proje bilgileri yukleniyor...</div>;
  }

  return (
    <div className="space-y-6">
      <SectionBox title="Proje Bilgileri" description="Proje adi, aciklama ve hedef URL'yi duzenleyin.">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSaveMsg(null);
            saveMut.mutate();
          }}
          className="space-y-5"
        >
          <div className="flex flex-col gap-1.5">
            <label htmlFor="proj-name" className="text-sm font-medium text-white">
              Proje Adi <span className="text-red-500">*</span>
            </label>
            <input
              id="proj-name"
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              className="h-9 rounded border border-slate-700 bg-slate-800 px-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Orn: ARK Bankacilik"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="proj-desc" className="text-sm font-medium text-white">Aciklama</label>
            <textarea
              id="proj-desc"
              rows={3}
              value={form.description}
              onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
              className="rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Projeyle ilgili kisa bir aciklama..."
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="proj-url" className="text-sm font-medium text-white">Base URL</label>
            <input
              id="proj-url"
              type="url"
              value={form.base_url}
              onChange={(e) => setForm((p) => ({ ...p, base_url: e.target.value }))}
              className="h-9 rounded border border-slate-700 bg-slate-800 px-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://uygulama.ornek.com"
            />
            <p className="text-xs text-slate-400">Test senaryolari ve otomasyon icin hedef uygulama adresi.</p>
          </div>
          {saveMsg && (
            <p className={`text-sm ${saveMsg.ok ? "text-emerald-400" : "text-red-400"}`}>
              {saveMsg.text}
            </p>
          )}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saveMut.isPending}
              className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {saveMut.isPending ? "Kaydediliyor..." : "Kaydet"}
            </button>
          </div>
        </form>
      </SectionBox>

      <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-6 space-y-3">
        <h2 className="text-sm font-semibold text-red-400">Tehlikeli Alan</h2>
        <p className="text-sm text-red-400/80">
          Bu projeyi silmek, tum senaryo, kosu ve raporlari kalici olarak kaldirir.
        </p>
        <button
          type="button"
          onClick={() => setConfirmDelete(true)}
          disabled={deleteMut.isPending}
          className="rounded-lg border border-red-600 bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 disabled:opacity-50 transition-colors"
        >
          {deleteMut.isPending ? "Siliniyor..." : "Projeyi Sil"}
        </button>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Projeyi Sil"
        description={`"${form.name}" projesini silmek istediginizden emin misiniz? Bu islem geri alinamaz.`}
        confirmLabel="Evet, Sil"
        variant="destructive"
        onConfirm={() => {
          setConfirmDelete(false);
          deleteMut.mutate();
        }}
        isLoading={deleteMut.isPending}
      />
    </div>
  );
}

// ── Notifications Tab ──────────────────────────────────────────────────────────

function NotificationsTab() {
  const { data: prefs, isLoading } = useNotifPrefs();
  const updateMut = useUpdateNotifPrefs();
  const [form, setForm] = useState<NotifPrefs>({
    notify_on_complete: false,
    notify_on_failure: true,
    slack_webhook_url: null,
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (prefs) setForm(prefs);
  }, [prefs]);

  function save() {
    setSaved(false);
    updateMut.mutate(form, {
      onSuccess: () => setSaved(true),
    });
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-800" />
        ))}
      </div>
    );
  }

  return (
    <SectionBox
      title="Bildirim Tercihleri"
      description="Test kosumlari icin e-posta ve Slack bildirimlerini yapilandirin."
    >
      <div className="space-y-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={form.notify_on_complete}
            onChange={(e) => setForm((p) => ({ ...p, notify_on_complete: e.target.checked }))}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500"
          />
          <span className="text-sm text-white">Kosum tamamlandiginda bildir</span>
        </label>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={form.notify_on_failure}
            onChange={(e) => setForm((p) => ({ ...p, notify_on_failure: e.target.checked }))}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500"
          />
          <span className="text-sm text-white">Kosum basarisiz oldugunda bildir</span>
        </label>

        <div className="flex flex-col gap-1.5 pt-2">
          <label className="text-sm font-medium text-white">Slack Webhook URL</label>
          <input
            type="url"
            value={form.slack_webhook_url ?? ""}
            onChange={(e) =>
              setForm((p) => ({ ...p, slack_webhook_url: e.target.value || null }))
            }
            placeholder="https://hooks.slack.com/services/..."
            className="h-9 rounded border border-slate-700 bg-slate-800 px-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-slate-400">Bos birakilirsa Slack bildirimleri gonderilmez.</p>
        </div>

        {saved && (
          <p className="text-sm text-emerald-400">Bildirim tercihleri kaydedildi.</p>
        )}
        {updateMut.isError && (
          <p className="text-sm text-red-400">Kaydetme basarisiz. Lutfen tekrar deneyin.</p>
        )}

        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={save}
            disabled={updateMut.isPending}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {updateMut.isPending ? "Kaydediliyor..." : "Kaydet"}
          </button>
        </div>
      </div>
    </SectionBox>
  );
}

// ── Webhooks Tab ───────────────────────────────────────────────────────────────

const WEBHOOK_EVENTS = [
  "execution.completed",
  "execution.failed",
  "scenario.failed",
  "coverage.updated",
];

function WebhooksTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [newUrl, setNewUrl] = useState("");
  const [newEvents, setNewEvents] = useState<string[]>(["execution.failed"]);
  const [addError, setAddError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data: webhooks = [], isLoading } = useQuery<WebhookNotification[]>({
    queryKey: ["webhooks", projectId],
    queryFn: () =>
      apiFetch<WebhookNotification[]>(
        `/api/v1/test-management/projects/${projectId}/webhook-notifications`,
      ),
    enabled: !!projectId,
    staleTime: 60 * 1000,
  });

  const addMut = useMutation({
    mutationFn: () =>
      apiFetch<WebhookNotification>(
        `/api/v1/test-management/projects/${projectId}/webhook-notifications`,
        { method: "POST", json: { url: newUrl, events: newEvents } },
      ),
    onSuccess: () => {
      setNewUrl("");
      setNewEvents(["execution.failed"]);
      setAddError(null);
      queryClient.invalidateQueries({ queryKey: ["webhooks", projectId] });
    },
    onError: () => setAddError("Webhook eklenemedi. URL'yi kontrol edin."),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) =>
      apiFetch(
        `/api/v1/test-management/projects/${projectId}/webhook-notifications/${id}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks", projectId] });
    },
  });

  function toggleEvent(ev: string) {
    setNewEvents((prev) =>
      prev.includes(ev) ? prev.filter((e) => e !== ev) : [...prev, ev],
    );
  }

  return (
    <div className="space-y-6">
      <SectionBox
        title="Yeni Webhook Ekle"
        description="Belirtilen olaylar gerceklestiginde bu URL'ye POST istegi gonderilir."
      >
        <div className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-white">Webhook URL</label>
            <input
              type="url"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://your-server.com/webhook"
              className="h-9 rounded border border-slate-700 bg-slate-800 px-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-white">Olaylar</span>
            <div className="flex flex-wrap gap-3">
              {WEBHOOK_EVENTS.map((ev) => (
                <label key={ev} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newEvents.includes(ev)}
                    onChange={() => toggleEvent(ev)}
                    className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-300 font-mono">{ev}</span>
                </label>
              ))}
            </div>
          </div>
          {addError && <p className="text-sm text-red-400">{addError}</p>}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => addMut.mutate()}
              disabled={addMut.isPending || !newUrl}
              className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {addMut.isPending ? "Ekleniyor..." : "Webhook Ekle"}
            </button>
          </div>
        </div>
      </SectionBox>

      <SectionBox title="Mevcut Webhook'lar">
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-800" />
            ))}
          </div>
        ) : webhooks.length === 0 ? (
          <p className="text-sm text-slate-500 py-4 text-center">Henuz webhook tanimlanmadi.</p>
        ) : (
          <div className="space-y-3">
            {webhooks.map((wh) => (
              <div
                key={wh.id}
                className="flex items-start justify-between gap-4 rounded-lg border border-slate-800 px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${wh.is_active ? "bg-emerald-500" : "bg-slate-600"}`}
                    />
                    <p className="truncate text-sm font-medium text-white">{wh.url}</p>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {wh.events.map((ev) => (
                      <span
                        key={ev}
                        className="rounded-md bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-slate-400"
                      >
                        {ev}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setConfirmDeleteId(wh.id)}
                  className="shrink-0 rounded-lg border border-red-900/50 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-950/30 transition-colors"
                >
                  Sil
                </button>
              </div>
            ))}
          </div>
        )}
      </SectionBox>

      <ConfirmDialog
        open={!!confirmDeleteId}
        onOpenChange={(open) => { if (!open) setConfirmDeleteId(null); }}
        title="Webhook'u Sil"
        description="Bu webhook'u silmek istediginizden emin misiniz? Islem geri alinamaz."
        confirmLabel="Evet, Sil"
        variant="destructive"
        onConfirm={() => {
          if (confirmDeleteId) {
            deleteMut.mutate(confirmDeleteId);
            setConfirmDeleteId(null);
          }
        }}
        isLoading={deleteMut.isPending}
      />
    </div>
  );
}

// ── Feature Flags Tab ──────────────────────────────────────────────────────────

function FeatureFlagsTab() {
  const { data: flags = [], isLoading } = useQuery<FeatureFlag[]>({
    queryKey: ["feature-flags"],
    queryFn: () => apiFetch<FeatureFlag[]>("/api/v1/feature-flags"),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-800" />
        ))}
      </div>
    );
  }

  return (
    <SectionBox
      title="Ozellik Bayraklari"
      description="Platformun aktif ozelliklerini goruntuleyin. Duzenleme icin sistem yoneticisiyle iletisime gecin."
    >
      {flags.length === 0 ? (
        <p className="text-sm text-slate-500 py-4 text-center">Hicbir ozellik bayragi tanimlanmamis.</p>
      ) : (
        <div className="space-y-2">
          {flags.map((flag) => (
            <div
              key={flag.key}
              className="flex items-center justify-between rounded-lg border border-slate-800 px-4 py-3"
            >
              <div>
                <p className="font-mono text-sm font-medium text-white">{flag.key}</p>
                {flag.description && (
                  <p className="mt-0.5 text-xs text-slate-400">{flag.description}</p>
                )}
              </div>
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                  flag.enabled
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : "bg-slate-800 text-slate-500 border border-slate-700"
                }`}
              >
                {flag.enabled ? "Aktif" : "Pasif"}
              </span>
            </div>
          ))}
        </div>
      )}
    </SectionBox>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const projectId = useRouteParam("projectId");
  const [activeTab, setActiveTab] = useState<Tab>("general");

  return (
    <div className="max-w-3xl mx-auto py-10 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">Proje Ayarlari</h1>
        <p className="mt-1 text-sm text-slate-400">
          Proje yapilandirmasi, bildirimler, webhook'lar ve ozellik bayraklari.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-900 p-1">
        <TabButton active={activeTab === "general"} onClick={() => setActiveTab("general")}>
          Genel
        </TabButton>
        <TabButton active={activeTab === "notifications"} onClick={() => setActiveTab("notifications")}>
          Bildirimler
        </TabButton>
        <TabButton active={activeTab === "webhooks"} onClick={() => setActiveTab("webhooks")}>
          Webhook
        </TabButton>
        <TabButton active={activeTab === "feature-flags"} onClick={() => setActiveTab("feature-flags")}>
          Ozellik Bayraklari
        </TabButton>
      </div>

      {/* Tab content */}
      {activeTab === "general" && <GeneralTab projectId={projectId} />}
      {activeTab === "notifications" && <NotificationsTab />}
      {activeTab === "webhooks" && <WebhooksTab projectId={projectId} />}
      {activeTab === "feature-flags" && <FeatureFlagsTab />}
    </div>
  );
}
