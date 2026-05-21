import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, Database, LockKeyhole, ShieldCheck } from "lucide-react";

export const metadata: Metadata = {
  title: "Gizlilik Politikası | Neurex QA",
  description: "Neurex QA çalışma alanı gizlilik politikası.",
};

const PRIVACY_ITEMS = [
  {
    icon: LockKeyhole,
    title: "Oturum güvenliği",
    body: "Oturum yönetimi güvenli çerez modeli ve workspace kapsamı üzerinden yürütülür.",
  },
  {
    icon: Database,
    title: "Veri kapsamı",
    body: "Test çıktıları, ekran görüntüleri, cihaz kayıtları ve otomasyon kanıtları proje bağlamında saklanır.",
  },
  {
    icon: ShieldCheck,
    title: "Denetlenebilirlik",
    body: "Girişler ve kritik kalite aksiyonları operasyonel güvenlik ve izlenebilirlik için kayıt altına alınabilir.",
  },
];

export default function PrivacyPage() {
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
          <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-300">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h1 className="text-3xl font-semibold tracking-normal">Gizlilik Politikası</h1>
          <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400">
            Neurex QA, kalite operasyonlarında kullanılan veriyi proje, rol ve kanıt zinciri
            sınırları içinde ele alacak şekilde tasarlanmıştır.
          </p>

          <div className="mt-8 grid gap-4">
            {PRIVACY_ITEMS.map((item) => (
              <div key={item.title} className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/50">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
                  <item.icon className="h-4 w-4 text-indigo-600 dark:text-indigo-300" />
                  {item.title}
                </div>
                <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{item.body}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
