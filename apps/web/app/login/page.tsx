"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ShieldCheck, Bot, Mail, Lock, Eye, EyeOff,
  Sun, Moon, Brain, Database, Smartphone, ScanEye,
  CheckCircle2, User, AlertCircle, KeyRound, Fingerprint, ServerCog,
  Activity, FileCheck2,
} from "lucide-react";
import { API_BASE, ENGINE_BASE, apiFetch, setTokens, migrateToCookieAuth } from "@/lib/api-client";

// ── helpers ──────────────────────────────────────────────────────────────────

function loginErrorMessage(err: unknown): string {
  if (
    err instanceof TypeError &&
    /failed to fetch|load failed|networkerror/i.test(String(err.message))
  ) {
    const hint =
      process.env.NODE_ENV === "development"
        ? ` API: ${API_BASE}`
        : "";
    return `Sunucuya ulaşılamıyor. Backend çalışıyor mu?${hint}`;
  }
  if (err instanceof Error) return err.message;
  return "Giriş başarısız";
}

// ── sol panel verileri ───────────────────────────────────────────────────────

const TRUST_SIGNALS = [
  { icon: ShieldCheck, label: "httpOnly oturum", sub: "Tokenlar tarayıcı depolamasına yazılmaz" },
  { icon: FileCheck2,  label: "Audit trail",     sub: "Girişler ve kritik aksiyonlar izlenebilir" },
  { icon: ServerCog,   label: "On-prem ready",   sub: "Yerel AI ve kapalı ağ çalışma modeli" },
];

const PLATFORM_SIGNALS = [
  { icon: Brain,      label: "AI karar katmanı" },
  { icon: Smartphone, label: "Neurex Farm" },
  { icon: Database,   label: "Sentetik veri" },
  { icon: ScanEye,    label: "Görsel kalite" },
];

const DEV_EMAIL    = "test@test.com";
const DEV_PASSWORD = "test";
const ALLOW_SELF_REGISTRATION =
  process.env.NEXT_PUBLIC_ALLOW_SELF_REGISTRATION === "true";

// ── bileşenler ───────────────────────────────────────────────────────────────

function DarkToggle({ dark, onToggle }: { dark: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className="fixed right-4 top-4 z-50 rounded-lg border border-slate-200/80 bg-white/[0.85] p-2.5 text-slate-600 shadow-sm backdrop-blur-sm transition-colors hover:bg-white dark:border-slate-700/80 dark:bg-slate-900/[0.85] dark:text-slate-300 dark:hover:bg-slate-800"
      aria-label="Tema değiştir"
      aria-pressed={dark}
    >
      {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  );
}

function LeftPanel() {
  return (
    <aside className="relative hidden overflow-hidden border-r border-slate-200/70 bg-slate-950 text-white lg:flex lg:w-1/2 xl:w-3/5">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.22),transparent_34%),linear-gradient(135deg,rgba(15,23,42,0.94),rgba(2,6,23,1))]" />
      <div className="absolute inset-y-0 right-0 w-px bg-gradient-to-b from-transparent via-indigo-400/40 to-transparent" />

      <div className="relative z-10 flex min-h-screen w-full flex-col justify-between p-12 xl:p-14">
        <div>
          <div className="mb-14 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-indigo-300/20 bg-indigo-400/10 shadow-lg shadow-indigo-950/30">
              <Bot className="h-6 w-6 text-indigo-200" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-normal text-white">Neurex QA</h1>
              <p className="text-sm text-slate-400">Secure Quality Workspace</p>
            </div>
          </div>

          <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs font-medium text-emerald-200">
            <Fingerprint className="h-3.5 w-3.5" />
            Enterprise access boundary
          </p>

          <h2 className="max-w-2xl text-4xl font-semibold leading-tight tracking-normal text-white xl:text-5xl">
            Kalite operasyonlarınız için güvenli komuta girişi.
          </h2>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-300">
            Web, API, mobil farm ve AI destekli test kararları tek çalışma alanında toplanır. Oturum,
            proje kapsamı ve kanıt zinciri denetlenebilir kalır.
          </p>

          <div className="mt-10 grid max-w-2xl gap-3">
            {TRUST_SIGNALS.map((item) => (
              <div key={item.label} className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.04] p-4">
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-white/[0.08] text-indigo-200">
                  <item.icon className="h-[18px] w-[18px]" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{item.label}</p>
                  <p className="mt-1 text-sm leading-5 text-slate-400">{item.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-4 flex items-center gap-2 text-xs font-medium uppercase tracking-normal text-slate-500">
            <Activity className="h-4 w-4" />
            Connected quality planes
          </div>
          <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
            {PLATFORM_SIGNALS.map((item) => (
              <div key={item.label} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <item.icon className="mb-3 h-[18px] w-[18px] text-indigo-200" />
                <p className="text-sm font-medium text-slate-200">{item.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

// ── Ana sayfa içeriği ─────────────────────────────────────────────────────────

function LoginPageContent() {
  const router       = useRouter();
  const searchParams = useSearchParams();

  const [dark,          setDark]          = useState(true);
  const [tab,           setTab]           = useState<"login" | "register">("login");
  const [email,         setEmail]         = useState("");
  const [password,      setPassword]      = useState("");
  const [showPw,        setShowPw]        = useState(false);
  const [uiReady,       setUiReady]       = useState(false);
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState<string | null>(null);
  const [forgotOpen,    setForgotOpen]    = useState(false);
  const [forgotEmail,   setForgotEmail]   = useState("");
  const [forgotMsg,     setForgotMsg]     = useState<string | null>(null);
  const [forgotLoading, setForgotLoading] = useState(false);

  // kayıt state
  const [regName,        setRegName]        = useState("");
  const [regEmail,       setRegEmail]       = useState("");
  const [regPassword,    setRegPassword]    = useState("");
  const [regConfirm,     setRegConfirm]     = useState("");
  const [showRegPw,      setShowRegPw]      = useState(false);
  const [showRegConfirm, setShowRegConfirm] = useState(false);
  const [regLoading,     setRegLoading]     = useState(false);
  const [regError,       setRegError]       = useState<string | null>(null);
  const [regSuccess,     setRegSuccess]     = useState(false);

  const nextPath = searchParams?.get("next") || "/";
  const autoLogin =
    process.env.NODE_ENV === "development" &&
    searchParams?.get("autologin") === "1";

  // dark mode html sınıfı
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  useEffect(() => { setUiReady(true); }, []);

  // auto-login (dev only)
  useEffect(() => {
    if (!autoLogin) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: DEV_EMAIL, password: DEV_PASSWORD }),
          signal: AbortSignal.timeout(5000),
        });
        if (!cancelled && res.ok) {
          const data = await res.json();
          setTokens(data.access_token, data.refresh_token, data.expires_in);
          migrateToCookieAuth();  // SECURITY: eski localStorage token'larını temizle
          router.replace(nextPath);
          return;
        }
      } catch { /* show form */ }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [autoLogin, nextPath, router]);

  async function syncEngine(e: string, p: string) {
    try {
      await fetch(`${ENGINE_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: e, password: p }),
        signal: AbortSignal.timeout(3000),
      });
    } catch { /* non-critical */ }
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || body?.error || "E-posta veya şifre hatalı");
      }
      const data = await res.json();
      setTokens(data.access_token, data.refresh_token, data.expires_in);
      migrateToCookieAuth();  // SECURITY: eski localStorage token'larını temizle
      void syncEngine(email, password);
      router.replace(nextPath);
    } catch (err: unknown) {
      setError(loginErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotPassword(e: React.FormEvent) {
    e.preventDefault();
    setForgotLoading(true);
    setForgotMsg(null);
    try {
      await apiFetch("/api/v1/auth/forgot-password", {
        method: "POST",
        json: { email: forgotEmail },
      });
      setForgotMsg("Sıfırlama bağlantısı e-posta adresinize gönderildi.");
    } catch {
      setForgotMsg("İşlem başarısız. E-posta adresinizi kontrol edin.");
    } finally {
      setForgotLoading(false);
    }
  }

  // şifre güç kontrolü
  function passwordStrength(pw: string): { score: number; labels: string[] } {
    const labels: string[] = [];
    if (pw.length < 12)             labels.push("en az 12 karakter");
    if (!/[A-Z]/.test(pw))         labels.push("büyük harf");
    if (!/[a-z]/.test(pw))         labels.push("küçük harf");
    if (!/\d/.test(pw))            labels.push("rakam");
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~]/.test(pw)) labels.push("özel karakter");
    return { score: 5 - labels.length, labels };
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setRegError(null);
    if (regPassword !== regConfirm) {
      setRegError("Şifreler eşleşmiyor.");
      return;
    }
    const { labels } = passwordStrength(regPassword);
    if (labels.length > 0) {
      setRegError(`Şifre gereksinimlerini karşılamıyor: ${labels.join(", ")}.`);
      return;
    }
    setRegLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: regEmail, password: regPassword, full_name: regName }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || "Kayıt başarısız");
      }
      const data = await res.json();
      setTokens(data.access_token, data.refresh_token, data.expires_in);
      void syncEngine(regEmail, regPassword);
      router.replace(nextPath);
    } catch (err: unknown) {
      setRegError(err instanceof Error ? err.message : "Kayıt sırasında hata oluştu");
    } finally {
      setRegLoading(false);
    }
  }

  const inputBase =
    "w-full rounded-lg border border-slate-200 bg-white py-3 text-sm text-slate-950 outline-none transition-colors placeholder:text-slate-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950/50 dark:text-white dark:placeholder:text-slate-500 dark:focus:border-indigo-400 dark:focus:ring-indigo-400/10";

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-950 dark:bg-slate-950 dark:text-white" data-testid="login-page" data-ui-ready={uiReady ? "true" : "false"}>

      <DarkToggle dark={dark} onToggle={() => setDark(d => !d)} />

      <LeftPanel />

      {/* ── Sağ panel ──────────────────────────────────────────────────────── */}
      <main className="flex w-full items-center justify-center p-6 sm:p-10 lg:w-1/2 xl:w-2/5">
        <div className="w-full max-w-md">

          {/* mobil logo */}
          <div className="flex lg:hidden items-center justify-center gap-3 mb-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-950 shadow-lg dark:bg-indigo-500/15">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white" data-testid="login-logo">Neurex QA</h1>
              <p className="text-xs text-gray-500 dark:text-slate-400">Quality Operations</p>
            </div>
          </div>

          {/* kart */}
          <section className="rounded-lg border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/70 dark:border-slate-800 dark:bg-slate-900/90 dark:shadow-black/20">

            {/* başlık */}
            <div className="mb-8">
              <div className="mb-4 inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-400">
                <KeyRound className="h-3.5 w-3.5" />
                Secure workspace sign-in
              </div>
              <h2 className="text-2xl font-semibold tracking-normal text-slate-950 dark:text-white" data-testid="login-heading">
                Giriş Yap
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400" data-testid="login-subtitle">
                Proje kapsamlı kalite operasyonlarına güvenli erişim için kimlik bilgilerinizi girin.
              </p>
            </div>

            {/* sekme */}
            {ALLOW_SELF_REGISTRATION ? (
              <div className="mb-6 flex rounded-lg border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-950/60">
                <button
                  type="button"
                  onClick={() => setTab("login")}
                  data-testid="login-btn-tab-login"
                  aria-pressed={tab === "login"}
                  className={`flex-1 rounded-md py-2.5 text-sm font-medium transition-colors ${
                    tab === "login"
                      ? "bg-white text-slate-950 shadow-sm dark:bg-slate-800 dark:text-white"
                      : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
                  }`}
                >
                  Giriş Yap
                </button>
                <button
                  type="button"
                  onClick={() => setTab("register")}
                  data-testid="login-btn-tab-register"
                  aria-pressed={tab === "register"}
                  className={`flex-1 rounded-md py-2.5 text-sm font-medium transition-colors ${
                    tab === "register"
                      ? "bg-white text-slate-950 shadow-sm dark:bg-slate-800 dark:text-white"
                      : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
                  }`}
                >
                  Kayıt Ol
                </button>
              </div>
            ) : null}

            {/* ── Giriş Formu ── */}
            {tab === "login" && (
              <form onSubmit={handleLogin} className="space-y-5" data-testid="login-form">

                {/* e-posta */}
                <div>
                  <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    E-posta Adresi
                  </label>
                  <div className="relative">
                    <Mail className="lucide absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                      id="email" type="email" placeholder="you@company.com"
                      value={email} onChange={e => setEmail(e.target.value)}
                      autoComplete="email" data-testid="login-input-email"
                      disabled={!uiReady || loading}
                      className={`${inputBase} pl-12 pr-4`}
                    />
                  </div>
                </div>

                {/* şifre */}
                <div>
                  <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Şifre
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                      id="password" type={showPw ? "text" : "password"} placeholder="••••••••"
                      value={password} onChange={e => setPassword(e.target.value)}
                      autoComplete="current-password" data-testid="login-input-password"
                      disabled={!uiReady || loading}
                      className={`${inputBase} pl-12 pr-12`}
                    />
                    <button
                      type="button" onClick={() => setShowPw(v => !v)}
                      aria-label={showPw ? "Şifreyi gizle" : "Şifreyi göster"}
                      aria-pressed={showPw}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 transition-colors hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
                    >
                      {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                {/* hata */}
                {error && (
                  <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-center text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300" data-testid="login-alert-error">
                    {error}
                  </div>
                )}

                {/* submit */}
                <button
                  type="submit" disabled={!uiReady || loading} data-testid="login-btn-submit"
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-950 py-3 font-semibold text-white shadow-lg shadow-slate-200/80 transition-colors hover:bg-slate-800 disabled:opacity-50 dark:bg-indigo-500 dark:shadow-indigo-950/30 dark:hover:bg-indigo-400"
                >
                  {loading ? (
                    <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Giriş yapılıyor…</>
                  ) : "Giriş Yap"}
                </button>

                {/* şifremi unuttum */}
                <div className="flex justify-end">
                  <button
                    type="button" onClick={() => setForgotOpen(f => !f)}
                    data-testid="login-btn-forgot"
                    className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                  >
                    Şifremi Unuttum
                  </button>
                </div>

                {/* şifre sıfırlama paneli */}
                {forgotOpen && (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/50" data-testid="login-forgot-panel">
                    <h3 className="mb-1 text-sm font-semibold text-gray-900 dark:text-white">Şifre Sıfırlama</h3>
                    <p className="mb-3 text-xs text-gray-500 dark:text-slate-400">E-posta adresinize sıfırlama bağlantısı gönderilecektir.</p>
                    <form onSubmit={handleForgotPassword} className="flex flex-col gap-3">
                      <input
                        type="email" placeholder="E-posta adresiniz" value={forgotEmail}
                        onChange={e => setForgotEmail(e.target.value)} required
                        data-testid="login-input-forgot-email"
                        className={`${inputBase} px-4`}
                      />
                      <div className="flex gap-2">
                        <button type="submit" disabled={forgotLoading} data-testid="login-btn-forgot-submit"
                          className="flex-1 rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800 disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-400">
                          {forgotLoading ? "Gönderiliyor…" : "Gönder"}
                        </button>
                        <button type="button" onClick={() => setForgotOpen(false)} data-testid="login-btn-forgot-cancel"
                          className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-500 transition-colors hover:border-slate-300 hover:text-slate-700 dark:border-slate-600 dark:text-slate-400 dark:hover:border-slate-500 dark:hover:text-white">
                          İptal
                        </button>
                      </div>
                    </form>
                    {forgotMsg && <p className="mt-2 text-xs text-blue-600 dark:text-blue-400" data-testid="login-forgot-msg">{forgotMsg}</p>}
                  </div>
                )}

                {/* dev credentials */}
                {process.env.NODE_ENV === "development" &&
                  process.env.NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS === "true" && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 dark:border-amber-500/20 dark:bg-amber-500/5">
                    <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">Geliştirici modu</p>
                    <div className="mt-1 space-y-0.5 text-xs text-amber-700 dark:text-amber-500/80">
                      <p><code>test@test.com</code> / <code>test</code></p>
                      <p><code>admin@example.com</code> / <code>admin123</code></p>
                    </div>
                  </div>
                )}
              </form>
            )}

            {/* ── Kayıt Formu ── */}
            {tab === "register" && !regSuccess && (
              <form onSubmit={handleRegister} className="space-y-4" data-testid="register-form">

                {/* ad soyad */}
                <div>
                  <label htmlFor="register-name" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Ad Soyad
                  </label>
                  <div className="relative">
                    <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                      id="register-name" type="text" placeholder="Ad Soyad"
                      value={regName} onChange={e => setRegName(e.target.value)}
                      autoComplete="name" disabled={regLoading}
                      className={`${inputBase} pl-12 pr-4`}
                    />
                  </div>
                </div>

                {/* e-posta */}
                <div>
                  <label htmlFor="register-email" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    E-posta Adresi
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                      id="register-email" type="email" placeholder="you@company.com"
                      value={regEmail} onChange={e => setRegEmail(e.target.value)}
                      autoComplete="email" required disabled={regLoading}
                      className={`${inputBase} pl-12 pr-4`}
                    />
                  </div>
                </div>

                {/* şifre */}
                <div>
                  <label htmlFor="register-password" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Şifre
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                      id="register-password" type={showRegPw ? "text" : "password"} placeholder="En az 12 karakter"
                      value={regPassword} onChange={e => setRegPassword(e.target.value)}
                      autoComplete="new-password" required disabled={regLoading}
                      className={`${inputBase} pl-12 pr-12`}
                    />
                    <button type="button" onClick={() => setShowRegPw(v => !v)}
                      aria-label={showRegPw ? "Şifreyi gizle" : "Şifreyi göster"}
                      aria-pressed={showRegPw}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 transition-colors hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300">
                      {showRegPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {/* güç göstergesi */}
                  {regPassword.length > 0 && (() => {
                    const { score, labels } = passwordStrength(regPassword);
                    const colors = ["bg-red-500", "bg-red-400", "bg-amber-400", "bg-yellow-400", "bg-emerald-400", "bg-emerald-500"];
                    return (
                      <div className="mt-2 space-y-1">
                        <div className="flex gap-1">
                          {[0,1,2,3,4].map(i => (
                            <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i < score ? colors[score] : "bg-gray-200 dark:bg-slate-600"}`} />
                          ))}
                        </div>
                        {labels.length > 0 && (
                          <p className="text-xs text-gray-400 dark:text-slate-500">Eksik: {labels.join(", ")}</p>
                        )}
                      </div>
                    );
                  })()}
                </div>

                {/* şifre tekrar */}
                <div>
                  <label htmlFor="register-confirm" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Şifre Tekrar
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                      id="register-confirm" type={showRegConfirm ? "text" : "password"} placeholder="Şifrenizi tekrar girin"
                      value={regConfirm} onChange={e => setRegConfirm(e.target.value)}
                      autoComplete="new-password" required disabled={regLoading}
                      className={`${inputBase} pl-12 pr-12`}
                    />
                    <button type="button" onClick={() => setShowRegConfirm(v => !v)}
                      aria-label={showRegConfirm ? "Şifreyi gizle" : "Şifreyi göster"}
                      aria-pressed={showRegConfirm}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 transition-colors hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300">
                      {showRegConfirm ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {regConfirm.length > 0 && regPassword !== regConfirm && (
                    <p className="mt-1 text-xs text-red-500">Şifreler eşleşmiyor</p>
                  )}
                </div>

                {/* hata */}
                {regError && (
                  <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>{regError}</span>
                  </div>
                )}

                {/* submit */}
                <button
                  type="submit" disabled={regLoading || !regEmail || !regPassword || !regConfirm}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-950 py-3 font-semibold text-white shadow-lg shadow-slate-200/80 transition-colors hover:bg-slate-800 disabled:opacity-50 dark:bg-indigo-500 dark:shadow-indigo-950/30 dark:hover:bg-indigo-400"
                >
                  {regLoading
                    ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Hesap oluşturuluyor…</>
                    : "Hesap Oluştur"}
                </button>
              </form>
            )}

            {/* ── Kayıt Başarı ── */}
            {tab === "register" && regSuccess && (
              <div className="space-y-4 py-4 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-lg bg-emerald-500 shadow-lg">
                  <CheckCircle2 className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-slate-950 dark:text-white">Hesap Oluşturuldu!</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Platforma yönlendiriliyorsunuz…</p>
              </div>
            )}

            {/* güven bandı — sadece login sekmesinde */}
            {tab === "login" && (
              <div className="my-6 grid grid-cols-3 gap-2 rounded-lg border border-slate-200 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-950/50">
                {["httpOnly session", "Audit logged", "Workspace scoped"].map((item) => (
                  <div key={item} className="rounded-md bg-white px-2 py-2 text-center text-[11px] font-medium text-slate-500 dark:bg-slate-900 dark:text-slate-400">
                    {item}
                  </div>
                ))}
              </div>
            )}

            {!ALLOW_SELF_REGISTRATION && (
              <p className="mb-4 text-center text-xs text-slate-500 dark:text-slate-400">
                Hesabınız yoksa workspace yöneticinizden davet isteyin.
              </p>
            )}

            {/* şartlar */}
            <p className="text-center text-xs text-slate-500 dark:text-slate-400" data-testid="login-text-register">
              Devam ederek,{" "}
              <Link href="/terms" className="font-medium text-indigo-600 hover:underline dark:text-indigo-300">Kullanım Koşulları</Link>
              {" "}ve{" "}
              <Link href="/privacy" className="font-medium text-indigo-600 hover:underline dark:text-indigo-300">Gizlilik Politikası</Link>
              'nı kabul etmiş olursunuz.
            </p>

            {/* footer */}
            <p className="mt-6 text-center text-xs text-slate-400 dark:text-slate-500" data-testid="login-footer">
              Neurex QA Operations · Secure Quality Workspace
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}

function LoginPageFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400 text-sm">
      Giriş ekranı hazırlanıyor…
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginPageFallback />}>
      <LoginPageContent />
    </Suspense>
  );
}
