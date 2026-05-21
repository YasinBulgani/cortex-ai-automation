"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BgtestLogo } from "@/components/BgtestLogo";
import { API_BASE } from "@/lib/api-client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || body?.error || "E-posta veya şifre hatalı");
      }
      router.replace("/projects");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Giriş başarısız");
    } finally {
      setLoading(false);
    }
  }

  const inputCls =
    "w-full rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/60 focus:bg-slate-800 transition-colors";

  return (
    <div
      className="flex min-h-screen items-center justify-center bg-slate-950 px-4"
      data-testid="login-page"
    >
      <div className="w-full max-w-md flex flex-col gap-6">
        <div className="flex flex-col items-center gap-3">
          <BgtestLogo className="h-12" data-testid="login-logo" />
          <p className="text-sm text-slate-400" data-testid="login-subtitle">
            Visium Product Family Access
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-900/70 backdrop-blur-xl p-8 shadow-2xl ring-1 ring-white/5">
          <h1
            className="mb-6 text-center text-xl font-bold text-white"
            data-testid="login-heading"
          >
            Giriş Yap
          </h1>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4" data-testid="login-form">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-sm font-medium text-slate-300">
                E-posta
              </label>
              <input
                id="email"
                type="email"
                placeholder="ornek@sirket.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                data-testid="login-input-email"
                disabled={loading}
                className={inputCls}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-sm font-medium text-slate-300">
                Şifre
              </label>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                data-testid="login-input-password"
                disabled={loading}
                className={inputCls}
              />
            </div>

            {error && (
              <div
                className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300 text-center"
                data-testid="login-alert-error"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              data-testid="login-btn-submit"
              className="flex items-center justify-center gap-2 w-full px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50 mt-1"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Giriş yapılıyor…
                </>
              ) : (
                "Giriş Yap"
              )}
            </button>
          </form>

          <div className="mt-6 border-t border-slate-800 pt-4">
            <p className="text-center text-xs text-slate-500" data-testid="login-text-register">
              Hesabınız yok mu?{" "}
              <span className="text-blue-400" data-testid="login-btn-register">
                Yöneticinizle iletişime geçin
              </span>
            </p>
          </div>
        </div>

        <p className="text-center text-xs text-slate-700" data-testid="login-footer">
          © {new Date().getFullYear()} Visium · Visium Operations
        </p>
      </div>
    </div>
  );
}
