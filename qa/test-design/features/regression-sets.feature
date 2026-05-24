# language: tr

Özellik: Regresyon Setleri ve AI Önerileri
  Senaryolar regresyon setlerine gruplandırılır.
  AI modeli mevcut senaryoları analiz ederek set önerileri sunar.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış
    Ve projede en az 5 senaryo mevcut

  @high @pozitif
  Senaryo: Yeni regresyon seti oluşturma
    Diyelim ki set adı "Smoke Test Seti" olarak belirleniyor
    O zaman POST ".../regression-sets" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "scenario_count" değeri 0 olmalı

  @high @pozitif
  Senaryo: Regresyon setine senaryo ekleme
    Diyelim ki "Smoke Test Seti" mevcut
    Ve 2 senaryo ID'si seçilmiş
    O zaman POST ".../regression-sets/{id}/add" isteği gönderilir
    Ve yanıtta "count" değeri 2 olmalı

  @medium @boundary
  Senaryo: Aynı senaryoyu tekrar ekleme (idempotent)
    Diyelim ki "Smoke Test Seti"nde 2 senaryo var
    Ve aynı 2 senaryo ID'si ile tekrar ekleme isteği gönderilir
    O zaman yanıtta "count" değeri hâlâ 2 olmalı

  @medium @pozitif
  Senaryo: AI regresyon seti önerisi
    Diyelim ki projede çeşitli konularda senaryolar mevcut
    O zaman POST ".../regression-sets/suggest" isteği gönderilir
    Ve yanıt kodu 200 olmalı
    Ve yanıtta "sets" listesi boş olmamalı
    Ve her öneride "name" ve "scenario_ids" alanları olmalı

  @medium @negatif
  Senaryo: Senaryo olmayan projede AI önerisi
    Diyelim ki projede hiç senaryo yok
    O zaman POST ".../regression-sets/suggest" isteği gönderilir
    Ve yanıt kodu 400 olmalı
    Ve yanıtta "en az bir senaryo olmalı" mesajı bulunmalı

  @high @pozitif
  Senaryo: AI önerilerini kabul etme
    Diyelim ki AI 2 set önerisi döndürmüş
    O zaman POST ".../regression-sets/accept-suggestions" ile öneriler gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta 2 yeni set oluşturulmuş olmalı
