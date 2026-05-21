
import pytest
import json
from app import app
from core import db

@pytest.fixture
def client(tmp_path, monkeypatch):
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'

    # core.db artık settings.DB_PATH kullanıyor — modül sabiti kaldırıldı.
    # Eski DB_PATH monkeypatch'i yerine _db_path fonksiyonunu geçici yola
    # döndürüyoruz.
    test_db = tmp_path / "test_integration.sqlite"
    from core import db as core_db
    monkeypatch.setattr(core_db, "_db_path", lambda: test_db)

    with app.test_client() as client:
        with app.app_context():
            core_db.init_db()
        yield client

def test_health_check(client):
    """Sağlık kontrolü endpointini test eder."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'running'

def test_unauthorized_access(client):
    """Giriş yapmadan korumalı bir endpoint'e erişimi test eder."""
    response = client.get('/api/features')
    assert response.status_code == 401
    assert "Unauthorized" in response.json['error']

def test_auth_and_protected_access(client):
    """Kayıt, giriş ve sonrasında korumalı endpoint'e erişimi test eder."""
    # 1. Kayıt
    reg_data = {"email": "test@api.com", "password": "password123"}
    reg_res = client.post('/api/auth/register', 
                          data=json.dumps(reg_data), 
                          content_type='application/json')
    assert reg_res.status_code == 200

    # 2. Giriş
    login_res = client.post('/api/auth/login', 
                            data=json.dumps(reg_data), 
                            content_type='application/json')
    assert login_res.status_code == 200
    
    # 3. Korumalı endpoint (Features)
    feat_res = client.get('/api/features')
    assert feat_res.status_code == 200
    assert isinstance(feat_res.json, list)

def test_manual_test_crud_api(client):
    """Manuel test API akışını test eder."""
    client.post('/api/auth/register', data=json.dumps({"email": "m@t.com", "password": "p"}), content_type='application/json')
    client.post('/api/auth/login', data=json.dumps({"email": "m@t.com", "password": "p"}), content_type='application/json')
    
    # 1. Create
    res = client.post('/api/manual-tests', data=json.dumps({"title": "Integration Test"}), content_type='application/json')
    assert res.status_code == 200
    
    # 2. Get
    res = client.get('/api/manual-tests')
    assert res.status_code == 200
    tests = res.json
    assert any(t['title'] == "Integration Test" for t in tests)
    test_id = tests[0]['id']
    
    # 3. Add Step
    res = client.post(f'/api/manual-tests/{test_id}/steps', 
                      data=json.dumps({"action": "Open App", "expected": "Success"}), 
                      content_type='application/json')
    assert res.status_code == 200

def test_regression_set_api(client):
    """Regresyon seti API akışını test eder."""
    client.post('/api/auth/register', data=json.dumps({"email": "r@t.com", "password": "p"}), content_type='application/json')
    client.post('/api/auth/login', data=json.dumps({"email": "r@t.com", "password": "p"}), content_type='application/json')
    
    # 1. Create
    res = client.post('/api/regression-sets', data=json.dumps({"name": "Smoke"}), content_type='application/json')
    assert res.status_code == 200
    
    # 2. Get
    res = client.get('/api/regression-sets')
    assert res.status_code == 200
    assert any(s['name'] == "Smoke" for s in res.json)

def test_locators_api(client):
    """Seçici deposu API akışını test eder."""
    client.post('/api/auth/register', data=json.dumps({"email": "l@t.com", "password": "p"}), content_type='application/json')
    client.post('/api/auth/login', data=json.dumps({"email": "l@t.com", "password": "p"}), content_type='application/json')
    
    # 1. Save
    res = client.post('/api/locators', data=json.dumps({"name": "Btn", "locator_value": "#btn"}), content_type='application/json')
    assert res.status_code == 200
    
def test_runner_api(client):
    """Test koşumu API'sini (SSE öncesi başlatma) test eder."""
    client.post('/api/auth/register', data=json.dumps({"email": "run@t.com", "password": "p"}), content_type='application/json')
    client.post('/api/auth/login', data=json.dumps({"email": "run@t.com", "password": "p"}), content_type='application/json')
    
    # 1. Run Tests (Trigger)
    res = client.post('/api/run', data=json.dumps({"markers": "not ai"}), content_type='application/json')
    assert res.status_code == 200
    assert "run_id" in res.json
    
    run_id = res.json["run_id"]
    
def test_ai_feature_generation_api(client):
    """AI feature üretimi API'sini test eder."""
    client.post('/api/auth/register', data=json.dumps({"email": "ai@t.com", "password": "p"}), content_type='application/json')
    client.post('/api/auth/login', data=json.dumps({"email": "ai@t.com", "password": "p"}), content_type='application/json')
    
    # Mock AIEngine logic inside the test by patching if needed, 
    # but for integration test, we check the endpoint logic.
    from unittest.mock import patch
    with patch("core.ai_engine.AIEngine.generate_gherkin") as mock_gen:
        mock_gen.return_value = "Feature: AI Generated"
        
        # Test with 'requirement' (singular - as sent by app.js)
        res = client.post('/api/generate-feature', 
                          data=json.dumps({"requirement": "Login test", "tech": "Pytest"}), 
                          content_type='application/json')
        assert res.status_code == 200
        assert "AI Generated" in res.json["content"]
        
        # Test with 'requirements' (plural - original backend name)
        res = client.post('/api/generate-feature', 
                          data=json.dumps({"requirements": "Search test"}), 
                          content_type='application/json')
        assert res.status_code == 200
