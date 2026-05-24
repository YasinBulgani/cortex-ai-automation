# language: tr

Özellik: BDD Senaryo Üretimi (AI)
  Analiz dokümanından AI ile BDD senaryoları üretilir,
  seçilir ve veritabanına kaydedilir.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış
    Ve proje mevcut

  @high @pozitif
  Senaryo: Analiz dokümanından BDD senaryoları üretme
    Diyelim ki analiz metni hazırlanıyor:
      """
      Kullanıcı giriş sistemi: Kullanıcılar e-posta ve şifre ile giriş yapabilir.
      Başarısız giriş denemeleri 5'ten fazla ise hesap kilitlenir.
      Şifre en az 8 karakter olmalı ve büyük/küçük harf içermeli.
      """
    O zaman POST ".../generate-bdd" isteği gönderilir
    Ve yanıt kodu 200 olmalı
    Ve yanıtta "scenarios" listesi boş olmamalı
    Ve her senaryoda "title", "gherkin", "steps" alanları olmalı

  @medium @boundary
  Senaryo: Minimum karakter sınırı (10 karakter)
    Diyelim ki analiz metni "12345" (5 karakter)
    O zaman POST ".../generate-bdd" isteği gönderilir
    Ve yanıt kodu 422 olmalı

  @low @boundary
  Senaryo: Tam 10 karakter analiz metni
    Diyelim ki analiz metni "1234567890" (10 karakter)
    O zaman POST ".../generate-bdd" isteği gönderilir
    Ve yanıt kodu 200 olmalı

  @high @pozitif
  Senaryo: Üretilen senaryoların seçilerek kaydedilmesi
    Diyelim ki BDD üretimi sonucu 3 senaryo dönmüş
    Ve kullanıcı 2 senaryo seçmiş
    O zaman POST ".../save-bdd" ile seçilen senaryolar gönderilir
    Ve yanıt kodu 201 olmalı
    Ve 2 yeni senaryo "draft" statusünde kaydedilmiş olmalı

  @medium @pozitif
  Senaryo: Ek talimatlar ile BDD üretimi
    Diyelim ki analiz metni ve ek talimat "Sadece negatif senaryolara odaklan" verilmiş
    O zaman POST ".../generate-bdd" isteği gönderilir
    Ve yanıttaki senaryoların çoğunluğu negatif senaryolar olmalı

  @high @exception
  Senaryo: OpenAI API key ayarlanmamışken BDD üretimi
    Diyelim ki OPENAI_API_KEY ortam değişkeni boş
    O zaman POST ".../generate-bdd" isteği gönderilir
    Ve yanıt kodu 500 veya 400 olmalı
    Ve yanıtta "OPENAI_API_KEY" ile ilgili hata mesajı olmalı

  @medium @exception
  Senaryo: OpenAI geçersiz JSON yanıtı
    Diyelim ki OpenAI mock'u geçersiz JSON döndürüyor
    O zaman POST ".../generate-bdd" isteği gönderilir
    Ve yanıtta "geçerli JSON formatında değil" mesajı olmalı

  @medium @pozitif
  Senaryo: Regresyon seti AI önerisi — fallback mekanizması
    Diyelim ki OPENAI_API_KEY ayarlanmamış (fallback mod)
    Ve projede 5 senaryo mevcut
    O zaman POST ".../regression-sets/suggest" isteği gönderilir
    Ve yanıt kodu 200 olmalı
    Ve yanıtta "sets" listesi boş olmamalı
    Ve fallback template'lerinden deterministik setler dönmeli

  @medium @pozitif
  Senaryo: Regresyon önerisi geçersiz senaryo ID filtreleme
    Diyelim ki AI yanıtında projede olmayan senaryo ID'leri var
    O zaman bu ID'ler filtrelenmeli
    Ve yalnızca projede mevcut olan ID'ler setlere dahil olmalı
