# app/core/config.py
import os
from functools import lru_cache

class Settings:
    def __init__(self):
        # MongoDB Atlas connection string, e.g. mongodb+srv://...
        self.mongo_url = os.getenv("MONGO_URL", "mongodb://mongo:27017")

        # DB name inside Mongo
        self.mongo_db = os.getenv("MONGO_DB", "webhooks_db")

        # Redis URL for RQ/queue
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

        # How long the worker "pretends" to call RazorPay, etc.
        # spec says ~30 seconds delay
        self.process_delay_seconds = int(
            os.getenv("PROCESS_DELAY_SECONDS", "30")
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()
