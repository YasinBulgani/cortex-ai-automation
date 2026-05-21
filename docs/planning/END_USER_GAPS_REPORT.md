# TestwrightAI — Son Kullanıcı Eksiklik Raporu (2026-04)

> Bu doküman, platformu gerçek bir son kullanıcı (QA uzmanı, banka ekibi,
> proje yöneticisi) gibi kullanan birinin karşılaşacağı somut boşlukları
> kategorize eder. Rapor, ilk tespitler + uygulamaya geçirilen paketler +
> kalan işler şeklindedir. Detaylı uygulama planı için:
> [END_USER_GAPS_PLAN.md](END_USER_GAPS_PLAN.md).

Son güncelleme: 2026-04-19. Branch: `chore/architecture-cleanup-2026-04`.

---

## Kategoriler ve İzlenebilirlik

| # | Kategori | Toplam bulgu | Giderilen | Kalan |
|---|----------|--------------|-----------|-------|
| 1 | Kritik güvenlik / konfigürasyon | 5 | 5 | 0 |
| 2 | Kırık / stub işlevsellik | 4 | 4 | 0 |
| 3 | UI / Türkçe dil deneyimi | 6 | 6 | 0 |
| 4 | Erişilebilirlik (a11y) | 3 | 3 | 0 |
| 5 | Repo / dokümantasyon hijyeni | 2 | 2 | 0 |
| 6 | Uçtan uca koşum (TSPM) | 3 | 3 | 0 |
| **Toplam** | | **23** | **23** | **0** |

---

## 1. Kritik Güvenlik / Konfigürasyon

| Bulgu | Kanıt | Durum |
|-------|-------|-------|
| `JWT_SECRET`, `ENGINE_INTERNAL_KEY`, `GATEWAY_INTERNAL_KEY` için varsayılan "change-me" string'leri | `backend/app/config.py` | ✅ `Settings._validate_secrets` prod'da `ValueError` fırlatıyor |
| Next.js `middleware.ts` yoktu — URL ile korumalı sayfalara doğrudan erişim | `apps/web/middleware.ts` (yoktu) | ✅ Edge middleware + `twai_session` cookie |
| Login ekranında sabit demo hesapları (`admin123`, `test123`) | `apps/web/app/login/page.tsx:434-442` | ✅ Artık çift koşullu flag arkasında (`NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS`) |
| `PermissionGate` bileşeni hiçbir yerde kullanılmıyor → rol kapısı yok | `apps/web/components/PermissionGate.tsx` | ✅ `/admin/*` layout'unda 403 Türkçe ekran |
| `engine/app.py` `X-Internal-Key` bilinen string olursa session bypass | `engine/app.py:44-78` | ⚠ Üretim env'da zorunlu override (doc güncellendi, kod warn) |

## 2. Kırık / Stub İşlevsellik

| Bulgu | Kanıt | Durum |
|-------|-------|-------|
| `n8n` ve `cicd` router'ları FastAPI'ye bağlanmamış | `backend/app/main.py` (eski) | ✅ `router_registry.py` tek kaynak + 6 entegrasyon testi |
| `ENGINE_BASE` sabit `127.0.0.1:5001` → docker/k8s'te koşum kopar | `tspm/test_runner_service.py:38` | ✅ `settings.engine_base_url` + `core/engine_client.py` |
| `/ready` engine kapalıyken de 200 → sahte "hazır" | `backend/app/main.py:252` | ✅ 503 + `ENGINE_REQUIRED_FOR_READY` escape hatch |
| CoverUp `istanbul`/`cobertura`/`nyc` parser'ları `return []` | `coverup/router.py:100-111` | ✅ `coverup/parsers.py` + 6 ünite testi |

## 3. UI / Türkçe Dil Deneyimi

| Bulgu | Kanıt | Durum |
|-------|-------|-------|
| ASCII Türkçe (ör. `Kirik`, `baglanti`, `Cozumle`, `adim`) | 56 dosya | ✅ `scripts/tr_normalize.py` + pre-commit hook; 395 satır düzeltildi |
| TR/EN karışık sidebar ("Page Objects", "Chain Builder", "Self-Healing", "Monkey Test", "Advanced") | `components/AppShell.tsx` | ✅ Tümü Türkçeleştirildi ("Sayfa Nesneleri", "Zincir Oluşturucu" vb.) |
| Backend İngilizce hata mesajları (`sample_data is required`) | `ai_synthetic_data/router.py:51` | ✅ Türkçeleştirildi |
| Hata sınırlarında ham `error.message` ekrana basılıyordu | `ErrorBoundary.tsx`, `error.tsx` | ✅ `lib/errors.ts` `friendlyError()` + "Detayları göster"/"Kopyala" |
| `CommandPalette` yalnızca 10 segment tanıyor (45+ sayfa var) | `CommandPalette.tsx:31` | ✅ Tüm segmentler + role=dialog/listbox ARIA |
| `ProjectSwitcher` kullanılmıyor; proje değişimi alt yolu koruyor mu? | `components/ProjectSwitcher.tsx` | ✅ Header pill dropdown entegre; alt yol korunuyor |

## 4. Erişilebilirlik (a11y)

| Bulgu | Durum |
|-------|-------|
| `loading.tsx` dosyalarında `aria-busy`/`aria-live` yok | ✅ Eklendi |
| `not-found.tsx` semantik `<main>` + heading eksik | ✅ `<main>`, `<h1>`, `aria-labelledby` |
| `CommandPalette` `role=dialog` / focus trap yok | ✅ `role=dialog`, `aria-modal`, `aria-activedescendant` |

## 5. Repo / Dokümantasyon Hijyeni

| Bulgu | Durum |
|-------|-------|
| Kökte 14 eski doküman + 2 duplike `.pptx` | ✅ `docs/history/`'e taşındı, duplike silindi |
| `.gitignore` `*.pptx` ve eski test `.db` dosyalarını hariç tutmuyor | ✅ Eklendi |

## 6. Uçtan Uca Koşum (TSPM)

| Bulgu | Kanıt | Durum |
|-------|-------|-------|
| TSPM "Koş" butonu gerçek Playwright yerine hash-tabanlı simülasyon | `engine/routes/runner_routes.py:48` | ✅ `mode=simulation\|playwright` + UI rozeti + scenario→.feature üretici |
| Engine subprocess timeout yok → pytest takılırsa kuyruk kilitli | `engine/routes/runner_routes.py:124` | ✅ `_spawn_timeout_watchdog` + `RUN_TIMEOUT_S` + 3 ünite testi |
| Şifre sıfırlama e-posta entegrasyonu `TODO` | `auth/router.py:211` | ✅ `app/services/email_service.py` (console/memory/smtp) + Türkçe şablon |

---

## Commit izleri

| Commit | Kapsam |
|--------|--------|
| `c07dca3` | Faz 0 — güvenlik/router/middleware/demo-creds |
| `62e2599` | Faz 2 — TR normalize + UI/nav + hata deneyimi |
| `e546aee` | Faz 3 — a11y + repo hijyeni |
| `b0cc072` | P1 — engine timeout + e-posta servisi |
| `f2662d3` | tr_normalize regresyon düzeltmesi + TSPM run-mode UI rozeti |
| `fced763` | CoverUp istanbul/cobertura/nyc parser'ları |
| (bu commit) | scenario→feature üretici + CI workflow + dokümantasyon |

---

## Test kapsamı (yeni eklenen)

| Test dosyası | Count | Kapsam |
|--------------|-------|--------|
| `backend/tests/unit/test_config_validation.py` | 4 | Prod'da default sırlar reddediliyor |
| `backend/tests/integration/test_router_registration.py` | 6 | `n8n`/`cicd`/`tspm`/`auth`/`dsl` prefix'leri OpenAPI'de |
| `backend/tests/unit/test_email_service.py` | 5 | Şifre reset mail + exception yutma |
| `backend/tests/unit/test_coverup_parsers.py` | 6 | cobertura/istanbul/nyc doğru parse |
| `engine/tests/test_runner_timeout.py` | 3 | Watchdog kill/no-kill/stop |
| `engine/tests/test_scenario_to_feature.py` | 7 | Gherkin üretim + keyword normalizasyon |
| **Toplam** | **31** | Tamamı yeşil |

## CI koruması

Yeni workflow: `.github/workflows/end-user-gaps-checks.yml`.

| İş | Engeller |
|-----|---------|
| `turkish-normalization` | ASCII Türkçe regresyon |
| `security-and-routing` | Sır sızma + router unutma |
| `engine-runtime-hardening` | Timeout watchdog + feature üretici regresyon |
| `no-demo-creds-in-prod-build` | Login sayfasında flag korumasının kaldırılması |

---

## Takip edilmesi gerekenler (follow-up)

1. **SMTP üretim konfigürasyonu**: Şu an default `EMAIL_BACKEND=console`. Üretim geçişinde `smtp` + SMTP credentials + throttling izlenmeli.
2. **`mode=playwright` step coverage**: Üretilen `.feature` dosyası engine'deki step definitions ile eşleşmezse test `undefined step` ile düşer. DSL katalog senkronizasyonu (mevcut pre-commit hook'u) sayesinde çoğu adım zaten tanımlı; sık-olmayan adımlar için step generator sprint'i ileride gerekebilir.
3. **Middleware whitelist**: `/api/*` Next.js API rotalarını (varsa) detaylı filtrelemek gerekebilir.
4. **Upload endpoint PII tarama**: Yüklenen PDF/DOCX içeriği `synthetic-data` PII scanner'ından geçirilerek hassas veri kaydedilmemeli (şu an ham olarak diske yazılıyor).

## Uygulanan follow-up paketler (2026-04-20)

| Paket | Etki |
|-------|------|
| `sifir-bilgi` dosya yükleme tamamlandı | "Yakında" mesajı kaldırıldı, drag-drop UI, `POST /api/v1/agents/v2/upload` |
| **Upload auth + rate limit** | JWT zorunlu + 10/minute limit + UUID rename + 20 MB cap + uzantı whitelist + 5 ünite testi |
| Engine internal-key prod zorunluluğu | `APP_ENV=production` + default sır → `RuntimeError`; 3 ünite testi |
| UI Allure link rozeti | Playwright koşumu biter bitmez sağ üstte "📊 Allure raporu" pill'i |
| Axe-core e2e a11y projesi | `playwright.config.ts` `a11y` projesi + `e2e/accessibility.spec.ts` (graceful skip) |
| TR normalize kapsamı | Sözlük ~60 giriş; frontend 231 + backend 823 ek düzeltme; kelime sınırı `onerror` regresyonunu engeller; CI backend'i de tarar |
| SectionCard `subtitle` desteği | ai-quality dashboard 6 TS hatası kapandı |
