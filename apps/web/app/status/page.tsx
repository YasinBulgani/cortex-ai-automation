"use client";

import { useEffect, useState } from "react";

type ServiceStatus = {
  name: string;
  status: "operational" | "degraded" | "outage" | "maintenance";
  latency_ms?: number;
  last_checked: string;
  uptime_30d?: number;
};

type Incident = {
  id: string;
  title: string;
  status: "investigating" | "identified" | "monitoring" | "resolved";
  severity: "minor" | "major" | "critical";
  started_at: string;
  resolved_at?: string;
  updates: { timestamp: string; message: string }[];
};

type StatusResponse = {
  overall: "operational" | "degraded" | "outage";
  services: ServiceStatus[];
  active_incidents: Incident[];
  recent_incidents: Incident[];
  uptime_90d: number;
};

const STATUS_LABELS: Record<ServiceStatus["status"], string> = {
  operational: "Çalışıyor",
  degraded: "Performans düşük",
  outage: "Kesinti",
  maintenance: "Bakım",
};

const STATUS_COLORS: Record<ServiceStatus["status"], string> = {
  operational: "bg-emerald-500",
  degraded: "bg-amber-500",
  outage: "bg-red-500",
  maintenance: "bg-sky-500",
};

const SEVERITY_COLORS: Record<Incident["severity"], string> = {
  minor: "border-amber-400 text-amber-400",
  major: "border-orange-400 text-orange-400",
  critical: "border-red-400 text-red-400",
};

export default function StatusPage() {
  const [data, setData] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("/api/v1/status", { credentials: "include" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as StatusResponse;
        setData(body);
        setError(null);
      } catch (e: any) {
        setError(e?.message ?? "Bilinmeyen hata");
      } finally {
        setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      className="min-h-screen bg-slate-950 text-slate-100 px-6 py-12"
      data-testid="status-page"
    >
      <div className="mx-auto max-w-4xl space-y-8">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Neurex QA Status</h1>
          <p className="text-sm text-slate-400">
            Servislerin gerçek zamanlı durumu — 30 saniyede bir güncellenir.
          </p>
        </header>

        {loading && (
          <div
            className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center text-slate-400"
            data-testid="status-loading"
          >
            Yükleniyor…
          </div>
        )}

        {error && (
          <div
            className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300"
            data-testid="status-error"
          >
            Durum alınamadı: {error}
          </div>
        )}

        {data && (
          <>
            <section
              className={`rounded-xl border p-6 ${
                data.overall === "operational"
                  ? "border-emerald-500/30 bg-emerald-500/10"
                  : data.overall === "degraded"
                    ? "border-amber-500/30 bg-amber-500/10"
                    : "border-red-500/30 bg-red-500/10"
              }`}
              data-testid="status-overall"
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold">
                    {data.overall === "operational"
                      ? "Tüm sistemler çalışıyor"
                      : data.overall === "degraded"
                        ? "Bazı servisler performans düşüklüğü yaşıyor"
                        : "Kritik kesinti var"}
                  </h2>
                  <p className="mt-1 text-sm text-slate-300">
                    90 günlük uptime:{" "}
                    <span className="font-medium">{data.uptime_90d.toFixed(3)}%</span>
                  </p>
                </div>
                <div className={`h-3 w-3 rounded-full ${STATUS_COLORS[data.overall === "operational" ? "operational" : data.overall === "degraded" ? "degraded" : "outage"]}`} />
              </div>
            </section>

            {data.active_incidents.length > 0 && (
              <section className="space-y-3" data-testid="status-active-incidents">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Aktif olaylar
                </h3>
                {data.active_incidents.map((inc) => (
                  <div
                    key={inc.id}
                    className={`rounded-lg border-l-4 bg-slate-900/40 p-4 ${SEVERITY_COLORS[inc.severity]}`}
                    data-testid={`incident-${inc.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{inc.title}</span>
                      <span className="text-xs uppercase tracking-wider opacity-70">
                        {inc.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      Başlangıç: {new Date(inc.started_at).toLocaleString("tr-TR")}
                    </p>
                  </div>
                ))}
              </section>
            )}

            <section className="space-y-2" data-testid="status-services">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                Servisler
              </h3>
              <div className="rounded-xl border border-slate-800 divide-y divide-slate-800">
                {data.services.map((svc) => (
                  <div
                    key={svc.name}
                    className="flex items-center justify-between p-4"
                    data-testid={`service-${svc.name}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-2.5 w-2.5 rounded-full ${STATUS_COLORS[svc.status]}`} />
                      <span className="font-medium">{svc.name}</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-slate-400">
                      {svc.latency_ms !== undefined && (
                        <span>{svc.latency_ms} ms</span>
                      )}
                      {svc.uptime_30d !== undefined && (
                        <span>{svc.uptime_30d.toFixed(2)}%</span>
                      )}
                      <span className="text-xs">{STATUS_LABELS[svc.status]}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {data.recent_incidents.length > 0 && (
              <section className="space-y-3" data-testid="status-recent-incidents">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Son 14 gün
                </h3>
                <div className="space-y-2">
                  {data.recent_incidents.map((inc) => (
                    <details
                      key={inc.id}
                      className="rounded-lg border border-slate-800 bg-slate-900/30 p-4"
                    >
                      <summary className="flex cursor-pointer items-center justify-between">
                        <span className="font-medium">{inc.title}</span>
                        <span className="text-xs text-slate-500">
                          {new Date(inc.started_at).toLocaleDateString("tr-TR")}
                        </span>
                      </summary>
                      <div className="mt-3 space-y-2 text-sm">
                        {inc.updates.map((upd, idx) => (
                          <div key={idx} className="border-l-2 border-slate-700 pl-3">
                            <p className="text-xs text-slate-500">
                              {new Date(upd.timestamp).toLocaleString("tr-TR")}
                            </p>
                            <p className="text-slate-300">{upd.message}</p>
                          </div>
                        ))}
                      </div>
                    </details>
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        <footer className="border-t border-slate-800 pt-6 text-center text-xs text-slate-500">
          Neurex QA · Otomatik durum sayfası · API:{" "}
          <code className="rounded bg-slate-900 px-1.5 py-0.5">/api/v1/status</code>
        </footer>
      </div>
    </div>
  );
}
