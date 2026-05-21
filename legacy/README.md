# Legacy Archive

Bu dizin, aktif koddan ayrıştırılmış **tarihsel modülleri** içerir.

## Silme politikası

- Her alt dizin 6 aylık saklama süresiyle arşivlenir.
- Saklama bitince `git rm -rf` ile silinir; geçmiş git history'de kalır.
- Aşağıdaki tabloda "silme tarihi" geçen dizin o tarihten sonra silinir.

## 2026-04 Cleanup

Tarih: **2026-04-19**
Branch: `chore/architecture-cleanup-2026-04`
Silme tarihi: **2026-10-19** (6 ay)

| Modül | Eski yeri | Yerine ne var? | Gerekçe |
|---|---|---|---|
| `ai-engine/` | `<repo>/ai-engine/` | `backend/app/domains/ai/` + `engine/` | README'nin kendisi "deneysel / CI TS araçları" diyor. Kullanılmıyor. |
| `MaviYakaTestOtomasyon/` | `<repo>/MaviYakaTestOtomasyon/` | `frameworks/playwright-cucumber-ts/` | Eski Java/Maven Selenium projesi. Playwright'a geçildi. |
| `scaffolded_projects/` | `<repo>/scaffolded_projects/` | — | Test scaffold örnekleri, canlı kodda referans yok. |
| `backend-synthetic-data-v2/` | `backend/synthetic-data-v2/` | `backend/app/domains/ai_synthetic_data/` | v2 eski sürüm. |
| `backend-synthetic-data-v3/` | `backend/synthetic-data-v3/` | `backend/app/domains/ai_synthetic_data/` | v3 eski sürüm. |
| `backend-synthetic-data-bgtsflow/` | `backend/synthetic-data-bgtsflow/` | `backend/app/domains/ai_synthetic_data/` | BGTSFlow deneyi. |
| `synthetic-data-platform/` | `synthetic-data/platform/` | `synthetic-data/platform-v4/` (aktif) | Önceki platform sürümü. |
| `frameworks-selenium-cucumber-java/` | `frameworks/selenium-cucumber-java/` | `frameworks/playwright-cucumber-ts/` | Selenium/Java'dan Playwright/TS'e geçiş tamam. |
| `frameworks-Test_Template/` | `frameworks/Test_Template/` | `frameworks/playwright-cucumber-ts/` | Boilerplate, kullanılmıyor. |
| `synthetic-data-mostlyai-datasets/` | `synthetic-data/mostlyai-datasets/` | — | MostlyAI training/output artefaktları (parquet/pt/json). Canlı referans yok. |
| `synthetic-data-mostlyai-generators/` | `synthetic-data/mostlyai-generators/` | — | MostlyAI model artefaktları. 375 tracked file, hiçbiri kod değil. |
| `docs-test-otomasyon/content/` | `docs/test-otomasyon/` | `frameworks/playwright-cucumber-ts/` | 10 alt-proje (MaviYaka duplicate + 9 deneysel: MyProject, MyProject2, MySome, Mydeskop, TestAutomation, jkk, myContains, yasin1). 61 MB, 3965 dosya. `docs/dsl-consolidation-plan.md` bile "birebir duplikat" olarak işaretlemiş. |

## Ayrıca temizlenenler (arşiv değil, direkt silindi)

| Modül | Gerekçe |
|---|---|
| `otomasyon-ekibi/` | Sadece bir `venv/` klasörü vardı, git'te tracked dosya yoktu. |

## Doğrulama

Arşivleme öncesi her modül için şu kriterlerin hepsi sağlandı:

1. `rg -l` ile canlı kod referansı yok
2. `docker-compose*.yml` içinde servis tanımı yok
3. `Makefile`, `package.json`, `pyproject.toml`, `.github/workflows/` içinde build hedefi yok
4. README/docs referansları sadece tarihsel anlatımda

## Geri dönüş

Yanlışlıkla arşive alındığı düşünülen bir modül için:

```bash
git mv legacy/2026-04-cleanup/<modül> <eski-yol>
git commit -m "revert: restore <modül> — still live because ..."
```

## Silme zamanı geldiğinde

```bash
git rm -rf legacy/2026-04-cleanup/
git commit -m "chore: purge 2026-04 legacy archive (6 month retention expired)"
```
