from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class ConstraintRequest(BaseModel):
    gender: Optional[str] = Field(None, description="M or F")
    birth_year: Optional[int] = Field(None, description="Year of birth")
    employment_status: Optional[str] = Field(None, description="EMPLOYED, UNEMPLOYED, STUDENT")
    account_count: Optional[int] = Field(1, description="Number of accounts to generate")

class GenerateRequest(BaseModel):
    intent: str
    constraints: ConstraintRequest

class CustomerSchema(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    gender: str
    date_of_birth: str
    age: int
    email: str
    phone: str
    address: Dict[str, str]
    employment_status: str
    annual_salary_try: Optional[float]
    risk_score: str

class AccountSchema(BaseModel):
    account_id: str
    customer_id: str
    account_type: str
    iban: str
    currency: str
    balance: float
    status: str
    interest_rate: Optional[float] = None

class TransactionSchema(BaseModel):
    txn_id: str
    account_id: str
    amount: float
    balance_after: float
    merchant: str
    category: str
    date: str

class SyntheticDataResponse(BaseModel):
    customer: CustomerSchema
    accounts: List[AccountSchema]
    transactions: List[TransactionSchema]
