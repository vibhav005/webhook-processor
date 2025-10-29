from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.schemas.transaction import TransactionIn, TransactionOut
from app.repository.transactions import (
    create_or_get_transaction,
    get_by_transaction_id,
)
from app.queues.tasks import enqueue_transaction

router = APIRouter()

@router.get("/")
def health_check():
    return {
        "status": "HEALTHY",
        "current_time": datetime.utcnow().isoformat() + "Z",
    }

@router.post(
    "/v1/webhooks/transactions",
    status_code=202,
)
def receive_webhook(payload: TransactionIn):
    # Persist (or get existing)
    doc, _created = create_or_get_transaction(
        payload.model_dump(by_alias=True)
    )

    # Enqueue background processing (idempotent)
    enqueue_transaction(doc["transaction_id"])

    # Explicit minimal ack, still 202
    return {
        "accepted": True,
        "transaction_id": doc["transaction_id"],
        "status": doc["status"],
    }

@router.get(
    "/v1/transactions/{transaction_id}",
    response_model=TransactionOut,
    response_model_exclude_none=True,
)
def transaction_status(transaction_id: str):
    doc = get_by_transaction_id(transaction_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return doc
