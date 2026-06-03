"""
AI OpenAPI spec endpoint — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/ai_openapi.py — Blueprint, GET /api/ai/openapi.json

SONRA (FastAPI):
  /backend/app/engine/routes/ai_openapi.py — APIRouter, GET /api/ai/openapi.json
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/ai", tags=["engine", "ai", "openapi"])

OPENAPI_SPEC: dict = {
    "openapi": "3.0.3",
    "info": {
        "title": "Neurex AI Test Engine API",
        "version": "1.0.0",
        "description": "AI destekli test üretimi, self-healing, analiz ve güvenlik tarama endpoint'leri.",
    },
    "servers": [{"url": "http://127.0.0.1:8000", "description": "FastAPI Engine (consolidated)"}],
    "paths": {
        "/api/ai/generate-feature": {
            "post": {
                "summary": "BDD Gherkin üretimi — legacy endpoint",
                "tags": ["Generation"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "requirements": {"type": "string"},
                                    "requirement": {"type": "string"},
                                    "url": {"type": "string"},
                                    "tech": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Gherkin feature içeriği"},
                    "400": {"description": "Gereksinim metni eksik"},
                    "500": {"description": "Üretim hatası"},
                    "503": {"description": "AI Engine kullanılamaz"},
                },
            }
        },
        "/api/ai/generate-test": {
            "post": {
                "summary": "Doğal dil gereksinimden test kodu üretir",
                "tags": ["Generation"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["requirement"],
                                "properties": {
                                    "requirement": {"type": "string", "description": "Doğal dil test gereksinimi"},
                                    "framework": {
                                        "type": "string",
                                        "enum": ["pytest-bdd", "playwright-ts", "pytest"],
                                        "default": "pytest-bdd",
                                    },
                                    "model": {"type": "string", "default": "gpt-4o"},
                                    "page_objects": {"type": "array", "items": {"type": "string"}},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Üretilen test kodu"},
                    "400": {"description": "Eksik parametre"},
                    "500": {"description": "Üretim hatası"},
                    "503": {"description": "LLM kullanılamaz"},
                },
            }
        },
        "/api/ai/generate-bdd": {
            "post": {
                "summary": "Doğal dil gereksinimden Gherkin BDD senaryosu üretir",
                "tags": ["Generation"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["requirement"],
                                "properties": {
                                    "requirement": {"type": "string"},
                                    "model": {"type": "string", "default": "gpt-4o"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Gherkin feature + step definitions"},
                    "400": {"description": "Eksik parametre"},
                    "503": {"description": "LLM kullanılamaz"},
                },
            }
        },
        "/api/ai/self-heal": {
            "post": {
                "summary": "Kırık locator için yeni locator önerisi üretir",
                "tags": ["Healing"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["failed_locator"],
                                "properties": {
                                    "failed_locator": {"type": "string"},
                                    "accessibility_tree": {"type": "string"},
                                    "error_message": {"type": "string"},
                                    "page_url": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Healing sonucu (healed, new_locator, strategy)"},
                    "400": {"description": "Eksik parametre"},
                    "503": {"description": "LLM kullanılamaz"},
                },
            }
        },
        "/api/ai/find-element": {
            "post": {
                "summary": "Accessibility tree'den element locator'ı üretir",
                "tags": ["Healing"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["element_intent"],
                                "properties": {
                                    "element_intent": {"type": "string"},
                                    "accessibility_tree": {"type": "string"},
                                },
                            }
                        }
                    },
                },
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
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "total": {"type": "integer"},
                                    "passed": {"type": "integer"},
                                    "failed": {"type": "integer"},
                                    "total_duration": {"type": "number"},
                                    "avg_duration": {"type": "number"},
                                },
                            }
                        }
                    }
                },
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
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "coverage_path": {"type": "string", "default": "reports/coverage.json"},
                                    "generate_suggestions": {"type": "boolean", "default": False},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "Coverage gap listesi"}},
            }
        },
        "/api/ai/prioritize": {
            "post": {
                "summary": "Git diff'e göre testleri önceliklendirir",
                "tags": ["Analysis"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "git_diff": {"type": "string"},
                                    "time_budget_seconds": {"type": "integer", "default": 300},
                                    "min_score_threshold": {"type": "number", "default": 0.1},
                                },
                            }
                        }
                    }
                },
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
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["file_path"],
                                "properties": {
                                    "file_path": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {"200": {"description": "Assertion önerileri"}},
            }
        },
        "/api/ai/security-scan": {
            "post": {
                "summary": "Güvenlik taraması başlatır",
                "tags": ["Security"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "target_url": {"type": "string", "default": "http://127.0.0.1:8000"},
                                    "scan_type": {"type": "string", "enum": ["quick", "api"], "default": "quick"},
                                    "openapi_spec_url": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "Güvenlik bulguları"}},
            }
        },
        "/api/ai/analyze-failure": {
            "post": {
                "summary": "Başarısız test çıktısını analiz eder, kategori ve düzeltme önerisi döner",
                "tags": ["Analysis"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "test_title": {"type": "string"},
                                    "feature_path": {"type": "string"},
                                    "error_hint": {"type": "string"},
                                    "status": {"type": "string", "default": "failed"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "Hata kategori ve düzeltme önerisi"}},
            }
        },
        "/api/ai/nl-test": {
            "post": {
                "summary": "Doğal dil isteğinden test senaryosu üretir ve pipeline'a gönderir",
                "tags": ["Generation"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["prompt"],
                                "properties": {
                                    "prompt": {"type": "string"},
                                    "project_id": {"type": "string"},
                                    "auto_run": {"type": "boolean", "default": False},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Üretilen test case"},
                    "400": {"description": "prompt zorunludur"},
                    "500": {"description": "LLM hatası"},
                },
            }
        },
        "/api/ai/impact-analysis": {
            "post": {
                "summary": "Commit diff'i analiz ederek etkilenen test dosyalarını döner",
                "tags": ["Analysis"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "diff": {"type": "string"},
                                    "changed_files": {"type": "array", "items": {"type": "string"}},
                                    "project_id": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "Etkilenen test dosyaları ve AI analizi"}},
            }
        },
        "/api/ai/extract-testcases": {
            "post": {
                "summary": "Doküman yükle → AI test case'leri çıkar → önizleme için döndür",
                "tags": ["Generation"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "required": ["file"],
                                "properties": {
                                    "file": {"type": "string", "format": "binary"},
                                    "module_id": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Çıkarılan test case listesi"},
                    "400": {"description": "Dosya yüklenemedi veya içerik boş"},
                },
            }
        },
        "/api/ai/save-test-cases": {
            "post": {
                "summary": "Onaylanan AI test case'lerini engine DB'ye kaydeder",
                "tags": ["Generation"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["cases"],
                                "properties": {
                                    "cases": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "title": {"type": "string"},
                                                "steps": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "action": {"type": "string"},
                                                            "expected": {"type": "string"},
                                                        },
                                                    },
                                                },
                                            },
                                        },
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Kaydedilen test ID'leri"},
                    "400": {"description": "cases listesi boş"},
                },
            }
        },
        "/api/ai/inspect": {
            "post": {
                "summary": "Playwright codegen çalıştırır ve çıktıyı Gherkin'e dönüştürür",
                "tags": ["Generation"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"url": {"type": "string"}},
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Gherkin çıktısı"},
                    "400": {"description": "Kayıt bulunamadı"},
                },
            }
        },
        "/api/ai/analyze-api-request": {
            "post": {
                "summary": "API istek/yanıt çiftini analiz eder",
                "tags": ["Analysis"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["request", "response"],
                                "properties": {
                                    "request": {"type": "object"},
                                    "response": {"type": "object"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Analiz sonucu"},
                    "400": {"description": "Veri eksik"},
                },
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


@router.get("/openapi.json", include_in_schema=False)
def openapi_spec() -> JSONResponse:
    """OpenAPI 3.0 spec'i döndürür.

    Flask engine'den FastAPI'ye port edilmiştir.
    """
    return JSONResponse(content=OPENAPI_SPEC)
