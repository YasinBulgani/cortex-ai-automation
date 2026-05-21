# language: tr

Özellik: Senaryo Yönetimi
  Senaryolar proje kapsamında oluşturulur, güncellenir, aranır,
  versiyonlanır ve toplu işlemlerle yönetilir.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış ve geçerli JWT token'a sahip
    Ve "Test Projesi" adıyla bir proje mevcut

  @critical @pozitif
  Senaryo: Yeni senaryo oluşturma ve varsayılan değerler
    Diyelim ki senaryo oluşturma verisi hazırlanıyor
    Ve senaryo başlığı "Login Fonksiyonellik Testi" olarak belirleniyor
    Ve senaryo açıklaması "Giriş ekranı doğrulama testi" olarak belirleniyor
    Ve adımlar listesi hazırlanıyor:
      | order | keyword | text                                |
      | 1     | Given   | Kullanıcı login sayfasında          |
      | 2     | When    | Geçerli bilgilerle giriş yapıyor    |
      | 3     | Then    | Ana sayfa görüntülenir              |
    O zaman proje altında POST ".../scenarios" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "status" değeri "draft" olmalı
    Ve yanıtta "current_version" değeri 1 olmalı

  @critical @pozitif
  Senaryo: Senaryo güncelleme ile otomatik versiyonlama
    Diyelim ki projede "Login Testi" başlıklı senaryo mevcut
    Ve senaryonun mevcut versiyonu 1
    O zaman senaryo başlığı "Login Testi v2" olarak güncellenir
    Ve yanıtta "current_version" değeri 2 olmalı
    Ve senaryo versiyon listesinde versiyon 1 kaydı bulunmalı
    Ve versiyon 1 kaydında eski başlık "Login Testi" olmalı

  @high @pozitif
  Senaryo: Senaryolar başlık ile aranabilir
    Diyelim ki projede şu senaryolar mevcut:
      | başlık              |
      | Login Testi         |
      | Ödeme Akışı Testi   |
      | Login Hata Senaryosu |
    O zaman senaryo listesi "?q=Login" parametresiyle çağrılır
    Ve yanıtta 2 senaryo dönmeli
    Ve yanıttaki tüm senaryoların başlığında "Login" geçmeli

  @high @pozitif
  Senaryo: Toplu senaryo silme
    Diyelim ki projede 3 senaryo oluşturulmuş: "A", "B", "C"
    Ve senaryoların ID'leri alınmış
    O zaman "A" ve "B" senaryolarının ID'leri ile bulk-delete isteği gönderilir
    Ve yanıt kodu 204 olmalı
    Ve senaryo listesinde yalnızca "C" senaryosu kalmalı

  @high @negatif
  Senaryo: Farklı projeye ait senaryoya erişim engellenir
    Diyelim ki "Proje-A" ve "Proje-B" mevcut
    Ve "Proje-A" altında "Test-A" senaryosu var
    O zaman "Proje-B" ID'si ile "Test-A" senaryosuna erişim denenir
    Ve yanıt kodu 404 olmalı
    Ve yanıtta "Senaryo bulunamadı" mesajı olmalı

  @high @boundary
  Senaryo: Boş başlıkla senaryo oluşturulamaz
    Diyelim ki senaryo oluşturma verisi hazırlanıyor
    Ve senaryo başlığı "" olarak belirleniyor
    O zaman proje altında POST ".../scenarios" isteği gönderilir
    Ve yanıt kodu 422 olmalı

  @medium @pozitif
  Senaryo: Versiyon karşılaştırma (diff)
    Diyelim ki projede senaryo mevcut ve 2 kez güncellenmiş
    Ve versiyon 1 başlığı "Orijinal Başlık"
    Ve versiyon 2 başlığı "Güncel Başlık"
    O zaman versiyon 1 ve 2 diff endpoint'i çağrılır
    Ve yanıtta "title_changed" değeri true olmalı
    Ve yanıtta "v1_snapshot" ve "v2_snapshot" dolu olmalı

  @high @negatif
  Senaryo: Toplu silmede farklı projeye ait ID yok sayılır
    Diyelim ki "Proje-A" ve "Proje-B" mevcut
    Ve "Proje-B" altında "Korunan Senaryo" var
    O zaman "Proje-A" altında "Korunan Senaryo"nun ID'si ile bulk-delete gönderilir
    Ve "Proje-B" altında "Korunan Senaryo" hâlâ mevcut olmalı
