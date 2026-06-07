from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class SMSTransaction(Base):
    __tablename__ = "sms_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    sender = Column(String)
    amount = Column(Float)
    timestamp = Column(DateTime)
    reconciled = Column(Boolean, default=False)
    
    # One-to-one relationship back reference
    receipt = relationship("ReceiptTransaction", back_populates="sms", uselist=False)


class ReceiptTransaction(Base):
    __tablename__ = "receipt_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    total_amount = Column(Float)
    timestamp = Column(DateTime)
    reconciled = Column(Boolean, default=False)
    
    # We keep a single foreign key here to establish the true link
    sms_id = Column(Integer, ForeignKey("sms_transactions.id"), nullable=True)
    
    # Establish the relationship mapping cleanly
    sms = relationship("SMSTransaction", back_populates="receipt")
