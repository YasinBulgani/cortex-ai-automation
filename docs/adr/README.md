# Architecture Decision Records (ADR)

Bu dizin, **Neurex QA** için önemli mimari kararların kayıtlarını içerir.

## Active ADRs

| # | Title | Status |
|---|-------|--------|
| [0001](./0001-monorepo-turborepo.md) | Monorepo with Turborepo | ✅ Accepted |
| [0002](./0002-httponly-cookie-auth.md) | httpOnly Cookie Authentication 🔒 | ✅ Accepted |
| [0003](./0003-ddd-bounded-contexts.md) | DDD Bounded Contexts in Backend | ✅ Accepted |
| [0004](./0004-outbox-pattern-events.md) | Outbox Pattern for Reliable Events | ✅ Accepted |
| [0005](./0005-engine-consolidation.md) | Flask Engine → FastAPI Consolidation | 🔄 In Progress |

## Arşivlenmiş (Eski Türkçe ADR'ler)

Eski Türkçe ADR'ler (Nisan 2026 öncesi) `archive/2026-04-tr/` altına taşındı.
Bunlar artık **kanonik kaynak değil** — yukarıdaki İngilizce ADR'ler geçerlidir.

| Arşiv dosyası | İçerik | Yerini alan |
|---|---|---|
| `0001-monorepo-yapisi.md` | Turborepo kararı | ADR-0001 |
| `0002-engine-vs-backend-ayirimi.md` | Engine/backend ayrımı | ADR-0005 |
| `0003-synthetic-data-konsolidasyonu.md` | Synthetic data gap | ADR-0003 |
| `0004-legacy-silme-politikasi.md` | Legacy cleanup | ADR-0004 |
| `0005-multi-tenant-rls.md` | RLS planı | (ilerleyen sprint) |
| `0005-test-taksonomisi.md` | Test taxonomy | `qa/strategy/test-strategy.md` |

## ADR nedir?

Bir **Architecture Decision Record**, belirli bir zamanda alınan önemli bir mimari/teknik kararı, o kararın **bağlamını**, **alternatiflerini** ve **sonuçlarını** kaydeder. Amaç: 6 ay sonra "neden böyle yapmıştık?" sorusunun cevabını bulabilmek.

## Ne zaman ADR yazılır?

- Yeni bir kütüphane/framework seçiminde
- İki meşru alternatif arasında karar vermekte
- Geri dönüşü pahalı olan kararlarda (DB şeması, auth, API şekli)
- "Bunu daha önce konuşmuştuk ama hatırlamıyorum" durumlarında

## Ne zaman ADR yazılmaz?

- Kod stili (lint/formatter konfigi yeterli)
- Günlük bug fix'leri
- Geçici deneyler (spike'lar)

## Şablon

Yeni ADR için: `docs/adr/NNNN-kisa-baslik.md`

```markdown
# ADR-NNNN: Başlık

**Durum:** Önerildi / Kabul edildi / Reddedildi / Değiştirildi / Yerine geçildi (ADR-XXXX)
**Tarih:** YYYY-MM-DD
**Karar verenler:** @kullanici

## Bağlam

Bu kararı gerektiren durum ne? Hangi kısıtlar var?

## Karar

Ne yapıyoruz?

## Alternatifler

1. **X yaklaşımı** — red sebebi
2. **Y yaklaşımı** — red sebebi

## Sonuçlar

### Olumlu
- ...

### Olumsuz / takas
- ...

### Takip işleri
- [ ] ...
```

## ADR indeksi

| # | Başlık | Durum | Tarih |
|---|---|---|---|
| [0001](0001-monorepo-yapisi.md) | Monorepo yapısı | Kabul edildi | 2026-04-19 |
| [0002](0002-engine-vs-backend-ayirimi.md) | Engine (Flask) ve Backend (FastAPI) ayrı kalıyor | Kabul edildi | 2026-04-19 |
| [0003](0003-synthetic-data-konsolidasyonu.md) | Synthetic-data v4 ana platform | Kabul edildi | 2026-04-19 |
| [0004](0004-legacy-silme-politikasi.md) | Legacy silme politikası (6 ay) | Kabul edildi | 2026-04-19 |
| [0005](0005-test-taksonomisi.md) | Test katmanları ve konumları | Kabul edildi | 2026-04-19 |
| [0006](0006-playwright-cucumber-framework-rolü.md) | `frameworks/playwright-cucumber-ts` rolü — DSL referansı | Kabul edildi | 2026-04-19 |

## Ek kaynaklar

- [Michael Nygard: Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [adr.github.io](https://adr.github.io/)
