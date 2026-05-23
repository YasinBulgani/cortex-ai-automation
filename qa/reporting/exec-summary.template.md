# BGTS Yönetici Özet Raporu Şablonu

---

## BGTS Test Yönetici Özeti

**Proje:** {PROJE_ADI}
**Rapor Tarihi:** {TARIH}
**Sprint/Dönem:** {SPRINT}
**Hazırlayan:** {HAZIRLAYAN}

---

### 1. Genel Sağlık Durumu

```
╔════════════════════════════════════════════════════════╗
║  PLATFORM SAĞLIK DURUMU:  🟢 SAĞLIKLI / 🟡 RİSKLİ / 🔴 KRİTİK  ║
╚════════════════════════════════════════════════════════╝
```

| Metrik | Değer | Trend | Hedef | Durum |
|--------|-------|-------|-------|-------|
| Genel Başarı Oranı | {PASS_RATE}% | {TREND} | >= 85% | {DURUM} |
| Kritik Test Başarısı | {CRITICAL_RATE}% | {TREND} | >= 95% | {DURUM} |
| Otomasyon Kapsama | {AUTO_COVERAGE}% | {TREND} | >= 70% | {DURUM} |
| Gereksinim Kapsama | {REQ_COVERAGE}% | {TREND} | >= 90% | {DURUM} |
| Ortalama Çalışma Süresi | {AVG_DURATION} | {TREND} | < 20dk | {DURUM} |

### 2. Son Çalıştırma Özeti

| | Sayı | Oran |
|---|------|------|
| Toplam Test | {TOTAL} | 100% |
| Başarılı | {PASSED} | {PASS_PCT}% |
| Başarısız | {FAILED} | {FAIL_PCT}% |
| Atlanan | {SKIPPED} | {SKIP_PCT}% |
| Çalışma Süresi | {DURATION} | — |

### 3. Kritik Bulgular

#### Başarısız Testler (İlk Müdahale Gerektiren)

| # | Test | Modül | Kök Neden | Etki | Aksiyon |
|---|------|-------|-----------|------|---------|
| 1 | {TEST_ADI} | {MODUL} | {KOK_NEDEN} | {ETKI} | {AKSIYON} |
| 2 | ... | ... | ... | ... | ... |

#### Yeni Keşfedilen Riskler

| # | Risk | Olasılık | Etki | Mevcut Durum |
|---|------|----------|------|-------------|
| 1 | {RISK_ACIKLAMA} | Yüksek/Orta/Düşük | Yüksek/Orta/Düşük | {DURUM} |

### 4. Kapsam Durumu

```
Gereksinim Kapsamı:  ████████████████░░░░ 85%  (34/40)
Otomasyon Kapsamı:   ████████████░░░░░░░░ 65%  (26/40)
Modül Kapsamı:       ██████████████░░░░░░ 73%  (8/11)
```

**Kapsanmayan Kritik Alanlar:**
- {ALAN_1}: {ACIKLAMA}
- {ALAN_2}: {ACIKLAMA}

### 5. Trend Analizi (Son 5 Sprint)

```
Başarı Oranı Trendi:

100% │                              ╭──
 90% │              ╭───╮     ╭────╯
 85% │─ ─ ─ ─ ─ ─ ─│─ ─│─ ─ ─│─ ─ ─ ─  Hedef
 80% │    ╭─────────╯   ╰─────╯
 75% │────╯
     └──────────────────────────────────
      S8    S9    S10   S11   S12
```

| Sprint | Toplam | Başarılı | Oran | Delta |
|--------|--------|----------|------|-------|
| Sprint 8 | 35 | 27 | 77.1% | — |
| Sprint 9 | 38 | 32 | 84.2% | +7.1% |
| Sprint 10 | 42 | 36 | 85.7% | +1.5% |
| Sprint 11 | 45 | 37 | 82.2% | -3.5% |
| Sprint 12 | 48 | 42 | 87.5% | +5.3% |

### 6. Kalite Metrikleri

| Metrik | Bu Dönem | Önceki Dönem | Değişim |
|--------|----------|-------------|---------|
| Defect Density | {VAL}/KLOC | {VAL}/KLOC | {DELTA} |
| Defect Leakage | {VAL}% | {VAL}% | {DELTA} |
| Mean Time to Detect | {VAL} saat | {VAL} saat | {DELTA} |
| Mean Time to Resolve | {VAL} saat | {VAL} saat | {DELTA} |
| Flaky Test Oranı | {VAL}% | {VAL}% | {DELTA} |
| Test Automation ROI | {VAL}x | {VAL}x | {DELTA} |

### 7. Sprint Deliverable Durumu

| Özellik | Test Durumu | Risk |
|---------|-------------|------|
| {FEATURE_1} | Tamamlandı / Devam Ediyor / Başlamadı | Düşük/Orta/Yüksek |
| {FEATURE_2} | ... | ... |

### 8. Öneriler ve Sonraki Adımlar

#### Acil Aksiyonlar (Bu Hafta)
1. {AKSIYON_1}
2. {AKSIYON_2}

#### Kısa Vadeli (Bu Sprint)
1. {AKSIYON_3}
2. {AKSIYON_4}

#### Orta Vadeli (Sonraki 2 Sprint)
1. {AKSIYON_5}
2. {AKSIYON_6}

### 9. Release Readiness

| Kriter | Durum | Notlar |
|--------|-------|--------|
| Tüm P0 testler geçiyor | {EVET/HAYIR} | {NOT} |
| Kritik bug kalmadı | {EVET/HAYIR} | {NOT} |
| Regresyon tamamlandı | {EVET/HAYIR} | {NOT} |
| Performance kabul edilebilir | {EVET/HAYIR} | {NOT} |
| Security scan temiz | {EVET/HAYIR} | {NOT} |

**Release Kararı:** GO / NO-GO / CONDITIONAL GO

---

**Sonraki rapor tarihi:** {SONRAKI_TARIH}
**Dağıtım:** {PM}, {QA_LEAD}, {DEV_LEAD}, {SCRUM_MASTER}
