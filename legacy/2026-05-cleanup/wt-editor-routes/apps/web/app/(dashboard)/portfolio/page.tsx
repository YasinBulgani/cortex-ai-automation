"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

type ProjectItem = {
  id: string;
  name: string;
  scenarios: number;
  lastRun: string;
  passRate: number;
  status: "active" | "warning" | "critical";
};

type ActivityItem = { user: string; action: string; time: string; avatar: string };

const SAMPLE_PROJECTS: ProjectItem[] = [
  { id: "p1", name: "Ödeme API", scenarios: 245, lastRun: "2 sa önce", passRate: 94, status: "active" },
  { id: "p2", name: "Müşteri Portal", scenarios: 189, lastRun: "5 sa önce", passRate: 87, status: "active" },
  { id: "p3", name: "Mobil App", scenarios: 312, lastRun: "1 gün önce", passRate: 76, status: "warning" },
  { id: "p4", name: "ERP Entegrasyon", scenarios: 156, lastRun: "3 gün önce", passRate: 91, status: "active" },
  { id: "p5", name: "Raporlama", scenarios: 82, lastRun: "1 hf önce", passRate: 68, status: "critical" },
];

const SAMPLE_ACTIVITIES: ActivityItem[] = [
  { user: "Yasin B.", action: "Ödeme API — 12 senaryo ekledi", time: "15 dk", avatar: "YB" },
  { user: "Ayşe K.", action: "Müşteri Portal regresyon tamamlandı", time: "1 sa", avatar: "AK" },
  { user: "Mehmet D.", action: "Mobil App — 3 senaryo onayladı", time: "3 sa", avatar: "MD" },
];

const STATUS_CFG = {
  active: { label: "Aktif", bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400" },
  warning: { label: "Uyarı", bg: "bg-amber-500/10", text: "text-amber-400", dot: "bg-amber-400" },
  critical: { label: "Kritik", bg: "bg-red-500/10", text: "text-red-400", dot: "bg-red-400" },
};

const AVATAR_COLORS = ["bg-violet-600", "bg-blue-600", "bg-teal-600", "bg-pink-600", "bg-amber-600"];

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectItem[]>(SAMPLE_PROJECTS);
  const [activities, setActivities] = useState<ActivityItem[]>(SAMPLE_ACTIVITIES);
  const [dataMode, setDataMode] = useState<"live" | "sample">("sample");

  useEffect(() => {
    apiFetch<{ projects?: ProjectItem[]; activities?: ActivityItem[] }>("/api/v1/tspm/dashboard/global")
      .then(d => {
        if (d.projects?.length || d.activities?.length) setDataMode("live");
        if (d.projects?.length) setProjects(d.projects);
        if (d.activities?.length) setActivities(d.activities);
      })
      .catch(() => {});
  }, []);

  const totalScenarios = projects.reduce((s, p) => s + p.scenarios, 0);
  const avgPass = projects.length
    ? Math.round(projects.reduce((s, p) => s + p.passRate, 0) / projects.length)
    : 0;

  const kpiCards = [
    { label: "Toplam Senaryo", value: totalScenarios.toLocaleString("tr-TR"), color: "text-blue-400" },
    { label: "Proje Sayısı", value: projects.length.toString(), color: "text-indigo-400" },
    { label: "Ort. Başarı", value: `%${avgPass}`, color: avgPass >= 85 ? "text-emerald-400" : avgPass >= 70 ? "text-amber-400" : "text-rose-400" },
    { label: "Kritik Proje", value: projects.filter(p => p.status === "critical").length.toString(), color: "text-rose-400" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 p-5 flex flex-col gap-5 text-slate-100" data-testid="portfolio-page">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Portföy Görünümü</h1>
          <p className="text-xs text-slate-500 mt-0.5">Portföy genelinde kalite ve koşu özetleri</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`rounded-full border px-3 py-1.5 text-[11px] font-medium ${
            dataMode === "live" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-amber-500/20 bg-amber-500/10 text-amber-200"
          }`}>
            {dataMode === "live" ? "Canlı veri" : "Örnek görünüm"}
          </span>
          <Link href="/new-project"
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 transition-colors text-white">
            + Yeni Proje
          </Link>
        </div>
      </header>

      {/* KPI Cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {kpiCards.map(c => (
          <div key={c.label} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="text-xs font-medium text-slate-400">{c.label}</div>
            <div className={`text-2xl font-bold mt-1 ${c.color}`}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Project Health Table */}
        <section className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-slate-200">Proje Sağlık Durumu</h2>
            <p className="text-xs text-slate-500">Başarı oranı ve güncel metrikler</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800 text-left text-[11px] text-slate-500 uppercase tracking-wide">
                  <th className="px-5 py-3 font-medium">Proje</th>
                  <th className="px-4 py-3 font-medium text-right">Senaryo</th>
                  <th className="px-4 py-3 font-medium">Başarı</th>
                  <th className="px-4 py-3 font-medium">Son Koşu</th>
                  <th className="px-4 py-3 font-medium">Durum</th>
                </tr>
              </thead>
              <tbody>
                {projects.map(p => {
                  const st = STATUS_CFG[p.status];
                  const barColor = p.passRate >= 90 ? "bg-emerald-500" : p.passRate >= 75 ? "bg-blue-500" : p.passRate >= 60 ? "bg-amber-500" : "bg-red-500";
                  return (
                    <tr key={p.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 transition-colors">
                      <td className="px-5 py-3.5">
                        <Link href={`/p/${p.id}`} className="font-medium text-white hover:text-blue-300 transition-colors text-sm">{p.name}</Link>
                      </td>
                      <td className="px-4 py-3.5 text-right text-sm tabular-nums text-slate-300">{p.scenarios}</td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-20 rounded-full bg-slate-800 overflow-hidden">
                            <div className={`h-full rounded-full ${barColor}`} style={{ width: `${p.passRate}%` }} />
                          </div>
                          <span className="text-xs text-slate-400">%{p.passRate}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-500">{p.lastRun}</td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex items-center gap-1 rounded-full border border-slate-700 px-2 py-0.5 text-[10px] font-medium ${st.bg} ${st.text}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
                          {st.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Activities */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="text-sm font-semibold text-slate-200 mb-4">Son Aktiviteler</h2>
          <div className="space-y-4">
            {activities.map((a, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${AVATAR_COLORS[i % AVATAR_COLORS.length]} text-[10px] font-bold text-white`}>
                  {a.avatar}
                </div>
                <div className="min-w-0 flex-1 pt-0.5">
                  <p className="text-xs">
                    <span className="font-semibold text-slate-200">{a.user}</span>{" "}
                    <span className="text-slate-400">{a.action}</span>
                  </p>
                  <p className="text-[10px] text-slate-600 mt-0.5">{a.time}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          { href: "/new-project", icon: "📁", label: "Yeni Proje" },
          { href: "/bgtest-wizard", icon: "🧙", label: "Akış Sihirbazı" },
          { href: "/projects", icon: "📋", label: "Projeler" },
          { href: "/veri-kaynagi", icon: "🗄️", label: "Veri Kaynağı" },
        ].map(a => (
          <Link key={a.label} href={a.href}
            className="flex items-center gap-2 rounded-xl border border-slate-700/60 bg-slate-800/30 p-3.5 hover:border-blue-500/40 hover:bg-blue-500/5 transition-all">
            <span className="text-xl">{a.icon}</span>
            <span className="text-xs font-semibold text-slate-200">{a.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
