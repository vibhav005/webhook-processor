# app/workers/processor.py
import time
from datetime import datetime
from app.db.mongo import get_collection
from app.core.config import get_settings

def process_transaction(transaction_id: str):
    """
    Long-running job:
    - atomically claim the transaction (RECEIVED -> PROCESSING)
    - simulate 30s external call
    - mark PROCESSED with processed_at timestamp
    """

    coll = get_collection()

    # 1. Try to atomically move RECEIVED -> PROCESSING.
    #    Only the first worker will succeed (modified_count == 1).
    claim = coll.update_one(
        {
            "transaction_id": transaction_id,
            "status": "RECEIVED",
        },
        {
            "$set": {
                "status": "PROCESSING",
                "processed_at": None,
            }
        },
    )

    if claim.modified_count == 0:
        # Somebody else is already processing or it's already processed.
        return

    # 2. Simulate heavy external work (e.g. RazorPay confirm, ledger writes ...)
    settings = get_settings()
    time.sleep(settings.process_delay_seconds)

    # 3. Mark as PROCESSED
    coll.update_one(
        {"transaction_id": transaction_id},
        {
            "$set": {
                "status": "PROCESSED",
                "processed_at": datetime.utcnow(),
            }
        },
    )
