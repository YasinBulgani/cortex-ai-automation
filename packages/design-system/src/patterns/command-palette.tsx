"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";
import { Kbd } from "../primitives/kbd";

export interface CommandItem {
  id: string;
  label: React.ReactNode;
  /** Arama indeksinde kullanılan text */
  keywords?: string[];
  /** Sol ikon */
  icon?: React.ReactNode;
  /** Sağ kısayol metni */
  shortcut?: string;
  /** Grup (header) — verilirse aynı group başlık altında toplanır */
  group?: string;
  /** Tehlikeli (kırmızı) */
  danger?: boolean;
  /** Pasif */
  disabled?: boolean;
  /** Çağrı */
  onSelect: () => void;
}

export interface CommandPaletteProps {
  /** Açık mı (controlled) */
  open: boolean;
  /** Kapanma talebi */
  onOpenChange: (open: boolean) => void;
  /** Tüm komutlar */
  items: ReadonlyArray<CommandItem>;
  /** Input placeholder */
  placeholder?: string;
  /** Boş arama sonucu */
  emptyMessage?: React.ReactNode;
  /** Arama özelleştir — default: label + keywords içerme (case-insensitive) */
  filter?: (query: string, item: CommandItem) => boolean;
  /** Maks görünür sonuç (perf için) */
  maxResults?: number;
  className?: string;
}

/**
 * CommandPalette — Spotlight-tarzı keyboard-driven launcher.
 *
 * - Modal overlay; ESC veya overlay click kapatır.
 * - Input otomatik focus.
 * - ↑↓ navigasyon, Enter seç, ⌘K ile dışarıdan açmak için kullanıcı kendi
 *   shortcut wiring'ini yapar (örn. useEffect + keydown).
 * - Group desteği: aynı `group` etiketi olan item'lar başlık altında toplanır.
 * - Default fuzzy-light filter: label ve keywords içinde her token aranır.
 */
export function CommandPalette({
  open,
  onOpenChange,
  items,
  placeholder = "Komut ara veya bir sayfaya git…",
  emptyMessage = "Sonuç yok",
  filter,
  maxResults = 50,
  className,
}: CommandPaletteProps) {
  const [query, setQuery] = React.useState("");
  const [activeIndex, setActiveIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement | null>(null);

  // Reset on close
  React.useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveIndex(0);
    } else {
      // Auto-focus input
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  // Body scroll lock
  React.useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  // Filter + group
  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    const defaultFilter = (item: CommandItem) => {
      if (!q) return true;
      const haystack = [
        typeof item.label === "string" ? item.label : "",
        ...(item.keywords ?? []),
      ].join(" ").toLowerCase();
      // Tüm token'lar geçmeli
      return q.split(/\s+/).every(token => haystack.includes(token));
    };
    const test = filter
      ? (it: CommandItem) => filter(q, it)
      : defaultFilter;

    return items.filter(test).slice(0, maxResults);
  }, [items, query, filter, maxResults]);

  // Gruplar
  const grouped = React.useMemo(() => {
    const map = new Map<string | undefined, CommandItem[]>();
    for (const item of filtered) {
      const g = item.group;
      const arr = map.get(g) ?? [];
      arr.push(item);
      map.set(g, arr);
    }
    return Array.from(map.entries()).map(([group, items]) => ({ group, items }));
  }, [filtered]);

  const flatActive = filtered.filter(it => !it.disabled);

  // Reset active on filter change
  React.useEffect(() => {
    setActiveIndex(0);
  }, [filtered.length]);

  const select = (item: CommandItem) => {
    if (item.disabled) return;
    item.onSelect();
    onOpenChange(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onOpenChange(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex(i => (i + 1) % Math.max(1, flatActive.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex(i => (i - 1 + flatActive.length) % Math.max(1, flatActive.length));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = flatActive[activeIndex];
      if (item) select(item);
    } else if (e.key === "Home") {
      e.preventDefault();
      setActiveIndex(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setActiveIndex(Math.max(0, flatActive.length - 1));
    }
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Komut paleti"
      className="fixed inset-0 z-[9999] flex items-start justify-center p-4 pt-[15vh]"
      onKeyDown={handleKeyDown}
      data-testid="command-palette"
    >
      <div
        aria-hidden
        className="absolute inset-0 bg-black/60"
        onClick={() => onOpenChange(false)}
        data-testid="command-overlay"
      />
      <div
        className={cn(
          "relative w-full max-w-xl overflow-hidden rounded-xl border border-border bg-surface-raised shadow-2xl",
          className,
        )}
      >
        <div className="flex items-center gap-2 border-b border-border px-3 py-2.5">
          <span aria-hidden className="text-fg-subtle">🔍</span>
          <input
            ref={inputRef}
            type="text"
            placeholder={placeholder}
            value={query}
            onChange={e => setQuery(e.target.value)}
            className={cn(
              "flex-1 bg-transparent text-sm text-fg placeholder:text-fg-subtle outline-none",
              focusRing,
            )}
            aria-label="Komut ara"
            data-testid="command-input"
          />
          <Kbd>ESC</Kbd>
        </div>
        <div
          role="listbox"
          aria-label="Komutlar"
          className="max-h-[50vh] overflow-y-auto py-1"
        >
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-fg-subtle">
              {emptyMessage}
            </div>
          ) : (
            grouped.map(({ group, items: groupItems }) => (
              <div key={group ?? "__default"} className="px-1">
                {group && (
                  <div
                    className="px-2 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle"
                    role="presentation"
                  >
                    {group}
                  </div>
                )}
                {groupItems.map(it => {
                  const flatIdx = flatActive.indexOf(it);
                  const isActive = flatIdx === activeIndex;
                  return (
                    <button
                      key={it.id}
                      type="button"
                      role="option"
                      aria-selected={isActive}
                      disabled={it.disabled}
                      onMouseMove={() => !it.disabled && flatIdx >= 0 && setActiveIndex(flatIdx)}
                      onClick={() => select(it)}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors text-left",
                        "disabled:cursor-not-allowed disabled:opacity-50",
                        it.danger
                          ? "text-danger hover:bg-danger-subtle"
                          : "text-fg hover:bg-surface-overlay",
                        isActive && (it.danger ? "bg-danger-subtle" : "bg-surface-overlay"),
                      )}
                      data-testid={`command-item-${it.id}`}
                    >
                      {it.icon && <span className="shrink-0">{it.icon}</span>}
                      <span className="flex-1 truncate">{it.label}</span>
                      {it.shortcut && (
                        <Kbd className="ml-2">{it.shortcut}</Kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
