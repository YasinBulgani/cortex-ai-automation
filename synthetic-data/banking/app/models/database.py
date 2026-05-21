from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    gender = Column(String)
    date_of_birth = Column(String)
    age = Column(Integer)
    email = Column(String)
    phone = Column(String)
    address = Column(JSON)
    employment_status = Column(String)
    annual_salary_try = Column(Float)
    credit_score = Column(Integer)
    risk_score = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    accounts = relationship("Account", back_populates="customer")
    cards = relationship("CreditCard", back_populates="customer")

class Account(Base):
    __tablename__ = 'accounts'
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey('customers.id'))
    account_type = Column(String)
    iban = Column(String)
    currency = Column(String)
    balance = Column(Float)
    status = Column(String)
    interest_rate = Column(Float)

    customer = relationship("Customer", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey('accounts.id'))
    amount = Column(Float)
    balance_after = Column(Float)
    merchant = Column(String)
    category = Column(String)
    date = Column(String)
    type = Column(String)

    account = relationship("Account", back_populates="transactions")

class CreditCard(Base):
    __tablename__ = 'credit_cards'
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey('customers.id'))
    card_number = Column(String)
    card_type = Column(String)  # ELITE, GOLD, CLASSIC
    expiry_date = Column(String)
    cvv = Column(String)
    limit = Column(Float)
    available_limit = Column(Float)
    status = Column(String)

    customer = relationship("Customer", back_populates="cards")
