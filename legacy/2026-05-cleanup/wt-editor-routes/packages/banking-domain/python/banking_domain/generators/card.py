"""
Card generator — Luhn-valid kart no + son kullanma + CVV.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from ..validators.luhn import generate_card_number, BIN_TEST_CARDS


class CardNetwork(str, Enum):
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    TROY = "TROY"
    AMEX = "AMEX"


class CardType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    PREPAID = "prepaid"
    VIRTUAL = "virtual"
    BUSINESS = "business"


# TR bankalarının BIN aralıkları (basitleştirilmiş örnek)
_TR_BANK_BINS: dict[str, dict[CardNetwork, str]] = {
    "Akbank": {
        CardNetwork.VISA: "455036",
        CardNetwork.MASTERCARD: "540601",
        CardNetwork.TROY: "979200",
    },
    "Garanti": {
        CardNetwork.VISA: "454360",
        CardNetwork.MASTERCARD: "540042",
    },
    "İş Bankası": {
        CardNetwork.VISA: "454670",
        CardNetwork.MASTERCARD: "515616",
        CardNetwork.TROY: "979201",
    },
    "Yapı Kredi": {
        CardNetwork.VISA: "432077",
        CardNetwork.MASTERCARD: "540668",
    },
    "Ziraat": {
        CardNetwork.MASTERCARD: "521830",
        CardNetwork.TROY: "979202",
    },
}


@dataclass
class Card:
    id: str
    customer_id: str
    account_id: str | None
    card_number: str
    card_network: CardNetwork
    card_type: CardType
    expiry_month: int   # 1-12
    expiry_year: int    # 2026-2030
    cvv: str            # 3 dijit (AMEX için 4)
    cardholder_name: str
    is_active: bool = True
    is_contactless: bool = True
    daily_limit: float = 0.0
    credit_limit: float = 0.0     # Kredi kartı için
    issued_at: date = field(default_factory=date.today)

    @property
    def masked_number(self) -> str:
        """PCI-DSS uyumlu maskeli görünüm."""
        from ..validators.luhn import mask_card_number
        return mask_card_number(self.card_number)

    @property
    def expiry_str(self) -> str:
        return f"{self.expiry_month:02d}/{self.expiry_year % 100:02d}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "account_id": self.account_id,
            "card_number_masked": self.masked_number,
            "card_network": self.card_network.value,
            "card_type": self.card_type.value,
            "expiry": self.expiry_str,
            "cardholder_name": self.cardholder_name,
            "is_active": self.is_active,
            "is_contactless": self.is_contactless,
            "daily_limit": self.daily_limit,
            "credit_limit": self.credit_limit,
            "issued_at": self.issued_at.isoformat(),
        }


def _cvv_for_network(network: CardNetwork) -> str:
    """AMEX 4 dijit, diğerleri 3 dijit."""
    length = 4 if network == CardNetwork.AMEX else 3
    return "".join(random.choices("0123456789", k=length))


def _bin_for_network(network: CardNetwork, bank: str | None = None) -> str:
    """Banka/network kombinasyonu için BIN."""
    if bank and bank in _TR_BANK_BINS:
        if network in _TR_BANK_BINS[bank]:
            return _TR_BANK_BINS[bank][network]
    # Fallback — generic test BIN
    return BIN_TEST_CARDS.get(network.value, "454360")


def generate_card(
    customer,
    account = None,
    *,
    network: CardNetwork | str | None = None,
    card_type: CardType | str = CardType.DEBIT,
    bank: str | None = None,
    expiry_years_ahead: int = 5,
) -> Card:
    """
    Luhn-valid kart üret.

    Args:
        customer: Customer instance
        account: İlişkili hesap (opsiyonel)
        network: VISA/MASTERCARD/TROY/AMEX (default: rastgele)
        card_type: DEBIT/CREDIT/PREPAID/VIRTUAL
        bank: Belirli banka BIN'i
        expiry_years_ahead: Son kullanma kaç yıl sonra
    """
    if network is None:
        network_enum = random.choice([CardNetwork.VISA, CardNetwork.MASTERCARD, CardNetwork.TROY])
    elif isinstance(network, str):
        network_enum = CardNetwork(network.upper())
    else:
        network_enum = network

    if isinstance(card_type, str):
        card_type_enum = CardType(card_type.lower())
    else:
        card_type_enum = card_type

    bin_prefix = _bin_for_network(network_enum, bank)
    length = 15 if network_enum == CardNetwork.AMEX else 16
    number = generate_card_number(bin_prefix, length=length)

    today = date.today()
    expiry_date = today + timedelta(days=random.randint(180, 365 * expiry_years_ahead))
    expiry_month = expiry_date.month
    expiry_year = expiry_date.year

    income = getattr(customer, "income", 30_000)

    if card_type_enum == CardType.CREDIT:
        credit_limit = round(income * random.uniform(2.0, 5.0), 2)
        daily_limit = round(credit_limit * random.uniform(0.05, 0.2), 2)
    elif card_type_enum == CardType.BUSINESS:
        credit_limit = round(income * random.uniform(5.0, 20.0), 2)
        daily_limit = round(credit_limit * random.uniform(0.1, 0.3), 2)
    else:
        credit_limit = 0.0
        daily_limit = round(random.uniform(500, min(50_000, income)), 2)

    name = f"{getattr(customer, 'first_name', 'AD').upper()} {getattr(customer, 'last_name', 'SOYAD').upper()}"

    return Card(
        id=str(uuid4()),
        customer_id=getattr(customer, "id", "unknown"),
        account_id=getattr(account, "id", None) if account else None,
        card_number=number,
        card_network=network_enum,
        card_type=card_type_enum,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        cvv=_cvv_for_network(network_enum),
        cardholder_name=name,
        is_contactless=random.random() > 0.05,  # %95 temassız
        daily_limit=daily_limit,
        credit_limit=credit_limit,
    )
