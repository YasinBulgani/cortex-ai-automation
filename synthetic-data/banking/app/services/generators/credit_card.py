import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from faker import Faker

class CreditCardGenerator:
    def __init__(self, locale: str = "tr_TR"):
        self.fake = Faker(locale)

    def generate(self, customer: Dict[str, Any], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        eligible_cards = constraints.get("eligible_cards", [])
        salary = customer.get("annual_salary_try", 30000)
        
        cards = []
        for card_info in eligible_cards:
            ctype = card_info["card_type"]
            multiplier = card_info["limit_multiplier"]
            
            # Base limit based on salary and card type
            limit = round(salary * multiplier * random.uniform(0.8, 1.2), -2)
            
            expiry = (datetime.now() + timedelta(days=random.randint(365, 365*5))).strftime("%m/%y")
            
            card = {
                "id": f"CARD-{uuid.uuid4().hex[:8].upper()}",
                "customer_id": customer["customer_id"],
                "card_number": self.fake.credit_card_number(card_type="mastercard"),
                "card_type": ctype,
                "expiry_date": expiry,
                "cvv": self.fake.credit_card_security_code(),
                "limit": limit,
                "available_limit": limit,
                "status": "ACTIVE"
            }
            cards.append(card)
            
        return cards
