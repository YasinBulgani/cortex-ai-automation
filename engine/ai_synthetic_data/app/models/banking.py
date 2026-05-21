import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    tc_kimlik = Column(String(11), unique=True, index=True)
    segment = Column(String(50)) # e.g. Bireysel, Premium, Kurumsal
    risk_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    accounts = relationship("Account", back_populates="customer", cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"))
    iban = Column(String(34), unique=True, index=True)
    account_type = Column(String(50)) # e.g. Vadesiz TL, Vadeli USD
    balance = Column(Float, default=0.0)
    currency = Column(String(3), default="TRY")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="accounts")
    transactions_out = relationship("Transaction", foreign_keys="[Transaction.from_account_id]", back_populates="from_account")
    transactions_in = relationship("Transaction", foreign_keys="[Transaction.to_account_id]", back_populates="to_account")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    from_account_id = Column(String(36), ForeignKey("accounts.id"), nullable=True) # None for deposits
    to_account_id = Column(String(36), ForeignKey("accounts.id"), nullable=True)   # None for withdrawals
    amount = Column(Float, nullable=False)
    description = Column(String(255))
    trans_date = Column(DateTime, default=datetime.utcnow)
    
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="transactions_out")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="transactions_in")
