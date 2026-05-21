# TestwrightAI — Son Kullanıcı Eksiklik Giderme Uygulama Planı

> Bu plan, [END_USER_GAPS_REPORT.md](END_USER_GAPS_REPORT.md) raporundaki
> 23 bulguyu uygulanabilir iş paketlerine böler. Faz 0/2/3 ve P1
> (runtime) tamamlandı; bu doküman geçmiş paketlerin kabul kriterlerini
> ve kalan follow-up'ları içerir.

---

## Faz ve paket özeti

| Faz | Süre | Paket | Durum |
|-----|------|-------|-------|
| **F0 — Durdurucu** | 1 hafta | P0-1..P0-5 | ✅ |
| **F1 — Gerçek akış** | 2-3 hafta | P1-1, P1-3, P1-4 | ✅ |
| **F2 — UI / dil** | 2 hafta | P2-1..P2-6 | ✅ |
| **F3 — Olgunluk** | 1 hafta | P3-1, P3-3, P3-4, P3-5 | ✅ |

---

## F0 — Durdurucu

### P0-1 · Sır varsayılanlarını üretimde zorunlu kıl

**Kabul kriterleri**
- `ENV=production|staging` + default sır → startup başarısız.
- `ENV=development` → warn ama devam eder.
- 4/4 ünite testi (`tests/unit/test_config_validation.py`).

**Dokunulan dosyalar**: `backend/app/config.py`, `.env.example`, CI workflow.

### P0-2 · Router kaydı tek kaynakta

**Kabul kriterleri**
- `register_api_routers(app)` tek çağrı; main.py'de duplike yok.
- `/api/v1/n8n/*` ve `/api/v1/cicd/*` OpenAPI'de.
- 6/6 entegrasyon testi.

**Dokunulan dosyalar**: `backend/app/core/router_registry.py`, `main.py`.

### P0-3 · Engine adresi + `/ready` sertleştirme

**Kabul kriterleri**
- `ENGINE_BASE_URL` env ile override edilebilir.
- Engine down → `/ready` 503 (escape hatch: `ENGINE_REQUIRED_FOR_READY=false`).

**Dokunulan dosyalar**: `backend/app/core/engine_client.py` (yeni), `tspm/test_runner_service.py`, `main.py`.

### P0-4 · Next.js middleware + rol kapısı

**Kabul kriterleri**
- Cookie'siz tarayıcı `/p/*` → `/login?next=...`.
- `role != admin` ile `/admin/*` → 403 Türkçe ekran.

**Dokunulan dosyalar**: `apps/web/middleware.ts` (yeni), `(dashboard)/admin/layout.tsx` (yeni), `lib/api-client.ts`.

### P0-5 · Login demo bilgileri env flag

**Kabul kriterleri**
- `next build` prod → login sayfasında hiçbir `admin123`/`test123` yok.
- CI check (`no-demo-creds-in-prod-build`).

---

## F1 — Gerçek Çalışma Akışı

### P1-1 · TSPM gerçek Playwright hattı

**Kabul kriterleri**
- `mode=simulation` (default): hash-tabanlı sahte sonuçlar, UI'da "Demo modu" rozeti.
- `mode=playwright`: scenario → `.feature` dosyası + pytest-bdd glue → pytest subprocess → Allure raporu.
- UI rozeti: demo modunda sarı, gerçek modunda yeşil.
- 7/7 ünite testi (`engine/tests/test_scenario_to_feature.py`).

**Yeni modüller**: `engine/core/scenario_to_feature.py`. Türkçe Gherkin keyword normalizasyonu (`verilen→Given`, `eğer→When`, `o zaman→Then`).

**Dokunulan**: `engine/routes/runner_routes.py` (`_run_playwright_worker` eklendi), `backend/app/domains/tspm/{schemas,router,test_runner_service}.py` (`mode` alanı), `apps/web/app/(dashboard)/p/[projectId]/executions/[runId]/page.tsx` (seçici + rozet).

### P1-3 · Şifre sıfırlama e-posta

**Kabul kriterleri**
- `POST /auth/forgot-password` → kullanıcıya Türkçe şablonlu mail (text+HTML).
- EMAIL_BACKEND: `console`/`memory`/`smtp` (pluggable).
- Rate limit (`3/minute` mevcut decorator).
- 5/5 ünite testi.

**Yeni modül**: `backend/app/services/email_service.py`.

### P1-4 · Engine subprocess timeout

**Kabul kriterleri**
- `RUN_TIMEOUT_S` (default 1800) sonunda pytest hâlâ ayakta → `proc.kill()`.
- Worker havuzu yeniden kullanılabilir (log dosya handle'ı kapanır).
- 3/3 ünite testi (kill/no-kill/stop).

---

## F2 — Kullanıcı Arayüzü

### P2-1 · Türkçe normalizasyonu

**Kabul kriterleri**
- `scripts/tr_normalize.py --check-only` 0 bulgu.
- Pre-commit hook aktif.
- Kelime sınırı (`(?<!\w)foo(?!\w)`) ile `onerror`-tipi regresyon önlendi.

### P2-2 · TR/EN karışık etiket tekilleştirme

**Kabul kriterleri**
- Sidebar tamamen Türkçe (marka adları hariç).

### P2-3 · CommandPalette kapsamı + a11y

**Kabul kriterleri**
- 45 sidebar segmenti palet araması üzerinden erişilebilir.
- `role=dialog`, `aria-modal`, `aria-activedescendant`, `Esc` kapat.

### P2-4 · ProjectSwitcher entegre + alt yol koruma

**Kabul kriterleri**
- Header pill dropdown'a "Diğer projelere geç" listesi eklendi.
- Proje değişince mevcut alt path korunuyor.

### P2-5 · Hata sınırı Türkçeleştirme

**Kabul kriterleri**
- Ham `error.message` asla kullanıcıya görünmez.
- "Detayları göster" / "Kopyala" butonları.
- `role="alert"` + `aria-live="assertive"`.

### P2-6 · "Beni hatırla"

**Kabul kriterleri**
- Checkbox → backend `remember_me: true` → 7 gün TTL.
- Default (unchecked) → 30 dk TTL (mevcut).

---

## F3 — Olgunluk

### P3-1 · CoverUp parser'ları

**Kabul kriterleri**
- cobertura XML, istanbul JSON, nyc summary doğru parse edilir.
- Malformed girdi → boş liste (router 400 döner).
- 6/6 ünite testi.

### P3-3 · a11y iyileştirmeleri

**Kabul kriterleri**
- `loading.tsx` `aria-busy`, `role=status`.
- `not-found.tsx` semantik `<main>` + heading.
- `<html lang="tr">` kök layout'ta.

### P3-4 · Repo hijyeni

**Kabul kriterleri**
- Kökte sadece `README.md`.
- `.gitignore` `*.pptx`, `*.db` filtreler.
- `docs/history/README.md` ile arşiv politikası yazılı.

### P3-5 · CI workflow

**Kabul kriterleri**
- Yeni workflow `end-user-gaps-checks.yml`:
  - Türkçe normalize check
  - Config + router + email + coverup tests
  - Engine timeout + scenario→feature tests
  - Demo creds leak check

---

## Takip (follow-up)

| # | Konu | Açıklama |
|---|------|----------|
| 1 | SMTP prod setup | Default `console` → `smtp` geçişi için throttling + rate limit + unsubscribe-header header |
| 2 | Step definition coverage | TSPM'den gelen bazı step text'leri engine/steps/ altında tanımlı değilse `undefined step` düşer; AI destekli step suggestion modülü (`engine/core/steps_suggester.py`) sonraki sprintde |
| 3 | Allure UI entegrasyonu | `mode=playwright` koşumu sonrasında UI'da dinamik "Allure raporunu aç" linki |
| 4 | ENGINE_SECRET_KEY override | `engine/app.py` hâlâ fallback'e sahip; prod'da zorunlu env |
| 5 | `/api/*` middleware allow-list | Next.js app router'daki API rotaları middleware'den muaf; iç inceleme gerekli |

---

## Sahiplik ve takip

Yeni eklenen CI workflow'lar PR gate'idir; herhangi biri kızarırsa merge engellenir.
Raporun güncel durumu için `git log --grep="fix(p0\|p1\|p2\|p3)" --since="2026-04-15"`
komutu kullanılabilir.
