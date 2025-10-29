# app/schemas/transaction.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TransactionIn(BaseModel):
    transaction_id: str = Field(..., alias="transaction_id")
    source_account: str
    destination_account: str
    amount: float
    currency: str

class TransactionOut(BaseModel):
    transaction_id: str
    source_account: str
    destination_account: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None
