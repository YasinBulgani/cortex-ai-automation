from faker import Faker
from datetime import date
import random
import uuid
from typing import Dict, Any

class CustomerGenerator:
    def __init__(self, locale: str = "tr_TR"):
        self.fake = Faker(locale)

    def generate(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        gender = constraints.get("gender", random.choice(["M", "F"]))
        birth_year = constraints.get("birth_year", random.randint(1950, 2005))
        
        current_year = date.today().year
        age = current_year - birth_year

        if gender == "F":
            first_name = self.fake.first_name_female()
        else:
            first_name = self.fake.first_name_male()
            
        last_name = self.fake.last_name()
        email_prefix = f"{first_name.lower()}.{last_name.lower()}{birth_year%100}".replace('ı','i').replace('ş','s').replace('ç','c').replace('ö','o').replace('ü','u').replace('ğ','g')

        dob = self.fake.date_of_birth(
            minimum_age=age,
            maximum_age=age
        )

        salary = None
        employment_status = constraints.get("employment_status", "EMPLOYED")
        if employment_status == "EMPLOYED":
            salary_range = constraints.get("salary_range", {"min": 35000, "max": 150000})
            salary = round(random.uniform(salary_range["min"], salary_range["max"]), 2)

        customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"

        # Credit Score Generation
        credit_score_range = constraints.get("credit_score_range", {"min": 500, "max": 1900})
        credit_score = random.randint(credit_score_range["min"], credit_score_range["max"])

        return {
            "customer_id": customer_id,
            "first_name": first_name,
            "last_name": last_name,
            "gender": gender,
            "date_of_birth": dob.isoformat(),
            "age": age,
            "email": f"{email_prefix}@{self.fake.free_email_domain()}",
            "phone": self.fake.phone_number(),
            "address": {
                "city": self.fake.city(),
                "district": self.fake.city_suffix(),
                "street": self.fake.street_name()
            },
            "employment_status": employment_status,
            "annual_salary_try": salary,
            "credit_score": credit_score,
            "risk_score": random.choice(["LOW", "MEDIUM", "HIGH"]),
            "created_at": self.fake.date_time_between(start_date="-3y").isoformat()
        }
