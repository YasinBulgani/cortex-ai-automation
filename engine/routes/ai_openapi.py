"""
/api/ai/* endpoint'leri için OpenAPI spec döndüren endpoint.

GET /api/ai/openapi.json — Tüm AI API'lerinin OpenAPI 3.0 tanımı.
"""
from flask import Blueprint, jsonify

ai_openapi_bp = Blueprint("ai_openapi", __name__, url_prefix="/api/ai")

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "TestwrightAI AI Test Engine API",
        "version": "1.0.0",
        "description": "AI destekli test üretimi, self-healing, analiz ve güvenlik tarama endpoint'leri.",
    },
    "servers": [{"url": "http://127.0.0.1:5001", "description": "Local Engine"}],
    "paths": {
        "/api/ai/generate-test": {
            "post": {
                "summary": "Doğal dil gereksinimden test kodu üretir",
                "tags": ["Generation"],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["requirement"], "properties": {
                    "requirement": {"type": "string", "description": "Doğal dil test gereksinimi"},
                    "framework": {"type": "string", "enum": ["pytest-bdd", "playwright-ts", "pytest"], "default": "pytest-bdd"},
                    "model": {"type": "string", "default": "gpt-4o"},
                    "page_objects": {"type": "array", "items": {"type": "string"}},
                }}}}},
                "responses": {"200": {"description": "Üretilen test kodu"}, "400": {"description": "Eksik parametre"}, "500": {"description": "Üretim hatası"}, "503": {"description": "LLM kullanılamaz"}},
            }
        },
        "/api/ai/generate-bdd": {
            "post": {
                "summary": "Doğal dil gereksinimden Gherkin BDD senaryosu üretir",
                "tags": ["Generation"],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["requirement"], "properties": {
                    "requirement": {"type": "string"},
                    "model": {"type": "string", "default": "gpt-4o"},
                }}}}},
                "responses": {"200": {"description": "Gherkin feature + step definitions"}, "400": {"description": "Eksik parametre"}, "503": {"description": "LLM kullanılamaz"}},
            }
        },
        "/api/ai/self-heal": {
            "post": {
                "summary": "Kırık locator için yeni locator önerisi üretir",
                "tags": ["Healing"],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["failed_locator"], "properties": {
                    "failed_locator": {"type": "string"},
                    "accessibility_tree": {"type": "string"},
                    "error_message": {"type": "string"},
                    "page_url": {"type": "string"},
                }}}}},
                "responses": {"200": {"description": "Healing sonucu (healed, new_locator, strategy)"}, "400": {"description": "Eksik parametre"}, "503": {"description": "LLM kullanılamaz"}},
            }
        },
        "/api/ai/find-element": {
            "post": {
                "summary": "Accessibility tree'den element locator'ı üretir",
                "tags": ["Healing"],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["element_intent"], "properties": {
                    "element_intent": {"type": "string"},
                    "accessibility_tree": {"type": "string"},
                }}}}},
                "responses": {"200": {"description": "Locator string"}},
            }
        },
        "/api/ai/healing-log": {
            "get": {
                "summary": "Self-healing geçmişini döndürür",
                "tags": ["Healing"],
                "responses": {"200": {"description": "Healing log entries"}},
            }
        },
        "/api/ai/analyze-anomaly": {
            "post": {
                "summary": "Test çalışma sonuçlarında anomaly tespit eder",
                "tags": ["Analysis"],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {
                    "total": {"type": "integer"},
                    "passed": {"type": "integer"},
                    "failed": {"type": "integer"},
                    "total_duration": {"type": "number"},
                    "avg_duration": {"type": "number"},
                }}}}},
                "responses": {"200": {"description": "Anomaly listesi"}},
            }
        },
        "/api/ai/flaky-report": {
            "get": {
                "summary": "Flaky test analiz raporunu döndürür",
                "tags": ["Analysis"],
                "responses": {"200": {"description": "Flaky test listesi ve istatistikler"}},
            }
        },
        "/api/ai/coverage-gaps": {
            "post": {
                "summary": "Coverage raporundan gap'leri analiz eder",
                "tags": ["Analysis"],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {
                    "coverage_path": {"type": "string", "default": "reports/coverage.json"},
                    "generate_suggestions": {"type": "boolean", "default": False},
                }}}}},
                "responses": {"200": {"description": "Coverage gap listesi"}},
            }
        },
        "/api/ai/prioritize": {
            "post": {
                "summary": "Git diff'e göre testleri önceliklendirir",
                "tags": ["Analysis"],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {
                    "git_diff": {"type": "string"},
                    "time_budget_seconds": {"type": "integer", "default": 300},
                    "min_score_threshold": {"type": "number", "default": 0.1},
                }}}}},
                "responses": {"200": {"description": "Önceliklendirilmiş test listesi"}},
            }
        },
        "/api/ai/stats": {
            "get": {
                "summary": "LLM kullanım istatistiklerini döndürür",
                "tags": ["Monitoring"],
                "responses": {"200": {"description": "Toplam çağrı, token, maliyet"}},
            }
        },
        "/api/ai/analyze-assertions": {
            "post": {
                "summary": "Test dosyasındaki eksik assertion'ları analiz eder",
                "tags": ["Analysis"],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["file_path"], "properties": {
                    "file_path": {"type": "string"},
                }}}}},
                "responses": {"200": {"description": "Assertion önerileri"}},
            }
        },
        "/api/ai/security-scan": {
            "post": {
                "summary": "Güvenlik taraması başlatır",
                "tags": ["Security"],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {
                    "target_url": {"type": "string", "default": "http://127.0.0.1:8000"},
                    "scan_type": {"type": "string", "enum": ["quick", "api"], "default": "quick"},
                    "openapi_spec_url": {"type": "string"},
                }}}}},
                "responses": {"200": {"description": "Güvenlik bulguları"}},
            }
        },
        "/api/ai/openapi.json": {
            "get": {
                "summary": "Bu OpenAPI spec'i döndürür",
                "tags": ["Monitoring"],
                "responses": {"200": {"description": "OpenAPI 3.0 JSON"}},
            }
        },
    },
}


@ai_openapi_bp.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """OpenAPI 3.0 spec'i döndürür."""
    return jsonify(OPENAPI_SPEC)
