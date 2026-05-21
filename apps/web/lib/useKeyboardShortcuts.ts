"use client";

import { useEffect } from "react";

export type Shortcut = {
  /** Key combo string. Modifier order: mod+shift+alt+<key>. mod = Cmd on Mac, Ctrl elsewhere. */
  combo: string;
  /** Description shown in the help panel. */
  description: string;
  /** Handler called when combo matches. */
  handler: (e: KeyboardEvent) => void;
  /** When true, prevent default browser shortcut. Default true. */
  preventDefault?: boolean;
  /** Allow firing while focus is on an input/textarea/contenteditable. Default false. */
  allowInInputs?: boolean;
};

function isMac(): boolean {
  if (typeof navigator === "undefined") return false;
  return navigator.platform?.toLowerCase().includes("mac");
}

/** Normalize a combo string ("Cmd+K", "ctrl+shift+P") to a canonical form. */
export function normalizeCombo(combo: string): string {
  const parts = combo
    .toLowerCase()
    .split("+")
    .map((p) => p.trim());
  const mods = new Set<string>();
  let key = "";
  for (const p of parts) {
    if (p === "mod" || p === "cmd" || p === "ctrl" || p === "meta") mods.add("mod");
    else if (p === "shift") mods.add("shift");
    else if (p === "alt" || p === "option") mods.add("alt");
    else key = p;
  }
  const order = ["mod", "shift", "alt"];
  return [...order.filter((m) => mods.has(m)), key].join("+");
}

function eventCombo(e: KeyboardEvent): string {
  const parts: string[] = [];
  if (e.metaKey || e.ctrlKey) parts.push("mod");
  if (e.shiftKey) parts.push("shift");
  if (e.altKey) parts.push("alt");
  const key = e.key.toLowerCase();
  if (key === " ") parts.push("space");
  else parts.push(key);
  return parts.join("+");
}

function isInInput(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  if (target.isContentEditable) return true;
  return false;
}

/**
 * Global keyboard shortcuts hook.
 *
 * Usage:
 *    useKeyboardShortcuts([
 *      { combo: "mod+k", description: "Komut paleti", handler: openPalette },
 *      { combo: "g s",   description: "Senaryolara git", handler: goScenarios }, // chord
 *    ]);
 *
 * Chord (2-step) support: combos with space are treated as 2-press chords —
 * first press arms, second press fires within 1.5s.
 */
export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const single: Map<string, Shortcut> = new Map();
    const chordPrefix: Map<string, Map<string, Shortcut>> = new Map();

    for (const s of shortcuts) {
      // Chord = "g s" (space-separated)
      if (s.combo.trim().includes(" ")) {
        const [first, second] = s.combo.trim().toLowerCase().split(/\s+/);
        if (!chordPrefix.has(first)) chordPrefix.set(first, new Map());
        chordPrefix.get(first)!.set(second, s);
      } else {
        single.set(normalizeCombo(s.combo), s);
      }
    }

    let chordArmed: string | null = null;
    let chordTimer: any = null;

    const onKey = (e: KeyboardEvent) => {
      // Disarm chord if a different non-modifier key arrives
      if (e.key === "Shift" || e.key === "Control" || e.key === "Alt" || e.key === "Meta") {
        return;
      }

      const inInput = isInInput(e.target);

      // Chord 2nd key (if armed)
      if (chordArmed) {
        const second = e.key.toLowerCase();
        const opts = chordPrefix.get(chordArmed);
        const matched = opts?.get(second);
        if (matched) {
          if (inInput && !matched.allowInInputs) {
            // Don't fire in inputs by default
          } else {
            if (matched.preventDefault !== false) e.preventDefault();
            matched.handler(e);
          }
        }
        chordArmed = null;
        clearTimeout(chordTimer);
        return;
      }

      // First key — check if it could arm a chord
      const key = e.key.toLowerCase();
      if (!e.metaKey && !e.ctrlKey && !e.altKey && chordPrefix.has(key)) {
        if (!inInput) {
          chordArmed = key;
          chordTimer = setTimeout(() => {
            chordArmed = null;
          }, 1500);
          return;
        }
      }

      // Check single combo match
      const combo = eventCombo(e);
      const matched = single.get(combo);
      if (matched) {
        if (inInput && !matched.allowInInputs) return;
        if (matched.preventDefault !== false) e.preventDefault();
        matched.handler(e);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      if (chordTimer) clearTimeout(chordTimer);
    };
  }, [shortcuts]);
}

/** Render-friendly representation of a combo. */
export function displayCombo(combo: string): string {
  const mac = isMac();
  const segs = combo.split("+").map((s) => s.trim());
  return segs
    .map((s) => {
      if (s === "mod") return mac ? "⌘" : "Ctrl";
      if (s === "shift") return mac ? "⇧" : "Shift";
      if (s === "alt") return mac ? "⌥" : "Alt";
      return s.toUpperCase();
    })
    .join(mac ? "" : "+");
}
