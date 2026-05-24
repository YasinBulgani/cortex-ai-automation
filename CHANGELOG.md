# Changelog

Bu dosya [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) formatını izler,
proje [Semantic Versioning](https://semver.org/spec/v2.0.0.html) kullanır.

Kategoriler: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

## [Unreleased]

### Added — P1/P2 sprint devamı (2026-05-24, Tur 4, Neurex_QA port)

**Backend — Kritik Bug Fix (Neurex_QA port)**
- `backend/app/core/router_registry.py`: `events`, `marketplace`, `visual`, `pilot` router'ları eklendi — 4 domain router'ı uygulamaya bağlanmamıştı; 404 dönüyordu.
- `backend/tests/integration/test_router_registration.py`: Parametrize listesi 14 prefix'e genişletildi.

**Docs**
- `docs/semgrep-secrets-runbook.md` oluşturuldu — SEMGREP_APP_TOKEN, CI secrets, yerel tarama, false positive suppression, eskalasyon prosedürü (P1 #35).

**Tests — Backend**
- `backend/tests/unit/conftest.py`: `feature_flags_svc` fixture eklendi (P1 #41).
- `backend/tests/unit/test_products_service.py`, `test_events_service.py`, `test_jobs_service.py`, `test_rules_service.py`, `test_automation_service.py`, `test_agents_service.py`, `test_n8n_service.py`, `test_artifacts_service.py`, `test_git_fetch_service.py`, `test_nexus_repo_service.py`, `test_pilot_service.py` — toplam 109 unit test (Neurex_QA port).
- `backend/tests/test_smoke.py`: 4 yeni smoke test — events/defects/kb/pilot router kaydı doğrulama.

**Frontend**
- `apps/web/lib/useKnowledgeBase.ts`: Backend-first load eklendi — `/api/v1/kb/articles` endpoint artık kayıtlı.

**Tests — Engine**
- `engine/tests/unit/core/test_step_mapper.py` — 9 test class, step_mapper coverage (P1 #31).
- `engine/tests/unit/test_utility_routes.py` — 11 test; utility Flask routes.
- `engine/tests/unit/test_auth_security.py` — 9 test; login/register/logout güvenlik testleri.
- `engine/tests/unit/test_recorder_routes.py` — 37 test; recorder routes + Cortex'e özgü pause/resume/status endpoint'leri.
- `engine/tests/unit/test_wizard_routes.py` — 20 test; 7 wizard endpoint coverage.
- `engine/tests/unit/test_pipeline_routes.py` — 25 test; assertion synthesis regresyon testleri dahil pipeline coverage.
- `backend/tests/integration/test_new_domain_routers.py` — 8 domain router kaydı kontrol testi.

### Added — Backend DDD service.py facade'ları + P0/P1 deficiency düzeltmeleri (2026-05-24)

**Backend — 6 yeni service.py facade (Neurex_QA'dan port, DDD pattern tamamlandı)**
- `domains/accessibility/service.py`, `cicd/service.py`, `compliance/service.py`, `evals/service.py`, `mobile/service.py`, `catalog/service.py` — router + specialist module arasında DDD facade katmanı.

**Backend — P0 hata düzeltmeleri (Neurex_QA'dan port)**
- `domains/cicd/quality_gate.py`: `BaseCheck` → `class BaseCheck(ABC)` + `run()` → `@abstractmethod`.
- `domains/migration/assistant.py`: sessiz `// TODO` çıktısı → `throw new Error('⚠ MIGRATION_REQUIRED: ...')` ve `pytest.fail('...')`.
- `engine/features/lks.featıres.feature`: boş dosya silindi.

**Backend — P2 sessiz exception düzeltmeleri**
- `playwright_mcp/browser_manager.py`, `evals/adapters/prompt_shield_adapter.py`, `ingestion/service.py`, `api_testing/security_scanner.py`, `api_testing/test_prioritizer.py`: `except: pass` → `logger.warning/debug(..., exc_info=True)`.
- `quality/service.py`: ENV double naming (`ENGINE_EVAL_REPORTS_DIR` → `EVAL_REPORTS_DIR` öncelikli, fallback korundu).

**Frontend**
- `apps/web/app/(dashboard)/kb/page.tsx`: Render-sync `setState` hazard → `useEffect + useRef` ile düzeltildi.
- `apps/web/app/(dashboard)/new-project/page.tsx:858`: Step definition üretiminde `// TODO: implement` → akıllı action skeleton (click/fill/expect/goto/waitFor/selectOption).
- `apps/web/package.json`: `@axe-core/playwright@^4.10.1` eklendi.

**Engine**
- `engine/core/test_recorder.py`: `TR_KEYWORDS` sözlüğüne 12 yeni action type eklendi. Bilinmeyen action'lar artık `raise NotImplementedError(...)` üretir.

**Tests**
- `backend/tests/conftest.py`: `feature_flags_svc` fixture eklendi.

### Added — Monorepo paketleri ve backend DDD (admiring-bartik-50490a, 2026-05-17)

**`@neurex/ai-sdk` — production-grade (109 test)**
- 4 provider implementasyonu (Anthropic / Groq / Gemini / Ollama), her biri circuit breaker + retry-safe error mapping ile.
- SSE stream parser, fetch-with-timeout helpers, BaseProvider.
- `IntelligentRouter`: intent → tier mapping, latency SLA filtresi, fallback chain, cost estimate.
- `PromptRegistry` + 3 built-in TR prompt (BDD üretimi, test failure analizi, locator healing).
- `ToolRegistry`: MCP-uyumlu tool registry (register/get/list/invoke), `searchProjectTool` örneği.
- Observability: `TelemetryRegistry`, `BufferSink`, `ConsoleSink`, `withTelemetry()` wrapper, `CostTracker` (tenant/user başı budget kontrolü).
- Guardrails: PII redaction (TCKN/IBAN/email/GSM/JWT/API key/IPv4) + injection detection (TR + EN heuristic, 0..1 score).
- Eval framework: `EvalCase` + `EvalRunner` (concurrency, tag filter, skip), 12 assertion türü (contains, regex, json_valid, json_has_keys, length, perf, custom). 3 starter case (scenario-generate, analyze-failure).
- Test coverage: 9 test file, 109 test — `tools/`, `prompts/library`, tüm modüller kapsandı.

**`@neurex/design-system` — 35+ primitive, 6 hook, 2 büyük pattern (307 test)**
- Form: `Button`, `Input`+`Textarea`, `Switch`, `Checkbox`, `Radio`+`RadioGroup`, `Select`, `Label`+`FieldHelp`, `FormField` composer, `FileInput` (button + dropzone), `Slider`, `Rating`.
- Feedback: `Badge`, `Alert`, `ToastProvider`+`useToast`, `Skeleton`+`SkeletonText`+`SkeletonCard`, `Spinner`, `Progress`, `Divider`.
- Container: `Card`+`CardHeader`+`CardBody`+`CardFooter`.
- Overlay: `Dialog` (focus trap, ESC, body scroll lock), `DropdownMenu`, `Popover`.
- Navigation: `Tabs`+`TabPanel`, `Accordion`, `Breadcrumb`, `Pagination`, `Stepper`, `Toolbar`+`ToolbarGroup`+`ToolbarSeparator`.
- Patterns: `DataTable<TRow>` (generic, sortable, paginated, controlled+uncontrolled), `CommandPalette` (cmdk-style fuzzy launcher), `CodeBlock` (line numbers, copy-to-clipboard).
- Hooks (SSR-safe): `useDebounce`, `useMediaQuery`+`breakpoints`, `useLocalStorage`, `useCopyToClipboard`, `useClickOutside`, `useDarkMode`.
- Test coverage: `Tooltip` (6), `EmptyState` (7), `Kbd`+`KbdGroup` (9), `Sparkline` (9), `StatCard` (10), `ActivityHeatmap` (8) — 40 test dosyası, 307 test toplamda.
- Storybook stories: Tooltip, EmptyState, Kbd, ActivityHeatmap — tüm primitive'ler için story mevcut.

**Backend DDD — identity context infrastructure + FastAPI routers (134 test)**
- `backend/app/contexts/identity/infrastructure/`: `InMemoryUserRepository` (email+id double index), `SqlAlchemyUserRepository`+`UserRow` (`iam_users` tablosu), `BcryptPasswordHasher` (lazy import), `FakePasswordHasher` (deterministic test double).
- `backend/app/contexts/identity/application/`: `ChangeEmailCommand`+Handler (conflict check, same-email noop), `DeactivateUserCommand`+Handler (idempotent).
- `backend/app/contexts/projects/api/router.py`: REST CRUD (POST/GET/PATCH/DELETE), `Depends(get_current_user)`, Pydantic v2 schemas, dependency-override-friendly.
- `backend/app/contexts/scenarios/api/router.py`: POST/GET/submit/approve, cross-context ProjectExistsCheckAdapter (singleton paylaşımı).
- `backend/app/core/router_registry.py`: defensive import (try/except) ile context router kayıt blokları.
- `backend/app/contexts/conftest.py`: test env vars (JWT_SECRET/ENGINE_INTERNAL_KEY/GATEWAY_INTERNAL_KEY) pytest collection öncesi set edilir.
- 25 use-case + infra testi (in-memory repos + fake checks), 12 projects API testi, 13 scenarios API testi — toplam 134 backend context testi.

**Backend DDD application + infrastructure (projects + scenarios — önceki)**
- `backend/app/contexts/projects/application/`: `CreateProjectCommand`+Handler (uniqueness), `RenameProjectCommand`+Handler (conflict check), `ArchiveProjectCommand`+Handler (idempotent), `ProjectRepository` Protocol.
- `backend/app/contexts/projects/infrastructure/`: `InMemoryProjectRepository` (test/dev), `SqlAlchemyProjectRepository`+`ProjectRow` (Postgres, async), `ProjectExistsCheckAdapter` (scenarios/application için).
- `backend/app/contexts/scenarios/application/`: `CreateScenarioCommand`+Handler (cross-context project guard), `SubmitForReviewCommand`+Handler (step-count guard), `ApproveScenarioCommand`+Handler, `ScenarioRepository` Protocol.

**Pipeline tamiri (önceki merge eksiklikleri)**
- `confirm-dialog.tsx` useRef init type error → düzeltildi.
- `eslint-config-next` 16 vs ESLint 8.57 circular-JSON çatışması → kurulu plugin'lerle çalışan minimal eslintrc (web + ai-sdk + design-system).
- Jest devDeps eksikti → `package.json`a eklendi + script self-check ile graceful no-op (sonraki `npm install` enable eder).
- Paketlerdeki `echo 'TODO: lint'` stub'lar → gerçek `eslint` script (storybook için no-source guard).

### Added (önceki)
- `docs/adr/` — 5 ADR ile mimari karar kayıtları sistemi (monorepo, engine/backend ayrımı, synthetic-data, legacy politikası, test taksonomisi)
- `docs/architecture/engine-backend-contract.md` — Flask engine ↔ FastAPI backend arası resmi HTTP kontratı, deprecation takvimi
- `docs/architecture/synthetic-data-gap-analysis.md` — platform-v4 → backend merge için özellik karşılaştırması
- `qa/strategy/test-strategy.md` — "yeni test nereye yazılır?" karar ağacı, piramit, marker sistemi
- `CONTRIBUTING.md` — setup, branch/PR/commit kuralları, release akışı
- `.github/CODEOWNERS` — domain bazlı review ataması
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/` (bug, feature, config)
- `.github/dependabot.yml` — 12 ekosistem × haftalık/aylık security güncellemeleri
- `.github/workflows/architecture-guards.yml` — 7 CI koruması (pyc/DS_Store/tsbuildinfo tracked değil, legacy salt-okunur, root dizin sprawl, broken symlink, duplicate ADR)
- `legacy/` dizini — 6 ay saklama politikası (ADR-0004) ile arşiv
- `performance-tests/` — k6 load/stress/spike/soak testleri için üst-seviye dizin
- `engine/services/llm_gateway.py`: proxy mode (`ENGINE_LLM_USE_GATEWAY=1`) — AI Gateway'e HTTP proxy, 9 unit test (feature-flag, default kapalı)
- `engine/app.py`: deprecated route'lara otomatik `Sunset: 2026-06-01` + `Deprecation: true` header

### Changed
- `docker-compose.yml` engine port `5001:5001` → `127.0.0.1:5001:5001` (LAN'dan erişim kapalı, docker iç ağdan açık)
- Engine healthcheck eklendi; backend `depends_on: engine: service_healthy`
- `.pre-commit-config.yaml`: 4 yeni guard (no-tracked-pyc, no-ds-store, no-tsbuildinfo, legacy-readonly)
- Root README "Silinmeye Aday Modüller" tablosu → `legacy/README.md`'ye link
- Backend `pytest.ini` marker'ları genişletildi (`ai`, `requires_db`, `requires_redis`, `flaky`, `P0`)

### Removed
- `tests/` (root) — hardcoded path'li kırık Python entegrasyon testleri silindi
- 38 tracked `*.pyc` dosyası untrack edildi
- `apps/web/pages/_document.tsx` — Next 14 App Router'da gereksiz
- `apps/web/apps/` phantom dizin + `apps/web/tsconfig.tsbuildinfo` tracking

### Archived (legacy/2026-04-cleanup/)
- `ai-engine/` — TypeScript CLI araçları (kullanılmıyor)
- `MaviYakaTestOtomasyon/` (root) — Java/Maven Selenium projesi
- `scaffolded_projects/` — test scaffold örnekleri
- `backend/synthetic-data-v2/`, `v3/`, `bgtsflow/` — eski sürümler
- `synthetic-data/platform/` — önceki platform sürümü
- `synthetic-data/mostlyai-datasets/`, `mostlyai-generators/` — 448 model artefaktı dosyası
- `frameworks/selenium-cucumber-java/`, `Test_Template/` — kullanılmayan framework'ler
- `docs/test-otomasyon/` — 61 MB, 3965 dosya (10 deneysel proje; MaviYaka duplicate + 9 scaffold)
- `otomasyon-ekibi/` — sadece venv içeren klasör (silindi)

### Fixed
- `backend/app/main.py`: startup'ta `load_schedules_from_db()` — restart sonrası TspmSchedule sessiz veri kaybı

### Security
- Engine 5001 portu LAN'dan erişilemez hale getirildi
- `.gitignore` genişletildi: `*.tsbuildinfo`, `*.bak`, `*.orig`, `*.rej`, `*.old`, `*.swo`, `*~`

---

## Sürüm notu şablonu (gelecek release'ler için)

```markdown
## [0.6.0] - 2026-MM-DD

### Added
- …

### Changed
- …

### Fixed
- …

### Removed / Deprecated
- …

### Security
- …

### Migration notes (breaking ise)
- …
```

## Takvim

- **2026-05-01** — `tests/` root klasörü silme hedefi (tamamlandı 2026-04-19 ✓)
- **2026-06-01** — Engine'deki deprecated route'ların tam kaldırılması (ADR-0002, sunset header aktif)
- **2026-10-19** — `legacy/2026-04-cleanup/` dizininin tümden silinmesi (ADR-0004)

[Unreleased]: https://github.com/YasinBulgani/cortex-ai-automation/compare/main...HEAD
