# app/queues/tasks.py
from rq import Retry
from rq.exceptions import InvalidJobOperation
from app.queues.redis_conn import get_queue

def enqueue_transaction(transaction_id: str):
    """
    Push a background job for this transaction.
    job_id is deterministic = transaction_id,
    so duplicate webhooks won't create duplicate jobs.
    """
    q = get_queue()
    try:
        q.enqueue(
            "app.workers.processor.process_transaction",
            transaction_id,
            job_id=transaction_id,  # idempotency at queue level
            retry=Retry(max=3, interval=[10, 30, 60]),
        )
    except (ValueError, InvalidJobOperation):
        # Job already enqueued or finished with same job_id.
        # That's fine; idempotency means we do nothing here.
        pass
