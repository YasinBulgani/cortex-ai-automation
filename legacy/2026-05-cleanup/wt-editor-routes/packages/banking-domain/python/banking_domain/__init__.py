"""
banking-domain — TR bankacılık validator, generator, referans tablo,
tatil takvimi ve compliance (KVKK/AML/BDDK) kütüphanesi.

Plan: docs/plan/12_BANKING_DOMAIN.md
"""

__version__ = "0.1.0"

# Validators
from .validators import (
    validate_iban_tr, generate_iban_tr, normalize_iban, format_iban,
    get_bank_code_from_iban, validate_iban_mod97,
    validate_tckn, generate_tckn, mask_tckn,
    validate_luhn, luhn_check_digit, generate_card_number, generate_test_card,
    mask_card_number, BIN_TEST_CARDS,
    validate_bic, bic_country_code, bic_bank_code,
    validate_vkn, generate_vkn,
    validate_phone_tr, generate_phone_tr, normalize_phone_tr, format_phone_tr,
    get_operator, mask_phone_tr,
)

# Reference
from .reference import (
    tcmb_banks, mcc_codes, bank_info, mcc_info,
    list_banks_by_type, list_high_risk_mcc,
)

# Calendar
from .calendar import (
    RESMI_TATILLER, DINI_BAYRAMLAR,
    is_holiday, is_weekend, is_business_day,
    next_business_day, previous_business_day,
    business_days_between, holidays_in_year, add_business_days,
    SalaryPattern, salary_day_for_month, is_salary_day,
)

# Generators
from .generators import (
    Customer, generate_customer, CustomerSegment,
    Account, generate_account, AccountType, Currency,
    Card, generate_card, CardNetwork, CardType,
)

# Compliance
from .compliance import (
    DataClass, classify_field, redact_value, redact_dict,
    FIELD_CLASSIFICATION,
    SUSPICIOUS_TRANSACTION_THRESHOLD_TRY,
    CUMULATIVE_DAILY_THRESHOLD_TRY,
    INTERNATIONAL_WIRE_THRESHOLD_USD,
    CASH_TRANSACTION_THRESHOLD_TRY,
    is_reportable_transaction,
    AmlFlag, check_aml_flags,
    DTI_LIMITS, calculate_credit_limit,
    check_capital_adequacy_ratio, CAR_MINIMUM,
)

__all__ = [
    # Package metadata
    "__version__",

    # Validators
    "validate_iban_tr", "generate_iban_tr", "normalize_iban", "format_iban",
    "get_bank_code_from_iban", "validate_iban_mod97",
    "validate_tckn", "generate_tckn", "mask_tckn",
    "validate_luhn", "luhn_check_digit", "generate_card_number",
    "generate_test_card", "mask_card_number", "BIN_TEST_CARDS",
    "validate_bic", "bic_country_code", "bic_bank_code",
    "validate_vkn", "generate_vkn",
    "validate_phone_tr", "generate_phone_tr", "normalize_phone_tr",
    "format_phone_tr", "get_operator", "mask_phone_tr",

    # Reference
    "tcmb_banks", "mcc_codes", "bank_info", "mcc_info",
    "list_banks_by_type", "list_high_risk_mcc",

    # Calendar
    "RESMI_TATILLER", "DINI_BAYRAMLAR",
    "is_holiday", "is_weekend", "is_business_day",
    "next_business_day", "previous_business_day",
    "business_days_between", "holidays_in_year", "add_business_days",
    "SalaryPattern", "salary_day_for_month", "is_salary_day",

    # Generators
    "Customer", "generate_customer", "CustomerSegment",
    "Account", "generate_account", "AccountType", "Currency",
    "Card", "generate_card", "CardNetwork", "CardType",

    # Compliance
    "DataClass", "classify_field", "redact_value", "redact_dict",
    "FIELD_CLASSIFICATION",
    "SUSPICIOUS_TRANSACTION_THRESHOLD_TRY",
    "CUMULATIVE_DAILY_THRESHOLD_TRY",
    "INTERNATIONAL_WIRE_THRESHOLD_USD",
    "CASH_TRANSACTION_THRESHOLD_TRY",
    "is_reportable_transaction",
    "AmlFlag", "check_aml_flags",
    "DTI_LIMITS", "calculate_credit_limit",
    "check_capital_adequacy_ratio", "CAR_MINIMUM",
]
