"""
TestwrightAI Bankacılık Test Verisi Üretim Paketi
BDDK/KVKK uyumlu, AI-free, kural tabanlı sentetik veri üretimi.
"""
from banking.generators.identity    import generate_tc_kimlik, validate_tc_kimlik, generate_vkn, validate_vkn
from banking.generators.account     import generate_tr_iban, validate_tr_iban, generate_swift, get_bank_list
from banking.generators.card        import generate_card_number, luhn_check, generate_cvv, generate_card_expiry
from banking.generators.transaction import generate_eft_reference, generate_doviz_kuru, generate_transaction_date
from banking.generators.credit      import generate_faiz_orani, generate_kredi_limiti, generate_risk_skoru, classify_segment
from banking.factories.banking_factories import generate_banking_data, generate_relational_dataset, FACTORY_MAP

__all__ = [
    'generate_tc_kimlik', 'validate_tc_kimlik', 'generate_vkn', 'validate_vkn',
    'generate_tr_iban', 'validate_tr_iban', 'generate_swift', 'get_bank_list',
    'generate_card_number', 'luhn_check', 'generate_cvv', 'generate_card_expiry',
    'generate_eft_reference', 'generate_doviz_kuru', 'generate_transaction_date',
    'generate_faiz_orani', 'generate_kredi_limiti', 'generate_risk_skoru', 'classify_segment',
    'generate_banking_data', 'generate_relational_dataset', 'FACTORY_MAP',
]

VERSION = '1.0.0'
BDDK_COMPLIANT = True
