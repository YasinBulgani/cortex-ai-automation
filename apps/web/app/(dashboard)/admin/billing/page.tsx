"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { StatCard, MetricRow } from "@/components/nexus";

// ── Types ─────────────────────────────────────────────────────────────────────

interface UsageStats {
  plan: string;
  plan_expires_at?: string | null;
  scenario_count: number;
  scenario_limit: number;
  run_count_month: number;
  run_limit_month: number;
  ai_token_spend_usd?: number;
  ai_token_limit_usd?: number;
  team_size: number;
  team_limit: number;
  storage_mb?: number;
  storage_limit_mb?: number;
  project_count?: number;
  project_limit?: number;
}

const PLAN_INFO: Record<string, { label: string; color: string; features: string[] }> = {
  free: {
    label: "Ücretsiz",
    color: "border-slate-700 bg-slate-800/40 text-slate-300",
    features: ["5 proje", "100 koşu/ay", "2 kullanıcı", "1 GB depolama"],
  },
  starter: {
    label: "Başlangıç",
    color: "border-blue-500/30 bg-blue-500/5 text-blue-300",
    features: ["25 proje", "1000 koşu/ay", "10 kullanıcı", "10 GB depolama", "AI analiz"],
  },
  pro: {
    label: "Profesyonel",
    color: "border-violet-500/30 bg-violet-500/5 text-violet-300",
    features: ["Sınırsız proje", "10.000 koşu/ay", "25 kullanıcı", "50 GB depolama", "Öncelikli destek", "AI analiz + LLM-as-Judge"],
  },
  enterprise: {
    label: "Kurumsal",
    color: "border-emerald-500/30 bg-emerald-500/5 text-emerald-300",
    features: ["Sınırsız her şey", "On-prem / VPC", "SSO / LDAP", "SLA garantisi", "Dedicated AI"],
  },
};

const PLANS = ["free", "starter", "pro", "enterprise"];

// ── Helpers ───────────────────────────────────────────────────────────────────

function UsageBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const color = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-slate-400">{label}</span>
        <span className="text-xs font-medium text-white">{used.toLocaleString()} / {limit.toLocaleString()}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <p className={`mt-0.5 text-right text-[10px] ${pct >= 90 ? "text-red-400" : "text-slate-500"}`}>{pct}% kullanıldı</p>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [changingPlan, setChangingPlan] = useState<string | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);

  const loadUsage = () => {
    apiFetch<UsageStats>("/api/v1/admin/billing/usage")
      .then(setStats)
      .catch(() => {
        // Fallback demo values when endpoint not available
        setStats({
          plan: "starter",
          scenario_count: 47,
          scenario_limit: 500,
          run_count_month: 312,
          run_limit_month: 1000,
          ai_token_spend_usd: 4.23,
          ai_token_limit_usd: 20,
          team_size: 5,
          team_limit: 10,
          storage_mb: 1240,
          storage_limit_mb: 10240,
        });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadUsage();
  }, []);

  const handlePlanChange = async (planCode: string) => {
    if (planCode === "enterprise") {
      window.location.href = "mailto:sales@neurexqa.com?subject=Kurumsal plan talebi";
      return;
    }
    setPlanError(null);
    setChangingPlan(planCode);
    try {
      // Paid plans → Stripe Checkout; free → direct downgrade
      if (planCode === "starter" || planCode === "pro") {
        try {
          const result = await apiFetch<{ checkout_url?: string }>(
            "/api/v1/admin/billing/checkout",
            {
              method: "POST",
              body: JSON.stringify({ plan_code: planCode }),
            },
          );
          if (result?.checkout_url) {
            window.location.href = result.checkout_url;
            return;
          }
          setPlanError("Stripe checkout adresi alınamadı.");
          return;
        } catch (e) {
          // 503 = Stripe not configured → fall back to direct plan change
          const msg = e instanceof Error ? e.message : "";
          if (!/503|not_configured|Stripe/i.test(msg)) {
            throw e;
          }
        }
      }

      await apiFetch("/api/v1/admin/billing/plan", {
        method: "POST",
        body: JSON.stringify({ plan_code: planCode }),
      });
      loadUsage();
    } catch (e) {
      setPlanError(
        e instanceof Error ? e.message : "Plan değiştirilemedi. Lütfen tekrar deneyin.",
      );
    } finally {
      setChangingPlan(null);
    }
  };

  const openCustomerPortal = async () => {
    setPlanError(null);
    try {
      const result = await apiFetch<{ portal_url?: string }>(
        "/api/v1/admin/billing/portal",
        { method: "POST" },
      );
      if (result?.portal_url) {
        window.location.href = result.portal_url;
      }
    } catch (e) {
      setPlanError(
        e instanceof Error
          ? e.message
          : "Müşteri portalı açılamadı. Lütfen daha sonra tekrar deneyin.",
      );
    }
  };

  const planInfo = PLAN_INFO[stats?.plan ?? "free"];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <PageHeader
        title="Faturalama & Kullanım"
        description="Plan kullanım durumu ve hesap sınırları"
        right={
          <div className="flex items-center gap-2">
            {stats?.plan && stats.plan !== "free" && (
              <button
                type="button"
                onClick={openCustomerPortal}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-1.5 text-sm font-medium text-slate-200 transition-colors hover:border-slate-500"
              >
                Faturayı Yönet
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowUpgrade(p => !p)}
              className="rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-1.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              Planı Yükselt
            </button>
          </div>
        }
      />

      <div className="mx-auto max-w-4xl px-6 py-6 space-y-6">
        {/* Current plan */}
        <SectionCard title="Mevcut Plan">
          {loading ? (
            <div className="animate-pulse h-16 rounded-xl bg-slate-800" />
          ) : (
            <div className={`flex items-center justify-between rounded-xl border px-5 py-4 ${planInfo?.color ?? ""}`}>
              <div>
                <p className="text-lg font-bold">{planInfo?.label ?? stats?.plan}</p>
                {stats?.plan_expires_at && (
                  <p className="text-xs opacity-70 mt-0.5">
                    Yenileme: {new Date(stats.plan_expires_at).toLocaleDateString("tr-TR")}
                  </p>
                )}
              </div>
              <span className="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide">
                {stats?.plan ?? "free"}
              </span>
            </div>
          )}
        </SectionCard>

        {/* Usage overview */}
        {stats && (
          <MetricRow cols={4}>
            <StatCard label="Senaryo" value={`${stats.scenario_count}/${stats.scenario_limit}`} color="blue" />
            <StatCard label="Koşu (Bu Ay)" value={`${stats.run_count_month}/${stats.run_limit_month}`} color="emerald" />
            <StatCard label="Ekip" value={`${stats.team_size}/${stats.team_limit}`} color="violet" />
            {stats.ai_token_spend_usd != null ? (
              <StatCard label="AI Harcama" value={`$${stats.ai_token_spend_usd.toFixed(2)}`} color="amber" />
            ) : (
              <StatCard label="Depolama" value={stats.storage_mb ? `${Math.round(stats.storage_mb / 1024)}GB` : "—"} color="slate" />
            )}
          </MetricRow>
        )}

        {/* Usage bars */}
        {stats && (
          <SectionCard title="Kullanım Detayı">
            <div className="space-y-4">
              {stats.project_count != null && stats.project_limit != null && stats.project_limit > 0 && (
                <UsageBar used={stats.project_count} limit={stats.project_limit} label="Proje" />
              )}
              <UsageBar used={stats.scenario_count} limit={stats.scenario_limit} label="Senaryo" />
              <UsageBar used={stats.run_count_month} limit={stats.run_limit_month} label="Aylık Koşu" />
              <UsageBar used={stats.team_size} limit={stats.team_limit} label="Ekip Üyesi" />
              {stats.storage_mb != null && stats.storage_limit_mb != null && (
                <UsageBar used={Math.round(stats.storage_mb)} limit={stats.storage_limit_mb} label="Depolama (MB)" />
              )}
              {stats.ai_token_spend_usd != null && stats.ai_token_limit_usd != null && (
                <UsageBar
                  used={Math.round(stats.ai_token_spend_usd * 100)}
                  limit={Math.round(stats.ai_token_limit_usd * 100)}
                  label="AI Harcama (cent)"
                />
              )}
            </div>
          </SectionCard>
        )}

        {/* Plan comparison */}
        {showUpgrade && (
          <SectionCard title="Plan Seçenekleri">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {PLANS.map(plan => {
                const info = PLAN_INFO[plan];
                const isCurrent = plan === stats?.plan;
                return (
                  <div
                    key={plan}
                    className={`rounded-xl border p-4 ${isCurrent ? "border-blue-500/40 bg-blue-500/5" : "border-slate-700 bg-slate-800/40"}`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-bold text-white">{info.label}</p>
                      {isCurrent && <span className="rounded-full bg-blue-600 px-2 py-0.5 text-[9px] font-bold text-white uppercase">Mevcut</span>}
                    </div>
                    <ul className="space-y-1.5 mb-4">
                      {info.features.map(f => (
                        <li key={f} className="flex items-center gap-1.5 text-xs text-slate-400">
                          <span className="h-1 w-1 rounded-full bg-slate-500 flex-shrink-0" />
                          {f}
                        </li>
                      ))}
                    </ul>
                    {!isCurrent && (
                      <button
                        type="button"
                        disabled={changingPlan !== null}
                        className="w-full rounded-lg border border-slate-600 px-3 py-2 text-xs font-medium text-slate-300 transition-colors hover:border-blue-500/40 hover:text-blue-300 disabled:opacity-50"
                        onClick={() => handlePlanChange(plan)}
                      >
                        {changingPlan === plan
                          ? "Geçiliyor…"
                          : plan === "enterprise"
                            ? "Bize Ulaşın"
                            : "Seç"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
            {planError && (
              <p className="mt-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                {planError}
              </p>
            )}
            <p className="mt-4 text-center text-xs text-slate-500">
              Ödeme altyapısı (Stripe) entegrasyonu üzerinde çalışıyoruz. Şu an plan
              değişiklikleri kayıt altına alınır; faturalama sonra etkinleşir. Kurumsal
              için satış ekibine yazın.
            </p>
          </SectionCard>
        )}
      </div>
    </div>
  );
}
