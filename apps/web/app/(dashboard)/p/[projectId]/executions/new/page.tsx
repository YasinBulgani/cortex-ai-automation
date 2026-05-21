"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Scenario = { id: string; title: string; status: string };

export default function NewExecutionPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  // Advanced execution options
  const [dryRun, setDryRun] = useState(false);
  const [platform, setPlatform] = useState<string>("desktop");
  const [browsers, setBrowsers] = useState<Set<string>>(new Set(["chromium"]));
  const [networkPreset, setNetworkPreset] = useState<string>("");
  const [timezone, setTimezone] = useState<string>("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const load = useCallback(() => {
    apiFetch<Scenario[]>(`/api/v1/tspm/projects/${projectId}/scenarios`).then(setScenarios).catch(() => {});
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  function toggle(id: string) {
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (selected.size === 0) {
      setErr("En az bir senaryo seçin.");
      return;
    }
    setSaving(true);
    try {
      const body: Record<string, unknown> = {
        name: name.trim() || "Koşu",
        scenario_ids: Array.from(selected),
        dry_run: dryRun,
      };
      if (platform !== "desktop") body.platform = platform;
      if (browsers.size > 1) body.browsers = Array.from(browsers);
      if (networkPreset) body.network_preset = networkPreset;
      if (timezone) body.timezone_id = timezone;

      const created = await apiFetch<{ id: string }>(`/api/v1/tspm/projects/${projectId}/executions`, {
        method: "POST",
        json: body,
      });
      router.push(`/p/${projectId}/executions/${created.id}`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="new-execution-page">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight" data-testid="new-execution-heading">Yeni execution</h1>
        <p className="text-sm text-slate-400">Koşuda yer alacak senaryoları seçin</p>
      </div>
      <form onSubmit={submit} className="space-y-4" data-testid="new-execution-form">
        <div>
          <label htmlFor="ex-name" className="mb-1 block text-xs text-slate-400">
            Koşu adı
          </label>
          <Input id="ex-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Örn. Sprint 12 regresyon" data-testid="execution-input-name" />
        </div>
        <div className="rounded-lg border border-slate-800" data-testid="execution-scenario-list">
          <div className="border-b border-slate-800 px-3 py-2 text-xs font-medium text-slate-400">Senaryolar</div>
          <ul className="max-h-72 divide-y divide-border overflow-auto">
            {scenarios.map((s) => (
              <li key={s.id} className="flex items-center gap-3 px-3 py-2">
                <input
                  type="checkbox"
                  checked={selected.has(s.id)}
                  onChange={() => toggle(s.id)}
                  aria-label={s.title}
                  data-testid={`execution-check-scenario-${s.id}`}
                />
                <span className="text-sm">{s.title}</span>
                <span className="text-xs text-slate-400">{s.status}</span>
              </li>
            ))}
          </ul>
          {scenarios.length === 0 && <p className="p-4 text-sm text-slate-400" data-testid="execution-empty-scenarios">Önce senaryo oluşturun.</p>}
        </div>
        {/* Advanced options toggle */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-3" data-testid="execution-advanced-options">
          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            className="w-full text-left text-xs font-medium text-slate-300 hover:text-white"
            data-testid="execution-toggle-advanced"
          >
            {showAdvanced ? "▼" : "▶"} Gelişmiş seçenekler
          </button>

          {showAdvanced && (
            <div className="mt-3 space-y-3" data-testid="execution-advanced-panel">
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input
                  type="checkbox"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                  data-testid="execution-toggle-dryrun"
                  className="h-4 w-4 rounded border-slate-700 bg-slate-900"
                />
                <span>
                  <span className="font-medium">Dry-run</span>
                  <span className="ml-2 text-xs text-slate-500">
                    Senaryoları kanıtlamadan doğrula — gerçek engine çağrısı yok
                  </span>
                </span>
              </label>

              <div>
                <label className="mb-1 block text-xs text-slate-400">Platform</label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm"
                  data-testid="execution-platform-select"
                >
                  <option value="desktop">🖥️ Desktop</option>
                  <option value="ios">📱 iOS</option>
                  <option value="android">📱 Android</option>
                </select>
              </div>

              {platform === "desktop" && (
                <div data-testid="execution-browser-matrix">
                  <label className="mb-1 block text-xs text-slate-400">Browser matrix (cross-browser paralel)</label>
                  <div className="flex flex-wrap gap-2">
                    {["chromium", "firefox", "webkit"].map((b) => (
                      <label key={b} className="flex items-center gap-1.5 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs">
                        <input
                          type="checkbox"
                          checked={browsers.has(b)}
                          onChange={() => {
                            const next = new Set(browsers);
                            if (next.has(b)) next.delete(b);
                            else next.add(b);
                            if (next.size === 0) next.add("chromium");
                            setBrowsers(next);
                          }}
                          data-testid={`execution-browser-${b}`}
                        />
                        {b}
                      </label>
                    ))}
                  </div>
                  {browsers.size > 1 && (
                    <p className="mt-1 text-[10px] text-emerald-400">
                      ✓ {browsers.size} browser paralel olarak koşulacak
                    </p>
                  )}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="mb-1 block text-xs text-slate-400">Network preset</label>
                  <select
                    value={networkPreset}
                    onChange={(e) => setNetworkPreset(e.target.value)}
                    className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm"
                    data-testid="execution-network-preset"
                  >
                    <option value="">Sınırsız</option>
                    <option value="wifi">WiFi</option>
                    <option value="4g">4G</option>
                    <option value="3g">3G</option>
                    <option value="slow-3g">Yavaş 3G</option>
                    <option value="2g">2G</option>
                    <option value="offline">Çevrimdışı</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-slate-400">Timezone</label>
                  <select
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm"
                    data-testid="execution-timezone-select"
                  >
                    <option value="">Sistem varsayılan</option>
                    <option value="Europe/Istanbul">İstanbul</option>
                    <option value="Europe/London">Londra</option>
                    <option value="America/New_York">New York</option>
                    <option value="Asia/Tokyo">Tokyo</option>
                    <option value="UTC">UTC</option>
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>

        {err && <p className="text-sm text-red-600" data-testid="execution-alert-error">{err}</p>}
        <div className="flex gap-2">
          <Button type="submit" disabled={saving} data-testid="execution-btn-start">
            {saving ? "…" : dryRun ? "Dry-run başlat" : "Koşuyu oluştur"}
          </Button>
          <Link href={`/p/${projectId}/executions`}>
            <Button type="button" variant="secondary">
              İptal
            </Button>
          </Link>
        </div>
      </form>
    </div>
  );
}
