import os
from functools import lru_cache

class Settings:
    def __init__(self):
        self.mongo_url = os.getenv("MONGO_URL", "mongodb://mongo:27017")
        self.mongo_db = os.getenv("MONGO_DB", "webhooks_db")
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.process_delay_seconds = int(
            os.getenv("PROCESS_DELAY_SECONDS", "30")
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()
