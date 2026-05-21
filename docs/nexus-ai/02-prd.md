# Nexus AI — Visium Intelligence PRD

Durum: Faz 1 ürün gereksinim dokümanı
Hedef sürüm: `v1-enterprise`

## 1. Problem Tanımı

Kurumsal test ekipleri, özellikle QA Lead seviyesinde, aşağıdaki sorunları aynı
anda yaşamaktadır:

- LLM kullanımı görünür değildir; hangi modelin ne kadar işe yaradığı ölçülemez.
- Test üretim süreçleri parçalıdır; doküman analizi, test case, Gherkin ve kod
  üretimi aynı hatta bağlanamaz.
- AI çıktıları operasyonel karara dönüşmez; öneri kalır, sistem etkisi sınırlı
  olur.
- Çok ürünlü organizasyonlarda bağlam yönetimi zayıftır; aynı AI akışı farklı
  ürünler için tekrar tekrar kurulmak zorunda kalır.
- Güvenlik ve regülasyon kısıtları nedeniyle dış LLM kullanımı kabul edilemez.

## 2. Ürün Hedefi

`Nexus AI` içinde yer alan `Visium Intelligence`, QA Lead'in test operasyonunu
ölçmesini, hızlandırmasını ve belirli sınırlar içinde otomatikleştirmesini
sağlar.

## 3. Başarı Tanımı

### Ana KPI

- Test üretim hızı

### Destek KPI'lar

- LLM dashboard açılışından aksiyona geçiş oranı
- Test artefaktı başına manuel düzenleme oranı
- Otomatik tamamlanan pipeline yüzdesi
- Prompt veya model değişimi sonrası kalite sapma oranı
- Haftalık aktif QA Lead kullanım oranı

## 4. Ana Persona

### Birincil Persona: QA Lead

Sorumluluklar:
- test süreçlerini izlemek
- kalite risklerini erken görmek
- ekip verimliliğini artırmak
- hangi projede hangi AI çıktısının işe yaradığını anlamak
- gerektiğinde otomasyonu devreye almak

Beklentiler:
- ilk 5 dakikada görünür değer
- farklı ürünlerde bağlam kaybı yaşamamak
- ekibin ürettiği AI çıktıları üzerinde kontrol
- güvenli ve denetlenebilir kullanım

## 5. Ürün Vaadi

Kullanıcıya verilen temel söz:
- LLM kullanımını görünür kılar
- test üretim sürecini hızlandırır
- test operasyonunu akış bazlı yönetir
- kritik olmayan alanlarda sıfıra yakın insan müdahalesi sağlar

## 6. Modül Kapsamı

### 6.1 `LLM Metrikleri`

Amaç:
- QA Lead için ilk değer ekranı olmak

Kapsam:
- model bazlı kullanım hacmi
- görev bazlı başarı veya kabul oranı
- latency
- token ve kaynak tüketimi
- prompt versiyon etkisi
- test üretim hızı metriği
- proje ve ürün bazlı filtreleme

Minimum kabul kriterleri:
- kullanıcı 3 tıklamadan az hareketle ürün ve proje filtreleyebilmeli
- en az son 7 ve 30 gün görünümü olmalı
- metrik ekranından ilgili aksiyon ekranına geçiş sağlanmalı

### 6.2 `AI Asistan`

Amaç:
- bağlama duyarlı sohbeti operasyonel aksiyona dönüştürmek

Kapsam:
- ürün ve proje bağlamlı sohbet
- test case, Gherkin, assertion, debug, regresyon önerisi
- metrikten gelen sinyale göre öneri sunma
- çıktıyı proje artefaktına dönüştürme

Minimum kabul kriterleri:
- kullanıcı konuşmadan aksiyon başlatabilmeli
- asistan öneriden doğrudan `NL Test Üretici` veya `QA Orkestratör`e geçirebilmeli
- sistem, bağlam dışı uydurma üretmemeli

### 6.3 `QA Orkestratör`

Amaç:
- çok adımlı AI görevlerini tek akış olarak yürütmek

Kapsam:
- doküman analizi
- test case üretimi
- Gherkin üretimi
- test kodu üretimi
- assertion analizi
- debug önerisi
- regresyon önerisi
- retry ve fallback
- teknik ekip tanımlı otomatik uygulama sınırları

Minimum kabul kriterleri:
- pipeline durumu görünür olmalı
- her adım loglanmalı
- başarısız adım tüm akışı körleştirmemeli

### 6.4 `NL Test Üretici`

Amaç:
- doğal dilden çalıştırılabilir test artefaktı üretmek

Kapsam:
- requirement → test case
- requirement → Gherkin
- requirement → Playwright veya Python test
- risk bazlı senaryo zenginleştirme
- ürün bağlamlı şablon kullanımı

Minimum kabul kriterleri:
- üretilen çıktı kaydedilebilir olmalı
- çıktı revize edilebilir olmalı
- artefakt birden fazla hedefe yazılabilmeli

### 6.5 `Akış Sihirbazı`

Amaç:
- kullanıcıyı ürün seçimi, proje bağlama ve ilk aksiyona hızlı taşımak

Kapsam:
- ürün seçimi
- ürün bağlamlı proje önerileri
- başlangıç yolu
- ilk önerilen aksiyon
- onboarding adım durumu

Minimum kabul kriterleri:
- sağ panel statik bilgi değil, gerçek yönlendirme olmalı
- kullanıcı ilk oturumunda en az bir işe yarar aksiyona yönlendirilmeli

## 7. Bilgi Mimarisi

Akış:
1. `Nexus AI` giriş yüzeyi
2. ürün seçimi
3. ürün özel landing sayfası
4. `LLM Metrikleri` dashboard
5. aksiyon modülleri: asistan, orkestratör, üretici

## 8. Ürün Sayfaları

### 8.1 Ürün Seçim Sayfası

İçerik:
- ürün kartları
- ürün kısa değeri
- ürün bağlamlı önerilen başlangıç

### 8.2 Ürün Landing Sayfası

İçerik:
- ürün başlığı
- modül kartları
- önerilen proje listesi
- sağ tarafta başlangıç yolu
- birincil CTA: `LLM Metriklerine Git`

### 8.3 LLM Metrik Dashboard

İçerik:
- üst filtreler
- özet kartlar
- hız ve kalite grafikleri
- sorunlu akışlar
- önerilen aksiyonlar

### 8.4 AI Asistan

İçerik:
- sohbet paneli
- bağlam etiketi
- önerilen aksiyon düğmeleri
- artefakt oluşturma kısa yolları

### 8.5 QA Orkestratör

İçerik:
- pipeline başlatma
- adım durumları
- çıktı önizleme
- otomatik uygulama durumu
- hata ve retry paneli

### 8.6 NL Test Üretici

İçerik:
- girdi alanı
- çıktı türü seçimi
- sonuç paneli
- refine ve export eylemleri

## 9. Veri ve Saklama Politikası

Artefaktlar aşağıdaki hedeflerde birlikte saklanabilmeli:
- sohbet geçmişi
- proje altı kayıtlı içerik
- dosya ve git çıktısı

Bu nedenle ürünün storage tasarımı çoklu hedef desteklemelidir.

## 10. Güvenlik ve Uyum

Zorunlu koşullar:
- müşteri verisi dış modele gitmez
- inference yalnızca kurum içi açık kaynak model katmanında yapılır
- veri prompta gitmeden önce maskeleme ve sınıflandırmadan geçer
- prompt ve model yönetimi yalnızca teknik ekiptedir
- otomatik uygulama whitelist ve kural sınırları içindedir
- tüm önemli aksiyonlar audit log'a yazılır

## 11. V1 Kapsam Dışı

- çok dilli destek
- son kullanıcı prompt editörü
- paket bazlı fiyatlama
- kurum adminine açık model yönetimi
- denetimsiz tam otomasyon

## 12. V1 Kabul Kriteri

Ürün `v1` kabul edilir, eğer:
- ürün seçimi sonrası kullanıcı ayrı ürün sayfasına giderse
- QA Lead ilk 5 dakikada anlamlı `LLM Metrikleri` görebilirse
- önerilen projeler ürün bağlamına göre çalışırsa
- en az bir uçtan uca AI pipeline tamamlanırsa
- üretilen artefakt en az iki hedefte saklanabiliyorsa
- müşteri verisinin dış modele gitmediği mimari ve log düzeyinde doğrulanabilirse
