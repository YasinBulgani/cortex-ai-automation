# BGTS Deployment Operations Guide

Version: 2.1  
Last Updated: 2026-04-16  
Audience: DevOps / SRE

## Deployment Model

Production ve staging dagitimi GitHub Actions uzerinden SSH + Docker Compose modeliyle yapilir.

- Workflow: `.github/workflows/deploy.yml`
- Runtime manifest: `docker-compose.prod.yml`
- Reverse proxy / TLS: `infra/nginx.prod.conf`, `infra/ssl/`
- Gozlemlenebilirlik: `infra/prometheus.yml`, `infra/grafana/`
- Alert rules: `infra/prometheus/rules/bgts-alerts.yml`
- Alert routing: `infra/alertmanager/alertmanager.noop.yml`

Deploy edilen container image'lari:

- `ghcr.io/<owner>/<repo>-backend:<sha>`
- `ghcr.io/<owner>/<repo>-engine:<sha>`
- `ghcr.io/<owner>/<repo>-web:<sha>`
- `ghcr.io/<owner>/<repo>-ai-gateway:<sha>`

## Pre-Deployment Checklist

1. `main` branch'inde deploy edilecek commit CI'dan gecmis olmali.
2. Hedef sunucuda `docker`, `docker compose` ve GHCR erisimi calisiyor olmali.
3. Hedef dizinde guncel `docker-compose.prod.yml`, `.env` ve `infra/ssl/` sertifikalari bulunmali.
4. `.env` icindeki kritik alanlar bos olmamali:
   - `APP_ENV=staging` veya `APP_ENV=production`
   - `JWT_SECRET`
   - `ENGINE_INTERNAL_KEY`
   - `ENGINE_SECRET_KEY`
   - `GATEWAY_INTERNAL_KEY`
   - `POSTGRES_PASSWORD`
   - `GRAFANA_ADMIN_PASSWORD`
   - Gerekli ise `ALERTMANAGER_WEBHOOK_URL`
5. `NEXT_PUBLIC_ENGINE_BASE` degeri browser tarafini backend proxy'ye yonlendirmeli:
   - onerilen: `/api/v1/automation/proxy`
6. `docker-compose.prod.yml` backend ve engine servislerine `APP_ENV` gectiginden emin olun.

## Runtime ve Dependency Governance

Bu runbook deployment tarafindaki zorunlu surum kontratlarinin tek kaynagidir.

| Alan | Beklenen |
|------|----------|
| Python runtime | `3.12` |
| Node runtime | `20.x` |
| PostgreSQL | `16` |
| Redis | `7` |

Release gate notlari:

1. Runtime guncellemeleri Dockerfile + CI + compose dosyalarinda birlikte yapilmalidir.
2. Dependency guncellemesi iceren PR'larda ilgili servis testleri ve `runtime-contracts` CI isi yesil olmadan deploy yapilmaz.
3. Haftalik otomatik dependency PR akisi `.github/dependabot.yml` ile yonetilir.
4. Security advisory (high/critical) iceren paketler normal sprint beklemeden hotfix penceresine alinmalidir.

## Secret Rotation Runbook

Bu bolum staging/production ortaminda uygulama secret'larini kontrollu sekilde dondurmek icindir.

Kapsamdaki kritikler:

- `JWT_SECRET`
- `ENGINE_INTERNAL_KEY`
- `ENGINE_SECRET_KEY`
- `GATEWAY_INTERNAL_KEY`
- `POSTGRES_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`
- Varsa `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `SENTRY_DSN`

### 1. Yeni degerleri uret

Mac/Linux:

```bash
openssl rand -base64 64    # JWT_SECRET
openssl rand -hex 32       # ENGINE_INTERNAL_KEY / ENGINE_SECRET_KEY / GATEWAY_INTERNAL_KEY
openssl rand -base64 32    # POSTGRES_PASSWORD / GRAFANA_ADMIN_PASSWORD
```

### 2. Once staging'de uygula

Hedef sunucudaki `.env` dosyasinda en az su alanlari guncelle:

```env
APP_ENV=staging
JWT_SECRET=<new-jwt-secret>
ENGINE_INTERNAL_KEY=<new-engine-internal-key>
ENGINE_SECRET_KEY=<new-engine-secret-key>
GATEWAY_INTERNAL_KEY=<new-gateway-internal-key>
POSTGRES_PASSWORD=<new-postgres-password>
GRAFANA_ADMIN_PASSWORD=<new-grafana-password>
```

Notlar:

- `APP_ENV` staging/production degilse backend ve engine development fallback'lerine donebilir; bu kabul edilmemelidir.
- `JWT_SECRET` rotasyonu mevcut access/refresh token'lari gecersiz kilacaktir; planli pencere ayarlayin.
- `ENGINE_INTERNAL_KEY` ve `GATEWAY_INTERNAL_KEY` backend, engine ve ai-gateway arasinda ayni anda guncellenmelidir.

### 3. PostgreSQL sifresini canli sistemde degistir

Mevcut container ayaktayken once veritabani kullanicisinin sifresini degistirin:

```bash
cd "$DEPLOY_PATH"
export NEW_POSTGRES_PASSWORD='<new-postgres-password>'
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres \
  -c "ALTER USER $POSTGRES_USER WITH PASSWORD '$NEW_POSTGRES_PASSWORD';"
```

Sonra `.env` icindeki `POSTGRES_PASSWORD` ve `DATABASE_URL` degerlerini yeni sifreyle guncelleyin.

### 4. Uygulama servislerini yeniden olustur

```bash
cd "$DEPLOY_PATH"
docker compose -f docker-compose.prod.yml up -d --force-recreate backend worker engine ai-gateway web
```

Gerekirse image guncellemesi ile birlikte:

```bash
cd "$DEPLOY_PATH"
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml pull backend worker engine web ai-gateway
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml up -d --force-recreate backend worker engine ai-gateway web
```

### 5. Dogrulama

```bash
cd "$DEPLOY_PATH"
docker compose -f docker-compose.prod.yml ps
curl --fail --silent --show-error "https://$HOST/health"
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml logs --tail=100 engine
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -c '\conninfo'
```

Beklenenler:

- `backend`, `worker`, `engine`, `ai-gateway`, `web` ayakta olmali
- `/health` basarili donmeli
- Backend log'larinda `JWT_SECRET` veya `DATABASE_URL` validation hatasi olmamali
- Engine log'larinda `ENGINE_SECRET_KEY zorunlu` benzeri hata olmamali

### 6. Production'a promote et

Staging dogrulandiktan sonra ayni adimlari production `.env` icin tekrarlayin:

```env
APP_ENV=production
...
```

### 7. Rollback sinirlari

- `JWT_SECRET` rotasyonu geri alinirsa sadece eski secret'a imzali token'lar tekrar gecerli olur; bu istenmiyorsa rollback'te eski secret'a donmeyin.
- `POSTGRES_PASSWORD` rollback'i sadece hem PostgreSQL kullanicisi hem `.env` birlikte geri alinirse calisir.
- `ENGINE_INTERNAL_KEY` ve `GATEWAY_INTERNAL_KEY` mismatch olursa backend-engine veya backend-ai-gateway cagrilari 401/403 verebilir.

## Staging Deployment

GitHub Actions staging asamasi sunucuda su akisi uygular:

```bash
cd "$DEPLOY_PATH"
docker compose -f docker-compose.prod.yml up -d postgres redis
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml pull backend worker engine web ai-gateway
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml run --rm -e SKIP_APP_BOOTSTRAP=1 backend alembic upgrade head
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml run --rm -e SKIP_APP_BOOTSTRAP=1 backend python -c 'from app.config import settings; assert settings.is_production_like'
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

Staging health check:

```bash
curl --fail --silent --show-error "https://$STAGING_HOST/health"
```

Beklenen yanit:

```json
{"status":"ok","service":"bgts-backend"}
```

## Production Deployment

Production asamasi staging sonrasinda ayni compose modeliyle ilerler:

```bash
cd "$DEPLOY_PATH"
docker compose -f docker-compose.prod.yml up -d postgres redis
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml pull backend worker engine web ai-gateway
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml run --rm -e SKIP_APP_BOOTSTRAP=1 backend alembic upgrade head
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml run --rm -e SKIP_APP_BOOTSTRAP=1 backend python -c 'from app.config import settings; assert settings.is_production_like'
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG="$GITHUB_SHA" docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

Post-deploy dogrulama:

```bash
docker compose -f docker-compose.prod.yml ps
curl --fail --silent --show-error "https://$PROD_HOST/health"
docker compose -f docker-compose.prod.yml exec backend sh -lc 'curl -sf http://127.0.0.1:8000/metrics | head -20'
docker compose -f docker-compose.prod.yml exec engine sh -lc 'curl -sf http://127.0.0.1:5001/metrics | head -20'
docker compose -f docker-compose.prod.yml exec ai-gateway sh -lc 'curl -sf http://127.0.0.1:8080/metrics | head -20'
docker compose -f docker-compose.prod.yml exec prometheus wget -qO- http://127.0.0.1:9090/api/v1/rules | head -40
docker compose -f docker-compose.prod.yml exec prometheus wget -qO- http://127.0.0.1:9090/api/v1/alerts | head -40
docker compose -f docker-compose.prod.yml logs --tail=50 alertmanager
```

## Runtime Checks

Genel durum:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml logs --tail=100 engine
docker compose -f docker-compose.prod.yml logs --tail=100 web
docker compose -f docker-compose.prod.yml logs --tail=100 ai-gateway
```

Prometheus scrape kontrolu:

```bash
docker compose -f docker-compose.prod.yml exec prometheus wget -qO- http://127.0.0.1:9090/api/v1/targets
```

Exporter kontrolu:

```bash
docker compose -f docker-compose.prod.yml exec prometheus wget -qO- http://127.0.0.1:9090/api/v1/targets | grep -E 'postgres|redis|nginx'
docker compose -f docker-compose.prod.yml logs --tail=50 postgres-exporter
docker compose -f docker-compose.prod.yml logs --tail=50 redis-exporter
docker compose -f docker-compose.prod.yml logs --tail=50 nginx-exporter
docker compose -f docker-compose.prod.yml logs --tail=50 alertmanager
```

Redis healthcheck dogrulamasi:

```bash
docker compose -f docker-compose.prod.yml exec redis sh -lc 'redis-cli -a "$REDIS_PASSWORD" ping'
```

## Rollback

Bu repo image-tag tabanli rollout kullandigi icin rollback de bir onceki saglam image tag ile yapilmalidir.

Jenkins kullanan kurulumlarda onerilen job:

- `bgts-rollback`
- script path: `jenkins/Jenkinsfile.rollback`
- detayli operasyon adimlari: `docs/jenkins-rollback-runbook.md`

1. Onceki saglam SHA'yi belirle.
2. Sunucuda `IMAGE_TAG` ortam degiskenini o SHA ile export et.
3. Ayni compose akisini tekrar calistir.

```bash
export IMAGE_TAG=<previous-good-sha>
export GITHUB_REPOSITORY=<owner/repo>
GITHUB_REPOSITORY=<owner/repo> docker compose -f docker-compose.prod.yml pull backend worker engine web ai-gateway
GITHUB_REPOSITORY=<owner/repo> docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

Gerekirse migration geri alma manuel planlanmalidir; workflow otomatik downgrade yapmaz.

Notlar:

- `latest` ile rollback yapmayin.
- Rollback image tag tabanlidir; secret veya schema rollback kapsamaz.
- Production rollback sonrasinda health check ve kritik akis dogrulamasi yapin.

## Incident Notes

- Browser tarafinda engine cagrilari dogrudan hosta gitmez; `NEXT_PUBLIC_ENGINE_BASE` backend proxy'yi gostermelidir.
- Engine veya AI Gateway metrikleri bos donuyorsa once ilgili container icinde `/metrics` endpoint'ini kontrol edin.
- Prometheus kurallari yuklense bile harici bildirim kanali (Alertmanager / webhook / email) ayrica baglanmadikca alarmlar yalnizca Prometheus/Grafana uzerinde gorunur.
- `ALERTMANAGER_WEBHOOK_URL` bos ise Alertmanager blackhole/no-op modunda calisir; bu durum test ortaminda kabul edilebilir, production icin genellikle istenmez.
- Yetkisiz engine istekleri gorulurse ilk bakilacak alanlar `ENGINE_INTERNAL_KEY` ve public endpoint politikalaridir.
- `/docs` ve `/grafana/` endpoint'leri varsayilan olarak sadece localhost/VPN-ozel IP araliklarina aciktir.
- `/alertmanager/` endpoint'i de ayni sekilde private IP/localhost erisimiyle kisitlidir.
- Uygulama container'lari outbound servis cagrilari yapabildigi icin internet erisimi gerektiren LLM/Sentry trafiklerinin ayrıca firewall seviyesinde izlenmesi onerilir.
