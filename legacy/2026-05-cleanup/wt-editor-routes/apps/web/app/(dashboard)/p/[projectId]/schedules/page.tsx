"use client";

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch, ENGINE_BASE } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
  StatCard,
  MetricRow,
  ToolbarActions,
} from "@/components/nexus";

type Schedule = {
  id: string;
  name: string;
  cron_expression: string;
  is_active: boolean;
  scenario_ids: string[];
  last_run_at: string | null;
  next_run_at: string | null;
};

type Form = { name: string; cron_expression: string; scenario_ids: string };
const emptyForm: Form = { name: "", cron_expression: "", scenario_ids: "" };

const PRESETS = [
  { label: "Her gün 02:00", cron: "0 2 * * *" },
  { label: "Her Pazartesi", cron: "0 9 * * 1" },
  { label: "Her saat", cron: "0 * * * *" },
  { label: "Her 6 saatte", cron: "0 */6 * * *" },
];

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
}

function cronHuman(cron: string) {
  const map: Record<string, string> = {
    "0 2 * * *": "Her gün 02:00",
    "0 9 * * 1": "Her Pazartesi 09:00",
    "0 * * * *": "Her saat başı",
    "0 */6 * * *": "Her 6 saatte bir",
  };
  return map[cron] ?? cron;
}

function PlatformBadge({ platform }: { platform?: string | null }) {
  if (platform === "ios") return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 border border-blue-500/20 text-blue-400">
      🍎 iOS
    </span>
  );
  if (platform === "android") return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-500/10 border border-green-500/20 text-green-400">
      🤖 Android
    </span>
  );
  return null;
}

/* ── Schedule Card ─────────────────────────────────────────────────────────── */
function ScheduleCard({
  schedule,
  onToggle,
  onTrigger,
  onDelete,
  triggering,
}: {
  schedule: Schedule;
  onToggle: () => void;
  onTrigger: () => void;
  onDelete: () => void;
  triggering: boolean;
}) {
  const countdown = useCountdown(schedule.next_run_at);
  return (
    <div
      className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 hover:border-slate-600 transition-all"
      data-testid={`schedule-card-${schedule.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="text-sm font-semibold text-white truncate">{schedule.name}</h3>
            {schedule.platform && <PlatformBadge platform={schedule.platform} />}
            <button
              onClick={onToggle}
              className={`shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                schedule.is_active
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${schedule.is_active ? "bg-emerald-400" : "bg-slate-500"}`} />
              {schedule.is_active ? "Aktif" : "Pasif"}
            </button>
          </div>
          <p className="font-mono text-xs text-blue-400 mb-1">{schedule.cron_expression}</p>
          <p className="text-xs text-slate-400">{cronHuman(schedule.cron_expression)}</p>
          {schedule.device_name && (
            <p className="text-xs text-indigo-400 mt-0.5">📱 {schedule.device_name}</p>
          )}
        </div>
        <div className="flex gap-1 shrink-0">
          <button
            onClick={onTrigger}
            disabled={triggering}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-300 border border-emerald-500/30 rounded-lg hover:bg-emerald-500/10 transition-all disabled:opacity-50"
          >
            {triggering ? (
              <div className="w-3 h-3 border border-emerald-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              </svg>
            )}
            Çalıştır
          </button>
          <button
            onClick={onDelete}
            className="px-2 py-1.5 text-xs text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-slate-800 grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-slate-500 mb-0.5">Son çalışma</p>
          <p className="text-xs text-slate-300">{fmtDate(schedule.last_run_at)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-0.5">Sonraki çalışma</p>
          <p className="text-xs text-slate-300">{fmtDate(schedule.next_run_at)}</p>
          {schedule.is_active && schedule.next_run_at && (
            <p className="text-xs text-blue-400 mt-0.5 font-medium">{countdown}</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Visium Farm Mobile Scheduler Panel ───────────────────────────────────── */
function MobileSchedulePanel({
  projectId,
  schedules,
  loading,
  triggering,
  onToggle,
  onTrigger,
  onDelete,
  onCreate,
}: {
  projectId: string;
  schedules: Schedule[];
  loading: boolean;
  triggering: string | null;
  onToggle: (s: Schedule) => void;
  onTrigger: (id: string) => void;
  onDelete: (id: string) => void;
  onCreate: (body: object) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<MobileForm>(emptyMobileForm);
  const [saving, setSaving] = useState(false);

  const mobileSchedules = schedules.filter(s => s.platform != null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await onCreate({
        name: form.name,
        cron_expression: form.cron_expression,
        scenario_ids: form.scenario_ids.split(",").map(s => s.trim()).filter(Boolean),
        platform: form.platform,
        device_name: form.device_name,
      });
      setForm(emptyMobileForm);
      setOpen(false);
    } finally { setSaving(false); }
  }

  return (
    <SectionCard
      title="📱 Visium Farm Zamanlayıcıları"
      icon={
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      }
      right={
        <span className="text-xs text-slate-500">iOS · Android · cron tabanlı</span>
      }
    >
      {/* Mobile schedule cards */}
      {mobileSchedules.length === 0 && !open ? (
        <EmptyState
          icon="📱"
          title="Henüz mobil zamanlayıcı yok"
          description="Visium Farm cihazlarında periyodik koşum ekleyin"
          action={
            <button
              onClick={() => setOpen(true)}
              className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-colors"
            >
              Mobil Zamanlayıcı Ekle
            </button>
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {mobileSchedules.map(s => (
            <ScheduleCard
              key={s.id}
              schedule={s}
              onToggle={() => onToggle(s)}
              onTrigger={() => onTrigger(s.id)}
              onDelete={() => onDelete(s.id)}
              triggering={triggering === s.id}
            />
          ))}
        </div>
      )}

      {/* Create form */}
      <div className={`${mobileSchedules.length > 0 || open ? "border-t border-slate-800 pt-4 mt-4" : "mt-2"}`}>
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <svg className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          📱 Yeni Mobil Zamanlayıcı Ekle
        </button>

        {open && (
          <form onSubmit={handleSubmit} className="mt-3 space-y-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                placeholder="Zamanlayıcı adı"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                required
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
              />
              <input
                placeholder="Cron: 0 2 * * *"
                value={form.cron_expression}
                onChange={e => setForm({ ...form, cron_expression: e.target.value })}
                required
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
              />

              {/* Platform seçimi */}
              <div className="flex gap-2">
                {(["ios", "android"] as const).map(p => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setForm({
                      ...form,
                      platform: p,
                      device_name: MOBILE_DEVICES[p][0],
                    })}
                    className={`flex-1 py-2 text-xs font-medium rounded-lg border transition-all ${
                      form.platform === p
                        ? p === "ios"
                          ? "border-blue-500/40 bg-blue-500/10 text-blue-400"
                          : "border-green-500/40 bg-green-500/10 text-green-400"
                        : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white"
                    }`}
                  >
                    {p === "ios" ? "🍎 iOS" : "🤖 Android"}
                  </button>
                ))}
              </div>

              {/* Cihaz seçimi */}
              <select
                value={form.device_name}
                onChange={e => setForm({ ...form, device_name: e.target.value })}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/50"
              >
                {MOBILE_DEVICES[form.platform].map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>

              <input
                placeholder="Senaryo ID'leri (virgülle ayırın)"
                value={form.scenario_ids}
                onChange={e => setForm({ ...form, scenario_ids: e.target.value })}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 sm:col-span-2"
              />
            </div>

            {/* Cron presets */}
            <div className="flex flex-wrap gap-1.5">
              <span className="text-xs text-slate-500 self-center mr-1">Hızlı:</span>
              {PRESETS.map(p => (
                <button
                  key={p.cron}
                  type="button"
                  onClick={() => setForm({ ...form, cron_expression: p.cron })}
                  className={`rounded-lg border px-2 py-1 text-xs transition-all ${
                    form.cron_expression === p.cron
                      ? "border-indigo-500/40 bg-indigo-500/10 text-indigo-400"
                      : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-colors disabled:opacity-50"
              >
                {saving ? "Oluşturuluyor…" : "📱 Zamanlayıcı Oluştur"}
              </button>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                İptal
              </button>
            </div>
          </form>
        )}
      </div>
    </SectionCard>
  );
}

/* ── Engine Scheduler Panel ───────────────────────────────────────────────── */
function EngineSchedulerPanel({ projectId }: { projectId: string }) {
  const [schedules, setSchedules] = useState<EngineSchedule[]>([]);
  const [form, setForm] = useState({ name: "", cron_expression: "", feature_path: "", browser: "chromium" });
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const load = useCallback(() => {
    fetch(`${ENGINE_BASE}/api/schedules?project_id=${projectId}`)
      .then(r => r.json())
      .then(setSchedules)
      .catch(() => {});
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await fetch(`${ENGINE_BASE}/api/schedules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, project_id: projectId }),
      });
      setForm({ name: "", cron_expression: "", feature_path: "", browser: "chromium" });
      setOpen(false);
      load();
    } finally { setLoading(false); }
  }

  async function toggle(s: EngineSchedule) {
    await fetch(`${ENGINE_BASE}/api/schedules/${s.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: !s.is_active }),
    });
    load();
  }

  async function triggerNow(id: string) {
    setTriggering(id);
    await fetch(`${ENGINE_BASE}/api/schedules/${id}/trigger`, { method: "POST" }).catch(() => {});
    setTimeout(() => { setTriggering(null); load(); }, 1000);
  }

  async function del(id: string) {
    await fetch(`${ENGINE_BASE}/api/schedules/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <SectionCard
      title="Engine Zamanlayıcıları"
      icon={
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      }
      right={
        <span className="text-xs text-slate-500">APScheduler · JSON store · kalıcı</span>
      }
      noPad
    >
      {schedules.length === 0 ? (
        <div className="p-4">
          <EmptyState icon="⚡" title="Engine zamanlayıcısı yok" description="Feature dosyası bazında cron koşu ekleyin" />
        </div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">İsim</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Cron</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tarayıcı</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Son Koşu</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Koşu #</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
              <th className="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody>
            {schedules.map(s => (
              <tr key={s.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30 group">
                <td className="px-4 py-3 text-sm font-medium text-white">{s.name}</td>
                <td className="px-4 py-3 font-mono text-xs text-blue-400">{s.cron_expression}</td>
                <td className="px-4 py-3 text-xs text-slate-400">{s.browser}</td>
                <td className="px-4 py-3 text-xs text-slate-400">{fmtDate(s.last_run_at)}</td>
                <td className="px-4 py-3 text-xs text-slate-400">{s.run_count}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggle(s)}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border cursor-pointer transition-all ${
                      s.is_active
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                        : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${s.is_active ? "bg-emerald-400" : "bg-slate-500"}`} />
                    {s.is_active ? "Aktif" : "Pasif"}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => triggerNow(s.id)}
                      disabled={triggering === s.id}
                      className="text-xs px-2 py-1 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-50"
                    >
                      {triggering === s.id ? "⏳" : "▶"}
                    </button>
                    <button
                      onClick={() => del(s.id)}
                      className="text-xs px-2 py-1 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      ✕
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Engine create form */}
      <div className="border-t border-slate-800 p-4">
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <svg className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          Yeni Engine Zamanlayıcısı Ekle
        </button>
        {open && (
          <form onSubmit={create} className="mt-3 space-y-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <input placeholder="İsim" value={form.name} onChange={e => setForm({...form, name: e.target.value})} required
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50" />
              <input placeholder="Cron: 0 2 * * *" value={form.cron_expression} onChange={e => setForm({...form, cron_expression: e.target.value})} required
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500/50" />
              <input placeholder="features/login.feature" value={form.feature_path} onChange={e => setForm({...form, feature_path: e.target.value})}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50" />
              <select value={form.browser} onChange={e => setForm({...form, browser: e.target.value})}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50">
                {["chromium","firefox","webkit"].map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {PRESETS.map(p => (
                <button key={p.cron} type="button" onClick={() => setForm({...form, cron_expression: p.cron})}
                  className="rounded-lg border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:border-slate-500 hover:text-white transition-all">
                  {p.label}
                </button>
              ))}
            </div>
            <button type="submit" disabled={loading}
              className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50">
              {loading ? "Oluşturuluyor…" : "Oluştur"}
            </button>
          </form>
        )}
      </div>
    </SectionCard>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────────── */
export default function SchedulesPage() {
  const projectId = useRouteParam("projectId");
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [form, setForm] = useState<Form>(emptyForm);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(() => {
    apiFetch<Schedule[]>(`/api/v1/tspm/projects/${projectId}/schedules`)
      .then(setSchedules)
      .catch(() => {});
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/schedules`, {
        method: "POST",
        json: {
          name: form.name,
          cron_expression: form.cron_expression,
          scenario_ids: form.scenario_ids.split(",").map((s) => s.trim()).filter(Boolean),
        },
      });
      setForm(emptyForm);
      setShowForm(false);
      load();
    } finally {
      setLoading(false);
    }
  }

  async function toggleActive(s: Schedule) {
    await apiFetch(`/api/v1/tspm/projects/${projectId}/schedules/${s.id}`, {
      method: "PUT",
      json: { is_active: !s.is_active },
    });
    load();
  }

  async function triggerNow(id: string) {
    setTriggering(id);
    await apiFetch(`/api/v1/tspm/projects/${projectId}/schedules/${id}/trigger`, { method: "POST" }).catch(() => {});
    setTimeout(() => { setTriggering(null); load(); }, 1000);
  }

  async function handleDelete(id: string) {
    await apiFetch(`/api/v1/tspm/projects/${projectId}/schedules/${id}`, { method: "DELETE" });
    load();
  }

  const active = schedules.filter((s) => s.is_active).length;

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="schedules-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
        title="Zamanlayıcılar"
        description="Cron tabanlı test koşu zamanlamaları"
        right={
          <ToolbarActions>
            <button
              onClick={() => setShowForm(f => !f)}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
              data-testid="schedules-btn-new"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {showForm ? "İptal" : "Yeni Zamanlayıcı"}
            </button>
          </ToolbarActions>
        }
      />

      {/* Stats */}
      <MetricRow cols={4}>
        <StatCard label="Toplam" value={schedules.length} color="slate" />
        <StatCard label="Aktif" value={active} color={active > 0 ? "emerald" : "slate"} />
        <StatCard label="Visium Farm" value={mobileSchedules.length} color="violet" sub="Mobile" />
        <StatCard label="Pasif" value={schedules.length - active} color="slate" />
      </MetricRow>

      {showForm && (
        <SectionCard title="Yeni Zamanlayıcı">
          <form onSubmit={handleCreate} className="space-y-3" data-testid="schedules-form">
            <div className="grid gap-3 sm:grid-cols-2">
              <input placeholder="İsim" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required data-testid="schedules-input-name" className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50" />
              <input placeholder="Cron: 0 2 * * *" value={form.cron_expression} onChange={(e) => setForm({ ...form, cron_expression: e.target.value })} required data-testid="schedules-input-cron" className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500/50" />
              <input placeholder="Senaryo ID'leri (virgülle ayırın)" value={form.scenario_ids} onChange={(e) => setForm({ ...form, scenario_ids: e.target.value })} data-testid="schedules-input-scenarios" className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 sm:col-span-2" />
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="text-xs text-slate-500 self-center mr-1">Hızlı seç:</span>
              {PRESETS.map((p) => (
                <button key={p.cron} type="button" onClick={() => setForm({ ...form, cron_expression: p.cron })} className={`rounded-lg border px-2 py-1 text-xs transition-all ${form.cron_expression === p.cron ? "border-blue-500/40 bg-blue-500/10 text-blue-400" : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white"}`}>
                  {p.label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={loading} data-testid="schedules-btn-create" className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50">
                {loading ? "Oluşturuluyor…" : "Oluştur"}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">İptal</button>
            </div>
          </form>
        </SectionCard>
      )}

      <SectionCard title="Zamanlayıcılar">
        {schedules.length === 0 ? (
          <EmptyState icon="⏰" title="Henüz zamanlayıcı yok" description="Cron tabanlı test koşu zamanlamaları oluşturun" action={<button onClick={() => setShowForm(true)} className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors">Zamanlayıcı Ekle</button>} />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {schedules.map((s) => (
              <div key={s.id} className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 hover:border-slate-600 transition-all" data-testid={`schedule-card-${s.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-white truncate mb-1">{s.name}</h3>
                    <p className="font-mono text-xs text-blue-400 mb-0.5">{s.cron_expression}</p>
                    <p className="text-xs text-slate-400">{cronHuman(s.cron_expression)}</p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button onClick={() => toggleActive(s)} className={`px-2 py-0.5 rounded-full text-xs font-medium border ${s.is_active ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-slate-800 border-slate-700 text-slate-400"}`}>
                      {s.is_active ? "Aktif" : "Pasif"}
                    </button>
                    <button onClick={() => triggerNow(s.id)} disabled={triggering === s.id} className="px-2 py-1 text-xs text-emerald-400 border border-emerald-500/30 rounded-lg hover:bg-emerald-500/10 disabled:opacity-50">
                      {triggering === s.id ? "⏳" : "▶"}
                    </button>
                    <button onClick={() => handleDelete(s.id)} className="px-2 py-1 text-xs text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/10">✕</button>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-800 grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">Son çalışma</p>
                    <p className="text-xs text-slate-300">{fmtDate(s.last_run_at)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">Sonraki çalışma</p>
                    <p className="text-xs text-slate-300">{fmtDate(s.next_run_at)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
