#!/usr/bin/env node
/**
 * qa/tools/import-results.mjs
 *
 * Imports automation runner results and produces a normalized Run YAML.
 *
 * Supported sources:
 *   - Playwright JSON      (--playwright=reports/e2e-results.json)
 *   - Cucumber JSON        (--cucumber=reports/bdd/cucumber-report.json)
 *   - JUnit XML            (--junit=reports/e2e-junit.xml)         [pytest, Playwright junit reporter]
 *   - Allure results dir   (--allure=api-tests/allure-results/)    [pytest-allure, allure-playwright]
 *
 * Output:
 *   qa/runs/YYYY/MM/TR-{YYYY}-{MM}-{DD}-{NAME}-{NNN}.yml
 *
 * Usage:
 *   node qa/tools/import-results.mjs --playwright=reports/e2e-results.json --name=nightly
 *   node qa/tools/import-results.mjs --cucumber=reports/bdd/cucumber-report.json --name=bdd
 *   node qa/tools/import-results.mjs --junit=reports/e2e-junit.xml --name=api-smoke
 *   node qa/tools/import-results.mjs --allure=api-tests/allure-results/ --name=api
 *   node qa/tools/import-results.mjs --playwright=... --cucumber=... --allure=... --name=full-suite
 */

import { mkdir, readFile, writeFile, stat } from "node:fs/promises";
import path from "node:path";
import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import yaml from "js-yaml";
import { QA_ROOT, REPO_ROOT } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    playwright: { type: "string" },
    cucumber: { type: "string" },
    junit: { type: "string" },
    allure: { type: "string" },
    name: { type: "string", default: "automated" },
    plan: { type: "string", default: "auto-imported" },
    env: { type: "string", default: "staging" },
    browser: { type: "string", default: "chromium" },
    url: { type: "string" },
    "dry-run": { type: "boolean", default: false },
  },
});

if (!args.playwright && !args.cucumber && !args.junit && !args.allure) {
  console.error("Provide at least one source: --playwright, --cucumber, --junit, or --allure");
  process.exit(2);
}

const startedAt = new Date();
const results = [];
let sourceTimings = { earliest: null, latest: null };

if (args.playwright) {
  const r = await importPlaywright(path.resolve(REPO_ROOT, args.playwright));
  results.push(...r.results);
  mergeTimings(sourceTimings, r.timings);
}
if (args.cucumber) {
  const r = await importCucumber(path.resolve(REPO_ROOT, args.cucumber));
  results.push(...r.results);
  mergeTimings(sourceTimings, r.timings);
}
if (args.junit) {
  const r = await importJunit(path.resolve(REPO_ROOT, args.junit));
  results.push(...r.results);
  mergeTimings(sourceTimings, r.timings);
}
if (args.allure) {
  const r = await importAllure(path.resolve(REPO_ROOT, args.allure));
  results.push(...r.results);
  mergeTimings(sourceTimings, r.timings);
}

if (results.length === 0) {
  console.error("No test results parsed from any source.");
  process.exit(1);
}

const taggedResults = [];
const untrackedTests = [];
for (const r of results) {
  if (r.tc) taggedResults.push(r);
  else untrackedTests.push(r);
}

const branch = safeGit("git rev-parse --abbrev-ref HEAD");
const commit = safeGit("git rev-parse --short HEAD");

const summary = { total: 0, passed: 0, failed: 0, blocked: 0, skipped: 0, untested: 0 };
for (const r of taggedResults) {
  summary.total++;
  switch (r.status) {
    case "pass": summary.passed++; break;
    case "fail": summary.failed++; break;
    case "blocked": summary.blocked++; break;
    case "skipped": summary.skipped++; break;
    default: summary.untested++;
  }
}

const startedIso = sourceTimings.earliest?.toISOString() || startedAt.toISOString();
const endedIso = sourceTimings.latest?.toISOString() || new Date().toISOString();

const d = new Date(startedIso);
const yyyy = d.getUTCFullYear();
const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
const dd = String(d.getUTCDate()).padStart(2, "0");
const monthDir = path.join(QA_ROOT, "runs", String(yyyy), mm);
await mkdir(monthDir, { recursive: true });

const existingForToday = await listExistingRunsForToday(monthDir, yyyy, mm, dd, args.name);
const seq = String(existingForToday.length + 1).padStart(3, "0");
const nameUpper = args.name.toUpperCase().replace(/[^A-Z0-9-]/g, "-");
const runId = `TR-${yyyy}-${mm}-${dd}-${nameUpper}-${seq}`;
const outPath = path.join(monthDir, `${runId}.yml`);

const executor = safeGit("git config user.name").toLowerCase().replace(/\s+/g, "-") || "ci-bot";

const yamlDoc = {
  id: runId,
  plan: args.plan,
  started: startedIso,
  ended: endedIso,
  executor: `@${executor}`,
  environment: {
    branch,
    commit,
    browser: args.browser,
    env: args.env,
  },
  summary,
  results: taggedResults.map((r) => ({
    tc: r.tc,
    tc_commit: commit,
    status: r.status,
    ...(r.duration_s !== undefined && { duration_s: r.duration_s }),
    ...(r.ref && { automation: r.ref }),
    ...(r.note && { note: r.note }),
  })),
};
if (args.url) yamlDoc.environment.url = args.url;

const yamlOut = yaml.dump(yamlDoc, { noRefs: true, lineWidth: 120 });

console.log(`Sources parsed: ${[
  args.playwright && "playwright",
  args.cucumber && "cucumber",
  args.junit && "junit",
  args.allure && "allure",
].filter(Boolean).join(", ")}`);
console.log(`Total results: ${results.length}`);
console.log(`  Tagged (have @TC-*): ${taggedResults.length}`);
console.log(`  Untracked (no @TC-* tag): ${untrackedTests.length}`);
console.log(`Summary: passed=${summary.passed}, failed=${summary.failed}, blocked=${summary.blocked}, skipped=${summary.skipped}`);
console.log(`\nRun ID: ${runId}`);
console.log(`Output: ${path.relative(REPO_ROOT, outPath)}`);

if (args["dry-run"]) {
  console.log("\n--- DRY RUN: would write below ---\n");
  console.log(yamlOut);
  if (untrackedTests.length) {
    console.log(`\n--- Untracked tests (${untrackedTests.length}) ---`);
    for (const t of untrackedTests.slice(0, 10)) {
      console.log(`  ${t.status.padEnd(7)} ${t.title}`);
    }
    if (untrackedTests.length > 10) console.log(`  ... +${untrackedTests.length - 10} more`);
  }
  process.exit(0);
}

await writeFile(outPath, yamlOut, "utf8");
console.log(`\n✓ Wrote ${path.relative(REPO_ROOT, outPath)}`);

if (untrackedTests.length) {
  console.log(`\n⚠ ${untrackedTests.length} test(s) had no @TC-* tag — they are NOT in the run YAML.`);
  console.log("  Run 'node tools/trace.mjs' to refresh orphans.md.");
}

// ─────────────────────────────────────────────────────────────────────────

function safeGit(cmd) {
  try {
    return execSync(cmd, { cwd: REPO_ROOT, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

function mergeTimings(target, src) {
  if (!src) return;
  if (src.earliest && (!target.earliest || src.earliest < target.earliest)) target.earliest = src.earliest;
  if (src.latest && (!target.latest || src.latest > target.latest)) target.latest = src.latest;
}

function extractTcTag(tags) {
  if (!tags) return null;
  const arr = Array.isArray(tags) ? tags : [tags];
  for (const t of arr) {
    const name = typeof t === "string" ? t : t.name;
    const m = /(?:^|@)(TC-[A-Z0-9]+-\d+)/.exec(name || "");
    if (m) return m[1];
  }
  return null;
}

function extractTcFromTitle(title) {
  if (!title) return null;
  const m = /(TC-[A-Z0-9]+-\d+)/.exec(title);
  return m ? m[1] : null;
}

async function listExistingRunsForToday(monthDir, yyyy, mm, dd, name) {
  try {
    const fs = await import("node:fs/promises");
    const all = await fs.readdir(monthDir);
    return all.filter((f) => f.startsWith(`TR-${yyyy}-${mm}-${dd}-${name.toUpperCase().replace(/[^A-Z0-9-]/g, "-")}-`));
  } catch {
    return [];
  }
}

// ── Playwright JSON ──────────────────────────────────────────────────────

async function importPlaywright(filePath) {
  const raw = JSON.parse(await readFile(filePath, "utf8"));
  const results = [];
  const timings = { earliest: null, latest: null };

  function walk(node, file = null) {
    const nodeFile = node.file || file;
    if (Array.isArray(node.tests)) {
      for (const t of node.tests) {
        const result = t.results?.[0] || {};
        const status = mapPlaywrightStatus(t.outcome, result.status);
        const tc = extractTcTag(t.tags) || extractTcFromTitle(t.title);
        const startTime = result.startTime ? new Date(result.startTime) : null;
        if (startTime) {
          if (!timings.earliest || startTime < timings.earliest) timings.earliest = startTime;
          const endTime = new Date(startTime.getTime() + (result.duration || 0));
          if (!timings.latest || endTime > timings.latest) timings.latest = endTime;
        }
        results.push({
          tc,
          title: t.title,
          status,
          duration_s: result.duration != null ? Math.round(result.duration) / 1000 : undefined,
          ref: nodeFile ? `${nodeFile}` : undefined,
          note: result.error?.message?.split("\n")[0],
        });
      }
    }
    if (Array.isArray(node.suites)) for (const s of node.suites) walk(s, nodeFile);
  }
  if (Array.isArray(raw.suites)) for (const s of raw.suites) walk(s);

  return { results, timings };
}

function mapPlaywrightStatus(outcome, resultStatus) {
  if (outcome === "skipped" || resultStatus === "skipped") return "skipped";
  if (outcome === "expected" || resultStatus === "passed") return "pass";
  if (outcome === "flaky") return "pass";
  if (outcome === "unexpected" || resultStatus === "failed" || resultStatus === "timedOut") return "fail";
  return "untested";
}

// ── Cucumber JSON ────────────────────────────────────────────────────────

async function importCucumber(filePath) {
  const raw = JSON.parse(await readFile(filePath, "utf8"));
  const features = Array.isArray(raw) ? raw : raw.features || [];
  const results = [];
  const timings = { earliest: null, latest: null };

  for (const feature of features) {
    for (const el of feature.elements || []) {
      if (el.type !== "scenario" && el.type !== "scenarioOutline") continue;
      const tc = extractTcTag(el.tags) || extractTcFromTitle(el.name);
      const stepResults = (el.steps || []).map((s) => s.result || {});
      const failedStep = stepResults.find((r) => r.status === "failed");
      const allPassed = stepResults.every((r) => r.status === "passed");
      const skipped = stepResults.some((r) => r.status === "skipped" || r.status === "undefined");
      let status = "untested";
      if (failedStep) status = "fail";
      else if (allPassed) status = "pass";
      else if (skipped) status = "skipped";

      const totalDurationNs = stepResults.reduce((acc, r) => acc + (r.duration || 0), 0);
      results.push({
        tc,
        title: el.name,
        status,
        duration_s: totalDurationNs > 0 ? Math.round(totalDurationNs / 1e6) / 1000 : undefined,
        ref: feature.uri,
        note: failedStep?.error_message?.split("\n")[0],
      });
    }
  }

  return { results, timings };
}

// ── JUnit XML ────────────────────────────────────────────────────────────

async function importJunit(filePath) {
  const raw = await readFile(filePath, "utf8");
  const results = [];
  const timings = { earliest: null, latest: null };

  const tcRegex = /<testcase\b([^>]*?)(\/>|>([\s\S]*?)<\/testcase>)/g;
  let m;
  while ((m = tcRegex.exec(raw)) !== null) {
    const attrs = parseAttrs(m[1]);
    const inner = m[3] || "";
    const title = attrs.name;
    const classname = attrs.classname || "";
    const tc = extractTcFromTitle(title) || extractTcFromTitle(classname);

    let status = "pass";
    let note;
    if (/<failure\b/.test(inner)) {
      status = "fail";
      const fm = /<failure\b[^>]*message="([^"]*)"/.exec(inner);
      if (fm) note = fm[1];
    } else if (/<error\b/.test(inner)) {
      status = "fail";
      const em = /<error\b[^>]*message="([^"]*)"/.exec(inner);
      if (em) note = em[1];
    } else if (/<skipped\b/.test(inner)) {
      status = "skipped";
    }

    const duration_s = attrs.time ? parseFloat(attrs.time) : undefined;
    results.push({ tc, title, status, duration_s, ref: classname || undefined, note });
  }

  return { results, timings };
}

function parseAttrs(attrString) {
  const out = {};
  const re = /(\w+)="([^"]*)"/g;
  let m;
  while ((m = re.exec(attrString)) !== null) out[m[1]] = m[2];
  return out;
}

// ── Allure results directory ─────────────────────────────────────────────

async function importAllure(dirPath) {
  const fs = await import("node:fs/promises");
  const results = [];
  const timings = { earliest: null, latest: null };

  let files;
  try {
    files = await fs.readdir(dirPath);
  } catch (err) {
    console.error(`Allure dir not readable: ${dirPath} (${err.message})`);
    return { results, timings };
  }

  const resultFiles = files.filter((f) => f.endsWith("-result.json"));
  if (resultFiles.length === 0) {
    console.warn(`No *-result.json found in ${dirPath}`);
    return { results, timings };
  }

  for (const file of resultFiles) {
    let json;
    try {
      json = JSON.parse(await fs.readFile(path.join(dirPath, file), "utf8"));
    } catch {
      continue;
    }

    const labels = json.labels || [];
    let tc = null;
    for (const lbl of labels) {
      const m = /(TC-[A-Z0-9]+-\d+)/.exec(lbl.value || "");
      if (m) { tc = m[1]; break; }
    }
    if (!tc) tc = extractTcFromTitle(json.name) || extractTcFromTitle(json.fullName);

    const status = mapAllureStatus(json.status);
    const start = json.start ? new Date(json.start) : null;
    const stop = json.stop ? new Date(json.stop) : null;
    if (start) {
      if (!timings.earliest || start < timings.earliest) timings.earliest = start;
    }
    if (stop) {
      if (!timings.latest || stop > timings.latest) timings.latest = stop;
    }
    const duration_s =
      start && stop ? Math.round((stop - start) / 10) / 100 : undefined;

    const featurelbl = labels.find((l) => l.name === "feature" || l.name === "story" || l.name === "epic");
    const ref = json.fullName || featurelbl?.value;

    results.push({
      tc,
      title: json.name,
      status,
      duration_s,
      ref,
      note: json.statusDetails?.message?.split("\n")[0],
    });
  }

  return { results, timings };
}

function mapAllureStatus(s) {
  switch (s) {
    case "passed": return "pass";
    case "failed": return "fail";
    case "broken": return "fail";
    case "skipped": return "skipped";
    case "unknown": return "untested";
    default: return "untested";
  }
}
