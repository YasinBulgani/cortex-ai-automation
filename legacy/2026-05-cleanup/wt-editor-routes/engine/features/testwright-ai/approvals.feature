# Platform: BGTS Test Dönüşüm
# URL: http://localhost:3000
# Modül: Onay İş Akışı
# API: /api/v1/tspm/projects/{projectId}/approvals*

Feature: Onay İş Akışı Yönetimi
  AI tarafından üretilen test senaryolarının onay kuyruğunda
  incelenmesi, onaylanması veya reddedilmesi süreçleri test edilir.
  Split view ile kaynak doküman ve AI taslağı karşılaştırılır.

  Background:
    Given kullanıcı ana sayfadadır
    Given kullanıcı "/login" sayfasındadır
    When kullanıcı "[data-testid='email-input']" kutusuna "admin@example.com" yazar
    When kullanıcı "[data-testid='password-input']" kutusuna "admin123" yazar
    When kullanıcı "Giriş Yap" metnine tıklar

  # ─── ONAY KUYRUĞU ──────────────────────────────────────────────────

  Scenario: Onay kuyruğunu görüntüleme
    Given kullanıcı test projesinin "approvals" sayfasındadır
    Then URL "/approvals" içermelidir
    Then "[data-testid='approval-list']" elementi görünür olmalıdır

  Scenario: Bekleyen onay sayısını kontrol etme
    Given kullanıcı test projesinin "approvals" sayfasındadır
    Then "[data-testid='pending-count']" elementi görünür olmalıdır

  Scenario: Boş onay kuyruğu durumu
    Given kullanıcı test projesinin "approvals" sayfasındadır
    Then "[data-testid='empty-state'], [data-testid='approval-list']" elementi görünür olmalıdır

  # ─── ONAY DETAY — SPLIT VIEW ───────────────────────────────────────

  Scenario: Onay detayında split view görüntüleme
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid='approval-item']" seçicisini tıklar
    Then "[data-testid='split-view']" elementi görünür olmalıdır
    Then "[data-testid='source-panel']" elementi görünür olmalıdır
    Then "[data-testid='draft-panel']" elementi görünür olmalıdır

  Scenario: Kaynak doküman içeriğini inceleme
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid='approval-item']" seçicisini tıklar
    Then "[data-testid='source-panel']" elementi görünür olmalıdır

  Scenario: AI taslak içeriğini inceleme
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid='approval-item']" seçicisini tıklar
    Then "[data-testid='draft-panel']" elementi görünür olmalıdır

  # ─── ONAY KARARLARI ────────────────────────────────────────────────

  Scenario: Onay taslağını onaylama
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid='approval-item']" seçicisini tıklar
    When kullanıcı "Onayla" metnine tıklar
    Then "[data-testid='success-message'], [data-testid='approval-list']" elementi görünür olmalıdır

  Scenario: Onay taslağını reddetme
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid='approval-item']" seçicisini tıklar
    When kullanıcı "Reddet" metnine tıklar
    Then "[data-testid='success-message'], [data-testid='approval-list']" elementi görünür olmalıdır

  Scenario: Onay taslağını düzenleyerek onaylama
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid='approval-item']" seçicisini tıklar
    When kullanıcı "Düzenle" metnine tıklar
    When kullanıcı "[data-testid='draft-editor']" kutusuna "Düzenlenmiş senaryo içeriği" yazar
    When kullanıcı "Kaydet ve Onayla" metnine tıklar
    Then "[data-testid='success-message'], [data-testid='approval-list']" elementi görünür olmalıdır

  # ─── ONAY SONRASI DURUM ────────────────────────────────────────────

  Scenario: Onaylanan taslağın senaryo havuzuna eklenmesi
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid='approval-item']" seçicisini tıklar
    When kullanıcı "Onayla" metnine tıklar
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    Then "[data-testid='scenario-table']" elementi görünür olmalıdır

  Scenario: Reddedilen taslağın senaryo havuzuna eklenmemesi
    Given kullanıcı test projesinin "approvals" sayfasındadır
    When kullanıcı "[data-testid='approval-item']" seçicisini tıklar
    When kullanıcı "Reddet" metnine tıklar
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    Then "[data-testid='scenario-table']" elementi görünür olmalıdır
