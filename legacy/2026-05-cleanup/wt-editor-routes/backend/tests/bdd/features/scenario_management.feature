# language: en

Feature: Senaryo Yönetimi
  Senaryolar proje kapsamında oluşturulur, güncellenir, aranır,
  versiyonlanır ve toplu işlemlerle yönetilir.

  Geçmiş:
    Diyelim ki kullanıcı oturum açmış ve geçerli JWT token'a sahip
    Ve "Test Projesi" adıyla bir proje mevcut

  @critical @pozitif
  Scenario: Yeni senaryo oluşturma ve varsayılan değerler
    Given senaryo oluşturma verisi hazırlanıyor
    And senaryo başlığı "Login Fonksiyonellik Testi" olarak belirleniyor
    And senaryo açıklaması "Giriş ekranı doğrulama testi" olarak belirleniyor
    And adımlar listesi hazırlanıyor:
      | order | keyword | text                                |
      | 1     | Given   | Kullanıcı login sayfasında          |
      | 2     | When    | Geçerli bilgilerle giriş yapıyor    |
      | 3     | Then    | Ana sayfa görüntülenir              |
    When proje altında POST ".../scenarios" isteği gönderilir
    Then yanıt kodu 201 olmalı
    And yanıtta "status" değeri "draft" olmalı
    And yanıtta "current_version" değeri 1 olmalı

  @critical @pozitif
  Scenario: Senaryo güncelleme ile otomatik versiyonlama
    Given projede "Login Testi" başlıklı senaryo mevcut
    And senaryonun mevcut versiyonu 1
    When senaryo başlığı "Login Testi v2" olarak güncellenir
    Then yanıtta "current_version" değeri 2 olmalı
    And senaryo versiyon listesinde versiyon 1 kaydı bulunmalı
    And versiyon 1 kaydında eski başlık "Login Testi" olmalı

  @high @pozitif
  Scenario: Senaryolar başlık ile aranabilir
    Given projede şu senaryolar mevcut:
      | başlık              |
      | Login Testi         |
      | Ödeme Akışı Testi   |
      | Login Hata Senaryosu |
    When senaryo listesi "?q=Login" parametresiyle çağrılır
    Then yanıtta 2 senaryo dönmeli
    And yanıttaki tüm senaryoların başlığında "Login" geçmeli

  @high @pozitif
  Scenario: Toplu senaryo silme
    Given projede 3 senaryo oluşturulmuş: "A", "B", "C"
    And senaryoların ID'leri alınmış
    When "A" ve "B" senaryolarının ID'leri ile bulk-delete isteği gönderilir
    Then yanıt kodu 204 olmalı
    And senaryo listesinde yalnızca "C" senaryosu kalmalı

  @high @negatif
  Scenario: Farklı projeye ait senaryoya erişim engellenir
    Given "Proje-A" ve "Proje-B" mevcut
    And "Proje-A" altında "Test-A" senaryosu var
    When "Proje-B" ID'si ile "Test-A" senaryosuna erişim denenir
    Then yanıt kodu 404 olmalı
    And yanıtta "Senaryo bulunamadı" mesajı olmalı

  @high @boundary
  Scenario: Boş başlıkla senaryo oluşturulamaz
    Given senaryo oluşturma verisi hazırlanıyor
    And senaryo başlığı "" olarak belirleniyor
    When proje altında POST ".../scenarios" isteği gönderilir
    Then yanıt kodu 422 olmalı

  @medium @pozitif
  Scenario: Versiyon karşılaştırma (diff)
    Given projede senaryo mevcut ve 2 kez güncellenmiş
    And versiyon 1 başlığı "Orijinal Başlık"
    And versiyon 2 başlığı "Güncel Başlık"
    When versiyon 1 ve 2 diff endpoint'i çağrılır
    Then yanıtta "title_changed" değeri true olmalı
    And yanıtta "v1_snapshot" ve "v2_snapshot" dolu olmalı

  @high @negatif
  Scenario: Toplu silmede farklı projeye ait ID yok sayılır
    Given "Proje-A" ve "Proje-B" mevcut
    And "Proje-B" altında "Korunan Senaryo" var
    When "Proje-A" altında "Korunan Senaryo"nun ID'si ile bulk-delete gönderilir
    Then "Proje-B" altında "Korunan Senaryo" hâlâ mevcut olmalı
