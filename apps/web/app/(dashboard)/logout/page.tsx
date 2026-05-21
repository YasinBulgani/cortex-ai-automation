"use client";

import { useEffect } from "react";
import Link from "next/link";
import { BgtestLogo } from "@/components/BgtestLogo";
import { clearTokens } from "@/lib/api-client";

export default function LogoutPage() {
  useEffect(() => {
    clearTokens();
  }, []);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center" data-testid="logout-page">
      <div className="w-full max-w-sm space-y-6 text-center">
        <BgtestLogo className="mx-auto h-10" />

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 backdrop-blur-sm p-8 shadow-2xl">
          <div className="mb-4 text-4xl">👋</div>
          <h1 className="text-xl font-semibold text-white">Çıkış Yapıldı</h1>
          <p className="mt-2 text-sm text-slate-400">
            Oturumunuz güvenli bir şekilde sonlandırıldı.
          </p>

          <div className="mt-6">
            <Link
              href="/"
              data-testid="logout-link-home"
              className="flex w-full items-center justify-center px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors"
              data-testid2="logout-btn-home"
            >
              Ana sayfaya dön
            </Link>
          </div>
        </div>

        <p className="text-xs text-slate-600">
          Güvenli çıkış tamamlandı.
        </p>
      </div>
    </div>
  );
}
