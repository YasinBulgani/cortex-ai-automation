"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";

type Project = {
  id: string;
  name: string;
  description: string;
  base_url: string;
};

export default function SettingsPage() {
  const projectId = useRouteParam("projectId");
  const router = useRouter();

  const [form, setForm] = useState<{ name: string; description: string; base_url: string }>({
    name: "",
    description: "",
    base_url: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    apiFetch<Project>(`/api/v1/tspm/projects/${projectId}`)
      .then((p) => {
        setForm({ name: p.name ?? "", description: p.description ?? "", base_url: p.base_url ?? "" });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [projectId]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}`, {
        method: "PUT",
        json: { name: form.name, description: form.description, base_url: form.base_url },
      });
      setSaveMsg({ ok: true, text: "Proje ayarları kaydedildi." });
    } catch {
      setSaveMsg({ ok: false, text: "Kaydetme başarısız. Lütfen tekrar deneyin." });
    } finally {
      setSaving(false);
    }
  }

  async function deleteProject() {
    const confirmed = window.confirm(
      `"${form.name}" projesini silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz.`
    );
    if (!confirmed) return;
    setDeleting(true);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}`, { method: "DELETE" });
      router.push("/portfolio");
    } catch {
      alert("Proje silinemedi. Lütfen tekrar deneyin.");
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto py-10 px-4">
        <p className="text-sm text-slate-400">Proje bilgileri yükleniyor…</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-10 px-4 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">Proje Ayarları</h1>
        <p className="mt-1 text-sm text-slate-400">Proje adı, açıklama ve hedef URL'yi düzenleyin.</p>
      </div>

      {/* Edit form */}
      <form onSubmit={save} className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="proj-name" className="text-sm font-medium text-white">
            Proje Adı <span className="text-red-500">*</span>
          </label>
          <input
            id="proj-name"
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            className="h-9 rounded border border-slate-800 bg-slate-900 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Örn: ARK Bankacılık"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="proj-desc" className="text-sm font-medium text-white">Açıklama</label>
          <textarea
            id="proj-desc"
            rows={3}
            value={form.description}
            onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
            className="rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Projeyle ilgili kısa bir açıklama…"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="proj-url" className="text-sm font-medium text-white">Base URL</label>
          <input
            id="proj-url"
            type="url"
            value={form.base_url}
            onChange={(e) => setForm((p) => ({ ...p, base_url: e.target.value }))}
            className="h-9 rounded border border-slate-800 bg-slate-900 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="https://uygulama.ornek.com"
          />
          <p className="text-xs text-slate-400">Test senaryoları ve otomasyon için hedef uygulama adresi.</p>
        </div>

        {saveMsg && (
          <p className={`text-sm ${saveMsg.ok ? "text-green-600" : "text-red-600"}`}>
            {saveMsg.text}
          </p>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-blue-600 px-5 py-2 text-sm font-semibold text-blue-400-fg hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {saving ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </div>
      </form>

      {/* Danger zone */}
      <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/20 p-6 space-y-3">
        <h2 className="text-sm font-semibold text-red-700 dark:text-red-400">Tehlikeli Alan</h2>
        <p className="text-sm text-red-600 dark:text-red-400">
          Bu projeyi silmek, tüm senaryo, koşu ve raporları kalıcı olarak kaldırır.
        </p>
        <button
          type="button"
          onClick={deleteProject}
          disabled={deleting}
          className="rounded border border-red-400 bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          {deleting ? "Siliniyor…" : "Projeyi Sil"}
        </button>
      </div>
    </div>
  );
}
