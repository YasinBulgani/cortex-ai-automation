# BGTS Test Dönüşüm — Genişletilmiş İzlenebilirlik Matrisi

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kapsam:** Tüm test dokümanlarını kapsayan uçtan uca traceability

---

## İş Kuralı → Test Dokümanı Eşleştirmesi

| İş Kuralı | Açıklama | Ana (75) | E2E (59) | Security (33) | Perf (28) | RBAC (180) | Contract (45) | CrossCut (42) | Advanced (84) | Specialized (49) | n8n/Chat (24) |
|-----------|----------|---------|---------|--------------|---------|-----------|--------------|--------------|--------------|-----------------|--------------|
| **BR-001** | Auth/JWT | 10 | 6 | 8 | 1 | — | 2 | — | — | — | — |
| **BR-002** | Proje | 8 | 7 | — | 2 | 3 | 2 | — | 2 | 3 | — |
| **BR-003** | Senaryo | 9 | 8 | 2 | 3 | 7 | 7 | — | 5 | 4 | — |
| **BR-004** | BDD | 4 | 2 | — | 1 | 2 | 2 | — | 1 | — | — |
| **BR-005** | Onay | 4 | — | — | — | 2 | 1 | — | 1 | — | — |
| **BR-006** | Import | — | — | — | — | 1 | — | 4 | — | — | — |
| **BR-007** | Koşu | 6 | 5 | — | 2 | 5 | 4 | — | 3 | 1 | — |
| **BR-008** | Analitik | 5 | 2 | — | 2 | 3 | 2 | — | 1 | — | — |
| **BR-009** | Akış | 3 | 5 | — | 1 | 2 | — | — | — | — | — |
| **BR-010** | Regresyon | 6 | 4 | — | — | 4 | 3 | — | 1 | — | — |
| **BR-011** | Gereksinim | 7 | 5 | — | 1 | 4 | 2 | — | 2 | — | — |
| **BR-012** | Zamanlama | 5 | 4 | — | — | 3 | 2 | — | 1 | — | — |
| **BR-013** | Test Verisi | 4 | 4 | — | — | 2 | 2 | — | 1 | — | — |
| **BR-014** | Entegrasyon | 3 | 3 | — | — | 3 | 1 | — | — | — | — |
| **BR-015** | API Test | 4 | — | 1 | 1 | 3 | 3 | — | — | — | — |
| **BR-016** | Üyeler | 3 | — | 1 | — | 3 | — | — | — | — | — |
| **BR-017** | Versiyon | 3 | 2 | — | — | — | — | 4 | 1 | — | — |
| **BR-018** | WebSocket | — | — | 2 | — | — | — | — | — | 12 | — |
| **BR-019** | n8n Workflow | — | — | 1 | — | — | — | — | — | — | 12 |
| **BR-020** | AI Chat | — | — | — | — | — | — | — | — | — | 12 |
| **CC-001** | Audit Log | — | — | 1 | — | — | — | 7 | — | — | — |
| **CC-002** | Webhooks | — | — | 1 | — | — | — | 7 | — | — | — |
| **CC-003** | Rate Limit | — | — | 4 | — | — | — | 5 | — | — | — |
| **CC-004** | Error Handle | — | — | — | — | — | — | 7 | — | — | — |
| **CC-005** | Export | — | — | — | — | — | — | 5 | — | — | — |

---

## Test Tipi → Doküman Eşleştirmesi

| Test Tipi | Dokümanlar | Toplam |
|-----------|-----------|--------|
| Fonksiyonel (Pozitif) | Ana, E2E, n8n/Chat | ~200 |
| Fonksiyonel (Negatif) | Ana, Security, Advanced | ~60 |
| Boundary / Edge Case | Ana, Specialized | ~45 |
| Exception / Error | CrossCut, Advanced, Specialized | ~25 |
| Güvenlik | Security, RBAC | ~213 |
| Performans | Performance | 28 |
| Erişilebilirlik | Advanced (a11y) | 14 |
| Uyumluluk | Advanced (browser) | 42 |
| Veri Bütünlüğü | Advanced (DI) | 10 |
| Eşzamanlılık | Advanced (Concurrency) | 8 |
| API Kontrat | Contract | 45 |

---

## Modül → Test Kapsama Durumu

| Modül | Toplam Test | Kapsam |
|-------|-----------|--------|
| Authentication | 27 | ✅ Tam |
| Projeler | 25 | ✅ Tam |
| Senaryolar | 45 | ✅ Tam |
| BDD Üretimi | 12 | ✅ Tam |
| Onay Kuyruğu | 8 | ✅ Tam |
| İçe Aktarma | 5 | ⚠️ Kısmi (stub) |
| Test Koşuları | 26 | ✅ Tam |
| Analitikler | 15 | ✅ Tam |
| Akışlar | 11 | ✅ Tam |
| Regresyon | 18 | ✅ Tam |
| Gereksinimler | 21 | ✅ Tam |
| Zamanlamalar | 15 | ✅ Tam |
| Test Verisi | 13 | ✅ Tam |
| Entegrasyonlar | 10 | ✅ Tam |
| API Test | 12 | ✅ Tam |
| Üyeler | 7 | ✅ Tam |
| Versiyonlama | 10 | ✅ Tam |
| WebSocket | 12 | ✅ Tam |
| n8n Workflow | 12 | ✅ Tam |
| AI Chat | 12 | ✅ Tam |
| Audit / Webhook / Rate | 26 | ✅ Tam |
| Export / Quality | 8 | ✅ Tam |

**Toplam kapsanan modül: 22/22 (İçe Aktarma kısmi)**
