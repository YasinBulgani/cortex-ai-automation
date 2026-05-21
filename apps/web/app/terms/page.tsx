import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, FileCheck2, ShieldCheck } from "lucide-react";

export const metadata: Metadata = {
  title: "Kullanım Koşulları | Neurex QA",
  description: "Neurex QA çalışma alanı kullanım koşulları.",
};

const TERMS = [
  "Neurex QA çalışma alanına erişen kullanıcılar, kendilerine atanmış proje ve rol kapsamı içinde işlem yapmayı kabul eder.",
  "Test verileri, mobil cihaz kayıtları, otomasyon çıktıları ve AI önerileri yalnızca kalite güvence amacıyla kullanılmalıdır.",
  "Platform üzerindeki kritik aksiyonlar denetlenebilir kayıt üretir. Kullanıcı, kendi hesabıyla yapılan işlemlerin güvenliğinden sorumludur.",
  "Üretim sistemleri, üçüncü taraf uygulamalar ve müşteri verileri üzerinde işlem yapılırken kurumunuzun güvenlik politikaları önceliklidir.",
];

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950 dark:bg-slate-950 dark:text-white">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/login"
          className="mb-8 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:border-slate-300 hover:text-slate-950 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-slate-700 dark:hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Giriş ekranına dön
        </Link>

        <section className="rounded-lg border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/60 dark:border-slate-800 dark:bg-slate-900/90 dark:shadow-black/20">
          <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-300">
            <FileCheck2 className="h-6 w-6" />
          </div>
          <h1 className="text-3xl font-semibold tracking-normal">Kullanım Koşulları</h1>
          <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400">
            Bu koşullar, Neurex QA kalite operasyonları çalışma alanındaki hesap, proje ve kanıt
            zinciri kullanımını düzenler.
          </p>

          <div className="mt-8 space-y-4">
            {TERMS.map((item) => (
              <div key={item} className="flex gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/50">
                <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600 dark:text-emerald-300" />
                <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{item}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
