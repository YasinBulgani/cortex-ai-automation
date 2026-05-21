"""Generator tests — Customer, Account, Card."""

from __future__ import annotations

import pytest

from banking_domain import (
    generate_customer, CustomerSegment,
    generate_account, AccountType, Currency,
    generate_card, CardNetwork, CardType,
    validate_tckn, validate_iban_tr, validate_luhn,
    validate_phone_tr,
)


class TestCustomerGenerator:
    def test_basic_generation(self):
        customer = generate_customer()
        assert customer.id
        assert validate_tckn(customer.tckn)
        assert validate_phone_tr(customer.phone)
        assert "@" in customer.email
        assert customer.first_name
        assert customer.last_name
        assert 18 <= customer.age <= 75

    def test_segment_enforcement(self):
        c = generate_customer(segment="affluent")
        assert c.segment == CustomerSegment.AFFLUENT
        # Affluent segmenti için gelir aralığı 60K-200K
        assert 60_000 <= c.income <= 200_000

    def test_age_range(self):
        for _ in range(20):
            c = generate_customer(age_range=(25, 30))
            assert 25 <= c.age <= 30

    def test_private_segment_high_income(self):
        c = generate_customer(segment=CustomerSegment.PRIVATE)
        assert c.income >= 150_000

    def test_to_dict_serializable(self):
        c = generate_customer()
        d = c.to_dict()
        assert d["tckn"] == c.tckn
        assert d["segment"] == c.segment.value
        # Date → ISO string
        assert isinstance(d["birth_date"], str)


class TestAccountGenerator:
    def test_basic_generation(self):
        customer = generate_customer()
        account = generate_account(customer)
        assert account.id
        assert validate_iban_tr(account.iban)
        assert account.customer_id == customer.id
        assert account.account_type == AccountType.CHECKING  # Default
        assert account.currency == Currency.TRY

    def test_different_types(self):
        customer = generate_customer()
        for account_type in AccountType:
            account = generate_account(customer, account_type=account_type)
            assert account.account_type == account_type
            assert validate_iban_tr(account.iban)

    def test_fx_currency(self):
        customer = generate_customer()
        usd = generate_account(customer, account_type=AccountType.FX, currency="USD")
        assert usd.currency == Currency.USD

    def test_specific_bank_code(self):
        customer = generate_customer()
        account = generate_account(customer, bank_code="00046")  # Akbank
        assert account.bank_code == "00046"
        assert account.iban[4:9] == "00046"

    def test_credit_limit_when_requested(self):
        customer = generate_customer(segment="affluent")
        account = generate_account(customer, include_credit_line=True)
        assert account.credit_limit > 0

    def test_interest_rate_reasonable(self):
        customer = generate_customer()
        time_deposit = generate_account(customer, account_type=AccountType.TIME_DEPOSIT)
        # 2026 TR vadeli %40-52
        assert 40 <= time_deposit.interest_rate <= 52

    def test_to_dict(self):
        customer = generate_customer()
        account = generate_account(customer)
        d = account.to_dict()
        assert d["iban"] == account.iban
        assert d["currency"] == "TRY"


class TestCardGenerator:
    def test_basic_generation(self):
        customer = generate_customer()
        card = generate_card(customer)
        assert card.id
        assert validate_luhn(card.card_number)
        assert card.customer_id == customer.id
        assert card.expiry_month in range(1, 13)
        assert card.expiry_year >= 2026

    def test_with_account(self):
        customer = generate_customer()
        account = generate_account(customer)
        card = generate_card(customer, account)
        assert card.account_id == account.id

    def test_network_specific(self):
        customer = generate_customer()
        visa = generate_card(customer, network=CardNetwork.VISA)
        assert visa.card_network == CardNetwork.VISA
        assert validate_luhn(visa.card_number)
        assert len(visa.card_number) == 16

    def test_amex_is_15_digits(self):
        customer = generate_customer()
        amex = generate_card(customer, network=CardNetwork.AMEX)
        assert len(amex.card_number) == 15
        assert validate_luhn(amex.card_number)

    def test_credit_card_has_limit(self):
        customer = generate_customer(segment="mass")
        credit = generate_card(customer, card_type=CardType.CREDIT)
        assert credit.card_type == CardType.CREDIT
        assert credit.credit_limit > 0

    def test_debit_no_credit_limit(self):
        customer = generate_customer()
        debit = generate_card(customer, card_type=CardType.DEBIT)
        assert debit.credit_limit == 0.0
        assert debit.daily_limit > 0

    def test_masked_display(self):
        customer = generate_customer()
        card = generate_card(customer, network=CardNetwork.VISA)
        masked = card.masked_number
        assert len(masked) == len(card.card_number)
        assert "*" in masked
        # İlk 6 + son 4 görünür
        assert masked[:6] == card.card_number[:6]
        assert masked[-4:] == card.card_number[-4:]

    def test_expiry_str_format(self):
        customer = generate_customer()
        card = generate_card(customer)
        assert "/" in card.expiry_str
        parts = card.expiry_str.split("/")
        assert len(parts[0]) == 2  # MM
        assert len(parts[1]) == 2  # YY

    def test_cardholder_name_uppercase(self):
        customer = generate_customer()
        card = generate_card(customer)
        assert card.cardholder_name.isupper() or card.cardholder_name.split()[0].isupper()
        assert customer.first_name.upper() in card.cardholder_name
