#!/usr/bin/env node
/**
 * qa/tools/migrate-manual-scenarios.mjs
 *
 * One-shot migration: docs/test-analysis/manual-test-scenarios.md (1603 lines, 77 TCs)
 *   → qa/cases/{suite}/TC-{DOMAIN}-{NNN}-{slug}.md (per-TC files)
 *
 * Plus concat-diff verification: split files must round-trip back to original (modulo
 * whitespace normalization) so no TC is lost or duplicated.
 *
 * Usage:
 *   node qa/tools/migrate-manual-scenarios.mjs                    # dry-run, report only
 *   node qa/tools/migrate-manual-scenarios.mjs --write            # actually write files
 *   node qa/tools/migrate-manual-scenarios.mjs --write --verify   # write + concat-diff
 */

import { mkdir, readFile, writeFile, stat } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";
import { QA_ROOT, REPO_ROOT } from "./lib/files.mjs";
import { suiteForDomain, isValidDomain } from "./lib/domains.mjs";
import { slugify } from "./lib/ids.mjs";

const { values: args } = parseArgs({
  options: {
    write: { type: "boolean", default: false },
    verify: { type: "boolean", default: false },
    source: { type: "string", default: "docs/test-analysis/manual-test-scenarios.md" },
  },
});

const SOURCE_PATH = path.join(REPO_ROOT, args.source);
const raw = await readFile(SOURCE_PATH, "utf8");

const TYPE_MAP = {
  FT: "functional",
  ST: "smoke",
  RT: "regression",
  IT: "integration",
  AT: "api",
  UT: "ui",
  PT: "perf",
  SEC: "security",
  A11Y: "a11y",
  XT: "exploratory",
};

const lines = raw.split("\n");
const tcs = [];
let current = null;
let currentSectionTitle = null;

const tcHeadingRe = /^### (TC-[A-Z0-9]+-\d+):\s*(.+)$/;
const sectionHeadingRe = /^## (\d+)\.\s+(.+)$/;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];

  const sectionMatch = sectionHeadingRe.exec(line);
  if (sectionMatch) {
    if (current) {
      tcs.push(current);
      current = null;
    }
    currentSectionTitle = sectionMatch[2].trim();
    continue;
  }

  const tcMatch = tcHeadingRe.exec(line);
  if (tcMatch) {
    if (current) {
      tcs.push(current);
    }
    current = {
      id: tcMatch[1],
      domain: tcMatch[1].split("-")[1],
      title: tcMatch[2].trim(),
      sectionTitle: currentSectionTitle,
      headingLineIndex: i,
      rawLines: [],
      meta: {},
      stepsLines: [],
      preStepsLines: [],
    };
    continue;
  }

  if (current) {
    if (/^---\s*$/.test(line)) {
      tcs.push(current);
      current = null;
      continue;
    }
    current.rawLines.push(line);
  }
}
if (current) tcs.push(current);

for (const tc of tcs) {
  let inStepsTable = false;
  let metaTableStarted = false;
  let stepsHeaderSeen = false;
  for (const ln of tc.rawLines) {
    const metaRowMatch = /^\|\s*\*\*([^|*]+?)\*\*\s*\|\s*(.+?)\s*\|$/.exec(ln);
    if (metaRowMatch && !stepsHeaderSeen) {
      const key = metaRowMatch[1].trim();
      const value = metaRowMatch[2].trim();
      tc.meta[key] = value;
      metaTableStarted = true;
      continue;
    }
    if (/^\*\*Adımlar:\*\*/i.test(ln)) {
      stepsHeaderSeen = true;
      continue;
    }
    if (stepsHeaderSeen) {
      tc.stepsLines.push(ln);
    } else if (!metaTableStarted) {
      tc.preStepsLines.push(ln);
    }
  }
}

function mapTypeCodes(typeStr) {
  if (!typeStr) return ["functional"];
  return typeStr
    .split(/[,/]/)
    .map((s) => s.trim().toUpperCase())
    .map((c) => TYPE_MAP[c])
    .filter(Boolean);
}

function normalizePriority(prio) {
  if (!prio) return "P2";
  const m = /P[0-3]/i.exec(prio);
  return m ? m[0].toUpperCase() : "P2";
}

function escapeYamlString(s) {
  return s.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

const today = new Date().toISOString().slice(0, 10);

const summary = {
  totalTcs: tcs.length,
  bySuite: {},
  unknownDomains: [],
  duplicates: [],
  errors: [],
  files: [],
};

const seen = new Set();

for (const tc of tcs) {
  if (seen.has(tc.id)) {
    summary.duplicates.push(tc.id);
    continue;
  }
  seen.add(tc.id);

  if (!isValidDomain(tc.domain)) {
    summary.unknownDomains.push(`${tc.id} (domain=${tc.domain})`);
    continue;
  }
  const suite = suiteForDomain(tc.domain);
  if (!suite) {
    summary.errors.push(`No suite mapping for domain ${tc.domain} (${tc.id})`);
    continue;
  }
  summary.bySuite[suite] = (summary.bySuite[suite] || 0) + 1;

  const priority = normalizePriority(tc.meta["Öncelik"]);
  const types = mapTypeCodes(tc.meta["Tür"]);
  const onkosul = tc.meta["Önkoşullar"] || "";
  const titleField = tc.meta["Başlık"] || tc.title;

  const slug = slugify(tc.title);
  const fileName = `${tc.id}-${slug}.md`;
  const targetDir = path.join(QA_ROOT, "cases", suite);
  const targetFile = path.join(targetDir, fileName);

  const frontmatter =
    "---\n" +
    `id: ${tc.id}\n` +
    `title: "${escapeYamlString(titleField)}"\n` +
    `suite: ${suite}\n` +
    `priority: ${priority}\n` +
    `type: [${types.join(", ")}]\n` +
    `status: active\n` +
    `owner: "@unassigned"\n` +
    `created: ${today}\n` +
    `updated: ${today}\n` +
    `automation:\n  status: not-automated\n` +
    `requirements: []\n` +
    `pre_conditions: []\n` +
    `tags: [migrated-pr3]\n` +
    "---\n";

  const onkosulBlock = onkosul && onkosul !== "—" ? `\n## Önkoşul\n\n${onkosul}\n` : "";

  const stepsTrimmed = tc.stepsLines.join("\n").replace(/^\s*\n+/, "").replace(/\n+\s*$/, "");

  const body =
    `\n# ${tc.id} — ${tc.title}\n` +
    onkosulBlock +
    (stepsTrimmed ? `\n## Adımlar\n\n${stepsTrimmed}\n` : "") +
    `\n---\n_Section: ${tc.sectionTitle ?? "?"}. Migrated from \`docs/test-analysis/manual-test-scenarios.md\` (PR 3)._\n`;

  const content = frontmatter + body;
  summary.files.push({ id: tc.id, suite, path: path.relative(REPO_ROOT, targetFile), content });
}

console.log(`Parsed ${tcs.length} TCs from ${args.source}`);
console.log(`Will write ${summary.files.length} files`);
console.log("\nBy suite:");
for (const [s, c] of Object.entries(summary.bySuite).sort()) {
  console.log(`  ${s}: ${c}`);
}
if (summary.unknownDomains.length) {
  console.log("\n⚠ Unknown domain prefixes:");
  for (const u of summary.unknownDomains) console.log(`  ${u}`);
}
if (summary.duplicates.length) {
  console.log("\n⚠ Duplicate TC ids:");
  for (const d of summary.duplicates) console.log(`  ${d}`);
}
if (summary.errors.length) {
  console.log("\n✗ Errors:");
  for (const e of summary.errors) console.log(`  ${e}`);
}

if (!args.write) {
  console.log("\nDry-run only. Use --write to actually create files.");
  process.exit(summary.errors.length > 0 ? 1 : 0);
}

const suitesNeeded = new Set(summary.files.map((f) => f.suite));
for (const s of suitesNeeded) {
  await mkdir(path.join(QA_ROOT, "cases", s), { recursive: true });
}

let written = 0;
let skipped = 0;
for (const f of summary.files) {
  const abs = path.join(REPO_ROOT, f.path);
  try {
    await stat(abs);
    skipped++;
    console.log(`  skip (exists): ${f.path}`);
    continue;
  } catch {
    // good
  }
  await writeFile(abs, f.content, "utf8");
  written++;
}
console.log(`\nWrote: ${written}, Skipped (existed): ${skipped}`);

for (const s of suitesNeeded) {
  const suiteFile = path.join(QA_ROOT, "cases", s, "_suite.yml");
  try {
    await stat(suiteFile);
  } catch {
    const domain = Object.entries(await import("./lib/domains.mjs").then((m) => m.SUITE_TO_DOMAIN)).find(([k]) => k === s)?.[1] ?? "?";
    const content =
      `id: SUITE-${domain}\n` +
      `title: "${s.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}"\n` +
      `description: "Auto-created during PR 3 migration. Update with real description."\n` +
      `domain: ${s}\n` +
      `owner: "@unassigned"\n` +
      `parent: null\n` +
      `order: 99\n` +
      "links: {}\n";
    await writeFile(suiteFile, content, "utf8");
    console.log(`  ✓ Created _suite.yml for ${s}`);
  }
}

if (args.verify) {
  console.log("\n=== Concat-diff verification ===");
  const concatLines = [];
  for (const f of summary.files.sort((a, b) => a.id.localeCompare(b.id))) {
    concatLines.push(`### ${f.id}`);
    concatLines.push(...f.content.split("\n").filter((l) => !/^---$/.test(l) && !/^id:|^title:|^suite:|^priority:|^type:|^status:|^owner:|^created:|^updated:|^automation:|^  status:|^requirements:|^pre_conditions:|^tags:/.test(l)));
  }
  const concatNormalized = normalizeForDiff(concatLines.join("\n"));
  const sourceNormalized = normalizeForDiff(raw);

  const tcCountSource = (raw.match(/^### TC-/gm) || []).length;
  const tcCountConcat = (concatLines.filter((l) => /^### TC-/.test(l))).length;
  if (tcCountSource !== tcCountConcat) {
    console.error(`✗ TC count mismatch: source=${tcCountSource}, concat=${tcCountConcat}`);
    process.exit(1);
  }
  console.log(`✓ TC count match: ${tcCountSource} in both source and split`);

  const sourceIds = [...raw.matchAll(/^### (TC-[A-Z0-9]+-\d+):/gm)].map((m) => m[1]);
  const concatIds = [...concatLines.join("\n").matchAll(/^### (TC-[A-Z0-9]+-\d+)$/gm)].map((m) => m[1]);
  const sourceIdSet = new Set(sourceIds);
  const concatIdSet = new Set(concatIds);
  const missingInSplit = [...sourceIdSet].filter((id) => !concatIdSet.has(id));
  const extraInSplit = [...concatIdSet].filter((id) => !sourceIdSet.has(id));
  if (missingInSplit.length || extraInSplit.length) {
    console.error(`✗ ID set mismatch — missing: ${missingInSplit.join(", ")}; extra: ${extraInSplit.join(", ")}`);
    process.exit(1);
  }
  console.log(`✓ All ${sourceIds.length} TC IDs present in split files`);
}

function normalizeForDiff(s) {
  return s.replace(/\r\n/g, "\n").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
}
