# ADR-0006: `frameworks/playwright-cucumber-ts` dizininin rolü

**Durum:** Kabul edildi
**Tarih:** 2026-04-19
**Karar verenler:** Platform ekibi

## Bağlam

Repoda iki paralel Playwright + TypeScript test ağacı bulunuyor:

| Yol | Runner | Uygulama altında test ettiği |
|-----|--------|-------------------------------|
| `e2e/` | **Playwright Test** (native) | TestwrightAI web uygulaması (`apps/web`) |
| `frameworks/playwright-cucumber-ts/` | **Cucumber-JS + Playwright** | Paribu + DummyJSON demo senaryoları; DSL step kataloğu |

Bu çiftlilik, otomasyon değerlendirmesinde kafa karışıklığı yarattı: yeni katkıcılar "yeni test hangisine yazılmalı?" sorusunu kullanıcı desteğine açıyor; bazı dosyalar her iki yerde de benzer POM'ları taklit ediyor ama çalışma zamanında birbirleriyle konuşmuyor.

İlgili veriler:
- `frameworks/playwright-cucumber-ts/features/` dizininde yalnızca **2** `.feature` dosyası var (`web_tests.feature`, `api_tests.feature`), ancak **19+** step modülü mevcut. Step'lerin büyük bölümü çalıştırılmıyor → ölü kod riski.
- DSL kataloğu (`packages/dsl/catalog/`) bu step modüllerini **"reference implementation"** olarak gösteriyor — yani step kodları doğrudan koşulmak için değil, AI'ın test üretirken hangi Gherkin vocabulary'sini kullanabileceğini öğrenmesi için orada.
- `e2e/`'deki testler `apps/web`'i doğrudan Playwright API ile test ediyor; Cucumber katmanı yok.

## Karar

İki ağacı **bilerek ayrı tutuyoruz**, ancak rollerini bu ADR ile netleştiriyoruz:

1. **Ürün E2E testleri** → `e2e/` (Playwright Test native).
   - BGTS (`apps/web`) için tüm regression/smoke/flow testleri burada.
   - Yeni test yazarken default hedef **bu ağaç**.

2. **DSL katalog / AI training reference** → `frameworks/playwright-cucumber-ts/`.
   - Buradaki step modülleri **AI test üreticinin (Agents v2, NL-Test) örnek olarak aldığı Gherkin→kod eşleşme kataloğudur**, production test koşum ağacı değildir.
   - `features/` altındaki 2 demo senaryosu **referans** olarak tutulur; CI pipeline'larında gündelik koşulmaz.
   - Yeni BGTS özelliği için **buraya test eklenmez**.

3. **Paylaşım yok** — iki ağaç birbirinin POM'larını import etmez, ortak data/helper taşımaz. Farklı uygulamaları test eden **iki farklı repoda** gibi davranılır.

## Alternatifler

1. **`frameworks/` ağacını arşivle (`legacy/2026-04-cleanup/`'a taşı)** — red sebebi: DSL kataloğu AI test üreticisinin "hangi step'ler mevcut?" sorusuna verdiği cevabın birincil kaynağı; silinince Agents v2 / NL-Test kalitesi düşer.

2. **İki ağacı birleştir, tek runner'da topla** — red sebebi: Cucumber-JS ve Playwright Test runner'ları farklı mental model'lere sahip (Gherkin BDD vs describe/test). Birleştirmek hem mevcut testleri kırar hem de DSL kataloğunu bozar. ROI negatif.

3. **`frameworks/`'ü BGTS'e yönlendir** (Paribu yerine `apps/web`'i test etsin) — red sebebi: Ürün testlerinin iki paralel yerde koşması büyük bakım yükü; CI süresi ~2x, flaky çarpanı ~2x. `e2e/` zaten bu rolü kapsıyor.

## Sonuçlar

### Olumlu

- Katkıcı için net yönlendirme: "yeni test → `e2e/`, DSL referansı → `frameworks/`".
- AI test üreticinin öğrenme kaynağı (DSL katalog) kesintiye uğramıyor.
- İki ağacın çakışan bakım yükü sona eriyor.

### Olumsuz / takas

- `frameworks/` artık "ürün testi değil ama silinmiyor" gri alanda; yeni gelen "bu dizin niye var?" diye sorabilir (bu ADR ile cevap yerinde).
- DSL step'leri zaman içinde Playwright API değişikliğiyle bitrot olabilir; `npm run test:framework:lint` gibi periyodik tip/derleme kontrolü gerekir (takip işi).

### Takip işleri

- [ ] `frameworks/playwright-cucumber-ts/README.md` başına rolünü netleştiren bir banner ekle ("DSL reference, not production tests").
- [ ] Root `README.md`'de "Test Komutları" altında iki ağacın amacını ayır.
- [ ] CI'da `frameworks/` için yalnızca **compile/lint** job'ı (gündelik koşum değil); bitrot'ı önler.
- [ ] DSL catalog'ta link'ler doğru dosyalara işaret ediyor mu periyodik doğrula.

## İlişkili ADR'ler

- [ADR-0005](./0005-test-taksonomisi.md) — Test katmanları ve konumları (bu ADR o taksonomiyi kategorize eder).
