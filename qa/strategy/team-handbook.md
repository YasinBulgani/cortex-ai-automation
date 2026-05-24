# QA Team Handbook — Cortex AI Automation

> **Bu doküman 1 saatte okunup tamamen anlaşılabilir tasarlandı.** Yeni QA ekip üyesi için onboarding rehberi.

---

## 1. Felsefe — 5 dakika

Cortex AI Automation'ın test sistemi **git-native**: SaaS test management aracı (TestRail/Xray/Qase) kullanmıyoruz. Test artifact'leri (case, plan, run, defect) `qa/` klasöründe markdown + YAML olarak yaşıyor.

**Niye git-native?**
1. PR review = test review (4 göz prensibi otomatik)
2. Tüm değişiklik history'de (audit log bedavaya)
3. Test ve kod aynı PR'da → tutarlılık garanti
4. Cortex AI dogfood — kendi ürünümüz ile test ediyoruz
5. Sıfır lisans + sıfır vendor lock-in

**Tradeoff**: glossy UI yerine CLI/editor + statik HTML dashboard. Eğer real-time UI kritikse `apps/web/qa-dashboard` Next.js sayfası ileride planda var.

---

## 2. Kurulum — 5 dakika

```bash
# 1. Repo clone (zaten yaptın)
git clone ... && cd Cortex_Ai_Automation

# 2. qa/ tooling
cd qa && npm install && cd ..

# 3. Pre-commit hook'lar (opsiyonel ama önerilen)
pip install pre-commit && pre-commit install

# 4. (AI özellikleri için) Provider key
export CORTEX_AI_GATEWAY_URL="..."   # tercih edilen
# veya ANTHROPIC_API_KEY, OPENAI_API_KEY
```

Detay: [INSTALL.md](../INSTALL.md)

---

## 3. Mental model — 10 dakika

### 4 anahtar kavram

| Kavram | Konum | Ne işe yarar |
|---|---|---|
| **Test Case (TC)** | `qa/cases/{suite}/TC-*.md` | "Bu adımları yaparsan bu sonucu görmelisin" kontratı |
| **Test Plan (TP)** | `qa/plans/*.yml` | "Bu release'de hangi TC'leri çalıştırırız" seçimi |
| **Test Run (TR)** | `qa/runs/YYYY/MM/TR-*.yml` | "Bu sefer ne oldu" — immutable koşum kaydı |
| **Requirement (REQ)** | `qa/requirements/REQ-*.md` | "Hangi davranışı garanti ediyoruz" — TC'lerin var olma sebebi |

### Zincirin akışı

```
Requirement (REQ-AUTH-001 "JWT login")
    ↓ covered_by
Test Case (TC-AUTH-001 "Başarılı login")
    ↓ automation.refs
BDD Scenario (e2e/bdd/features/auth/login.feature:6 @TC-AUTH-001)
    ↓ koşum
Test Run (TR-2026-05-23-SMOKE-001.yml → result: pass)
    ↓ fail varsa
Defect (GH-1234, qa/defects/GH-1234.md mirror)
```

Her halka **kod ile** bağlı, manuel kopyala-yapıştır yok.

### Suite vs Domain

- **Suite** = klasör adı: `auth`, `projects`, `scenarios`, …
- **Domain** = TC ID prefix: `AUTH`, `PRJ`, `SCN`, …
- 1-1 eşleşme: `qa/cases/auth/` → `AUTH` domain
- 33 domain tanımlı (`qa/CONVENTIONS.md`)

---

## 4. Günlük workflow — 15 dakika

### Yeni TC yazmak

```bash
cd qa
npm run new-tc -- --suite=auth --title="MFA fallback akışı"
# → qa/cases/auth/TC-AUTH-019-mfa-fallback-akisi.md
```

Editöründe aç, adımları doldur. **3 önemli kural**:

1. **Bir TC = bir doğrulama amacı.** "Login + profile update + logout" → 3 ayrı TC.
2. **Adımlar deterministic olmalı.** "Login ol" yetmez; "POST /auth/login → 200 + JWT" gerek.
3. **Beklenen sonuç spesifik olmalı.** "Çalışır" yetmez; "HTTP 200, response.email = 'test@example.com'" gerek.

### TC'yi commit etmeden önce

```bash
npm run validate    # Schema + ID + ref doğrulama
npm run trace       # coverage/* güncelle
```

Pre-commit hook bunu otomatik yapıyor ama lokal hızlı feedback için yararlı.

### Manuel koşum kaydetmek

```bash
npm run run-record -- --plan=smoke-daily
```

Interaktif TUI:
1. Her TC için pass/fail/blocked/skipped sor
2. fail/blocked'da not + evidence path + GitHub Issue numarası iste
3. `qa/runs/YYYY/MM/TR-*.yml` üret

### Otomasyon sonuçlarını içe aktar

CI bunu otomatik yapıyor (`.github/workflows/qa-import-results.yml`). Lokal test için:

```bash
npm run import-results -- \
  --playwright=../reports/e2e-results.json \
  --cucumber=../reports/bdd/cucumber-report.json \
  --name=local
```

### Defect açmak

GitHub Issues template kullan: **Issue → New → QA Defect**. Form yapılandırılmış:
- İlgili TC (ID)
- Bulunduğu Run (TR ID)
- Severity (S1-S4)
- Reproduce / Expected / Actual

Issue kapanınca CI bot `qa/defects/GH-{NUMBER}.md` mirror üretir.

---

## 5. AI ile çalışmak — 10 dakika

Cortex AI Automation kendi LLM stack'ine sahip. `qa/tools/ai-suggest.mjs` bunu QA için kullanır.

### TC draft üretimi

```bash
npm run ai-suggest -- --requirement=REQ-AUTH-005 --suite=auth --max-cases=5
# → qa/cases/auth/_draft/DRAFT-TC-AUTH-019-*.md
#   DRAFT-TC-AUTH-020-*.md
#   ...
```

LLM bir requirement'tan 3-6 adımlı TC taslakları üretir. **Hiçbiri active değildir** — `_draft/` klasöründe izole.

### Promote akışı

```bash
npm run tc-promote -- --suite=auth
# Interaktif: her draft için Promote / Skip / Delete
```

**Kural**: her draft mutlaka insan review'ından geçecek. AI taslağı doğrudan koşulmaz.

### AI cost rails

- Hard cap: **$5/gün** (`qa/.ai-budget.json`)
- Warn threshold: $1
- Max cases per request: **10**
- CI'da default çalışmaz — opt-in

### Ne zaman AI, ne zaman manuel?

| AI iyi | Manuel daha iyi |
|---|---|
| Boilerplate TC (CRUD'un negative case'leri) | UX/usability TC'leri |
| Spec'ten TC çıkarma | Edge case keşfi (exploratory) |
| 5+ benzer pattern (parametrik) | Subjective değerlendirmeler |
| Brainstorm | Stakeholder onayı gerektirenler |

---

## 6. Manuel vs otomasyon kararı — 5 dakika

Her TC için `automation.status` field'ı kararı yansıtır:

| Status | Anlam | Frontmatter |
|---|---|---|
| `not-automated` | Henüz otomatize edilmedi (yapılacak) | Default migration sonrası |
| `in-progress` | Otomasyon yazılıyor | Geçici durum |
| `automated` | BDD scenario var, `refs` doldurulmuş | `refs: [path:line]` zorunlu |
| `out-of-scope` | Manuel kalacak — UX, accessibility subjektif | `reason:` zorunlu |

### Karar matrisi

| Durum | Karar | Mantık |
|---|---|---|
| Tekrarlanan smoke testi | Automate (P0 öncelik) | ROI yüksek |
| Karmaşık akış, nadir koşulur | Manuel (out-of-scope) | Otomasyon maliyeti > değer |
| UX/accessibility subjektif | Manuel + AI-assisted | İnsan yargısı şart |
| Yeni feature, henüz spec olgun değil | Manuel önce, automate sonra | Feature dondukça automate |
| Security / compliance audit | Hybrid: otomatik scan + manuel review | İki katman |

---

## 7. CI ve QA gates — 5 dakika

3 GitHub Actions workflow var:

| Workflow | Tetik | Görev |
|---|---|---|
| `qa-validate.yml` | Her PR | Schema + ID + ref kontrolü (**blocking**) |
| `qa-import-results.yml` | Test workflow sonrası | Test sonuçlarını run YAML'a çevir, auto-commit |
| `qa-defect-mirror.yml` | Issue closed (label: qa-defect) | `qa/defects/GH-*.md` mirror üret |

**Branch workflow** (zorunlu): `feature/* → test → main`. Detay: `docs/BRANCHING_WORKFLOW.md`.

---

## 8. Debug workflow — 5 dakika

### TC fail oldu, ne yapayım?

1. **Reproduce et lokalde**:
   ```bash
   # Manuel TC ise:
   npm run run-record -- --plan=smoke-daily
   # Otomatik ise (BDD):
   cd e2e && npx cucumber-js --tags @TC-AUTH-001
   ```

2. **Gerçek bug mı, flaky mi?**:
   ```bash
   node tools/flakiness.mjs    # flip oranını gör
   ```

3. **Bug ise**: GitHub Issue aç (QA Defect template). Run ID + TC ID + reproduce adımları.

4. **Flaky ise**:
   - `e2e/quarantine.json`'a ekle (otomasyon)
   - TC frontmatter'ına `tags: [flaky]` ekle
   - Root cause analizi → `qa/reporting/rca.template.md`'i doldur

### Cross-validation

```bash
node tools/test-impact.mjs --base=main  # PR'ın etkilediği TC'leri gör
node tools/trace.mjs                     # traceability güncel mi
node tools/dashboard.mjs                 # browser'da aç → coverage/dashboard.html
```

---

## 9. Release sign-off — 5 dakika

```bash
node tools/signoff.mjs --plan=TP-2026.Q2-RELEASE
# → qa/reporting/release-R-2026.Q2-signoff.md
```

Otomatik kontrol:
- Tüm P0 TC pass mı?
- P1 fail oranı limit altında mı?
- Açık S1 defect var mı?
- Hiç koşturulmamış TC sayısı

Karar: **GO** / **NO-GO** önerisi (insan onayı zorunlu).

---

## 10. Sık sorulan sorular

### "TC nereye yazılır?" karar ağacı

```
Manuel test çalışacak mı?
├── Evet, sadece manuel → qa/cases/{suite}/TC-*.md (status: out-of-scope veya not-automated)
├── BDD ile otomatik → qa/cases/ + e2e/bdd/features/{suite}/*.feature + @TC-* tag
├── Unit test → qa kapsamı dışı; backend/tests/unit/ veya packages/*/test/
└── API contract → qa/cases/{suite}/ + backend/tests/bdd/ veya api-tests/
```

### "Owner kim olmalı?"

TC frontmatter `owner:` field'ı = ana sorumlu. CODEOWNERS otomatik üretiliyor:
```bash
node tools/sync-codeowners.mjs --write
```

### "Tag mi, type mi, tag mi?"

| Konsept | Konum | Örnek |
|---|---|---|
| `type` (taksonomi) | Frontmatter, enum | `[functional, smoke, security]` |
| `tags` (free-form) | Frontmatter, kebab-case | `[mobile-only, third-party-api]` |
| BDD tag (linking) | `.feature` üstüne | `@TC-AUTH-001` |

### "Aynı TC iki BDD'de tag'lensin mi?" (UI + API katmanı)

Evet, hem `e2e/bdd/features/auth/login.feature:12` (UI) hem `backend/tests/bdd/features/authentication.feature:11` (API) aynı TC-AUTH-001'i tag'leyebilir. Trace.mjs ikisini de `automation.refs` olarak gösterir.

### "Plan ne sıklıkta güncellenir?"

- `smoke-daily.yml` — release-agnostic, statik
- `2026.Q2-release.yml` — release başına, milestone'a bağlı
- `hotfix-*.yml` — gerektiğinde, kısa ömürlü

---

## 11. İletişim

| Kanal | Ne zaman |
|---|---|
| GitHub Issue (qa-defect label) | Bug raporu |
| GitHub Discussion | Mimari soru, "nasıl yapılır" |
| Slack #qa-team (varsa) | Hızlı senkron |
| `qa/strategy/test-strategy.md` | Politika kararları |

---

## 12. İlk hafta için checklist

- [ ] `qa/INSTALL.md`'i takip ederek kurulum yap
- [ ] Bu handbook'u oku (1 saat)
- [ ] `qa/CONVENTIONS.md`'i hızla geç (ID şeması + frontmatter spec)
- [ ] Bir TC'yi end-to-end yaz (new-tc → editle → validate → commit)
- [ ] Bir TC'yi manuel koş (run-record)
- [ ] Bir AI-suggest dene (dry-run + promote)
- [ ] Dashboard'u aç (`node tools/dashboard.mjs && open coverage/dashboard.html`)
- [ ] Mevcut bir GitHub Issue'u QA Defect template ile aç (test amaçlı)
- [ ] PR aç, qa-validate workflow'unun yeşil verdiğini gör

Sonraki sprint: bir release sign-off'ta gözlemci ol.

---

## Lisans ve katkı

Bu doküman canlı (living document) — değişiklik için PR aç, CODEOWNERS (@qa-leads) review eder.
