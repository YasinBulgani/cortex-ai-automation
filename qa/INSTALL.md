# qa/ — Geliştirici Kurulumu

İlk kurulum (bir kez) ve günlük kullanım.

## İlk kurulum

```bash
# 1. Node.js 18+ gerekli (zaten monorepo gereksinimi)
node --version  # >= 18

# 2. qa/ tooling kur
cd qa
npm install
cd ..

# 3. Pre-commit hook'lar (opsiyonel ama önerilen)
pip install pre-commit
pre-commit install

# 4. (Opsiyonel) AI özellikleri için provider key
export CORTEX_AI_GATEWAY_URL="http://localhost:8000/ai-gateway"  # tercih
# VEYA
export ANTHROPIC_API_KEY="sk-ant-..."
# VEYA
export OPENAI_API_KEY="sk-..."
```

Toplam kurulum süresi: **~3 dakika**.

## Günlük kullanım

### Yeni TC yazmak

```bash
cd qa
npm run new-tc -- --suite=auth --title="MFA login akışı"
# → qa/cases/auth/TC-AUTH-019-mfa-login-akisi.md (frontmatter dolu)
```

Editöründe aç, adımları doldur, commit. Pre-commit hook validate.mjs çalıştırır.

### AI ile TC draft

```bash
npm run ai-suggest -- --requirement=REQ-AUTH-001 --suite=auth
# → qa/cases/auth/_draft/DRAFT-TC-AUTH-020-*.md (LLM üretti, review gerek)
```

Review sonrası promote:

```bash
npm run tc-promote -- --suite=auth
# Interaktif: her draft için promote / skip / delete
```

### Validate + traceability

```bash
npm run validate   # Schema + ID + cross-ref
npm run trace      # coverage/* dosyalarını güncelle
```

### Manuel koşum kaydı

```bash
npm run run-record -- --plan=smoke-daily
# Interaktif TUI; sonuç qa/runs/YYYY/MM/TR-*.yml
```

### Otomasyon sonuçlarını içe aktar

```bash
npm run import-results -- \
  --playwright=../reports/e2e-results.json \
  --cucumber=../reports/bdd/cucumber-report.json \
  --name=local-test
```

### Statik dashboard üret

```bash
node tools/dashboard.mjs
# → qa/coverage/dashboard.html (browser'da aç)
```

### Release sign-off raporu

```bash
node tools/signoff.mjs --plan=TP-2026.Q2-RELEASE
# → qa/reporting/release-R-2026.Q2-signoff.md
```

## CI entegrasyonu

3 workflow zaten kurulu:
- `.github/workflows/qa-validate.yml` — Her PR'da validate + trace
- `.github/workflows/qa-import-results.yml` — Test koşumları sonrası run YAML üret
- `.github/workflows/qa-defect-mirror.yml` — Kapanan Issue'lardan defect mirror

## Sorun giderme

### `Error: no schema with key "https://json-schema.org/draft/2020-12/schema"`

Ajv default JSON Schema Draft 2020-12'yi tanımıyor. `tools/validate.mjs` zaten `ajv/dist/2020.js` import ediyor. `cd qa && npm install` ile node_modules güncelle.

### `Cannot find module 'fast-glob'`

Wrong cwd. CLI'ları her zaman `qa/` içinden çalıştır:
```bash
cd qa && node tools/validate.mjs   # ✓
node qa/tools/validate.mjs          # ✗ (node_modules bulunamaz)
```

### Pre-commit hook fail ediyor

```bash
# Lokalde manuel çalıştır:
cd qa && npm run validate
cd qa && npm run trace
git add qa/coverage
```

### AI provider error

```bash
# Dry-run ile prompt'u inspect et:
npm run ai-suggest -- --requirement=REQ-AUTH-001 --suite=auth --dry-run
```

## Dokümantasyon

| Konu | Dosya |
|---|---|
| Mimari + felsefe | [README.md](README.md) |
| ID şeması, frontmatter, naming | [CONVENTIONS.md](CONVENTIONS.md) |
| Strateji + migration tarihçesi | [strategy/](strategy/) |
| Reporting şablonları | [reporting/](reporting/) |
| Test design dokümanları | [test-design/](test-design/) |
