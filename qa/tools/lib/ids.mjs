import { DOMAIN_PREFIXES } from "./domains.mjs";

const PATTERNS = {
  tc: /^TC-([A-Z0-9]+)-(\d{3,})$/,
  pre: /^PRE-(\d{3,})$/,
  ss: /^SS-(\d{3,})$/,
  req: /^REQ-([A-Z0-9]+)-(\d{3,})$/,
  plan: /^TP-(\d{4}\.Q[1-4])-([A-Z0-9-]+)$/,
  milestone: /^R-(\d{4})\.(Q[1-4])$/,
  run: /^TR-(\d{4})-(\d{2})-(\d{2})-([A-Z0-9-]+)-(\d{3,})$/,
  defect: /^GH-(\d+)$/,
  exp: /^EXP-(\d{4})-(\d{2})-(\d{2})-([a-z0-9-]+)$/,
  suite: /^SUITE-([A-Z0-9]+)$/,
};

const KIND_FOR_PREFIX = {
  TC: "tc",
  PRE: "pre",
  SS: "ss",
  REQ: "req",
  TP: "plan",
  R: "milestone",
  TR: "run",
  GH: "defect",
  EXP: "exp",
  SUITE: "suite",
};

export function detectKind(id) {
  if (typeof id !== "string") return null;
  const head = id.split("-")[0];
  return KIND_FOR_PREFIX[head] ?? null;
}

export function validateId(id) {
  const kind = detectKind(id);
  if (!kind) return { ok: false, reason: "unknown_prefix" };

  const pattern = PATTERNS[kind];
  const match = pattern.exec(id);
  if (!match) return { ok: false, reason: "pattern_mismatch", pattern: pattern.source };

  if (kind === "tc" || kind === "req") {
    const domain = match[1];
    if (!DOMAIN_PREFIXES.includes(domain)) {
      return { ok: false, reason: "unknown_domain", domain };
    }
  }

  return { ok: true, kind };
}

export function nextSequence(existingIds, prefix) {
  let max = 0;
  for (const id of existingIds) {
    if (!id.startsWith(prefix + "-")) continue;
    const tail = id.slice(prefix.length + 1);
    const num = parseInt(tail, 10);
    if (!Number.isNaN(num) && num > max) max = num;
  }
  return String(max + 1).padStart(3, "0");
}

export function slugify(text, maxLength = 50) {
  const turkishMap = { ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u", İ: "i" };
  return text
    .toLowerCase()
    .split("")
    .map((ch) => turkishMap[ch] ?? ch)
    .join("")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, maxLength)
    .replace(/-+$/g, "");
}
