---
id: REQ-IMP-002
title: "İçe aktarma dosya format ve içerik validation"
domain: IMP
source: internal-spec
external: ""
covered_by: [TC-IMP-003]
status: active
---

# REQ-IMP-002 — Import validation

## Tanım

İçe aktarma sırasında desteklenmeyen format veya bozuk dosyalar reddedilir; kullanıcıya açıklayıcı hata mesajı verilir.

## Kabul Kriterleri

- [ ] Desteklenen format: .json (Cucumber), .feature, .csv (TC matrix), .xlsx (test plan)
- [ ] Desteklenmeyen format → 415 Unsupported Media Type
- [ ] Bozuk JSON / malformed feature → 422 + parse error detail
- [ ] Max dosya boyutu: 10 MB (config-driven)
- [ ] Boyut aşıldı → 413 Payload Too Large
- [ ] Malicious content scan (basic): script injection, zip bomb

## Bağımlılık

- REQ-IMP-001 (import endpoint var)
