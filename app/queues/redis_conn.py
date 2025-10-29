# app/queues/redis_conn.py
import redis
from rq import Queue
from app.core.config import get_settings

_redis_conn = None
_queue = None

def get_queue() -> Queue:
    global _redis_conn, _queue
    if _queue is None:
        settings = get_settings()
        _redis_conn = redis.from_url(settings.redis_url)
        # We'll use a single queue named "transactions"
        _queue = Queue("transactions", connection=_redis_conn)
    return _queue
