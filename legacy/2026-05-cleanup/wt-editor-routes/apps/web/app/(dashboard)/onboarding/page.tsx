"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

type ProjectOut = { id: string; name: string };

export default function OnboardingPage() {
  const router = useRouter();
  const [projName, setProjName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCreate() {
    if (!projName.trim()) {
      setError("Proje adı zorunludur.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const p = await apiFetch<ProjectOut>("/api/v1/tspm/projects", {
        method: "POST",
        json: { name: projName.trim() },
      });
      if (typeof window !== "undefined") localStorage.setItem("onboarded", "true");
      router.push(`/p/${p.id}`);
    } catch (e: unknown) {
      setError((e instanceof Error ? e.message : null) ?? "Proje oluşturulamadı.");
    } finally {
      setLoading(false);
    }
  }

  function goToProjects() {
    if (typeof window !== "undefined") localStorage.setItem("onboarded", "true");
    router.push("/projects");
  }

  return (
    <div className="min-h-screen bg-[#0d0d0f] flex flex-col items-center justify-center px-4 py-12" data-testid="onboarding-page">
      <div className="mb-8 text-center">
        <div className="text-2xl font-bold text-white tracking-tight mb-1">
          <span className="text-indigo-400">Visium</span> Operations
        </div>
        <p className="text-slate-400 text-sm">Test otomasyon platformuna hoş geldiniz</p>
      </div>

      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-8 space-y-5">
        <div>
          <h2 className="text-lg font-semibold text-white mb-1">İlk projenizi oluşturun</h2>
          <p className="text-slate-400 text-sm">Başlamak için bir proje adı girin veya mevcut projelerinize gidin.</p>
        </div>

        <div>
          <label className="text-xs text-slate-400 block mb-1">
            Proje Adı <span className="text-red-400">*</span>
          </label>
          <input
            className={`w-full rounded-xl bg-slate-800/60 border px-4 py-3 text-sm text-slate-100 outline-none placeholder-slate-500 transition-colors ${
              error ? "border-red-500 focus:border-red-400" : "border-slate-700 focus:border-indigo-500"
            }`}
            placeholder="ör. Ödeme API, Mobil Uygulama…"
            value={projName}
            onChange={(e) => { setProjName(e.target.value); setError(""); }}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            autoFocus
            data-testid="onboarding-input-name"
          />
        </div>

        {error && <p className="text-red-400 text-xs" data-testid="onboarding-error">{error}</p>}

        <button
          onClick={handleCreate}
          disabled={loading}
          data-testid="onboarding-btn-create"
          className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2"
        >
          {loading && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
          {loading ? "Oluşturuluyor…" : "Proje Oluştur"}
        </button>

        <div className="relative flex items-center gap-3">
          <div className="flex-1 h-px bg-slate-800" />
          <span className="text-xs text-slate-600">veya</span>
          <div className="flex-1 h-px bg-slate-800" />
        </div>

        <button
          onClick={goToProjects}
          data-testid="onboarding-btn-skip"
          className="w-full py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-sm transition-colors"
        >
          Projelerime Git
        </button>
      </div>
    </div>
  );
}
