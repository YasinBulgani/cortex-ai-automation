# ADR-001: Backend (FastAPI) ve Engine (Flask) ayrı süreçler olarak kalması

- **Durum:** Kabul edildi (varsayılan)
- **Tarih:** 2026-04-04
- **Bağlam:** [`REPO_CONSOLIDATION_PLAN.md`](REPO_CONSOLIDATION_PLAN.md) Faz 5

## Bağlam

BGTS monoreposunda `backend/` FastAPI ile TSPM ve proxy sunar; `engine/` Flask ile Playwright, BDD ve otomasyon işlerini yürütür. Bu ayrım deploy, ölçekleme ve hata izolasyonu sağlar.

## Karar

**Şu aşamada** iki servisi tek süreçte birleştirmiyoruz. Entegrasyon mevcut HTTP/proxy ve ortam değişkenleri ile kalır.

## Sonuçlar

- Olumlu: Değişiklik riski düşük; mevcut CI ve dokümantasyon geçerli.
- Olumsuz: İki servis operasyonu (iki port, iki health check).

## Birleştirme seçeneği

İleride tek süreç istenirse ayrı proje açılır; migration, test matrisi ve rollback [REPO_CONSOLIDATION_PLAN.md](REPO_CONSOLIDATION_PLAN.md) bölüm 7’deki maddelerle yürütülür.
