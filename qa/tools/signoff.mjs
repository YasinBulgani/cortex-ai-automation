#!/usr/bin/env node
/**
 * qa/tools/signoff.mjs
 *
 * Generates a release sign-off report from a plan + its runs.
 *
 * Evaluates exit_criteria heuristically (P0 pass rate, P1 fail rate, open S1 defects)
 * and produces a markdown report.
 *
 * Usage:
 *   node qa/tools/signoff.mjs --plan=TP-2026.Q2-SMOKE-DAILY
 *   node qa/tools/signoff.mjs --plan=smoke-daily --out=reporting/release-2026.Q2-signoff.md
 */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";
import {
  QA_ROOT,
  loadAllTestCases,
  loadAllRuns,
  loadAllPlans,
} from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    plan: { type: "string" },
    out: { type: "string" },
  },
});

if (!args.plan) {
  console.error("Usage: signoff --plan=<plan-id-or-filename> [--out=<path>]");
  process.exit(2);
}

const plans = (await loadAllPlans()).filter((p) => p.data);
const plan = plans.find(
  (p) => p.data.id === args.plan || path.basename(p.file, ".yml") === args.plan,
);
if (!plan) {
  console.error(`Plan not found: ${args.plan}`);
  process.exit(1);
}

const tcs = (await loadAllTestCases()).filter((t) => t.data);
const tcById = new Map(tcs.map((t) => [t.data.id, t]));

const runs = (await loadAllRuns()).filter((r) => r.data && r.data.plan === plan.data.id);

const scoped = resolveScope(plan.data, tcs);

const lastResultByTc = new Map();
for (const r of runs.slice().sort((a, b) => (a.data.started || "").localeCompare(b.data.started || ""))) {
  for (const res of r.data.results || []) {
    if (scoped.find((t) => t.data.id === res.tc)) {
      lastResultByTc.set(res.tc, { runId: r.data.id, status: res.status, started: r.data.started, defect: res.defect });
    }
  }
}

const statusCount = { pass: 0, fail: 0, blocked: 0, skipped: 0, untested: 0, never: 0 };
const failedTcs = [];
const blockedTcs = [];
const neverRunTcs = [];
for (const t of scoped) {
  const last = lastResultByTc.get(t.data.id);
  if (!last) {
    statusCount.never++;
    neverRunTcs.push({ id: t.data.id, priority: t.data.priority, title: t.data.title });
  } else {
    statusCount[last.status] = (statusCount[last.status] || 0) + 1;
    if (last.status === "fail") failedTcs.push({ ...t.data, last });
    if (last.status === "blocked") blockedTcs.push({ ...t.data, last });
  }
}

const p0InScope = scoped.filter((t) => t.data.priority === "P0").length;
const p0Passed = scoped
  .filter((t) => t.data.priority === "P0")
  .filter((t) => lastResultByTc.get(t.data.id)?.status === "pass").length;
const p1InScope = scoped.filter((t) => t.data.priority === "P1").length;
const p1Failed = scoped
  .filter((t) => t.data.priority === "P1")
  .filter((t) => lastResultByTc.get(t.data.id)?.status === "fail").length;
const p1FailRate = p1InScope > 0 ? (p1Failed / p1InScope) * 100 : 0;

const openDefects = new Set();
for (const t of scoped) {
  for (const d of t.data.open_defects || []) openDefects.add(d);
}

const criteriaResults = (plan.data.exit_criteria || []).map((criterion) => {
  const lower = criterion.toLowerCase();
  let passed = null;
  let detail = "";
  if (lower.includes("p0") && (lower.includes("pass") || lower.includes("geç"))) {
    passed = p0Passed === p0InScope && p0InScope > 0;
    detail = `${p0Passed}/${p0InScope} P0 pass`;
  } else if (lower.includes("p1") && lower.includes("%")) {
    const m = /(\d+)\s*%/.exec(criterion);
    const threshold = m ? parseInt(m[1], 10) : 5;
    passed = p1FailRate <= threshold;
    detail = `P1 fail rate ${p1FailRate.toFixed(1)}% (limit %${threshold})`;
  } else if (lower.includes("s1") && (lower.includes("0") || lower.includes("yok"))) {
    passed = openDefects.size === 0;
    detail = `${openDefects.size} açık defect`;
  } else {
    detail = "manuel doğrulama gerekir";
  }
  return { criterion, passed, detail };
});

const allCriteriaPassed = criteriaResults.every((c) => c.passed === true);
const decision = allCriteriaPassed && statusCount.fail === 0 ? "GO" : "NO-GO";

const today = new Date().toISOString().slice(0, 10);
const md = `# Release Sign-off — ${plan.data.milestone}

**Plan:** ${plan.data.id} — ${plan.data.title}
**Tarih:** ${today}
**Karar:** ${decision === "GO" ? "🟢 **GO**" : "🔴 **NO-GO**"}

---

## Test kapsamı

| | Sayı |
|---|---:|
| Plan kapsamındaki TC | ${scoped.length} |
| Pass | ${statusCount.pass} |
| Fail | ${statusCount.fail} |
| Blocked | ${statusCount.blocked} |
| Skipped | ${statusCount.skipped} |
| **Hiç koşturulmadı** | ${statusCount.never} |
| Toplam koşum | ${runs.length} |

## Exit criteria

| Kriter | Durum | Detay |
|---|---|---|
${criteriaResults
  .map(
    (c) =>
      `| ${c.criterion} | ${c.passed === true ? "🟢 PASS" : c.passed === false ? "🔴 FAIL" : "🟡 MANUEL"} | ${c.detail} |`,
  )
  .join("\n")}

## Açık defect'ler

${openDefects.size === 0 ? "_Yok._" : Array.from(openDefects).map((d) => `- ${d}`).join("\n")}

## Failed TC'ler

${
  failedTcs.length === 0
    ? "_Yok._"
    : failedTcs
        .map(
          (t) =>
            `- **${t.id}** (${t.priority}) — ${t.title}\n  Last run: ${t.last.runId}${t.last.defect ? `, defect: ${t.last.defect}` : ""}`,
        )
        .join("\n")
}

## Blocked TC'ler

${
  blockedTcs.length === 0
    ? "_Yok._"
    : blockedTcs.map((t) => `- **${t.id}** (${t.priority}) — ${t.title}`).join("\n")
}

## Hiç koşturulmamış TC'ler (${neverRunTcs.length})

${
  neverRunTcs.length === 0
    ? "_Yok._"
    : neverRunTcs
        .sort((a, b) => a.priority.localeCompare(b.priority))
        .slice(0, 20)
        .map((t) => `- ${t.id} (${t.priority}) — ${t.title}`)
        .join("\n") + (neverRunTcs.length > 20 ? `\n- ... +${neverRunTcs.length - 20} more` : "")
}

## Önemli koşumlar (en son 5)

${runs.length === 0 ? "_Yok._" : runs
  .slice()
  .sort((a, b) => (b.data.started || "").localeCompare(a.data.started || ""))
  .slice(0, 5)
  .map(
    (r) => {
      const s = r.data.summary || {};
      return `- **${r.data.id}** (${r.data.started?.slice(0, 16) || "?"}) — pass: ${s.passed}, fail: ${s.failed}, blocked: ${s.blocked}, skipped: ${s.skipped}`;
    },
  )
  .join("\n")}

## Onaylar

- [ ] QA Lead
- [ ] Tech Lead
- [ ] PM

---

_Otomatik üretildi — \`qa/tools/signoff.mjs\` ile. Karar heuristic exit_criteria evaluation'ına dayanır; insan onayı zorunludur._
`;

const outPath = args.out
  ? path.resolve(QA_ROOT, "..", args.out)
  : path.join(QA_ROOT, "reporting", `release-${plan.data.milestone}-signoff.md`);

await mkdir(path.dirname(outPath), { recursive: true });
await writeFile(outPath, md, "utf8");

console.log(`Decision: ${decision}`);
console.log(`Scope: ${scoped.length} TC, ${runs.length} runs`);
console.log(`Exit criteria: ${criteriaResults.filter((c) => c.passed === true).length}/${criteriaResults.length} pass`);
console.log(`Output: ${path.relative(process.cwd(), outPath)}`);

function resolveScope(plan, allTcs) {
  const matches = new Set();
  for (const inc of plan.scope?.include || []) {
    for (const t of allTcs) {
      let ok = true;
      if (inc.suite && t.data.suite !== inc.suite) ok = false;
      if (inc.priorities && !inc.priorities.includes(t.data.priority)) ok = false;
      if (inc.tags && !(t.data.tags || []).some((g) => inc.tags.includes(g))) ok = false;
      if (inc.cases && !inc.cases.includes(t.data.id)) ok = false;
      if (ok && (inc.suite || inc.priorities || inc.tags || inc.cases)) matches.add(t.data.id);
    }
  }
  for (const exc of plan.scope?.exclude || []) {
    for (const t of allTcs) {
      if (exc.tags && (t.data.tags || []).some((g) => exc.tags.includes(g))) matches.delete(t.data.id);
      if (exc.cases && exc.cases.includes(t.data.id)) matches.delete(t.data.id);
    }
  }
  return allTcs.filter((t) => matches.has(t.data.id));
}
