#!/usr/bin/env node
/**
 * qa/tools/test-impact.mjs
 *
 * Git diff'ten etkilenen otomasyon dosyalarını çıkarır, bu dosyalara
 * `automation.refs` ile bağlı TC'leri raporlar. PR review sırasında
 * "bu PR hangi TC'leri etkiler?" sorusuna heuristic cevap.
 *
 * Usage:
 *   node qa/tools/test-impact.mjs                     # uncommitted (working tree)
 *   node qa/tools/test-impact.mjs --base=main         # main'den beri (PR diff)
 *   node qa/tools/test-impact.mjs --base=main --json  # JSON output (CI için)
 */

import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import { REPO_ROOT, loadAllTestCases } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    base: { type: "string" },
    json: { type: "boolean", default: false },
  },
});

let changedFiles;
try {
  const cmd = args.base
    ? `git diff --name-only ${args.base}...HEAD`
    : `git diff --name-only HEAD && git diff --name-only --cached`;
  changedFiles = execSync(cmd, { cwd: REPO_ROOT, encoding: "utf8", shell: "/bin/bash" })
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  changedFiles = [...new Set(changedFiles)];
} catch (err) {
  console.error(`git diff failed: ${err.message}`);
  process.exit(1);
}

if (changedFiles.length === 0) {
  console.log("No changed files.");
  process.exit(0);
}

const tcs = (await loadAllTestCases()).filter((t) => t.data);

const impactedTcs = new Set();
const impactByFile = new Map();

for (const file of changedFiles) {
  for (const t of tcs) {
    const refs = t.data.automation?.refs || [];
    for (const ref of refs) {
      const refPath = ref.split(":")[0];
      if (file === refPath || file.startsWith(refPath + "/") || refPath.startsWith(file + "/")) {
        impactedTcs.add(t.data.id);
        if (!impactByFile.has(file)) impactByFile.set(file, []);
        impactByFile.get(file).push({ tc: t.data.id, priority: t.data.priority, suite: t.data.suite });
      }
    }
  }
}

// Heuristic: changed file path'inin suite ismi ile eşleştiği TC'leri de "potentially impacted" işaretle
const suiteHints = new Map();
for (const file of changedFiles) {
  for (const t of tcs) {
    if (impactedTcs.has(t.data.id)) continue;
    const suite = t.data.suite;
    if (file.includes(`/${suite}/`) || file.includes(`/${suite}.`) || file.endsWith(`/${suite}`)) {
      if (!suiteHints.has(file)) suiteHints.set(file, []);
      suiteHints.get(file).push({ tc: t.data.id, priority: t.data.priority, suite });
    }
  }
}

if (args.json) {
  console.log(JSON.stringify({
    changedFiles,
    direct: Array.from(impactByFile.entries()).map(([file, tcs]) => ({ file, tcs })),
    suite_hints: Array.from(suiteHints.entries()).map(([file, tcs]) => ({ file, tcs })),
    total_impacted: impactedTcs.size,
  }, null, 2));
  process.exit(impactedTcs.size > 0 ? 0 : 0);
}

console.log(`Changed files: ${changedFiles.length}`);
console.log(`Directly impacted TCs (automation.refs match): ${impactedTcs.size}\n`);

if (impactByFile.size > 0) {
  console.log("## Direct impact\n");
  for (const [file, tcs] of impactByFile) {
    console.log(`📁 ${file}`);
    for (const t of tcs) {
      console.log(`   • [${t.priority}] ${t.tc} (suite: ${t.suite})`);
    }
  }
}

if (suiteHints.size > 0) {
  console.log("\n## Suite hints (potential impact, manual review)\n");
  const allHints = new Set();
  for (const tcs of suiteHints.values()) {
    for (const t of tcs) allHints.add(`[${t.priority}] ${t.tc}`);
  }
  for (const h of [...allHints].sort()) console.log(`   • ${h}`);
}

if (impactedTcs.size === 0 && suiteHints.size === 0) {
  console.log("No TC impact detected.");
  console.log("Consider: changed files may not have automation.refs back-link.");
}
