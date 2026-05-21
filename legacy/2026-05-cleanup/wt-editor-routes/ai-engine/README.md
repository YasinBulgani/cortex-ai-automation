# @bgts/ai-engine

TypeScript yardımcıları: flaky analizi, BDD üretimi, veri fabrikası, healwright kurulumu vb. **CLI** üzerinden çalışır; `package.json` içindeki `npm run` script’lerine bakın.

## Bu monorepo içindeki yer

| Bileşen | Entegrasyon |
|--------|-------------|
| **TSPM web (Next.js)** | Doğrudan kullanılmaz; test üretimi ve analiz **Flask `engine/`** ve **FastAPI `backend/`** üzerinden yapılır. |
| **Flask engine** | Python tarafında AI/BDD ve Playwright akışı. |
| **Bu paket** | Deneysel veya CI’de çağrılan TS araçları; `npm run build` ile derlenir. |

Üretimde `apiFetch` + `/api/v1/automation/proxy/...` ile motoru çağırın; `apps/web/lib/api.ts` içindeki yorumlara bakın.

## Örnek

```bash
cd ai-engine
npm install
npm run analyze:anomalies
```

API anahtarları ve model seçimi için `src/config/ai-config.ts` (varsa) ve ortam değişkenlerini kullanın.
