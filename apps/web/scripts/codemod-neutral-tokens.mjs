#!/usr/bin/env node
/**
 * Deterministik codemod: neutral renk ailesini (gray/slate/white/border) semantic
 * token'lara çevirir. Light/dark inversiyonu token katmanında otomatik çözülür.
 *
 * KASITLI OLARAK DOKUNULMAYANLAR:
 *  - Semantic renkler (red/green/blue/amber/emerald/violet/indigo...) → bağlam gerektirir
 *  - text-white → renkli buton üstünde kasıtlı
 *  - bg-gray-500 / bg-gray-600 → nadir, manuel inceleme
 *
 * Kullanım: node scripts/codemod-neutral-tokens.mjs <dosya1> <dosya2> ...
 */
import { readFileSync, writeFileSync } from "node:fs";

// Variant prefix'i (hover:/focus:/group-hover:/active:/md: vb.) koruyarak class gövdesini map et.
const MAP = [
  ["bg-white", "bg-surface-raised"],
  ["bg-gray-50", "bg-surface"],
  ["bg-gray-100", "bg-surface-overlay"],
  ["bg-gray-200", "bg-surface-overlay"],
  ["bg-slate-50", "bg-surface"],
  ["bg-slate-100", "bg-surface-overlay"],
  ["bg-slate-200", "bg-surface-overlay"],
  ["border-gray-100", "border-border"],
  ["border-gray-200", "border-border"],
  ["border-gray-300", "border-border"],
  ["border-slate-100", "border-border"],
  ["border-slate-200", "border-border"],
  ["border-slate-300", "border-border"],
  ["divide-gray-100", "divide-border"],
  ["divide-gray-200", "divide-border"],
  ["text-gray-900", "text-fg"],
  ["text-gray-800", "text-fg"],
  ["text-gray-700", "text-fg"],
  ["text-gray-600", "text-fg-muted"],
  ["text-gray-500", "text-fg-subtle"],
  ["text-gray-400", "text-fg-subtle"],
  ["text-gray-300", "text-fg-disabled"],
  ["text-slate-900", "text-fg"],
  ["text-slate-700", "text-fg"],
  ["text-slate-600", "text-fg-muted"],
  ["text-slate-500", "text-fg-subtle"],
  ["text-slate-400", "text-fg-subtle"],
  ["placeholder-gray-400", "placeholder-fg-subtle"],
  ["placeholder-gray-500", "placeholder-fg-subtle"],
];

// En uzun class adından kısaya sırala ki "bg-gray-50" "bg-gray-500"'ü yanlış eşlemesin.
MAP.sort((a, b) => b[0].length - a[0].length);

const PREFIX = "(?:[a-z-]+:)*"; // hover: focus: group-hover: md: vb. zincirlerini korur

let totalChanges = 0;
for (const file of process.argv.slice(2)) {
  let src = readFileSync(file, "utf8");
  let fileChanges = 0;
  for (const [from, to] of MAP) {
    // Sınır: class'tan önce sınır karakteri, sonra word-boundary (sonraki -[0-9] yoksa)
    const re = new RegExp(`(${PREFIX})${from.replace(/[-]/g, "\\-")}(?![\\w-])`, "g");
    src = src.replace(re, (_m, p) => {
      fileChanges++;
      return `${p}${to}`;
    });
  }
  if (fileChanges > 0) {
    writeFileSync(file, src);
    totalChanges += fileChanges;
    console.log(`${String(fileChanges).padStart(4)}  ${file}`);
  }
}
console.log(`\nToplam ${totalChanges} değişiklik.`);
