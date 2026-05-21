"use client";

import Link from "next/link";

import { LearningChecklistCard } from "@/components/LearningChecklistCard";
import { useRouteParam } from "@/lib/use-route-param";

const QUICK_STARTS = [
  {
    title: "Senaryo Yaz",
    description: "Manuel, AI ile (Sıfır Bilgi) veya recorder ile",
    icon: "📝",
    href: "scenarios/new",
    color: "border-blue-500/30 bg-blue-500/5 hover:bg-blue-500/10",
  },
  {
    title: "AI ile Otomatik Üret",
    description: "9 ajan, dokuman/URL'den senaryo paketi",
    icon: "🤖",
    href: "sifir-bilgi",
    color: "border-purple-500/30 bg-purple-500/5 hover:bg-purple-500/10",
  },
  {
    title: "Test Koş",
    description: "Mevcut senaryoları çalıştır, sonuçları izle",
    icon: "▶️",
    href: "executions/new",
    color: "border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10",
  },
  {
    title: "Pipeline Görünümü",
    description: "Analiz → Tasarım → Koşum → Rapor — tek ekranda",
    icon: "🔄",
    href: "pipeline",
    color: "border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10",
  },
  {
    title: "Mobil Test",
    description: "iOS + Android cihaz farm'ında koşum",
    icon: "📱",
    href: "mobile",
    color: "border-rose-500/30 bg-rose-500/5 hover:bg-rose-500/10",
  },
  {
    title: "API Test",
    description: "Endpoint testleri, chain builder, contract validation",
    icon: "🔌",
    href: "api-tests",
    color: "border-cyan-500/30 bg-cyan-500/5 hover:bg-cyan-500/10",
  },
];

export default function ProjectWelcomePage() {
  const projectId = useRouteParam("projectId");

  return (
    <div
      className="min-h-screen bg-slate-950 text-slate-100"
      data-testid="project-welcome-page"
    >
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">👋 Hoş geldin</h1>
          <p className="mt-2 text-sm text-slate-400">
            Test otomasyon platformuna giriş — buradan başla.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <section data-testid="welcome-quick-starts">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
                Hızlı başlangıç
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {QUICK_STARTS.map((q) => (
                  <Link
                    key={q.title}
                    href={`/p/${projectId}/${q.href}`}
                    className={`block rounded-xl border p-4 transition-colors ${q.color}`}
                    data-testid={`quick-start-${q.href.replace(/[/.]/g, "-")}`}
                  >
                    <div className="text-2xl">{q.icon}</div>
                    <h3 className="mt-2 text-sm font-semibold text-white">{q.title}</h3>
                    <p className="mt-1 text-xs text-slate-400">{q.description}</p>
                  </Link>
                ))}
              </div>
            </section>

            <section className="grid grid-cols-2 gap-3">
              <Link
                href="/workflows-gallery"
                className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 hover:bg-indigo-500/10"
                data-testid="welcome-workflows-gallery"
              >
                <div className="text-2xl">⚡</div>
                <h3 className="mt-2 text-sm font-semibold text-white">Workflow Galerisi</h3>
                <p className="mt-1 text-xs text-slate-400">8 hazır akış — smoke, regresyon, compliance</p>
              </Link>
              <Link
                href="/kb"
                className="rounded-xl border border-slate-500/30 bg-slate-500/5 p-4 hover:bg-slate-500/10"
                data-testid="welcome-kb"
              >
                <div className="text-2xl">📚</div>
                <h3 className="mt-2 text-sm font-semibold text-white">Knowledge Base</h3>
                <p className="mt-1 text-xs text-slate-400">Rehberler, nasıl yapılır, sorun giderme</p>
              </Link>
            </section>
          </div>

          <aside className="space-y-6">
            <LearningChecklistCard />

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <h3 className="text-sm font-semibold text-white">💡 İpucu</h3>
              <p className="mt-2 text-xs text-slate-400">
                <kbd className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs">⌘K</kbd>{" "}
                ile her yere klavyeden ulaş.
              </p>
              <p className="mt-2 text-xs text-slate-400">
                <kbd className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs">?</kbd>{" "}
                ile klavye kısayollarını gör.
              </p>
              <p className="mt-2 text-xs text-slate-400">
                Sağ alttaki{" "}
                <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-[10px] text-white">
                  ?
                </span>{" "}
                ile yardım merkezini aç.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
