
import pytest
from unittest.mock import MagicMock, patch
from core.ai_engine import AIEngine

@pytest.fixture
def engine():
    return AIEngine()

def test_parse_actions(engine):
    """JSON aksiyon listesi ayrıştırma mantığını test eder."""
    raw_json = '[{"action": "click", "selector": "button"}]'
    actions = engine._parse_actions(raw_json)
    assert len(actions) == 1
    assert actions[0]["action"] == "click"
    
    # Markdown temizliği
    raw_md = "```json\n[{\"action\": \"wait\", \"ms\": 500}]\n```"
    actions = engine._parse_actions(raw_md)
    assert actions[0]["action"] == "wait"
    
    # Hatalı format
    assert engine._parse_actions("invalid") == []

@patch("core.ai_engine.AIEngine._call_llm")
def test_generate_gherkin(mock_llm, engine):
    """Gherkin üretimi fonksiyonunun LLM çağrısını test eder."""
    mock_llm.return_value = "Feature: Test\n  Scenario: Login"
    
    res = engine.generate_gherkin("Kullanıcı giriş yapabilmeli")
    
    assert "Feature:" in res
    mock_llm.assert_called_once()

@patch("core.ai_engine.AIEngine._call_llm")
def test_analyze_api_response(mock_llm, engine):
    """API analiz fonksiyonunu test eder."""
    mock_llm.return_value = "### Analiz Raporu\n1. Başarılı"
    
    req = {"url": "test.com", "method": "GET"}
    res = {"status": 200, "body": "{}"}
    
    analysis = engine.analyze_api_response(req, res)
    assert "Analiz" in analysis
    mock_llm.assert_called_once()

def test_execute_model_name(engine, monkeypatch):
    """Model ismi çözümleme mantığını test eder."""
    from config.settings import settings
    
    monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-4")
    assert engine.execute_model_name == "gpt-4"
    
    monkeypatch.setattr(settings, "OPENAI_MODEL", "g4f-gpt-3.5-turbo")
    assert engine.execute_model_name == "gpt-3.5-turbo"
