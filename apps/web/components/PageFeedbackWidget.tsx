"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

/**
 * Sayfa altına yerleştirilebilir "Bu sayfa faydalı mı?" widget.
 *
 * localStorage'a path başına 1 oy kaydeder.
 * Production'da `/api/v1/feedback` endpoint'ine de gönderilebilir.
 */

const STORAGE_KEY = "neurex_page_feedback_v1";

type FeedbackRecord = {
  path: string;
  helpful: boolean;
  comment?: string;
  ts: number;
};

function readAll(): FeedbackRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveAll(items: FeedbackRecord[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    /* quota */
  }
}

// Module-level instance counter to dedupe when both layout and page render the widget.
let _activeInstanceCount = 0;

export function PageFeedbackWidget() {
  const pathname = usePathname() ?? "";
  const [voted, setVoted] = useState<null | "yes" | "no">(null);
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [shouldRender, setShouldRender] = useState(true);

  useEffect(() => {
    _activeInstanceCount += 1;
    if (_activeInstanceCount > 1) setShouldRender(false);
    return () => {
      _activeInstanceCount = Math.max(0, _activeInstanceCount - 1);
    };
  }, []);

  useEffect(() => {
    const all = readAll();
    const found = all.find((r) => r.path === pathname);
    if (found) {
      setVoted(found.helpful ? "yes" : "no");
      setSubmitted(true);
    } else {
      setVoted(null);
      setSubmitted(false);
      setComment("");
      setShowCommentInput(false);
    }
  }, [pathname]);

  const submit = (helpful: boolean) => {
    if (submitted) return;
    const all = readAll().filter((r) => r.path !== pathname);
    all.push({
      path: pathname,
      helpful,
      comment: comment.trim() || undefined,
      ts: Date.now(),
    });
    saveAll(all);
    setVoted(helpful ? "yes" : "no");
    if (!helpful) {
      // Show comment field after negative vote
      setShowCommentInput(true);
    } else {
      setSubmitted(true);
    }

    // Production: also POST to /api/v1/feedback
    if (typeof fetch !== "undefined") {
      fetch("/api/v1/feedback", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: pathname,
          helpful,
          comment: comment.trim() || undefined,
        }),
      }).catch(() => {
        // Endpoint may not exist yet; localStorage'a kaydetmek yeterli
      });
    }
  };

  const submitComment = () => {
    const all = readAll().filter((r) => r.path !== pathname);
    all.push({
      path: pathname,
      helpful: false,
      comment: comment.trim() || undefined,
      ts: Date.now(),
    });
    saveAll(all);
    setSubmitted(true);
    setShowCommentInput(false);
  };

  // Skip on auth/internal pages
  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/reset-password") ||
    pathname === "/offline" ||
    pathname === "/"
  ) {
    return null;
  }

  if (!shouldRender) return null;

  return (
    <div
      className="mt-12 border-t border-slate-800 px-6 py-6"
      data-testid="page-feedback-widget"
    >
      <div className="mx-auto max-w-md text-center">
        {submitted ? (
          <p
            className="text-xs text-slate-500"
            data-testid="page-feedback-thanks"
          >
            ✓ Geri bildirim için teşekkürler.
          </p>
        ) : showCommentInput && voted === "no" ? (
          <div data-testid="page-feedback-comment-form">
            <p className="mb-2 text-sm text-slate-300">
              Daha iyi yapmamıza yardım eder misin?
            </p>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              placeholder="Hangi konuda yardım gerekiyor?"
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs"
              data-testid="page-feedback-comment-input"
            />
            <div className="mt-2 flex justify-center gap-2">
              <button
                type="button"
                onClick={submitComment}
                className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-indigo-500"
                data-testid="page-feedback-comment-submit"
              >
                Gönder
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowCommentInput(false);
                  setSubmitted(true);
                }}
                className="rounded-lg border border-slate-700 px-4 py-1.5 text-xs text-slate-400 hover:bg-slate-800"
                data-testid="page-feedback-comment-skip"
              >
                Geç
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-xs text-slate-400">Bu sayfa faydalı oldu mu?</p>
            <div className="mt-2 flex justify-center gap-2">
              <button
                type="button"
                onClick={() => submit(true)}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs hover:bg-slate-800"
                data-testid="page-feedback-yes"
              >
                👍 Evet
              </button>
              <button
                type="button"
                onClick={() => submit(false)}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs hover:bg-slate-800"
                data-testid="page-feedback-no"
              >
                👎 Hayır
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
