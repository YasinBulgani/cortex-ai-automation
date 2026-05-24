# language: tr

Özellik: Zamanlamalar ve Test Verisi Yönetimi
  Cron ifadeleri ile periyodik koşular zamanlanır.
  Test veri setleri oluşturulur ve senaryolara parametrik olarak bağlanır.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış
    Ve projede senaryolar mevcut

  # ═══════════════════════════════════════════════════════════
  # Zamanlamalar
  # ═══════════════════════════════════════════════════════════

  @high @pozitif
  Senaryo: Zamanlama oluşturma
    Diyelim ki zamanlama verisi hazırlanıyor
    Ve zamanlama adı "Gece Regresyon Koşusu" olarak belirleniyor
    Ve cron ifadesi "0 2 * * *" olarak belirleniyor
    Ve 3 senaryo ID'si ekleniyor
    O zaman POST ".../schedules" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "is_active" değeri true olmalı

  @high @pozitif
  Senaryo: Zamanlama tetikleme ile koşu oluşturma
    Diyelim ki aktif zamanlama mevcut ve senaryoları tanımlı
    O zaman POST ".../schedules/{id}/trigger" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta koşu adı "Scheduled:" ile başlamalı
    Ve zamanlama last_run_at güncellenmeli

  @high @negatif
  Senaryo: Senaryosuz zamanlama tetikleme
    Diyelim ki zamanlama mevcut ama scenario_ids boş ve regression_set_id null
    O zaman POST ".../schedules/{id}/trigger" isteği gönderilir
    Ve yanıt kodu 400 olmalı
    Ve yanıtta "Zamanlamada senaryo bulunamadı" mesajı olmalı

  @medium @pozitif
  Senaryo: Zamanlama regression set'ten senaryo çeker
    Diyelim ki zamanlama scenario_ids boş ama regression_set_id dolu
    Ve ilgili regresyon setinde 3 senaryo var
    O zaman zamanlama tetiklendiğinde
    Ve oluşturulan koşuda 3 senaryo olmalı

  @medium @boundary
  Senaryo: Boş cron ifadesi ile zamanlama oluşturulamaz
    Diyelim ki cron ifadesi "" olarak belirleniyor
    O zaman POST ".../schedules" isteği gönderilir
    Ve yanıt kodu 422 olmalı

  # ═══════════════════════════════════════════════════════════
  # Test Verisi Yönetimi
  # ═══════════════════════════════════════════════════════════

  @high @pozitif
  Senaryo: Test veri seti oluşturma
    Diyelim ki veri seti verisi hazırlanıyor
    Ve veri seti adı "Login Test Verileri" olarak belirleniyor
    Ve kolonlar tanımlanıyor:
      | name     |
      | username |
      | password |
    Ve satırlar tanımlanıyor:
      | username | password    |
      | user1    | pass123     |
      | user2    | password456 |
      | admin    | admin123    |
    O zaman POST ".../test-data" isteği gönderilir
    Ve yanıt kodu 201 olmalı

  @high @pozitif
  Senaryo: Senaryoya veri bağlama
    Diyelim ki "Login Testi" senaryosu mevcut
    Ve senaryoda "{{kullanici}}" ve "{{sifre}}" yer tutucuları var
    Ve "Login Test Verileri" veri seti mevcut
    O zaman senaryo-veri bağlama isteği gönderilir
    Ve parameter_mapping {"kullanici": "username", "sifre": "password"} olarak ayarlanır
    Ve yanıt kodu 201 olmalı

  @high @pozitif
  Senaryo: Parametre genişletme (expanded scenario)
    Diyelim ki senaryo-veri bağlaması yapılmış
    Ve veri setinde 3 satır var
    O zaman GET ".../scenarios/{id}/expanded" isteği gönderilir
    Ve yanıtta "expanded_rows" listesinde 3 satır olmalı
    Ve her satırın adımlarında "{{kullanici}}" yerine gerçek değerler olmalı

  @medium @negatif
  Senaryo: Var olmayan veri seti ile bağlama
    Diyelim ki geçersiz data_set_id ile bağlama isteği gönderiliyor
    O zaman yanıt kodu 404 olmalı
    Ve yanıtta "Veri seti bulunamadı" mesajı olmalı
