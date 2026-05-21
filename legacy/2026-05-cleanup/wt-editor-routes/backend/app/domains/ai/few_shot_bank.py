"""
Few-Shot Example Bank — Bankacilik domain'i icin kalibreli ornek seti.

Her ajan modu icin yuksek kaliteli giris/cikis ornekleri icerir.
LLM'e "bu kalitede uret" mesajini verir — cikti tutarliligi ve domainin
dogru yansitilmasi icin kritik oneme sahiptir.

Kullanim:
    from app.domains.ai.few_shot_bank import get_few_shot_examples

    examples = get_few_shot_examples("test_generation", ["transfer", "iban"])
    system_prompt += examples
"""

import json
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# FEW-SHOT EXAMPLE BANK
# ============================================================================

FEW_SHOT_EXAMPLES: Dict[str, Dict[str, dict]] = {

    # ── TEST GENERATION ─────────────────────────────────────────────────────
    "test_generation": {

        "banking_transfer": {
            "input": "POST /api/v1/transfers endpoint with fields: from_iban, to_iban, amount, currency, description",
            "output": {
                "test_cases": [
                    {
                        "id": "API-TRF-001",
                        "title": "Gecerli para transferi - tum alanlar dolu",
                        "description": "Gecerli IBAN, tutar ve aciklama ile basarili havale islemi",
                        "test_type": "positive",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
                        "owasp_category": None,
                        "regulation": None,
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/transfers",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json",
                                "X-Idempotency-Key": "{{idempotency_key}}"
                            },
                            "body": {
                                "from_iban": "TR330006100519786457841326",
                                "to_iban": "TR120006200000000123456789",
                                "amount": 250.50,
                                "currency": "TRY",
                                "description": "Kira odemesi - Nisan 2026"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 201},
                            {"type": "json_path", "path": "$.transfer_id", "operator": "exists"},
                            {"type": "json_path", "path": "$.status", "operator": "equals", "expected": "completed"},
                            {"type": "response_time", "max_ms": 3000}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "Temel basari senaryosu — tum zorunlu alanlar gecerli degerlerle doldurulmus, happy path dogrulamasi"
                    },
                    {
                        "id": "API-TRF-002",
                        "title": "Zorunlu alan eksik - tutar alani yok",
                        "description": "Amount alani gonderilmeden transfer istegi — 400 donmeli",
                        "test_type": "negative",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
                        "owasp_category": None,
                        "regulation": None,
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/transfers",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json"
                            },
                            "body": {
                                "from_iban": "TR330006100519786457841326",
                                "to_iban": "TR120006200000000123456789",
                                "description": "Eksik tutar testi"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 400},
                            {"type": "json_path", "path": "$.error", "operator": "exists"},
                            {"type": "json_path", "path": "$.error.field", "operator": "equals", "expected": "amount"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "Zorunlu alan dogrulamasi — API'nin anlamli hata mesaji dondurmesi gerekir"
                    },
                    {
                        "id": "API-TRF-003",
                        "title": "Sinir degeri - minimum tutar (0.01 TRY)",
                        "description": "Minimum gecerli para birimi olan 0.01 TRY ile transfer",
                        "test_type": "boundary",
                        "priority": "P2",
                        "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
                        "owasp_category": None,
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/transfers",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json",
                                "X-Idempotency-Key": "{{idempotency_key}}"
                            },
                            "body": {
                                "from_iban": "TR330006100519786457841326",
                                "to_iban": "TR120006200000000123456789",
                                "amount": 0.01,
                                "currency": "TRY",
                                "description": "Minimum tutar testi"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 201},
                            {"type": "json_path", "path": "$.amount", "operator": "equals", "expected": 0.01}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "Sinir degeri testi — minimum islem tutari kabul edilmeli, float hassasiyet kontrolu"
                    },
                    {
                        "id": "API-TRF-004",
                        "title": "Sinir degeri - maksimum tutar (999999.99 TRY)",
                        "description": "Gunluk bireysel limit olan 999999.99 TRY ile transfer denemesi",
                        "test_type": "boundary",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
                        "owasp_category": None,
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/transfers",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json",
                                "X-Idempotency-Key": "{{idempotency_key}}"
                            },
                            "body": {
                                "from_iban": "TR330006100519786457841326",
                                "to_iban": "TR120006200000000123456789",
                                "amount": 999999.99,
                                "currency": "TRY",
                                "description": "Maksimum tutar testi"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "operator": "one_of", "expected": [201, 403]},
                            {"type": "response_time", "max_ms": 3000}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "BDDK gunluk limit kontrolu — yuksek tutarli islem ya basarili ya da limit asildi hatasi donmeli"
                    },
                    {
                        "id": "API-TRF-005",
                        "title": "Guvenlik - BOLA: Baska kullanicinin hesabindan transfer",
                        "description": "Kullanici A'nin token'i ile Kullanici B'nin IBAN'indan transfer denemesi",
                        "test_type": "security",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
                        "owasp_category": "API1",
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/transfers",
                            "headers": {
                                "Authorization": "Bearer {{user_a_token}}",
                                "Content-Type": "application/json"
                            },
                            "body": {
                                "from_iban": "{{user_b_iban}}",
                                "to_iban": "TR120006200000000123456789",
                                "amount": 1000.00,
                                "currency": "TRY",
                                "description": "BOLA test — yetkisiz transfer"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "operator": "one_of", "expected": [403, 404]},
                            {"type": "json_path", "path": "$.transfer_id", "operator": "not_exists"},
                            {"type": "json_path", "path": "$.error", "operator": "exists"}
                        ],
                        "setup_chain": [
                            {"step": "Login User A", "endpoint": "POST /api/v1/auth/login", "extract": {"user_a_token": "$.access_token"}},
                            {"step": "Get User B IBAN", "endpoint": "GET /api/v1/accounts", "note": "Onceden bilinen veya test setup'tan alinan deger"}
                        ],
                        "ai_reasoning": "OWASP API1 BOLA — bankacilikta en kritik guvenlik acigi, baska kullanicinin hesabindan para transferi engellenmeli"
                    },
                    {
                        "id": "API-TRF-006",
                        "title": "MASAK - Suphe esigi ustu tutar bildirimi (75.000 TRY)",
                        "description": "MASAK bildirim esigini asan tutar icin islem kaydinin duzgun olusturulmasi",
                        "test_type": "compliance",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
                        "owasp_category": None,
                        "regulation": "MASAK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/transfers",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json",
                                "X-Idempotency-Key": "{{idempotency_key}}"
                            },
                            "body": {
                                "from_iban": "TR330006100519786457841326",
                                "to_iban": "TR120006200000000123456789",
                                "amount": 80000.00,
                                "currency": "TRY",
                                "description": "MASAK esik testi"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 201},
                            {"type": "json_path", "path": "$.masak_report_required", "operator": "equals", "expected": True},
                            {"type": "json_path", "path": "$.transfer_id", "operator": "exists"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "MASAK supheli islem bildirimi — 75.000 TRY ustu islemler otomatik bildirim gerektirir, denetim izi olusturulmali"
                    },
                    {
                        "id": "API-TRF-007",
                        "title": "BDDK - Gunluk kumulatif limit kontrolu",
                        "description": "Ayni gunde birden fazla transferle gunluk limiti asma denemesi",
                        "test_type": "compliance",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
                        "owasp_category": None,
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/transfers",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json",
                                "X-Idempotency-Key": "{{idempotency_key}}"
                            },
                            "body": {
                                "from_iban": "TR330006100519786457841326",
                                "to_iban": "TR120006200000000123456789",
                                "amount": 500000.00,
                                "currency": "TRY",
                                "description": "Kumulatif limit testi — 2. islem"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 403},
                            {"type": "json_path", "path": "$.error.code", "operator": "equals", "expected": "DAILY_LIMIT_EXCEEDED"},
                            {"type": "json_path", "path": "$.error.daily_remaining", "operator": "exists"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}},
                            {"step": "Ilk transfer (limit doldurucu)", "endpoint": "POST /api/v1/transfers", "body": {"amount": 600000.00}}
                        ],
                        "ai_reasoning": "BDDK gunluk kumulatif islem limiti — tek islem degil, gun boyunca yapilan islemlerin toplami kontrol edilmeli"
                    }
                ]
            }
        },

        "banking_auth": {
            "input": "POST /api/v1/auth/login with email and password",
            "output": {
                "test_cases": [
                    {
                        "id": "API-AUTH-001",
                        "title": "Gecerli kimlik bilgileri ile basarili giris",
                        "description": "Dogru email ve sifre ile login — access_token ve refresh_token donmeli",
                        "test_type": "positive",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "owasp_category": None,
                        "regulation": None,
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/auth/login",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "email": "test.user@bgtsbank.com.tr",
                                "password": "Test1234!Secure"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 200},
                            {"type": "json_path", "path": "$.access_token", "operator": "exists"},
                            {"type": "json_path", "path": "$.refresh_token", "operator": "exists"},
                            {"type": "json_path", "path": "$.token_type", "operator": "equals", "expected": "Bearer"},
                            {"type": "json_path", "path": "$.expires_in", "operator": "greater_than", "expected": 0},
                            {"type": "response_time", "max_ms": 2000}
                        ],
                        "setup_chain": [],
                        "ai_reasoning": "Temel auth happy path — token donusunun kontrol edilmesi tum diger testlerin on kosulu"
                    },
                    {
                        "id": "API-AUTH-002",
                        "title": "Yanlis sifre ile basarisiz giris",
                        "description": "Gecerli email, yanlis sifre — 401 donmeli, sifre bilgisi acilanmamali",
                        "test_type": "negative",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "owasp_category": "API2",
                        "regulation": None,
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/auth/login",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "email": "test.user@bgtsbank.com.tr",
                                "password": "YanlisSifre123!"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 401},
                            {"type": "json_path", "path": "$.access_token", "operator": "not_exists"},
                            {"type": "json_path", "path": "$.error", "operator": "contains", "expected": "kimlik"},
                            {"type": "header", "name": "X-RateLimit-Remaining", "operator": "exists"}
                        ],
                        "setup_chain": [],
                        "ai_reasoning": "Yanlis sifre — hata mesaji 'email bulunamadi' veya 'sifre yanlis' gibi ayristirici bilgi vermemeli (user enumeration onleme)"
                    },
                    {
                        "id": "API-AUTH-003",
                        "title": "Zorunlu alan eksik - email alani yok",
                        "description": "Email alani olmadan login istegi — 400 donmeli",
                        "test_type": "negative",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "owasp_category": None,
                        "regulation": None,
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/auth/login",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "password": "Test1234!Secure"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 400},
                            {"type": "json_path", "path": "$.error.field", "operator": "equals", "expected": "email"}
                        ],
                        "setup_chain": [],
                        "ai_reasoning": "Input dogrulama — zorunlu alan eksik oldugunda anlamli hata donmeli"
                    },
                    {
                        "id": "API-AUTH-004",
                        "title": "Guvenlik - Brute force korumasi (6. deneme kilitleme)",
                        "description": "5 basarisiz giris denemesinden sonra 6. deneme hesap kilidine neden olmali",
                        "test_type": "security",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "owasp_category": "API2",
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/auth/login",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "email": "brute.test@bgtsbank.com.tr",
                                "password": "YanlisDenemeSifre6"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 429},
                            {"type": "json_path", "path": "$.error.code", "operator": "equals", "expected": "ACCOUNT_LOCKED"},
                            {"type": "json_path", "path": "$.error.retry_after_seconds", "operator": "greater_than", "expected": 0},
                            {"type": "header", "name": "Retry-After", "operator": "exists"}
                        ],
                        "setup_chain": [
                            {"step": "5x basarisiz giris", "endpoint": "POST /api/v1/auth/login", "repeat": 5, "body": {"password": "YanlisSifre"}}
                        ],
                        "ai_reasoning": "OWASP API2 + BDDK gereksinimleri — brute force korumasiz login bankacilikta kabul edilemez, 5 denemede kilit + gecici blok"
                    },
                    {
                        "id": "API-AUTH-005",
                        "title": "Guvenlik - SQL injection email alaninda",
                        "description": "Email alanina SQL injection payload gonderilmesi — 400 donmeli, veritabani hatasi acilanmamali",
                        "test_type": "security",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "owasp_category": "API8",
                        "regulation": None,
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/auth/login",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "email": "admin'--; DROP TABLE users;--",
                                "password": "irrelevant"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "operator": "one_of", "expected": [400, 401]},
                            {"type": "json_path", "path": "$.error", "operator": "not_contains", "expected": "SQL"},
                            {"type": "json_path", "path": "$.error", "operator": "not_contains", "expected": "syntax"},
                            {"type": "json_path", "path": "$.error", "operator": "not_contains", "expected": "postgresql"}
                        ],
                        "setup_chain": [],
                        "ai_reasoning": "SQL injection — API hata mesajinda veritabani detayi sizdirilmamali, parametrize sorgu kullanildigi dogrulanmali"
                    },
                    {
                        "id": "API-AUTH-006",
                        "title": "Uyumluluk - KVKK basarisiz giris loglama",
                        "description": "Basarisiz giris denemesi audit log'a kaydedilmeli — IP, tarih, email",
                        "test_type": "compliance",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "owasp_category": None,
                        "regulation": "KVKK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/auth/login",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "email": "audit.test@bgtsbank.com.tr",
                                "password": "YanlisSifre123!"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 401},
                            {"type": "audit_log_check", "event_type": "LOGIN_FAILED", "fields": ["ip_address", "timestamp", "email", "user_agent"]}
                        ],
                        "setup_chain": [],
                        "ai_reasoning": "KVKK 12. madde — kisisel veri isleme faaliyetleri kaydedilmeli, basarisiz girisler de denetim izine dahil"
                    }
                ]
            }
        },

        "banking_account": {
            "input": "GET /api/v1/accounts/{id} and GET /api/v1/accounts/{id}/balance",
            "output": {
                "test_cases": [
                    {
                        "id": "API-ACC-001",
                        "title": "Kendi hesap detaylarini goruntuleme",
                        "description": "Oturum acmis kullanicinin kendi hesap bilgilerini getirmesi",
                        "test_type": "positive",
                        "priority": "P1",
                        "endpoint": {"method": "GET", "path": "/api/v1/accounts/{id}"},
                        "owasp_category": None,
                        "regulation": None,
                        "request": {
                            "method": "GET",
                            "path": "/api/v1/accounts/{{own_account_id}}",
                            "headers": {"Authorization": "Bearer {{auth_token}}"}
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 200},
                            {"type": "json_path", "path": "$.account_id", "operator": "equals", "expected": "{{own_account_id}}"},
                            {"type": "json_path", "path": "$.iban", "operator": "matches", "expected": "^TR\\d{24}$"},
                            {"type": "json_path", "path": "$.owner_name", "operator": "exists"},
                            {"type": "response_time", "max_ms": 1000}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}},
                            {"step": "Get Account ID", "endpoint": "GET /api/v1/accounts", "extract": {"own_account_id": "$.accounts[0].id"}}
                        ],
                        "ai_reasoning": "Temel hesap erisim senaryosu — kendi hesabina erisim her zaman calisir olmali"
                    },
                    {
                        "id": "API-ACC-002",
                        "title": "Guvenlik - BOLA: Baska kullanicinin hesabina erisim",
                        "description": "Kullanici A'nin token'i ile Kullanici B'nin hesap ID'sine erisim denemesi",
                        "test_type": "security",
                        "priority": "P0",
                        "endpoint": {"method": "GET", "path": "/api/v1/accounts/{id}"},
                        "owasp_category": "API1",
                        "regulation": "BDDK",
                        "request": {
                            "method": "GET",
                            "path": "/api/v1/accounts/{{other_user_account_id}}",
                            "headers": {"Authorization": "Bearer {{user_a_token}}"}
                        },
                        "assertions": [
                            {"type": "status_code", "operator": "one_of", "expected": [403, 404]},
                            {"type": "json_path", "path": "$.iban", "operator": "not_exists"},
                            {"type": "json_path", "path": "$.balance", "operator": "not_exists"},
                            {"type": "json_path", "path": "$.owner_name", "operator": "not_exists"}
                        ],
                        "setup_chain": [
                            {"step": "Login User A", "endpoint": "POST /api/v1/auth/login", "extract": {"user_a_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "OWASP API1 BOLA — en yaygin API guvenlik acigi, hesap ID'si degistirerek baskasinin verisine erisim engellenmeli"
                    },
                    {
                        "id": "API-ACC-003",
                        "title": "Uyumluluk - KVKK IBAN maskeleme",
                        "description": "API response'undaki IBAN degeri kismen maskelenmis olmali",
                        "test_type": "compliance",
                        "priority": "P1",
                        "endpoint": {"method": "GET", "path": "/api/v1/accounts/{id}"},
                        "owasp_category": "API3",
                        "regulation": "KVKK",
                        "request": {
                            "method": "GET",
                            "path": "/api/v1/accounts/{{own_account_id}}",
                            "headers": {"Authorization": "Bearer {{auth_token}}"}
                        },
                        "assertions": [
                            {"type": "json_path", "path": "$.iban_masked", "operator": "matches", "expected": "^TR\\*{16}\\d{4}$"},
                            {"type": "json_path", "path": "$.tckn", "operator": "not_exists", "note": "TCKN asla tam olarak donmemeli"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "KVKK veri minimizasyonu — hassas veriler (IBAN, TCKN) API response'larinda maskelenmeli, yalnizca son 4 hane gorunur"
                    },
                    {
                        "id": "API-ACC-004",
                        "title": "Performans - Bakiye sorgulama SLA (< 1sn)",
                        "description": "Hesap bakiye endpointi bankacilik SLA gereksinimini (1 saniye) karsilamali",
                        "test_type": "performance",
                        "priority": "P1",
                        "endpoint": {"method": "GET", "path": "/api/v1/accounts/{id}/balance"},
                        "owasp_category": None,
                        "regulation": "BDDK",
                        "request": {
                            "method": "GET",
                            "path": "/api/v1/accounts/{{own_account_id}}/balance",
                            "headers": {"Authorization": "Bearer {{auth_token}}"}
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 200},
                            {"type": "json_path", "path": "$.balance", "operator": "exists"},
                            {"type": "json_path", "path": "$.currency", "operator": "equals", "expected": "TRY"},
                            {"type": "response_time", "max_ms": 1000}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "BDDK dijital kanal SLA — bakiye sorgulama kritik musteri deneyimi, 1 saniye ustu kabul edilemez"
                    }
                ]
            }
        }
    },

    # ── SECURITY AUDIT ──────────────────────────────────────────────────────
    "security_audit": {

        "owasp_api1_bola": {
            "input": "GET /api/v1/accounts/{account_id}",
            "output": {
                "security_tests": [
                    {
                        "id": "SEC-BOLA-001",
                        "title": "BOLA — Baska kullanicinin hesap detayina erisim",
                        "owasp": "API1",
                        "cwe": "CWE-639",
                        "severity": "critical",
                        "endpoint": {"method": "GET", "path": "/api/v1/accounts/{account_id}"},
                        "attack_scenario": (
                            "Saldirgan (Kullanici A) kendi hesabi icin gecerli bir JWT token alir. "
                            "Ardindan GET /api/v1/accounts/{account_id} istegindeki account_id parametresini "
                            "Kullanici B'nin hesap ID'si ile degistirir. Eger API yalnizca JWT'nin gecerliligini "
                            "kontrol edip, hesap sahipligini dogrulamiyorsa, Kullanici B'nin tum hesap bilgileri "
                            "(bakiye, IBAN, islem gecmisi) saldirganin eline gecer."
                        ),
                        "expected_defense": (
                            "403 Forbidden veya 404 Not Found donmeli. "
                            "API, JWT'deki user_id ile talep edilen account_id'nin sahiplik iliskisini kontrol etmeli. "
                            "Basarisiz erisim denemesi audit log'a kaydedilmeli (IP, user_id, hedef account_id, zaman)."
                        ),
                        "regulation": "BDDK",
                        "request": {
                            "method": "GET",
                            "path": "/api/v1/accounts/{{victim_account_id}}",
                            "headers": {
                                "Authorization": "Bearer {{attacker_token}}"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "operator": "one_of", "expected": [403, 404]},
                            {"type": "json_path", "path": "$.account_number", "operator": "not_exists"},
                            {"type": "json_path", "path": "$.balance", "operator": "not_exists"},
                            {"type": "json_path", "path": "$.iban", "operator": "not_exists"}
                        ]
                    },
                    {
                        "id": "SEC-BOLA-002",
                        "title": "BOLA — IDOR ile hesap ID'si numaralandirma (enumeration)",
                        "owasp": "API1",
                        "cwe": "CWE-639",
                        "severity": "high",
                        "endpoint": {"method": "GET", "path": "/api/v1/accounts/{account_id}"},
                        "attack_scenario": (
                            "Saldirgan, hesap ID'lerinin tahmin edilebilir bir sirada (sequential integer: 1, 2, 3...) "
                            "oldugunu fark eder. GET /api/v1/accounts/1 den baslayarak sirayla tum hesaplari tarar. "
                            "Her istekte farkli bir HTTP status kodu donmesi (200 var, 404 yok) hangi ID'lerin "
                            "gercek hesaplara ait oldugunu acilar."
                        ),
                        "expected_defense": (
                            "Hesap ID'leri UUID v4 formatinda olmali (tahmin edilemez). "
                            "Yetkisiz erisim denemelerinde her zaman 404 donmeli (403 degil — 403 hesabin var oldugunu acilar). "
                            "Rate limiting: dakikada 20'den fazla farkli account_id sorgulama 429 donmeli."
                        ),
                        "regulation": "BDDK",
                        "request": {
                            "method": "GET",
                            "path": "/api/v1/accounts/{{sequential_id}}",
                            "headers": {
                                "Authorization": "Bearer {{attacker_token}}"
                            },
                            "note": "sequential_id: 1, 2, 3... sirayla denenir"
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 404},
                            {"type": "response_time", "max_ms": 500, "note": "Sabit yanit suresi — timing attack onleme"}
                        ]
                    }
                ],
                "risk_matrix": {
                    "API1": {"tested": True, "findings": 2}
                }
            }
        },

        "owasp_api2_auth": {
            "input": "POST /api/v1/auth/login",
            "output": {
                "security_tests": [
                    {
                        "id": "SEC-AUTH-001",
                        "title": "Brute Force — Sifre deneme saldirisi",
                        "owasp": "API2",
                        "cwe": "CWE-307",
                        "severity": "critical",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "attack_scenario": (
                            "Saldirgan, bilinen bir email adresi icin yaygin sifreleri sirayla dener "
                            "(credential stuffing / dictionary attack). Otomasyon araci ile saniyede 10+ "
                            "istek gonderir. Koruma yoksa binlerce sifre kisa surede denenebilir."
                        ),
                        "expected_defense": (
                            "5 basarisiz denemeden sonra hesap gecici olarak kilitlenmeli (15 dakika). "
                            "Progressive delay: her basarisiz denemede yanit suresi artar (1sn, 2sn, 4sn...). "
                            "IP bazli rate limiting: ayni IP'den dakikada 10 login istegi sonrasi 429. "
                            "CAPTCHA: 3. basarisiz denemeden sonra aktif."
                        ),
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/auth/login",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "email": "target@bgtsbank.com.tr",
                                "password": "{{wordlist_password}}"
                            },
                            "note": "6+ kez tekrarlanir"
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 429, "note": "6. denemede"},
                            {"type": "header", "name": "Retry-After", "operator": "exists"},
                            {"type": "json_path", "path": "$.error.code", "operator": "equals", "expected": "ACCOUNT_LOCKED"}
                        ]
                    },
                    {
                        "id": "SEC-AUTH-002",
                        "title": "Token Manipulasyonu — JWT payload degistirme",
                        "owasp": "API2",
                        "cwe": "CWE-345",
                        "severity": "critical",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "attack_scenario": (
                            "Saldirgan gecerli bir JWT token alir, base64 ile decode eder ve payload'daki "
                            "user_id veya role alanini degistirir (ornegin role: 'user' -> 'admin'). "
                            "Degistirilmis token'i imzasiz veya sifresiz olarak API'ye gonderir. "
                            "Ayrica 'alg: none' saldirisi ile imza dogrulamayi bypass etmeye calisir."
                        ),
                        "expected_defense": (
                            "Her istekte JWT imzasi sunucu tarafinda dogrulanmali (HS256/RS256). "
                            "'alg: none' kabul edilmemeli. Token suresi kontrol edilmeli. "
                            "Manipule edilmis token 401 donmeli."
                        ),
                        "regulation": None,
                        "request": {
                            "method": "GET",
                            "path": "/api/v1/accounts",
                            "headers": {
                                "Authorization": "Bearer {{manipulated_token}}"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 401},
                            {"type": "json_path", "path": "$.accounts", "operator": "not_exists"}
                        ]
                    },
                    {
                        "id": "SEC-AUTH-003",
                        "title": "Session Fixation — Onceden belirlenmis oturum ID'si",
                        "owasp": "API2",
                        "cwe": "CWE-384",
                        "severity": "high",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "attack_scenario": (
                            "Saldirgan login oncesi bir session/token olusturur ve bunu kurbana gonderir "
                            "(phishing link, XSS). Kurban bu session ile basarili login yaparsa, saldirgan "
                            "ayni session ile sisteme erisir. Bankacilikta ozellikle tehlikeli — hesap "
                            "islemleri saldirganin kontrolune gecer."
                        ),
                        "expected_defense": (
                            "Basarili login sonrasi mevcut session ID tamamen yenilenmeli (session regeneration). "
                            "Eski session_id / refresh_token gecersiz kilinmali. "
                            "Login isleminde onceki tum aktif oturumlarin listesi kullaniciya gosterilmeli."
                        ),
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/auth/login",
                            "headers": {
                                "Content-Type": "application/json",
                                "Cookie": "session_id={{attacker_session}}"
                            },
                            "body": {
                                "email": "victim@bgtsbank.com.tr",
                                "password": "VictimPass123!"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 200},
                            {"type": "json_path", "path": "$.session_id", "operator": "not_equals", "expected": "{{attacker_session}}"},
                            {"type": "header", "name": "Set-Cookie", "operator": "contains", "expected": "session_id="}
                        ]
                    }
                ],
                "risk_matrix": {
                    "API2": {"tested": True, "findings": 3}
                }
            }
        }
    },

    # ── CHAIN BUILDER ───────────────────────────────────────────────────────
    "chain_builder": {

        "transfer_flow": {
            "input": "Login, get accounts, create transfer, verify balance",
            "output": {
                "chains": [
                    {
                        "name": "Para Transferi End-to-End Akisi",
                        "description": "Login'den baslayarak hesap secimi, transfer islemi ve bakiye dogrulama adimlarini kapsayan tam bir havale akisi",
                        "priority": "P0",
                        "estimated_duration_ms": 8000,
                        "steps": [
                            {
                                "order": 1,
                                "label": "Kullanici Girisi",
                                "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                                "headers": {"Content-Type": "application/json"},
                                "body": {
                                    "email": "{{test_email}}",
                                    "password": "{{test_password}}"
                                },
                                "extract": [
                                    {"name": "auth_token", "json_path": "$.access_token"},
                                    {"name": "user_id", "json_path": "$.user.id"}
                                ],
                                "assertions": [
                                    {"type": "status_code", "expected": 200},
                                    {"type": "json_path", "path": "$.access_token", "operator": "exists"}
                                ],
                                "on_failure": "abort",
                                "timeout_ms": 3000
                            },
                            {
                                "order": 2,
                                "label": "Hesap Listesi Getir",
                                "endpoint": {"method": "GET", "path": "/api/v1/accounts"},
                                "headers": {"Authorization": "Bearer {{auth_token}}"},
                                "extract": [
                                    {"name": "from_iban", "json_path": "$.accounts[0].iban"},
                                    {"name": "from_account_id", "json_path": "$.accounts[0].id"},
                                    {"name": "balance_before", "json_path": "$.accounts[0].balance"}
                                ],
                                "assertions": [
                                    {"type": "status_code", "expected": 200},
                                    {"type": "json_path", "path": "$.accounts", "operator": "length_gte", "expected": 1}
                                ],
                                "on_failure": "abort",
                                "timeout_ms": 2000
                            },
                            {
                                "order": 3,
                                "label": "Para Transferi",
                                "endpoint": {"method": "POST", "path": "/api/v1/transfers"},
                                "headers": {
                                    "Authorization": "Bearer {{auth_token}}",
                                    "Content-Type": "application/json",
                                    "X-Idempotency-Key": "{{$randomUUID}}"
                                },
                                "body": {
                                    "from_iban": "{{from_iban}}",
                                    "to_iban": "TR120006200000000123456789",
                                    "amount": 100.00,
                                    "currency": "TRY",
                                    "description": "E2E test transferi — {{$timestamp}}"
                                },
                                "extract": [
                                    {"name": "transfer_id", "json_path": "$.transfer_id"},
                                    {"name": "transfer_status", "json_path": "$.status"}
                                ],
                                "assertions": [
                                    {"type": "status_code", "expected": 201},
                                    {"type": "json_path", "path": "$.transfer_id", "operator": "exists"},
                                    {"type": "json_path", "path": "$.status", "operator": "one_of", "expected": ["completed", "pending"]},
                                    {"type": "response_time", "max_ms": 3000}
                                ],
                                "on_failure": "abort",
                                "timeout_ms": 5000,
                                "retry": {"max_attempts": 2, "backoff_ms": 1000}
                            },
                            {
                                "order": 4,
                                "label": "Bakiye Dogrulama",
                                "endpoint": {"method": "GET", "path": "/api/v1/accounts/{{from_account_id}}/balance"},
                                "headers": {"Authorization": "Bearer {{auth_token}}"},
                                "extract": [
                                    {"name": "balance_after", "json_path": "$.balance"}
                                ],
                                "assertions": [
                                    {"type": "status_code", "expected": 200},
                                    {"type": "computed", "expression": "{{balance_before}} - {{balance_after}}", "operator": "equals", "expected": 100.00, "note": "Transfer tutari kadar azalma"},
                                    {"type": "response_time", "max_ms": 1000}
                                ],
                                "on_failure": "warn",
                                "timeout_ms": 2000
                            }
                        ],
                        "post_conditions": [
                            "Bakiye tutarlilik kontrolu: balance_before - balance_after == transfer_amount",
                            "Transaction log kaydi: transfer_id islem gecmisinde gorunmeli",
                            "Idempotency: Ayni X-Idempotency-Key ile tekrar istek gonderirsek duplicate islem olmamalı"
                        ],
                        "cleanup": [
                            {"label": "Test transferini geri al (varsa)", "endpoint": "POST /api/v1/transfers/{{transfer_id}}/reverse"}
                        ]
                    }
                ]
            }
        },

        "auth_flow": {
            "input": "Register, login, refresh token, access protected resource, logout",
            "output": {
                "chains": [
                    {
                        "name": "Kimlik Dogrulama Yasam Dongusu",
                        "description": "Kullanici kayit, giris, token yenileme, korunakli kaynak erisimi ve cikis adimlarini kapsayan tam auth akisi",
                        "priority": "P0",
                        "estimated_duration_ms": 6000,
                        "steps": [
                            {
                                "order": 1,
                                "label": "Kullanici Girisi",
                                "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                                "headers": {"Content-Type": "application/json"},
                                "body": {
                                    "email": "{{test_email}}",
                                    "password": "{{test_password}}"
                                },
                                "extract": [
                                    {"name": "access_token", "json_path": "$.access_token"},
                                    {"name": "refresh_token", "json_path": "$.refresh_token"}
                                ],
                                "assertions": [
                                    {"type": "status_code", "expected": 200}
                                ],
                                "on_failure": "abort",
                                "timeout_ms": 3000
                            },
                            {
                                "order": 2,
                                "label": "Token Yenileme",
                                "endpoint": {"method": "POST", "path": "/api/v1/auth/refresh"},
                                "headers": {"Content-Type": "application/json"},
                                "body": {
                                    "refresh_token": "{{refresh_token}}"
                                },
                                "extract": [
                                    {"name": "new_access_token", "json_path": "$.access_token"},
                                    {"name": "new_refresh_token", "json_path": "$.refresh_token"}
                                ],
                                "assertions": [
                                    {"type": "status_code", "expected": 200},
                                    {"type": "json_path", "path": "$.access_token", "operator": "not_equals", "expected": "{{access_token}}"}
                                ],
                                "on_failure": "abort",
                                "timeout_ms": 2000
                            },
                            {
                                "order": 3,
                                "label": "Korunakli Kaynak Erisimi (Yeni Token ile)",
                                "endpoint": {"method": "GET", "path": "/api/v1/accounts"},
                                "headers": {"Authorization": "Bearer {{new_access_token}}"},
                                "assertions": [
                                    {"type": "status_code", "expected": 200},
                                    {"type": "json_path", "path": "$.accounts", "operator": "exists"}
                                ],
                                "on_failure": "warn",
                                "timeout_ms": 2000
                            },
                            {
                                "order": 4,
                                "label": "Eski Token ile Erisim (Revoke Kontrolu)",
                                "endpoint": {"method": "GET", "path": "/api/v1/accounts"},
                                "headers": {"Authorization": "Bearer {{access_token}}"},
                                "assertions": [
                                    {"type": "status_code", "expected": 401, "note": "Eski token refresh sonrasi gecersiz olmali"}
                                ],
                                "on_failure": "warn",
                                "timeout_ms": 2000
                            },
                            {
                                "order": 5,
                                "label": "Cikis",
                                "endpoint": {"method": "POST", "path": "/api/v1/auth/logout"},
                                "headers": {"Authorization": "Bearer {{new_access_token}}"},
                                "assertions": [
                                    {"type": "status_code", "operator": "one_of", "expected": [200, 204]}
                                ],
                                "on_failure": "warn",
                                "timeout_ms": 2000
                            }
                        ],
                        "post_conditions": [
                            "Logout sonrasi new_access_token ile erisim 401 donmeli",
                            "Refresh token rotation: eski refresh_token artik kullanilamaz",
                            "Tum oturum islemleri audit log'a kaydedilmeli"
                        ]
                    }
                ]
            }
        }
    },

    # ── SPEC ANALYSIS ───────────────────────────────────────────────────────
    "spec_analysis": {

        "banking_api_spec": {
            "input": (
                "OpenAPI spec with endpoints: "
                "POST /auth/login, GET /accounts, GET /accounts/{id}, "
                "POST /transfers, GET /transfers/{id}, POST /payments"
            ),
            "output": {
                "risk_summary": {"critical": 3, "high": 2, "medium": 1, "low": 0},
                "high_risk_endpoints": [
                    {
                        "method": "POST",
                        "path": "/transfers",
                        "risk": "critical",
                        "reason": "Finansal islem — para transferi, BOLA ve yetkisiz erisim riski"
                    },
                    {
                        "method": "POST",
                        "path": "/auth/login",
                        "risk": "critical",
                        "reason": "Kimlik dogrulama — brute force, credential stuffing riski"
                    },
                    {
                        "method": "POST",
                        "path": "/payments",
                        "risk": "critical",
                        "reason": "Odeme islemi — PCI-DSS kapsami, kart verisi guvenligi"
                    }
                ],
                "pii_endpoints": [
                    {"method": "GET", "path": "/accounts/{id}", "pii_fields": ["iban", "tckn", "owner_name", "phone"]},
                    {"method": "GET", "path": "/transfers/{id}", "pii_fields": ["from_iban", "to_iban", "description"]}
                ],
                "financial_endpoints": [
                    {"method": "POST", "path": "/transfers", "type": "havale/eft"},
                    {"method": "POST", "path": "/payments", "type": "odeme"}
                ],
                "compliance_requirements": [
                    {"regulation": "BDDK", "endpoints": ["/transfers", "/payments"], "requirement": "Gunluk islem limiti, cift kontrol, islem kaydi"},
                    {"regulation": "KVKK", "endpoints": ["/accounts/{id}"], "requirement": "IBAN/TCKN maskeleme, erisim kaydi tutma"},
                    {"regulation": "MASAK", "endpoints": ["/transfers"], "requirement": "75.000 TRY ustu islemler icin otomatik bildirim"},
                    {"regulation": "PCI-DSS", "endpoints": ["/payments"], "requirement": "Kart verisi tokenizasyonu, TLS 1.2+"}
                ],
                "dependency_graph": [
                    {"from": "POST /auth/login", "to": "GET /accounts", "data": "access_token"},
                    {"from": "GET /accounts", "to": "POST /transfers", "data": "from_iban, account_id"},
                    {"from": "POST /transfers", "to": "GET /transfers/{id}", "data": "transfer_id"}
                ]
            }
        }
    }
}


# ============================================================================
# KEYWORD → EXAMPLE MAPPING
# ============================================================================

_KEYWORD_MAP: Dict[str, List[str]] = {
    # test_generation keywords
    "transfer": ["test_generation.banking_transfer"],
    "havale": ["test_generation.banking_transfer"],
    "eft": ["test_generation.banking_transfer"],
    "para": ["test_generation.banking_transfer"],
    "iban": ["test_generation.banking_transfer", "test_generation.banking_account"],
    "auth": ["test_generation.banking_auth"],
    "login": ["test_generation.banking_auth"],
    "giris": ["test_generation.banking_auth"],
    "password": ["test_generation.banking_auth"],
    "sifre": ["test_generation.banking_auth"],
    "account": ["test_generation.banking_account"],
    "hesap": ["test_generation.banking_account"],
    "balance": ["test_generation.banking_account"],
    "bakiye": ["test_generation.banking_account"],
    # security_audit keywords
    "bola": ["security_audit.owasp_api1_bola"],
    "idor": ["security_audit.owasp_api1_bola"],
    "api1": ["security_audit.owasp_api1_bola"],
    "brute": ["security_audit.owasp_api2_auth"],
    "token": ["security_audit.owasp_api2_auth"],
    "session": ["security_audit.owasp_api2_auth"],
    "api2": ["security_audit.owasp_api2_auth"],
    # chain_builder keywords
    "flow": ["chain_builder.transfer_flow", "chain_builder.auth_flow"],
    "akis": ["chain_builder.transfer_flow", "chain_builder.auth_flow"],
    "chain": ["chain_builder.transfer_flow", "chain_builder.auth_flow"],
    "e2e": ["chain_builder.transfer_flow"],
    "refresh": ["chain_builder.auth_flow"],
    "logout": ["chain_builder.auth_flow"],
    # spec_analysis keywords
    "spec": ["spec_analysis.banking_api_spec"],
    "openapi": ["spec_analysis.banking_api_spec"],
    "swagger": ["spec_analysis.banking_api_spec"],
    "risk": ["spec_analysis.banking_api_spec"],
}

# Path pattern → example mapping (for endpoint path matching)
_PATH_PATTERNS: List[tuple] = [
    (re.compile(r"/transfer", re.I), "banking_transfer"),
    (re.compile(r"/havale|/eft", re.I), "banking_transfer"),
    (re.compile(r"/auth|/login|/token", re.I), "banking_auth"),
    (re.compile(r"/account|/hesap|/balance|/bakiye", re.I), "banking_account"),
    (re.compile(r"/payment|/odeme", re.I), "banking_transfer"),  # similar structure
]


# ============================================================================
# PUBLIC API
# ============================================================================

def get_few_shot_examples(
    mode: str,
    endpoint_keywords: Optional[List[str]] = None,
    max_examples: int = 2,
) -> str:
    """
    Verilen mod icin formatlanmis few-shot ornekleri dondurur.

    Args:
        mode:              Ajan modu — "test_generation", "security_audit",
                           "chain_builder", "spec_analysis"
        endpoint_keywords: Endpoint anahtar kelimeleri — ["transfer", "iban"]
        max_examples:      Maksimum ornek sayisi (default 2)

    Returns:
        System prompt'a eklenmeye hazir formatlanmis string.
        Ornek bulunamazsa bos string.
    """
    mode_examples = FEW_SHOT_EXAMPLES.get(mode)
    if not mode_examples:
        logger.debug("Few-shot ornekleri bulunamadi: mode=%s", mode)
        return ""

    # Keyword-based matching
    matched_keys: List[str] = []
    if endpoint_keywords:
        seen = set()  # type: set
        for kw in endpoint_keywords:
            kw_lower = kw.lower().strip()
            refs = _KEYWORD_MAP.get(kw_lower, [])
            for ref in refs:
                parts = ref.split(".", 1)
                if len(parts) == 2 and parts[0] == mode and parts[1] not in seen:
                    matched_keys.append(parts[1])
                    seen.add(parts[1])

    # If no keyword matches, fall back to all examples for this mode
    if not matched_keys:
        matched_keys = list(mode_examples.keys())

    # Limit
    selected_keys = matched_keys[:max_examples]
    if not selected_keys:
        return ""

    # Format
    sections = []  # type: List[str]
    for key in selected_keys:
        example = mode_examples.get(key)
        if not example:
            continue
        formatted = _format_example(key, example)
        sections.append(formatted)

    if not sections:
        return ""

    header = (
        "\n\n# === FEW-SHOT ORNEKLER (Kalite Referansi) ===\n"
        "Asagidaki ornekler BEKLENEN kalite seviyesini gosterir.\n"
        "Ayni yapiyi, detay seviyesini ve bankacilik domain bilgisini kullan.\n\n"
    )
    footer = "\n# === FEW-SHOT ORNEKLER SONU ===\n"

    return header + "\n---\n".join(sections) + footer


def get_example_for_endpoint(
    endpoint_path: str,
    mode: str,
) -> Optional[dict]:
    """
    Belirli bir endpoint path'i icin en uygun ornegi bul.

    Args:
        endpoint_path: API endpoint path'i — "/api/v1/transfers"
        mode:          Ajan modu

    Returns:
        Eslesen ornek dict'i veya None.
    """
    mode_examples = FEW_SHOT_EXAMPLES.get(mode)
    if not mode_examples:
        return None

    # 1. Path pattern matching
    for pattern, example_key in _PATH_PATTERNS:
        if pattern.search(endpoint_path):
            example = mode_examples.get(example_key)
            if example:
                return example

    # 2. Direct substring match on example input
    path_lower = endpoint_path.lower()
    for key, example in mode_examples.items():
        example_input = example.get("input", "").lower()
        # Check if any significant part of the path appears in the example input
        path_parts = [p for p in path_lower.split("/") if p and len(p) > 2]
        for part in path_parts:
            if part in example_input:
                return example

    return None


def list_available_examples() -> Dict[str, List[str]]:
    """
    Mevcut ornek kategorilerini listele.
    Returns: {"test_generation": ["banking_transfer", "banking_auth", ...], ...}
    """
    result = {}  # type: Dict[str, List[str]]
    for mode, examples in FEW_SHOT_EXAMPLES.items():
        result[mode] = list(examples.keys())
    return result


def get_example_count() -> Dict[str, int]:
    """Her mode icin ornek sayisini dondur."""
    return {mode: len(examples) for mode, examples in FEW_SHOT_EXAMPLES.items()}


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _format_example(key: str, example: dict) -> str:
    """Tek bir ornegi okunabilir string formatina donustur."""
    parts = []  # type: List[str]
    parts.append("## Ornek: %s" % key.replace("_", " ").title())
    parts.append("**Giris:** %s" % example.get("input", ""))
    parts.append("**Beklenen Cikti:**")

    output = example.get("output", {})
    # JSON'u guzel formatla — ama cok buyuk olmamasi icin limit koy
    output_str = json.dumps(output, indent=2, ensure_ascii=False)
    if len(output_str) > 4000:
        # Cok buyuk ornekleri kisalt
        output_str = output_str[:4000] + "\n  ... (kisaltildi)"
    parts.append("```json\n%s\n```" % output_str)

    return "\n".join(parts)
