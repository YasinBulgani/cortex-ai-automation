#!/usr/bin/env node
/**
 * qa/tools/new-tc.mjs
 *
 * Creates a new test case markdown file with auto-incremented ID, frontmatter scaffold, body template.
 *
 * Usage:
 *   node qa/tools/new-tc.mjs --suite=auth --title="MFA login akışı"
 *   node qa/tools/new-tc.mjs --suite=auth --title="..." --priority=P1 --type=functional,security
 */

import { mkdir, writeFile, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";
import { execSync } from "node:child_process";

import { QA_ROOT, loadAllTestCases } from "./lib/files.mjs";
import { domainForSuite, isValidDomain } from "./lib/domains.mjs";
import { nextSequence, slugify } from "./lib/ids.mjs";

const { values: args } = parseArgs({
  options: {
    suite: { type: "string" },
    title: { type: "string" },
    priority: { type: "string", default: "P2" },
    type: { type: "string", default: "functional" },
    owner: { type: "string" },
    "dry-run": { type: "boolean", default: false },
  },
});

if (!args.suite || !args.title) {
  console.error("Usage: new-tc --suite=<suite> --title=\"<title>\" [--priority=P0|P1|P2|P3] [--type=functional,smoke]");
  process.exit(2);
}

const suite = args.suite;
const domain = domainForSuite(suite);
if (!domain) {
  console.error(`Unknown suite '${suite}'. Map it in qa/tools/lib/domains.mjs first.`);
  process.exit(2);
}
if (!isValidDomain(domain)) {
  console.error(`Domain prefix '${domain}' not registered in CONVENTIONS.md.`);
  process.exit(2);
}

const allTcs = await loadAllTestCases();
const existingIds = allTcs.map((t) => t.data?.id).filter(Boolean);
const sequence = nextSequence(existingIds, `TC-${domain}`);
const id = `TC-${domain}-${sequence}`;
const slug = slugify(args.title);
const fileName = `${id}-${slug}.md`;

const suiteDir = path.join(QA_ROOT, "cases", suite);
const filePath = path.join(suiteDir, fileName);

function gitUser() {
  if (args.owner) return args.owner.startsWith("@") ? args.owner : `@${args.owner}`;
  try {
    const name = execSync("git config user.name", { encoding: "utf8" }).trim();
    return name ? `@${name.toLowerCase().replace(/\s+/g, "-")}` : "@unknown";
  } catch {
    return "@unknown";
  }
}

const today = new Date().toISOString().slice(0, 10);
const types = args.type.split(",").map((s) => s.trim()).filter(Boolean);
const owner = gitUser();

const frontmatter = `---
id: ${id}
title: "${args.title.replace(/"/g, '\\"')}"
suite: ${suite}
priority: ${args.priority}
type: [${types.join(", ")}]
status: draft
owner: "${owner}"
created: ${today}
updated: ${today}
estimated_minutes: 5
automation:
  status: not-automated
requirements: []
pre_conditions: []
tags: []
---
`;

const body = `
# ${id} — ${args.title}

## Önkoşul
*(Doldurulacak)*

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | *(adımı yaz)* | *(beklenen sonuç)* |

## Notlar
*(opsiyonel)*
`;

const content = frontmatter + body;

async function fileExists(p) {
  try { await stat(p); return true; } catch { return false; }
}

if (await fileExists(filePath)) {
  console.error(`File already exists: ${filePath}`);
  process.exit(1);
}

if (args["dry-run"]) {
  console.log(`Would create: ${filePath}`);
  console.log("---");
  console.log(content);
  process.exit(0);
}

await mkdir(suiteDir, { recursive: true });
await writeFile(filePath, content, "utf8");
console.log(`✓ Created ${filePath}`);
console.log(`  ID: ${id}`);
console.log(`  Suite: ${suite}`);
console.log(`  Owner: ${owner}`);
