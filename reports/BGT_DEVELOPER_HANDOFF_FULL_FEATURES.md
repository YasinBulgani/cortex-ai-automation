# BGT / BGTS — Geliştirici devreye alma (tam özellik çerçevesi)

Bu dosya [`PROGRESS.md`](../PROGRESS.md) ile birlikte **atanan geliştirici** için giriş noktasıdır. Ayrıntılı tamamlanma geçmişi `PROGRESS.md` içindedir; burada mimari harita, öncelik çerçevesi ve test beklentileri özetlenir.

---

## 1. Mimari harita (monorepo)

| Katman | Dizin | Rol |
|--------|--------|-----|
| Web | `apps/web/` | Next.js 14, `apiFetch` → FastAPI |
| API | `backend/` | FastAPI, TSPM domain, JWT, proxy → engine |
| Motor | `engine/` | Flask, Playwright, pytest-bdd, BDD özellikleri |
| E2E (TS) | `e2e/` | Playwright, page object’ler, `playwright.config.ts` |
| AI CLI | `ai-engine/` | TypeScript yardımcı araçlar (web’den bağımsız akışlar) |

**Veri akışı (özet):** Tarayıcı → Next.js → FastAPI → (gerektiğinde) engine URL / proxy. Detay: [`README.md`](../README.md) diyagramı ve [`docs/product.md`](../docs/product.md) (varsa).

---

## 2. P0–P3 öncelik çerçevesi

Repoda sabit bir “ürün backlog” tablosu yerine **test/otomasyon öncelikleri** şu dokümanlarda tanımlıdır:

| Öncelik | Tipik içerik | Kaynak |
|---------|----------------|--------|
| **P0** | Smoke, kritik API/E2E, RBAC, sözleşme testleri | `docs/AI_TEST_OTOMASYON_RAPORU.md`, `qa/test-design/`, pytest marker `@pytest.mark.P0` |
| **P1** | Regresyon, güvenlik/performans genişlemesi, ek tarayıcı | Aynı + `docs/test-platform-guide.md` |
| **P2** | Mobil/responsive, ek entegrasyonlar | `docs/AI_TEST_OTOMASYON_RAPORU.md`, `docs/synthetic-data-research.md` |
| **P3** | İyileştirme / nice-to-have | Marker kullanımı ile `engine` / `backend` testlerinde |

**Çalıştırma:** `pytest -m P0` vb. — ayrıntı: `docs/test-platform-guide.md`.

> **Not:** Ürün ekibinin sprint backlog’u buraya taşınmadıysa, P0–P3 maddeleri `PROGRESS.md` veya proje yönetim aracındaki liste ile eşlenmelidir.

---

## 3. Kabul kriterleri (genel)

- **API değişikliği:** İlgili router + şema; mümkünse `backend/tests` veya contract testleri.
- **UI değişikliği:** `data-testid` ([`.cursor/rules/data-testid-convention.mdc`](../.cursor/rules/data-testid-convention.mdc)); ilgili `e2e/*.spec.ts` veya yeni spec.
- **Motor / BDD:** `engine/features/`, step’ler ve `engine/pages/` page object ile uyum.
- **Kırıcı değişiklik:** README veya `.env.example` güncellemesi; migration gerekiyorsa Alembic notu.

---

## 4. Test beklentileri

| Tür | Konum / tetikleyici |
|-----|---------------------|
| Lint / tip | CI: `.github/workflows/ci.yml` |
| Playwright E2E | `e2e/`, projeler: `smoke`, `regression`, vb. — `playwright.config.ts` |
| pytest | `backend/tests`, `engine/tests`; marker’lar `smoke`, `P0`–`P3` |
| BDD | `engine/` içi pytest-bdd |

**Yerel özet komutlar:** [`README.md`](../README.md) “Test” bölümü.

---

## 5. Cursor / agent kuralları

- **Araştırma önceliği:** [`.cursor/rules/agent-research-first.mdc`](../.cursor/rules/agent-research-first.mdc) (always on).
- **Page Object:** [`.cursor/rules/page-object-pattern.mdc`](../.cursor/rules/page-object-pattern.mdc).
- **Sidebar Test Verisi / Otomasyon:** [`.cursor/rules/sidebar-test-data-otomasyon.mdc`](../.cursor/rules/sidebar-test-data-otomasyon.mdc).

---

## 6. Bilinen teknik borç / kontrol listesi (kısa)

- CI’da birden fazla workflow (`ci.yml`, `bgts-e2e.yml`, …) farklı servis varsayımları kullanabilir; değişiklik öncesi ilgili YAML’ı okuyun.
- `PROGRESS.md` “Post-MVP” bölümü tamamlanan adımları listeler; yeni iş için bu dosya + yukarıdaki P0–P3 kaynakları birlikte kullanılmalıdır.

---

**Son güncelleme:** 2026-04-04 — dosya `PROGRESS.md` içindeki kopuk bağlantıyı gidermek için eklendi; içerik repo dokümanlarına referans verir, sprint backlog’u türetmez.
