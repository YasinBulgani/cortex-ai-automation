# Neurex Mobile Implementation Checklist
## React Native MVP (Weeks 1-12)

**Project Lead:** Mobile Tech Lead  
**Team Size:** 4 FTE (1 Tech Lead, 2 Devs, 1 QA/DevOps)  
**Launch Date:** Week 12 (Q3 2026)  
**Status:** Ready for kickoff

---

## Pre-Launch (Week 0)

### Team & Hiring
- [ ] Hire React Native Tech Lead (start immediately)
- [ ] Hire RN Developer 1 (week 0)
- [ ] Hire RN Developer 2 (week 1)
- [ ] Hire QA/DevOps engineer (week 2)
- [ ] Assign Product Manager (mobile-first mindset)
- [ ] Assign Designer (RN Paper component theming)

### Architecture & Planning
- [ ] Review & approve `/docs/MOBILE_PLATFORM_ANALYSIS_2026-06-09.md`
- [ ] Customer validation: 20 phone calls (mobile use-case urgency)
- [ ] Define "Done" criteria for MVP (NPS ≥40, <0.5% crash rate)
- [ ] Create 12-week sprint board (Jira/Linear)
- [ ] Procurement: Buy Apple Developer account ($99/yr), Google Play account ($25)
- [ ] Secrets setup: EAS secrets or 1Password (FCM, OAuth credentials)

---

## Week 1-2: Foundation

### [ ] Project Scaffold
- [ ] Initialize RN project (`npx create-expo-app neurex-mobile`)
- [ ] Install core dependencies:
  ```bash
  npm install react-native-paper zustand react-hook-form zod axios
  npm install @react-navigation/native @react-navigation/bottom-tabs
  npm install expo-secure-store expo-sqlite expo-notifications firebase
  npm install sentry-expo amplitude-react-native
  ```
- [ ] TypeScript setup (tsconfig.json, strict mode)
- [ ] ESLint + Prettier (align with web repo)
- [ ] Git repo (same monorepo or separate GitHub org)
- [ ] Branch protection (main → main, feature branches)

### [ ] Authentication Flow
- [ ] Implement OAuth2 client:
  - Sign-in screen (email, password)
  - MFA screen (OTP code)
  - Token storage (secure enclave/keystore)
  - Token refresh mechanism (auto-refresh on 401)
- [ ] API client setup:
  - Base axios instance (interceptors for auth)
  - Retry logic (exponential backoff)
  - Error handling (401, 403, 500)
- [ ] Deep-linking config (`app.json` URI schemes)
- [ ] Unit tests:
  - [ ] OAuth token refresh (3 test cases)
  - [ ] Secure storage (2 test cases)
  - [ ] Retry logic (3 test cases)

### [ ] CI/CD Pipeline
- [ ] GitHub Actions config (lint, test, build)
- [ ] EAS build setup (iOS + Android configs)
- [ ] Code coverage integration (Codecov)
- [ ] Sentry DSN config (dev/staging/prod)
- [ ] Secrets management (EAS or 1Password)

### [ ] Documentation
- [ ] API compatibility guide (mobile vs web endpoints)
- [ ] Development setup guide (environment variables, SDK versions)
- [ ] Architecture decision record (ADR-0014: Mobile platform choice)

### Deliverables (EOW2)
- [ ] RN project buildable locally
- [ ] Auth flow works end-to-end (sign-in → home → sign-out)
- [ ] CI/CD pipeline green (all tests passing)
- [ ] 50+ unit tests for auth/API
- [ ] Architecture documented

---

## Week 3-4: MVP Core

### [ ] Navigation Structure
- [ ] Bottom tab navigator (5 tabs: Dashboard, Execution, Defects, Notifications, Profile)
- [ ] Stack navigators (detail screens nested under each tab)
- [ ] Splash screen (logo, loading animation)
- [ ] Error boundary (crash recovery, offline fallback)
- [ ] Deep-linking resolution (URI → screen navigation)

### [ ] Dashboard Screen
- [ ] Case list (FlatList virtualization)
  - [ ] Display: title, status, priority, assignee
  - [ ] Tap → case detail
  - [ ] Pull-to-refresh
  - [ ] Search & filter (by status, priority, team)
  - [ ] Pagination (cursor-based, load more)
- [ ] Empty state (no cases message)
- [ ] Offline indicator (badge when no network)
- [ ] Performance: render 1K cases without lag (<100ms)

### [ ] Case Detail Screen
- [ ] Display case metadata:
  - [ ] Title, description, status, priority, tags
  - [ ] Assignee, created/updated dates
  - [ ] Related defects (link list)
- [ ] Tabs: Overview, Runs, Defects, Comments
- [ ] Action buttons: Edit, Execute, Link Defect
- [ ] Share button (generate share link)

### [ ] State Management
- [ ] Zustand stores:
  - [ ] `authStore` (user, tokens, MFA state)
  - [ ] `uiStore` (notifications, loading, bottom sheet)
  - [ ] `syncStore` (queue status, conflict count)
- [ ] TanStack Query setup (cache, background sync)
- [ ] Devtools integration (React Query devtools)

### [ ] Error Handling
- [ ] API error responses (400, 401, 403, 500)
- [ ] Network error detection (offline banner)
- [ ] User-friendly error messages (i18n TR/EN)
- [ ] Sentry integration (error tracking)

### Deliverables (EOW4)
- [ ] Navigation stack functional
- [ ] Dashboard renders 1K cases smoothly
- [ ] Case detail screen complete
- [ ] 100+ unit tests for components/hooks
- [ ] No TypeScript errors

---

## Week 5-6: Execution Feature

### [ ] Test Step Recorder
- [ ] Step form:
  - [ ] Input: action type (click, type, wait, etc.)
  - [ ] Input: element locator (accessibility id, text, xpath)
  - [ ] Input: expected result (optional)
  - [ ] Validation: required fields, character limits
- [ ] Step list (reorderable with drag-and-drop)
- [ ] Edit/delete step actions
- [ ] Step preview (what does this step do?)
- [ ] Undo/redo (stack-based)

### [ ] Screenshot Capture & Annotation
- [ ] Camera roll access (request permission)
- [ ] Capture from camera (live screenshot)
- [ ] Annotate (draw, add text, highlight)
- [ ] Save locally (SQLite attachment table)
- [ ] Attach to step/run (link screenshot)

### [ ] Run Submission
- [ ] Create run (POST /api/v1/cases/:id/runs)
  - [ ] Summary: case_id, status (pass/fail/blocked), duration
  - [ ] Attach steps (POST each step)
  - [ ] Attach screenshots (multipart upload to S3)
- [ ] Success toast + navigation to run detail
- [ ] Error handling (retry, offline queue)
- [ ] Optimistic update (show submitted locally, verify on sync)

### [ ] Offline Behavior
- [ ] If offline during submission:
  - [ ] Queue run to SQLite
  - [ ] Show "pending sync" badge
  - [ ] Auto-sync when online
  - [ ] Show success on sync completion

### Deliverables (EOW6)
- [ ] Step recorder functional (10+ test cases)
- [ ] Screenshot capture works (iOS + Android)
- [ ] Run submission (online + offline paths)
- [ ] 80+ integration tests for execution
- [ ] Performance: submit run in <2 sec (network permitting)

---

## Week 7-8: Offline & Sync Layer

### [ ] SQLite Database
- [ ] Schema creation:
  - [ ] cases, runs, defects, comments tables
  - [ ] sync_queue (pending operations)
  - [ ] attachments (local screenshot metadata)
- [ ] Migrations (alembic-style, version tracking)
- [ ] Encryption at rest (AES-256 via realm-web-crypto)
- [ ] Database size monitoring (purge old data >3 months)

### [ ] Sync Manager
- [ ] Background sync task (expo-background-fetch):
  - [ ] Trigger on network reconnect
  - [ ] Replay queue (POST /api/v1/mobile/sync)
  - [ ] Fetch delta (GET /api/v1/mobile/delta?since=...)
  - [ ] Merge local + remote
  - [ ] Show toast notification ("Synced 5 items")
- [ ] Conflict resolution (server wins, log warning)
- [ ] Retry logic (exponential backoff, max 3 retries)
- [ ] Error recovery (persist queue to S3 on app exit)

### [ ] Offline UX
- [ ] Offline indicator badge (top bar)
- [ ] Disable submit button (force offline mode)
- [ ] Show pending changes (list of queued operations)
- [ ] Sync status screen (in progress, last synced timestamp)
- [ ] Network state listener (listen to platform connectivity)

### [ ] Data Persistence
- [ ] Case list caching (load from SQLite first)
- [ ] Run history caching (5-day rolling cache)
- [ ] Image caching (local filesystem, max 500MB)
- [ ] Cache invalidation (manual refresh, 1-hour TTL)

### Deliverables (EOW8)
- [ ] SQLite schema complete + migrations
- [ ] Sync manager tested with 20+ scenarios (online/offline transitions)
- [ ] Offline queue persists across app restarts
- [ ] Zero data loss under network failure (tested)
- [ ] 50+ sync tests passing
- [ ] Offline mode documented (user + dev)

---

## Week 9-10: Polish & Features

### [ ] Push Notifications
- [ ] FCM setup (iOS + Android)
  - [ ] Device token registration (POST /api/v1/notifications/subscribe)
  - [ ] Notification handling (foreground, background)
  - [ ] Deep-linking on notification tap
- [ ] Notification types:
  - [ ] "test.assigned" → case detail
  - [ ] "run.completed" → run results
  - [ ] "defect.commented" → defect detail
  - [ ] "team.invite" → onboarding
- [ ] Notification badge (count)
- [ ] Notification history screen (paginated list)
- [ ] Fallback polling (if FCM fails, poll every 30s)

### [ ] Defect Triage
- [ ] Defect list screen (similar to case list)
- [ ] Defect detail:
  - [ ] Title, description, status, priority, assignee
  - [ ] Comment thread (view + add comments)
  - [ ] Link to cases (1:N relationship)
  - [ ] Action: reassign, update status
- [ ] Comment input (rich text optional)
- [ ] Offline: queue comments locally, sync on reconnect

### [ ] Team Collaboration
- [ ] Team member list (search, @mention)
- [ ] User presence (optional, deferred to Y2)
- [ ] Assignee dropdown (with avatar)
- [ ] Comments: show author avatar + name

### [ ] Accessibility (WCAG 2.1 AA)
- [ ] Screen reader support (VoiceOver/TalkBack labels)
- [ ] Color contrast (4.5:1 ratio minimum)
- [ ] Touch targets (48pt minimum)
- [ ] Keyboard navigation (tab order)
- [ ] Testing with: Xcode Accessibility Inspector, Android TalkBack

### [ ] Localization (i18n)
- [ ] TR + EN translations (gettext or i18next)
- [ ] RTL support (if needed, defer to Y2)
- [ ] Date/time formatting (locale-aware)
- [ ] Number formatting (currency, decimals)

### [ ] Performance Audit
- [ ] Cold start measurement (<2 sec target)
- [ ] Memory profiling (peak <150MB)
- [ ] Frame rate monitoring (60 FPS target)
- [ ] Network request batching (reduce API calls)
- [ ] Image optimization (WebP, lazy loading)

### Deliverables (EOW10)
- [ ] Notifications working (FCM + fallback)
- [ ] Defect triage complete (view, comment, reassign)
- [ ] Team collaboration foundation
- [ ] Accessibility audit passed (WCAG 2.1 AA)
- [ ] Localization complete (TR + EN)
- [ ] Performance benchmarks documented
- [ ] 100+ new unit/integration tests
- [ ] 0 TypeScript errors, full type coverage

---

## Week 11-12: Launch Prep

### [ ] App Store Submission (iOS)
- [ ] Create Apple Developer account
- [ ] Create app record on App Store Connect
- [ ] Generate provisioning profiles + certificates
- [ ] Build + sign (eas build --platform ios)
- [ ] Upload to TestFlight (eas submit --platform ios)
- [ ] Internal testing (QA team, 5+ test devices)
- [ ] Closed beta (50 external testers, 2-week feedback window)
- [ ] Resolve rejections (privacy policy, permissions, guidelines)
- [ ] App Store review submission
- [ ] Monitor review progress (1-3 days typical)

### [ ] Google Play Submission (Android)
- [ ] Create Google Play Developer account
- [ ] Create app on Google Play Console
- [ ] Generate signing key (upload key certificate)
- [ ] Build + sign (eas build --platform android)
- [ ] Upload to Google Play internal testing
- [ ] QA testing (5+ test devices, various Android versions)
- [ ] Closed beta track (50 external testers)
- [ ] Internal review for Play Store compliance
- [ ] Publish to production

### [ ] Launch Marketing
- [ ] Landing page (`neurex.ai/mobile`)
  - [ ] Feature highlights (3-5 bullet points)
  - [ ] Screenshots (5 key screens)
  - [ ] Video demo (30-60 sec, hosted on YouTube)
  - [ ] Download buttons (TestFlight + Google Play)
  - [ ] User testimonials (1-2 quotes from beta testers)
  - [ ] FAQ (5-10 common questions)
- [ ] Blog post ("Why Neurex chose React Native", tech + business angles)
- [ ] Press release (Product Hunt, Hacker News, tech blogs)
- [ ] Email campaign (to 500+ web users, segmented by role)
- [ ] Social media (Twitter/LinkedIn threads, daily updates for 1 week)
- [ ] Customer outreach (call 20 enterprise customers, demo + early access)

### [ ] Post-Launch Monitoring
- [ ] Sentry dashboard live (monitor crashes hourly)
- [ ] Analytics dashboard live (Amplitude funnels)
- [ ] App store reviews monitoring (daily, first 30 days)
- [ ] Customer support (respond to issues <24 hours)
- [ ] Hotfix SLA (critical bugs patched within 24 hours)

### [ ] Documentation & Knowledge Transfer
- [ ] README + setup guide (onboard new devs in future)
- [ ] Architecture ADR (decisions made, trade-offs)
- [ ] API reference (mobile-specific endpoints)
- [ ] Deployment guide (how to ship updates)
- [ ] Incident playbook (common issues + fixes)
- [ ] Team retrospective (lessons learned)

### Deliverables (EOW12)
- [ ] iOS + Android builds passing all checks
- [ ] TestFlight + Google Play beta live
- [ ] Landing page published
- [ ] Blog post + PR published
- [ ] Launch day press/social scheduled
- [ ] Monitoring dashboards live
- [ ] Documentation complete
- [ ] Team trained on deployment/support

---

## Week 13+ (Post-Launch Monitoring)

### [ ] Week 13-16: Closed Beta Feedback
- [ ] Collect NPS from 50 beta testers
- [ ] Track crash rate + top issues
- [ ] Merge critical bug fixes daily
- [ ] OTA updates (no app review delay)
- [ ] Customer interviews (5-10 deep-dive calls)

### [ ] Week 17-24: Open Release & Scale
- [ ] Public launch to app stores
- [ ] Monitor adoption (target: 50 installs/week)
- [ ] Feature iteration (bi-weekly releases)
- [ ] Performance optimization (based on real user data)
- [ ] User feedback synthesis (10 top feature requests)

### [ ] End of Year Review (Dec 2026)
- [ ] Adoption metric check (5K+ MAU?)
- [ ] Revenue (ARR $250K on track?)
- [ ] NPS (≥40?)
- [ ] Go/No-Go decision on mobile strategy Y2

---

## Success Criteria (Green Lights)

### Launch Gate (Week 12)
- [ ] Zero critical bugs (app doesn't crash on happy path)
- [ ] Latency <2 sec (cold start, case list load)
- [ ] Sync accuracy 100% (no data loss observed)
- [ ] Offline mode works (record offline, sync online)
- [ ] Authentication works (sign-in, MFA, logout)
- [ ] App store & Play store approval obtained

### 6-Month Gate (Dec 2026)
- [ ] MAU ≥5K (minimum viability)
- [ ] DAU/MAU ≥25% (basic engagement)
- [ ] Crash-free rate ≥99% (stability)
- [ ] NPS ≥40 (acceptable satisfaction)
- [ ] ARPU ≥$10 (revenue potential)

### Decision Gate (Jan 2027)
- [ ] If all gates green → continue mobile, plan Y2 roadmap
- [ ] If NPS <30 or MAU <1K → sunset project (cut losses, focus web)
- [ ] If performance issues → technical debt sprint before scale

---

## Risk Checklist

| Risk | Probability | Mitigation | Owner |
|------|-----------|-----------|-------|
| RN performance lag (10K lists) | 30% | Profile early, FlatList virtualization, Hermes | Tech Lead |
| App store rejection | 20% | Audit week 10, legal review, support tier | QA/DevOps |
| Data loss in offline mode | 10% | Atomic SQLite, encrypted backup | Dev 1 |
| Sync conflicts (server/client) | 15% | Comprehensive test suite, conflict resolution | Dev 2 |
| Low adoption (<50/week) | 15% | Customer validation, landing page, email | PM |
| Competitor ships native | 60% | Ship fast, differentiate on features | Leadership |
| Team member churn | 20% | Documentation, pair programming | Tech Lead |

---

## Budget Tracking

### Personnel (12 weeks)
- Tech Lead: 12w × $3.5K/week = $42K
- Dev 1: 12w × $2.6K/week = $31.2K
- Dev 2: 12w × $2.6K/week = $31.2K
- QA/DevOps: 12w × $2.4K/week = $28.8K
- **Subtotal:** $133.2K

### Infrastructure & Tools
- EAS Build: $10K (pro plan, 12 weeks)
- TestFlight: $0 (free, bundled with Apple Dev)
- Google Play: $0.5K (developer account + submission)
- Sentry: $5K (annual pro plan)
- Amplitude: $2K (annual startup plan)
- Firebase: $1.5K (hosting + FCM + analytics)
- AWS S3 (backups): $1K
- Domain + SSL: $0.3K (shared with web)
- **Subtotal:** $20.3K

### Contingency (15% of salaries)
- **Contingency:** $20K

### Total Budget
- **Personnel:** $133.2K
- **Infrastructure:** $20.3K
- **Contingency:** $20K
- **Total:** $173.5K

Plus web team overhead (design, PM, QA, infra support): ~$80K  
**Grand Total:** ~$250K (slightly over initial $200K estimate, acceptable)

---

## Sign-off

- [ ] CTO approval (technical approach)
- [ ] CFO approval (budget $250K)
- [ ] Product Lead approval (roadmap fit)
- [ ] Engineering Lead approval (team capacity)
- [ ] Customer Advisory Board approval (feature priority)

**Approval Date:** _________

**Approved By:**
- CTO: ________________________
- CFO: ________________________
- Product: ________________________
- Engineering: ________________________

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-09  
**Next Review:** Week 0 kickoff (approval meeting)
