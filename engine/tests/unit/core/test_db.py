
import pytest
import sqlite3
import os
from pathlib import Path
from core import db

@pytest.fixture
def mock_db(monkeypatch, tmp_path):
    """Her test icin gecici bir veritabani olusturur."""
    test_db_path = tmp_path / "test_database.sqlite"
    # settings.DB_PATH yerine _db_path'i doğrudan patch'le — böylece
    # test_engine_secrets.py'nin module-cache temizliği bağımlılığı kalmaz.
    monkeypatch.setattr(db, "_db_path", lambda: test_db_path)
    db.init_db()
    return test_db_path

def test_init_db(mock_db):
    """Veritabanı tablolarının doğru oluşturulduğunu test eder."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "test_runs" in tables
        assert "mock_users" in tables
        assert "mock_products" in tables
        assert "platform_users" in tables
        assert "regression_sets" in tables
        assert "manual_tests" in tables
        assert "object_repository" in tables

def test_record_test_run(mock_db):
    """Test koşusu kaydetme fonksiyonunu test eder."""
    db.record_test_run("RUN-123", "@smoke", 5, 2, 1500)
    
    history = db.get_run_history(limit=1)
    assert len(history) == 1
    assert history[0]["run_id"] == "RUN-123"
    assert history[0]["passed"] == 5
    assert history[0]["failed"] == 2

def test_regression_sets(mock_db):
    """Regresyon seti oluşturma ve feature ekleme işlemlerini test eder."""
    # Set oluştur
    success = db.create_regression_set("Smoke Test Set")
    assert success is True
    
    # Feature ekle
    db.add_feature_to_set(1, "login.feature")
    
    sets = db.get_regression_sets()
    assert len(sets) == 1
    assert sets[0]["name"] == "Smoke Test Set"
    assert "login.feature" in sets[0]["features"]
    
    # Çift kayıt engeli
    success = db.create_regression_set("Smoke Test Set")
    assert success is False

def test_manual_tests(mock_db):
    """Manuel test oluşturma ve adım ekleme işlemlerini test eder."""
    test_id = db.create_manual_test("Yeni Kullanıcı Kaydı")
    assert test_id == 1
    
    db.add_manual_step(test_id, "Kaydol butonuna bas", "Kayıt formu açılmalı")
    
    tests = db.get_manual_tests()
    assert len(tests) == 1
    assert tests[0]["title"] == "Yeni Kullanıcı Kaydı"
    assert len(tests[0]["steps"]) == 1
    assert tests[0]["steps"][0]["action"] == "Kaydol butonuna bas"

def test_object_repository(mock_db):
    """Seçici deposu (Object Repository) işlemlerini test eder."""
    loc_id = db.save_locator("LoginBtn", "//button[@id='login']", "https://test.com")
    assert loc_id is not None
    
    # Çözümleme (Resolve)
    selector = db.resolve_locator("LoginBtn")
    assert selector == "//button[@id='login']"
    
    # Olmayan kayıt
    raw = db.resolve_locator(".not-exists")
    assert raw == ".not-exists"
    
    # Güncelleme (Upsert)
    db.save_locator("LoginBtn", "//div[@class='btn-login']")
    selector = db.resolve_locator("LoginBtn")
    assert selector == "//div[@class='btn-login']"
