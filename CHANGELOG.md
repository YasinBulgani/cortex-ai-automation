# Changelog

Bu dosya [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) formatını izler,
proje [Semantic Versioning](https://semver.org/spec/v2.0.0.html) kullanır.

Kategoriler: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

## [Unreleased]

### Added — Wave 16/17: Router testleri tamamlandı, security fixes (2026-05-26, Tur 14)

**Backend — Router unit testleri (Wave 16)**
- `test_events_router.py` — 10 test; history/stats/publish-test.
- `test_defects_router.py` — 13 test; CRUD, state machine, invalid transition 404.
- `test_ingestion_router.py` — 13 test; ingest/requirements CRUD, jira webhook.
- `test_knowledge_base_router.py` — 19 test; articles CRUD, search, sort/filter.
- `test_compliance_router.py` — 11 test; controls list/filter/map, coverage.
- `test_visual_router.py` — 12 test; compare (Pillow unavailable 503), results, baseline.
- `test_marketplace_router.py` — 15 test; templates/categories/stats, install, status.
- `test_pilot_router.py` — 16 test; session CRUD, converse, execute-stage, clarify.
- `test_artifacts_router.py` — 10 test; download (path traversal guard, 403/404), admin bypass.
- `test_jobs_router.py` — 12 test; enqueue, status, events, artifacts.
- `test_rules_router.py` — 11 test; rule-set CRUD, audit log.
- `backend/tests/unit/conftest.py`: `rbac_audit_store` fixture eklendi.

**Engine**
- `engine/app.py`: `visual_ai_bp` eklendi — blueprint kayıt eksikliği giderildi.

**Backend — Servis testleri**
- `engine/tests/unit/services/test_bdd_generator.py` — 17 test; generate, parse, coverage analizi.

**Güvenlik (Auth router P1 fixes)**
- `backend/app/domains/auth/router.py`: Timing attack düzeltildi — kullanıcı bulunamasa dahi dummy bcrypt hash verify yapılıyor.
- `backend/app/domains/auth/router.py`: In-memory rate limiting eklendi — 10 deneme/5 dakika/IP.
- `backend/app/domains/auth/router.py`: Refresh token hata mesajında internal detail ifşası giderildi.
- `backend/app/domains/auth/service.py`: `_DUMMY_HASH` sabit eklendi.

**Dokümantasyon**
- `docs/testing-coverage-report.md` — Sprint sonu test kapsama raporu (355+ dosya, 3960+ test).

### Added — Wave 15/16: Router testleri, domain tamamlama, final düzeltmeler (2026-05-26, Tur 13)

**Backend — Router unit testleri**
- `backend/tests/unit/test_auth_router.py` — 12 test; login/logout/refresh/me/forgot-password/reset-password, enumeration-safe 200.
- `backend/tests/unit/test_billing_router.py` — 12 test; GET plans/usage/subscription, POST plan/checkout, ValueError→400.
- `backend/tests/unit/test_tspm_router.py` — 9 test; project/scenario/execution CRUD, 404/422 hata yolları.
- `backend/tests/test_smoke.py`: Wave 12 router smoke testleri eklendi (rbac, navigation, email, pr-bot).
- `backend/tests/integration/test_router_registration.py`: 44 prefix'e genişletildi.

**Engine — Servis testleri**
- `engine/tests/unit/services/test_bdd_generator.py` — 17 test; generate, _parse_output, _analyze_step_coverage, _step_matches, LLMGateway mock.
- `engine/tests/unit/test_metrics_routes.py` — 15 test; Prometheus format, counter increment, JSON schema.

**Frontend**
- `apps/web/lib/__tests__/useKnowledgeBase.test.ts` — 13 test; backend-first load, localStorage fallback, CRUD, search, vote.

**CI/CD**
- `.github/workflows/ci.yml` (Neurex): Python 3.11+3.12 matrix + `actions/cache@v4` pip cache.

**Altyapı**
- `scripts/validate-prod-env.sh` — REQUIRED/OPTIONAL değişken doğrulama, deployment öncesi zorunlu.
- `.env.example`: `SEMGREP_APP_TOKEN`, `ENGINE_EVAL_REPORTS_DIR`, `EVAL_REPORTS_DIR` eklendi.
- `docs/runbooks/jenkins-setup.md` — 5 kritik Jenkins credential kurulum rehberi (P0 #2 tamamlandı).
- `docs/adr/ADR-0007-service-layer-ddd-pattern.md` — Yeniden numaralandırıldı.
- `docs/backend-domain-coverage.md` — 48/48 domain coverage, tüm "eylem gerektiren" domainler tamamlandı.

### Added — Wave 14: CI matrix, smoke testler, runbook'lar (2026-05-26, Tur 12)

**CI/CD İyileştirmeleri**
- `.github/workflows/ci.yml` (Neurex): Python matrix genişletildi `["3.11", "3.12"]` — 4 backend job'da paralel test.
- `.github/workflows/ci.yml` (Neurex): `actions/cache@v4` pip cache adımı eklendi — versiyon-bazlı key ile.

**Backend — Yeni testler**
- `backend/tests/test_smoke.py`: Wave 12 router'ları (rbac, navigation, email, pr-bot) smoke testlere eklendi.
- `backend/tests/integration/test_router_registration.py`: 4 yeni prefix eklendi (rbac, navigation, email, pr-bot) — toplam 44 prefix.
- `backend/tests/unit/test_automation_suite_router.py` — 11 test; generate/run/run-status/catalog-suggest/health/mobile-generate endpoint'leri.
- `backend/tests/unit/test_ai_router.py` — 14 test; chat sessions, LLM usage, providers, knowledge ingest, assert-advisor.
- `backend/tests/unit/test_rbac_service.py` — 36 test; list_roles, check_permission, wildcard, enforce_segregation, multi-role.
- `backend/tests/unit/test_navigation_service.py` — 21 test; nav tree, bookmark CRUD, multi-user.

**Frontend**
- `apps/web/lib/__tests__/useKnowledgeBase.test.ts` — 13 test; backend-first load, localStorage fallback, CRUD, search, vote.

**Dokümantasyon**
- `docs/runbooks/jenkins-setup.md` — 5 kritik Jenkins credential (ghcr-creds, staging-db-url, staging-redis-url, prod-db-url, prod-deploy-key) kurulum rehberi (P0 #2 tamamlandı).
- `docs/adr/ADR-0007-service-layer-ddd-pattern.md` — Yeniden numaralandırıldı (0006 çakışması giderildi).
- `docs/backend-domain-coverage.md` — 48 domain coverage güncellendi; 6 eski "eylem gerektiren" domain ✅ tamamlandı.

**Infra**
- `scripts/validate-prod-env.sh` — Production env değişken doğrulama scripti (P1 #34).
- `Makefile`: `validate-env` hedefi eklendi.

### Added — Wave 13: P0 düzeltmeleri, RBAC/Navigation, Engine metrics (2026-05-26, Tur 11)

**P0 Düzeltmeleri**
- `Makefile`: `setup-venv` (Python venv kurulumu), `sec-audit` (Bandit+Safety), `eval`, `tia` hedefleri eklendi (P0 #1 tamamlandı).
- `backend/app/domains/products/router.py`: Demo data `X-Data-Mode: demo` header + `demo_mode: true` ile şeffaf olarak işaretlendi (P0 #4).

**Engine — P1 #36 tamamlandı**
- `engine/routes/metrics_routes.py`: Prometheus-uyumlu `/api/metrics` + JSON `/api/metrics/json` endpoint'leri.
- `engine/app.py`: `metrics_bp` kaydedildi.
- `engine/tests/unit/test_metrics_routes.py` — 15 test; Prometheus format, counter increment, JSON schema.

**Backend — Yeni servis ve router testleri**
- `backend/tests/unit/test_rbac_service.py` — 36 test; list_roles, get_role, check_permission, wildcard, enforce_segregation, multi-role union.
- `backend/tests/unit/test_navigation_service.py` — 21 test; nav tree, bookmark CRUD, multi-user, idempotent add, KeyError remove.

**Dokümantasyon**
- `docs/adr/ADR-0011-service-layer-ddd-pattern.md` — DDD servis katmanı kararı (ADR-0011).
- `docs/INDEX.md`: Son güncelleme tarihi ve 4 yeni doküman girişi eklendi.

### Added — Wave 12: Eksik domain'ler tamamlandı (2026-05-26, Tur 10)

**Backend — Yeni servis facade'ları ve router'lar**
- `backend/app/domains/rbac/service.py` + `router.py` — RBAC/SoD servisi; GET /roles, POST /check-permission, POST /enforce-sod.
- `backend/app/domains/email/service.py` + `router.py` — Email gönderim servisi; GET /templates, POST /preview, POST /send.
- `backend/app/domains/pr_bot/router.py` — PR bot router; POST /pr-bot/analyze, GET /pr-bot/health.
- `backend/app/domains/navigation/service.py` + `router.py` — Navigasyon bookmark yönetimi; tree, bookmark CRUD.
- `backend/app/domains/automation_templates/service.py` — Template CRUD, 3 built-in template ile başlıyor.
- `backend/app/domains/migration/service.py` — Migration assistant facade.
- `backend/app/core/router_registry.py`: 4 yeni router eklendi (rbac, email, pr_bot, navigation) — defansif import ile.

**Backend — Wave 12 unit testleri**
- `backend/tests/unit/test_rbac_service.py` — 15 test; list_roles, get_role, check_permission, enforce_segregation.
- `backend/tests/unit/test_navigation_service.py` — 12 test; bookmark CRUD, multi-user, KeyError remove.
- `backend/tests/unit/test_email_service.py` — 12 test; preview, send, unknown template → ValueError.
- `backend/tests/unit/test_automation_templates_service.py` — 14 test; CRUD, apply_template.
- `backend/tests/unit/test_migration_service.py` — 12 test; migrate/migrate_file/get_supported_frameworks.

**Engine**
- `engine/routes/metrics_routes.py`: Prometheus-uyumlu `/api/metrics` endpoint + JSON format.
- `engine/tests/unit/test_metrics_routes.py` — 10 test; Prometheus format, JSON format, counter increment.

**P0 Düzeltmeleri**
- `Makefile`: `setup-venv`, `sec-audit`, `eval`, `tia` hedefleri eklendi (P0 #1).
- `backend/app/domains/products/router.py`: Demo data `X-Data-Mode: demo` header + `demo_mode: true` ile işaretlendi (P0 #4).
- `README.md`: `framework/` → `frameworks/cortex-java/`, `BGTS_Test_Donusum` → `Cortex_Ai_Automation` (P0 #9).

### Added — Wave 11: AI testleri, güvenlik, dokümantasyon (2026-05-26, Tur 9)

**AI Domain — Genişletilmiş testler**
- `backend/app/domains/ai/tests/test_streaming_service.py` — 15 test; SSE stream token events, complete event, mid-stream hata, RAG context enjeksiyonu.
- `backend/app/domains/ai/tests/test_pii_redactor_extended.py` — 42 test; TCKN/IBAN/email/telefon maskeleme, nested JSON, çoklu PII, `redact_with_stats`.
- `backend/app/domains/ai/tests/test_output_shield_extended.py` — 32 test; Luhn kart tespiti, SQL injection, jailbreak marker, PII sızıntısı, system prompt leak.

**Backend — Yeni test dosyaları**
- `backend/tests/unit/test_exception_handlers.py` — 24 test; ValueError→400, KeyError→404, RuntimeError→500, global handler doğrulaması.
- `backend/tests/unit/test_quality_service_perf.py` — 11 test; EvalSnapshot instantiation <1ms, parse_eval_report <10ms, _read_history 100 dosya <500ms.

**Frontend**
- `backend/app/domains/ai/tests/test_streaming_service.py` — Cortex ve Neurex'e ported.
- `apps/web/lib/__tests__/useCustomDashboard.test.ts` — 13 test; backend-first load, localStorage fallback, CRUD operasyonları.

**Güvenlik**
- `.github/workflows/security.yml`: Bandit Python SAST + Safety dependency check job'ları eklendi.
- `.github/workflows/security-sast.yml` (Cortex): Bandit + Safety + npm audit eklendi.

**Dokümantasyon**
- `docs/adr/ADR-0006-service-layer-ddd-pattern.md` — DDD servis katmanı kararı belgelendi.
- `docs/testing-runbook.md` — Backend/engine/frontend test koşumu rehberi.
- `docs/backend-domain-coverage.md` — 48 domain coverage matrisi.

**Wave 10 porting**
- 42 Cortex backend test dosyası Neurex_QA'ya ported edildi (domain-agnostic olanlar).
- `backend/tests/unit/test_qa_service.py` (Cortex only) — 31 test; qa/ filesystem reader.
- `backend/tests/unit/test_test_management_service.py` (Cortex only) — 22 test.

### Added — Wave 9/10: Son testler, altyapı ve CI iyileştirmeleri (2026-05-26, Tur 8)

**Engine — Son route testleri (Wave 9)**
- `engine/tests/unit/test_visual_routes.py` — 21 test; baseline CRUD, karşılaştırma, toplu karşılaştırma, yükleme.
- `engine/tests/unit/test_llm_agent_routes.py` — 29 test; start/act/snapshot/close, warmup, stats, cache clear; PlaywrightWorker stub ile.

**Backend — Altyapı iyileştirmeleri (Wave 9)**
- `backend/pytest.ini`: `asyncio_mode = auto` eklendi — pytest-asyncio entegrasyonu.
- `engine/pytest.ini`: `asyncio_mode = auto` + `filterwarnings` eklendi.
- `backend/tests/conftest.py` + `backend/tests/unit/conftest.py`: `mock_db_session`, `mock_http_client`, `override_settings` fixture'ları eklendi.
- `backend/tests/integration/test_router_registration.py`: 18 prefix'ten 40 prefix'e genişletildi — tüm kayıtlı router'lar kapsandı.
- `backend/app/core/exception_handlers.py`: `value_error_handler` (400), `key_error_handler` (404) global handler'ları eklendi.

**P0 Bug Fix (Wave 9)**
- `backend/app/domains/test_management/service.py` (Cortex): 24 HTTPException → ValueError/KeyError/RuntimeError dönüşümü.

**Backend — Wave 10 test dosyaları**
- `backend/tests/unit/test_exception_handlers.py` — 12 test; ValueError→400, KeyError→404, global exception handler doğrulaması.
- `backend/tests/unit/test_test_management_service.py` (Cortex only) — 15 test; proje/test case/test run CRUD.
- `backend/tests/unit/test_qa_service.py` (Cortex only) — 12 test; qa/ filesystem reader, test case listesi, health raporu.
- 40+ Cortex backend test dosyası Neurex_QA'ya ported edildi — ortak altyapı testleri her iki repoda mevcut.

### Added — Backend domain testleri Wave 7/8 tamamlandı (2026-05-26, Tur 7)

**Backend — Domain servis unit testleri (Wave 7 — 222 test, 11 dosya)**
- `test_billing_service.py` — 28 test; plan katalogu, limit kontrolü, kullanım takibi, set_plan, record_usage.
- `test_catalog_service.py` — 18 test; dataset CRUD, versiyon yönetimi.
- `test_cicd_service.py` — 30 test; BaseCheck ABC, PassRateCheck/MaxFailuresCheck/DurationCheck/NoNewFlakiesCheck/CoverageCheck, QualityGate.evaluate, build_gate_from_config, run_quality_gate.
- `test_evals_service.py` — 27 test; EvalCase.from_dict, Suite.from_dict, run_eval_suite, run_all_suites, get_history, list_suite_names.
- `test_accessibility_service.py` — 16 test; _parse_json_array, analyzer_info, analyze_violations (feature on/off, LLM hata yönetimi).
- `test_audit_service.py` — 14 test; canonical_payload, compute_hash, verify_chain (değişiklik tespiti), log_audit.
- `test_notifications_service.py` — 14 test; WSMessage, ConnectionManager, notify_user, broadcast.
- `test_dsl_service.py` — 22 test; _tokenize, list_actions (sayfalama), get_action, search_actions, category_tree.
- `test_automation_suite_service.py` — 14 test; _RunRegistry, start_run, _match_gherkin_with_dsl.
- `test_cost_service.py` — 19 test; _usd_to_try_rate, _scale_to_monthly, get_pricing, estimate_cost_usd, estimate_monthly_cost.
- `engine/tests/unit/test_mobile_routes.py` — 20 test; cihaz katalogu, farm durumu (local/browserstack/sauce), run, APK yükleme.

**Backend — Domain servis unit testleri (Wave 8 — 261 test, 14 dosya + 1 bug fix)**
- `test_ai_service.py` — 33 test; PII tespiti/maskeleme, OpenAI/Anthropic mock, retry mekanizması, test sonucu analizi.
- `test_quality_service.py` — 32 test; EvalSnapshot, parse_eval_report (9 alan), _read_latest_report, _read_history.
- `test_tspm_service.py` — 19 test; SQLAlchemy session mock, proje/senaryo CRUD, limit cap.
- `test_health_service.py` — 21 test; _check_database, _check_redis, _check_engine, _check_ai_gateway, get_extended_health.
- `test_playwright_mcp_service.py` — 15 test; AsyncMock tabanlı, create/get/list/close session, execute_action, screenshot.
- `test_mobile_service.py` — 13 test; get_device_list, start_mobile_session, generate_steps_from_prompt, list_recent_sessions.
- `test_pr_bot_service.py` — 17 test; PRSummary, build_pr_summary, render_markdown.
- `test_prompts_service.py` — 15 test; list/get/upsert/archive prompt, add/get version.
- `test_onboarding_service.py` — 20 test; DEFAULT_STEPS, ProgressStore, compute_progress.
- `test_auth_service.py` — 22 test; bcrypt hash/verify, JWT create/decode/revoke, password reset token.
- `test_privacy_service.py` — 12 test; DSAR export, delete_user_ai_data, dry_run modu.
- `test_ai_synthetic_data_service.py` — 14 test; generate (KDE/CTGAN/bilinmeyen), list/get_dataset.
- `test_api_testing_service.py` — 12 test; import_spec, generate_tests_with_ai.
- `test_coverup_service.py` — 16 test; create_report, get_report_or_404, analyze_report, build_trend_response.

**P0 Bug Fix**
- `backend/app/domains/coverup/service.py`: HTTPException → ValueError/KeyError/RuntimeError dönüşümü (DDD servis katmanı ihlali).
- `backend/app/domains/coverup/router.py`: try/except ValueError→400, KeyError→404 sarmalayıcıları eklendi.

**Engine — Son route testleri (Wave 9)**
- `engine/tests/unit/test_visual_routes.py` — 18 test; baseline CRUD, karşılaştırma, raporlar, config.
- `engine/tests/unit/test_llm_agent_routes.py` — 15 test; start/act/snapshot/close, session yönetimi.

### Added — Engine route testleri Wave 5/6 + Backend servisleri (2026-05-26, Tur 6)

**Engine — Route testleri (Wave 5)**
- `engine/tests/unit/test_ai_analysis_routes.py` — 28 test; anomaly detection, flaky report, coverage gaps, prioritize, stats, assertions, security scan. Feature-flag 503 path + exception 500 path kapsamlı.
- `engine/tests/unit/test_ai_healing_routes.py` — 16 test; self-heal (LLM unavailable 503, broken selector), find-element, healing-log (dosya var/yok senaryoları).
- `engine/tests/unit/test_ai_generation_routes.py` — 22 test; generate-test + generate-bdd (feature disabled 503, LLM unavailable 503, missing requirement 400, success).
- `engine/tests/unit/test_banking_routes.py` — 23 test; BANKING_AVAILABLE guard, tc-kimlik, IBAN, kart, EFT, graceful degradation.
- `engine/tests/unit/test_datasim_routes.py` — 17 test; dataset katalog listesi, generate (bilinmeyen id 404), CSV/JSON export.
- `engine/tests/unit/test_accessibility_routes.py` — 15 test; WCAG testi, rapor al/listele, config CRUD.
- `engine/tests/unit/test_playback_routes.py` — 15 test; replay (path yok 404, session_path eksik 400, başarı), session listesi.
- `engine/tests/unit/test_registry_routes.py` — 19 test; locator registry CRUD, screen filtresi, sync, stats.
- `engine/tests/unit/test_tm_routes.py` — 42 test; test management tam kapsama: proje/modül/test case/adım/sprint/run/bug/rapor.
- `backend/tests/integration/test_domain_endpoints.py` — 12 test; yeni domain endpoint'leri ≠ 500 doğrulaması.

**Engine — Route testleri (Wave 6)**
- `engine/tests/unit/test_ai_routes.py` — 22 test; generate-feature (BDDGenerator + AIEngine fallback), analyze-api-request, security-scan.
- `engine/tests/unit/test_ai_intelligence_routes.py` — 24 test; generate-locators, audit-locators, map-steps, feedback-insights, quality-score, security-analyze, perf-analyze, optimize-suite.
- `engine/tests/unit/test_manual_routes.py` — 23 test; manuel test CRUD + adım yönetimi tam kapsama.
- `engine/tests/unit/test_editor_routes.py` — 26 test; dosya ağacı, okuma/yazma, path traversal guard, komut allowlist.
- `engine/tests/unit/test_device_manager_routes.py` — 29 test; cihaz listesi (demo), ekran görüntüsü, uygulama yükleme/kaldırma, sağlık skoru.
- `engine/tests/unit/test_datasim_banking_routes.py` — 31 test; bankacılık veri simülasyonu tam kapsama.
- `engine/tests/unit/test_mobile_routes.py` — 20 test; cihaz katalogu, farm durumu, test koşumu, APK yükleme.

**Backend — Yeni unit testleri (Wave 6)**
- `backend/tests/unit/test_llm_gateway.py` — 29 test; PII maskeleme, model routing, circuit breaker, maliyet tahmini, HTTP retry.
- `backend/tests/unit/test_feature_flags_service.py` — 12 test; P1 #41 tamamlandı — list/get/enable/disable/update, fail-closed guard.

**Frontend**
- `apps/web/lib/useCustomDashboard.ts`: Backend-first load eklendi — localStorage anlık yükleme + `/api/v1/dashboards` async override, offline sync korundu.

### Added — Engine route testleri + Backend domain testleri Wave 3/4 (2026-05-26, Tur 5)

**Engine — Route testleri (Wave 3 tamamlandı)**
- `engine/tests/unit/test_analytics_routes.py` — 30 test; 8 test class, analytics/reporting blueprint tümü kapsandı.
- `engine/tests/unit/test_reporting_routes.py` — 28 test; raporlama endpoint'leri (PDF/HTML/JSON export).
- `engine/tests/unit/test_scheduler_routes.py` — 22 test; APScheduler CRUD, JSON file store, schedule list/add/delete.

**Backend — Wave 3 domain unit testleri**
- `backend/tests/unit/test_defects_service.py` — 13 test; state machine (open→awaiting_fix→verifying→closed), rejected path, jira_webhook_ingest, ADF flattening.
- `backend/tests/unit/test_ingestion_service.py` — 11 test; ingest_text, get_requirement, list_requirements, jira_webhook_ingest.
- `backend/tests/unit/test_knowledge_base_service.py` — 20 test; PermissionError non-author, admin bypass, sort/filter, view count, voting.
- `backend/tests/unit/test_compliance_service.py` — 12 test; get_coverage_summary, list_controls standard filter, get_control, mappings_for.
- `backend/tests/unit/test_visual_service.py` — 10 test; start_comparison compare_png mock, get_result, list_results.
- `backend/tests/unit/test_marketplace_service.py` — 13 test; list_items, get_item, install_item.

**Engine — Route testleri (Wave 4)**
- `engine/tests/unit/test_feature_routes.py` — 20 test; feature file CRUD, glue content generation.
- `engine/tests/unit/test_jira_routes.py` — 18 test; config CRUD, bug push, project list, testcase link.
- `engine/tests/unit/test_lifecycle_routes.py` — 12 test; process-analyst endpoint, AI mock, save flow.
- `engine/tests/unit/test_locators_routes.py` — 15 test; DB/JSON kaynak, save/delete, discover URL normalizasyonu.
- `engine/tests/unit/test_monkey_routes.py` — 18 test; SSE dışı endpoint'ler, start/stop/status/report.
- `engine/tests/unit/test_project_routes.py` — 20 test; CRUD, set-active, scaffold stub.
- `engine/tests/unit/test_regression_routes.py` — 15 test; regression set CRUD, feature add/remove.
- `engine/tests/unit/test_runner_routes.py` — 25 test; enqueue, SSE stream mock, cancel, status.
- `engine/tests/unit/test_visual_ai_routes.py` — 15 test; compare, heal, AI analysis mock.
- `engine/tests/unit/test_webhook_routes.py` — 12 test; GitHub/Jira webhook handlers, HMAC validation.

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
