"use client";

import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const RECENT_KEY = "neurex_recent_v1";
const FAV_KEY = "neurex_favorites_v1";
const MAX_RECENT = 10;

export type RecentItem = {
  path: string;
  label: string;
  ts: number;
};

export type FavoriteItem = {
  path: string;
  label: string;
  pinned_at: number;
};

function read<T>(key: string): T[] {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write<T>(key: string, items: T[]) {
  try {
    localStorage.setItem(key, JSON.stringify(items));
  } catch {
    /* quota */
  }
}

// Path → human-readable label
const LABEL_RULES: { test: RegExp; label: (m: RegExpMatchArray) => string }[] = [
  { test: /^\/p\/[^/]+\/scenarios\/?$/, label: () => "Senaryolar" },
  { test: /^\/p\/[^/]+\/scenarios\/new$/, label: () => "Yeni Senaryo" },
  { test: /^\/p\/[^/]+\/sifir-bilgi/, label: () => "Sıfır Bilgi (AI)" },
  { test: /^\/p\/[^/]+\/executions\/?$/, label: () => "Koşumlar" },
  { test: /^\/p\/[^/]+\/executions\/new$/, label: () => "Yeni Koşum" },
  { test: /^\/p\/[^/]+\/executions\/([^/]+)/, label: (m) => `Koşum ${m[1].slice(0, 8)}` },
  { test: /^\/p\/[^/]+\/flaky/, label: () => "Flaky Testler" },
  { test: /^\/p\/[^/]+\/healing/, label: () => "Self-Healing" },
  { test: /^\/p\/[^/]+\/mobile/, label: () => "Mobil" },
  { test: /^\/p\/[^/]+\/api-tests/, label: () => "API Testleri" },
  { test: /^\/p\/[^/]+\/reports/, label: () => "Raporlar" },
  { test: /^\/p\/[^/]+\/analytics/, label: () => "Analitik" },
  { test: /^\/p\/[^/]+\/coverage/, label: () => "Kapsama" },
  { test: /^\/p\/[^/]+\/cicd/, label: () => "CI/CD" },
  { test: /^\/p\/[^/]+\/schedules/, label: () => "Zamanlayıcı" },
  { test: /^\/p\/[^/]+\/dashboards/, label: () => "Özel Dashboard" },
  { test: /^\/p\/[^/]+\/(.+)/, label: (m) => m[1].split("/")[0].replace(/-/g, " ") },
  { test: /^\/portfolio/, label: () => "Projeler" },
  { test: /^\/admin/, label: () => "Admin" },
  { test: /^\/status/, label: () => "Sistem Durumu" },
  { test: /^\/kb/, label: () => "Knowledge Base" },
  { test: /^\/$/, label: () => "Ana Panel" },
];

function pathToLabel(path: string): string {
  for (const { test, label } of LABEL_RULES) {
    const m = path.match(test);
    if (m) return label(m);
  }
  return path;
}

const SKIP_PATTERNS: RegExp[] = [
  /^\/login/,
  /^\/reset-password/,
  /^\/onboarding/,
  /^\/offline/,
  /^\/$/,  // ana panel zaten kolay erişilir
];

function shouldSkip(path: string): boolean {
  return SKIP_PATTERNS.some((p) => p.test(path));
}

export function useRecentAndFavorites() {
  const pathname = usePathname() ?? "";
  const [recent, setRecent] = useState<RecentItem[]>([]);
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);

  // Initial load
  useEffect(() => {
    setRecent(read<RecentItem>(RECENT_KEY));
    setFavorites(read<FavoriteItem>(FAV_KEY));
  }, []);

  // Track navigation
  useEffect(() => {
    if (!pathname || shouldSkip(pathname)) return;
    const label = pathToLabel(pathname);
    const now = Date.now();

    const prior = read<RecentItem>(RECENT_KEY);
    // Drop existing entry with same path, prepend new
    const updated: RecentItem[] = [
      { path: pathname, label, ts: now },
      ...prior.filter((r) => r.path !== pathname),
    ].slice(0, MAX_RECENT);
    write(RECENT_KEY, updated);
    setRecent(updated);
  }, [pathname]);

  const isFavorite = useCallback(
    (path: string) => favorites.some((f) => f.path === path),
    [favorites],
  );

  const toggleFavorite = useCallback(
    (path: string, labelOverride?: string) => {
      const current = read<FavoriteItem>(FAV_KEY);
      const exists = current.some((f) => f.path === path);
      let next: FavoriteItem[];
      if (exists) {
        next = current.filter((f) => f.path !== path);
      } else {
        next = [
          ...current,
          {
            path,
            label: labelOverride ?? pathToLabel(path),
            pinned_at: Date.now(),
          },
        ];
      }
      write(FAV_KEY, next);
      setFavorites(next);
    },
    [],
  );

  const clearRecent = useCallback(() => {
    write(RECENT_KEY, []);
    setRecent([]);
  }, []);

  const clearFavorites = useCallback(() => {
    write(FAV_KEY, []);
    setFavorites([]);
  }, []);

  return {
    recent,
    favorites,
    isFavorite,
    toggleFavorite,
    clearRecent,
    clearFavorites,
  };
}
