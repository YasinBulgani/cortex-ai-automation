#!/usr/bin/env node
/**
 * qa/tools/validate.mjs
 *
 * Validates all qa/ artifacts against schemas + cross-reference integrity.
 *
 * Exit codes:
 *   0 = no failures (warnings allowed)
 *   1 = at least one failure
 *
 * Usage:
 *   node qa/tools/validate.mjs                  # full validation
 *   node qa/tools/validate.mjs --quiet          # only fail/warn output
 *   node qa/tools/validate.mjs --strict         # warnings cause exit 1 too
 */

import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import fg from "fast-glob";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";

import {
  QA_ROOT,
  REPO_ROOT,
  loadAllTestCases,
  loadAllSuites,
  loadAllPreConditions,
  loadAllRequirements,
  loadAllPlans,
  loadAllRuns,
  relativeToQa,
} from "./lib/files.mjs";
import { detectKind, validateId } from "./lib/ids.mjs";
import { DOMAIN_PREFIXES } from "./lib/domains.mjs";
import { fail, warn, info, ok, section, summary, getCounters, resetCounters } from "./lib/logger.mjs";

const { values: args } = parseArgs({
  options: {
    quiet: { type: "boolean", default: false },
    strict: { type: "boolean", default: false },
    json: { type: "boolean", default: false },
  },
});

resetCounters();

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

async function loadSchema(name) {
  const file = path.join(QA_ROOT, "tools/schemas", `${name}.schema.json`);
  const raw = await readFile(file, "utf8");
  return JSON.parse(raw);
}

const schemas = {
  tc: await loadSchema("test-case"),
  suite: await loadSchema("suite"),
  plan: await loadSchema("plan"),
  run: await loadSchema("run"),
  defect: await loadSchema("defect"),
  requirement: await loadSchema("requirement"),
  pre: await loadSchema("pre-condition"),
  milestone: await loadSchema("milestone"),
};

const validators = Object.fromEntries(Object.entries(schemas).map(([k, s]) => [k, ajv.compile(s)]));

function fmtAjvErrors(errors) {
  return errors.map((e) => `${e.instancePath || "(root)"} ${e.message}`).join("; ");
}

async function fileExists(p) {
  try {
    await stat(p);
    return true;
  } catch {
    return false;
  }
}

const allTestCases = await loadAllTestCases();
const allSuites = await loadAllSuites();
const allPreConditions = await loadAllPreConditions();
const allRequirements = await loadAllRequirements();
const allPlans = await loadAllPlans();
const allRuns = await loadAllRuns();

const tcIds = new Set();
const preIds = new Set();
const reqIds = new Set();
const planIds = new Set();
const runIds = new Set();
const suiteFolders = new Set();

for (const s of allSuites) {
  if (s.data?.id) {
    const folder = path.basename(path.dirname(s.file));
    suiteFolders.add(folder);
  }
}

section("Test cases");
for (const { file, data, error } of allTestCases) {
  const rel = relativeToQa(file);
  if (error) {
    fail(`Parse error: ${error}`, rel);
    continue;
  }
  if (!data) {
    fail("Empty frontmatter", rel);
    continue;
  }
  const valid = validators.tc(data);
  if (!valid) {
    fail(fmtAjvErrors(validators.tc.errors), rel);
    continue;
  }
  const idCheck = validateId(data.id);
  if (!idCheck.ok) {
    fail(`Invalid TC id: ${data.id} (${idCheck.reason})`, rel);
    continue;
  }
  if (tcIds.has(data.id)) {
    fail(`Duplicate TC id: ${data.id}`, rel);
    continue;
  }
  tcIds.add(data.id);

  const expectedFolder = path.basename(path.dirname(file));
  if (data.suite !== expectedFolder) {
    fail(`suite '${data.suite}' does not match folder '${expectedFolder}'`, rel);
  }

  const domain = data.id.split("-")[1];
  if (!DOMAIN_PREFIXES.includes(domain)) {
    fail(`Unknown domain prefix: ${domain}`, rel);
  }

  if (data.automation?.status === "automated") {
    for (const ref of data.automation.refs || []) {
      const [refPath] = ref.split(":");
      const abs = path.join(REPO_ROOT, refPath);
      if (!(await fileExists(abs))) {
        fail(`Broken automation ref: ${ref}`, rel);
      }
    }
  }
}

if (allTestCases.length > 0 && getCounters().fail === 0 && !args.quiet) {
  ok(`${allTestCases.length} test case validated`);
}

section("Suites");
for (const { file, data, error } of allSuites) {
  const rel = relativeToQa(file);
  if (error) {
    fail(`Parse error: ${error}`, rel);
    continue;
  }
  if (!data) continue;
  const valid = validators.suite(data);
  if (!valid) {
    fail(fmtAjvErrors(validators.suite.errors), rel);
    continue;
  }
  if (!args.quiet) ok(`${data.id}`, rel);
}

section("Pre-conditions");
for (const { file, data, error } of allPreConditions) {
  const rel = relativeToQa(file);
  if (error) {
    fail(`Parse error: ${error}`, rel);
    continue;
  }
  if (!data) continue;
  const valid = validators.pre(data);
  if (!valid) {
    fail(fmtAjvErrors(validators.pre.errors), rel);
    continue;
  }
  if (preIds.has(data.id)) {
    fail(`Duplicate PRE id: ${data.id}`, rel);
    continue;
  }
  preIds.add(data.id);
}

section("Requirements");
for (const { file, data, error } of allRequirements) {
  const rel = relativeToQa(file);
  if (error) {
    fail(`Parse error: ${error}`, rel);
    continue;
  }
  if (!data) continue;
  const valid = validators.requirement(data);
  if (!valid) {
    fail(fmtAjvErrors(validators.requirement.errors), rel);
    continue;
  }
  if (reqIds.has(data.id)) {
    fail(`Duplicate REQ id: ${data.id}`, rel);
    continue;
  }
  reqIds.add(data.id);
}

section("Plans");
for (const { file, data, error } of allPlans) {
  const rel = relativeToQa(file);
  if (error) {
    fail(`Parse error: ${error}`, rel);
    continue;
  }
  if (!data) continue;
  const valid = validators.plan(data);
  if (!valid) {
    fail(fmtAjvErrors(validators.plan.errors), rel);
    continue;
  }
  if (planIds.has(data.id)) {
    fail(`Duplicate Plan id: ${data.id}`, rel);
    continue;
  }
  planIds.add(data.id);

  for (const inc of data.scope?.include || []) {
    if (inc.suite && !suiteFolders.has(inc.suite)) {
      warn(`Plan references unknown suite: ${inc.suite}`, rel);
    }
    for (const tcRef of inc.cases || []) {
      if (!tcIds.has(tcRef)) {
        fail(`Plan references unknown TC: ${tcRef}`, rel);
      }
    }
  }
}

section("Runs");
for (const { file, data, error } of allRuns) {
  const rel = relativeToQa(file);
  if (error) {
    fail(`Parse error: ${error}`, rel);
    continue;
  }
  if (!data) continue;
  const valid = validators.run(data);
  if (!valid) {
    fail(fmtAjvErrors(validators.run.errors), rel);
    continue;
  }
  if (runIds.has(data.id)) {
    fail(`Duplicate Run id: ${data.id}`, rel);
    continue;
  }
  runIds.add(data.id);

  for (const r of data.results || []) {
    if (!tcIds.has(r.tc)) {
      warn(`Run references unknown TC: ${r.tc}`, rel);
    }
  }
}

section("Cross references");
for (const { file, data } of allTestCases) {
  if (!data) continue;
  const rel = relativeToQa(file);
  for (const req of data.requirements || []) {
    if (!reqIds.has(req)) {
      warn(`TC references unknown requirement: ${req}`, `${rel} (${data.id})`);
    }
  }
  for (const pre of data.pre_conditions || []) {
    if (!preIds.has(pre)) {
      warn(`TC references unknown pre-condition: ${pre}`, `${rel} (${data.id})`);
    }
  }
}

section("Orphan check");
const referencedByPlan = new Set();
for (const { data } of allPlans) {
  if (!data) continue;
  for (const inc of data.scope?.include || []) {
    for (const tc of inc.cases || []) referencedByPlan.add(tc);
  }
}
const referencedByRun = new Set();
for (const { data } of allRuns) {
  if (!data) continue;
  for (const r of data.results || []) referencedByRun.add(r.tc);
}
let orphans = 0;
for (const tcId of tcIds) {
  if (!referencedByPlan.has(tcId) && !referencedByRun.has(tcId)) {
    orphans++;
    if (!args.quiet) info(`Orphan TC (no plan, no run): ${tcId}`);
  }
}
if (orphans > 0 && !args.quiet) info(`${orphans} orphan TC total`);

summary();

const counters = getCounters();
const failOnWarn = args.strict && counters.warn > 0;

if (args.json) {
  console.log(JSON.stringify({ ok: counters.fail === 0 && !failOnWarn, counters }, null, 2));
}

process.exit(counters.fail > 0 || failOnWarn ? 1 : 0);
