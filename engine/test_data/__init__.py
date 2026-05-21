"""
engine/test_data — TestwrightAI test veri modülü

Tüm fixture fonksiyonlarını doğrudan import etmek için:
    from engine.test_data import load_test_data, random_tckn, get_admin_user
"""

from .fixtures import (
    get_admin_user,
    get_api_payload,
    get_environment,
    get_locators,
    get_scenarios_by_project,
    get_test_projects,
    get_test_scenarios,
    get_user_by_role,
    load_test_data,
    random_account_number,
    random_currency_amount,
    random_customer_id,
    random_email,
    random_iban,
    random_phone,
    random_tckn,
    random_turkish_first_name,
    random_turkish_last_name,
    random_turkish_name,
    validate_iban,
    validate_tckn,
)

__all__ = [
    "load_test_data",
    "get_admin_user",
    "get_user_by_role",
    "get_test_projects",
    "get_test_scenarios",
    "get_scenarios_by_project",
    "get_api_payload",
    "get_environment",
    "get_locators",
    "random_turkish_name",
    "random_turkish_first_name",
    "random_turkish_last_name",
    "random_tckn",
    "validate_tckn",
    "random_iban",
    "validate_iban",
    "random_phone",
    "random_email",
    "random_currency_amount",
    "random_account_number",
    "random_customer_id",
]
