# Docs Index — Neurex QA Platform

**Son güncelleme:** 2026-05-26  
**Kapsam:** `docs/` dizinindeki tüm dokümantasyon  

> Bu dosya `docs/` içeriğinin haritası. Yeni bir doküman eklendiğinde bu dosyayı da güncelleyin.

---

## Son Güncellemeler (2026-05-26)

Wave 11/12 kapsamında eklenen yeni belgeler:

| Dosya | Konu | Tarih |
|---|---|---|
| [adr/ADR-0011-service-layer-ddd-pattern.md](./adr/ADR-0011-service-layer-ddd-pattern.md) | DDD servis katmanı kararı (Wave 11) | 2026-05-26 |
| [testing-runbook.md](./testing-runbook.md) | Backend/engine/frontend test koşumu rehberi (Wave 11) | 2026-05-26 |
| [backend-domain-coverage.md](./backend-domain-coverage.md) | 48 domain coverage matrisi (Wave 11) | 2026-05-26 |
| [semgrep-secrets-runbook.md](./semgrep-secrets-runbook.md) | Semgrep secrets tarama runbook'u (Wave 11) | 2026-05-26 |

---

## Mimari Kararlar (ADR)

> Tüm aktif ADR'lar → [`docs/adr/`](./adr/README.md)

| # | Başlık | Durum |
|---|---|---|
| [0001](./adr/0001-monorepo-yapisi.md) | Monorepo yapısı (Turborepo) | ✅ Kabul |
| [0002](./adr/0002-engine-vs-backend-ayirimi.md) | Engine (Flask) ↔ Backend (FastAPI) ayrımı | ✅ Kabul |
| [0003](./adr/0003-synthetic-data-konsolidasyonu.md) | Synthetic-data v4 ana platform | ✅ Kabul |
| [0004](./adr/0004-legacy-silme-politikasi.md) | Legacy silme politikası (6 ay) | ✅ Kabul |
| [0005](./adr/0005-test-taksonomisi.md) | Test katmanları ve konumları | ✅ Kabul |
| [0006](./adr/0006-playwright-cucumber-framework-rolü.md) | Playwright-Cucumber framework rolü | ✅ Kabul |
| [ADR-0011](./adr/ADR-0011-service-layer-ddd-pattern.md) | Servis katmanı DDD pattern kararı | ✅ Kabul |

---

## Mimari Belgeler

| Dosya | İçerik |
|---|---|
| [architecture/engine-backend-contract.md](./architecture/engine-backend-contract.md) | Flask engine ↔ FastAPI backend HTTP kontratı |
| [architecture/synthetic-data-gap-analysis.md](./architecture/synthetic-data-gap-analysis.md) | Platform-v4 → backend özellik karşılaştırması |
| [ARCHITECTURE_PLAN.md](./ARCHITECTURE_PLAN.md) | Genel mimari plan (ilk taslak) |
| [architecture.md](./architecture.md) | Sistem bileşenleri ve katman açıklaması |
| [ADR-001-backend-engine-separation.md](./ADR-001-backend-engine-separation.md) | Engine/backend ayrımı — eski format (adr/0002 ile örtüşür) |

---

## Vizyon ve Yol Haritası

| Dosya | Ufuk | Durum |
|---|---|---|
| [vision/PLAN-FRONTIER-2030.md](./vision/PLAN-FRONTIER-2030.md) | 2030 ufku | 📋 Vizyon belgesi |
| [vision/PLAN-BEYOND-2035.md](./vision/PLAN-BEYOND-2035.md) | 2035+ ufku | 📋 Vizyon belgesi |
| [vision/PLAN-ULTIMATE-10.md](./vision/PLAN-ULTIMATE-10.md) | 10 yıllık hedef | 📋 Vizyon belgesi |
| [ai-test-roadmap.md](./ai-test-roadmap.md) | AI test otomasyon yol haritası | 📋 Aktif |
| [NEUREX_FARM_10_10_GELISTIRME_PLANI.md](./NEUREX_FARM_10_10_GELISTIRME_PLANI.md) | Neurex Farm 10/10 geliştirme planı | 📋 Aktif |

---

## Çalışma Rehberleri (Runbooks)

| Dosya | Konu |
|---|---|
| [jenkins-setup.md](./jenkins-setup.md) | Jenkins credential kurulumu |
| [jenkins-rollback-runbook.md](./jenkins-rollback-runbook.md) | Jenkins rollback prosedürü |
| [ai-workflow-incident-runbook.md](./ai-workflow-incident-runbook.md) | AI workflow olay müdahale |
| [ai-workflow-release-signoff.md](./ai-workflow-release-signoff.md) | AI workflow release onay süreci |
| [runtime-hardening-checklist.md](./runtime-hardening-checklist.md) | Runtime güvenlik kontrol listesi |
| [REBRAND_DEPLOY_CHECKLIST.md](./REBRAND_DEPLOY_CHECKLIST.md) | Rebrand deploy kontrol listesi |
| [testing-runbook.md](./testing-runbook.md) | Backend/engine/frontend test koşumu rehberi |
| [semgrep-secrets-runbook.md](./semgrep-secrets-runbook.md) | Semgrep secrets tarama runbook'u |

---

## Geliştirici Rehberleri

| Dosya | Konu |
|---|---|
| [test-platform-guide.md](./test-platform-guide.md) | Test platform kullanım kılavuzu |
| [test-platform-index.md](./test-platform-index.md) | Test platform bileşenleri indeksi |
| [locator-strategy.md](./locator-strategy.md) | Locator stratejisi (Playwright/Selenium) |
| [local-login-setup.md](./local-login-setup.md) | Lokal login kurulumu |
| [BRANCHING_WORKFLOW.md](./BRANCHING_WORKFLOW.md) | Git branch ve PR iş akışı |
| [dependency-governance.md](./dependency-governance.md) | Bağımlılık yönetim politikası |
| [web-route-onboarding.md](./web-route-onboarding.md) | Web route ekleme rehberi |
| [backend-domain-coverage.md](./backend-domain-coverage.md) | 48 domain coverage matrisi |

---

## AI / LLM Belgeleri

| Dosya | Konu |
|---|---|
| [ai-test-architecture.md](./ai-test-architecture.md) | AI test otomasyon mimarisi |
| [ai-test-best-practices.md](./ai-test-best-practices.md) | AI test en iyi pratikler |
| [ai-test-automation-research.md](./ai-test-automation-research.md) | AI test otomasyon araştırması |
| [ai-test-code-examples.md](./ai-test-code-examples.md) | Kod örnekleri |
| [ai-test-project-structure.md](./ai-test-project-structure.md) | Proje yapısı önerisi |
| [ai-test-tools-comparison.md](./ai-test-tools-comparison.md) | Araç karşılaştırması |
| [ai-ops-stack.md](./ai-ops-stack.md) | AI ops altyapı stack'i |
| [llm-agent-model-recommendations.md](./llm-agent-model-recommendations.md) | LLM model önerileri |
| [llm-rule-sets.md](./llm-rule-sets.md) | LLM kural setleri |
| [llm-akilli-kurulum.md](./llm-akilli-kurulum.md) | Akıllı LLM kurulum rehberi |
| [AI_OTOMASYON_GELISTIRME_PLANI.md](./AI_OTOMASYON_GELISTIRME_PLANI.md) | AI otomasyon geliştirme planı |
| [AI_TEST_OTOMASYON_RAPORU.md](./AI_TEST_OTOMASYON_RAPORU.md) | AI test otomasyon raporu |
| [AI_Test_Automation_Research_Report.md](./AI_Test_Automation_Research_Report.md) | Detaylı araştırma raporu |

---

## Ürün ve UX Belgeleri

| Dosya | Konu |
|---|---|
| [product.md](./product.md) | Ürün genel tanımı |
| [akis-bazli-kullanim-tasarimi.md](./akis-bazli-kullanim-tasarimi.md) | Akış bazlı kullanım tasarımı |
| [kullanim-kurgulari-sunumu.md](./kullanim-kurgulari-sunumu.md) | Kullanım kurguları sunumu |
| [persona-akis-hibridi.md](./persona-akis-hibridi.md) | Persona + akış hibrit tasarımı |
| [demo-30-gun-plani.md](./demo-30-gun-plani.md) | Demo 30 gün planı |
| [sprint-11-ux-iyilestirme-plani.md](./sprint-11-ux-iyilestirme-plani.md) | Sprint 11 UX iyileştirme planı |
| [visium-urun-agaci-ve-menu-mimarisi.md](./visium-urun-agaci-ve-menu-mimarisi.md) | Ürün ağacı ve menü mimarisi |
| [visium-urun-ailesi-arastirma.md](./visium-urun-ailesi-arastirma.md) | Ürün ailesi araştırması |
| [visium-domain-ayristirma-plani.md](./visium-domain-ayristirma-plani.md) | Domain ayrıştırma planı |
| [visium-10-10-ux-refactor-plani.md](./visium-10-10-ux-refactor-plani.md) | UX refactor planı |
| [smart-step-builder-plan.md](./smart-step-builder-plan.md) | Smart Step Builder tasarımı |

---

## Konsolidasyon ve Geçiş Belgeleri

| Dosya | Konu |
|---|---|
| [REPO_CONSOLIDATION_PLAN.md](./REPO_CONSOLIDATION_PLAN.md) | Repo konsolidasyon planı |
| [MERGE_PLAN_ALL_PROJECTS.md](./MERGE_PLAN_ALL_PROJECTS.md) | Tüm proje merge planı |
| [MERGE_ANALYSIS.md](./MERGE_ANALYSIS.md) | Merge analizi |
| [dsl-consolidation-plan.md](./dsl-consolidation-plan.md) | DSL konsolidasyon planı |
| [synthetic-data-research.md](./synthetic-data-research.md) | Synthetic data araştırması |
| [MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md](./MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md) | Mobil otomasyon araştırma raporu |

---

## Raporlar (Anlık / Arşiv)

| Dosya | İçerik |
|---|---|
| [AGENTS_V2_PROGRESS_REPORT.md](./AGENTS_V2_PROGRESS_REPORT.md) | Agents v2 ilerleme raporu |
| [AGENT_ACTIVE_WORK.md](./AGENT_ACTIVE_WORK.md) | Aktif agent çalışmaları |
| [MASTER.md](./MASTER.md) | Master plan belgesi |
| [validation-report.md](./validation-report.md) | Validasyon raporu |
| [repository-inventory.md](./repository-inventory.md) | Repo envanter belgesi |
| [gaps-backlog-template.md](./gaps-backlog-template.md) | Eksiklik backlog şablonu |

---

## Yeni Belge Eklerken

1. İlgili kategoriye bu INDEX dosyasına bir satır ekle.
2. Belge adını `küçük-harf-tire.md` formatında tut.
3. ADR ise `docs/adr/NNNN-başlık.md` formatını kullan ve ADR README'yi güncelle.
4. Vizyon/roadmap belgesi ise `docs/vision/` altına koy.
