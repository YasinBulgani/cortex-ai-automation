"use client";

import Link from "next/link";

import { useRecentAndFavorites } from "@/lib/useRecentAndFavorites";

/**
 * Sidebar üstüne yerleştirilebilir küçük panel:
 * - ⭐ Favoriler (pin'lenen sayfalar)
 * - 🕐 Son Ziyaret (otomatik)
 */
export function RecentFavoritesPanel() {
  const { recent, favorites, toggleFavorite } = useRecentAndFavorites();

  if (recent.length === 0 && favorites.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3 px-3 py-2" data-testid="recent-favorites-panel">
      {favorites.length > 0 && (
        <div>
          <div className="mb-1 flex items-center justify-between px-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              ⭐ Favoriler
            </span>
          </div>
          <ul className="space-y-0.5" data-testid="favorites-list">
            {favorites.map((f) => (
              <li key={f.path} className="group flex items-center justify-between">
                <Link
                  href={f.path}
                  className="flex-1 truncate rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
                  data-testid={`favorite-link-${f.path}`}
                >
                  {f.label}
                </Link>
                <button
                  type="button"
                  onClick={() => toggleFavorite(f.path, f.label)}
                  className="opacity-0 group-hover:opacity-100 px-1 text-amber-400 hover:text-amber-300"
                  aria-label={`${f.label} favorilerden çıkar`}
                  data-testid={`favorite-remove-${f.path}`}
                >
                  ⭐
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {recent.length > 0 && (
        <div>
          <div className="mb-1 px-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              🕐 Son Ziyaret
            </span>
          </div>
          <ul className="space-y-0.5" data-testid="recent-list">
            {recent.slice(0, 5).map((r) => (
              <li key={`${r.path}-${r.ts}`} className="group flex items-center justify-between">
                <Link
                  href={r.path}
                  className="flex-1 truncate rounded px-2 py-1 text-xs text-slate-400 hover:bg-slate-800"
                  data-testid={`recent-link-${r.path}`}
                >
                  {r.label}
                </Link>
                <button
                  type="button"
                  onClick={() => toggleFavorite(r.path, r.label)}
                  className="opacity-0 group-hover:opacity-100 px-1 text-slate-500 hover:text-amber-400"
                  aria-label={`${r.label} favorilere ekle`}
                  data-testid={`recent-pin-${r.path}`}
                >
                  ☆
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
