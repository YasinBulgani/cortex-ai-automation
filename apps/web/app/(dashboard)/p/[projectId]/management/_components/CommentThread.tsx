"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  buildCommentTree,
  type CommentEntityType,
  type CommentNode,
  type MgmtComment,
  useComments,
  useCreateComment,
  useDeleteComment,
  useReactToComment,
  useThreadSummary,
  useUpdateComment,
} from "@/lib/hooks/use-mgmt-comments";

const REACTION_PALETTE: readonly string[] = ["+1", "-1", "heart", "rocket", "eyes", "tada"];

const REACTION_ICON: Record<string, string> = {
  "+1": "👍",
  "-1": "👎",
  heart: "❤️",
  rocket: "🚀",
  eyes: "👀",
  tada: "🎉",
};

export interface CommentThreadProps {
  entityType: CommentEntityType;
  entityId: string;
  projectId?: string | null;
  currentUserId?: string | null;
  /** Map user id → display label, used to render @mentions. */
  userDirectory?: Record<string, string>;
  /** Override the header title. */
  title?: string;
}

export function CommentThread({
  entityType,
  entityId,
  projectId = null,
  currentUserId = null,
  userDirectory,
  title = "Yorumlar",
}: CommentThreadProps) {
  const { data, isLoading, isError, error } = useComments(entityType, entityId);
  const tree = useMemo(() => buildCommentTree(data ?? []), [data]);
  const createMutation = useCreateComment();
  const updateMutation = useUpdateComment(entityType, entityId);
  const deleteMutation = useDeleteComment(entityType, entityId);
  const reactMutation = useReactToComment(entityType, entityId);

  const [draft, setDraft] = useState("");
  const [summaryOpen, setSummaryOpen] = useState(false);
  const summary = useThreadSummary(entityType, entityId, summaryOpen);

  const submitRoot = async () => {
    const body = draft.trim();
    if (!body) return;
    await createMutation.mutateAsync({
      entity_type: entityType,
      entity_id: entityId,
      project_id: projectId,
      body_md: body,
    });
    setDraft("");
  };

  return (
    <section className="rounded-lg border border-border bg-surface-raised p-5">
      <header className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-fg">{title}</h2>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setSummaryOpen((v) => !v)}
            aria-pressed={summaryOpen}
            className={`rounded-md border px-2 py-1 text-[11px] transition ${
              summaryOpen
                ? "border-brand/40 bg-brand-soft text-brand"
                : "border-border text-fg-muted hover:border-brand/40 hover:text-brand"
            }`}
          >
            {summaryOpen ? "Hide AI özet" : "AI özet"}
          </button>
          <span className="text-xs text-fg-subtle">{data?.length ?? 0} comment(s)</span>
        </div>
      </header>

      {summaryOpen ? (
        <div className="mb-4 rounded-md border border-teal-500/30 bg-teal-500/5 p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-teal-300">
            AI başlık özeti
          </p>
          {summary.isLoading ? (
            <p className="text-xs text-fg-muted">Oluşturuluyor…</p>
          ) : summary.isError ? (
            <p className="text-xs text-danger">
              Özet kullanılamıyor: {(summary.error as Error)?.message ?? "bilinmeyen hata"}
            </p>
          ) : summary.data ? (
            <div className="space-y-2 text-xs text-fg">
              <p>
                <span className="font-semibold text-brand">Özet — </span>
                {summary.data.tldr || "(özet yok)"}
              </p>
              {summary.data.decisions.length > 0 ? (
                <div>
                  <p className="font-semibold text-brand">Kararlar</p>
                  <ul className="ml-4 list-disc space-y-0.5">
                    {summary.data.decisions.map((d, i) => (
                      <li key={`d-${i}`}>{d}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {summary.data.openQuestions.length > 0 ? (
                <div>
                  <p className="font-semibold text-brand">Açık sorular</p>
                  <ul className="ml-4 list-disc space-y-0.5">
                    {summary.data.openQuestions.map((q, i) => (
                      <li key={`q-${i}`}>{q}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {summary.data.source === "fallback" ? (
                <p className="text-[10px] italic text-fg-subtle">
                  (heuristic fallback — LLM unavailable)
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {isError ? (
        <p className="rounded border border-red-800 bg-red-950/40 p-3 text-xs text-red-200">
          Yorumlar yüklenemedi: {(error as Error)?.message ?? "bilinmeyen hata"}
        </p>
      ) : null}

      {isLoading ? (
        <p className="text-xs text-fg-subtle">Yükleniyor…</p>
      ) : tree.length === 0 ? (
        <p className="rounded border border-dashed border-border bg-surface-overlay p-3 text-xs text-fg-subtle">
          Henüz yorum yok.
        </p>
      ) : (
        <ul className="space-y-3">
          {tree.map((node) => (
            <li key={node.id}>
              <CommentItem
                node={node}
                depth={0}
                entityType={entityType}
                entityId={entityId}
                projectId={projectId}
                currentUserId={currentUserId}
                userDirectory={userDirectory}
                onReply={(parentId, body) =>
                  createMutation.mutateAsync({
                    entity_type: entityType,
                    entity_id: entityId,
                    project_id: projectId,
                    parent_id: parentId,
                    body_md: body,
                  })
                }
                onEdit={(commentId, body) =>
                  updateMutation.mutateAsync({ commentId, body_md: body })
                }
                onDelete={(commentId) => deleteMutation.mutateAsync(commentId)}
                onReact={(commentId, emoji, currentlyReacted) =>
                  reactMutation.mutateAsync({ commentId, emoji, add: !currentlyReacted })
                }
              />
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 border-t border-border pt-4">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Yorum yazın… Bir takım arkadaşını etiketlemek için @<kullanıcı-uuid> kullanın."
          rows={3}
          className="w-full resize-y rounded-md border border-border bg-surface-overlay p-2 text-sm text-fg outline-none focus:border-brand/50 placeholder:text-fg-disabled"
        />
        <div className="mt-2 flex items-center justify-between">
          <span className="text-[11px] text-fg-subtle">
            Markdown desteklenir. Etiketlemeler bildirim tetikler.
          </span>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => void submitRoot()}
            disabled={!draft.trim() || createMutation.isPending}
          >
            {createMutation.isPending ? "Gönderiliyor…" : "Yorum Ekle"}
          </Button>
        </div>
      </div>
    </section>
  );
}

interface CommentItemProps {
  node: CommentNode;
  depth: number;
  entityType: CommentEntityType;
  entityId: string;
  projectId: string | null;
  currentUserId: string | null;
  userDirectory: Record<string, string> | undefined;
  onReply: (parentId: string, body: string) => Promise<MgmtComment>;
  onEdit: (commentId: string, body: string) => Promise<MgmtComment>;
  onDelete: (commentId: string) => Promise<MgmtComment>;
  onReact: (
    commentId: string,
    emoji: string,
    currentlyReacted: boolean,
  ) => Promise<MgmtComment>;
}

function CommentItem({
  node,
  depth,
  entityType,
  entityId,
  projectId,
  currentUserId,
  userDirectory,
  onReply,
  onEdit,
  onDelete,
  onReact,
}: CommentItemProps) {
  const [replying, setReplying] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [draft, setDraft] = useState("");
  const [editDraft, setEditDraft] = useState(node.body_md);

  const isAuthor = currentUserId !== null && node.author_id === currentUserId;
  const isDeleted = !!node.deleted_at;
  const authorLabel =
    (node.author_id && userDirectory?.[node.author_id]) ?? node.author_id?.slice(0, 8) ?? "unknown";

  return (
    <div
      className="rounded-md border border-border bg-surface-overlay p-3"
      style={{ marginLeft: depth > 0 ? Math.min(depth, 4) * 16 : 0 }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-fg-muted">
            <span className="font-semibold text-fg">{authorLabel}</span>{" "}
            <span className="text-fg-subtle">
              · {new Date(node.created_at).toLocaleString()}
              {node.edited_at ? " · edited" : ""}
              {isDeleted ? " · silindi" : ""}
            </span>
          </p>
          {editing ? (
            <div className="mt-2">
              <textarea
                value={editDraft}
                onChange={(e) => setEditDraft(e.target.value)}
                rows={3}
                className="w-full resize-y rounded-md border border-border bg-surface-overlay p-2 text-sm text-fg outline-none focus:border-brand/50"
              />
              <div className="mt-2 flex gap-2">
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  onClick={async () => {
                    const trimmed = editDraft.trim();
                    if (!trimmed) return;
                    await onEdit(node.id, trimmed);
                    setEditing(false);
                  }}
                >
                  Kaydet
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setEditing(false);
                    setEditDraft(node.body_md);
                  }}
                >
                  Vazgeç
                </Button>
              </div>
            </div>
          ) : (
            <p
              className={`mt-1 whitespace-pre-wrap text-sm ${
                isDeleted ? "italic text-fg-subtle" : "text-fg"
              }`}
            >
              {isDeleted ? "[yorum kaldırıldı]" : renderBody(node.body_md, userDirectory)}
            </p>
          )}
        </div>
      </div>

      {!isDeleted ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {REACTION_PALETTE.map((emoji) => {
            const userIds = node.reactions[emoji] ?? [];
            const count = userIds.length;
            const reacted = currentUserId ? userIds.includes(currentUserId) : false;
            return (
              <button
                key={emoji}
                type="button"
                onClick={() => void onReact(node.id, emoji, reacted)}
                className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] transition ${
                  reacted
                    ? "border-brand/40 bg-brand-soft text-brand"
                    : "border-border text-fg-muted hover:border-border-strong"
                }`}
                aria-pressed={reacted}
                aria-label={`React with ${emoji}`}
              >
                <span>{REACTION_ICON[emoji] ?? emoji}</span>
                {count > 0 ? <span className="font-semibold">{count}</span> : null}
              </button>
            );
          })}
          <button
            type="button"
            className="ml-auto text-[11px] text-fg-muted hover:text-fg"
            onClick={() => setReplying((v) => !v)}
          >
            {replying ? "Yanıtı iptal et" : "Yanıtla"}
          </button>
          {isAuthor ? (
            <>
              <button
                type="button"
                className="text-[11px] text-fg-muted hover:text-fg"
                onClick={() => {
                  setEditing(true);
                  setEditDraft(node.body_md);
                }}
              >
                Düzenle
              </button>
              {confirmingDelete ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="text-[11px] text-fg-muted">Emin misiniz?</span>
                  <button
                    type="button"
                    className="text-[11px] font-semibold text-red-300 hover:text-red-100"
                    onClick={() => { setConfirmingDelete(false); void onDelete(node.id); }}
                  >
                    Evet, sil
                  </button>
                  <button
                    type="button"
                    className="text-[11px] text-fg-subtle hover:text-fg"
                    onClick={() => setConfirmingDelete(false)}
                  >
                    Vazgeç
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  className="text-[11px] text-red-300 hover:text-red-100"
                  onClick={() => setConfirmingDelete(true)}
                >
                  Sil
                </button>
              )}
            </>
          ) : null}
        </div>
      ) : null}

      {replying ? (
        <div className="mt-2 rounded border border-border bg-surface-overlay p-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={2}
            placeholder="Yanıt yazın…"
            className="w-full resize-y rounded-md border border-border bg-surface-overlay p-2 text-sm text-fg outline-none focus:border-brand/50 placeholder:text-fg-disabled"
          />
          <div className="mt-2 flex gap-2">
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={async () => {
                const trimmed = draft.trim();
                if (!trimmed) return;
                await onReply(node.id, trimmed);
                setDraft("");
                setReplying(false);
              }}
            >
              Yanıtla
            </Button>
          </div>
        </div>
      ) : null}

      {node.children.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {node.children.map((child) => (
            <li key={child.id}>
              <CommentItem
                node={child}
                depth={depth + 1}
                entityType={entityType}
                entityId={entityId}
                projectId={projectId}
                currentUserId={currentUserId}
                userDirectory={userDirectory}
                onReply={onReply}
                onEdit={onEdit}
                onDelete={onDelete}
                onReact={onReact}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

const MENTION_RE = /@([0-9a-fA-F-]{36})/g;

function renderBody(body: string, dir: Record<string, string> | undefined): React.ReactNode {
  if (!body) return null;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = MENTION_RE.exec(body)) !== null) {
    if (match.index > lastIndex) {
      parts.push(body.slice(lastIndex, match.index));
    }
    const uid = match[1];
    const label = (dir?.[uid] ?? uid.slice(0, 8));
    parts.push(
      <span
        key={`m-${key++}`}
        className="rounded bg-teal-500/15 px-1 py-0.5 text-teal-200"
      >
        @{label}
      </span>,
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < body.length) {
    parts.push(body.slice(lastIndex));
  }
  return parts;
}
