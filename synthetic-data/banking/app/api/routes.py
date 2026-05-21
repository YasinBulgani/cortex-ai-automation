from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.generators.customer import CustomerGenerator
from app.services.generators.account import AccountGenerator
from app.services.generators.transaction import TransactionGenerator
from app.services.generators.credit_card import CreditCardGenerator
from app.services.rule_engine import BankingRuleEngine
from app.models.db_session import get_db
from app.models.database import Customer, Account as DBAccount, Transaction as DBTransaction, CreditCard as DBCard
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

router = APIRouter()

customer_gen = CustomerGenerator(locale="tr_TR")
account_gen = AccountGenerator(locale="tr_TR")
transaction_gen = TransactionGenerator()
card_gen = CreditCardGenerator(locale="tr_TR")
rule_engine = BankingRuleEngine(rules_path="rules/banking_rules.yaml")


# --- Request Models ---

class GenerateRequest(BaseModel):
    gender: Optional[str] = Field(None, description="M or F", examples=["F"])
    birth_year: Optional[int] = Field(None, description="Year of birth", examples=[1995])
    employment_status: Optional[str] = Field(None, description="EMPLOYED, UNEMPLOYED, STUDENT", examples=["EMPLOYED"])
    account_count: Optional[int] = Field(1, description="Number of accounts", examples=[2])
    include_transactions: Optional[bool] = Field(True, description="Generate transactions?")
    transactions_per_account: Optional[int] = Field(15, description="Number of transactions per account")
    save_to_db: Optional[bool] = Field(False, description="Save to PostgreSQL?")

class BatchGenerateRequest(BaseModel):
    count: int = Field(..., description="Number of customers to generate", examples=[5])
    gender: Optional[str] = None
    birth_year_min: Optional[int] = Field(None, examples=[1980])
    birth_year_max: Optional[int] = Field(None, examples=[2000])
    employment_status: Optional[str] = None
    account_count: Optional[int] = Field(1)
    include_transactions: Optional[bool] = Field(True)
    save_to_db: Optional[bool] = Field(False)


# --- Endpoints ---

@router.post("/generate", summary="Generate a single synthetic customer with accounts & transactions")
async def generate_single(request: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """
    Tek bir sentetik müşteri, bağlı hesapları, kredi kartları ve işlem geçmişini üretir.
    """
    try:
        # Build constraints dict
        constraints = {
            "gender": request.gender or "F",
            "birth_year": request.birth_year or 1990,
            "employment_status": request.employment_status or "EMPLOYED",
            "account_count": request.account_count or 1,
        }

        # Apply rule engine
        enriched = rule_engine.apply(constraints)

        # Generate customer
        customer_data = customer_gen.generate(enriched)

        # Generate accounts
        accounts_data = account_gen.generate(customer_data["customer_id"], enriched)

        # Generate cards
        cards_data = card_gen.generate(customer_data, enriched)

        # Generate transactions
        transactions_data = []
        if request.include_transactions:
            txn_constraints = {**enriched, "annual_salary_try": customer_data.get("annual_salary_try")}
            transactions_data = transaction_gen.generate(
                accounts_data, txn_constraints,
                txn_count_per_account=request.transactions_per_account or 15
            )

        # --- DB Persistence ---
        if request.save_to_db:
            # 1. Save Customer
            db_customer = Customer(**customer_data)
            db.add(db_customer)
            
            # 2. Save Accounts
            for acc in accounts_data:
                db_acc = DBAccount(**acc)
                db.add(db_acc)
            
            # 3. Save Cards
            for card in cards_data:
                db_card = DBCard(**card)
                db.add(db_card)
                
            # 4. Save Transactions
            for txn in transactions_data:
                # Remove 'type' if your DB model doesn't have it or maps it differently
                db_txn = DBTransaction(**txn)
                db.add(db_txn)
            
            await db.commit()

        return {
            "status": "success",
            "data": {
                "customer": customer_data,
                "accounts": accounts_data,
                "cards": cards_data,
                "transactions": transactions_data
            },
            "meta": {
                "constraints_applied": enriched,
                "saved_to_db": request.save_to_db,
                "total_accounts": len(accounts_data),
                "total_cards": len(cards_data),
                "total_transactions": len(transactions_data)
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/batch", summary="Generate multiple synthetic customers in batch")
async def generate_batch(request: BatchGenerateRequest, db: AsyncSession = Depends(get_db)):
    """
    Toplu sentetik müşteri, hesap, kart ve işlem verisi üretir.
    """
    import random

    results = []
    for _ in range(request.count):
        birth_year = request.birth_year_min or 1980
        if request.birth_year_max:
            birth_year = random.randint(request.birth_year_min or 1960, request.birth_year_max)

        constraints = {
            "gender": request.gender or random.choice(["M", "F"]),
            "birth_year": birth_year,
            "employment_status": request.employment_status or random.choice(["EMPLOYED", "UNEMPLOYED", "STUDENT"]),
            "account_count": request.account_count or 1,
        }

        enriched = rule_engine.apply(constraints)
        
        # Generator flow
        customer_data = customer_gen.generate(enriched)
        accounts_data = account_gen.generate(customer_data["customer_id"], enriched)
        cards_data = card_gen.generate(customer_data, enriched)

        transactions_data = []
        if request.include_transactions:
            txn_constraints = {**enriched, "annual_salary_try": customer_data.get("annual_salary_try")}
            transactions_data = transaction_gen.generate(accounts_data, txn_constraints, txn_count_per_account=5)

        # --- DB Persistence ---
        if request.save_to_db:
            db_customer = Customer(**customer_data)
            db.add(db_customer)
            
            for acc in accounts_data:
                db_acc = DBAccount(**acc)
                db.add(db_acc)
            
            for card in cards_data:
                db_card = DBCard(**card)
                db.add(db_card)
                
            for txn in transactions_data:
                db_txn = DBTransaction(**txn)
                db.add(db_txn)

        results.append({
            "customer": customer_data,
            "accounts": accounts_data,
            "cards": cards_data,
            "transactions": transactions_data
        })

    if request.save_to_db:
        await db.commit()

    return {
        "status": "success",
        "count": len(results),
        "data": results,
        "meta": {
            "saved_to_db": request.save_to_db
        }
    }


@router.get("/health", summary="Health check")
async def health_check():
    return {"status": "healthy", "service": "banking-synthetic-data-generator"}
