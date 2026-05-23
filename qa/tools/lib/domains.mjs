export const DOMAIN_PREFIXES = Object.freeze([
  "AUTH",
  "PRJ",
  "SCN",
  "EXC",
  "APR",
  "RBAC",
  "FLW",
  "INT",
  "API",
  "RPT",
  "ADM",
  "BIL",
  "NTF",
  "SCH",
  "IMP",
  "REG",
  "REQ",
  "MEM",
  "DASH",
  "BDD",
  "AI",
  "MOB",
  "A11Y",
  "PERF",
  "SEC",
  "SYN",
  "ENG",
  "VIS",
  "REC",
  "DSM",
  "INF",
  "QA",
  "RUN",
]);

export const SUITE_TO_DOMAIN = Object.freeze({
  auth: "AUTH",
  projects: "PRJ",
  scenarios: "SCN",
  executions: "EXC",
  approvals: "APR",
  rbac: "RBAC",
  flows: "FLW",
  integrations: "INT",
  "api-tests": "API",
  reports: "RPT",
  admin: "ADM",
  billing: "BIL",
  notifications: "NTF",
  schedules: "SCH",
  imports: "IMP",
  regression: "REG",
  requirements: "REQ",
  members: "MEM",
  dashboard: "DASH",
  bdd: "BDD",
  ai: "AI",
  mobile: "MOB",
  a11y: "A11Y",
  performance: "PERF",
  security: "SEC",
  "synthetic-data": "SYN",
  engine: "ENG",
  "visual-regression": "VIS",
  recorder: "REC",
  datasim: "DSM",
  infrastructure: "INF",
  "qa-engine": "QA",
  runs: "RUN",
});

export const DOMAIN_TO_SUITE = Object.freeze(
  Object.fromEntries(Object.entries(SUITE_TO_DOMAIN).map(([s, d]) => [d, s])),
);

export function isValidDomain(prefix) {
  return DOMAIN_PREFIXES.includes(prefix);
}

export function domainForSuite(suiteName) {
  return SUITE_TO_DOMAIN[suiteName] ?? null;
}

export function suiteForDomain(domainPrefix) {
  return DOMAIN_TO_SUITE[domainPrefix] ?? null;
}
