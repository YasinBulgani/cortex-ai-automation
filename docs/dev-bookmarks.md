# Dev Bookmarks — açık tarayıcı sekmeleri

IntelliJ'de `Ctrl+Shift+A` → "Open in Browser" veya bookmark bar'a ekle.

## Web uygulamaları

| URL | Ne | Komut |
|---|---|---|
| http://localhost:3000 | Neurex web (Next.js) | `npm run web:dev` veya **Run "Neurex - Web (Next.js dev)"** |
| http://localhost:3000/products/intelligence | Intelligence product sayfası | (üstteki dev server) |
| http://localhost:3000/products/one | One product sayfası | |
| http://localhost:3000/products/data | Data product sayfası | |
| http://localhost:3000/products/web | Web product sayfası | |
| http://localhost:3000/products/mobile | Mobile product sayfası | |
| http://localhost:3000/products/service | Service product sayfası | |
| http://localhost:3000/products/studio | Studio product sayfası | |
| http://localhost:3000/products/nexus-code | Nexus Code product sayfası | |
| http://localhost:5001 | **Cortex Dashboard** | `make cortex-dashboard` |
| http://localhost:6006 | Storybook | `npm run storybook` |

## API endpoint'leri

| URL | Ne | Komut |
|---|---|---|
| http://localhost:8000/docs | Backend FastAPI Swagger | `make nexusqa-dev` |
| http://localhost:8000/redoc | Backend ReDoc | |
| http://localhost:8080/docs | AI Gateway Swagger | `make gateway-dev` |
| http://localhost:5000 | Engine Flask | `cd engine && python app.py` |

## Observability

| URL | Ne | Komut |
|---|---|---|
| http://localhost:3001 | **Grafana** dashboard | **Run "Docker - Observability"** |
| http://localhost:9090 | Prometheus | (üstteki) |
| http://localhost:3200 | Tempo (traces) | (üstteki) |
| http://localhost:3100 | Loki (logs) | (üstteki) |
| http://localhost:13133 | OTel collector health | (üstteki) |

## Test raporları (build sonrası)

| URL/Path | Ne | Komut |
|---|---|---|
| `frameworks/cortex-java/target/cucumber-report.html` | Cortex Cucumber HTML | `make cortex-smoke` sonrası |
| `frameworks/cortex-java/target/allure-results/` | Cortex Allure raw | `make cortex-report` (interactive UI) |
| `reports/e2e-html/index.html` | Playwright TS HTML | `npm run test:e2e` sonrası |

## AuthLess dev mode

Login olmadan sayfaları görmek için (zaten ayarlı):
```bash
# apps/web/.env.local
NEXT_PUBLIC_AUTH_MIDDLEWARE_ENABLED=false
```

## Cortex test ortamı

| URL | Notlar |
|---|---|
| https://cortex-test.bgtsai.com/ | Cortex test ortamı (testlerin koştuğu yer) |
| https://cortex-test.bgtsai.com/login | Login sayfası |
