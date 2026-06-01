# Backend Domain Coverage Summary

**Güncelleme:** 2026-05-26  
**Toplam Domain Sayısı:** 48  
**Kaynak:** `backend/app/domains/` + `backend/tests/unit/`

## Kapsam Tablosu

| Domain | Service | Router | Tests | Coverage Notları |
|---|---|---|---|---|
| a11y | ✅ | ✅ | ✅ | `test_a11y_service.py` mevcut |
| accessibility | ✅ | ✅ | ✅ | `test_accessibility_service.py` + `test_accessibility_router.py` + `test_accessibility_analyzer.py` |
| agents | ✅ | ✅ | ✅ | `test_agents_service.py` mevcut |
| ai | ✅ | ✅ | ✅ | `test_ai_service.py` + helpers mevcut |
| ai_synthetic_data | ✅ | ✅ | ✅ | `test_ai_synthetic_data_service.py` mevcut |
| api_testing | ✅ | ✅ | ✅ | `test_api_testing_service.py` + feedback helpers |
| artifacts | ✅ | ✅ | ✅ | `test_artifacts_service.py` mevcut |
| audit | ✅ | ✅ | ✅ | `test_audit_service.py` + export + chain testleri |
| auth | ✅ | ✅ | ✅ | `test_auth_service.py` + `test_mfa_auth_flow.py` + `test_mfa_service.py` |
| automation | ✅ | ✅ | ✅ | `test_automation_service.py` mevcut |
| automation_suite | ✅ | ✅ | ✅ | `test_automation_suite_service.py` mevcut |
| automation_templates | ✅ | — | ✅ | `service.py` tamamlandı (Wave 12); router gerekmez |
| billing | ✅ | ✅ | ✅ | `test_billing_service.py` + `test_pricing.py` + `test_budget.py` |
| catalog | ✅ | ✅ | ✅ | `test_catalog_service.py` mevcut |
| cicd | ✅ | ✅ | ✅ | `test_cicd_service.py` + jenkins/crypto/quality gate/TIA testleri |
| compliance | ✅ | ✅ | ✅ | `test_compliance_service.py` + `test_compliance_mapping.py` (extended dahil) |
| cost | ✅ | ✅ | ✅ | `test_cost_service.py` + `test_cost_estimator.py` |
| coverup | ✅ | ✅ | ✅ | `test_coverup_service.py` + `test_coverup_parsers.py` |
| defects | ✅ | ✅ | ✅ | `test_defects_service.py` mevcut |
| dsl | ✅ | ✅ | ✅ | `test_dsl_service.py` + editor/grounding/reranker/yaml writer testleri |
| email | ✅ | ✅ | ✅ | `service.py` + `router.py` tamamlandı (Wave 12); `test_email_service.py` mevcut |
| evals | ✅ | ✅ | ✅ | `test_evals_service.py` + `test_evals_reporting_helpers.py` + visual helpers |
| events | ✅ | ✅ | ✅ | `test_events_service.py` mevcut |
| feature_flags | ✅ | ✅ | ✅ | `test_feature_flags_service.py` + `test_feature_flags.py` |
| git_fetch | ✅ | ✅ | ✅ | `test_git_fetch_service.py` mevcut |
| health | ✅ | ✅ | ✅ | `test_health_service.py` + `test_extended_health.py` |
| ingestion | ✅ | ✅ | ✅ | `test_ingestion_service.py` mevcut |
| jobs | ✅ | ✅ | ✅ | `test_jobs_service.py` mevcut |
| knowledge_base | ✅ | ✅ | ✅ | `test_knowledge_base_service.py` + gateway/runner/knowledge helpers |
| marketplace | ✅ | ✅ | ✅ | `test_marketplace_service.py` + `test_marketplace_templates.py` |
| migration | ✅ | — | ✅ | `service.py` tamamlandı (Wave 12); router gerekmez — `test_migration_assistant.py` mevcut |
| mobile | ✅ | ✅ | ✅ | `test_mobile_service.py` + `test_device_farm_adapters.py` + network/mobile helpers |
| n8n | ✅ | ✅ | ✅ | `test_n8n_service.py` mevcut |
| navigation | ✅ | ✅ | ✅ | `service.py` + `router.py` tamamlandı (Wave 12); `test_navigation_service.py` mevcut |
| nexus_repo | ✅ | ✅ | ✅ | `test_nexus_repo_service.py` + `test_nexus_exporter_helpers.py` |
| notifications | ✅ | ✅ | ✅ | `test_notifications_service.py` mevcut |
| onboarding | ✅ | ✅ | ✅ | `test_onboarding_service.py` + `test_onboarding.py` |
| pilot | ✅ | ✅ | ✅ | `test_pilot_service.py` mevcut |
| playwright_mcp | ✅ | ✅ | ✅ | `test_playwright_mcp_service.py` mevcut |
| pr_bot | ✅ | ✅ | ✅ | `service.py` + `router.py` tamamlandı (Wave 12); `test_pr_bot_service.py` + `test_pr_bot.py` mevcut |
| privacy | ✅ | ✅ | ✅ | `test_privacy_service.py` + `test_privacy_scanner.py` + `test_pii_redactor.py` + workflow helpers |
| products | ✅ | ✅ | ✅ | `test_products_service.py` mevcut |
| prompts | ✅ | ✅ | ✅ | `test_prompts_service.py` + `test_prompts.py` + `test_prompt_registry.py` + `test_prompt_shield.py` |
| quality | ✅ | ✅ | ✅ | `test_quality_service.py` + `test_quality_metrics.py` |
| rbac | ✅ | ✅ | ✅ | `service.py` + `router.py` tamamlandı (Wave 12); `test_rbac_service.py` mevcut |
| rules | ✅ | ✅ | ✅ | `test_rules_service.py` mevcut |
| tspm | ✅ | ✅ | ✅ | `test_tspm_service.py` + db schema/reporting/scheduler/xpath/test case helpers |
| visual | ✅ | ✅ | ✅ | `test_visual_service.py` + `test_visual_compare.py` + eval helpers |

## Özet

| Durum | Sayı |
|---|---|
| Tam kapsamlı (service + router + test) | 46 |
| Service + test var, router gerekmez | 2 (automation_templates, migration) |
| **Toplam** | **48** |

> Wave 12 tamamlandı — tüm 6 eksik domain (rbac, email, pr_bot, navigation, automation_templates, migration) servis ve testleriyle teslim edildi.
