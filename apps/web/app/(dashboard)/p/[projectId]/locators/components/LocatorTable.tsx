"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { SectionCard, StatCard, EmptyState } from "@/components/nexus";

// ── Shared style constants (duplicated from page.tsx to keep component standalone) ──

const STATUS_STYLES: Record<string, { color: string; dot: string; label: string }> = {
  healthy: { color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", dot: "bg-emerald-400", label: "Saglikli" },
  broken:  { color: "bg-red-500/10 border-red-500/20 text-red-400",            dot: "bg-red-400",     label: "Kırık" },
  warning: { color: "bg-amber-500/10 border-amber-500/20 text-amber-400",      dot: "bg-amber-400",   label: "Uyari" },
};

const TYPE_COLORS: Record<string, string> = {
  css:    "bg-blue-500/10 border-blue-500/20 text-blue-400",
  xpath:  "bg-amber-500/10 border-amber-500/20 text-amber-400",
  testid: "bg-violet-500/10 border-violet-500/20 text-violet-400",
  text:   "bg-slate-800 border-slate-700 text-slate-300",
};

const BTN_PRIMARY = "inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all";
const INPUT_CLS = "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

// ── Types ────────────────────────────────────────────────────────────

export type Locator = {
  id: string;
  name: string;
  selector: string;
  type: string;
  page: string;
  status: string;
};

// ── Sub-components ───────────────────────────────────────────────────

function Spinner({ className = "w-5 h-5" }: { className?: string }) {
  return <div className={`border-2 border-slate-700 border-t-blue-400 rounded-full animate-spin ${className}`} />;
}

// ── Props ────────────────────────────────────────────────────────────

export interface LocatorTableProps {
  locators: Locator[];
  loading: boolean;
  refresh: () => void;
  projectId: string;
}

// ── Component ────────────────────────────────────────────────────────

export function LocatorTable({ locators, loading, refresh, projectId }: LocatorTableProps) {
  const healthy = locators.filter((l) => l.status === "healthy").length;
  const broken  = locators.filter((l) => l.status === "broken").length;
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", selector: "", page: "", type: "css" });

  const filtered = search
    ? locators.filter(
        (l) =>
          l.name.toLowerCase().includes(search.toLowerCase()) ||
          l.selector.toLowerCase().includes(search.toLowerCase()) ||
          l.page.toLowerCase().includes(search.toLowerCase()),
      )
    : locators;

  async function createLocator(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name || !form.selector) return;
    setCreating(true);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/locators`, { method: "POST", json: form });
      setForm({ name: "", selector: "", page: "", type: "css" });
      setShowForm(false);
      refresh();
    } catch { /* ignore */ } finally {
      setCreating(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Toplam" value={locators.length} />
        <StatCard label="Saglikli" value={healthy} color="emerald" />
        <StatCard label="Kırık" value={broken} color="red" />
      </div>

      {/* Add button */}
      {!showForm && (
        <div className="flex justify-end">
          <button onClick={() => setShowForm(true)} className={BTN_PRIMARY}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Locator Ekle
          </button>
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <SectionCard
          title="Yeni Locator"
          icon={
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          }
        >
          <form onSubmit={createLocator} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                placeholder="Ad (orn. loginButton)"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                className={INPUT_CLS}
              />
              <input
                placeholder="Selector (orn. [data-testid='login'])"
                value={form.selector}
                onChange={(e) => setForm({ ...form, selector: e.target.value })}
                required
                className={`${INPUT_CLS} font-mono`}
              />
              <input
                placeholder="Sayfa (orn. Login)"
                value={form.page}
                onChange={(e) => setForm({ ...form, page: e.target.value })}
                className={INPUT_CLS}
              />
              <select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
              >
                <option value="css">CSS</option>
                <option value="xpath">XPath</option>
                <option value="testid">Test ID</option>
                <option value="text">Metin</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={creating || !form.name || !form.selector}
                className={BTN_PRIMARY}
              >
                {creating ? "Kaydediliyor..." : "Kaydet"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                Iptal
              </button>
            </div>
          </form>
        </SectionCard>
      )}

      {/* Search */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          placeholder="Locator ara..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900/40 pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <h3 className="text-sm font-semibold">Locator Listesi</h3>
          <span className="text-xs text-slate-500">{locators.length} locator</span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
            <Spinner /> Yükleniyor...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon="🎯"
              title={search ? "Sonuç yok" : "Henuz locator yok"}
              description={search ? "Arama kriterini değiştirin" : "Element konumlandiricilarini ekleyin"}
              action={
                !search ? (
                  <button onClick={() => setShowForm(true)} className={BTN_PRIMARY}>
                    Locator Ekle
                  </button>
                ) : undefined
              }
            />
          </div>
        ) : (
          <table className="w-full" data-testid="locators-table">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Ad</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Selector</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tip</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Sayfa</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((l) => {
                const st = STATUS_STYLES[l.status] ?? STATUS_STYLES.warning;
                const tc = TYPE_COLORS[l.type] ?? TYPE_COLORS.text;
                return (
                  <tr key={l.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-mono text-xs font-medium text-white">{l.name}</td>
                    <td
                      className="px-4 py-3 font-mono text-xs text-slate-400 max-w-xs truncate"
                      title={l.selector}
                    >
                      {l.selector}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium ${tc}`}>
                        {l.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">{l.page || "—"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${st.color}`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
                        {st.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
