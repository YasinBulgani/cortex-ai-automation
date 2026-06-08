# ADR-0015: Selenium WebDriver Support Decision

## Status

Rejected

## Date

2026-06-09

## Context

Neurex's browser automation is built on **Playwright** (engine `core/browser.py`,
recorder, playback, monkey, a11y, visual). A recurring request is whether the
platform should also ship a **Selenium WebDriver** driver, since Selenium is the
most widely known automation tool and some teams have existing Selenium skills.

This ADR records the decision and rationale so the question does not keep
re-surfacing in gap reports.

### What the platform already covers

| Need | Current driver | Status |
|------|----------------|--------|
| Desktop browsers (Chromium/Firefox/WebKit) | Playwright | Implemented |
| Cross-browser cloud | Playwright CDP → BrowserStack / Sauce Labs | Implemented |
| Mobile web (emulation) | Playwright mobile viewports | Implemented |
| Native iOS/Android | Appium W3C ([ADR-0014](ADR-0014-mobile-automation-driver-strategy.md)) | Implemented |
| Recording → code | Playwright recorder → Playwright/pytest/Gherkin/**Selenium** code export | Implemented (codegen target) |

Note: the recorder **already exports Selenium code** as one of its output
formats (for users who run tests in their own Selenium harness). What does NOT
exist is an in-platform Selenium *execution* driver.

## Decision

**Do not add a Selenium execution driver.** Continue with Playwright (web) +
Appium (native) as the only in-platform drivers. Keep Selenium **code export**
in the recorder for interoperability.

### Rationale

1. **No capability gap.** Playwright + Appium already cover every browser and
   platform Selenium would. Adding Selenium yields zero new automation
   capability.
2. **Duplicate maintenance surface.** A Selenium driver would need its own
   session lifecycle, locator resolution, self-healing, waiting strategy,
   screenshot/artifact plumbing, and farm integration — duplicating the mature
   Playwright path (self-healing locator chains, perceptual-hash visual diff,
   WCAG runner) with no payoff.
3. **Inferior primitives.** Playwright's auto-waiting, network interception, and
   tracing are first-class; replicating equivalent reliability on Selenium is
   ongoing cost.
4. **Interop already preserved.** Teams wanting Selenium get generated Selenium
   code from the recorder and run it in their own infra; they are not blocked.

## Consequences

**Positive**
- One automation runtime to maintain and harden, not two.
- Engineering effort stays on Playwright/Appium depth (healing, visual, a11y).

**Negative / trade-offs**
- Teams that want Neurex to *execute* their existing Selenium suites in-platform
  cannot. Mitigation: migrate via the recorder, or run Selenium externally and
  ingest results through the standard run/report APIs.

## Revisiting criteria

Reopen this decision only if a concrete need appears that Playwright + Appium
genuinely cannot serve — e.g. a target browser/runtime Playwright never supports
that a customer contractually requires. Absent that, Selenium stays out.

## Related

- [ADR-0014](ADR-0014-mobile-automation-driver-strategy.md) — Mobile driver strategy
- [ADR-0006](0006-playwright-cucumber-framework-rolü.md) — Playwright/Cucumber framework role
