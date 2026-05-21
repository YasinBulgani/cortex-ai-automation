"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { useKnowledgeBase, type KbArticle } from "@/lib/useKnowledgeBase";

function renderMarkdown(md: string): string {
  // Very minimal markdown — headings, bold, italic, code, lists, links
  // Production: replace with `marked` or `react-markdown`
  return md
    .replace(/^### (.*)$/gm, '<h3 class="mt-4 mb-2 text-base font-semibold">$1</h3>')
    .replace(/^## (.*)$/gm, '<h2 class="mt-5 mb-2 text-lg font-bold">$1</h2>')
    .replace(/^# (.*)$/gm, '<h1 class="mt-5 mb-3 text-xl font-bold">$1</h1>')
    .replace(/```([^`]+)```/gs, '<pre class="my-3 overflow-auto rounded bg-slate-800 p-3 text-xs"><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code class="rounded bg-slate-800 px-1 py-0.5 text-xs">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.*)$/gm, '<li class="ml-5 list-disc">$1</li>')
    .replace(/^\d+\. (.*)$/gm, '<li class="ml-5 list-decimal">$1</li>')
    .replace(/\n\n/g, '</p><p class="mt-3">')
    .replace(/^(?!<)/, '<p>');
}

export default function ArticleDetailPage() {
  const articleId = useRouteParam("articleId");
  const { articles, incrementView, vote } = useKnowledgeBase();
  const [voted, setVoted] = useState<null | "helpful" | "unhelpful">(null);
  const [article, setArticle] = useState<KbArticle | null>(null);

  useEffect(() => {
    const found = articles.find((a) => a.id === articleId) ?? null;
    setArticle(found);
    if (found) incrementView(found.id);
  }, [articleId, articles, incrementView]);

  if (!article) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300"
        data-testid="kb-article-not-found"
      >
        <div className="text-center">
          <div className="text-4xl">🔎</div>
          <p className="mt-3">Makale bulunamadı</p>
          <Link
            href="/kb"
            className="mt-4 inline-block rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
          >
            ← KB'ye dön
          </Link>
        </div>
      </div>
    );
  }

  const onVote = (helpful: boolean) => {
    if (voted) return;
    vote(article.id, helpful);
    setVoted(helpful ? "helpful" : "unhelpful");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100" data-testid="kb-article-page">
      <div className="mx-auto max-w-3xl px-6 py-8">
        <Link
          href="/kb"
          className="text-xs text-slate-400 hover:text-white"
          data-testid="kb-article-back"
        >
          ← Knowledge Base
        </Link>

        <article className="mt-4">
          <h1 className="text-3xl font-bold tracking-tight" data-testid="kb-article-title">
            {article.title}
          </h1>
          <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
            <span>{article.category}</span>
            <span>·</span>
            <span>{article.view_count} görüntüleme</span>
            <span>·</span>
            <span>👍 {article.helpful_count}</span>
            {article.tags.length > 0 && (
              <>
                <span>·</span>
                <div className="flex gap-1">
                  {article.tags.map((t) => (
                    <span key={t} className="rounded bg-slate-800 px-1.5 py-0.5">
                      #{t}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>

          <div
            className="mt-6 prose prose-invert prose-sm max-w-none text-slate-300"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(article.body) }}
            data-testid="kb-article-body"
          />
        </article>

        <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm font-medium">Bu makale faydalı oldu mu?</p>
          {voted ? (
            <p
              className="mt-2 text-xs text-emerald-400"
              data-testid="kb-vote-thanks"
            >
              ✓ Teşekkürler — geri bildirimin kaydedildi
            </p>
          ) : (
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => onVote(true)}
                className="rounded-lg border border-slate-700 px-4 py-2 text-xs hover:bg-slate-800"
                data-testid="kb-vote-yes"
              >
                👍 Evet, faydalı
              </button>
              <button
                type="button"
                onClick={() => onVote(false)}
                className="rounded-lg border border-slate-700 px-4 py-2 text-xs hover:bg-slate-800"
                data-testid="kb-vote-no"
              >
                👎 Yeterli değil
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
