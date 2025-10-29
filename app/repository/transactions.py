# app/repository/transactions.py
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from app.db.mongo import get_collection

def create_or_get_transaction(data: dict):
    """
    Try to insert the transaction with status=RECEIVED.
    If it already exists (DuplicateKeyError), just read it back.

    Returns (doc, created_flag)
    """
    coll = get_collection()
    now = datetime.utcnow()

    base_doc = {
        "transaction_id": data["transaction_id"],
        "source_account": data["source_account"],
        "destination_account": data["destination_account"],
        "amount": data["amount"],
        "currency": data["currency"],
        "status": "RECEIVED",
        "created_at": now,
        "processed_at": None,
    }

    created = False
    try:
        coll.insert_one(base_doc)
        created = True
    except DuplicateKeyError:
        # already exists, so just fetch

        # NOTE: we are *not* overwriting anything,
        # because first write wins for idempotency.
        pass

    doc = coll.find_one(
        {"transaction_id": data["transaction_id"]},
        {"_id": 0}  # don't leak Mongo _id
    )
    return doc, created


def get_by_transaction_id(transaction_id: str):
    coll = get_collection()
    return coll.find_one(
        {"transaction_id": transaction_id},
        {"_id": 0}
    )
