"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * usePinned — kullanıcının pin'lediği itemler (proje, senaryo, sayfa).
 *
 * localStorage tabanlı, çoklu tab senkron. Sidebar/CommandPalette'de kullanılır.
 */

export type PinnedItem = {
  id: string;
  type: "project" | "scenario" | "page";
  label: string;
  href: string;
  addedAt: number;
};

const STORAGE_KEY = "neurex_pinned";
const MAX_PINS = 10;

function loadPinned(): PinnedItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as PinnedItem[];
  } catch { return []; }
}

function savePinned(items: PinnedItem[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX_PINS)));
    window.dispatchEvent(new CustomEvent("neurex:pinned-changed"));
  } catch { /* ignore */ }
}

export function usePinned() {
  const [items, setItems] = useState<PinnedItem[]>([]);

  useEffect(() => {
    setItems(loadPinned());
    const handler = () => setItems(loadPinned());
    const storageHandler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setItems(loadPinned());
    };
    window.addEventListener("neurex:pinned-changed", handler);
    window.addEventListener("storage", storageHandler);
    return () => {
      window.removeEventListener("neurex:pinned-changed", handler);
      window.removeEventListener("storage", storageHandler);
    };
  }, []);

  const pin = useCallback((item: Omit<PinnedItem, "addedAt">) => {
    const list = loadPinned().filter(i => i.id !== item.id);
    list.unshift({ ...item, addedAt: Date.now() });
    savePinned(list);
  }, []);

  const unpin = useCallback((id: string) => {
    savePinned(loadPinned().filter(i => i.id !== id));
  }, []);

  const togglePin = useCallback((item: Omit<PinnedItem, "addedAt">) => {
    const current = loadPinned();
    const exists = current.find(i => i.id === item.id);
    if (exists) {
      savePinned(current.filter(i => i.id !== item.id));
    } else {
      const next = [{ ...item, addedAt: Date.now() }, ...current];
      savePinned(next);
    }
  }, []);

  const isPinned = useCallback((id: string) => items.some(i => i.id === id), [items]);

  return { items, pin, unpin, togglePin, isPinned };
}
