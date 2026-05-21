# BGTS Demo-First 30 Gün Planı

**Tarih:** 2026-04-10  
**Ana hedef:** 30 gün içinde satış/gösterim odaklı, uçtan uca çalışan tek bir demo akışı çıkarmak  
**Odak:** Test Platformu + Sentetik Veri birlikte, LLM tarafında semantic RAG + tool-calling + kaynak gösterme

## 1. Karar Özeti

Bu plan şu kararları baz alır:

- Öncelik production-hardening değil, **güven veren demo akışı**
- Demo tek sektöre odaklanacak: **bankacılık**
- Demo hikayesinde **test platformu** ve **sentetik veri** birlikte gösterilecek
- LLM tarafında bir sonraki yatırım **tek başına model büyütmek değil**
  - semantic retrieval
  - tool-calling
  - kaynaklı cevap

## 2. Demo Hikayesi

Tek cümlelik ürün demosu:

> Analist dokümanı veya iş kuralı sisteme yüklenir, BGTS gereksinim ve test senaryosu önerir, sentetik bankacılık verisi üretir, onaylanan senaryolardan otomasyon çıkarır, testi koşturur ve sonucu AI ile kaynaklı olarak açıklar.

## 3. Demo Başarı Kriterleri

30 gün sonunda aşağıdakiler sorunsuz gösterilebilmeli:

1. Kullanıcı bir proje açar veya seçer.
2. Bir doküman yükler.
3. Sistem requirement/test case/senaryo önerir.
4. Kullanıcı onay verir.
5. Sistem sentetik veri seti üretir ve senaryoya bağlar.
6. Sistem Gherkin ve en az bir runnable otomasyon artifact üretir.
7. Execution çalışır ve sonuç döner.
8. AI chat/debug ekranı sonucu kaynaklı açıklar.

## 4. Demo KPI'ları

- Doküman yükleme -> ilk AI öneri süresi: `<= 30 sn`
- AI öneriden onaylı senaryoya dönüşüm: `<= 5 dk`
- Onaylı test case -> otomasyon artifact üretim başarısı: `>= %70`
- Demo execution başarıyla başlama oranı: `>= %90`
- AI cevaplarında kaynak gösterme oranı: `>= %90`
- Demo boyunca elle müdahale gerektiren adım sayısı: `<= 1`

## 5. Haftalık Backlog

## Hafta 1: Demo Omurgasını Kilitle

### Hedef

Tek resmi demo akışını sabitlemek ve gereksiz dallanmaları dondurmak.

### P0

- Demo için tek örnek domain seçimini sabitle: bankacılık
- Demo verisi, demo dokümanı, demo kullanıcıları ve beklenen sonuçları sabitle
- Demo sırasında açılacak ekranları belirle
- Her ekran için "mutlaka çalışmalı" senaryoyu yaz
- Demo akışını bozan ekran ve özellikleri "out of scope" olarak işaretle

### P1

- `demo mode` düşüncesi için route ve veri bağımlılıklarını çıkar
- Demo için örnek proje seed planı hazırla
- Demo günü fallback senaryoları tanımla

### Çıktılar

- Demo ekran listesi
- Sabit örnek doküman
- Sabit sentetik veri örneği
- Sabit kabul kriterleri

### Hafta Sonu Kabul Kriteri

Takım şu soruya net cevap verebilmeli:

> Demosu yapılacak tek akış tam olarak hangisi ve hangi ekranlardan geçiyor?

## Hafta 2: LLM'i Güvenilir ve Kaynaklı Hale Getir

### Hedef

LLM'in "güzel konuşan ama uyduran" görünümden çıkıp veri temelli görünmesi.

### P0

- Import edilen dokümanları chunk'layıp indeksleme akışını kur
- Requirement, scenario, execution result ve test case kayıtlarını retrieval'a aç
- Semantic retrieval katmanını ekle
- En az 4 tool ekle:
  - `get_project_requirements`
  - `get_related_scenarios`
  - `get_failed_executions`
  - `get_test_data_sets`
- AI yanıtlarında kaynak listesi döndür

### P1

- Intent bazlı routing ekle: chat/debug/coverage/automation/data
- Retrieval kalitesi için top-k ve score logging ekle
- AI cevaplarında "emin değilim" ve "dayandığım kayıtlar" formatını netleştir

### Çıktılar

- Grounded AI chat
- Grounded debug analizi
- Kaynaklı cevap formatı

### Hafta Sonu Kabul Kriteri

AI chat ekranında sorulan bir soruya cevap verirken sistem:

- ilgili requirement'ı
- ilgili scenario'yu
- ilgili failed run'ı

isim ve içerik düzeyinde referanslayabiliyor olmalı.

## Hafta 3: Sentetik Veri + Otomasyon Birleşik Akışı

### Hedef

Sentetik veri tarafını demo hikayesine gerçekten bağlamak.

### P0

- Demo için sentetik bankacılık veri seti üretim akışını sabitle
- Üretilen veri setini test senaryosu ile bağla
- Otomasyon üretim prompt'larına veri bağlamı ekle
- En az bir akış için runnable artifact üret:
  - müşteri oluşturma
  - başvuru
  - limit kontrolü
  - hata varyantı

### P1

- Veri seti önizleme ekranını demoya uygun hale getir
- Test data binding görünürlüğünü artır
- Negatif veri varyantlarını ekle

### Çıktılar

- Senaryoya bağlı veri seti
- Veri kullanan otomasyon örneği
- En az 1 başarılı ve 1 başarısız akış demosu

### Hafta Sonu Kabul Kriteri

Demo sırasında "Bu test hangi veriyle koşuyor?" sorusuna UI üstünden cevap gösterilebilmeli.

## Hafta 4: Execution, Raporlama ve Demo Polish

### Hedef

Tüm zinciri tek oturumda güvenli şekilde gösterebilmek.

### P0

- Tek tık execution akışını stabilize et
- Execution sonucu için sade bir özet alanı hazırla
- AI debug sonucunu kaynaklı ve anlaşılır hale getir
- Demo script'ini yaz ve prova et
- Demo günü fallback akışını hazırla

### P1

- Dashboard'ta demo KPI kartları göster
- Export/share ekranı gerekiyorsa hafif sürüm ekle
- UI boş durum ve loading durumlarını polish et

### Çıktılar

- 10 dakikalık demo script
- 3 dakikalık kısa demo script
- Fallback planı
- Demo KPI görünümü

### Hafta Sonu Kabul Kriteri

Tek kişi 10 dakikada kesintisiz demo yapabiliyor olmalı.

## 6. Ekran Bazlı Yapılacaklar

Bu bölüm gerçek route'lar üzerinden yazıldı.

### `/p/[projectId]/import`

Amaç: dokümanı sisteme giriş noktası yapmak.

Yapılacaklar:

- Yükleme sonrası anında parse özeti göster
- Chunk sayısı, başlıklar ve preview göster
- "AI ile analiz et" aksiyonunu netleştir
- Hata durumunda kullanıcıyı boş bırakma

Demo mesajı:

> Bu ekranda iş analizi dokümanını sisteme veriyoruz; sistem bunu teste dönüştürmeye başlıyor.

### `/p/[projectId]/approvals`

Amaç: AI önerisini insan onayına bağlamak.

Yapılacaklar:

- Kaynak metin ile AI önerisini aynı ekranda açık göster
- Approve/reject/edit akışını hızlandır
- Demo için split-view okunurluğunu artır
- "Bu öneri hangi kaynaktan çıktı?" görünürlüğünü yükselt

Demo mesajı:

> AI öneriyor, ama son kararı insan veriyor.

### `/p/[projectId]/scenarios`

Amaç: onaylanan çıktının kalıcı senaryo havuzuna dönüştüğünü göstermek.

Yapılacaklar:

- Onaylanan senaryoları kolay filtrelenir hale getir
- Tags, status ve source görünürlüğünü artır
- Demo için arama ve filtreler güvenilir çalışsın

Demo mesajı:

> Onaydan geçen her şey artık kurumsal test varlığına dönüşüyor.

### `/p/[projectId]/test-data` ve `/p/[projectId]/synthetic`

Amaç: sentetik veri tarafını sadece yan özellik değil, ana akış parçası yapmak.

Yapılacaklar:

- Demo veri setini önceden üret veya hızlı üretim sağla
- Veri kolonlarını iş diliyle göster
- Senaryoya bağlı veri setini görünür yap
- Başarılı/başarısız veri varyantı ayır

Demo mesajı:

> Aynı platform test verisini de güvenli şekilde üretiyor.

### `/p/[projectId]/automation` veya otomasyon üretim akışı

Amaç: onaylı test case'lerin gerçek artifact'e dönüştüğünü göstermek.

Yapılacaklar:

- Hangi test case'lerden üretim yapıldığı görünür olsun
- Gherkin, Playwright ve Java çıktıları sekmeli şekilde sunulsun
- Üretim sonrası doğrulama sonucu gösterilsin

Demo mesajı:

> Burada AI sadece fikir vermiyor, çalıştırılabilir çıktı üretiyor.

### `/p/[projectId]/executions` ve `/p/[projectId]/runs`

Amaç: gerçek koşum ve ölçüm.

Yapılacaklar:

- Tek tık run başlatma sadeleşsin
- Status, pass/fail ve duration net görünsün
- Son failed step ve note görünürlüğü artsın
- Demo sırasında gereksiz teknik detay gizlenebilsin

Demo mesajı:

> Üretilen otomasyon burada gerçekten koşuyor.

### `/p/[projectId]/ai-chat`

Amaç: LLM'in grounded ve güvenilir göründüğü ekran.

Yapılacaklar:

- Cevap içinde kaynak kayıtları göster
- "İlgili senaryolar", "İlgili koşular", "İlgili requirement'lar" blokları ekle
- Quick action'ları demo senaryosuna göre optimize et

Demo mesajı:

> Asistan, projedeki gerçek verilere dayanarak konuşuyor.

### `/p/[projectId]/reports` veya debug raporu ekranı

Amaç: yönetsel kapanış.

Yapılacaklar:

- Execution summary kısa ve etkili olsun
- AI debug sonucu kök neden + öneri + kaynak ile gelsin
- Coverage veya kalite özeti için 3-4 kart yeterli

Demo mesajı:

> Test sadece koşulmadı; sonuç yorumlandı ve aksiyona dönüştürüldü.

## 7. Backend Görev Listesi

## P0 Backend

- Doküman chunk indexleme servisi
- Semantic retrieval servisi
- Tool-calling orchestration katmanı
- AI cevaplarına kaynak metadata ekleme
- Execution result retrieval servisi
- Test data set retrieval servisi
- Demo seed script
- Otomasyon artifact doğrulama pipeline'ı

## P1 Backend

- Retrieval telemetry
- Prompt version alanı
- AI response evaluation log'u
- Provider fallback ve latency logları
- Demo mode için sabit örnek data loader

## Önerilen Yeni Servisler

- `backend/app/domains/ai/retrieval_service.py`
- `backend/app/domains/ai/tools.py`
- `backend/app/domains/ai/citation_formatter.py`
- `backend/app/domains/tspm/demo_seed_service.py`

## Önerilen Yeni Veri Yapısı

- `ai_context_chunks`
  - `id`
  - `project_id`
  - `source_type`
  - `source_id`
  - `chunk_text`
  - `metadata`
  - `embedding`

## 8. Frontend Görev Listesi

## P0 Frontend

- Import ekranında parse özeti
- Approval ekranında kaynak görünürlüğü
- Chat ekranında citation UI
- Execution ekranında sade özet
- Synthetic data ekranında preview + senaryo bağı

## P1 Frontend

- Demo mode badge
- Faster loading skeletons
- Basitleştirilmiş empty states
- Copy/export aksiyonları

## 9. Demo Günü 10 Dakikalık Script

## Dakika 0-1: Açılış

- Projeyi aç
- Bankacılık demo projesini göster
- Kısa ürün vaadini söyle:
  - dokümandan teste
  - testten otomasyona
  - otomasyondan analize

## Dakika 1-3: Doküman -> AI Öneri

- Import ekranında analist dokümanını yükle
- Parse ve analiz sonucunu göster
- Requirement/test case önerilerini göster

Vurgu:

> AI iş dilini test diline çeviriyor.

## Dakika 3-4: İnsan Onayı

- Approval ekranını aç
- Bir öneriyi onayla
- Gerekirse bir öneride küçük edit yap

Vurgu:

> AI destekli ama denetlenebilir.

## Dakika 4-6: Sentetik Veri

- Synthetic/test-data ekranını aç
- Oluşan veri setini göster
- Bu veri setinin senaryo ile bağını göster

Vurgu:

> Gerçek müşteri verisi kullanmadan güvenli test verisi üretebiliyoruz.

## Dakika 6-7: Otomasyon Üretimi

- Onaylı test case'lerden Gherkin/Playwright/Java üret
- En az bir artifact önizlemesi göster

Vurgu:

> AI fikir vermekle kalmıyor, çalıştırılabilir çıktıya dönüştürüyor.

## Dakika 7-8: Execution

- Run başlat
- Canlı sonucu veya tamamlanmış sonucu göster

Vurgu:

> Ürettiğimiz şeyi gerçekten koşturuyoruz.

## Dakika 8-10: AI Debug ve Kapanış

- AI chat/debug ekranını aç
- "Bu test neden fail oldu?" sorusunu sor
- Cevapta kaynakları göster

Kapanış cümlesi:

> Aynı platform analizi, veri üretimini, otomasyon üretimini ve kalite yorumunu tek akışta birleştiriyor.

## 10. Demo Fallback Planı

## Eğer AI gecikirse

- Önceden üretilmiş analiz ve senaryo sonuçlarını göster
- "Live yerine cached demo result" akışına geç

## Eğer execution gecikirse

- Son başarılı run sonucunu göster
- Canlı run yerine rapor ekranından ilerle

## Eğer sentetik veri üretimi yavaşlarsa

- Önceden seed edilmiş veri setine dön

## Eğer otomasyon üretimi parse edilemezse

- Önceden üretilmiş doğrulanmış artifact'i aç

## 11. Net Öncelik Sırası

Bu ay için resmi sıra:

1. Demo omurgası
2. Grounded LLM
3. Sentetik veri entegrasyonu
4. Otomasyon artifact doğrulama
5. Execution/report polish

## 12. Bir Sonraki Adım

Bu döküman tamamlandıktan sonra hemen çıkarılması gereken operasyonel çıktı:

- Haftalık issue listesi
- Sorumlu bazlı görev dağılımı
- Demo günü checklist
- Günlük standup için kısa takip tablosu
