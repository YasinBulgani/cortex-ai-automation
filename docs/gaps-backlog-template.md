# Gaps Backlog Template

Bu sayfa, teknik eksiklerin ayni formatta takip edilmesi icin ornek bir backlog iskeleti sunar.

## Alanlar

Her kayitta asagidaki alanlar bulunmali:

- `Pillar`: Security / Runtime / CI / Frontend / Docs
- `Severity`: S1 (kritik) - S4 (dusuk)
- `Owner`: Backend / Web / Platform / QA
- `Evidence`: Dosya yolu veya test raporu baglantisi
- `Impact`: Riskin urun veya operasyon etkisi
- `Action`: Cozum adimi
- `Target Sprint`: Planlanan teslim periyodu

## Ornek tablo

| Pillar | Severity | Owner | Evidence | Impact | Action | Target Sprint |
|---|---|---|---|---|---|---|
| Security | S1 | Backend | `backend/app/domains/automation/router.py` | Yetkisiz proxy cagrisi | Auth zorunlulugu ekle | Sprint 1 |
| CI | S2 | Platform | `.github/workflows/ci.yml` | Regression guveni dusuk | PR gate kuralini netlestir | Sprint 1 |
| Frontend | S2 | Web | `apps/web/lib/hooks/use-auth.ts` | Auth davranis farkliligi | `apiFetch` kontratini standartlastir | Sprint 2 |
