"use client";

import Link from "next/link";
import { useCurrentUser } from "@/lib/hooks/use-auth";

/**
 * Admin alt alanı için rol kapısı.
 *
 * Middleware zaten login olmamış kullanıcıları yönlendiriyor; bu katman
 * ise giriş yapmış fakat admin yetkisi olmayan kullanıcılara "403" ekranı
 * göstermek için. `admin.*` permission'ı veya `admin` rolü bekler.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, hasPermission } = useCurrentUser();

  if (loading) {
    return (
      <div
        className="flex min-h-[50vh] items-center justify-center text-sm text-slate-400"
        aria-busy="true"
        aria-live="polite"
      >
        Yetki bilgisi doğrulanıyor…
      </div>
    );
  }

  const isAdmin =
    !!user && (user.roles?.includes("admin") || hasPermission("admin.*"));

  if (!isAdmin) {
    return (
      <div className="mx-auto my-16 max-w-lg rounded-2xl border border-amber-500/20 bg-amber-500/5 p-6 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-400">
          403 · Yetkisiz erişim
        </p>
        <h1 className="mt-3 text-2xl font-semibold text-white">
          Bu alana erişim yetkiniz yok
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Yönetim paneli yalnızca admin rolündeki kullanıcılar içindir.
          Erişim gerekiyorsa yöneticinizle iletişime geçin.
        </p>
        <Link
          href="/projects"
          className="mt-5 inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500"
        >
          Portföye dön
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
