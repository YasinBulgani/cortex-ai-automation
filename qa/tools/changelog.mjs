#!/usr/bin/env node
/**
 * qa/tools/changelog.mjs
 *
 * qa/ klasörüne özel git commit log → qa/CHANGELOG.md üretir.
 * Conventional commits varsa kategoriler (Added, Changed, Fixed, ...).
 *
 * Usage:
 *   node qa/tools/changelog.mjs              # tüm history
 *   node qa/tools/changelog.mjs --since=v1.0 # son tag'den beri
 *   node qa/tools/changelog.mjs --write      # qa/CHANGELOG.md'e yaz
 */

import { writeFile } from "node:fs/promises";
import path from "node:path";
import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import { QA_ROOT, REPO_ROOT } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    since: { type: "string" },
    write: { type: "boolean", default: false },
    "max-commits": { type: "string", default: "200" },
  },
});

const range = args.since ? `${args.since}..HEAD` : "";
const maxCount = parseInt(args["max-commits"], 10) || 200;

const log = execSync(
  `git log --pretty=format:'%H|%ad|%an|%s' --date=short -n ${maxCount} ${range} -- qa/`,
  { cwd: REPO_ROOT, encoding: "utf8" },
).trim();

if (!log) {
  console.log("No commits found for qa/.");
  process.exit(0);
}

const commits = log.split("\n").map((line) => {
  const [hash, date, author, subject] = line.split("|");
  return { hash, date, author, subject };
});

const categories = {
  added: [],
  changed: [],
  fixed: [],
  removed: [],
  docs: [],
  other: [],
};

for (const c of commits) {
  const s = c.subject.toLowerCase();
  if (/^(feat|add)[:(]/.test(s) || s.includes("add ") || s.startsWith("create")) categories.added.push(c);
  else if (/^fix[:(]/.test(s) || s.includes(" fix ")) categories.fixed.push(c);
  else if (/^(refactor|chore|perf|update|change)[:(]/.test(s)) categories.changed.push(c);
  else if (/^(remove|delete)[:(]/.test(s) || s.includes("remove ") || s.includes("delete ")) categories.removed.push(c);
  else if (/^docs?[:(]/.test(s)) categories.docs.push(c);
  else categories.other.push(c);
}

const lines = [
  "# qa/ Changelog",
  "",
  `_Otomatik üretildi — \`qa/tools/changelog.mjs\` ile. Son güncelleme: ${new Date().toISOString().slice(0, 10)}._`,
  "",
  `Toplam ${commits.length} commit, ${args.since ? `${args.since} → HEAD` : "tüm history"}.`,
  "",
];

const sections = [
  ["Added", categories.added],
  ["Changed", categories.changed],
  ["Fixed", categories.fixed],
  ["Removed", categories.removed],
  ["Documentation", categories.docs],
  ["Other", categories.other],
];

for (const [title, items] of sections) {
  if (items.length === 0) continue;
  lines.push(`## ${title} (${items.length})`);
  lines.push("");
  for (const c of items.slice(0, 50)) {
    lines.push(`- \`${c.hash.slice(0, 7)}\` ${c.date} — ${escapeMd(c.subject)} _(${c.author})_`);
  }
  if (items.length > 50) lines.push(`- _... +${items.length - 50} more_`);
  lines.push("");
}

const out = lines.join("\n");

if (args.write) {
  const outPath = path.join(QA_ROOT, "CHANGELOG.md");
  await writeFile(outPath, out, "utf8");
  console.log(`✓ ${path.relative(REPO_ROOT, outPath)} (${commits.length} commits)`);
} else {
  console.log(out);
}

function escapeMd(s) {
  return s.replace(/\|/g, "\\|").replace(/`/g, "\\`");
}
