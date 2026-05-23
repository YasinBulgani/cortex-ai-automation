# PR 34 — engine/features/api/ → backend/tests/bdd/features/api/ Migration Planı

**Durum:** Plan onayı bekliyor (engineering team sahipliği).
**Tahmini süre:** 1-2 sprint.

## Kapsam

`engine/features/api/` altındaki **16 .feature dosyası, 713 satır** backend katmanına (pytest-bdd) taşınacak.

| Dosya | Hedef | TC eşleşme adayı |
|---|---|---|
| `analytics.feature` | `backend/tests/bdd/features/analytics.feature` | TC-EXC-004 (trends) |
| `api_tests.feature` | `backend/tests/bdd/features/api_tests.feature` | TC-API-001..004 |
| `approvals.feature` | `backend/tests/bdd/features/approvals.feature` | TC-APR-001..005 |
| `auth.feature` | **MERGE** `backend/tests/bdd/features/authentication.feature` | TC-AUTH-001..008 |
| `bdd_generation.feature` | `backend/tests/bdd/features/bdd_generation.feature` | TC-SCN-005, 006 (AI generation) |
| `dashboard.feature` | `backend/tests/bdd/features/dashboard.feature` | TC-PRJ-003 (dashboard) |
| `executions.feature` | `backend/tests/bdd/features/executions.feature` | TC-EXC-001..005, TC-RUN-001..002 |
| `flows.feature` | `backend/tests/bdd/features/flows.feature` | TC-FLW-001, 002 |
| `integrations.feature` | `backend/tests/bdd/features/integrations.feature` | TC-INT-001, 002 |
| `members.feature` | `backend/tests/bdd/features/members.feature` | TC-PRJ-005, 006 |
| `projects.feature` | **MERGE** `backend/tests/bdd/features/project_management.feature` | TC-PRJ-001..006 |
| `regression.feature` | `backend/tests/bdd/features/regression.feature` | TC-REG-001..004 |
| `requirements_coverage.feature` | `backend/tests/bdd/features/requirements_coverage.feature` | TC-REQ-001..004 |
| `scenarios.feature` | **MERGE** `backend/tests/bdd/features/scenario_management.feature` | TC-SCN-001..009 |
| `schedules.feature` | `backend/tests/bdd/features/schedules.feature` | TC-SCH-001..003 |
| `test_data.feature` | `backend/tests/bdd/features/test_data.feature` | TC-SYN-005, 006 |

## Aşamalı plan (3 aşama)

### Aşama 1 — Step defs envanteri (engineering team, 1 gün)

```bash
# engine/steps/'taki hangi dosya hangi feature'a referans?
grep -rn "@given\|@when\|@then" engine/steps/ | wc -l  # toplam step def
# Pattern matching: feature dosya isminden step file isim çıkar
```

Çıktı: `engine/steps/`'in 40 dosyasının hangisinin hangi feature'a bağlı olduğu matris.

### Aşama 2 — Kopyala + tag ekle (3 ayrı PR, her biri 2-4 saat)

**Mutually exclusive group'lar** (paralel yapılabilir):
- Group A: auth + projects + scenarios (MERGE'ler) — riskli, dikkatli
- Group B: approvals + executions + flows + members — standart
- Group C: analytics + dashboard + integrations + schedules + test_data + regression + requirements_coverage + api_tests + bdd_generation — kalanlar

Her PR'da:
1. Feature dosyasını backend/tests/bdd/features/'a `cp` (engine/'de bırak)
2. `@TC-*` tag'lerini ekle (qa/cases/ ile eşleştir)
3. Backend step defs yaz (mevcut engine/steps/ pattern'ini referans al)
4. backend/pytest.ini'de bdd_features_base_dir varsa güncelle
5. `pytest backend/tests/bdd/` çalıştır → yeşil olmalı
6. `node qa/tools/trace.mjs` çalıştır → coverage güncel

### Aşama 3 — engine cleanup (engineering team, 1 gün)

Aşama 2 tamamlandıktan **sonra**:
1. `engine/steps/` kullanılmayan step defs sil
2. `engine/features/api/` klasörünü sil (`git rm -rf`)
3. `engine/pytest.ini`'den `bdd_features_base_dir = features/` kaldır
4. `engine/features/DEPRECATED.md` güncelle (api/ tamamlandı)
5. engine pytest suite yeşil mi tam regression çalıştır

## Risk azaltma

| Risk | Mitigation |
|---|---|
| Step defs runtime hatası | Aşama 2'de feature `cp` (orijinal bırak) — paralel yaşar |
| Pytest config çakışması | backend/pytest.ini'de ayrı `bdd_features_base_dir` |
| Test data bağımlılığı | conftest.py'leri portla; fixture'lar paylaşılan |
| BDD step naming farkı | TR/EN tutarlılığı: backend EN, engine TR — `# language:` directive |
| Aşama 2 ortasında ekip diğer feature ekler | engine/features/api/'a freeze tag (CODEOWNERS readonly) |

## Coverage etkisi (tahmin)

Şu an: 28/77 = 36% automation
PR 34 sonrası: ~50/77 = 65% (yeni BDD scenario'ların tag'lendiği TC'ler)

## CI gate

Aşama 2 her PR'da:
```yaml
- name: Backend BDD regression
  run: cd backend && pytest tests/bdd/ -v
```

## Sahip

- Aşama 1: Backend team (envanter)
- Aşama 2: Backend + QA (her PR çift sahip)
- Aşama 3: Backend team (cleanup)

QA sahipliği: `@qa-leads` her PR'da review (label: `qa-migration`).
