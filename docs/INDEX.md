# Cortex AI Automation — Docs Index

> **Kanonik kaynak.** Yeni bir dokümana link vermeden önce bu dosyayı güncelle.
> Son güncelleme: 2026-05-24 · Branch: `feature/qa-system-bootstrap`

---

## Hızlı Başlangıç

| Amaç | Doküman |
|---|---|
| Projeyi ilk kez kurmak | [`../README.md`](../README.md) |
| GitHub Actions secret'ları | [`setup/github-secrets.md`](setup/github-secrets.md) |
| Jenkins pipeline kurulumu | [`jenkins-setup.md`](jenkins-setup.md) |
| Yerel geliştirme ortamı | [`local-login-setup.md`](local-login-setup.md) |
| Servis mimarisine genel bakış | [`architecture.md`](architecture.md) |

---

## Mimari

| Doküman | İçerik |
|---|---|
| [`architecture.md`](architecture.md) | Genel mimari özeti |
| [`architecture/services.md`](architecture/services.md) | Servis katmanları ve sorumlulukları |
| [`architecture/engine-backend-contract.md`](architecture/engine-backend-contract.md) | Engine ↔ Backend API sözleşmesi |
| [`architecture/synthetic-data-gap-analysis.md`](architecture/synthetic-data-gap-analysis.md) | Planlanan endpoint'ler (⚠️ demo data) |
| [`adr/README.md`](adr/README.md) | Architecture Decision Records dizini |
| [`ai-test-architecture.md`](ai-test-architecture.md) | AI test mimari rehberi |

---

## Geliştirici Kılavuzları

| Doküman | İçerik |
|---|---|
| [`test-platform-guide.md`](test-platform-guide.md) | Test platformu kullanım rehberi |
| [`test-platform-index.md`](test-platform-index.md) | Test platform bileşen dizini |
| [`locator-strategy.md`](locator-strategy.md) | Selector / locator stratejisi |
| [`dependency-governance.md`](dependency-governance.md) | Bağımlılık yönetim politikası |
| [`runtime-hardening-checklist.md`](runtime-hardening-checklist.md) | Üretim sertleştirme kontrol listesi |
| [`web-route-onboarding.md`](web-route-onboarding.md) | Frontend yeni route ekleme rehberi |
| [`llm-rule-sets.md`](llm-rule-sets.md) | LLM prompt / kural setleri |

---

## CI / Ops

| Doküman | İçerik |
|---|---|
| [`jenkins-setup.md`](jenkins-setup.md) | Jenkins pipeline kurulumu ve kimlik bilgileri |
| [`jenkins-rollback-runbook.md`](jenkins-rollback-runbook.md) | Rollback prosedürü |
| [`setup/github-secrets.md`](setup/github-secrets.md) | GitHub Actions secret referansı |
| [`ai-workflow-incident-runbook.md`](ai-workflow-incident-runbook.md) | AI workflow olay müdahale |
| [`ai-workflow-release-signoff.md`](ai-workflow-release-signoff.md) | Sürüm onay kontrol listesi |
| [`BRANCHING_WORKFLOW.md`](BRANCHING_WORKFLOW.md) | Git branch stratejisi |

---

## Ürün & Planlama

| Doküman | İçerik |
|---|---|
| [`product.md`](product.md) | Ürün genel bakışı |
| [`nexus-ai/README.md`](nexus-ai/README.md) | Nexus AI modül dizini |
| [`nexus-ai/02-prd.md`](nexus-ai/02-prd.md) | Ürün gereksinimleri |
| [`nexus-ai/05-delivery-plan.md`](nexus-ai/05-delivery-plan.md) | Teslimat planı |
| [`nexus-ai/06-backlog.md`](nexus-ai/06-backlog.md) | Backlog |
| [`planning/END_USER_GAPS_REPORT.md`](planning/END_USER_GAPS_REPORT.md) | Son kullanıcı eksiklik raporu |
| [`planning/END_USER_GAPS_PLAN.md`](planning/END_USER_GAPS_PLAN.md) | Eksiklik giderme planı |

---

## Araştırma & Referans

| Doküman | İçerik |
|---|---|
| [`ai-ops-stack.md`](ai-ops-stack.md) | AI ops teknoloji yığını |
| [`ai-test-best-practices.md`](ai-test-best-practices.md) | AI test en iyi uygulamalar |
| [`ai-test-code-examples.md`](ai-test-code-examples.md) | AI test kod örnekleri |
| [`ai-test-tools-comparison.md`](ai-test-tools-comparison.md) | AI test araç karşılaştırması |
| [`llm-agent-model-recommendations.md`](llm-agent-model-recommendations.md) | Model önerileri |
| [`synthetic-data-research.md`](synthetic-data-research.md) | Sentetik veri araştırması |

---

## Cursor Prompts (Agent Görevleri)

| Doküman | İçerik |
|---|---|
| [`cursor-prompts/README.md`](cursor-prompts/README.md) | Agent görev dizini |
| `agent-01` → `agent-10` | Sıralı refactoring görevleri |
| `design-01` → `design-07` | UI/UX iyileştirme görevleri |

---

## Vizyon & Roadmap

> **Yapılacaklar listesi değil** — stratejik referans belgelerdir. Aktif sprint çalışması için Planlama bölümünü kullan.

| Doküman | İçerik |
|---|---|
| [`vision/README.md`](vision/README.md) | Vizyon dizini |
| [`vision/PLAN-FRONTIER-2030.md`](vision/PLAN-FRONTIER-2030.md) | 2030 vizyonu |
| [`vision/PLAN-BEYOND-2035.md`](vision/PLAN-BEYOND-2035.md) | 2035+ uzun vade |

---

## Arşiv & Tarihsel

Aktif geliştirme için **kullanılmaz** — yalnızca tarihsel referans amaçlıdır.

| Konum | İçerik |
|---|---|
| [`history/`](history/) | Eski proje yönetimi dökümanları |
| [`project-history/`](project-history/) | Haftalık sprint özetleri (H7–H12) |
| [`adr/archive/2026-04-tr/`](adr/archive/2026-04-tr/) | Arşivlenmiş Türkçe ADR'ler |
| [`adr/archive/ADR-001-backend-engine-separation.md`](adr/archive/ADR-001-backend-engine-separation.md) | ~~ADR-001~~ → `adr/0005-engine-consolidation.md` ile supersede edildi |

---

## Bakım Notları

- Bu dosya `docs/` altına eklenen her yeni dokümanda güncellenmelidir.
- Yinelenen veya eski dokümanlar `docs/history/` veya `docs/adr/archive/` altına taşınmalıdır.
- "Kanonik kaynak değil" olarak işaretlenen dosyalara doğrudan link verilmemelidir.
