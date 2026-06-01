# @cortex/sdk

**Cortex AI Automation — public TypeScript SDK**

A fully-typed client for the Cortex backend API, covering:
- **Test Management** — projects, suites, cases, runs, requirements, defects, imports
- **Automation** — Playwright MCP proxy, NL test generation, health checks
- **Projects** — core project CRUD

---

## Installation

The SDK lives in `packages/sdk` inside the monorepo.  Reference it from
workspace packages:

```json
{
  "dependencies": {
    "@cortex/sdk": "workspace:*"
  }
}
```

---

## Quick start

```ts
import { CortexSdk } from "@cortex/sdk";

const sdk = new CortexSdk({
  baseUrl: "https://api.cortex.example.com",
  apiKey: process.env.CORTEX_API_KEY,
});

// List test management projects
const projects = await sdk.management.projects.list();

// Get test cases with search
const cases = await sdk.management.cases(projects[0].id).list({ q: "checkout" });

// Fetch traceability matrix
const matrix = await sdk.management.requirements(projects[0].id).traceability();

// Start a Playwright session
const session = await sdk.automation.playwright.createSession({ headless: true });
await sdk.automation.playwright.navigate(session.session_id, {
  url: "https://staging.example.com",
});
const { base64 } = await sdk.automation.playwright.screenshot(session.session_id);
await sdk.automation.playwright.closeSession(session.session_id);
```

---

## Configuration

| Option | Type | Default | Description |
|---|---|---|---|
| `baseUrl` | `string` | — | Backend base URL (required) |
| `apiKey` | `string` | — | Bearer token / API key |
| `defaultHeaders` | `Record<string,string>` | `{}` | Headers added to every request |
| `maxRetries` | `number` | `2` | Max retries on 429/5xx |
| `retryDelayMs` | `number` | `500` | Initial retry delay (doubles each attempt) |
| `fetch` | `typeof fetch` | `globalThis.fetch` | Custom fetch (Node.js polyfill / testing) |

---

## Error handling

```ts
import { CortexApiError } from "@cortex/sdk";

try {
  await sdk.management.cases("bad-id").list();
} catch (err) {
  if (err instanceof CortexApiError) {
    console.error(err.status, err.body);  // 404, { detail: "..." }
  }
}
```

---

## Domain clients

### Management

```ts
sdk.management.projects.list()
sdk.management.projects.get(projectId)
sdk.management.projects.create({ key, name })

sdk.management.cases(projectId).list({ q, includeArchived })
sdk.management.cases(projectId).create(input)
sdk.management.cases(projectId).update(caseId, patch)
sdk.management.cases(projectId).archive(caseId)

sdk.management.runs(projectId).list(statusFilter?)
sdk.management.runs(projectId).get(runId)
sdk.management.runs(projectId).create(input)
sdk.management.runs(projectId).updateStepResult(runCaseId, stepNo, input)

sdk.management.requirements(projectId).list(caseId?)
sdk.management.requirements(projectId).traceability()
sdk.management.requirements(projectId).create(input)

sdk.management.defects(projectId).list()
sdk.management.defects(projectId).create(input)

sdk.management.imports(projectId).list()
sdk.management.imports(projectId).get(jobId)
sdk.management.imports(projectId).create(input)
sdk.management.imports(projectId).commit(jobId)

sdk.management.reports(projectId).executionSummary()
sdk.management.reports(projectId).export()
```

### Automation

```ts
sdk.automation.playwright.createSession(config?)
sdk.automation.playwright.navigate(sessionId, { url })
sdk.automation.playwright.click(sessionId, { selector })
sdk.automation.playwright.fill(sessionId, { selector, value })
sdk.automation.playwright.screenshot(sessionId)
sdk.automation.playwright.closeSession(sessionId)

sdk.automation.nlTest.validate({ nl_description, project_id? })

sdk.automation.health()
```

---

## Development

```bash
# From monorepo root
pnpm --filter @cortex/sdk test
pnpm --filter @cortex/sdk type-check
```
