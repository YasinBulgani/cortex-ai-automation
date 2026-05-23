# qa/ Incident Response Runbook

> QA tarafından sahiplenilen incident'lar için adım adım yanıt prosedürü.
> Production incident'ları için `docs/ai-workflow-incident-runbook.md` (ürün ekibi).

## Severity tanımları (QA bağlamı)

| Sev | Etki | Yanıt süresi | Örnek |
|---|---|---|---|
| **S1** | Release stopper, prod'a etki | < 1 saat | CI yeşil ama prod fail, P0 TC regression |
| **S2** | Major QA blokajı | < 4 saat | Smoke suite kırık, test environment down |
| **S3** | Workflow yavaşlatıyor | < 1 gün | Flaky %20+, dashboard hatası |
| **S4** | İyileştirme | < 1 hafta | Doc eksiği, tooling UX |

---

## Senaryo 1 — P1+ fail patlaması (S1)

**Trigger:** Nightly run'da 5+ TC ardışık fail veya P0 fail.

### Adımlar

1. **Triage (5 dk)**
   ```bash
   cd qa && node tools/health-check.mjs
   node tools/flakiness.mjs    # flaky mi gerçek mi
   ```
2. **Root cause sınıflandırma**:
   - Code regression → `engineering` team eskale
   - Test data corruption → `seed:test` çalıştır
   - Env down → `infrastructure` team eskale
   - Flaky cluster → quarantine + Issue aç
3. **İletişim**: Slack #qa-incidents, `@on-call`'a ping
4. **Mitigation**:
   - Eğer code regression: ilgili PR'ı revert öner
   - Eğer env: failed run'lar `blocked` olarak işaretle (manuel run-record)
5. **Post-mortem**: 24 saat içinde `qa/reporting/rca.template.md` kullan, qa/reporting/rca-YYYYMMDD-{slug}.md'e yaz

---

## Senaryo 2 — CI yeşil ama prod red (S1)

**Trigger:** Smoke yeşil, deploy sonrası kullanıcı bildirimi var.

### Adımlar

1. **Gap analizi**: ne test edilmedi?
   - `node tools/test-impact.mjs --base=last-deploy-sha`
   - Etkilenen TC'lerin coverage'ı var mı?
2. **Acil reproducer TC yaz**:
   ```bash
   npm run new-tc -- --suite={domain} --title="REGRESSION: {short desc}"
   ```
3. Frontmatter:
   ```yaml
   priority: P0
   type: [functional, regression]
   tags: [post-deploy-discovered, incident-NNNN]
   ```
4. **Coverage gap kayıt**: `qa/coverage/gap-incidents.md`'e satır ekle
5. **Defect Issue aç** (qa-defect template)
6. **Post-mortem**: niye smoke yakalayamadı? Smoke set genişletilmeli mi?

---

## Senaryo 3 — qa-validate workflow sürekli fail (S2)

**Trigger:** PR'lar merge edilemiyor, CI badge kırmızı.

### Adımlar

1. **Lokal reproduce**:
   ```bash
   cd qa && rm -rf node_modules && npm install
   node tools/validate.mjs
   ```
2. **Genelde sebep**:
   - Yeni TC schema'ya uymuyor (en yaygın)
   - Eski TC silinmiş ama plan referans veriyor
   - `automation.refs` ölü link
3. **Quick fix**: validate output'undaki `✗ FAIL` mesajını oku, ilgili dosyayı düzelt
4. **Yapısal sorun varsa**: schema versiyonunu artır (`qa/tools/schemas/*.json`), migration script yaz
5. **Geçici bypass**: PR'da `--no-verify` git commit (sadece acil deploy)

---

## Senaryo 4 — Dashboard hatası (S3)

**Trigger:** `node tools/dashboard.mjs` 500 veya boş HTML.

### Adımlar

1. **Hata mesajını oku**: stderr'a düşer
2. **Genelde sebep**:
   - Bozuk YAML (gray-matter parse fail)
   - Tipte tutmayan frontmatter (date string vs Date object)
   - `coverage/` dosyaları stale
3. **Fix**:
   ```bash
   node tools/validate.mjs            # bozuk dosya bul
   node tools/trace.mjs               # coverage regenerate
   node tools/dashboard.mjs
   ```
4. Eğer hala fail: `apps/web/qa-dashboard/` Next.js fallback'i dene

---

## Senaryo 5 — AI suggest cost patlaması (S2)

**Trigger:** `qa/.ai-budget.json` $5/gün hard cap'e ulaştı.

### Adımlar

1. **Lokal kontrol**:
   ```bash
   cat qa/.ai-budget.json
   ```
2. **Anlama**:
   - Hangi kullanıcı/CI çağırdı? `git log --since="1 day ago" -- qa/cases/*/_draft/`
   - LLM provider rate limit'i ayrıca devrede mi?
3. **Reset**:
   ```bash
   echo '{"day":"'$(date +%Y-%m-%d)'","usd":0}' > qa/.ai-budget.json
   ```
4. **Kalıcı çözüm**: `--max-cases` flag'ini düşür (5 → 3), CI'da AI özelliği opt-in
5. **Audit**: 7 günlük AI usage raporu (history'den çek)

---

## Senaryo 6 — Defect mirror workflow fail (S3)

**Trigger:** Issue kapandı ama `qa/defects/GH-*.md` mirror oluşmadı.

### Adımlar

1. GitHub Actions log'una bak (`qa-defect-mirror.yml`)
2. **Genelde sebep**:
   - Issue body template'i ile uyumsuz (kullanıcı template kullanmamış)
   - `gh api` rate limit
   - `qa-bot` commit izni yok
3. **Manuel mirror**:
   ```bash
   cd qa && node tools/mirror-defect.mjs --issue=1234 --repo=owner/repo
   git add qa/defects && git commit -m "qa: manual mirror #1234"
   ```
4. **Workflow fix**: `.github/workflows/qa-defect-mirror.yml` log'unda hata düzelt

---

## Senaryo 7 — Migration sırasında veri kaybı şüphesi (S1)

**Trigger:** Migration PR sonrası TC sayısı düşmüş, validate yeşil olsa bile.

### Adımlar

1. **Hızlı sayım**:
   ```bash
   find qa/cases -name "TC-*.md" | wc -l   # şu an
   git log --diff-filter=D --name-only -- qa/cases/ | grep "TC-" | head -20  # silinenler
   ```
2. **Concat-diff test** (PR 3'teki teknik):
   ```bash
   # son commit'i göster
   git show HEAD~1:qa/cases/...md  # eski versiyon
   ```
3. **Recovery**:
   ```bash
   git revert <migration-sha>      # tam revert
   # veya
   git checkout HEAD~1 -- qa/cases/<lost-file>.md  # spesifik dosya
   ```
4. **Post-mortem**: migration script'ine concat-diff doğrulama eklenmeli

---

## Genel iletişim akışı

```
QA on-call (PR review on-duty)
       │
       ▼  triage
   Severity belirle
       │
       ├── S1 → Slack #incidents + @on-call (immediate)
       ├── S2 → Slack #qa-team (saatler içinde)
       ├── S3 → GitHub Issue (gün içinde)
       └── S4 → Backlog
```

## Eskalasyon matrisi

| Konu | Sahip | Eskalasyon |
|---|---|---|
| qa/ tooling | @qa-leads | Tech Lead |
| Test data | Backend team | DBA + Backend Lead |
| CI workflow | DevOps + @qa-leads | Tech Lead |
| AI cost | @qa-leads | CTO + Finance |
| Veri kaybı | @qa-leads | Tech Lead + CTO |
| Compliance/security | Security team | CTO + Legal |

## Post-mortem şablonu

Bkz: `qa/reporting/rca.template.md`

5 Whys + Timeline + What worked / What didn't + Action items zorunlu.

## Bu runbook'un kendisi

- Update: yeni senaryo eklendikçe canlı doküman
- CODEOWNERS: `@qa-leads`
- Review cadence: quarterly
