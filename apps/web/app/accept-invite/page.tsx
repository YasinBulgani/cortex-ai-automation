"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bot, Lock, Mail, CheckCircle2, XCircle } from "lucide-react";
import { API_BASE } from "@/lib/api-client";

const inputBase =
  "w-full py-3 px-4 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-gray-900 dark:text-white text-sm";

function AcceptInviteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams?.get("token") ?? "";

  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-slate-950">
        <div className="text-center text-slate-300">
          <XCircle className="w-12 h-12 mx-auto text-red-400 mb-3" />
          <h1 className="text-xl font-semibold">Gecersiz davet baglantisi</h1>
          <p className="text-sm text-slate-500 mt-2">Token eksik veya hatali.</p>
        </div>
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMessage("");
    if (password !== confirm) {
      setStatus("error");
      setMessage("Sifreler uyusmuyor.");
      return;
    }
    if (password.length < 8) {
      setStatus("error");
      setMessage("Sifre en az 8 karakter olmali.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/organizations/invitations/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, full_name: fullName || undefined, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Davet kabul edilemedi");
      }
      setStatus("success");
      setMessage("Davetiniz kabul edildi. Giris sayfasina yonlendiriliyorsunuz...");
      setTimeout(() => router.push("/login"), 1800);
    } catch (e) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Bir hata olustu.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="w-full max-w-md bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-600/20 mb-3">
            <Bot className="w-7 h-7 text-blue-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Ekibe Katil</h1>
          <p className="text-sm text-slate-400 mt-1">Hesabini olusturup ekibe katil.</p>
        </div>

        {status === "success" ? (
          <div className="text-center py-6">
            <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-400 mb-3" />
            <p className="text-emerald-400">{message}</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="accept-invite-form">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                <Mail className="inline w-3.5 h-3.5 mr-1" /> Ad Soyad (opsiyonel)
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={inputBase}
                placeholder="Adiniz Soyadiniz"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                <Lock className="inline w-3.5 h-3.5 mr-1" /> Sifre
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className={inputBase}
                data-testid="accept-invite-input-password"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Sifre Tekrar
              </label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={8}
                className={inputBase}
                data-testid="accept-invite-input-confirm"
              />
            </div>

            {status === "error" && (
              <p className="text-sm text-red-400 flex items-center gap-2">
                <XCircle className="w-4 h-4" />
                {message}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              data-testid="accept-invite-btn-submit"
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors"
            >
              {loading ? "Isleniyor..." : "Daveti Kabul Et"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950" />}>
      <AcceptInviteContent />
    </Suspense>
  );
}
