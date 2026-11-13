import re

from backend.shared.contracts import utcnow
from .memory_manager import database_operation, object_id, observation_from_document


class MemoryRetriever:
    """Replace search with semantic retrieval later; return the same bounded models."""
    def __init__(self, db, manager):
        self.db, self.manager = db, manager

    @staticmethod
    def live_filter():
        # MongoDB TTL cleanup is delayed; expired records must never reach prompts.
        return {"$or": [{"expires_at": None}, {"expires_at": {"$gt": utcnow()}}]}

    @database_operation
    async def get(self, memory_id: str):
        doc = await self.db.screen_observations.find_one({"_id": object_id(memory_id), **self.live_filter()})
        return observation_from_document(doc) if doc else None

    @database_operation
    async def recent(self, limit: int = 20):
        cursor = self.db.screen_observations.find(self.live_filter()).sort("timestamp", -1).limit(min(max(limit, 1), 50))
        return [observation_from_document(doc) async for doc in cursor]

    @database_operation
    async def search(self, query: str, limit: int = 10):
        await self.manager.ensure_indexes()
        # Remove MongoDB query syntax; this endpoint is a plain-word search.
        words = re.findall(r"[\w]+", query, flags=re.UNICODE)[:40]
        if not words:
            return []
        cursor = self.db.screen_observations.find(
            {"$text": {"$search": " ".join(words)}, **self.live_filter()},
            {"score": {"$meta": "textScore"}},
        ).sort([("score", {"$meta": "textScore"}), ("timestamp", -1)]).limit(min(max(limit, 1), 50))
        return [observation_from_document(doc) async for doc in cursor]
