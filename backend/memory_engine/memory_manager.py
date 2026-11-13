from datetime import timedelta
from functools import wraps

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import PyMongoError

from backend.shared.contracts import AnalyzedObservation, UserSettings, utcnow
from backend.shared.security import redact_value
from .collections import setup_indexes
from .mongo_client import MemoryUnavailable


def database_operation(fn):
    @wraps(fn)
    async def wrapped(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except PyMongoError as exc:
            raise MemoryUnavailable("MongoDB operation failed. Check the local service and retry") from exc
    return wrapped


def object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(422, "Memory ID must be a 24-character MongoDB ObjectId")
    return ObjectId(value)


def expiry(days: int):
    return utcnow() + timedelta(days=days) if days else None


def observation_from_document(document: dict) -> AnalyzedObservation:
    data = {key: value for key, value in document.items() if key in AnalyzedObservation.model_fields}
    data.update(observation_id=str(document["_id"]), persisted=True)
    return AnalyzedObservation.model_validate(data)


class MemoryManager:
    def __init__(self, db):
        self.db = db
        self.ready = False

    @database_operation
    async def ensure_indexes(self):
        if not self.ready:
            await setup_indexes(self.db)
            self.ready = True

    @database_operation
    async def save_observation(self, observation: AnalyzedObservation, retention_days: int = 30) -> str:
        await self.ensure_indexes()
        document = redact_value(observation.model_dump(exclude={"observation_id", "persisted", "memory_error"}))
        document.update(created_at=utcnow(), expires_at=expiry(retention_days))
        result = await self.db.screen_observations.insert_one(document)
        observation.observation_id = str(result.inserted_id)
        observation.persisted = True
        return observation.observation_id

    @database_operation
    async def save_summary(self, title: str, summary: str, source_ids: list[str], retention_days=30) -> str:
        await self.ensure_indexes()
        result = await self.db.memory_summaries.insert_one(redact_value({
            "title": title[:300], "summary": summary[:12000], "source_observation_ids": source_ids,
            "created_at": utcnow(), "expires_at": expiry(retention_days)}))
        return str(result.inserted_id)

    @database_operation
    async def save_answer(self, question: str, answer: str, source_ids: list[str], retention_days=30) -> str:
        await self.ensure_indexes()
        result = await self.db.assistant_conversations.insert_one(redact_value({
            "question": question, "answer": answer, "source_observation_ids": source_ids,
            "created_at": utcnow(), "expires_at": expiry(retention_days)}))
        return str(result.inserted_id)

    @database_operation
    async def delete(self, memory_id: str) -> int:
        result = await self.db.screen_observations.delete_one({"_id": object_id(memory_id)})
        # Remove derived material that could otherwise retain deleted sensitive text.
        for name in ("assistant_conversations", "memory_summaries"):
            await self.db[name].delete_many({"source_observation_ids": memory_id})
        return result.deleted_count

    @database_operation
    async def clear(self) -> int:
        count = 0
        for name in ("screen_observations", "assistant_conversations", "memory_summaries"):
            count += (await self.db[name].delete_many({})).deleted_count
        return count

    @database_operation
    async def load_settings(self) -> UserSettings | None:
        document = await self.db.user_settings.find_one({"_id": "local"})
        if not document:
            return None
        document.pop("_id", None)
        return UserSettings.model_validate(document)

    @database_operation
    async def save_settings(self, settings: UserSettings):
        await self.db.user_settings.replace_one({"_id": "local"}, {"_id": "local", **settings.model_dump()}, upsert=True)

    @database_operation
    async def apply_retention(self, days: int):
        # Recompute expiry for existing records relative to their creation time.
        for name in ("screen_observations", "assistant_conversations", "memory_summaries"):
            await self.db[name].update_many({}, [{"$set": {"expires_at": (
                {"$add": ["$created_at", days * 86400000]} if days else None)}}])
