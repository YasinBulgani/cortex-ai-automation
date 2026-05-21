"use client";

/**
 * DSL Proposal Review
 * --------------------
 * "Review" sayfasının ana bileşeni. Sol listede status'e göre filtrelenen
 * öneriler, sağ tarafta seçili önerinin diff görünümü ve Onayla / Reddet
 * butonları.
 *
 * Diff render'ı için minimal bir "before vs after" key-value tablosu
 * kullanıyoruz. JSON büyük görünmesi gereken değerlerde `<pre>` bloğuna
 * düşer. Üçüncü-parti diff kütüphanesi eklemeden basit, okunur.
 */

import { useMemo, useState } from "react";
import Link from "next/link";

import {
  useDslApproveProposal,
  useDslProposals,
  useDslRejectProposal,
  type DslProposal,
  type DslProposalStatus,
} from "@/lib/hooks/use-dsl";

const STATUS_FILTERS: Array<{ id: DslProposalStatus | "all"; label: string }> = [
  { id: "pending", label: "Bekleyen" },
  { id: "merged", label: "Tamamlanan" },
  { id: "rejected", label: "Reddedilen" },
  { id: "error", label: "Hatalı" },
  { id: "all", label: "Hepsi" },
];

const OP_BADGE: Record<string, string> = {
  create: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  update: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  delete: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  deprecate: "border-amber-500/30 bg-amber-500/10 text-amber-300",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  approved: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  merged: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  rejected: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  error: "border-rose-500/30 bg-rose-500/10 text-rose-300",
};

export function DslProposalReview() {
  const [filter, setFilter] = useState<DslProposalStatus | "all">("pending");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useDslProposals({
    status: filter === "all" ? undefined : filter,
    limit: 100,
  });

  const proposals = useMemo(() => data?.items ?? [], [data?.items]);
  const selected = useMemo(
    () => proposals.find((p) => p.id === selectedId) ?? proposals[0] ?? null,
    [proposals, selectedId],
  );

  return (
    <div className="flex h-full flex-col gap-4 p-4 sm:p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">DSL Öneri İnceleme</h1>
          <p className="mt-1 text-sm text-slate-400">
            Pending önerileri incele, onayla ya da reddet. Onaylanan öneri
            YAML'e yazılır ve commit edilir.
          </p>
        </div>
        <Link
          href="/dsl-catalog"
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
        >
          ← Katalog
        </Link>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => {
              setFilter(f.id);
              setSelectedId(null);
            }}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.id
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
            data-testid={`dsl-review-filter-${f.id}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        {/* Sol liste */}
        <aside className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50">
          <div className="border-b border-slate-800 px-3 py-2 text-xs text-slate-500">
            {isLoading ? "Yükleniyor…" : `${proposals.length} kayıt`}
          </div>
          <div className="flex-1 overflow-y-auto">
            {proposals.length === 0 && !isLoading && (
              <div className="p-6 text-center text-xs text-slate-500">
                Bu filtreye uygun öneri yok.
              </div>
            )}
            {proposals.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelectedId(p.id)}
                className={`flex w-full flex-col gap-1 border-b border-slate-800 px-3 py-2.5 text-left transition-colors ${
                  selected?.id === p.id
                    ? "bg-slate-800/70"
                    : "hover:bg-slate-800/40"
                }`}
                data-testid={`dsl-proposal-item-${p.id}`}
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] uppercase ${
                      OP_BADGE[p.operation] ?? "border-slate-700 bg-slate-800 text-slate-300"
                    }`}
                  >
                    {p.operation}
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] uppercase ${
                      STATUS_BADGE[p.status] ?? "border-slate-700 bg-slate-800 text-slate-300"
                    }`}
                  >
                    {p.status}
                  </span>
                  <span className="ml-auto text-[10px] text-slate-500">
                    {p.proposer_kind === "ai" ? "🤖" : "👤"}
                  </span>
                </div>
                <div className="truncate font-mono text-xs text-white">
                  {p.action_id}
                </div>
                <div className="text-[10px] text-slate-500">
                  {new Date(p.created_at).toLocaleString()}
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* Sağ detay */}
        <main className="min-h-0 overflow-auto rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          {selected ? (
            <ProposalDetail proposal={selected} />
          ) : (
            <div className="p-8 text-center text-sm text-slate-500">
              Sol panelden bir öneri seçin.
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function ProposalDetail({ proposal }: { proposal: DslProposal }) {
  const approve = useDslApproveProposal();
  const reject = useDslRejectProposal();
  const [note, setNote] = useState("");

  const diff = proposal.diff ?? { op: "update", before: null, after: null, changed_fields: [] };
  const before = diff.before ?? null;
  const after = diff.after ?? null;

  async function onApprove() {
    try {
      await approve.mutateAsync({
        proposalId: proposal.id,
        body: { note: note.trim() || undefined },
      });
      setNote("");
    } catch (err) {
      alert(`Onay hatası: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  async function onReject() {
    if (!confirm("Bu öneriyi reddetmek istediğinizden emin misiniz?")) return;
    try {
      await reject.mutateAsync({
        proposalId: proposal.id,
        body: { note: note.trim() || undefined },
      });
      setNote("");
    } catch (err) {
      alert(`Red hatası: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  const canAct = proposal.status === "pending";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <h2 className="font-mono text-base font-semibold text-white">
            {proposal.action_id}
          </h2>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
            <span
              className={`rounded-full border px-2 py-0.5 uppercase ${
                OP_BADGE[proposal.operation] ?? ""
              }`}
            >
              {proposal.operation}
            </span>
            <span
              className={`rounded-full border px-2 py-0.5 uppercase ${
                STATUS_BADGE[proposal.status] ?? ""
              }`}
            >
              {proposal.status}
            </span>
            <span>{new Date(proposal.created_at).toLocaleString()}</span>
          </div>
        </div>
        {proposal.pr_url && (
          <a
            href={proposal.pr_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs text-blue-200 hover:bg-blue-500/20"
          >
            PR'ı aç ↗
          </a>
        )}
      </div>

      {proposal.ai_reasoning && (
        <div className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-3 text-xs text-violet-200">
          <div className="mb-1 font-semibold">🤖 AI gerekçesi</div>
          {proposal.ai_reasoning}
        </div>
      )}

      {proposal.error_message && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs text-rose-200">
          <div className="mb-1 font-semibold">Hata</div>
          <pre className="whitespace-pre-wrap font-mono">{proposal.error_message}</pre>
        </div>
      )}

      <DiffView before={before} after={after} changed={diff.changed_fields} />

      {canAct && (
        <div className="space-y-2 border-t border-slate-800 pt-3">
          <label className="block text-xs font-medium uppercase tracking-wider text-slate-500">
            Not (opsiyonel)
          </label>
          <textarea
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Review notunuz (commit mesajında görünmez, kayıt altına alınır)."
            rows={2}
          />
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={onReject}
              disabled={reject.isPending}
              className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-sm text-rose-200 hover:bg-rose-500/20 disabled:opacity-40"
              data-testid="dsl-proposal-reject"
            >
              {reject.isPending ? "Reddediliyor…" : "Reddet"}
            </button>
            <button
              type="button"
              onClick={onApprove}
              disabled={approve.isPending}
              className="rounded-lg border border-transparent bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-500 disabled:opacity-40"
              data-testid="dsl-proposal-approve"
            >
              {approve.isPending ? "Uygulanıyor…" : "Onayla & Uygula"}
            </button>
          </div>
        </div>
      )}

      {(proposal.commit_sha || proposal.branch) && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs">
          <div className="mb-1 font-semibold text-slate-300">Git bilgisi</div>
          <ul className="space-y-1 font-mono text-slate-400">
            {proposal.branch && <li>branch: {proposal.branch}</li>}
            {proposal.commit_sha && <li>commit: {proposal.commit_sha.slice(0, 10)}</li>}
            {proposal.base_commit_sha && (
              <li>base: {proposal.base_commit_sha.slice(0, 10)}</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

function DiffView({
  before,
  after,
  changed,
}: {
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  changed: string[];
}) {
  const fields = useMemo(() => {
    const keys = new Set<string>();
    for (const k of Object.keys(before ?? {})) keys.add(k);
    for (const k of Object.keys(after ?? {})) keys.add(k);
    const arr = Array.from(keys);
    arr.sort((a, b) => {
      const aChanged = changed.includes(a) ? 0 : 1;
      const bChanged = changed.includes(b) ? 0 : 1;
      return aChanged - bChanged || a.localeCompare(b);
    });
    return arr;
  }, [before, after, changed]);

  if (fields.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-500">
        Gösterilecek değişiklik yok.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60">
      <div className="border-b border-slate-800 px-3 py-2 text-xs text-slate-500">
        Değişen alanlar: {changed.length > 0 ? changed.join(", ") : "—"}
      </div>
      <div className="divide-y divide-slate-800">
        {fields.map((key) => {
          const b = before?.[key];
          const a = after?.[key];
          const isChanged = changed.includes(key);
          return (
            <div
              key={key}
              className={`grid grid-cols-1 gap-2 px-3 py-2.5 text-xs md:grid-cols-[140px_1fr_1fr] ${
                isChanged ? "bg-amber-500/5" : ""
              }`}
            >
              <div className="font-mono text-slate-300">
                {isChanged && <span className="mr-1 text-amber-400">●</span>}
                {key}
              </div>
              <DiffValue label="before" value={b} />
              <DiffValue label="after" value={a} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DiffValue({ label, value }: { label: string; value: unknown }) {
  const isEmpty = value === undefined || value === null;
  const pretty = isEmpty
    ? "—"
    : typeof value === "object"
    ? JSON.stringify(value, null, 2)
    : String(value);
  const multiline = typeof pretty === "string" && pretty.includes("\n");

  return (
    <div>
      <div className="mb-0.5 text-[10px] uppercase tracking-wider text-slate-600">
        {label}
      </div>
      {multiline ? (
        <pre className="max-h-48 overflow-auto rounded-md border border-slate-800 bg-slate-950 p-2 font-mono text-[11px] text-slate-200">
          {pretty}
        </pre>
      ) : (
        <div className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 font-mono text-[11px] text-slate-200">
          {pretty}
        </div>
      )}
    </div>
  );
}
