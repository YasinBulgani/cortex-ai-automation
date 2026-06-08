# ADR-0014: Mobile Automation Driver Strategy (Playwright + Appium W3C)

## Status

Accepted

## Date

2026-06-09

## Context

Neurex must run mobile test automation across two distinct needs:

1. **Fast, CI-friendly checks** on emulated devices for web/responsive flows.
2. **Real native app automation** on physical/emulated iOS & Android devices.

A recurring question is whether the platform needs a "native Appium driver"
to be built and whether Selenium should also be supported (Selenium is covered
separately in [ADR-0015](ADR-0015-selenium-support-decision.md)).

This ADR records the **actual** driver architecture and the one genuinely
hardware-gated gap, because prior gap reports incorrectly listed native Appium
as "not implemented".

### Current implementation (verified 2026-06-09)

| Layer | File | State |
|-------|------|-------|
| W3C WebDriver/Appium HTTP client | `backend/app/domains/mobile/appium_client.py` | **Real** — `create_session`, W3C `alwaysMatch` capabilities, `find_element`, element ops, `quit`, `status` over httpx |
| Step runner | `backend/app/domains/mobile/appium_runner.py` | **Real** — executes `openUrl`/`find`/`tap`/`sendKeys`/… with per-step validation, emits SSE events |
| Device registry | `backend/app/domains/mobile/device_broker.py` | **Real** for listing/status/reboot/`probe_appium`; **stub** only for the physical-device ADB/WDA enrollment handshake |
| Orchestrator | `backend/app/domains/mobile/orchestrator.py` | Runs `mode="simulation"` (default, deterministic) and `mode="appium"` (real WebDriver); sessions persisted to SQL per [ADR-runs] / `mobile_sessions` |
| Emulation (web) | engine Playwright | Mobile viewport emulation + BrowserStack/Sauce CDP |

So three of four layers are real. Native Appium automation works against any
reachable Appium server (`appium_url`).

## Decision

**Keep the two-track driver strategy and do not build a new mobile driver.**

- **Playwright** remains the driver for web/responsive flows and emulated
  devices (and cloud farms via CDP). It is already the desktop driver.
- **Appium (W3C)** remains the driver for native iOS/Android automation,
  using the existing `AppiumClient`/`AppiumRunner`. No rewrite is warranted.

The only remaining work is **hardware-gated** and intentionally deferred until
real devices are available in the environment:

1. **Physical device enrollment handshake** (`device_broker.enroll_physical`,
   currently a stub): perform the real ADB (`adb devices`/`adb connect`) and
   iOS WebDriverAgent handshake to validate a physically attached device before
   marking it `idle`. Requires a real Android device/emulator with ADB and, for
   iOS, a macOS host with Xcode + WDA.
2. **`probe_appium` deepening**: beyond the current reachability probe, query
   the live Appium `/status` and device capabilities on enrollment.
3. **Wi-Fi ADB & iOS wireless**: marked "Planlı" in the UI — depends on (1).

### Why hardware-gated work is NOT implemented blindly here

Driver code that talks to real devices cannot be verified in this environment
(no attached devices, no Appium server, no macOS+Xcode). Writing it unverified
would create untested automation code — the opposite of the platform's purpose.
This ADR therefore scopes it as a hardware-prerequisite task, not a code gap.

## Consequences

**Positive**
- No new driver layer to maintain; the W3C Appium client already covers native.
- Clear, honest scope: only the physical-enrollment handshake is outstanding,
  and its blocker (hardware) is explicit.
- `mode="appium"` is usable today against any reachable Appium server.

**Negative / trade-offs**
- Physical-device onboarding remains a stub until hardware is provisioned.
- iOS native automation requires a macOS+Xcode+WDA host (inherent to Appium/iOS).

**Verification prerequisites (when hardware is available)**
- Android: a device/emulator with USB debugging + `adb` on PATH.
- iOS: macOS host, Xcode, a provisioned WebDriverAgent build.
- A running Appium 2.x server reachable at the device's `appium_url`.
- Then: end-to-end test of `enroll_physical` → `probe_appium` → `mode="appium"`
  session against the real device.

## Related

- [ADR-0015](ADR-0015-selenium-support-decision.md) — Selenium support decision
- `mobile_sessions` SQL persistence (run history durable across restarts)
