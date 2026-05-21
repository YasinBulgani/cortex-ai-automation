"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// ─── Types ───────────────────────────────────────────────────────────────────

type Feature = {
  name: string;
  content?: string;
  path: string;
  updated_at?: string | null;
};

type FeatureTreeItem = {
  type: "file" | "folder";
  name: string;
  path: string;
  modified?: string;
  children?: FeatureTreeItem[];
};

type CreateFeatureForm = {
  name: string;
  content: string;
};

// ─── Constants ───────────────────────────────────────────────────────────────

const PROXY = "/api/v1/automation/proxy/api/features";

const GHERKIN_PLACEHOLDER = `Feature: Örnek özellik
  Senaryo olarak kullanıcı

  Scenario: Kullanıcı başarıyla giriş yapar
    Given kullanıcı login sayfasındadır
    When kullanıcı e-posta ve şifre girer
    And "Giriş Yap" butonuna tıklar
    Then anasayfaya yönlendirilir`;

function ensureFeatureFilename(name: string): string {
  const trimmed = name.trim().replace(/^\/+/, "");
  if (!trimmed) return "";
  return trimmed.endsWith(".feature") ? trimmed : `${trimmed}.feature`;
}

function flattenFeatureTree(items: FeatureTreeItem[]): Feature[] {
  const result: Feature[] = [];

  for (const item of items) {
    if (item.type === "file") {
      result.push({
        name: item.name,
        path: item.path,
        updated_at: item.modified ?? null,
      });
      continue;
    }

    if (item.children?.length) {
      result.push(...flattenFeatureTree(item.children));
    }
  }

  return result;
}

// ─── Create Modal ─────────────────────────────────────────────────────────────

function CreateFeatureModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<CreateFeatureForm>({ name: "", content: "" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const filename = ensureFeatureFilename(form.name);
    if (!filename) return;
    setErr(null);
    setSaving(true);
    try {
      await apiFetch(`${PROXY}/${filename}`, {
        method: "PUT",
        json: { content: form.content.trim() },
      });
      onCreated();
      onClose();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata oluştu");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      data-testid="automation-create-modal"
    >
      <div className="w-full max-w-xl rounded-lg border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Yeni Feature Dosyası</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded opacity-70 hover:opacity-100 focus:outline-none"
            aria-label="Kapat"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" data-testid="automation-create-form">
          <div className="space-y-1">
            <label className="text-xs text-slate-400">Dosya adı *</label>
            <Input
              ref={nameRef}
              placeholder="ör. login.feature"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              data-testid="automation-input-name"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-slate-400">Gherkin içeriği</label>
            <textarea
              placeholder={GHERKIN_PLACEHOLDER}
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              rows={10}
              className="flex w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 font-mono text-xs text-white placeholder:text-slate-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent resize-y"
              data-testid="automation-textarea-content"
            />
          </div>
          {err && (
            <p className="text-sm text-red-600" data-testid="automation-create-error">
              {err}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              İptal
            </Button>
            <Button
              type="submit"
              disabled={saving}
              data-testid="automation-btn-save"
            >
              {saving ? "Kaydediliyor…" : "Oluştur"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AutomationPage() {
  const projectId = useRouteParam("projectId");

  const [features, setFeatures] = useState<Feature[]>([]);
  const [selected, setSelected] = useState<Feature | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<FeatureTreeItem[]>(PROXY);
      setFeatures(flattenFeatureTree(data ?? []));
    } catch {
      setFeatures([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (feature: Feature) => {
    // Fetch fresh detail in case content is not included in list response
    setEditMode(false);
    setSaveErr(null);
    try {
      const detail = await apiFetch<{ name: string; content: string }>(`${PROXY}/${feature.path}`);
      setSelected({ ...feature, content: detail.content });
    } catch {
      setSelected(feature);
    }
  }, []);

  async function handleSaveEdit() {
    if (!selected) return;
    setSaving(true);
    setSaveErr(null);
    try {
      await apiFetch(`${PROXY}/${selected.path}`, {
        method: "PUT",
        json: { content: editContent },
      });
      setSelected({ ...selected, content: editContent });
      setEditMode(false);
      await load();
    } catch (e: unknown) {
      setSaveErr(e instanceof Error ? e.message : "Kaydetme hatası");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    load();
  }, [load]);

  // Auto-select first item when list loads
  useEffect(() => {
    if (!loading && features.length > 0 && !selected) {
      void loadDetail(features[0]);
    }
    if (!loading && features.length === 0) {
      setSelected(null);
    }
  }, [loading, features, selected, loadDetail]);

  async function handleDelete(path: string) {
    setDeleting(path);
    try {
      await apiFetch(`${PROXY}/${path}`, { method: "DELETE" });
      if (selected?.path === path) setSelected(null);
      await load();
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4" data-testid="automation-page">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1
            className="text-2xl font-semibold tracking-tight"
            data-testid="automation-heading"
          >
            Otomasyonlar
          </h1>
          <p className="text-sm text-slate-400">
            Gherkin feature dosyalarını yönet ve Playwright testleri çalıştır
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link href={`/p/${projectId}/scenarios/generate`}>
            <Button
              type="button"
              variant="secondary"
              data-testid="automation-btn-ai-generate"
            >
              AI ile Oluştur
            </Button>
          </Link>
          <Button
            type="button"
            onClick={() => setShowCreate(true)}
            data-testid="automation-btn-new"
          >
            + Yeni Feature
          </Button>
          <Link href={`/p/${projectId}/executions/new`}>
            <Button
              type="button"
              variant="secondary"
              data-testid="automation-btn-run"
            >
              Test Koşusu Başlat
            </Button>
          </Link>
        </div>
      </div>

      {/* Body: two-column layout */}
      {loading ? (
        <div
          className="py-16 text-center text-sm text-slate-400"
          data-testid="automation-loading"
        >
          Yükleniyor…
        </div>
      ) : features.length === 0 ? (
        <div
          className="rounded-xl border border-dashed border-slate-800 py-16 text-center"
          data-testid="automation-empty"
        >
          <p className="text-sm text-slate-400">Henüz feature dosyası oluşturulmadı.</p>
          <Button
            type="button"
            className="mt-4"
            onClick={() => setShowCreate(true)}
            data-testid="automation-btn-empty-new"
          >
            İlk feature dosyasını oluştur
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
          {/* Left panel: file list */}
          <aside
            className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden"
            data-testid="automation-file-list"
          >
            <div className="border-b border-slate-800 px-3 py-2.5">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                Feature Dosyaları ({features.length})
              </span>
            </div>
            <ul className="divide-y divide-border">
              {features.map((feature) => {
                const isActive = selected?.path === feature.path;
                return (
                  <li key={feature.path}>
                    <div
                      className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer transition-colors ${
                        isActive
                          ? "bg-blue-500/10 text-white"
                          : "hover:bg-black/[0.03] dark:hover:bg-white/[0.05] text-white"
                      }`}
                      onClick={() => loadDetail(feature)}
                      data-testid={`automation-file-item-${feature.path.replaceAll("/", "_")}`}
                    >
                      <svg
                        className="h-4 w-4 shrink-0 text-slate-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{feature.name}</p>
                        {feature.updated_at && (
                          <p className="text-xs text-slate-400">{feature.updated_at}</p>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(feature.path);
                        }}
                        disabled={deleting === feature.path}
                        className="shrink-0 rounded p-1 text-slate-400 opacity-0 group-hover:opacity-100 hover:text-red-600 disabled:opacity-50 transition-opacity"
                        aria-label={`${feature.name} sil`}
                        data-testid={`automation-delete-${feature.path.replaceAll("/", "_")}`}
                      >
                        {deleting === feature.path ? (
                          <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                        ) : (
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </aside>

          {/* Right panel: content viewer */}
          <div
            className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden"
            data-testid="automation-content-panel"
          >
            {selected ? (
              <>
                <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <svg
                      className="h-4 w-4 text-slate-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <span
                      className="text-sm font-medium"
                      data-testid="automation-selected-name"
                    >
                      {selected.name}
                    </span>
                    {selected.path && (
                      <span className="text-xs text-slate-400 font-mono">{selected.path}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {selected.updated_at && !editMode && (
                      <span className="text-xs text-slate-400">
                        Son güncelleme: {selected.updated_at}
                      </span>
                    )}
                    {!editMode ? (
                      <button
                        type="button"
                        onClick={() => { setEditContent(selected.content ?? ""); setEditMode(true); setSaveErr(null); }}
                        className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
                        data-testid="automation-btn-edit"
                      >
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        Düzenle
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        {saveErr && <span className="text-xs text-red-400">{saveErr}</span>}
                        <button
                          type="button"
                          onClick={() => { setEditMode(false); setSaveErr(null); }}
                          disabled={saving}
                          className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                        >
                          İptal
                        </button>
                        <button
                          type="button"
                          onClick={handleSaveEdit}
                          disabled={saving}
                          className="rounded-lg bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50"
                          data-testid="automation-btn-save-edit"
                        >
                          {saving ? "Kaydediliyor…" : "Kaydet"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                <div className="overflow-auto p-4" data-testid="automation-content-viewer">
                  {editMode ? (
                    <textarea
                      value={editContent}
                      onChange={e => setEditContent(e.target.value)}
                      className="w-full font-mono text-xs text-white bg-slate-950 border border-slate-700 rounded-lg p-3 focus:outline-none focus:border-blue-500 resize-none leading-relaxed"
                      style={{ minHeight: 400 }}
                      data-testid="automation-textarea-edit"
                      autoFocus
                    />
                  ) : (
                    <pre className="font-mono text-xs text-white leading-relaxed whitespace-pre-wrap break-words">
                      {selected.content || (
                        <span className="text-slate-400 italic">İçerik yok.</span>
                      )}
                    </pre>
                  )}
                </div>
              </>
            ) : (
              <div
                className="flex h-64 items-center justify-center"
                data-testid="automation-no-selection"
              >
                <p className="text-sm text-slate-400">Görüntülemek için bir dosya seçin.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <CreateFeatureModal
          onClose={() => setShowCreate(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}
