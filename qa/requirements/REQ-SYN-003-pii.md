---
id: REQ-SYN-003
title: "PII (kişisel veri) tespiti ve maskeleme"
domain: SYN
source: internal-spec
external: ""
covered_by: [TC-SYN-003]
status: active
---

# REQ-SYN-003 — PII tespiti

## Tanım

Yüklenen veri setinde kişisel veri içeren kolonlar (email, telefon, TC kimlik, IBAN, adres) otomatik tespit edilir ve kullanıcıya gösterilir. Sentetik üretimde bu kolonlar maskelenir veya tamamen synthesize edilir.

## Kabul Kriterleri

- [ ] Email pattern detection (regex + ML hybrid)
- [ ] Telefon numarası (TR formatı + uluslararası)
- [ ] TC Kimlik No (11 hane + check digit)
- [ ] IBAN (TR + EU)
- [ ] Tam ad heuristics (high-uncertainty flag)
- [ ] Adres heuristics (string length + keyword)
- [ ] Custom regex desteği (kullanıcı tanımlı)
- [ ] PII raporu UI'da dataset detail sayfasında gösterilir

## GDPR / KVKK uyumu

- [ ] PII data hiçbir log'a yazılmaz
- [ ] Tespit raporu encrypted-at-rest
- [ ] Audit: PII tespit eyleminin kendisi audit log'a düşer
