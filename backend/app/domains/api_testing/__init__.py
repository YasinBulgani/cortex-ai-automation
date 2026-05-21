"""
AI-Powered API Testing Intelligence Module
==========================================

Bankacilik API'leri için uctan uca AI-destekli servis test otomasyonu.

Alt moduller:
  - spec_parser      : OpenAPI/Swagger spec parse + endpoint cikarimi
  - request_executor : Async HTTP istemci + timing breakdown
  - assertion_engine : JSON Path + Schema + AI-powered assertions
  - environment      : Environment degisken yonetimi ({{variable}} syntax)
  - chain_engine     : Request chaining + veri bagimliligi cozumleme
  - security_scanner : OWASP API Top 10 + BDDK/KVKK/PCI-DSS
  - models           : SQLAlchemy modelleri
  - schemas          : Pydantic schemalar
  - router           : FastAPI endpoint'leri
  - service          : Is mantigi katmani
  - coverage_analyzer: Test coverage gap analysis + recommendations
"""
