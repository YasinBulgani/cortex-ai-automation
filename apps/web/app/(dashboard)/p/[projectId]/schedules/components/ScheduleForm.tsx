"use client";

// ── Types ─────────────────────────────────────────────────────────────────────

export type ScheduleFormData = {
  name: string;
  cron_expression: string;
  scenario_ids: string;
};

export const EMPTY_SCHEDULE_FORM: ScheduleFormData = {
  name: "",
  cron_expression: "",
  scenario_ids: "",
};

const PRESETS = [
  { label: "Her gün 02:00", cron: "0 2 * * *" },
  { label: "Her Pazartesi", cron: "0 9 * * 1" },
  { label: "Her saat", cron: "0 * * * *" },
  { label: "Her 6 saatte", cron: "0 */6 * * *" },
];

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ScheduleFormProps {
  form: ScheduleFormData;
  onChange: (form: ScheduleFormData) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  loading: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ScheduleForm({
  form,
  onChange,
  onSubmit,
  onCancel,
  loading,
}: ScheduleFormProps) {
  return (
    <form
      onSubmit={onSubmit}
      className="space-y-3"
      data-testid="schedules-form"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          placeholder="İsim"
          value={form.name}
          onChange={(e) => onChange({ ...form, name: e.target.value })}
          required
          data-testid="schedules-input-name"
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
        />
        <input
          placeholder="Cron: 0 2 * * *"
          value={form.cron_expression}
          onChange={(e) =>
            onChange({ ...form, cron_expression: e.target.value })
          }
          required
          data-testid="schedules-input-cron"
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
        />
        <input
          placeholder="Senaryo ID'leri (virgülle ayırın)"
          value={form.scenario_ids}
          onChange={(e) => onChange({ ...form, scenario_ids: e.target.value })}
          data-testid="schedules-input-scenarios"
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 sm:col-span-2"
        />
      </div>

      {/* Cron presets */}
      <div className="flex flex-wrap gap-1.5">
        <span className="text-xs text-slate-500 self-center mr-1">
          Hızlı seç:
        </span>
        {PRESETS.map((p) => (
          <button
            key={p.cron}
            type="button"
            onClick={() => onChange({ ...form, cron_expression: p.cron })}
            className={`rounded-lg border px-2 py-1 text-xs transition-all ${
              form.cron_expression === p.cron
                ? "border-blue-500/40 bg-blue-500/10 text-blue-400"
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
          disabled={loading}
          data-testid="schedules-btn-create"
          className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
        >
          {loading ? "Oluşturuluyor…" : "Oluştur"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
        >
          İptal
        </button>
      </div>
    </form>
  );
}
