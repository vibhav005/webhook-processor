# app/db/mongo.py
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from app.core.config import get_settings

_client = None
_collection = None

def get_collection() -> Collection:
    """
    Returns the Mongo 'transactions' collection.
    Ensures unique index on transaction_id (idempotency at DB layer).
    """
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        _client = MongoClient(settings.mongo_url)
        db = _client[settings.mongo_db]

        _collection = db["transactions"]

        # Unique index => duplicate transaction_id won't insert twice
        _collection.create_index(
            [("transaction_id", ASCENDING)], unique=True
        )
    return _collection
