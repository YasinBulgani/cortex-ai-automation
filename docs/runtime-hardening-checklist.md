# Runtime Hardening Checklist

Bu kontrol listesi production/staging ortami icin minimum guvenlik ve operasyonel gereksinimleri tanimlar.

## Zorunlu ayarlar

- `APP_ENV=production` veya `APP_ENV=staging` kullan.
- `JWT_SECRET` en az 64 karakter rastgele deger olmalı.
- `ENGINE_INTERNAL_KEY` varsayilan olmamali ve en az 32 karakter olmali.
- `DATABASE_URL` placeholder/development kimlik bilgileri icermemeli.
- `GITHUB_WEBHOOK_SECRET` bos olmamali (veya `CICD_REQUIRE_WEBHOOK_SECRETS=1` zorunlu tutulmali).

## Rate limit ve abuse korumasi

- `slowapi` paketi image icinde kurulu olmali.
- `RATE_LIMIT_REQUIRED=1` ayari production image'larinda aktif olmali.
- `REDIS_URL` coklu instance topolojisinde ortak bir Redis noktasina isaret etmeli.

## API yuzeyi

- FastAPI docs endpointleri (`/docs`, `/redoc`, `/openapi.json`) production'da kapali olmali.
- `automation/proxy` ve CI/CD operasyon endpointleri sadece authenticated kullanicilara acik olmali.
- AI gateway `X-Internal-Key` header zorunlulugu ile internal networkte sinirlanmali.

## Gozlemlenebilirlik

- Uygulama loglarinda token veya key parcalari loglanmamali.
- Runtime startup loglarinda rate limiter aktif/pasif durumu gorunur olmali.
- Hata metrikleri (Sentry/Prometheus) production'da dogrulanmali.

## CI dogrulama

- Backend security testleri CI'da zorunlu gate olarak calismali.
- E2E testleri tek `API_BASE` kaynagini kullanmali.
- `ai-gateway` testleri ana CI pipeline icine dahil edilmeli.
