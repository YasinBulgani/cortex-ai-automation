"""Otomasyon Süiti — yüksek seviye orkestrasyon façade'ı.

`backend/app/domains/automation/` mevcut proxy rolünü sürdürür (DEĞİŞMEZ);
bu domain onun üzerine, mevcut engine + DSL servisinin birleşik bir HTTP
sözleşmesiyle kullanılmasını sağlar:

  * POST /api/v1/automation-suite/generate  — manuel test ID → pipeline
  * POST /api/v1/automation-suite/run       — feature_path'i koştur
  * GET  /api/v1/automation-suite/runs/{id} — koşum durumu
  * POST /api/v1/automation-suite/catalog/suggest — NL → DSL önerisi

Bu katmanın amacı: frontend ve CI tek tip bir REST yüzeyi kullansın,
engine endpoint'leri değişse bile tüketiciler kırılmasın.

`__init__.py` hafif tutulmuştur; router ihtiyaç duyulduğunda
`from app.domains.automation_suite.router import router` ile alınır.
"""
