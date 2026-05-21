# Depo envanteri ve kopya analizi

Bu belge depo birleştirme planı kapsamında üretilmiştir: hangi dizinlerin **kanonik ürün kodu** olduğu, tekrarların durumu ve `diff` özeti.

## 1. Kapsam kilidi (single source of truth)

Bu doküman, planlanan `coreOnly` kapsamını kilitlemek için kullanılacaktır.
`README.md` içindeki modül haritası bu dosyayı referans alır; kanonik kapsam kararı burada tutulur.

| Kategori | Dizin | Amaç | CoreOnly kapsamında değişiklik izni |
|----------|-------|------|-------------------------------------|
| Core (Ana) | `apps/web/` | Next.js 14 dashboard | ✅ Evet |
| Core (Ana) | `backend/` | FastAPI API ve domain servisleri | ✅ Evet |
| Core (Ana) | `engine/` | Playwright + Flask otomasyon motoru | ✅ Evet |
| Core (Ana) | `e2e/` | Playwright e2e testleri | ✅ Evet |
| Core (Ana) | `api-tests/` | API entegrasyon testleri | ✅ Evet |
| Core (Ana) | `ai-gateway/` | AI yönlendirme ve model gateway'i | ✅ Evet |
| Çekirdek dışında, destek | `ai-engine/` | TypeScript AI CLI yardımcıları | ⛔ Hayır (referans / planlama yalnızca) |
| Legacy | `NexusQATestOtomasyon/` | Eski Java/Selenium otomasyon | ⛔ Hayır |
| Legacy | `frameworks/` | Eski framework ve şablonlar | ⛔ Hayır |
| Legacy | `ai-test-pipeline/` | Eski AI otomasyon pipeline | ⛔ Hayır |
| Legacy | `ai-test-automation/` | Eski AI otomasyon kütüphanesi | ⛔ Hayır |
| Legacy | `backend/synthetic-data-v2/` | Eski synthetic data implementasyonu | ⛔ Hayır |
| Legacy | `backend/synthetic-data-v3/` | Eski synthetic data implementasyonu | ⛔ Hayır |
| Legacy | `backend/synthetic-data-bgtsflow/` | Eski BGTSFlow versiyonu | ⛔ Hayır |

`coreOnly` kapsamı, yalnızca yukarıdaki "Core (Ana)" ve destek test akışları olan `api-tests/` altında yapılan değişikliklere izin verir; diğer satırlardaki dizinlere doğrudan patch uygulanmaz.

`synthetic-data/platform-v4/` ve `frameworks/playwright-cucumber-ts/` yalnızca referans ve geçmiş karşılaştırma amaçlı tutulur; canlı değişiklik hedefi olarak ele alınmaz.

**Sonuç:** Yeni özellik ve düzeltmeler için yalnızca bu ağaçlar kullanılmalıdır.

## 2. `repo-*` ve `bgt-agent-*` klasörleri

Bu checkout’ta kökte **`repo-api`, `repo-merge`, `bgt-agent-*` dizinleri yoktur** (bazı geliştirici makinelerinde geçmişte oluşturulmuş kopya ağaçlar olabilir).

Eğer tekrar görülürse:

- İçerik tipik olarak `test-automation/` + `ai_synthetic_data/` alt kopyalarıdır.
- **Kanonik kaynak** her zaman `engine/` ve `backend/` olmalıdır.
- Kaldırmadan önce: `diff -rq engine/ai_synthetic_data <kopya>/ai_synthetic_data` ile fark kontrolü yapın; fark yoksa veya sadece eski snapshot ise silinebilir veya `tools/agent-snapshots/README.md` yönergelerine uygun arşivlenir.

## 3. `diff` özeti: `engine/ai_synthetic_data` vs `SyntheticBankData/.../worktrees/.../ai_synthetic_data`

Örnek worktree (`interesting-yonath`) ile karşılaştırma:

- **Boyut:** `engine/ai_synthetic_data` tam ve güncel; worktree içi kopya **küçük ve eksik** (eski snapshot).
- **Farklar:** Worktree’de birçok modül yok (`banking_distributions.py`, `copula_synth.py`, `relational_synth.py`, vb.); ortak dosyalar da (`routes.py`, `config.py`, `analyzer.py`) **içerik olarak farklı**.
- **Sonuç:** Worktree kopyaları **kanonik değildir**; `engine/ai_synthetic_data` kullanılmalıdır.

## 4. `SyntheticBankData/.claude/worktrees/`

- **Karar:** Claude IDE worktree artefaktları; CI veya üretim yolu **değildir**.
- **Uygulama:** Dizin silinir; gelecekte oluşmaması için `.gitignore` ile hariç tutulur (bkz. kök `.gitignore`).
- Proje verisi için bkz. `SyntheticBankData/README.md`.

## 5. Kök dizin sadeleştirmesi

Sunum, analiz ve geçici test çıktıları [`archive/root-misc/`](../archive/root-misc/) altına taşınmıştır (bkz. [`archive/README.md`](../archive/README.md)).

## 6. Uygulama notları (2026-04-16)

- **Faz 0:** Yedek dal `backup/pre-consolidation-20260416` oluşturuldu.
- **Faz 1:** Kök arşiv tamam; liste `archive/README.md` içinde.
- **Faz 2A:** Bu checkout’ta `SyntheticBankData/.claude/worktrees` yoktu (zaten temiz veya klasör yok).
- **Faz 3:** Kök `package.json` içinde npm `workspaces`: `apps/web`, `ai-engine`.

---

**Son güncelleme:** 2026-04-16 — konsolidasyon uygulaması.
