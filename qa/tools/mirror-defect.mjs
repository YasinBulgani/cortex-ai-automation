#!/usr/bin/env node
/**
 * qa/tools/mirror-defect.mjs
 *
 * Reads a GitHub Issue payload (from gh CLI or GH Action event) and writes
 * qa/defects/GH-{NUMBER}.md mirror.
 *
 * Triggered by .github/workflows/qa-defect-mirror.yml on issue close
 * (when label includes "qa-defect").
 *
 * Usage:
 *   node qa/tools/mirror-defect.mjs --issue-json=event.json
 *   node qa/tools/mirror-defect.mjs --issue=1234 --repo=owner/repo  (uses `gh api`)
 */

import { mkdir, readFile, writeFile, stat } from "node:fs/promises";
import path from "node:path";
import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import { QA_ROOT } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    "issue-json": { type: "string" },
    issue: { type: "string" },
    repo: { type: "string" },
  },
});

let issue;
if (args["issue-json"]) {
  const raw = await readFile(args["issue-json"], "utf8");
  const json = JSON.parse(raw);
  issue = json.issue || json;
} else if (args.issue && args.repo) {
  const raw = execSync(`gh api repos/${args.repo}/issues/${args.issue}`, { encoding: "utf8" });
  issue = JSON.parse(raw);
} else {
  console.error("Usage: mirror-defect --issue-json=event.json | --issue=N --repo=owner/repo");
  process.exit(2);
}

if (issue.state !== "closed") {
  console.log(`Issue #${issue.number} is not closed (state=${issue.state}). Skipping mirror.`);
  process.exit(0);
}

const number = issue.number;
const title = (issue.title || "").replace(/^\[QA\]\s*/i, "").trim();
const url = issue.html_url;
const author = issue.user?.login;
const opened = issue.created_at?.slice(0, 10);
const closed = issue.closed_at?.slice(0, 10);

const body = issue.body || "";
const labels = (issue.labels || []).map((l) => l.name || l);

function pickField(label) {
  const re = new RegExp(`(?:^|\\n)###\\s+${label}\\s*\\n([\\s\\S]*?)(?=\\n###\\s+|$)`, "i");
  const m = re.exec(body);
  return m ? m[1].trim() : "";
}

const tcRaw = pickField("İlgili Test Case") || pickField("Related Test Case");
const tcMatch = /(TC-[A-Z0-9]+-\d+)/.exec(tcRaw);
const tcId = tcMatch ? tcMatch[1] : "";

const foundInRaw = pickField("Bulunduğu Run") || pickField("Found in Run");
const foundIn = /(TR-\d{4}-\d{2}-\d{2}-[A-Z0-9-]+-\d+)/.exec(foundInRaw)?.[1] || "";

const severityRaw = pickField("Severity");
const severity = /S([1-4])/.exec(severityRaw)?.[0] || "S3";

const reproduce = pickField("Tekrar üretme adımları") || pickField("Reproduce");
const expected = pickField("Beklenen davranış") || pickField("Expected");
const actual = pickField("Gerçekleşen davranış") || pickField("Actual");
const environment = pickField("Ortam") || pickField("Environment");
const evidence = pickField("Kanıt") || pickField("Evidence");

const frontmatter = `---
id: GH-${number}
title: "${title.replace(/"/g, '\\"')}"
severity: ${severity}
status: closed
found_in: ${foundIn || "TR-UNKNOWN-000"}
related_tc: [${tcId || "TC-UNKNOWN-000"}]
external: "${url}"
opened: ${opened}
closed: ${closed}
reporter: "@${author || "unknown"}"
---
`;

const mdBody = `
# GH-${number} — ${title}

**External:** ${url}

## Tekrar üretme

${reproduce || "_Bilgi yok._"}

## Beklenen vs Gerçekleşen

**Beklenen:** ${expected || "_Bilgi yok._"}

**Gerçekleşen:** ${actual || "_Bilgi yok._"}

## Ortam

${environment || "_Bilgi yok._"}

## Kanıt

${evidence || "_Yok._"}

## Etiketler

${labels.length ? labels.map((l) => `- ${l}`).join("\n") : "_Yok._"}

---

_Otomatik mirror — \`qa/tools/mirror-defect.mjs\` ile. Kanonik kaynak GitHub Issue [${url}](${url})._
`;

const outPath = path.join(QA_ROOT, "defects", `GH-${number}.md`);
await mkdir(path.dirname(outPath), { recursive: true });

if (await fileExists(outPath)) {
  console.log(`Updating existing mirror: ${outPath}`);
}

await writeFile(outPath, frontmatter + mdBody, "utf8");
console.log(`✓ ${path.relative(process.cwd(), outPath)}`);
console.log(`  Related TC: ${tcId || "(none)"}`);
console.log(`  Severity: ${severity}`);

async function fileExists(p) {
  try { await stat(p); return true; } catch { return false; }
}
