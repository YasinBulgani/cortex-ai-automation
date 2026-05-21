import random
import uuid
from typing import Dict, Any, List
from faker import Faker

class AccountGenerator:
    def __init__(self, locale: str = "tr_TR"):
        self.fake = Faker(locale)

    def generate(self, customer_id: str, constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        account_count = constraints.get("account_count", 1)
        account_mix = constraints.get("account_mix", ["CHECKING"])
        
        accounts = []
        for i in range(account_count):
            acc_type = account_mix[i % len(account_mix)] if account_mix else "CHECKING"
            
            balance = round(random.uniform(100.0, 50000.0), 2)
            if acc_type == "SAVINGS":
                balance = round(random.uniform(5000.0, 250000.0), 2)
                
            interest_rate = None
            if acc_type == "SAVINGS":
                interest_rate = round(random.uniform(0.15, 0.45), 3)

            iban = self.fake.iban()

            account = {
                "account_id": f"ACC-{uuid.uuid4().hex[:8].upper()}",
                "customer_id": customer_id,
                "account_type": acc_type,
                "iban": iban,
                "currency": "TRY",
                "balance": balance,
                "status": "ACTIVE",
                "interest_rate": interest_rate
            }
            accounts.append(account)
            
        return accounts
