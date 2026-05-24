# Jenkins Setup Guide

Last updated: 2026-04-16

Bu repo icin temel Jenkins entegrasyonu `Jenkinsfile`, `jenkins/Jenkinsfile.deploy`, `jenkins/Jenkinsfile.rollback` ve `scripts/ci/` altindaki yardimci script'lerle hazirlandi.

## Files

- `Jenkinsfile`
- `jenkins/Jenkinsfile.deploy`
- `jenkins/Jenkinsfile.rollback`
- `scripts/ci/common.sh`
- `scripts/ci/test.sh`
- `scripts/ci/deploy.sh`
- `scripts/ci/rollback.sh`

Pipeline mantigi su sekilde bolunur:

- `Jenkinsfile`: Jenkins orchestration katmani
- `jenkins/Jenkinsfile.deploy`: deploy-only orchestration katmani
- `jenkins/Jenkinsfile.rollback`: rollback-only orchestration katmani
- `scripts/ci/test.sh`: CI test suite'leri
- `scripts/ci/deploy.sh`: staging ve production deploy akisi
- `scripts/ci/rollback.sh`: image tag tabanli rollback akisi
- `scripts/ci/common.sh`: ortak helper fonksiyonlari
- `scripts/ci/allure.sh`: Allure HTML rapor uretimi
- `scripts/ci/notify.sh`: webhook bildirimleri

Guncel pipeline, ilk geri bildirim icin guvenle paralellestirilebilen adimlari ayri stage'lerde calistirir:

- frontend checks
- backend lint
- engine unit

DB ve port kullanan testler ise cakisma riskini dusurmek icin ayrik stage'lerde sirali calisir.

Ek olarak CI script'leri artik build bazli port turetir:

- Postgres: `CI_POSTGRES_PORT`
- Redis: `CI_REDIS_PORT`
- Backend API: `API_PORT`
- Web app: `APP_PORT`
- Engine: `ENGINE_PORT`

Bu degiskenler verilmezse Jenkins `BUILD_NUMBER` degerinden turetilen varsayilan portlar kullanilir.

## Jenkins Prerequisites

Jenkins controller veya agent tarafinda asagidaki araclar kurulu olmali:

- `git`
- `bash`
- `python3`
- `node`
- `npm`
- `docker`
- `docker compose`
- `curl`
- `ssh`

Onerilen minimum versiyonlar:

- Python `3.12`
- Node `20`
- Docker `24+`

Playwright testleri icin Jenkins agent'in Chromium bagimliliklarini kurabilecek durumda olmasi gerekir. Linux agent kullanimi tavsiye edilir.
Allure HTML uretimi icin agent'ta `java` olmasi onerilir.

## Recommended Plugins

Pipeline'in sorunsuz calismasi icin su Jenkins plugin'lerini oneririm:

- `Pipeline`
- `Git`
- `Credentials Binding`
- `SSH Agent`
- `JUnit`
- `AnsiColor`
- `Timestamper`

Opsiyonel ama faydali:

- `Docker Pipeline`
- `HTML Publisher`
- `Workspace Cleanup`
- `Mailer`

Not: Mevcut `Jenkinsfile`, workspace temizligi icin `deleteDir()` kullandigi icin `Workspace Cleanup` zorunlu degildir.

## Required Credentials

Pipeline bu credential adlarini bekler. Jenkins UI → **Manage Jenkins → Credentials → System → Global credentials** altinda ekle.

> ⚠️ Bu credential'lar Jenkins'de **tanımlı olmadan** `PUSH_IMAGES=true` veya `DEPLOY_STAGING=true` çalıştırılırsa ilgili stage hata verir.

### Container Registry

| ID | Tip | Ne gireceğin |
|---|---|---|
| `ghcr-creds` | `Username with password` | GitHub kullanıcı adı + `ghcr.io` için oluşturulmuş PAT (scopes: `write:packages`, `read:packages`) |

**PAT oluşturma:** GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic) → `write:packages` seç.

### Staging SSH

| ID | Tip | Ne gireceğin |
|---|---|---|
| `staging-ssh-key` | `SSH Username with private key` | Staging sunucusu için `ssh-keygen -t ed25519` ile oluşturulan private key |
| `staging-host` | `Secret text` | Staging sunucu IP veya hostname (örn. `staging.example.com`) |
| `staging-user` | `Secret text` | SSH kullanıcısı (örn. `deploy`) |
| `staging-path` | `Secret text` | Sunucudaki deploy dizini (örn. `/srv/cortex`) |

### Production SSH

| ID | Tip | Ne gireceğin |
|---|---|---|
| `prod-ssh-key` | `SSH Username with private key` | Production sunucu private key (staging'den farklı olmalı) |
| `prod-host` | `Secret text` | Production IP/hostname |
| `prod-user` | `Secret text` | SSH kullanıcısı |
| `prod-path` | `Secret text` | Deploy dizini |

**Kontrol komutu (credential'lar tanımlı mı?):**
```bash
# Jenkins Script Console'da çalıştır (Manage Jenkins → Script Console):
println Jenkins.instance.getExtensionList('com.cloudbees.plugins.credentials.SystemCredentialsProvider')[0]
  .getCredentials().collect { it.id }
```
Çıktıda `ghcr-creds`, `staging-ssh-key`, `staging-host`, `staging-user`, `staging-path`, `prod-ssh-key`, `prod-host`, `prod-user`, `prod-path` görünmeli.

## Recommended Job Type

En iyi secenek iki ayri job kullanmaktir:

- `cortex-ci`: script path `Jenkinsfile`
- `cortex-deploy`: script path `jenkins/Jenkinsfile.deploy`
- `cortex-rollback`: script path `jenkins/Jenkinsfile.rollback`

`cortex-ci` icin `Multibranch Pipeline` daha uygundur.
`cortex-deploy` icin normal `Pipeline` job genelde daha kontrolludur.

Kurulum:

1. Jenkins'te `cortex-ci` icin `New Item` sec.
2. `Multibranch Pipeline` olustur.
3. Repo baglantisini tanimla.
4. Branch discovery aktif et.
5. Script path olarak `Jenkinsfile` kullan.

Deploy job icin:

1. Jenkins'te `cortex-deploy` adli yeni bir `Pipeline` job olustur.
2. Repo baglantisini tanimla.
3. `Pipeline script from SCM` sec.
4. Script path olarak `jenkins/Jenkinsfile.deploy` kullan.

Rollback job icin:

1. Jenkins'te `cortex-rollback` adli yeni bir `Pipeline` job olustur.
2. Repo baglantisini tanimla.
3. `Pipeline script from SCM` sec.
4. Script path olarak `jenkins/Jenkinsfile.rollback` kullan.

Eger tek job ile ilerleyeceksen sadece `Jenkinsfile` da yeterlidir, ancak operasyonel olarak ayri deploy job daha sagliklidir.

## Pipeline Parameters

`Jenkinsfile` su parametreleri kullanir:

- `TEST_SUITE`
  Degerler: `smoke`, `standard`, `full`
- `PUSH_IMAGES`
  Docker image push asamasini acar
- `DEPLOY_STAGING`
  Staging deploy asamasini acar
- `DEPLOY_PRODUCTION`
  Production approval ve deploy asamasini acar
- `IMAGE_TAG`
  Bos birakilirsa mevcut commit short SHA kullanilir
- `REGISTRY_REPO`
  Ornek: `ghcr.io/bgts/bgts`
- `NOTIFY_EMAIL_TO`
  Opsiyonel e-posta alici listesi

`jenkins/Jenkinsfile.deploy` su parametreleri kullanir:

- `TARGET_ENV`
  Degerler: `staging`, `production`
- `IMAGE_TAG`
  Deploy edilecek image tag
- `REMOTE_COMPOSE_FILE`
  Uzak sunucudaki compose dosyasi
- `HEALTHCHECK_URL`
  Opsiyonel health check override
- `REQUIRE_APPROVAL`
  Production deploy oncesi manuel onay ister
- `NOTIFY_EMAIL_TO`
  Opsiyonel e-posta alici listesi

`jenkins/Jenkinsfile.rollback` su parametreleri kullanir:

- `TARGET_ENV`
  Degerler: `staging`, `production`
- `ROLLBACK_IMAGE_TAG`
  Geri donulecek image tag
- `ROLLBACK_REASON`
  Audit ve bildirimlerde kullanilan aciklama
- `REMOTE_COMPOSE_FILE`
  Uzak sunucudaki compose dosyasi
- `HEALTHCHECK_URL`
  Opsiyonel health check override
- `REQUIRE_APPROVAL`
  Production rollback oncesi manuel onay ister
- `SKIP_HEALTHCHECK`
  Acil durumda health check'i atlar
- `NOTIFY_EMAIL_TO`
  Opsiyonel e-posta alici listesi

## Notifications

Bildirimler iki kanaldan gidebilir:

- webhook tabanli Slack veya Teams bildirimi
- Jenkins `mail` step ile e-posta bildirimi

Webhook bildirimleri icin job veya folder seviyesinde su environment variable tanimlanabilir:

```bash
NOTIFY_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Bu degisken tanimliysa `scripts/ci/notify.sh` success, unstable ve failure durumlarinda bildirim yollar.
Teams incoming webhook URL'leri icin de ayni script kullanilir.

E-posta bildirimleri icin ilgili job calistirilirken `NOTIFY_EMAIL_TO` parametresi doldurulabilir:

```text
devops@example.com,qa@example.com
```

Not:

- webhook tanimli degilse pipeline hata vermez, bildirimi sessizce atlar
- `mail` step kullanimi icin Jenkins mail configuration yapilmis olmali

## What Each Suite Runs

### `smoke`

- frontend type check ve build
- backend lint
- local postgres ve redis baslatma
- migration + seed
- backend smoke tests
- engine unit tests
- Playwright smoke

### `standard`

- `smoke` kapsamindaki her sey
- backend service tests
- backend API, RBAC, contract ve security tests
- BDD API tests
- Allure report generation

### `full`

- `standard` kapsamindaki her sey
- Playwright regression

## Agent Requirements

Pipeline local Docker container'lari kullanir:

- `jenkins-postgres-<build-slug>`
- `jenkins-redis-<build-slug>`

Bu nedenle Jenkins agent'ta Docker daemon erisimi olmali. Docker-in-Docker yerine host Docker socket kullanan bir Linux agent daha pratiktir.

Varsayilan durumda build bazli turetilen portlar kullanilir. Istenirse manuel override yapilabilir:

```bash
export CI_POSTGRES_PORT=15432
export CI_REDIS_PORT=16379
export API_PORT=18000
export APP_PORT=13000
export ENGINE_PORT=15001
```

Statik port zorlamasi yapilacaksa agent'ta ilgili portlar bos olmali:

- `CI_POSTGRES_PORT`
- `CI_REDIS_PORT`
- `API_PORT`
- `APP_PORT`
- `ENGINE_PORT`

Eger ayni agent uzerinde paralel job kosacaksa bu tasarim port cakismasi riskini ciddi azaltir. Yine de su yaklasimlar onerilir:

- ayrik agent havuzu kullanilir
- gerekiyorsa port override env'leri job seviyesinde sabitlenir
- daha ileri izolasyon icin test servisleri compose project name ile ayrilabilir

## First Run Plan

Ilk kurulumda su sirayi kullan:

1. Jenkins agent'ta `python3`, `node`, `docker`, `docker compose` dogrula.
2. Credential'lari Jenkins'e ekle.
3. `TEST_SUITE=smoke` ile ilk build'i calistir.
4. Sonra `TEST_SUITE=standard` dene.
5. Registry erisimi dogrulandiktan sonra `PUSH_IMAGES=true` ile image push test et.
6. Son olarak `DEPLOY_STAGING=true` ile staging deploy akisini ac.
7. Production deploy'u en son aktif et.

## Manual Test Commands

Jenkins disinda local olarak script'leri denemek icin:

```bash
chmod +x scripts/ci/*.sh
./scripts/ci/test.sh smoke
./scripts/ci/test.sh standard
./scripts/ci/test.sh full
```

Granuler stage komutlari da tek tek kosulabilir:

```bash
./scripts/ci/test.sh frontend
./scripts/ci/test.sh lint
./scripts/ci/test.sh engine-unit
./scripts/ci/test.sh backend-smoke
./scripts/ci/test.sh backend-service
./scripts/ci/test.sh backend-api
./scripts/ci/test.sh bdd-api
./scripts/ci/test.sh e2e-smoke
./scripts/ci/test.sh e2e-regression
./scripts/ci/allure.sh
NOTIFY_WEBHOOK_URL=https://hooks.slack.com/services/... ./scripts/ci/notify.sh cortex-ci SUCCESS http://jenkins.example/job/1
```

Deploy script'i localden de dogrulanabilir:

```bash
export DEPLOY_HOST=example.com
export DEPLOY_USER=deploy
export DEPLOY_PATH=/srv/bgts
export IMAGE_TAG=abc1234
./scripts/ci/deploy.sh staging
```

Deploy-only pipeline mantigi:

- CI build'i image push yapar
- `cortex-deploy` job'u sadece secilen `IMAGE_TAG` ile staging veya production deploy yapar
- production icin opsiyonel approval adimi vardir

Rollback-only pipeline mantigi:

- `cortex-rollback` job'u yalnizca secilen `ROLLBACK_IMAGE_TAG` ile geri doner
- rollback sırasında migration downgrade yapilmaz
- production icin opsiyonel approval adimi vardir
- rollback sonunda `reports/rollback-metadata.json` artifact olarak saklanir

Port override ile lokal smoke denemesi:

```bash
export CI_POSTGRES_PORT=15432
export CI_REDIS_PORT=16379
export API_PORT=18000
export APP_PORT=13000
export ENGINE_PORT=15001
./scripts/ci/test.sh smoke
```

## Expected Jenkins Stage Flow

Temel stage akisi:

1. `Checkout`
2. `Verify Tooling`
3. `Parallel Checks`
4. `Backend Smoke`
5. `Backend Service`
6. `Backend API`
7. `BDD API`
8. `E2E Smoke`
9. `E2E Regression`
10. `Allure Report`
11. `Build Docker Images`
12. `Push Docker Images`
13. `Deploy Staging`
14. `Production Approval`
15. `Deploy Production`

Her build sonrasinda:

- `reports/*.xml` JUnit olarak publish edilir
- `reports/**/*` artifact olarak arsivlenir
- `reports/allure-report/index.html` varsa HTML Publisher ile yayinlanir

## Failure Triage

### Frontend build fails

Kontrol et:

- `apps/web` icindeki dependency uyumu
- `npm ci` lockfile senkronu
- Next.js build-time env degiskenleri

### Backend tests fail before execution

Kontrol et:

- Docker ayakta mi
- `5432` portu dolu mu
- postgres container basladi mi
- migration hatasi var mi

### Playwright fails to install browsers

Kontrol et:

- agent'in internet erisimi
- Linux library dependency'leri
- Docker veya host izinleri

### Allure report is missing

Kontrol et:

- `reports/allure-results/` dolu mu
- agent'ta `java` var mi
- `npx` erisimi calisiyor mu
- Jenkins'te `HTML Publisher` plugin'i yuklu mu

### Deploy fails over SSH

Kontrol et:

- `staging-ssh-key` veya `prod-ssh-key`
- `known_hosts` olusumu
- hedef hostta `docker compose` var mi
- hedef dizinde `docker-compose.prod.yml` mevcut mu

### Rollback validation fails

Kontrol et:

- `ROLLBACK_IMAGE_TAG` bos mu
- `ROLLBACK_IMAGE_TAG=latest` verilmis mi
- image registry'de mevcut mu
- rollback nedeni audit icin girilmis mi

### Health check fails after deploy

Kontrol et:

- `https://<host>/health`
- Nginx TLS ayarlari
- backend container log'lari
- migration'in tamamlanip tamamlanmadigi

## Current Limitations

Mevcut ilk surum bilerek sade tutuldu. Su alanlar henuz eklenmedi:

- cache optimization
- remote release history kaydi
- registry tag varlik dogrulamasi

## Recommended Next Improvements

Bu temel kurulumdan sonra su iyilestirmeler mantikli olur:

1. Docker test servislerini tekil port yerine izole compose projesine almak
2. Ayrica `cortex-deploy` adli ayrik bir deployment pipeline olusturmak
3. Image build ve test cache'lerini kalici hale getirmek
4. Allure sonuc kapsamını BDD disindaki testlere de genisletmek
