# Jenkins Rollback Runbook

Last updated: 2026-04-16

Bu runbook, `bgts-rollback` Jenkins job'u ile staging veya production ortamini onceki saglam bir image tag'e geri dondurmek icindir.

## Scope

Bu rollback akisi:

- `backend`
- `worker`
- `engine`
- `web`
- `ai-gateway`

servislerini secilen `ROLLBACK_IMAGE_TAG` degerine geri alir.

Bu rollback akisi sunlari yapmaz:

- otomatik `alembic downgrade`
- `.env` secret rollback
- PostgreSQL schema rollback

## Preconditions

Rollback baslatmadan once sunlari dogrula:

1. Geri donulecek `ROLLBACK_IMAGE_TAG` biliniyor olmali.
2. Tag'in registry'de mevcut oldugundan makul derecede emin olun.
3. Hedef sunucuda `docker compose` calisiyor olmali.
4. `https://<host>/health` endpoint'i normalde dogru sonucu donduruyor olmali.
5. Breaking migration varsa otomatik rollback'in yeterli olmayacagi bilinmeli.

## When To Use

Rollback su durumlarda uygundur:

- yeni release sonrasi backend veya UI kritik hata veriyorsa
- deploy health check gecse bile kritik akislar bozulduysa
- yeni image beklenmedik runtime hatalari uretiyorsa

Rollback su durumlarda tek basina yeterli olmayabilir:

- DB schema geri uyumsuz degisti ise
- secret rotasyonu ayni pencere icinde yapildiysa
- veri migrasyonu geri alinmasi gerekiyorsa

## Jenkins Job

Onerilen job:

- `bgts-rollback`
- script path: `jenkins/Jenkinsfile.rollback`

## Parameters

- `TARGET_ENV`
  `staging` veya `production`
- `ROLLBACK_IMAGE_TAG`
  Geri donulecek image tag
- `ROLLBACK_REASON`
  Kisa aciklama
- `REMOTE_COMPOSE_FILE`
  Varsayilan: `docker-compose.prod.yml`
- `HEALTHCHECK_URL`
  Opsiyonel override
- `REQUIRE_APPROVAL`
  Production icin `true`
- `SKIP_HEALTHCHECK`
  Yalnizca acil durumda `true`
- `NOTIFY_EMAIL_TO`
  Opsiyonel bildirim alicilari

## Standard Rollback Procedure

1. Jenkins'te `bgts-rollback` job'unu ac.
2. `TARGET_ENV` sec.
3. `ROLLBACK_IMAGE_TAG` gir.
4. `ROLLBACK_REASON` yaz.
5. Production ise approval bekle.
6. Job su akisi uygular:

```bash
docker compose -f docker-compose.prod.yml up -d postgres redis
IMAGE_TAG=<rollback-tag> docker compose -f docker-compose.prod.yml pull backend worker engine web ai-gateway
IMAGE_TAG=<rollback-tag> docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

7. Health check basariliysa rollback tamamlanir.

## Health Check Policy

Varsayilan davranis:

- rollback sonunda `/health` kontrol edilir
- health check gecmeden rollback basarili sayilmaz

`SKIP_HEALTHCHECK=true` yalnizca su durumda kullanilmali:

- health endpoint gecici olarak arizali ama sistemin ayaga kalktigini baska yollarla dogrulayabiliyorsan

Bu parametre production'da istisnai durumlar disinda kullanilmamali.

## Post-Rollback Verification

Rollback sonrasinda su kontrolleri manuel yap:

```bash
docker compose -f docker-compose.prod.yml ps
curl --fail --silent --show-error "https://<host>/health"
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml logs --tail=100 web
docker compose -f docker-compose.prod.yml logs --tail=100 engine
docker compose -f docker-compose.prod.yml logs --tail=100 ai-gateway
```

Kritik durumlarda ek olarak:

- login akisi
- ana dashboard yuklenmesi
- kritik API smoke

## Failure Handling

Rollback job basarisiz olursa:

1. Jenkins console output incelenir.
2. Hedef hostta `docker compose ps` kontrol edilir.
3. Hedef servis log'lari incelenir.
4. Registry'de ilgili tag var mi kontrol edilir.
5. Gerekirse bir onceki daha eski saglam tag denenir.

## Important Limits

- Bu rollback yalnizca image tag rollback yapar.
- DB downgrade otomatik yapilmaz.
- Secret rotation rollback kapsaminda degildir.
- `latest` ile rollback desteklenmez.

## Audit Trail

Rollback sonrasi Jenkins su artifact'i saklar:

- `reports/rollback-metadata.json`

Beklenen alanlar:

- `action`
- `target_env`
- `image_tag`
- `reason`
- `healthcheck_url`
- `skip_healthcheck`
- `job_name`
- `build_number`
- `build_url`
- `timestamp_utc`

## Recommended Operational Rule

Production rollback karari almadan once su soru sorulmali:

- Sorun image kaynakli mi, yoksa schema veya secret degisimi kaynakli mi?

Eger sorun schema veya secret tarafindaysa bu runbook tek basina yeterli degildir; manuel operasyon gerekir.
