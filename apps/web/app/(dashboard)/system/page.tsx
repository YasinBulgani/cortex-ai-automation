"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { StatCard, MetricRow } from "@/components/nexus";
import { useCoreRuntime } from "@/lib/core-runtime";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AiHealthProvider {
  name: string;
  ok: boolean;
  latency_ms?: number;
}

interface AiHealth {
  status: string;
  providers: Record<string, boolean>;
  latency_ms?: Record<string, number>;
  version?: string;
}

interface DbHealth {
  status: string;
  latency_ms?: number;
  connections?: number;
  pool_size?: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function dot(ok: boolean | null, label: string) {
  const cls = ok === null ? "bg-slate-500" : ok ? "bg-emerald-400" : "bg-red-400";
  return (
    <span className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full flex-shrink-0 ${cls} ${ok ? "animate-pulse" : ""}`} />
      <span className={ok === null ? "text-slate-500" : ok ? "text-emerald-300" : "text-red-300"}>
        {ok === null ? "Kontrol ediliyor…" : ok ? label + " aktif" : label + " yanıt vermiyor"}
      </span>
    </span>
  );
}

function fmt(dt: string | null) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "medium" });
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SystemPage() {
  const runtime = useCoreRuntime();
  const [aiHealth, setAiHealth] = useState<AiHealth | null>(null);
  const [dbHealth, setDbHealth] = useState<DbHealth | null>(null);
  const [aiError, setAiError] = useState(false);
  const [dbError, setDbError] = useState(false);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);

  useEffect(() => {
    async function check() {
      setCheckedAt(new Date());
      // AI Gateway health
      try {
        const r = await fetch("/api/ai/health");
        if (r.ok) setAiHealth(await r.json());
        else setAiError(true);
      } catch { setAiError(true); }

      // Backend DB health
      try {
        const r = await fetch("/api/v1/health/db");
        if (r.ok) setDbHealth(await r.json());
        else setDbError(true);
      } catch { setDbError(true); }
    }
    check();
    const t = setInterval(check, 60_000);
    return () => clearInterval(t);
  }, []);

  const runningServices = runtime.services.filter(s => s.state === "running").length;
  const totalServices = runtime.services.length;
  const allOk = runtime.backendReady && !aiError && !dbError && runningServices === totalServices;

  const aiProviders: AiHealthProvider[] = aiHealth
    ? Object.entries(aiHealth.providers).map(([name, ok]) => ({
        name,
        ok,
        latency_ms: aiHealth.latency_ms?.[name],
      }))
    : [];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <PageHeader
        title="Sistem Durumu"
        description={checkedAt ? `Son kontrol: ${fmt(checkedAt.toISOString())}` : "Yükleniyor…"}
        badge={
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${allOk ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-amber-500/20 bg-amber-500/10 text-amber-300"}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${allOk ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
            {allOk ? "Tüm Sistemler Normal" : "Dikkat"}
          </span>
        }
        right={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => runtime.refresh()}
              className="rounded-xl border border-slate-700 px-4 py-1.5 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800"
            >
              Yenile
            </button>
            <Link
              href="/system/services"
              className="rounded-xl bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
            >
              Servis Yönetimi →
            </Link>
          </div>
        }
      />

      <div className="mx-auto max-w-6xl px-6 py-6 space-y-6">
        {/* Status overview */}
        <MetricRow cols={4}>
          <StatCard
            label="Backend"
            value={runtime.backendReady ? "Aktif" : "Kapalı"}
            color={runtime.backendReady ? "emerald" : "red"}
          />
          <StatCard
            label="Servisler"
            value={`${runningServices}/${totalServices}`}
            color={runningServices === totalServices ? "emerald" : "amber"}
          />
          <StatCard
            label="AI Gateway"
            value={aiError ? "Kapalı" : aiHealth ? "Aktif" : "…"}
            color={aiError ? "red" : aiHealth ? "emerald" : "slate"}
          />
          <StatCard
            label="Veritabanı"
            value={dbError ? "Kapalı" : dbHealth ? "Aktif" : "…"}
            color={dbError ? "red" : dbHealth ? "emerald" : "slate"}
          />
        </MetricRow>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Core services */}
          <SectionCard title="Çekirdek Servisler">
            {runtime.loading ? (
              <p className="text-sm text-slate-500">Yükleniyor…</p>
            ) : runtime.services.length === 0 ? (
              <p className="text-sm text-slate-500">Servis bilgisi alınamadı.</p>
            ) : (
              <div className="space-y-2">
                {runtime.services.map(svc => (
                  <div key={svc.name} className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-800/40 px-4 py-2.5">
                    <div>
                      <p className="text-sm font-medium text-white">{svc.name}</p>
                      {svc.healthUrl && <p className="text-xs text-slate-500 font-mono">{svc.healthUrl}</p>}
                    </div>
                    <div className="text-right">
                      <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${
                        svc.state === "running" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" :
                        svc.state === "stopped" ? "border-slate-700 bg-slate-800 text-slate-400" :
                        svc.state === "unhealthy" ? "border-amber-500/20 bg-amber-500/10 text-amber-300" :
                        "border-slate-700 bg-slate-800 text-slate-400"
                      }`}>
                        {svc.state}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          {/* AI Gateway providers */}
          <SectionCard title="AI Sağlayıcıları">
            {aiError ? (
              <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300">
                AI Gateway yanıt vermiyor
              </div>
            ) : aiProviders.length === 0 ? (
              <p className="text-sm text-slate-500">AI Gateway sorgulanıyor…</p>
            ) : (
              <div className="space-y-2">
                {aiProviders.map(p => (
                  <div key={p.name} className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-800/40 px-4 py-2.5">
                    <div className="flex items-center gap-3">
                      <span className={`h-2 w-2 rounded-full flex-shrink-0 ${p.ok ? "bg-emerald-400" : "bg-red-400"}`} />
                      <span className="text-sm font-medium capitalize text-white">{p.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {p.latency_ms != null && (
                        <span className="text-xs text-slate-400">{Math.round(p.latency_ms)}ms</span>
                      )}
                      <span className={`text-xs font-medium ${p.ok ? "text-emerald-400" : "text-red-400"}`}>
                        {p.ok ? "Kullanılabilir" : "Kullanılamaz"}
                      </span>
                    </div>
                  </div>
                ))}
                {aiHealth?.version && (
                  <p className="text-xs text-slate-500 pt-1">Gateway v{aiHealth.version}</p>
                )}
              </div>
            )}
          </SectionCard>

          {/* Database health */}
          <SectionCard title="Veritabanı">
            {dbError ? (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-300">
                DB sağlık endpoint&#39;i yanıt vermiyor — PostgreSQL bağlı olabilir.
              </div>
            ) : dbHealth ? (
              <div className="space-y-2">
                {[
                  { label: "Durum", value: dbHealth.status },
                  dbHealth.latency_ms != null ? { label: "Gecikme", value: `${Math.round(dbHealth.latency_ms)}ms` } : null,
                  dbHealth.connections != null ? { label: "Bağlantılar", value: String(dbHealth.connections) } : null,
                  dbHealth.pool_size != null ? { label: "Havuz", value: String(dbHealth.pool_size) } : null,
                ].filter(Boolean).map((row) => row && (
                  <div key={row.label} className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">{row.label}</span>
                    <span className="font-medium text-white">{row.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">Sorgulanıyor…</p>
            )}
          </SectionCard>

          {/* Quick links */}
          <SectionCard title="Bağlantılar">
            <div className="space-y-1">
              {[
                { href: "/system/services", label: "Servis Yönetimi", desc: "Başlat / Durdur / Yeniden başlat" },
                { href: "/notifications", label: "Bildirimler", desc: "Hata + heal olayları inbox" },
                { href: "/admin/audit", label: "Audit Logu", desc: "Tüm sistem eylemleri" },
                { href: "/admin/users", label: "Kullanıcı Yönetimi", desc: "Davet, rol, deaktivasyon" },
                { href: "/admin/prompts", label: "Prompt Registry", desc: "Prompt versiyon, rollout ve resolve görünümü" },
                { href: "/ai-quality", label: "AI Kalite Dashboard", desc: "Model maliyet ve LLM-as-Judge" },
                { href: "/ai-workflows", label: "Workflow Health", desc: "Queue, DLQ ve artifact operasyon görünümü" },
              ].map(({ href, label, desc }) => (
                <Link
                  key={href}
                  href={href}
                  className="flex items-center justify-between rounded-xl border border-slate-700 px-4 py-3 transition-colors hover:bg-slate-800/40 group"
                >
                  <div>
                    <p className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors">{label}</p>
                    <p className="text-xs text-slate-500">{desc}</p>
                  </div>
                  <span className="text-slate-600 group-hover:text-slate-400 transition-colors">→</span>
                </Link>
              ))}
            </div>
          </SectionCard>
        </div>

        {/* Runtime checkedAt */}
        {runtime.checkedAt && (
          <p className="text-center text-xs text-slate-600">
            Servis kontrolü: {fmt(runtime.checkedAt)}
          </p>
        )}
      </div>
    </div>
  );
}
