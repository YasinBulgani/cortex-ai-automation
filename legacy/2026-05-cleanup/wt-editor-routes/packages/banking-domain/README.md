# @twai/banking-domain

Türk bankacılık sektörü için validator, generator, fraud pattern ve compliance kütüphanesi.

## Özellikler

### Validators (ISO & resmi algoritmalar)
- **IBAN (TR)** — ISO 13616 Mod-97
- **TCKN** — MERNIS 11 haneli algoritma
- **Luhn** — Kredi/banka kartı (ISO/IEC 7812)
- **BIC** — SWIFT ISO 9362 (8 veya 11 karakter)
- **VKN** — Türkiye Vergi Kimlik No (10 dijit)
- **Telefon** — TR mobil operatör prefix kontrolü + normalize

### Generators (Faker + banka kuralları)
- **Customer** — TR lokalli müşteri üretir
- **Account** — Geçerli TR IBAN + segment
- **Card** — BIN range + Luhn check digit
- *(gelecek)* Loan, Deposit, Investment

### Reference Tables
- **TCMB Banks** — 60+ banka kodu + BIC + tip
- **MCC Codes** — 50+ merchant category code
- *(gelecek)* SWIFT BIC, Currencies, Cities

### Calendar (TR)
- **Resmi Tatiller 2026-27** — Yılbaşı, 23 Nisan, 1 Mayıs, 19 Mayıs, 30 Ağustos, 29 Ekim
- **Dini Bayramlar 2026** — Ramazan, Kurban
- `is_business_day()`, `next_business_day()`, `business_days_between()`

### Compliance
- **KVKK** — Veri sınıflandırma (personal / sensitive / financial / biometric / location)
- **KVKK** — Redact helpers (TCKN / IBAN / kart no / telefon / e-posta)
- **AML** — MASAK 2006/55 raporlama eşikleri
- *(gelecek)* BDDK sermaye yeterliliği kontrolleri

## Kullanım

```python
from banking_domain import (
    validate_iban_tr, generate_iban_tr,
    validate_tckn, generate_tckn,
    validate_luhn, generate_card_number,
    generate_customer, generate_account,
)

# Validation
assert validate_iban_tr("TR330006100519786457841326")
assert validate_tckn("10000000146")

# Generation
tckn = generate_tckn()                # Geçerli TCKN
iban = generate_iban_tr()             # Geçerli TR IBAN
card = generate_card_number("454360") # VISA BIN + Luhn

# Customer + Account
customer = generate_customer(segment="affluent")
account = generate_account(customer, currency="TRY")
```

## Test

```bash
cd packages/banking-domain
pip install -e ".[dev]"
pytest
```

**Golden test vectors**: TCMB, MERNIS, ISO resmi dokümanlarından alınmış.

## Plan Referansı

[`docs/plan/12_BANKING_DOMAIN.md`](../../docs/plan/12_BANKING_DOMAIN.md)
