# Nexus AI — Ürün Karar Özeti

Son güncelleme: 2026-04-22
Durum: Onaylı karar seti

## Çekirdek Karar

`Visium Intelligence`, ayrı bir ürün olarak değil, `Nexus AI` içinde yer alan
kurumsal AI kalite ve otomasyon modülü olarak konumlanır.

## Resmi Ürün Vaadi

`Nexus AI, kurum içi açık kaynak LLM altyapısı ile QA ve test operasyonlarını uçtan uca, sıfıra yakın insan müdahalesiyle otomatikleştirir.`

## İç Vizyon

Hedef durum:
- sıfır insan müdahalesine yaklaşan QA otomasyonu
- kritik akışlarda kontrollü otomasyon
- sürekli ölçülen ve optimize edilen LLM performansı

## Karar Tablosu

| Konu | Karar |
|------|-------|
| Ürün konumu | `Nexus AI` içinde modül |
| Dağıtım modeli | Kuruma özel enterprise kurulum |
| LLM mimarisi | Tamamen açık kaynak, self-hosted |
| Ana persona | QA Lead |
| Faz 1 modülleri | `AI Asistan`, `LLM Metrikleri`, `QA Orkestratör`, `NL Test Üretici`, `Akış Sihirbazı` |
| İlk değer | `LLM metrik görünürlüğü` |
| Ana KPI | Test üretim hızı |
| Dil | Sadece Türkçe |
| Paketleme | İlk sürüm tek paket |
| Prompt/model yönetimi | Yalnızca teknik ekip |
| Otomasyon seviyesi | Bazı akışlarda otomatik uygulama serbest |
| Çok ürünlü yapı | Korunacak |
| Ürün seçimi sonrası yapı | Ayrı ürün sayfası |
| Proje bağlama | Ürün bağlamına göre önerilen proje listesi |
| Artefakt saklama | Birden fazla yerde birlikte |
| En kritik güvenlik ilkesi | Müşteri verisi dış modele gitmemeli |

## Değiştirilmeyecek Ürün İlkeleri

1. Bu çözüm dış sağlayıcıya bağlı SaaS mantığıyla değil, kurum içi kurulum
mantığıyla tasarlanır.
2. Müşteri verisi hiçbir dış modele veya kontrolsüz üçüncü taraf servise
gönderilmez.
3. Kullanıcı ilk açılışta önce sohbet değil, ölçülebilir görünürlük görür.
4. Ürün, tek ürün değil çok ürünlü bağlamı desteklemek zorundadır.
5. Otomasyon iddiası yüksek tutulur; ama kritik sınırlar teknik ekip tarafından
yönetilir.

## Faz 1 İçin Yönetim Kararı

Faz 1'de tüm modüller görünür olacak; ancak ürünün birincil açılış deneyimi
`LLM Metrikleri` dashboard'u üzerinden kurgulanacaktır. Bunun nedeni, seçilen
ana persona olan `QA Lead` için ilk ve en güçlü değerin operasyonel görünürlük
olmasıdır.

## Ürün Başarısız Sayılacağı Durumlar

- Dashboard açılıyor ama test üretim hızına etki etmiyorsa
- LLM çıktıları ölçülüyor gibi görünse de eyleme dönüşmüyorsa
- Kullanıcı her modülde farklı kalite ve ton deneyimi yaşıyorsa
- Otomatik akışlar kurum güvenlik ilkelerini zorluyorsa
- Ürün seçimi sonrası bağlam kullanıcıyı hızlandırmak yerine yavaşlatıyorsa

## Faz 1 Dışında Tutulan Alanlar

- Son kullanıcıya açık prompt editörü
- Çok dilli arayüz
- Lisans paketleri (`Core`, `Pro`, `Enterprise`) ayrımı
- Müşteri tarafında serbest model yönetimi
- Sınırsız ve onaysız otomatik operasyon

## Bu Karar Setinin Sonucu

Ürün, "AI ile sohbet" deneyimi etrafında değil; "AI ile görünürlük,
orkestrasyon ve otomasyon" etrafında şekillenecektir.
