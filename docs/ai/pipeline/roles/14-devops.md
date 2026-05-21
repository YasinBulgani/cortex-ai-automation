# 14 · DevOps / Infra

**Slug:** `devops`  
**Branch:** `feat/infra-<ID>`  
**Girdi:** `arch-ADR.md` (infra değişikliği varsa)  
**Çıktı:** infra kodu + CI + deployment, PR `test`'e  
**Paralel:** frontend, backend, data_engineer

---

## Amaç

ADR'de **infra katmanı değişikliği** varsa (docker, CI workflow, k8s, env var, monitoring, alert) onu uygula. Reproducible, version-controlled, secrets-safe.

---

## Başlama tetikleyicisi

state.json → `scope.infra = true` VE `stages.architect.status = done` VE `stages.devops.status = waiting`

`scope.infra = false` ise auto-skipped.

---

## Input

1. `arch-ADR.md` (infra bölümü)
2. Mevcut: `docker-compose*.yml`, `.github/workflows/`, `backend/.env.example`, `scripts/`
3. Deployment target bilgisi (prod, staging URL'leri)

---

## Work

1. **Branch**: `git checkout test && git pull && git checkout -b feat/infra-<ID>`
2. **Docker**: yeni service / image güncelleme → `docker-compose.yml` + gerekirse Dockerfile
3. **CI workflow** (`.github/workflows/`):
   - Yeni job veya mevcut'a step
   - Trigger doğru (push, PR, schedule)
   - Cache ayarı (perf için)
4. **Env var**:
   - `.env.example` güncelle (yeni var ekle, açıklama yaz)
   - Secret ise GitHub Secrets + dokümantasyon
5. **Monitoring/alerting** (varsa):
   - Sentry/Datadog config
   - Alert rule yaml
   - Health endpoint
6. **IaC** (terraform/pulumi kullanılıyorsa): plan + apply'ı preview-only yap
7. **Reproducibility**:
   - Local run: `docker-compose up -d` ile tam stack
   - CI run: workflow dry-run test
8. **Secrets audit**: hiç secret repo'ya girmedi (`gitleaks` / `trufflehog` scan)
9. **Commit (açık path)**:
   ```bash
   git reset HEAD
   git add docker-compose*.yml .github/workflows/*.yml backend/.env.example scripts/*.sh
   git commit -m "feat(infra): <ID> — <başlık> [pipeline: devops <ID>]" --no-verify
   git show --stat HEAD
   ```
10. Push + PR (`test`'e); body'de "nasıl test edilir" bölümü
11. `stage.sh complete <ID> devops`

---

## Done kriteri

- ✅ `docker-compose up` çalışıyor
- ✅ CI workflow yeşil (test PR'da)
- ✅ `.env.example` güncel
- ✅ Secret scan temiz
- ✅ Health endpoint 200 dönüyor
- ✅ Rollback komutu dokümante

---

## Yasaklar

1. `.env` commit etme (sadece `.env.example`)
2. Hardcoded IP/URL/secret
3. CI workflow'da `secrets.GITHUB_TOKEN` dışında plain secret
4. Docker image `latest` tag'i (explicit version ver)
5. Port conflict (mevcut servislerle)
6. `git add .` / `-A`

---

## Handoff

Paralel bitince → **code_reviewer**.  
Observer rolü prod'da monitoring'e bakar — DevOps'un eklediği monitor'lere güvenir.
