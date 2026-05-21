"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";

// ── Bildirim Tercihleri Tipi ─────────────────────────────────────────────────
type NotifPrefs = {
  notify_on_complete: boolean;
  notify_on_failure: boolean;
  slack_webhook_url: string | null;
};

// ── Bildirim Tercihleri Paneli ───────────────────────────────────────────────
function NotificationPrefsPanel() {
  const [prefs, setPrefs] = useState<NotifPrefs>({
    notify_on_complete: true,
    notify_on_failure: true,
    slack_webhook_url: null,
  });
  const [slackInput, setSlackInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    apiFetch<NotifPrefs>("/api/v1/notifications/prefs")
      .then((p) => {
        setPrefs(p);
        setSlackInput(p.slack_webhook_url ?? "");
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  async function save() {
    setSaving(true); setMsg(null);
    try {
      await apiFetch("/api/v1/notifications/prefs", {
        method: "PUT",
        json: {
          notify_on_complete: prefs.notify_on_complete,
          notify_on_failure: prefs.notify_on_failure,
          slack_webhook_url: slackInput.trim() || null,
        },
      });
      setMsg({ ok: true, text: "Bildirim tercihleri kaydedildi." });
    } catch {
      setMsg({ ok: false, text: "Kaydedilemedi. Lütfen tekrar deneyin." });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="mt-6 animate-pulse h-32 rounded-2xl bg-slate-800/40 border border-slate-800" />
    );
  }

  return (
    <div className="mt-6 rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-5">
      <h3 className="text-base font-semibold text-white">Bildirim Tercihleri</h3>

      {/* Toggle'lar */}
      <div className="space-y-3">
        {[
          { key: "notify_on_complete" as const, label: "Koşum tamamlandığında e-posta gönder",   icon: "✅" },
          { key: "notify_on_failure"  as const, label: "Koşum başarısız olduğunda e-posta gönder", icon: "❌" },
        ].map(({ key, label, icon }) => (
          <label key={key} className="flex items-center justify-between cursor-pointer group">
            <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
              {icon} {label}
            </span>
            <button
              role="switch"
              aria-checked={prefs[key]}
              onClick={() => setPrefs(p => ({ ...p, [key]: !p[key] }))}
              className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors
                ${prefs[key] ? "bg-indigo-500" : "bg-slate-700"}`}
            >
              <span
                className={`inline-block h-4 w-4 mt-0.5 rounded-full bg-white shadow transition-transform
                  ${prefs[key] ? "translate-x-4.5" : "translate-x-0.5"}`}
              />
            </button>
          </label>
        ))}
      </div>

      {/* Slack Webhook */}
      <div>
        <label className="text-xs text-slate-400 block mb-1.5">
          Slack Incoming Webhook URL
          <span className="ml-1 text-slate-600">(isteğe bağlı)</span>
        </label>
        <input
          type="url"
          className="w-full rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          placeholder="https://hooks.slack.com/services/T.../B.../..."
          value={slackInput}
          onChange={e => setSlackInput(e.target.value)}
        />
        <p className="text-[11px] text-slate-600 mt-1">
          Ayarlandığında her koşum sonuçu Slack kanalınıza iletilir.
        </p>
      </div>

      {msg && (
        <p className={`text-sm ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>
      )}

      <button
        onClick={save}
        disabled={saving}
        className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition-colors flex items-center gap-2"
      >
        {saving && <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
        {saving ? "Kaydediliyor…" : "Kaydet"}
      </button>
    </div>
  );
}

type Profile = {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  department: string | null;
  roles: string[];
  created_at: string | null;
};

const inputCls = "w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [dept, setDept] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [pwOpen, setPwOpen] = useState(false);
  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [pwMsg, setPwMsg] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    apiFetch<Profile>("/api/v1/auth/profile").then((p) => {
      setProfile(p);
      setName(p.full_name || "");
      setPhone(p.phone || "");
      setDept(p.department || "");
    });
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      const updated = await apiFetch<Profile>("/api/v1/auth/profile", {
        method: "PUT",
        json: { full_name: name, phone, department: dept },
      });
      setProfile(updated);
      setMsg({ text: "Profil güncellendi", ok: true });
    } catch {
      setMsg({ text: "Güncelleme başarısız", ok: false });
    } finally {
      setSaving(false);
    }
  }

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    setPwMsg(null);
    try {
      await apiFetch("/api/v1/auth/password", {
        method: "PUT",
        json: { current_password: curPw, new_password: newPw },
      });
      setPwMsg({ text: "Şifre değiştirildi", ok: true });
      setCurPw("");
      setNewPw("");
      setPwOpen(false);
    } catch {
      setPwMsg({ text: "Şifre değiştirilemedi", ok: false });
    }
  }

  if (!profile) {
    return (
      <div className="mx-auto max-w-3xl p-6 space-y-6">
        <div className="flex items-center gap-4">
          <div className="h-16 w-16 animate-pulse rounded-full bg-slate-800/60" />
          <div className="flex-1 space-y-2">
            <div className="h-5 w-48 animate-pulse rounded bg-slate-800/60" />
            <div className="h-4 w-64 animate-pulse rounded bg-slate-800/60" />
          </div>
        </div>
        <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/40 p-6">
          <div className="h-4 w-32 animate-pulse rounded bg-slate-800/60" />
          <div className="h-10 w-full animate-pulse rounded bg-slate-800/60" />
          <div className="h-4 w-40 animate-pulse rounded bg-slate-800/60" />
          <div className="h-10 w-full animate-pulse rounded bg-slate-800/60" />
        </div>
      </div>
    );
  }

  const initials = (name || profile.email).split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="profile-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        }
        title="Profil"
        description="Hesap bilgilerinizi görüntüleyin ve düzenleyin."
        data-testid="profile-heading"
      />

      <div className="mx-auto w-full max-w-2xl rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <div className="flex items-center gap-4 border-b border-slate-800 pb-6 mb-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-600 text-xl font-bold text-white">
            {initials}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">{name || profile.email}</h2>
            <p className="text-sm text-slate-400">{profile.roles.join(", ") || "Kullanıcı"}</p>
          </div>
        </div>

        <form onSubmit={handleSave} className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Ad Soyad</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} data-testid="profile-input-name" />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">E-posta</label>
            <input value={profile.email} disabled className={inputCls} data-testid="profile-input-email" />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Telefon</label>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} className={inputCls} data-testid="profile-input-phone" />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Departman</label>
            <input value={dept} onChange={(e) => setDept(e.target.value)} className={inputCls} data-testid="profile-input-department" />
          </div>

          <div className="sm:col-span-2 flex flex-wrap gap-3 border-t border-slate-800 pt-5 mt-1">
            <button
              type="submit"
              disabled={saving}
              data-testid="profile-btn-save"
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
            >
              {saving ? "Kaydediliyor…" : "Kaydet"}
            </button>
            <button
              type="button"
              onClick={() => setPwOpen(!pwOpen)}
              data-testid="profile-btn-password"
              className="px-4 py-2 text-sm font-medium text-slate-300 border border-slate-700 hover:border-slate-500 hover:text-white rounded-xl transition-colors"
            >
              Şifre Değiştir
            </button>
          </div>
        </form>

        {msg && (
          <p className={`mt-3 text-sm ${msg.ok ? "text-emerald-400" : "text-red-400"}`} data-testid="profile-alert-msg">
            {msg.text}
          </p>
        )}
      </div>

      {pwOpen && (
        <div className="mx-auto w-full max-w-2xl rounded-xl border border-slate-800 bg-slate-900/40 p-6">
          <h3 className="text-sm font-semibold text-white mb-4">Şifre Değiştir</h3>
          <form onSubmit={handlePasswordChange} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-slate-300">Mevcut Şifre</label>
              <input type="password" value={curPw} onChange={(e) => setCurPw(e.target.value)} required className={inputCls} data-testid="profile-input-current-pw" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-slate-300">Yeni Şifre</label>
              <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={6} className={inputCls} data-testid="profile-input-new-pw" />
            </div>
            <div className="flex gap-3">
              <button type="submit" data-testid="profile-btn-change-pw" className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors">
                Değiştir
              </button>
              <button type="button" onClick={() => setPwOpen(false)} className="px-4 py-2 text-sm text-slate-400 border border-slate-700 hover:border-slate-500 hover:text-white rounded-xl transition-colors">
                İptal
              </button>
            </div>
          </form>
          {pwMsg && (
            <p className={`mt-2 text-sm ${pwMsg.ok ? "text-emerald-400" : "text-red-400"}`}>
              {pwMsg.text}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
