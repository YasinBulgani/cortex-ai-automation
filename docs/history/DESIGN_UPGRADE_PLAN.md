# Nexus QA — Tam Tasarım Yükseltme Planı
> Proje taraması: 50+ sayfa analiz edildi. Hedef: Tüm UI'yı debug-report / ai-chat / visual kalitesine çıkarmak.

---

## 🎨 Tasarım Dili (Referans: Benim Yaptığım Sayfalar)

### Temel Kurallar
```
Arkaplan:    bg-slate-950 / bg-slate-900
Kenarlık:    border-slate-700 / border-slate-800
Kart:        rounded-xl border border-slate-700 bg-slate-900/40
Badge:       rounded-full border px-2 py-0.5 text-xs font-medium
Başlık:      text-lg font-bold text-white flex items-center gap-2
Alt başlık:  text-xs text-slate-400
Buton-Ana:   bg-blue-600 hover:bg-blue-500 rounded-xl px-4 py-2 text-sm font-semibold
Buton-İkil:  border border-slate-700 hover:border-slate-500 rounded-lg px-3 py-1.5 text-xs
Tablo başlık:px-4 py-2.5 text-xs font-medium text-slate-400
Tablo satır: border-b border-slate-800 hover:bg-slate-900/40
```

---

## 📋 ÖNCELIK 1 — Kritik (En Çok Kullanılan Sayfalar)

### 1. `scenarios/page.tsx` — Senaryo Listesi
**Sorun:** `Button`, `Input` komponent bağımlılığı, DnD var ama dark/slate yok, tablo beyaz zemin
**Yapılacak:**
- Header: icon + başlık + açıklama + sağda "Yeni Senaryo" + "Üret" butonları
- Status badge: renk kodlu (draft=slate, active=emerald, archived=red)
- Tablo: slate-800 zemin, hover efekti, version badge
- Drag handle: sadece ikon, subtle
- Boş durum: emoji + açıklama + CTA
- Filtreleme çubuğu: status dropdown + arama input

### 2. `executions/page.tsx` — Koşu Listesi
**Sorun:** Temel tablo, renk yok, metrik gösterge yok
**Yapılacak:**
- Header: stats row (toplam/aktif/tamamlanan/başarı oranı)
- Her satır: progress bar (geçti/kaldı), status pill, süre badge
- "Yeni Koşu" butonu → executions/new ile entegre
- Boş durum: 🧪 + açıklama

### 3. `analytics/page.tsx` — Analitik
**Sorun:** DataTable + useFetch bağımlılığı, grafik container düzensiz
**Yapılacak:**
- Stat cards grid (4'lü): total/pass rate/trend/active
- Chart wrapper: rounded-xl border, dark background
- Zaman filtresi: 7g/30g/90g pill buttons
- Trend badge: ↑ yeşil / ↓ kırmızı

### 4. `runs/page.tsx` — Test Koşuları (Engine)
**Sorun:** En kötü sayfa — 417 satır, karışık eski/yeni, DataTable kullanıyor
**Yapılacak:**
- Tam yeniden yazım
- SSE log stream paneli (debug-report tarzı)
- Live status feed
- Allure export butonu → Faz 6 entegrasyonu

### 5. `regression/page.tsx` — Regresyon Setleri
**Sorun:** Kısmen dark, ama border-gray var, form alanları raw HTML
**Yapılacak:**
- Set kartları: scenario count badge, priority renk
- Coverage % progress bar
- "AI Öner" butonu entegrasyonu

### 6. `reports/page.tsx` — Raporlar
**Sorun:** Beyaz arka plan, tablo ham
**Yapılacak:**
- Report type ikonları (HTML/PDF/Allure)
- İndirme butonları belirgin
- Son üretilen raporlar listesi

---

## 📋 ÖNCELIK 2 — Yüksek (Sık Kullanılan Araç Sayfaları)

### 7. `manual/page.tsx` — Manuel Test
**Sorun:** 532 satır, form heavy, ham HTML
**Yapılacak:**
- Adım editörü: drag-reorderable step cards
- Status toggle: pass/fail/blocked buton grubu
- Note alanı: inline collapsible

### 8. `approvals/page.tsx` — Onaylar
**Sorun:** Temel liste, aksiyon butonları düz
**Yapılacak:**
- Onay kuyruğu layout (inbox stili)
- Batch approve butonu
- AI önerileri preview

### 9. `requirements/page.tsx` — Gereksinimler
**Sorun:** DataTable bağımlı, çok fazla border-gray
**Yapılacak:**
- Requirement → Scenario bağlantı görselleştirme
- Coverage badge per requirement
- Priority filter

### 10. `schedules/page.tsx` — Zamanlamalar
**Sorun:** 367 satır, ham form, cron input düz metin
**Yapılacak:**
- Schedule card: next run countdown, status badge
- Cron builder: preset seçimi (her gün/hafta/ay)
- Son çalışma sonucu badge

### 11. `api-tests/page.tsx` — API Testleri
**Sorun:** 436 satır, en fazla eski sınıf kullanan sayfa
**Yapılacak:**
- Postman-tarzı request builder
- Response viewer: syntax highlight
- Status code renk kodlama

### 12. `recorder/page.tsx` — Kaydedici
**Sorun:** Tabs bileşeni eski, generate sonucu düzensiz
**Yapılacak:**
- Session kartları: action count badge, domain
- Kod üretim seçici: pill toggle
- Üretilen kod: CodeBlock bileşeni (automation-gen tarzı)

---

## 📋 ÖNCELIK 3 — Orta (Destek Sayfaları)

### 13. `flaky/page.tsx` — Flaky Testler
- Flakiness score progress bar
- Trend grafik mini sparkline
- Auto-heal butonu entegrasyonu

### 14. `coverage/page.tsx` — Kapsam
- Coverage heatmap (scenario/requirement matrisi)
- % gösterge donut chart

### 15. `locators/page.tsx` — Locator'lar
- Locator type badge (css/xpath/testid)
- Copy to clipboard butonu
- Kullanım sayısı badge

### 16. `flows/page.tsx` — Akışlar
- Flow durumu renk kodlu
- Step count badge

### 17. `monkey/page.tsx` — Monkey Test
- Çok büyük (914 satır), modüler parçalara bölünmeli
- Sonuç kartları: bug count, coverage %, screenshots

### 18. `cicd/page.tsx` — CI/CD
- Pipeline status badge (GitHub/GitLab/Jenkins)
- Webhook URL display

### 19. `import/page.tsx` — İçe Aktarma
- Drag-drop upload alanı
- Format destekleri ikonlu listesi

### 20. `integrations/page.tsx` — Entegrasyonlar
- Provider kartları: Slack/Jira/GitHub logo
- Bağlı/bağlı değil durumu

### 21. `accessibility/page.tsx` — Erişilebilirlik
- WCAG level badge
- Hata/uyarı sayısı renk kodlu

### 22. `synthetic/page.tsx` — Sentetik Veri
- Veri tipi seçici: avatar ile listeler
- Üretilen veri preview kartı

### 23. `test-data/page.tsx` — Test Verileri
- DataSet kartları
- Bağlı senaryo sayısı badge

### 24. `page-objects/page.tsx` — Sayfa Nesneleri
- POM hiyerarşi görünümü
- Locator listesi per PO

### 25. `wizard/page.tsx` — Wizard (Engine)
- Adım ilerleme bar'ı yenile
- Responsive layout

---

## 📋 ÖNCELIK 4 — Global Bileşenler

### 26. `app/page.tsx` — Proje Listesi (Ana Sayfa)
**Sorun:** Proje kartları düz, arama yok, arşiv filtresi yok
**Yapılacak:**
- Grid kartlar: son koşu pass rate badge, senaryo sayısı
- Arama + filtre (aktif/arşiv)
- "Yeni Proje" butonu belirgin CTA

### 27. `p/[projectId]/page.tsx` — Proje Dashboard
**Sorun:** 4 kart, minimal
**Yapılacak:**
- Stats row: 6 metrik
- Son koşuların mini listesi
- Pass rate trend sparkline
- AI sağlık göstergesi

### 28. `login/page.tsx` — Giriş
- Branded login: logo + gradient background
- Hata mesajı animasyonlu

### 29. `AppShell.tsx` — Sidebar
- Aktif proje adı üstte
- Nav gruplarına ikon ekle
- Alt kısmda AI status dot

### 30. `components/ui/` — UI Primitives
- `button.tsx`: variant sistemi genişlet (ghost-danger)
- `data-table.tsx`: slate dark theme
- `tabs.tsx`: pill style

---

## 🔧 Paylaşılan Bileşen Kütüphanesi (Oluşturulacak)

```
apps/web/components/nexus/
├── PageHeader.tsx          # icon + başlık + açıklama + sağ slot
├── StatCard.tsx            # icon + değer + label + renk
├── StatusBadge.tsx         # renk kodlu durum pill
├── ProgressBar.tsx         # renkli segmentli bar
├── EmptyState.tsx          # emoji + başlık + CTA
├── CodeBlock.tsx           # dil badge + satır numarası + kopyala/indir
├── SectionCard.tsx         # başlıklı rounded-xl kart
├── FilterBar.tsx           # arama + dropdown filtreler
└── DataGrid.tsx            # slate-themed table
```

---

## 📅 Uygulama Sırası

| Hafta | Sayfalar | Öncelik |
|-------|----------|---------|
| 1 | Paylaşılan bileşenler (nexus/) | Altyapı |
| 1 | scenarios, executions, analytics | P1 |
| 2 | runs, regression, reports, manual | P1 |
| 3 | approvals, requirements, schedules, api-tests | P2 |
| 4 | recorder, flaky, coverage, locators | P2 |
| 5 | flows, monkey, cicd, import, integrations | P3 |
| 6 | accessibility, synthetic, test-data, page-objects, wizard | P3 |
| 7 | Global: login, app/page, dashboard, AppShell, UI primitives | P4 |

---

## ✅ Tasarım Referans Sayfalar (Değiştirme)

Bunlar zaten yeni kalitede, dokunma:
- `debug-report/page.tsx` ✓
- `ai-chat/page.tsx` ✓
- `automation-gen/page.tsx` ✓
- `visual/page.tsx` ✓ (yeni)
- `executions/[runId]/page.tsx` ✓ (yeni)
- `test-cases/page.tsx` ✓
- `analysis/page.tsx` ✓

---

## 🎯 Tahmini Etki

- **30 sayfa** yeniden tasarlanacak
- **~8.000 satır** kod değişecek
- **7 paylaşılan bileşen** oluşturulacak
- Sonuç: Tüm platform tek ve tutarlı tasarım dili
