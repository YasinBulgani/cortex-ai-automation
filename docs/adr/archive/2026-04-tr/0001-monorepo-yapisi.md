# ADR-0001: Monorepo yapısı

**Durum:** Kabul edildi
**Tarih:** 2026-04-19
**Karar verenler:** @yasin_bulgan

## Bağlam

TestwrightAI üç ana ürün bileşeninden oluşuyor:

1. **TSPM** — test süreç yönetimi (frontend + backend + DB)
2. **AI Test Generation** — doküman/doğal dil → Playwright kodu (backend + engine)
3. **Sentetik Veri Platformu** — şema tabanlı + AI zenginleştirme (backend service)

Üç ürün de:
- Aynı kullanıcı hesabı altında çalışıyor
- Aynı PostgreSQL DB'yi paylaşıyor
- Aynı AI Gateway'i kullanıyor
- Aynı frontend'den yönetiliyor
- Aynı deploy pipeline'ına giriyor

Alternatifler değerlendirildi:
- **Polyrepo (ayrı repo'lar)**: Her ürün kendi repo'su
- **Monorepo (tek repo)**: Hepsi tek repo altında

## Karar

**Monorepo** kullanıyoruz: `/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/`.

Yapı:
```
├── apps/web/              # Next.js frontend
├── backend/               # FastAPI backend (REST API)
├── engine/                # Flask test runtime
├── synthetic-data/        # Sentetik veri platform(lar)ı
├── ai-gateway/            # LLM gateway (Groq→Gemini→Ollama→g4f)
├── frameworks/            # Test framework'leri (Playwright+Cucumber)
├── api-tests/             # API regression suite
├── e2e/                   # End-to-end testler
├── infra/                 # Docker, k8s, nginx configs
├── docs/                  # Tüm dokümantasyon (ADR, architecture, testing)
├── packages/              # Paylaşılan paketler (DSL)
└── legacy/                # Arşivlenmiş modüller
```

## Alternatifler

### A. Polyrepo
Her servis kendi repo'sunda.

**Red sebepleri:**
- Atomik commit imkansız: "backend schema + frontend tip güncellemesi" iki PR'a bölünürdü
- Cross-cutting refactor (ör: auth değişikliği) 3 repo'ya yayılır
- CI pipeline 3 yerde tekrarlanır
- Küçük ekip için çok yüksek koordinasyon yükü

### B. Monorepo + Nx/Turborepo
Build cache ve task orchestration için Nx veya Turborepo.

**Red sebepleri (şimdilik):**
- Python ve TS karışık — Nx ikisinde de optimal değil
- Makefile şu an yeterli (19KB, olgun)
- Ek bağımlılık maliyeti > kazanç

**Kabul edilebilir:** Projeler büyürse (5+ servis) tekrar değerlendirilecek.

## Sonuçlar

### Olumlu
- Atomik commit: schema + backend + frontend değişiklikleri tek PR
- Cross-cutting refactor kolay (ör: auth header değişikliği)
- Shared types/constants tek yerde (`packages/`)
- Dokümantasyon merkezi (`docs/`)
- Tek CI pipeline, tek release tag'i

### Olumsuz / takas
- Repo büyük: `git clone` süresi uzar
- `git log` gürültülü — hangi servise dokundu filtrelemek zor
- CODEOWNERS olmadan kod sahipliği belirsiz
- Yeni gelen için "nereden başlasam" kafa karıştırıcı

### Takip işleri
- [ ] `.github/CODEOWNERS` ekle
- [ ] `git log -- backend/` gibi path-scoped log kullanımını CONTRIBUTING'e yaz
- [x] `legacy/` ile tarihsel kod ayrıştırıldı (2026-04-19)
- [ ] Build cache (Turborepo/Bazel) — projeler 5+ servise ulaştığında

## İlgili ADR'lar

- [ADR-0002](0002-engine-vs-backend-ayirimi.md) — iki Python backend'i
- [ADR-0004](0004-legacy-silme-politikasi.md) — arşiv yönetimi
