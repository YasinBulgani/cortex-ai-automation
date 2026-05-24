#!/usr/bin/env node
/**
 * qa/tools/tc-promote.mjs
 *
 * AI-suggest tarafından üretilen _draft/ TC'lerini active TC'lere promote eder.
 *
 * Akış:
 *   1. _draft/DRAFT-TC-*.md'i listele
 *   2. Her birini hızlıca göster (id, title, ai-generated tag)
 *   3. Kullanıcı seçimi: promote (interactive: confirm), edit (open in $EDITOR), skip, delete
 *   4. Promote: filename DRAFT- prefix kaldır, frontmatter status: draft→active, owner update
 *   5. cases/{suite}/{ID}-{slug}.md'e taşı
 *
 * Usage:
 *   node qa/tools/tc-promote.mjs                          # interactive list
 *   node qa/tools/tc-promote.mjs --id=TC-AUTH-018         # specific promote
 *   node qa/tools/tc-promote.mjs --suite=auth --all       # bulk promote (with confirm)
 */

import { mkdir, readFile, writeFile, readdir, unlink, stat } from "node:fs/promises";
import path from "node:path";
import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import { intro, outro, select, confirm, isCancel, cancel, log } from "@clack/prompts";
import { QA_ROOT } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    id: { type: "string" },
    suite: { type: "string" },
    all: { type: "boolean", default: false },
  },
});

intro("qa/ tc-promote");

const drafts = await findAllDrafts();
if (drafts.length === 0) {
  log.info("No drafts found in qa/cases/**/_draft/. Run ai-suggest first.");
  outro("Done.");
  process.exit(0);
}
log.info(`Found ${drafts.length} draft(s)`);

let targets = drafts;
if (args.id) {
  targets = drafts.filter((d) => d.id === args.id);
  if (targets.length === 0) {
    log.warn(`No draft with id=${args.id}`);
    process.exit(1);
  }
}
if (args.suite) {
  targets = targets.filter((d) => d.suite === args.suite);
}

let promoted = 0;
let skipped = 0;
let deleted = 0;

const owner = gitUser();

for (const d of targets) {
  let action;
  if (args.all) {
    const ok = await confirm({
      message: `Promote ${d.id} (${d.title})?`,
      initialValue: true,
    });
    if (isCancel(ok)) return cancelExit();
    action = ok ? "promote" : "skip";
  } else {
    const choice = await select({
      message: `${d.id} — ${d.title}`,
      options: [
        { value: "promote", label: "✓ Promote → active TC" },
        { value: "skip", label: "↪ Skip (leave as draft)" },
        { value: "delete", label: "✗ Delete (reject draft)" },
      ],
    });
    if (isCancel(choice)) return cancelExit();
    action = choice;
  }

  if (action === "skip") {
    skipped++;
    continue;
  }
  if (action === "delete") {
    await unlink(d.path);
    log.warn(`Deleted ${path.relative(QA_ROOT, d.path)}`);
    deleted++;
    continue;
  }

  // Promote
  const updated = d.raw
    .replace(/^status:\s+draft$/m, "status: active")
    .replace(/^owner:\s+"@ai-suggest"$/m, `owner: "${owner}"`)
    .replace(/^tags:\s+\[ai-generated\]$/m, "tags: [ai-generated, promoted]")
    .replace(/\n---\n_AI tarafından üretildi\..*?_\n?$/m, "")
    .replace(/_AI tarafından üretildi\..*?$/m, "");

  const newName = d.fileName.replace(/^DRAFT-/, "");
  const newPath = path.join(path.dirname(path.dirname(d.path)), newName);

  if (await fileExists(newPath)) {
    log.error(`Target already exists: ${path.relative(QA_ROOT, newPath)} — skipping`);
    skipped++;
    continue;
  }

  await writeFile(newPath, updated, "utf8");
  await unlink(d.path);
  promoted++;
  log.success(`Promoted ${d.id} → ${path.relative(QA_ROOT, newPath)}`);
}

outro(`Done. promoted=${promoted}, skipped=${skipped}, deleted=${deleted}`);

if (promoted > 0) {
  log.info("Run 'npm run validate' and 'npm run trace' to refresh.");
}

function cancelExit() {
  cancel("Cancelled.");
  process.exit(0);
}

function gitUser() {
  try {
    const n = execSync("git config user.name", { encoding: "utf8" }).trim();
    return n ? `@${n.toLowerCase().replace(/\s+/g, "-")}` : "@unassigned";
  } catch {
    return "@unassigned";
  }
}

async function findAllDrafts() {
  const drafts = [];
  const suitesDir = path.join(QA_ROOT, "cases");
  let suites;
  try {
    suites = await readdir(suitesDir);
  } catch {
    return drafts;
  }
  for (const suite of suites) {
    const draftDir = path.join(suitesDir, suite, "_draft");
    let files;
    try {
      files = await readdir(draftDir);
    } catch {
      continue;
    }
    for (const f of files) {
      if (!f.startsWith("DRAFT-TC-") || !f.endsWith(".md")) continue;
      const fp = path.join(draftDir, f);
      const raw = await readFile(fp, "utf8");
      const id = /^id:\s+(TC-[A-Z0-9]+-\d+)/m.exec(raw)?.[1] || "?";
      const title = /^title:\s+"(.+)"/m.exec(raw)?.[1] || "(no title)";
      drafts.push({ id, title, suite, fileName: f, path: fp, raw });
    }
  }
  return drafts;
}

async function fileExists(p) {
  try { await stat(p); return true; } catch { return false; }
}
