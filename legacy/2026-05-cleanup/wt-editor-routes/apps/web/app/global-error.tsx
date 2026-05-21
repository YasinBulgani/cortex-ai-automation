"use client";

/**
 * Global Error Boundary — Next.js root-level hata yakalayıcı.
 * Tüm layout'ları aşan kritik hatalar için son savunma hattı.
 * Bu dosya kendi <html> ve <body> tag'lerini sağlamalıdır.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="tr">
      <body className="bg-slate-950 text-white">
        <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
          {/* Logo placeholder */}
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-red-500/30 bg-red-500/10">
            <svg
              className="h-8 w-8 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>

          <div className="text-center">
            <h1 className="text-2xl font-bold text-white mb-2">
              Uygulama Hatası
            </h1>
            <p className="text-slate-400 text-sm max-w-md">
              Beklenmedik bir hata oluştu. Sayfayı yenilemeyi veya uygulamayı
              yeniden başlatmayı deneyin.
            </p>
            {error.digest && (
              <p className="mt-2 font-mono text-xs text-slate-600">
                Hata kodu: {error.digest}
              </p>
            )}
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => reset()}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
            >
              Tekrar dene
            </button>
            <button
              type="button"
              onClick={() => (window.location.href = "/")}
              className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-2.5 text-sm font-semibold text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
            >
              Ana sayfaya dön
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
