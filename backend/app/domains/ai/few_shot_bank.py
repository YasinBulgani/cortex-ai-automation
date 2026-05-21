"""
Few-Shot Example Bank — Bankacilik domain'i için kalibreli ornek seti.

Her ajan modu için yuksek kaliteli giriş/cikis ornekleri icerir.
LLM'e "bu kalitede üret" mesajini verir — cikti tutarliligi ve domainin
dogru yansitilmasi için kritik oneme sahiptir.

Kullanim:
    from app.domains.ai.few_shot_bank import get_few_shot_examples

    examples = get_few_shot_examples("test_generation", ["transfer", "iban"])
    system_prompt += examples
"""

import hashlib
import json
import logging
import re
import threading
from typing import Any, Dict, List, Optional

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
                        "title": "Gecerli para transferi - tüm alanlar dolu",
                        "description": "Gecerli IBAN, tutar ve aciklama ile başarılı havale islemi",
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
                        "ai_reasoning": "Temel başarı senaryosu — tüm zorunlu alanlar gecerli degerlerle doldurulmus, happy path dogrulamasi"
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
                        "ai_reasoning": "Zorunlu alan dogrulamasi — API'nin anlamli hata mesajı dondurmesi gerekir"
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
                        "ai_reasoning": "BDDK gunluk limit kontrolu — yuksek tutarli islem ya başarılı ya da limit asildi hatasi donmeli"
                    },
                    {
                        "id": "API-TRF-005",
                        "title": "Guvenlik - BOLA: Baska kullanicinin hesabindan transfer",
                        "description": "Kullanıcı A'nin token'i ile Kullanıcı B'nin IBAN'indan transfer denemesi",
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
                        "description": "MASAK bildirim esigini asan tutar için islem kaydinin duzgun olusturulmasi",
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
                        "title": "Gecerli kimlik bilgileri ile başarılı giriş",
                        "description": "Dogru email ve şifre ile login — access_token ve refresh_token donmeli",
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
                        "ai_reasoning": "Temel auth happy path — token donusunun kontrol edilmesi tüm diger testlerin on kosulu"
                    },
                    {
                        "id": "API-AUTH-002",
                        "title": "Yanlis şifre ile başarısız giriş",
                        "description": "Gecerli email, yanlis şifre — 401 donmeli, şifre bilgisi acilanmamali",
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
                        "ai_reasoning": "Yanlis şifre — hata mesajı 'email bulunamadi' veya 'şifre yanlis' gibi ayristirici bilgi vermemeli (user enumeration onleme)"
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
                        "description": "5 başarısız giriş denemesinden sonra 6. deneme hesap kilidine neden olmali",
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
                            {"step": "5x başarısız giriş", "endpoint": "POST /api/v1/auth/login", "repeat": 5, "body": {"password": "YanlisSifre"}}
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
                        "title": "Uyumluluk - KVKK başarısız giriş loglama",
                        "description": "Başarısız giriş denemesi audit log'a kaydedilmeli — IP, tarih, email",
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
                        "ai_reasoning": "KVKK 12. madde — kişisel veri isleme faaliyetleri kaydedilmeli, başarısız girisler de denetim izine dahil"
                    }
                ]
            }
        },

        # ── Kredi basvurusu ────────────────────────────────────────────────
        "banking_kredi_basvuru": {
            "input": "POST /api/v1/credit/applications with fields: customer_id, amount, currency, term_months, purpose",
            "output": {
                "test_cases": [
                    {
                        "id": "API-CRD-001",
                        "title": "Gecerli kredi basvurusu - bireysel",
                        "description": "Mevcut musteri kimligi ile gecerli tuketici kredisi basvurusu",
                        "test_type": "positive",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/credit/applications"},
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/credit/applications",
                            "headers": {"Authorization": "Bearer {{auth_token}}", "Content-Type": "application/json"},
                            "body": {
                                "customer_id": "{{customer_id}}",
                                "amount": 25000.00,
                                "currency": "TRY",
                                "term_months": 24,
                                "purpose": "consumer"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 201},
                            {"type": "json_path", "path": "$.application_id", "operator": "exists"},
                            {"type": "json_path", "path": "$.status", "operator": "one_of", "expected": ["pending_review", "approved"]},
                            {"type": "json_path", "path": "$.interest_rate", "operator": "greater_than", "expected": 0}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "Kredi basvurusu happy path — BDDK geregi faiz orani ve durum alanlari zorunlu"
                    },
                    {
                        "id": "API-CRD-002",
                        "title": "BDDK - gelir bilgisi eksik ise red",
                        "description": "Belirli tutar uzerinde gelir belgesi zorunlu",
                        "test_type": "compliance",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/credit/applications"},
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/credit/applications",
                            "headers": {"Authorization": "Bearer {{auth_token}}", "Content-Type": "application/json"},
                            "body": {
                                "customer_id": "{{customer_id}}",
                                "amount": 50000.00,
                                "currency": "TRY",
                                "term_months": 36,
                                "purpose": "consumer"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 422},
                            {"type": "json_path", "path": "$.error.code", "operator": "equals", "expected": "INCOME_PROOF_REQUIRED"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "BDDK tuketici kredisi: belirli tutar uzerinde gelir belgesi zorunlu"
                    },
                    {
                        "id": "API-CRD-003",
                        "title": "Guvenlik - Baska musterinin adina basvuru (BOLA)",
                        "description": "Kullanıcı A'nin token'i ile Kullanıcı B'nin customer_id'si — reddedilmeli",
                        "test_type": "security",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/credit/applications"},
                        "owasp_category": "API1",
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/credit/applications",
                            "headers": {"Authorization": "Bearer {{user_a_token}}", "Content-Type": "application/json"},
                            "body": {
                                "customer_id": "{{user_b_customer_id}}",
                                "amount": 10000.00,
                                "currency": "TRY",
                                "term_months": 12,
                                "purpose": "consumer"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "operator": "one_of", "expected": [403, 404]},
                            {"type": "json_path", "path": "$.application_id", "operator": "not_exists"}
                        ],
                        "setup_chain": [
                            {"step": "Login User A", "endpoint": "POST /api/v1/auth/login", "extract": {"user_a_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "OWASP API1: customer_id JWT user ile eslesmeli"
                    }
                ]
            }
        },

        # ── Kart odemesi ───────────────────────────────────────────────────
        "banking_odeme_kart": {
            "input": "POST /api/v1/payments/card with fields: card_token, amount, merchant_ref, currency",
            "output": {
                "test_cases": [
                    {
                        "id": "API-PAY-001",
                        "title": "Gecerli kart odeme - 3DS sonrasi",
                        "description": "3D Secure dogrulanmis token ile başarılı odeme",
                        "test_type": "positive",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/payments/card"},
                        "regulation": "PCI-DSS",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/payments/card",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json",
                                "X-Idempotency-Key": "{{idempotency_key}}"
                            },
                            "body": {
                                "card_token": "{{3ds_verified_token}}",
                                "amount": 149.90,
                                "currency": "TRY",
                                "merchant_ref": "ORDER-2026-000123"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 201},
                            {"type": "json_path", "path": "$.payment_id", "operator": "exists"},
                            {"type": "json_path", "path": "$.card_number", "operator": "not_exists", "note": "PCI-DSS: PAN donmemeli"},
                            {"type": "json_path", "path": "$.cvv", "operator": "not_exists"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}},
                            {"step": "3DS dogrulama", "endpoint": "POST /api/v1/cards/verify-3ds", "extract": {"3ds_verified_token": "$.token"}}
                        ],
                        "ai_reasoning": "PCI-DSS: PAN/CVV response'ta donmemeli; sadece token/payment_id"
                    },
                    {
                        "id": "API-PAY-002",
                        "title": "Guvenlik - Ham PAN reddedilmeli",
                        "description": "Token yerine ham kart numarasi gonderilirse API reddetmeli",
                        "test_type": "security",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/payments/card"},
                        "owasp_category": "API3",
                        "regulation": "PCI-DSS",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/payments/card",
                            "headers": {"Authorization": "Bearer {{auth_token}}", "Content-Type": "application/json"},
                            "body": {
                                "card_number": "4111111111111111",
                                "amount": 100.00,
                                "currency": "TRY"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "operator": "one_of", "expected": [400, 422]},
                            {"type": "json_path", "path": "$.error.code", "operator": "equals", "expected": "RAW_PAN_NOT_ALLOWED"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "PCI-DSS uyumlu API asla ham PAN kabul etmemeli"
                    },
                    {
                        "id": "API-PAY-003",
                        "title": "Idempotency - Ayni anahtar tekrar odeme yapmaz",
                        "description": "Network retry sırasında mukerrer islem onlenmeli",
                        "test_type": "boundary",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/payments/card"},
                        "regulation": "BDDK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/payments/card",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json",
                                "X-Idempotency-Key": "{{fixed_key}}"
                            },
                            "body": {"card_token": "{{token}}", "amount": 100.00, "currency": "TRY"}
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 200, "note": "2. cagri 200 + ayni payment_id"},
                            {"type": "json_path", "path": "$.payment_id", "operator": "equals", "expected": "{{first_payment_id}}"}
                        ],
                        "setup_chain": [
                            {"step": "Ilk odeme", "endpoint": "POST /api/v1/payments/card", "extract": {"first_payment_id": "$.payment_id"}}
                        ],
                        "ai_reasoning": "Odeme API'lari idempotent olmali"
                    }
                ]
            }
        },

        # ── Limit degisikligi ──────────────────────────────────────────────
        "banking_limit_degisim": {
            "input": "PATCH /api/v1/customers/{id}/limits with fields: daily_transfer_limit, monthly_transfer_limit",
            "output": {
                "test_cases": [
                    {
                        "id": "API-LIM-001",
                        "title": "Gecerli limit yukseltme (step-up sonrasi)",
                        "description": "Musteri gunluk transfer limitini yukseltir; OTP/biyometri zorunlu",
                        "test_type": "positive",
                        "priority": "P1",
                        "endpoint": {"method": "PATCH", "path": "/api/v1/customers/{id}/limits"},
                        "regulation": "BDDK",
                        "request": {
                            "method": "PATCH",
                            "path": "/api/v1/customers/{{customer_id}}/limits",
                            "headers": {"Authorization": "Bearer {{step_up_token}}", "Content-Type": "application/json"},
                            "body": {"daily_transfer_limit": 50000.00, "monthly_transfer_limit": 500000.00}
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 200},
                            {"type": "json_path", "path": "$.new_limits.daily", "operator": "equals", "expected": 50000.00}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}},
                            {"step": "Step-up OTP", "endpoint": "POST /api/v1/auth/step-up", "extract": {"step_up_token": "$.step_up_token"}}
                        ],
                        "ai_reasoning": "BDDK: limit yukseltmek için kimlik step-up zorunlu"
                    },
                    {
                        "id": "API-LIM-002",
                        "title": "Step-up olmadan limit degisikligi reddi",
                        "description": "Standart token ile limit degisikligi 403 donmeli",
                        "test_type": "security",
                        "priority": "P0",
                        "endpoint": {"method": "PATCH", "path": "/api/v1/customers/{id}/limits"},
                        "owasp_category": "API5",
                        "regulation": "BDDK",
                        "request": {
                            "method": "PATCH",
                            "path": "/api/v1/customers/{{customer_id}}/limits",
                            "headers": {"Authorization": "Bearer {{auth_token}}", "Content-Type": "application/json"},
                            "body": {"daily_transfer_limit": 50000.00}
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 403},
                            {"type": "json_path", "path": "$.error.code", "operator": "equals", "expected": "STEP_UP_REQUIRED"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "OWASP API5: finansal etkili islem için step-up zorunlu"
                    }
                ]
            }
        },

        # ── Musteri onboarding ─────────────────────────────────────────────
        "banking_musteri_onboarding": {
            "input": "POST /api/v1/customers/onboarding with fields: tckn, full_name, dob, phone, email, address",
            "output": {
                "test_cases": [
                    {
                        "id": "API-ONB-001",
                        "title": "Gecerli yeni musteri (18 yas ustu)",
                        "description": "Tüm zorunlu alanlarla başarılı hesap acilisi",
                        "test_type": "positive",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/customers/onboarding"},
                        "regulation": "MASAK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/customers/onboarding",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "tckn": "{{valid_tckn}}",
                                "full_name": "Ayse Yilmaz",
                                "dob": "1990-05-12",
                                "phone": "+905551234567",
                                "email": "ayse.yilmaz@example.com",
                                "address": "Kadikoy, Istanbul"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 201},
                            {"type": "json_path", "path": "$.customer_id", "operator": "exists"},
                            {"type": "json_path", "path": "$.kyc_status", "operator": "one_of", "expected": ["pending", "in_review"]},
                            {"type": "json_path", "path": "$.tckn", "operator": "not_exists", "note": "KVKK: TCKN donmez"}
                        ],
                        "setup_chain": [],
                        "ai_reasoning": "MASAK: yeni musteri KYC surecinden gecene kadar full yetki almamali"
                    },
                    {
                        "id": "API-ONB-002",
                        "title": "Yas dogrulama - 18 yas alti reddedilmeli",
                        "description": "MASAK geregi 18 yas alti bireysel hesap acilamaz",
                        "test_type": "compliance",
                        "priority": "P0",
                        "endpoint": {"method": "POST", "path": "/api/v1/customers/onboarding"},
                        "regulation": "MASAK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/customers/onboarding",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "tckn": "{{valid_tckn}}",
                                "full_name": "Kucuk Musteri",
                                "dob": "2015-01-01",
                                "phone": "+905551234567",
                                "email": "kucuk@example.com",
                                "address": "Istanbul"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 422},
                            {"type": "json_path", "path": "$.error.code", "operator": "equals", "expected": "AGE_REQUIREMENT_NOT_MET"}
                        ],
                        "setup_chain": [],
                        "ai_reasoning": "MASAK: 18 yas alti bireysel hesap acilamaz"
                    }
                ]
            }
        },

        # ── KYC dogrulama ──────────────────────────────────────────────────
        "banking_kyc_verification": {
            "input": "POST /api/v1/kyc/verify with fields: customer_id, document_type, document_image, selfie",
            "output": {
                "test_cases": [
                    {
                        "id": "API-KYC-001",
                        "title": "Başarılı liveness + belge eslestirme",
                        "description": "Selfie + kimlik belgesi uyumu tam; KYC approved",
                        "test_type": "positive",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/kyc/verify"},
                        "regulation": "MASAK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/kyc/verify",
                            "headers": {"Authorization": "Bearer {{auth_token}}", "Content-Type": "application/json"},
                            "body": {
                                "customer_id": "{{customer_id}}",
                                "document_type": "TC_ID",
                                "document_image_base64": "{{valid_doc_image}}",
                                "selfie_base64": "{{matching_selfie}}"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 200},
                            {"type": "json_path", "path": "$.kyc_status", "operator": "equals", "expected": "approved"},
                            {"type": "json_path", "path": "$.liveness_score", "operator": "greater_than", "expected": 0.85}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "MASAK: KYC yuz dogrulama + belge dogrulama"
                    },
                    {
                        "id": "API-KYC-002",
                        "title": "Dusuk liveness - manuel inceleme kuyruguna",
                        "description": "Esigin altinda otomatik red yerine manuel kuyrua",
                        "test_type": "negative",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/kyc/verify"},
                        "regulation": "MASAK",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/kyc/verify",
                            "headers": {"Authorization": "Bearer {{auth_token}}", "Content-Type": "application/json"},
                            "body": {
                                "customer_id": "{{customer_id}}",
                                "document_type": "TC_ID",
                                "document_image_base64": "{{doc}}",
                                "selfie_base64": "{{low_quality_selfie}}"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 202},
                            {"type": "json_path", "path": "$.kyc_status", "operator": "equals", "expected": "manual_review"},
                            {"type": "json_path", "path": "$.review_queue_id", "operator": "exists"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "Dusuk skor otomatik red degil manuel kuyrua gider (UX)"
                    }
                ]
            }
        },

        # ── Fatura odeme ───────────────────────────────────────────────────
        "banking_fatura_odeme": {
            "input": "POST /api/v1/bill-payments with fields: institution_code, subscriber_number, amount, currency",
            "output": {
                "test_cases": [
                    {
                        "id": "API-BILL-001",
                        "title": "Elektrik faturasi odeme - başarılı",
                        "description": "Gecerli kurum kodu ve abone no ile elektrik faturasi odemesi",
                        "test_type": "positive",
                        "priority": "P1",
                        "endpoint": {"method": "POST", "path": "/api/v1/bill-payments"},
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/bill-payments",
                            "headers": {
                                "Authorization": "Bearer {{auth_token}}",
                                "Content-Type": "application/json",
                                "X-Idempotency-Key": "{{idempotency_key}}"
                            },
                            "body": {
                                "institution_code": "BEDAS",
                                "subscriber_number": "1234567890",
                                "amount": 245.75,
                                "currency": "TRY"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 201},
                            {"type": "json_path", "path": "$.payment_id", "operator": "exists"},
                            {"type": "json_path", "path": "$.institution_confirmation_ref", "operator": "exists"},
                            {"type": "response_time", "max_ms": 5000}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "Fatura odeme proxy; institution_confirmation_ref dispute için kritik"
                    },
                    {
                        "id": "API-BILL-002",
                        "title": "Geçersiz kurum kodu - 400, SQL sizintisi yok",
                        "description": "Bilinmeyen institution_code reddedilmeli, internal detay acilamali",
                        "test_type": "security",
                        "priority": "P2",
                        "endpoint": {"method": "POST", "path": "/api/v1/bill-payments"},
                        "owasp_category": "API8",
                        "request": {
                            "method": "POST",
                            "path": "/api/v1/bill-payments",
                            "headers": {"Authorization": "Bearer {{auth_token}}", "Content-Type": "application/json"},
                            "body": {
                                "institution_code": "FAKE_INST_XYZ",
                                "subscriber_number": "1234567890",
                                "amount": 100.00,
                                "currency": "TRY"
                            }
                        },
                        "assertions": [
                            {"type": "status_code", "expected": 400},
                            {"type": "json_path", "path": "$.error.code", "operator": "equals", "expected": "INVALID_INSTITUTION"},
                            {"type": "json_path", "path": "$.error", "operator": "not_contains", "expected": "SELECT"}
                        ],
                        "setup_chain": [
                            {"step": "Login", "endpoint": "POST /api/v1/auth/login", "extract": {"auth_token": "$.access_token"}}
                        ],
                        "ai_reasoning": "OWASP API8: error mesajı SQL/internal detay sizdirmamali"
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
                        "description": "Kullanıcı A'nin token'i ile Kullanıcı B'nin hesap ID'sine erisim denemesi",
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
                            "Saldirgan (Kullanıcı A) kendi hesabi için gecerli bir JWT token alir. "
                            "Ardindan GET /api/v1/accounts/{account_id} istegindeki account_id parametresini "
                            "Kullanıcı B'nin hesap ID'si ile degistirir. Eger API yalnizca JWT'nin gecerliligini "
                            "kontrol edip, hesap sahipligini dogrulamiyorsa, Kullanıcı B'nin tüm hesap bilgileri "
                            "(bakiye, IBAN, islem gecmisi) saldirganin eline geçer."
                        ),
                        "expected_defense": (
                            "403 Forbidden veya 404 Not Found donmeli. "
                            "API, JWT'deki user_id ile talep edilen account_id'nin sahiplik iliskisini kontrol etmeli. "
                            "Başarısız erisim denemesi audit log'a kaydedilmeli (IP, user_id, hedef account_id, zaman)."
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
                            "oldugunu fark eder. GET /api/v1/accounts/1 den baslayarak sirayla tüm hesaplari tarar. "
                            "Her istekte farkli bir HTTP status kodu donmesi (200 var, 404 yok) hangi ID'lerin "
                            "gerçek hesaplara ait oldugunu acilar."
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
                            {"type": "response_time", "max_ms": 500, "note": "Sabit yanıt süresi — timing attack onleme"}
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
                        "title": "Brute Force — Şifre deneme saldirisi",
                        "owasp": "API2",
                        "cwe": "CWE-307",
                        "severity": "critical",
                        "endpoint": {"method": "POST", "path": "/api/v1/auth/login"},
                        "attack_scenario": (
                            "Saldirgan, bilinen bir email adresi için yaygin sifreleri sirayla dener "
                            "(credential stuffing / dictionary attack). Otomasyon araci ile saniyede 10+ "
                            "istek gonderir. Koruma yoksa binlerce şifre kisa surede denenebilir."
                        ),
                        "expected_defense": (
                            "5 başarısız denemeden sonra hesap gecici olarak kilitlenmeli (15 dakika). "
                            "Progressive delay: her başarısız denemede yanıt süresi artar (1sn, 2sn, 4sn...). "
                            "IP bazli rate limiting: ayni IP'den dakikada 10 login istegi sonrasi 429. "
                            "CAPTCHA: 3. başarısız denemeden sonra aktif."
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
                            "'alg: none' kabul edilmemeli. Token süresi kontrol edilmeli. "
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
                            "(phishing link, XSS). Kurban bu session ile başarılı login yaparsa, saldirgan "
                            "ayni session ile sisteme erisir. Bankacilikta ozellikle tehlikeli — hesap "
                            "islemleri saldirganin kontrolune geçer."
                        ),
                        "expected_defense": (
                            "Başarılı login sonrasi mevcut session ID tamamen yenilenmeli (session regeneration). "
                            "Eski session_id / refresh_token geçersiz kilinmali. "
                            "Login isleminde onceki tüm aktif oturumlarin listesi kullaniciya gosterilmeli."
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
                                "label": "Kullanıcı Girisi",
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
                        "description": "Kullanıcı kayit, giriş, token yenileme, korunakli kaynak erisimi ve cikis adimlarini kapsayan tam auth akisi",
                        "priority": "P0",
                        "estimated_duration_ms": 6000,
                        "steps": [
                            {
                                "order": 1,
                                "label": "Kullanıcı Girisi",
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
                                    {"type": "status_code", "expected": 401, "note": "Eski token refresh sonrasi geçersiz olmali"}
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
                            "Tüm oturum islemleri audit log'a kaydedilmeli"
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
                    {"regulation": "MASAK", "endpoints": ["/transfers"], "requirement": "75.000 TRY ustu islemler için otomatik bildirim"},
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
    "giriş": ["test_generation.banking_auth"],
    "password": ["test_generation.banking_auth"],
    "şifre": ["test_generation.banking_auth"],
    "account": ["test_generation.banking_account"],
    "hesap": ["test_generation.banking_account"],
    "balance": ["test_generation.banking_account"],
    "bakiye": ["test_generation.banking_account"],
    # kredi
    "kredi": ["test_generation.banking_kredi_basvuru"],
    "credit": ["test_generation.banking_kredi_basvuru"],
    "loan": ["test_generation.banking_kredi_basvuru"],
    "basvuru": ["test_generation.banking_kredi_basvuru"],
    "gelir": ["test_generation.banking_kredi_basvuru"],
    # odeme/kart
    "kart": ["test_generation.banking_odeme_kart"],
    "card": ["test_generation.banking_odeme_kart"],
    "payment": ["test_generation.banking_odeme_kart", "test_generation.banking_fatura_odeme"],
    "odeme": ["test_generation.banking_odeme_kart", "test_generation.banking_fatura_odeme"],
    "3ds": ["test_generation.banking_odeme_kart"],
    "pci": ["test_generation.banking_odeme_kart"],
    # limit
    "limit": ["test_generation.banking_limit_degisim"],
    "stepup": ["test_generation.banking_limit_degisim"],
    "step-up": ["test_generation.banking_limit_degisim"],
    "otp": ["test_generation.banking_limit_degisim"],
    # onboarding
    "onboarding": ["test_generation.banking_musteri_onboarding"],
    "kayit": ["test_generation.banking_musteri_onboarding"],
    "register": ["test_generation.banking_musteri_onboarding"],
    "musteri": ["test_generation.banking_musteri_onboarding"],
    # kyc
    "kyc": ["test_generation.banking_kyc_verification"],
    "liveness": ["test_generation.banking_kyc_verification"],
    "selfie": ["test_generation.banking_kyc_verification"],
    "belge": ["test_generation.banking_kyc_verification"],
    "tckn": ["test_generation.banking_kyc_verification", "test_generation.banking_musteri_onboarding"],
    # fatura
    "fatura": ["test_generation.banking_fatura_odeme"],
    "bill": ["test_generation.banking_fatura_odeme"],
    "elektrik": ["test_generation.banking_fatura_odeme"],
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
    query: Optional[str] = None,
) -> str:
    """
    Verilen mod için formatlanmis few-shot ornekleri dondurur.

    Oncelik:
        1. DB (few_shot_examples) — quality_score + verified + embedding
        2. Statik FEW_SHOT_EXAMPLES — DB yoksa veya kayit bulunamazsa

    Args:
        mode:              Ajan modu
        endpoint_keywords: Endpoint anahtar kelimeleri
        max_examples:      Max ornek sayisi
        query:             Kullanıcı sorgusu (embedding secimi için)
    """
    # 1) DB tarafli
    db_examples = _fetch_from_db(mode, endpoint_keywords, query, max_examples)
    if db_examples:
        return _format_many(db_examples)

    # 2) Statik fallback
    mode_examples = FEW_SHOT_EXAMPLES.get(mode)
    if not mode_examples:
        logger.debug("Few-shot ornekleri bulunamadi: mode=%s", mode)
        return ""

    matched_keys: List[str] = []
    if endpoint_keywords:
        seen: set = set()
        for kw in endpoint_keywords:
            kw_lower = kw.lower().strip()
            refs = _KEYWORD_MAP.get(kw_lower, [])
            for ref in refs:
                parts = ref.split(".", 1)
                if len(parts) == 2 and parts[0] == mode and parts[1] not in seen:
                    matched_keys.append(parts[1])
                    seen.add(parts[1])

    if not matched_keys:
        matched_keys = list(mode_examples.keys())

    selected_keys = matched_keys[:max_examples]
    if not selected_keys:
        return ""

    sections: List[str] = []
    for key in selected_keys:
        example = mode_examples.get(key)
        if not example:
            continue
        sections.append(_format_example(key, example))

    if not sections:
        return ""

    return _format_header() + "\n---\n".join(sections) + _format_footer()


def _format_header() -> str:
    return (
        "\n\n# === FEW-SHOT ORNEKLER (Kalite Referansi) ===\n"
        "Asagidaki ornekler BEKLENEN kalite seviyesini gosterir.\n"
        "Ayni yapiyi, detay seviyesini ve bankacilik domain bilgisini kullan.\n\n"
    )


def _format_footer() -> str:
    return "\n# === FEW-SHOT ORNEKLER SONU ===\n"


def _format_many(examples: List[Dict[str, Any]]) -> str:
    """DB'den gelen ornek listesini formatla (negatif ornek destekli)."""
    sections: List[str] = []
    for ex in examples:
        key = ex.get("key", "example")
        is_negative = bool(ex.get("is_negative", False))
        bad_reason = ex.get("bad_reason") or ""
        data = {"input": ex.get("input_text", ""), "output": ex.get("output_json", {})}
        sections.append(_format_example(key, data, is_negative=is_negative, bad_reason=bad_reason))
    if not sections:
        return ""
    return _format_header() + "\n---\n".join(sections) + _format_footer()


# ── DB katmani ───────────────────────────────────────────────────────────


_DB_CACHE: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
_DB_CACHE_TTL = 300.0
_DB_CACHE_LOCK = threading.RLock()


def _cache_key(mode: str, keywords: Optional[List[str]], query: Optional[str], n: int) -> str:
    raw = f"{mode}|{','.join(sorted(keywords or []))}|{(query or '').lower()[:120]}|{n}"
    return hashlib.sha1(raw.encode(), usedforsecurity=False).hexdigest()[:16]


def _fetch_from_db(
    mode: str,
    keywords: Optional[List[str]],
    query: Optional[str],
    max_examples: int,
) -> Optional[List[Dict[str, Any]]]:
    """DB'den ornekleri cek. DB yoksa/hata None (statik fallback tetiklenir)."""
    import time
    ck = _cache_key(mode, keywords, query, max_examples)
    with _DB_CACHE_LOCK:
        cached = _DB_CACHE.get(ck)
        if cached and (time.time() - cached[0]) < _DB_CACHE_TTL:
            return cached[1]

    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception as exc:
        logger.debug("few_shot DB baglanamadi: %s", exc)
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'few_shot_examples')"
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None

            kw_list = [k.lower().strip() for k in (keywords or []) if k and k.strip()]
            if kw_list:
                cur.execute(
                    """
                    SELECT id, key, input_text, output_json, is_negative, bad_reason,
                           quality_score, verified_by_human,
                           (CARDINALITY(ARRAY(SELECT UNNEST(domain_tags)
                                              INTERSECT
                                              SELECT UNNEST(%s::text[])))) AS match_cnt
                    FROM few_shot_examples
                    WHERE mode = %s
                    ORDER BY match_cnt DESC, verified_by_human DESC,
                             quality_score DESC, usage_count DESC, id ASC
                    LIMIT %s
                    """,
                    (kw_list, mode, max_examples * 3),
                )
            else:
                cur.execute(
                    """
                    SELECT id, key, input_text, output_json, is_negative, bad_reason,
                           quality_score, verified_by_human, 0 AS match_cnt
                    FROM few_shot_examples
                    WHERE mode = %s
                    ORDER BY verified_by_human DESC, quality_score DESC,
                             usage_count DESC, id ASC
                    LIMIT %s
                    """,
                    (mode, max_examples * 3),
                )
            rows = cur.fetchall() or []
    except Exception as exc:
        logger.debug("few_shot DB okuma hatasi: %s", exc)
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass

    positives = [r for r in rows if not r[4]]
    negatives = [r for r in rows if r[4]]
    selected = positives[:max_examples]
    if max_examples > 1 and negatives and len(selected) < max_examples:
        selected.append(negatives[0])
    if not selected:
        return None

    results: List[Dict[str, Any]] = []
    ids_to_bump: List[int] = []
    for r in selected:
        results.append({
            "id": r[0],
            "key": r[1],
            "input_text": r[2],
            "output_json": r[3] or {},
            "is_negative": bool(r[4]),
            "bad_reason": r[5],
            "quality_score": float(r[6]) if r[6] is not None else 5.0,
            "verified_by_human": bool(r[7]),
        })
        ids_to_bump.append(r[0])

    if ids_to_bump:
        threading.Thread(target=_bump_usage_counts, args=(ids_to_bump,), daemon=True).start()

    with _DB_CACHE_LOCK:
        _DB_CACHE[ck] = (time.time(), results)
    return results


def _bump_usage_counts(ids: List[int]) -> None:
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE few_shot_examples SET usage_count = usage_count + 1, updated_at = now() WHERE id = ANY(%s)",
                    (ids,),
                )
        finally:
            conn.close()
    except Exception as exc:
        logger.debug("usage_count bump hatasi: %s", exc)


def seed_few_shot_examples_from_static(force: bool = False) -> Dict[str, int]:
    """Statik FEW_SHOT_EXAMPLES'i DB'ye yaz (idempotent)."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception as exc:
        logger.warning("few_shot seed: DB baglanamadi: %s", exc)
        return {"inserted": 0, "skipped": 0}

    inserted = 0
    skipped = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'few_shot_examples')"
            )
            row = cur.fetchone()
            if not row or not row[0]:
                logger.warning("few_shot_examples tablosu yok — migration çalıştır")
                return {"inserted": 0, "skipped": 0}

            for mode, examples in FEW_SHOT_EXAMPLES.items():
                for key, example in examples.items():
                    input_text = example.get("input") or ""
                    output = example.get("output") or {}
                    tags = _derive_tags(mode, key, input_text)
                    output_str = json.dumps(output, ensure_ascii=False)
                    if force:
                        cur.execute(
                            """
                            INSERT INTO few_shot_examples
                                (mode, key, input_text, output_json, domain_tags,
                                 quality_score, verified_by_human, source)
                            VALUES (%s, %s, %s, %s::jsonb, %s, 10.00, TRUE, 'seed')
                            ON CONFLICT (mode, key) DO UPDATE SET
                                input_text = EXCLUDED.input_text,
                                output_json = EXCLUDED.output_json,
                                domain_tags = EXCLUDED.domain_tags,
                                quality_score = 10.00,
                                verified_by_human = TRUE,
                                updated_at = now()
                            """,
                            (mode, key, input_text, output_str, tags),
                        )
                        inserted += 1
                    else:
                        cur.execute(
                            """
                            INSERT INTO few_shot_examples
                                (mode, key, input_text, output_json, domain_tags,
                                 quality_score, verified_by_human, source)
                            VALUES (%s, %s, %s, %s::jsonb, %s, 10.00, TRUE, 'seed')
                            ON CONFLICT (mode, key) DO NOTHING
                            """,
                            (mode, key, input_text, output_str, tags),
                        )
                        if cur.rowcount > 0:
                            inserted += 1
                        else:
                            skipped += 1
    except Exception as exc:
        logger.warning("few_shot seed hatasi: %s", exc)
        return {"inserted": inserted, "skipped": skipped, "error": str(exc)}
    finally:
        try:
            conn.close()
        except Exception:
            pass

    logger.info("few_shot seed: inserted=%d skipped=%d force=%s", inserted, skipped, force)
    with _DB_CACHE_LOCK:
        _DB_CACHE.clear()
    return {"inserted": inserted, "skipped": skipped}


def _derive_tags(mode: str, key: str, input_text: str) -> List[str]:
    """Ornek için domain tag listesi turet."""
    text = f"{mode} {key} {input_text}".lower()
    tags: set[str] = set()
    for kw in _KEYWORD_MAP.keys():
        if kw in text:
            tags.add(kw)
    return sorted(tags)


def approve_candidate(example_id: int, *, reviewer: Optional[str] = None) -> bool:
    """Admin: aday ornegini onayla."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE few_shot_examples
                SET verified_by_human = TRUE, updated_at = now()
                WHERE id = %s
                RETURNING id
                """,
                (example_id,),
            )
            approved = cur.fetchone() is not None
        with _DB_CACHE_LOCK:
            _DB_CACHE.clear()
        return approved
    except Exception as exc:
        logger.warning("approve_candidate hatasi: %s", exc)
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def list_candidates(limit: int = 20) -> List[Dict[str, Any]]:
    """Admin: onay bekleyen adaylari listele."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, mode, key, input_text, quality_score, source,
                       usage_count, created_at
                FROM few_shot_examples
                WHERE verified_by_human = FALSE
                ORDER BY quality_score DESC, created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall() or []
            return [
                {
                    "id": r[0],
                    "mode": r[1],
                    "key": r[2],
                    "input_text": (r[3] or "")[:300],
                    "quality_score": float(r[4]) if r[4] else 0.0,
                    "source": r[5],
                    "usage_count": r[6],
                    "created_at": r[7].isoformat() if r[7] else None,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.debug("list_candidates hatasi: %s", exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_example_for_endpoint(
    endpoint_path: str,
    mode: str,
) -> Optional[dict]:
    """
    Belirli bir endpoint path'i için en uygun ornegi bul.

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
    """Her mode için ornek sayisini dondur."""
    return {mode: len(examples) for mode, examples in FEW_SHOT_EXAMPLES.items()}


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _format_example(
    key: str,
    example: dict,
    *,
    is_negative: bool = False,
    bad_reason: Optional[str] = None,
) -> str:
    """Tek bir ornegi okunabilir string formatina donustur.

    is_negative=True ise "YANLIS ORNEK" etiketlenir — LLM bundan kacinir.
    """
    parts: List[str] = []
    label = "## Ornek (YANLIS - bu sekilde URETME): " if is_negative else "## Ornek: "
    parts.append(label + key.replace("_", " ").title())
    parts.append("**Giriş:** %s" % example.get("input", ""))
    if is_negative:
        parts.append(
            "**Dikkat:** Asagidaki cikti KABUL EDILEMEZ. Nedeni: %s"
            % (bad_reason or "kalite duzeyi yetersiz")
        )
        parts.append("**Hatali Cikti:**")
    else:
        parts.append("**Beklenen Cikti:**")

    output = example.get("output", {})
    output_str = json.dumps(output, indent=2, ensure_ascii=False)
    if len(output_str) > 4000:
        output_str = output_str[:4000] + "\n  ... (kisaltildi)"
    parts.append("```json\n%s\n```" % output_str)

    if is_negative:
        parts.append("**Bu cikti HATALI — dogrusunu üret.**")

    return "\n".join(parts)
