# language: tr

Özellik: Akışlar, Entegrasyonlar ve API Test Koleksiyonları
  Test akışları görsel editörde düzenlenir.
  Dış araçlarla entegrasyon kurulur.
  API endpoint'leri koleksiyon olarak test edilir.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış
    Ve proje mevcut

  # ═══════════════════════════════════════════════════════════
  # Akışlar
  # ═══════════════════════════════════════════════════════════

  @high @pozitif
  Senaryo: Yeni akış oluşturma
    Diyelim ki akış adı "Login Akışı" olarak belirleniyor
    O zaman POST ".../flows" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "name" değeri "Login Akışı" olmalı

  @high @pozitif
  Senaryo: Akış grafı güncelleme
    Diyelim ki mevcut bir akış var
    Ve nodes ve edges verisi hazırlanıyor
    O zaman PUT ".../flows/{id}/graph" isteği gönderilir
    Ve yanıt kodu 200 olmalı
    Ve akış detayında güncel nodes ve edges dönmeli

  @medium @boundary
  Senaryo: Boş isimle akış oluşturulamaz
    Diyelim ki akış adı "" olarak belirleniyor
    O zaman POST ".../flows" isteği gönderilir
    Ve yanıt kodu 422 olmalı

  # ═══════════════════════════════════════════════════════════
  # Entegrasyonlar
  # ═══════════════════════════════════════════════════════════

  @medium @pozitif
  Senaryo: Entegrasyon oluşturma
    Diyelim ki provider "jira" ve config belirlenmiş
    O zaman POST ".../integrations" isteği gönderilir
    Ve yanıt kodu 201 olmalı

  @medium @pozitif
  Senaryo: Entegrasyon sync
    Diyelim ki mevcut entegrasyon var
    O zaman POST ".../integrations/{id}/sync" isteği gönderilir
    Ve yanıtta "last_sync_at" güncellenmeli

  # ═══════════════════════════════════════════════════════════
  # API Test Koleksiyonları
  # ═══════════════════════════════════════════════════════════

  @high @pozitif
  Senaryo: API test koleksiyonu oluşturma
    Diyelim ki koleksiyon adı "Auth API" ve base_url "http://localhost:8000"
    O zaman POST ".../api-tests/collections" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "request_count" değeri 0 olmalı

  @high @pozitif
  Senaryo: Koleksiyona request ekleme ve çalıştırma
    Diyelim ki mevcut koleksiyona "Health Check" request'i eklenmiş
    Ve method "GET", path "/health"
    O zaman koleksiyon çalıştırılır
    Ve yanıtta results listesinde 1 sonuç olmalı
    Ve sonuçta "status_code" ve "duration_ms" alanları dolu olmalı

  @medium @exception
  Senaryo: Erişilemeyen URL ile koleksiyon çalıştırma
    Diyelim ki base_url "http://unreachable:9999" olan koleksiyon var
    O zaman koleksiyon çalıştırılır
    Ve sonuçta "passed" değeri false olmalı
    Ve "error" alanı dolu olmalı
