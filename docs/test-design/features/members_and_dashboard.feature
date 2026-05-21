# language: tr

Özellik: Proje Üyeleri ve Dashboard
  Projelere üye eklenir/çıkarılır ve dashboard istatistikleri takip edilir.

  Arka plan:
    Diyelim ki admin kullanıcısı oturum açmış
    Ve proje mevcut

  # ═══════════════════════════════════════════════════════════
  # Proje Üyeleri
  # ═══════════════════════════════════════════════════════════

  @high @pozitif
  Senaryo: Projeye üye ekleme
    Diyelim ki başka bir kullanıcı mevcut
    O zaman bu kullanıcı "operator" rolüyle projeye eklenir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "role" değeri "operator" olmalı

  @medium @pozitif
  Senaryo: Varsayılan rol kontrolü
    Diyelim ki üye ekleme isteğinde rol belirtilmemiş
    O zaman yanıtta "role" değeri "viewer" olmalı

  @high @pozitif
  Senaryo: Proje üyesi kaldırma
    Diyelim ki projede eklenen üye var
    O zaman DELETE ".../members/{id}" isteği gönderilir
    Ve yanıt kodu 204 olmalı
    Ve üye listesinde artık görünmemeli

  @medium @negatif
  Senaryo: Var olmayan üye kaldırma
    O zaman DELETE ".../members/nonexistent" isteği gönderilir
    Ve yanıt kodu 404 olmalı

  # ═══════════════════════════════════════════════════════════
  # Dashboard
  # ═══════════════════════════════════════════════════════════

  @high @pozitif
  Senaryo: Dashboard metrikleri doğru hesaplanır
    Diyelim ki projede 5 senaryo, 2 pending onay, 1 import ve 3 koşu var
    O zaman GET ".../dashboard" isteği gönderilir
    Ve yanıtta "scenario_count" değeri 5 olmalı
    Ve yanıtta "pending_approvals" değeri 2 olmalı
    Ve yanıtta "import_count" değeri 1 olmalı
    Ve yanıtta "execution_count" değeri 3 olmalı

  @medium @boundary
  Senaryo: Boş proje dashboard
    Diyelim ki yeni oluşturulmuş boş proje var
    O zaman GET ".../dashboard" isteği gönderilir
    Ve tüm sayaçlar 0 olmalı
    Ve "latest_run_pass_rate" null olmalı

  @high @pozitif
  Senaryo: Dashboard pass rate hesaplama
    Diyelim ki son koşuda 5 senaryo var: 3 passed, 2 failed
    O zaman GET ".../dashboard" isteği gönderilir
    Ve "latest_run_pass_rate" değeri 60.0 olmalı
