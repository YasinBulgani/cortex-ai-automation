# Platform: BGTS Test Dönüşüm
# URL: http://localhost:8000 (Backend), http://localhost:5001 (Engine)
# Modül: API Endpoint Testleri — Deterministik httpx
# Step dosyası: steps/bgts_api_steps.py

@api
Feature: API Endpoint Doğrulama Testleri
  Backend (FastAPI :8000) ve Engine (Flask :5001) API endpoint'lerinin
  doğru çalıştığını deterministik httpx istemcisi ile doğrular.

  # ═══════════════════════════════════════════════════════════════════
  # SAĞLIK KONTROLLERİ
  # ═══════════════════════════════════════════════════════════════════

  @smoke @critical
  Scenario: Backend sağlık kontrolü
    When API sağlık kontrolü yapılır
    Then API yanıt kodu 200 olmalıdır

  @smoke @critical
  Scenario: Backend hazırlık kontrolü
    When API hazırlık kontrolü yapılır
    Then API yanıt kodu 200 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # AUTH API
  # ═══════════════════════════════════════════════════════════════════

  @smoke @critical
  Scenario: Geçerli kimlik bilgileriyle giriş
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    Then API yanıt kodu 200 olmalıdır
    And API yanıtı "access_token" alanını içermelidir

  @negative
  Scenario: Geçersiz parola ile giriş reddi
    When API ile geçersiz parola ile giriş yapılır
    Then API yanıt kodu 401 olmalıdır

  @smoke
  Scenario: Kullanıcı bilgisi sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile kullanıcı bilgisi sorgulanır
    Then API yanıt kodu 200 olmalıdır
    And API yanıtı "email" alanını içermelidir

  @negative
  Scenario: Token olmadan kullanıcı bilgisi erişim engeli
    When API ile token olmadan kullanıcı bilgisi sorgulanır
    Then API yanıt kodu 401 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # PROJE API
  # ═══════════════════════════════════════════════════════════════════

  @smoke
  Scenario: Proje listesi sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile proje listesi sorgulanır
    Then API yanıt kodu 200 olmalıdır

  @critical
  Scenario: Yeni proje oluşturma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    Then API yanıt kodu 201 olmalıdır
    And API yanıtı "id" alanını içermelidir

  Scenario: Proje dashboard sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile proje dashboard sorgulanır
    Then API yanıt kodu 200 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # SENARYO API
  # ═══════════════════════════════════════════════════════════════════

  @smoke
  Scenario: Senaryo listesi sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile senaryo listesi sorgulanır
    Then API yanıt kodu 200 olmalıdır

  @critical
  Scenario: Yeni senaryo oluşturma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile yeni senaryo oluşturulur
    Then API yanıt kodu 201 olmalıdır

  Scenario: Senaryo güncelleme
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile yeni senaryo oluşturulur
    When API ile senaryo güncellenir
    Then API yanıt kodu 200 olmalıdır

  Scenario: Senaryoları toplu silme
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile yeni senaryo oluşturulur
    When API ile senaryolar toplu silinir
    Then API yanıtı başarılı olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # ONAY API
  # ═══════════════════════════════════════════════════════════════════

  Scenario: Onay listesi sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile onay listesi sorgulanır
    Then API yanıt kodu 200 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # KOŞU API
  # ═══════════════════════════════════════════════════════════════════

  Scenario: Koşu oluşturma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile yeni senaryo oluşturulur
    When API ile koşu oluşturulur
    Then API yanıt kodu 201 olmalıdır

  Scenario: Koşu trendleri sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile koşu trendleri sorgulanır
    Then API yanıt kodu 200 olmalıdır

  Scenario: Flaky testler sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile flaky testler sorgulanır
    Then API yanıt kodu 200 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # REGRESYON API
  # ═══════════════════════════════════════════════════════════════════

  Scenario: Regresyon seti oluşturma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile regresyon seti oluşturulur
    Then API yanıt kodu 201 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # ZAMANLAMA API
  # ═══════════════════════════════════════════════════════════════════

  Scenario: Zamanlama oluşturma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile yeni senaryo oluşturulur
    When API ile zamanlama oluşturulur
    Then API yanıt kodu 201 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # GEREKSİNİM VE KAPSAM API
  # ═══════════════════════════════════════════════════════════════════

  Scenario: Gereksinim oluşturma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile gereksinim oluşturulur
    Then API yanıt kodu 201 olmalıdır

  Scenario: Kapsam matrisi sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile kapsam matrisi sorgulanır
    Then API yanıt kodu 200 olmalıdır

  Scenario: Kapsam boşlukları sorgulama
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile kapsam boşlukları sorgulanır
    Then API yanıt kodu 200 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # API TEST KOLEKSİYONU
  # ═══════════════════════════════════════════════════════════════════

  Scenario: Koleksiyon oluşturma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile koleksiyon oluşturulur
    Then API yanıt kodu 201 olmalıdır

  Scenario: Koleksiyon çalıştırma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile koleksiyon oluşturulur
    When API ile koleksiyon çalıştırılır
    Then API yanıtı başarılı olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # ENTEGRASYON API
  # ═══════════════════════════════════════════════════════════════════

  Scenario: Entegrasyon oluşturma
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    When API ile yeni proje oluşturulur
    When API ile entegrasyon oluşturulur
    Then API yanıt kodu 201 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # ENGINE API
  # ═══════════════════════════════════════════════════════════════════

  @smoke
  Scenario: Engine feature listesi sorgulama
    When Engine ile feature listesi sorgulanır
    Then API yanıtı başarılı olmalıdır

  Scenario: Engine regresyon setleri sorgulama
    When Engine ile regresyon setleri sorgulanır
    Then API yanıtı başarılı olmalıdır
