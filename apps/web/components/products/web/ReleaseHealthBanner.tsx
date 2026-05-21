"use client";

import Link from "next/link";
import { useProject } from "@/lib/useProject";
import {
  useReleaseHealth,
  type ReleaseHealthCheck,
  type ReleaseVerdict,
} from "@/lib/hooks/use-web-dashboard";

const DEMO_CHECKS: ReleaseHealthCheck[] = [
  { key: "visual", label: "Visual regression",     status: "warn", detail: "1 kritik diff onay bekliyor",  href: "#visual" },
  { key: "a11y",   label: "Accessibility (a11y)",  status: "fail", detail: "2 WCAG AA blocker — Checkout", href: "#a11y" },
  { key: "pass",   label: "Pass rate (24s)",        status: "ok",   detail: "94.8% · hedef 92%",            href: "#stats" },
  { key: "perf",   label: "Perf (Core Web Vitals)", status: "warn", detail: "LCP 2.9s · hedef <2.5s",       href: "#perf" },
];

const DEMO_RELEASE = "web@2.5.0-rc3";

function verdictFromChecks(c: ReleaseHealthCheck[]): ReleaseVerdict {
  if (c.some((x) => x.status === "fail")) return "block";
  if (c.some((x) => x.status === "warn")) return "caution";
  return "ship";
}

const VERDICT_STYLE = {
  ship: {
    bg: "from-emerald-500/15 via-emerald-500/5 to-transparent border-emerald-500/30",
    dot: "bg-emerald-400",
    title: "Ship'e hazır",
    sub: "Tüm release kontrolleri yeşil.",
    label: "GREEN",
    labelCls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  },
  caution: {
    bg: "from-amber-500/15 via-amber-500/5 to-transparent border-amber-500/30",
    dot: "bg-amber-400",
    title: "Ship dikkatli ol",
    sub: "Yayına çıkmadan gözden geçirilecek noktalar var.",
    label: "AMBER",
    labelCls: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  },
  block: {
    bg: "from-rose-500/15 via-rose-500/5 to-transparent border-rose-500/30",
    dot: "bg-rose-400",
    title: "Ship'e hazır değil",
    sub: "Açık blocker'lar çözülmeden yayınlama.",
    label: "RED",
    labelCls: "bg-rose-500/20 text-rose-300 border-rose-500/40",
  },
} as const;

const STATUS_ICON = {
  ok:   { icon: "✓", cls: "text-emerald-400" },
  warn: { icon: "⚠", cls: "text-amber-400"   },
  fail: { icon: "✕", cls: "text-rose-400"    },
} as const;

export function ReleaseHealthBanner() {
  const { projectId } = useProject();
  const { data, isLoading } = useReleaseHealth(projectId);

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 lg:p-6 animate-pulse">
        <div className="flex flex-col lg:flex-row lg:items-center gap-5">
          <div className="flex items-center gap-4 lg:min-w-[320px]">
            <div className="h-14 w-14 rounded-2xl bg-slate-800 shrink-0" />
            <div className="flex-1">
              <div className="h-3 w-24 rounded bg-slate-800 mb-2" />
              <div className="h-5 w-40 rounded bg-slate-800" />
            </div>
          </div>
          <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 rounded-lg bg-slate-800/50" />
            ))}
          </div>
          <div className="lg:min-w-[140px]">
            <div className="h-10 rounded-lg bg-slate-800" />
          </div>
        </div>
      </section>
    );
  }

  const checks = data?.checks ?? DEMO_CHECKS;
  const release = data?.release ?? DEMO_RELEASE;
  const verdict: ReleaseVerdict = data?.verdict ?? verdictFromChecks(checks);
  const isDemo = !data;
  const v = VERDICT_STYLE[verdict];

  return (
    <section className={`relative rounded-2xl border bg-gradient-to-r ${v.bg} p-5 lg:p-6`}>
      <div className="flex flex-col lg:flex-row lg:items-center gap-5">
        {/* Sol: trafik ışığı + verdict */}
        <div className="flex items-center gap-4 lg:min-w-[320px]">
          <div className="relative shrink-0">
            <div className={`h-14 w-14 rounded-2xl ${v.dot} shadow-lg`} />
            <div className={`absolute inset-0 h-14 w-14 rounded-2xl ${v.dot} animate-ping opacity-30`} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold tracking-widest px-2 py-0.5 rounded-full border ${v.labelCls}`}>
                {v.label}
              </span>
              <span className="text-[11px] text-slate-400">Release Sağlığı · {release}</span>
              {isDemo && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">
                  Demo
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold text-white mt-1">{v.title}</h2>
            <p className="text-xs text-slate-400">{v.sub}</p>
          </div>
        </div>

        {/* Sağ: kontrol listesi */}
        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2 min-w-0">
          {checks.map((c) => {
            const s = STATUS_ICON[c.status];
            return (
              <Link
                key={c.key}
                href={c.href ?? "#"}
                className="flex items-start gap-2 rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2 hover:bg-slate-900/60 transition-colors"
              >
                <span className={`text-base font-bold ${s.cls} shrink-0 leading-5`}>{s.icon}</span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-white truncate">{c.label}</p>
                  <p className="text-[11px] text-slate-400 truncate">{c.detail}</p>
                </div>
              </Link>
            );
          })}
        </div>

        {/* CTA */}
        <div className="lg:min-w-[140px] flex lg:flex-col lg:items-stretch items-center gap-2">
          <button
            type="button"
            disabled={verdict === "block"}
            className={`flex-1 lg:flex-initial px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
              verdict === "block"
                ? "bg-rose-500/15 text-rose-300 border border-rose-500/30 cursor-not-allowed"
                : verdict === "caution"
                  ? "bg-amber-500/15 text-amber-200 border border-amber-500/30 hover:bg-amber-500/25"
                  : "bg-emerald-500 text-white hover:bg-emerald-400 shadow-lg shadow-emerald-500/20"
            }`}
          >
            {verdict === "block" ? "Ship'lenemez" : verdict === "caution" ? "Yine de ship et" : "Ship'e başla →"}
          </button>
          <button
            type="button"
            className="px-3 py-2 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800/60"
          >
            Detay raporu
          </button>
        </div>
      </div>
    </section>
  );
}
