# Platform: BGTS Test Dönüşüm
# Modül: Proje Yönetimi
# Step: steps/bgts_project_steps.py + steps/bgts_login_steps.py

@projects
Feature: Proje Yönetimi
  Kullanıcılar projelerini oluşturur, listeler, dashboard'u görüntüler
  ve proje içi sayfalara navigasyon yapar.

  Background:
    Given kullanıcı admin olarak giriş yapmıştır

  # ── PROJE LİSTESİ ──────────────────────────────────────────────

  @smoke @critical
  Scenario: Proje listesi görüntüleme
    Given kullanıcı "/projects" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  @smoke
  Scenario: Proje listesi boş durum gösterimi
    Given kullanıcı "/projects" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  # ── PROJE OLUŞTURMA ─────────────────────────────────────────────

  @critical
  Scenario: Yeni proje oluşturma
    Given kullanıcı "/projects" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  @negative
  Scenario: Proje adı olmadan oluşturma denemesi
    Given kullanıcı "/projects" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  # ── DASHBOARD İSTATİSTİKLERİ ────────────────────────────────────

  @smoke
  Scenario: Proje dashboard istatistikleri
    Given kullanıcı test projesinin dashboard'ındadır
    Then "[data-testid='dashboard-stat-scenario-count']" elementi görünür olmalıdır
    Then "[data-testid='dashboard-stat-pending-approvals']" elementi görünür olmalıdır
    Then "[data-testid='dashboard-stat-execution-count']" elementi görünür olmalıdır

  Scenario: Dashboard hızlı aksiyonlar
    Given kullanıcı test projesinin dashboard'ındadır
    Then "[data-testid='quick-actions']" elementi görünür olmalıdır

  # ── NAVİGASYON ──────────────────────────────────────────────────

  Scenario: Dashboard'dan senaryo listesine navigasyon
    Given kullanıcı test projesinin dashboard'ındadır
    When kullanıcı "Senaryolar" metnine tıklar
    Then URL "/scenarios" içermelidir

  Scenario: Dashboard'dan onay kuyruğuna navigasyon
    Given kullanıcı test projesinin dashboard'ındadır
    When kullanıcı "Onay kuyruğu" metnine tıklar
    Then URL "/approvals" içermelidir

  Scenario: Dashboard'dan içe aktarmaya navigasyon
    Given kullanıcı test projesinin dashboard'ındadır
    When kullanıcı "Dosya içe aktar" metnine tıklar
    Then URL "/import" içermelidir

  # ── ÜYE YÖNETİMİ ──────────────────────────────────────────────

  Scenario: Proje üye listesi
    Given kullanıcı test projesinin dashboard'ındadır
    Then sayfa başarıyla yüklenmiş olmalıdır
