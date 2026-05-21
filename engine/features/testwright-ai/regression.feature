# Platform: BGTS Test Dönüşüm
# URL: http://localhost:3000
# Modül: Regresyon Test Seti
# Amaç: Sprint sonu ve release öncesi tam regresyon doğrulaması

Feature: Regresyon Test Seti
  Platform genelinde kritik iş akışlarının uçtan uca doğrulanması.
  Her sprint sonunda ve release öncesinde çalıştırılır.
  Tüm modüllerin temel fonksiyonelliğini kapsar.

  Background:
    Given kullanıcı admin olarak giriş yapmıştır

  # ═══════════════════════════════════════════════════════════════════
  # REG-AUTH: Kimlik Doğrulama Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-AUTH-001 Başarılı giriş ve yönlendirme
    Then URL "/projects" içermelidir

  Scenario: REG-AUTH-002 Kullanıcı menüsü görünürlüğü
    Then "[data-testid='user-menu']" elementi görünür olmalıdır

  Scenario: REG-AUTH-003 Oturum kapatma akışı
    When kullanıcı "[data-testid='sidebar-btn-logout']" seçicisini tıklar
    Then URL "/login" içermelidir

  # ═══════════════════════════════════════════════════════════════════
  # REG-PRJ: Proje Yönetimi Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-PRJ-001 Proje listesi erişimi
    Given kullanıcı "/projects" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  Scenario: REG-PRJ-002 Yeni proje oluşturma
    Given kullanıcı "/projects" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  Scenario: REG-PRJ-003 Proje dashboard erişimi
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    Then "[data-testid='dashboard-stat-scenario-count']" elementi görünür olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # REG-SCN: Senaryo Yönetimi Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-SCN-001 Senaryo listesi erişimi
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    Then "[data-testid='scenario-table']" elementi görünür olmalıdır

  Scenario: REG-SCN-002 Yeni senaryo oluşturma
    Given kullanıcı test projesinin "scenarios/new" sayfasındadır
    When kullanıcı "[data-testid='scenario-title']" kutusuna "Regresyon: Login Senaryo" yazar
    When kullanıcı "[data-testid='scenario-description']" kutusuna "Regresyon test senaryosu" yazar
    When kullanıcı "Kaydet" metnine tıklar
    Then URL "/scenarios" içermelidir

  Scenario: REG-SCN-003 Senaryo arama fonksiyonu
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid='search-input']" kutusuna "Regresyon" yazar
    When kullanıcı "500" milisaniye bekler
    Then "[data-testid='scenario-table']" elementi görünür olmalıdır

  Scenario: REG-SCN-004 Senaryo detay görüntüleme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid^='scenarios-link-']" seçicisini tıklar
    Then "[data-testid='scenario-detail-page']" elementi görünür olmalıdır

  Scenario: REG-SCN-005 Senaryo düzenleme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid^='scenarios-link-']" seçicisini tıklar
    When kullanıcı "Düzenle" metnine tıklar
    When kullanıcı "[data-testid='scenario-edit-input-title']" kutusuna "Güncellenmiş Regresyon Senaryosu" yazar
    When kullanıcı "Kaydet" metnine tıklar
    Then URL "/scenarios" içermelidir

  Scenario: REG-SCN-006 Versiyon geçmişi
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid^='scenarios-link-']" seçicisini tıklar
    When kullanıcı "Versiyon Geçmişi" metnine tıklar
    Then "[data-testid='version-list']" elementi görünür olmalıdır

  Scenario: REG-SCN-007 BDD senaryo üretimi
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "BDD Üret" metnine tıklar
    When kullanıcı "[data-testid='analysis-text']" kutusuna "Müşteri hesap özeti görüntüleme" yazar
    When kullanıcı "Senaryoları Üret" metnine tıklar
    When kullanıcı "5000" milisaniye bekler
    Then "[data-testid='generated-scenarios'], [data-testid='scenario-generate-page']" elementi görünür olmalıdır

  Scenario: REG-SCN-008 Toplu seçim fonksiyonu
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid='select-all-checkbox']" seçicisini tıklar
    Then "[data-testid='bulk-actions']" elementi görünür olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # REG-APR: Onay İş Akışı Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-APR-001 Onay kuyruğu erişimi
    Given kullanıcı test projesinin "approvals" sayfasındadır
    Then "[data-testid='approval-list']" elementi görünür olmalıdır

  Scenario: REG-APR-002 Onay detay split view
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid^='approvals-card-']" seçicisini tıklar
    Then "[data-testid='split-view']" elementi görünür olmalıdır

  Scenario: REG-APR-003 Onaylama akışı
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid^='approvals-card-']" seçicisini tıklar
    When kullanıcı "Onayla" metnine tıklar
    Then "[data-testid='success-message'], [data-testid='approval-list']" elementi görünür olmalıdır

  Scenario: REG-APR-004 Reddetme akışı
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid^='approvals-card-']" seçicisini tıklar
    When kullanıcı "Reddet" metnine tıklar
    Then "[data-testid='success-message'], [data-testid='approval-list']" elementi görünür olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # REG-IMP: İçe Aktarma Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-IMP-001 İçe aktarma sayfası erişimi
    Given kullanıcı test projesinin "import" sayfasındadır
    Then "[data-testid='import-form']" elementi görünür olmalıdır

  Scenario: REG-IMP-002 Dosya yükleme alanı
    Given kullanıcı test projesinin "import" sayfasındadır
    Then "[data-testid='file-upload']" elementi görünür olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # REG-EXC: Test Koşusu Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-EXC-001 Koşu listesi erişimi
    Given kullanıcı test projesinin "runs" sayfasındadır
    Then "[data-testid='runs-page']" elementi görünür olmalıdır

  Scenario: REG-EXC-002 Koşu sayfası görüntüleme
    Given kullanıcı test projesinin "runs" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # REG-REG: Regresyon Seti Yönetimi Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-REG-001 Regresyon seti listesi
    Given kullanıcı test projesinin "regression" sayfasındadır
    Then "[data-testid='regression-page']" elementi görünür olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # REG-DATA: Sentetik Veri Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-DATA-001 Veri seti sayfası erişimi
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # REG-NAV: Navigasyon Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-NAV-001 Ana menü navigasyonu — Projeler
    When kullanıcı "Projeler" metnine tıklar
    When kullanıcı "1000" milisaniye bekler
    Then URL "/projects" içermelidir

  Scenario: REG-NAV-002 Proje içi navigasyon — Senaryolar
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    Then URL "/scenarios" içermelidir

  Scenario: REG-NAV-003 Proje içi navigasyon — Onaylar
    Given kullanıcı test projesinin "approvals" sayfasındadır
    Then URL "/approvals" içermelidir

  Scenario: REG-NAV-004 Proje içi navigasyon — İçe Aktarma
    Given kullanıcı test projesinin "import" sayfasındadır
    Then URL "/import" içermelidir

  # ═══════════════════════════════════════════════════════════════════
  # REG-API: API Endpoint Regresyonu
  # ═══════════════════════════════════════════════════════════════════

  Scenario: REG-API-001 Backend sağlık kontrolü
    Given kullanıcı ana sayfadadır
    When AI "GET /health endpoint'ini çağır ve status ok döndüğünü doğrula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır

  Scenario: REG-API-002 Auth API erişimi
    Given kullanıcı ana sayfadadır
    When AI "POST /api/v1/auth/login endpoint'ine geçerli kimlik bilgileri gönder ve token döndüğünü doğrula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır

  Scenario: REG-API-003 TSPM proje API erişimi
    Given kullanıcı ana sayfadadır
    When AI "GET /api/v1/tspm/projects endpoint'ini sorgula ve proje listesi döndüğünü doğrula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır

  Scenario: REG-API-004 TSPM senaryo API erişimi
    Given kullanıcı ana sayfadadır
    When AI "GET /api/v1/tspm/projects/{id}/scenarios endpoint'ini sorgula ve senaryo listesi döndüğünü doğrula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır

  Scenario: REG-API-005 Engine feature API erişimi
    Given kullanıcı ana sayfadadır
    When AI "GET /api/features/ endpoint'ini Engine üzerinde sorgula ve feature listesi döndüğünü doğrula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır
