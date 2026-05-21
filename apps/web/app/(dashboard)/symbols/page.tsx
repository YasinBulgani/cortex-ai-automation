"use client";

import { BgtestLogo } from "@/components/BgtestLogo";
import { PageHeader } from "@/components/nexus/PageHeader";

const statusIcons = [
  { label: "Başarılı", color: "bg-emerald-500", symbol: "✓" },
  { label: "Başarısız", color: "bg-red-500", symbol: "✗" },
  { label: "Beklemede", color: "bg-amber-500", symbol: "⏳" },
  { label: "Çalışıyor", color: "bg-blue-500", symbol: "▶" },
  { label: "Atlandı", color: "bg-slate-500", symbol: "⏭" },
  { label: "İptal", color: "bg-slate-600", symbol: "⊘" },
];

const priorityIcons = [
  { label: "Kritik", color: "bg-red-600", symbol: "P0" },
  { label: "Yüksek", color: "bg-orange-500", symbol: "P1" },
  { label: "Orta", color: "bg-amber-500", symbol: "P2" },
  { label: "Düşük", color: "bg-blue-400", symbol: "P3" },
];

const moduleIcons = [
  { label: "Senaryolar", emoji: "📋" },
  { label: "Koşular", emoji: "🚀" },
  { label: "Akışlar", emoji: "🔀" },
  { label: "Regresyon", emoji: "📊" },
  { label: "Onaylar", emoji: "✅" },
  { label: "İçe Aktar", emoji: "📥" },
  { label: "Projeler", emoji: "📁" },
  { label: "Kullanıcılar", emoji: "👥" },
  { label: "Ayarlar", emoji: "⚙️" },
  { label: "Raporlar", emoji: "📈" },
];

export default function SymbolsPage() {
  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
          </svg>
        }
        title="Simge Yönetimi"
        description="Platform genelinde kullanılan simgeler, renkler ve durum göstergeleri."
      />

      {/* Logo */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Marka</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col items-center gap-3 rounded-xl border border-slate-800 bg-white/5 p-6">
            <BgtestLogo className="h-12" />
            <span className="text-xs text-slate-500">Ana Logo (Koyu Tema)</span>
          </div>
          <div className="flex flex-col items-center gap-3 rounded-xl border border-slate-800 bg-slate-800/50 p-6">
            <BgtestLogo className="h-12" />
            <span className="text-xs text-slate-400">Ana Logo (Alternatif)</span>
          </div>
        </div>
      </div>

      {/* Status Icons */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Durum Simgeleri</h3>
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
          {statusIcons.map((icon) => (
            <div key={icon.label} className="flex flex-col items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className={`flex h-10 w-10 items-center justify-center rounded-full ${icon.color} text-white text-sm font-bold`}>
                {icon.symbol}
              </div>
              <span className="text-xs text-slate-400">{icon.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Priority Icons */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Öncelik Seviyeleri</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {priorityIcons.map((icon) => (
            <div key={icon.label} className="flex flex-col items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${icon.color} text-white text-xs font-bold`}>
                {icon.symbol}
              </div>
              <span className="text-xs text-slate-400">{icon.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Module Icons */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Modül Simgeleri</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {moduleIcons.map((icon) => (
            <div key={icon.label} className="flex flex-col items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-2xl">{icon.emoji}</span>
              <span className="text-xs text-slate-400">{icon.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Color Palette */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Renk Paleti</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { name: "Birincil", color: "bg-blue-600", hex: "#2563eb" },
            { name: "Başarılı", color: "bg-emerald-500", hex: "#10b981" },
            { name: "Uyarı", color: "bg-amber-500", hex: "#f59e0b" },
            { name: "Hata", color: "bg-red-500", hex: "#ef4444" },
            { name: "Bilgi", color: "bg-blue-500", hex: "#3b82f6" },
            { name: "Marka Yeşil", color: "bg-[#1B8C4E]", hex: "#1B8C4E" },
            { name: "Arka Plan", color: "bg-slate-950", hex: "#020617" },
            { name: "Kart", color: "bg-slate-900", hex: "#0f172a" },
          ].map((c) => (
            <div key={c.name} className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-3">
              <div className={`h-8 w-8 rounded-lg border border-slate-700 ${c.color} shrink-0`} />
              <div>
                <p className="text-xs font-medium text-slate-300">{c.name}</p>
                <p className="text-xs text-slate-500 font-mono">{c.hex}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className="text-center text-xs text-slate-700">
        Bu sayfa şu an pasif durumdadır. Simge düzenleme yakında aktif edilecektir.
      </p>
    </div>
  );
}
