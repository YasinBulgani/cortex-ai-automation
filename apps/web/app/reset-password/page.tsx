"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bot, Lock, Eye, EyeOff, CheckCircle2, XCircle } from "lucide-react";
import { API_BASE } from "@/lib/api-client";

const inputBase =
  "w-full py-3 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-xl focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 transition-all text-sm";

function ResetPasswordContent() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const token        = searchParams?.get("token") ?? "";

  const [password,    setPassword]    = useState("");
  const [confirm,     setConfirm]     = useState("");
  const [showPw,      setShowPw]      = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading,     setLoading]     = useState(false);
  const [status,      setStatus]      = useState<"idle" | "success" | "error">("idle");
  const [message,     setMessage]     = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Geçersiz veya eksik sıfırlama bağlantısı.");
    }
  }, [token]);

  const passwordsMatch = password === confirm;
  const isValid = password.length >= 8 && passwordsMatch;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || "İşlem başarısız");
      }
      setStatus("success");
      setMessage("Şifreniz başarıyla sıfırlandı. Giriş sayfasına yönlendiriliyorsunuz…");
      setTimeout(() => router.push("/login"), 2500);
    } catch (err: unknown) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Bir hata oluştu");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950 flex items-center justify-center p-6">
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-xl">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Neurex QA</h1>
            <p className="text-xs text-gray-500 dark:text-slate-400">Quality Operations</p>
          </div>
        </div>

        {/* Kart */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl dark:shadow-2xl dark:shadow-black/20 border border-gray-100 dark:border-slate-700 p-8">

          {/* Başarı */}
          {status === "success" && (
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-green-500 rounded-2xl flex items-center justify-center mx-auto shadow-lg">
                <CheckCircle2 className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Şifre Sıfırlandı</h2>
              <p className="text-sm text-gray-500 dark:text-slate-400">{message}</p>
            </div>
          )}

          {/* Hata (token geçersiz) */}
          {status === "error" && (
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-gradient-to-br from-red-500 to-rose-500 rounded-2xl flex items-center justify-center mx-auto shadow-lg">
                <XCircle className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Geçersiz Bağlantı</h2>
              <p className="text-sm text-gray-500 dark:text-slate-400">{message}</p>
              <button
                onClick={() => router.push("/login")}
                className="w-full bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-700 hover:via-indigo-700 hover:to-purple-700 text-white font-semibold py-3 rounded-xl transition-all shadow-lg"
              >
                Giriş Sayfasına Dön
              </button>
            </div>
          )}

          {/* Form */}
          {status === "idle" && (
            <>
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Yeni Şifre Belirle</h2>
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  En az 8 karakter içeren güçlü bir şifre seçin.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Yeni şifre */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                    Yeni Şifre
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                      type={showPw ? "text" : "password"}
                      placeholder="En az 8 karakter"
                      value={password} onChange={e => setPassword(e.target.value)}
                      disabled={loading}
                      className={`${inputBase} pl-12 pr-12`}
                    />
                    <button
                      type="button" onClick={() => setShowPw(v => !v)} tabIndex={-1}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
                    >
                      {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {password.length > 0 && password.length < 8 && (
                    <p className="mt-1 text-xs text-red-500">En az 8 karakter gerekli</p>
                  )}
                </div>

                {/* Şifre tekrar */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                    Şifre Tekrar
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                      type={showConfirm ? "text" : "password"}
                      placeholder="Şifrenizi tekrar girin"
                      value={confirm} onChange={e => setConfirm(e.target.value)}
                      disabled={loading}
                      className={`${inputBase} pl-12 pr-12`}
                    />
                    <button
                      type="button" onClick={() => setShowConfirm(v => !v)} tabIndex={-1}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
                    >
                      {showConfirm ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {confirm.length > 0 && !passwordsMatch && (
                    <p className="mt-1 text-xs text-red-500">Şifreler eşleşmiyor</p>
                  )}
                </div>

                <button
                  type="submit" disabled={!isValid || loading}
                  className="w-full bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-700 hover:via-indigo-700 hover:to-purple-700 text-white font-semibold py-3 rounded-xl transition-all shadow-lg hover:shadow-xl disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading
                    ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Sıfırlanıyor…</>
                    : "Şifreyi Sıfırla"}
                </button>

                <div className="text-center">
                  <button
                    type="button" onClick={() => router.push("/login")}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                  >
                    ← Giriş sayfasına dön
                  </button>
                </div>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-xs text-gray-400 dark:text-slate-500 mt-6">
          Neurex QA Platform v1.0 — Powered by Anthropic Claude
        </p>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400 text-sm">
        Yükleniyor…
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  );
}
