# Architecture Decision Records (ADR)

Bu dizin, **Neurex QA** için önemli mimari kararların kayıtlarını içerir.

## Aktif ADR'lar

| # | Başlık | Durum | Tarih |
|---|---|---|---|
| [0001](./0001-monorepo-yapisi.md) | Monorepo yapısı (Turborepo) | ✅ Kabul edildi | 2026-04-19 |
| [0002](./0002-engine-vs-backend-ayirimi.md) | Engine (Flask) ve Backend (FastAPI) ayrı kalıyor | ✅ Kabul edildi | 2026-04-19 |
| [0003](./0003-synthetic-data-konsolidasyonu.md) | Synthetic-data v4 ana platform | ✅ Kabul edildi | 2026-04-19 |
| [0004](./0004-legacy-silme-politikasi.md) | Legacy silme politikası (6 ay) | ✅ Kabul edildi | 2026-04-19 |
| [0005](./0005-test-taksonomisi.md) | Test katmanları ve konumları | ✅ Kabul edildi | 2026-04-19 |
| [0006](./0006-playwright-cucumber-framework-rolü.md) | `frameworks/playwright-cucumber-ts` rolü — DSL referansı | ✅ Kabul edildi | 2026-04-19 |

## Arşivlenenler

> [`archive/`](./archive/) dizininde: içerik çakışması veya scope değişikliği nedeniyle arşivlenen eski ADR taslakları.

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
Mevcut en yüksek numara: **0006** → yeni ADR için **0007** kullan.

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

## Kaynaklar

- [Michael Nygard: Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [adr.github.io](https://adr.github.io/)
