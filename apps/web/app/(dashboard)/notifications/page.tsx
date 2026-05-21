"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useWebSocket, type WSMessage } from "@/lib/useWebSocket";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus";

// ── Types ─────────────────────────────────────────────────────────────────────

type NotifKind = "run_failed" | "run_complete" | "heal_applied" | "schedule" | "system" | string;

interface Notification {
  id: string;
  type: NotifKind;
  title: string;
  body: string;
  timestamp: string;
  read: boolean;
  severity: "error" | "success" | "info" | "warning";
}

interface NotifPrefs {
  notify_on_complete: boolean;
  notify_on_failure: boolean;
  slack_webhook_url: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const READ_KEY = "neurex_notif_read";

function loadReadIds(): Set<string> {
  try {
    const raw = localStorage.getItem(READ_KEY);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

function saveReadId(id: string) {
  try {
    const s = loadReadIds();
    s.add(id);
    localStorage.setItem(READ_KEY, JSON.stringify([...s].slice(-500)));
  } catch { /* ignore */ }
}

function saveAllReadIds(ids: string[]) {
  try {
    const s = loadReadIds();
    ids.forEach(id => s.add(id));
    localStorage.setItem(READ_KEY, JSON.stringify([...s].slice(-500)));
  } catch { /* ignore */ }
}

function wsToNotif(msg: WSMessage, readIds: Set<string>): Notification {
  const id = `ws-${msg.timestamp ?? Date.now()}-${msg.type}`;
  const kind = msg.type as NotifKind;
  const p = msg.payload as Record<string, string>;

  let title = kind.replace(/[._]/g, " ");
  let body = "";
  let severity: Notification["severity"] = "info";

  if (kind.includes("fail") || kind.includes("error")) {
    severity = "error";
    title = p.title ?? "Koşu başarısız";
    body = p.message ?? p.scenario_title ?? "";
  } else if (kind.includes("complete") || kind.includes("success")) {
    severity = "success";
    title = p.title ?? "Koşu tamamlandı";
    body = p.message ?? p.scenario_title ?? "";
  } else if (kind.includes("heal")) {
    severity = "info";
    title = "Self-Heal uygulandı";
    body = p.message ?? `${p.healed_count ?? "?"} test düzeltildi`;
  } else if (kind.includes("schedule")) {
    severity = "info";
    title = "Zamanlı koşu tetiklendi";
    body = p.schedule_name ?? "";
  }

  return {
    id,
    type: kind,
    title,
    body,
    timestamp: msg.timestamp ?? new Date().toISOString(),
    read: readIds.has(id),
    severity,
  };
}

function severityDot(sev: Notification["severity"]) {
  const cls = {
    error: "bg-red-400",
    success: "bg-emerald-400",
    warning: "bg-amber-400",
    info: "bg-blue-400",
  }[sev];
  return <span className={`h-2 w-2 flex-shrink-0 rounded-full ${cls}`} />;
}

function fmt(ts: string) {
  const d = new Date(ts);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "Az önce";
  if (diff < 3600) return `${Math.floor(diff / 60)}d önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}s önce`;
  return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
}

const FILTER_LABELS: Record<string, string> = {
  all: "Tümü",
  unread: "Okunmamış",
  error: "Hatalar",
  success: "Başarılar",
  info: "Bilgi",
};

// ── Notification Row ──────────────────────────────────────────────────────────

function NotifRow({ n, onRead }: { n: Notification; onRead: (id: string) => void }) {
  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 border-b border-slate-800 last:border-0 transition-colors cursor-pointer hover:bg-slate-800/40 ${n.read ? "opacity-60" : ""}`}
      onClick={() => onRead(n.id)}
    >
      <div className="mt-1 flex-shrink-0">{severityDot(n.severity)}</div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className={`text-sm font-medium truncate ${n.read ? "text-slate-400" : "text-white"}`}>{n.title}</p>
          <span className="flex-shrink-0 text-[10px] text-slate-500">{fmt(n.timestamp)}</span>
        </div>
        {n.body && <p className="text-xs text-slate-500 truncate mt-0.5">{n.body}</p>}
        <span className="inline-block mt-1 rounded px-1.5 py-0.5 text-[9px] font-mono border border-slate-700 text-slate-500">
          {n.type}
        </span>
      </div>
      {!n.read && (
        <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-500" />
      )}
    </div>
  );
}

// ── Prefs Panel ───────────────────────────────────────────────────────────────

function PrefsPanel() {
  const [prefs, setPrefs] = useState<NotifPrefs | null>(null);
  const [slack, setSlack] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch<NotifPrefs>("/api/v1/notifications/prefs")
      .then(p => { setPrefs(p); setSlack(p.slack_webhook_url ?? ""); })
      .catch(() => {});
  }, []);

  async function handleSave() {
    if (!prefs) return;
    setSaving(true);
    try {
      const updated = await apiFetch<NotifPrefs>("/api/v1/notifications/prefs", {
        method: "PUT",
        json: { ...prefs, slack_webhook_url: slack || null },
      });
      setPrefs(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { /* ignore */ } finally {
      setSaving(false);
    }
  }

  if (!prefs) return (
    <div className="py-6 text-center text-xs text-slate-500">Tercihler yükleniyor...</div>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-800/50 px-4 py-3">
        <div>
          <p className="text-sm font-medium text-white">Koşu tamamlandı</p>
          <p className="text-xs text-slate-400">Her başarılı koşu sonrası bildir</p>
        </div>
        <button
          type="button"
          onClick={() => setPrefs(p => p ? { ...p, notify_on_complete: !p.notify_on_complete } : p)}
          className={`relative h-6 w-11 rounded-full transition-colors ${prefs.notify_on_complete ? "bg-blue-600" : "bg-slate-700"}`}
        >
          <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${prefs.notify_on_complete ? "translate-x-5" : "translate-x-0.5"}`} />
        </button>
      </div>

      <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-800/50 px-4 py-3">
        <div>
          <p className="text-sm font-medium text-white">Koşu başarısız</p>
          <p className="text-xs text-slate-400">Hata durumunda hemen bildir</p>
        </div>
        <button
          type="button"
          onClick={() => setPrefs(p => p ? { ...p, notify_on_failure: !p.notify_on_failure } : p)}
          className={`relative h-6 w-11 rounded-full transition-colors ${prefs.notify_on_failure ? "bg-blue-600" : "bg-slate-700"}`}
        >
          <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${prefs.notify_on_failure ? "translate-x-5" : "translate-x-0.5"}`} />
        </button>
      </div>

      <div className="rounded-xl border border-slate-700 bg-slate-800/50 px-4 py-3">
        <p className="text-sm font-medium text-white mb-2">Slack Webhook</p>
        <input
          type="url"
          placeholder="https://hooks.slack.com/services/..."
          value={slack}
          onChange={e => setSlack(e.target.value)}
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors"
        />
      </div>

      <button
        type="button"
        onClick={handleSave}
        disabled={saving}
        className="w-full rounded-xl bg-blue-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
      >
        {saved ? "✓ Kaydedildi" : saving ? "Kaydediliyor..." : "Tercihleri Kaydet"}
      </button>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [showPrefs, setShowPrefs] = useState(false);
  const readIdsRef = useRef(new Set<string>());

  useEffect(() => {
    readIdsRef.current = loadReadIds();
  }, []);

  const handleWsMessage = useCallback((msg: WSMessage) => {
    const n = wsToNotif(msg, readIdsRef.current);
    setNotifications(prev => {
      if (prev.some(x => x.id === n.id)) return prev;
      return [n, ...prev].slice(0, 100);
    });
  }, []);

  const { messages, connected } = useWebSocket(handleWsMessage);

  // Sync existing WS messages into notifications on mount
  useEffect(() => {
    if (messages.length === 0) return;
    const readIds = readIdsRef.current;
    setNotifications(prev => {
      const existingIds = new Set(prev.map(n => n.id));
      const newOnes = messages
        .map(m => wsToNotif(m, readIds))
        .filter(n => !existingIds.has(n.id));
      return [...newOnes, ...prev].slice(0, 100);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function markRead(id: string) {
    saveReadId(id);
    readIdsRef.current.add(id);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  }

  function markAllRead() {
    const ids = notifications.map(n => n.id);
    saveAllReadIds(ids);
    ids.forEach(id => readIdsRef.current.add(id));
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }

  const filtered = notifications.filter(n => {
    if (filter === "all") return true;
    if (filter === "unread") return !n.read;
    return n.severity === filter;
  });

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <PageHeader
        title="Bildirimler"
        description={connected ? `Canlı bağlantı aktif · ${unreadCount} okunmamış` : `Bağlantı yok · ${unreadCount} okunmamış`}
        right={
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={markAllRead}
                className="rounded-xl border border-slate-700 px-4 py-1.5 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800"
              >
                Tümünü Okundu Say
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowPrefs(p => !p)}
              className={`rounded-xl border px-4 py-1.5 text-sm font-medium transition-colors ${showPrefs ? "border-blue-500/40 bg-blue-500/10 text-blue-300" : "border-slate-700 text-slate-200 hover:bg-slate-800"}`}
            >
              Tercihler
            </button>
          </div>
        }
      />

      <div className="mx-auto max-w-5xl px-6 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main inbox */}
          <div className="lg:col-span-2 space-y-4">
            {/* Connection status */}
            <div className={`flex items-center gap-2 rounded-xl border px-4 py-2.5 text-xs font-medium ${connected ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-300" : "border-slate-700 bg-slate-800/40 text-slate-400"}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
              {connected ? "WebSocket bağlı — gerçek zamanlı bildirim aktif" : "Bağlantı yok — yeniden bağlanmaya çalışıyor"}
            </div>

            {/* Filter tabs */}
            <div className="flex gap-1 rounded-xl bg-slate-800/50 border border-slate-700 p-1">
              {Object.entries(FILTER_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilter(key)}
                  className={`flex-1 rounded-lg py-1.5 text-xs font-medium transition-colors ${filter === key ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"}`}
                >
                  {label}
                  {key === "unread" && unreadCount > 0 && (
                    <span className="ml-1.5 rounded-full bg-blue-600 px-1.5 py-0.5 text-[9px] font-bold text-white">{unreadCount}</span>
                  )}
                </button>
              ))}
            </div>

            {/* Notification list */}
            <SectionCard title="Gelen Kutusu" className="p-0 overflow-hidden">
              {filtered.length === 0 ? (
                <EmptyState
                  title="Bildirim yok"
                  description={filter === "all" ? "Koşu tamamlandığında veya hata oluştuğunda burada görürsünüz." : "Bu filtreye uygun bildirim bulunamadı."}
                />
              ) : (
                filtered.map(n => (
                  <NotifRow key={n.id} n={n} onRead={markRead} />
                ))
              )}
            </SectionCard>
          </div>

          {/* Right sidebar */}
          <div className="space-y-4">
            {/* Stats */}
            <SectionCard title="Özet">
              <div className="space-y-2">
                {[
                  { label: "Toplam", value: notifications.length, cls: "text-white" },
                  { label: "Okunmamış", value: unreadCount, cls: "text-blue-400" },
                  { label: "Hata", value: notifications.filter(n => n.severity === "error").length, cls: "text-red-400" },
                  { label: "Başarı", value: notifications.filter(n => n.severity === "success").length, cls: "text-emerald-400" },
                ].map(({ label, value, cls }) => (
                  <div key={label} className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">{label}</span>
                    <span className={`font-semibold ${cls}`}>{value}</span>
                  </div>
                ))}
              </div>
            </SectionCard>

            {/* Channel info */}
            <SectionCard title="Kanallar">
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-slate-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                  In-app (aktif)
                </div>
                <div className="flex items-center gap-2 text-slate-500">
                  <span className="h-1.5 w-1.5 rounded-full bg-slate-600 flex-shrink-0" />
                  E-posta (tercihler)
                </div>
                <div className="flex items-center gap-2 text-slate-500">
                  <span className="h-1.5 w-1.5 rounded-full bg-slate-600 flex-shrink-0" />
                  Slack webhook
                </div>
              </div>
            </SectionCard>

            {/* Prefs panel */}
            {showPrefs && (
              <SectionCard title="Bildirim Tercihleri">
                <PrefsPanel />
              </SectionCard>
            )}

            {/* Quick links */}
            <SectionCard title="Hızlı Bağlantılar">
              <div className="space-y-1">
                {[
                  { href: "/admin/audit", label: "Audit Logu" },
                  { href: "/system/services", label: "Servis Durumu" },
                  { href: "/", label: "Aktivite Monitörü" },
                ].map(({ href, label }) => (
                  <Link
                    key={href}
                    href={href}
                    className="block rounded-lg px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
                  >
                    {label} →
                  </Link>
                ))}
              </div>
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}
