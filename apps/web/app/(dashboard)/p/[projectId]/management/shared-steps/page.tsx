"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  useSharedSteps,
  useCreateSharedStep,
  useUpdateSharedStep,
  useDeleteSharedStep,
  type SharedStep,
  type SharedStepItem,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { useToast } from "@/lib/useToast";
import { useProjectRole } from "@/lib/hooks/use-management-role";

// ── Empty State ───────────────────────────────────────────────────────────────
function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-border bg-surface-overlay">
        <svg className="h-8 w-8 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
      </div>
      <div>
        <p className="text-[14px] font-semibold text-fg">Henüz paylaşılan adım yok</p>
        <p className="mt-1 text-[12px] text-fg-subtle max-w-xs">Birden fazla test senaryosunda tekrar eden adımları şablon olarak kaydedin.</p>
      </div>
      <Button
        type="button"
        onClick={onNew}
        variant="primary"
        size="default"
        className="gap-2 rounded-xl"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>
        İlk şablonu oluştur
      </Button>
    </div>
  );
}

// ── Step Editor Row ───────────────────────────────────────────────────────────
function StepEditorRow({
  step, index, onChange, onRemove,
}: {
  step: SharedStepItem; index: number;
  onChange: (idx: number, field: keyof SharedStepItem, val: string | boolean) => void;
  onRemove: (idx: number) => void;
}) {
  return (
    <div className="group flex gap-2 rounded-lg border border-border bg-surface-overlay p-3">
      <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-raised text-[10px] font-semibold text-fg-muted">
        {index + 1}
      </span>
      <div className="flex flex-1 flex-col gap-2 min-w-0">
        <input
          value={step.action}
          onChange={e => onChange(index, "action", e.target.value)}
          placeholder="Adım aksiyonu…"
          className="w-full rounded-lg border border-border bg-surface-raised px-2.5 py-1.5 text-[12px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
        />
        <input
          value={step.expected_result}
          onChange={e => onChange(index, "expected_result", e.target.value)}
          placeholder="Beklenen sonuç…"
          className="w-full rounded-lg border border-border bg-surface-raised px-2.5 py-1.5 text-[12px] text-fg-muted placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
        />
      </div>
      <button
        type="button"
        onClick={() => onRemove(index)}
        className="mt-1 shrink-0 rounded p-1 text-fg-subtle opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>
  );
}

// ── Step Template Card ────────────────────────────────────────────────────────
function SharedStepCard({
  ss, onEdit, onDelete, isDeleting,
}: {
  ss: SharedStep; onEdit?: (s: SharedStep) => void; onDelete?: (id: string) => void; isDeleting?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <button
          type="button"
          onClick={() => setExpanded(v => !v)}
          className="flex flex-1 items-center gap-3 text-left min-w-0"
        >
          <svg className={cn("h-3.5 w-3.5 shrink-0 text-fg-subtle transition-transform", expanded && "rotate-90")}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6"/>
          </svg>
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-fg truncate">{ss.name}</p>
            {ss.description && <p className="text-[11px] text-fg-subtle truncate">{ss.description}</p>}
          </div>
          <div className="flex items-center gap-2 ml-auto shrink-0">
            {ss.tags.slice(0, 3).map(t => (
              <span key={t} className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-subtle">{t}</span>
            ))}
            <span className="text-[11px] text-fg-subtle">{ss.steps.length} adım</span>
            <span className="text-[10px] text-fg-disabled">{ss.usage_count}× kullanım</span>
          </div>
        </button>
        {onEdit && (
          <button
            type="button"
            onClick={() => onEdit(ss)}
            className="shrink-0 rounded-md p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors"
            title="Düzenle"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
            </svg>
          </button>
        )}
        {onDelete && (
          <button
            type="button"
            onClick={() => !isDeleting && onDelete(ss.id)}
            disabled={isDeleting}
            className="shrink-0 rounded-md p-1.5 text-fg-subtle hover:bg-red-500/10 hover:text-red-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={isDeleting ? "Siliniyor…" : "Sil"}
          >
            {isDeleting ? (
              <span className="h-3.5 w-3.5 block rounded-full border-2 border-red-400 border-t-transparent animate-spin" />
            ) : (
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            )}
          </button>
        )}
      </div>
      {expanded && (
        <div className="border-t border-border/50 px-4 py-3 space-y-2">
          {ss.steps.map((s, i) => (
            <div key={i} className="flex gap-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-overlay text-[10px] font-semibold text-fg-muted">{i + 1}</span>
              <div className="min-w-0">
                <p className="text-[12px] text-fg">{s.action}</p>
                {s.expected_result && <p className="text-[11px] text-fg-subtle mt-0.5">{s.expected_result}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Form Modal ────────────────────────────────────────────────────────────────
function SharedStepModal({
  initial, onSave, onClose, saving,
}: {
  initial?: SharedStep;
  onSave: (data: { name: string; description: string; steps: SharedStepItem[]; tags: string[] }) => void;
  onClose: () => void;
  saving: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [tagInput, setTagInput] = useState(initial?.tags.join(", ") ?? "");
  const [steps, setSteps] = useState<SharedStepItem[]>(
    initial?.steps ?? [{ step_no: 1, action: "", expected_result: "", is_required: true }]
  );

  const addStep = () => setSteps(p => [...p, { step_no: p.length + 1, action: "", expected_result: "", is_required: true }]);
  const removeStep = (i: number) => setSteps(p => p.filter((_, idx) => idx !== i).map((s, idx) => ({ ...s, step_no: idx + 1 })));
  const changeStep = (i: number, field: keyof SharedStepItem, val: string | boolean) =>
    setSteps(p => p.map((s, idx) => idx === i ? { ...s, [field]: val } : s));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const tags = tagInput.split(",").map(t => t.trim()).filter(Boolean);
    onSave({ name: name.trim(), description: description.trim(), steps, tags });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-6 bg-black/70 backdrop-blur-sm">
      <div className="relative flex max-h-[88vh] w-full max-w-lg flex-col rounded-2xl border border-border bg-surface-raised shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-[14px] font-semibold text-fg">{initial ? "Şablonu Düzenle" : "Yeni Paylaşılan Adım Şablonu"}</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 overflow-y-auto p-5">
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">Şablon Adı *</label>
            <input autoFocus value={name} onChange={e => setName(e.target.value)} required
              className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
              placeholder="ör. Kullanıcı girişi adımları" />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">Açıklama</label>
            <input value={description} onChange={e => setDescription(e.target.value)}
              className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
              placeholder="Ne zaman kullanılmalı?" />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">Etiketler (virgülle ayır)</label>
            <input value={tagInput} onChange={e => setTagInput(e.target.value)}
              className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
              placeholder="auth, login, smoke" />
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-[11px] font-medium text-fg-muted">Adımlar</label>
              <button type="button" onClick={addStep}
                className="flex items-center gap-1 text-[11px] text-brand hover:text-brand-secondary transition-colors">
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>
                Adım Ekle
              </button>
            </div>
            <div className="space-y-2">
              {steps.map((s, i) => (
                <StepEditorRow key={i} step={s} index={i} onChange={changeStep} onRemove={removeStep} />
              ))}
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <Button type="submit" variant="primary" size="default" disabled={saving || !name.trim()}
              className="flex-1 rounded-xl">
              {saving ? "Kaydediliyor…" : (initial ? "Güncelle" : "Oluştur")}
            </Button>
            <Button type="button" onClick={onClose} variant="outline" size="default"
              className="rounded-xl">
              İptal
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

type SortKey = "usage" | "name" | "steps" | "newest";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "usage",  label: "Kullanım (çok→az)" },
  { key: "name",   label: "Ad (A→Z)" },
  { key: "steps",  label: "Adım sayısı" },
  { key: "newest", label: "En yeni" },
];

// ── Page ──────────────────────────────────────────────────────────────────────
export default function SharedStepsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);
  const currentRole = useProjectRole(projectId ?? "");
  const canEdit = currentRole === "owner" || currentRole === "admin" || currentRole === "member";

  const { data: steps = [], isLoading, isError, refetch } = useSharedSteps(mpid || undefined);
  const create = useCreateSharedStep(mpid || "");
  const update = useUpdateSharedStep(mpid || "");
  const del = useDeleteSharedStep(mpid || "");

  const toast = useToast();

  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<SharedStep | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("usage");
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Collect all unique tags from all templates
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    for (const s of steps) s.tags.forEach(t => tagSet.add(t));
    return Array.from(tagSet).sort();
  }, [steps]);

  // Summary stats
  const totalUsage = useMemo(() => steps.reduce((acc, s) => acc + (s.usage_count ?? 0), 0), [steps]);
  const totalStepCount = useMemo(() => steps.reduce((acc, s) => acc + s.steps.length, 0), [steps]);

  const filtered = useMemo(() => {
    let list = steps.filter(s => {
      const q = search.trim().toLowerCase();
      const matchesSearch = !q || s.name.toLowerCase().includes(q) ||
        s.description?.toLowerCase().includes(q) ||
        s.tags.some(t => t.toLowerCase().includes(q));
      const matchesTag = !activeTag || s.tags.includes(activeTag);
      return matchesSearch && matchesTag;
    });
    switch (sortKey) {
      case "usage":  list = [...list].sort((a, b) => (b.usage_count ?? 0) - (a.usage_count ?? 0)); break;
      case "name":   list = [...list].sort((a, b) => a.name.localeCompare(b.name, "tr")); break;
      case "steps":  list = [...list].sort((a, b) => b.steps.length - a.steps.length); break;
      case "newest": list = [...list].sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? "")); break;
    }
    return list;
  }, [steps, search, activeTag, sortKey]);

  const handleSave = async (data: { name: string; description: string; steps: SharedStepItem[]; tags: string[] }) => {
    setSaving(true);
    try {
      if (editing) {
        await update.mutateAsync({ id: editing.id, ...data });
        toast.success("Şablon güncellendi");
      } else {
        await create.mutateAsync(data);
        toast.success("Şablon oluşturuldu");
      }
      setShowModal(false);
      setEditing(null);
    } catch (err: unknown) {
      console.error("[SharedSteps] Save failed:", err);
      toast.error("Adım şablonu kaydedilemedi");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRequest = (id: string) => {
    setConfirmDeleteId(id);
  };

  const handleDeleteConfirm = async () => {
    if (!confirmDeleteId) return;
    const id = confirmDeleteId;
    setConfirmDeleteId(null);
    setDeletingId(id);
    try {
      await del.mutateAsync(id);
      toast.success("Şablon silindi");
    } catch (err: unknown) {
      console.error("[SharedSteps] Delete failed:", err);
      toast.error("Adım şablonu silinemedi");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="flex flex-col min-h-0 flex-1">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border bg-surface-base px-6 py-4 shrink-0">
        <div>
          <h1 className="text-[15px] font-semibold text-fg">Paylaşılan Adımlar</h1>
          <p className="mt-0.5 text-[12px] text-fg-subtle">
            Birden fazla test senaryosunda kullanılabilen yeniden kullanılabilir adım şablonları
          </p>
        </div>
        {canEdit && (
          <Button
            type="button"
            onClick={() => { setEditing(null); setShowModal(true); }}
            variant="primary"
            size="default"
            className="gap-2 rounded-xl"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>
            Yeni Şablon
          </Button>
        )}
      </div>

      {/* Stats row */}
      {!isLoading && steps.length > 0 && (
        <div className="border-b border-border bg-surface-base px-6 py-3 shrink-0">
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-[18px] font-bold text-fg tabular-nums">{steps.length}</p>
              <p className="text-[10px] text-fg-subtle">Şablon</p>
            </div>
            <div className="h-8 w-px bg-border" />
            <div className="text-center">
              <p className="text-[18px] font-bold text-fg tabular-nums">{totalStepCount}</p>
              <p className="text-[10px] text-fg-subtle">Toplam Adım</p>
            </div>
            <div className="h-8 w-px bg-border" />
            <div className="text-center">
              <p className="text-[18px] font-bold text-brand tabular-nums">{totalUsage}</p>
              <p className="text-[10px] text-fg-subtle">Toplam Kullanım</p>
            </div>
          </div>
        </div>
      )}

      {/* Search + sort bar */}
      <div className="border-b border-border bg-surface-base px-6 py-2.5 shrink-0 flex items-center gap-3 flex-wrap">
        <div className="flex w-56 items-center gap-2 rounded-xl border border-border bg-surface-raised px-3 py-1.5 focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15 transition-all">
          <svg className="h-3.5 w-3.5 shrink-0 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><circle cx="11" cy="11" r="8"/><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35"/></svg>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Şablon ara…"
            className="flex-1 bg-transparent text-[12px] text-fg placeholder:text-fg-subtle outline-none" />
          {search && (
            <button type="button" onClick={() => setSearch("")} className="text-fg-subtle hover:text-fg">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          )}
        </div>
        {/* Sort dropdown */}
        <select
          value={sortKey}
          onChange={e => setSortKey(e.target.value as SortKey)}
          className="rounded-xl border border-border bg-surface-raised px-3 py-1.5 text-[12px] text-fg outline-none focus:border-brand cursor-pointer"
        >
          {SORT_OPTIONS.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}
        </select>
        {/* Tag filter chips */}
        {allTags.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {activeTag && (
              <button
                type="button"
                onClick={() => setActiveTag(null)}
                className="flex items-center gap-1 rounded-full bg-brand/20 border border-brand/30 px-2 py-0.5 text-[10px] text-brand font-medium"
              >
                <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                {activeTag}
              </button>
            )}
            {allTags.filter(t => t !== activeTag).slice(0, 8).map(t => (
              <button
                key={t}
                type="button"
                onClick={() => setActiveTag(t)}
                className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-subtle hover:border-brand/40 hover:text-brand transition-colors"
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-14 rounded-xl border border-border bg-surface-raised animate-pulse" />
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <p className="text-[13px] text-red-400">Şablonlar yüklenemedi</p>
            <button onClick={() => refetch()} className="text-[12px] text-brand hover:text-brand-secondary transition-colors">Tekrar Dene</button>
          </div>
        ) : filtered.length === 0 ? (
          search ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
              <p className="text-[14px] font-medium text-fg-muted">"{search}" için sonuç bulunamadı</p>
              <button onClick={() => setSearch("")} className="text-[12px] text-brand transition-colors">Aramayı temizle</button>
            </div>
          ) : (
            <EmptyState onNew={canEdit ? () => { setEditing(null); setShowModal(true); } : () => {}} />
          )
        ) : (
          <div className="space-y-2">
            <p className="mb-3 text-[11px] text-fg-subtle">
              {filtered.length} şablon
              {(search || activeTag) && <span className="text-fg-disabled"> (toplam {steps.length}'den)</span>}
            </p>
            {filtered.map(ss => (
              <SharedStepCard
                key={ss.id}
                ss={ss}
                isDeleting={deletingId === ss.id}
                onEdit={canEdit ? (s) => { setEditing(s); setShowModal(true); } : undefined}
                onDelete={canEdit ? handleDeleteRequest : undefined}
              />
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <SharedStepModal
          initial={editing ?? undefined}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditing(null); }}
          saving={saving}
        />
      )}

      {confirmDeleteId && (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          onClick={() => setConfirmDeleteId(null)}
        >
          <div
            className="w-full max-w-sm rounded-2xl border border-border bg-surface-raised p-6 shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-danger-subtle">
                <svg className="h-5 w-5 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-[14px] font-semibold text-fg">Şablonu Sil</h3>
                <p className="mt-1 text-[12px] text-fg-muted">Bu adım şablonu kalıcı olarak silinecek. Bu işlem geri alınamaz.</p>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button
                type="button"
                onClick={() => setConfirmDeleteId(null)}
                variant="outline"
                size="default"
                className="rounded-xl"
              >
                İptal
              </Button>
              <Button
                type="button"
                onClick={handleDeleteConfirm}
                variant="destructive"
                size="default"
                className="rounded-xl"
              >
                Sil
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
