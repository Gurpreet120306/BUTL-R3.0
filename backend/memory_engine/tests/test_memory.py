from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId
import pytest
from fastapi import HTTPException
from pymongo.errors import ServerSelectionTimeoutError

from backend.memory_engine.collections import setup_indexes
from backend.memory_engine.memory_manager import MemoryManager, observation_from_document
from backend.memory_engine.memory_retriever import MemoryRetriever
from backend.memory_engine.mongo_client import MemoryUnavailable, MongoConnection
from backend.shared.contracts import AnalyzedObservation


def database():
    db = MagicMock()
    for name in ("screen_observations", "assistant_conversations", "memory_summaries", "user_settings"):
        setattr(db, name, AsyncMock())
    db.__getitem__.side_effect = lambda key: getattr(db, key)
    return db


def observation():
    return AnalyzedObservation(capture_status="success", capture_id="capture-test", extracted_text="NameError username", ai_summary="Undefined variable")


async def test_indexes_are_native_text_and_ttl():
    db = database()
    await setup_indexes(db)
    calls = db.screen_observations.create_index.call_args_list
    assert any(call.kwargs.get("name") == "observation_text" for call in calls)
    assert any(call.kwargs.get("expireAfterSeconds") == 0 for call in calls)


async def test_insert_returns_string_id_and_redacts():
    db = database()
    oid = ObjectId()
    db.screen_observations.insert_one.return_value = SimpleNamespace(inserted_id=oid)
    manager = MemoryManager(db)
    item = observation()
    item.extracted_text = "api_key=secret"
    assert await manager.save_observation(item) == str(oid)
    document = db.screen_observations.insert_one.call_args.args[0]
    assert "[REDACTED]" in document["extracted_text"]
    assert "image_bytes" not in document and "preview_base64" not in document
    assert item.persisted


async def test_insertion_failure_is_meaningful():
    db = database()
    db.screen_observations.insert_one.side_effect = ServerSelectionTimeoutError("offline")
    manager = MemoryManager(db)
    with pytest.raises(MemoryUnavailable):
        await manager.save_observation(observation())


async def test_retrieval_serializes_object_id():
    db = database()
    oid = ObjectId()
    db.screen_observations.find_one.return_value = {"_id": oid, **observation().model_dump()}
    retriever = MemoryRetriever(db, MemoryManager(db))
    item = await retriever.get(str(oid))
    assert item.observation_id == str(oid)
    assert "_id" not in item.model_dump()


async def test_invalid_memory_id_is_422():
    db = database()
    with pytest.raises(HTTPException) as error:
        await MemoryRetriever(db, MemoryManager(db)).get("bad-id")
    assert error.value.status_code == 422


async def test_search_uses_text_query_bounded_cursor():
    db = database()
    collection = MagicMock()
    db.screen_observations = collection
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.__aiter__.return_value = [{"_id": ObjectId(), **observation().model_dump()}]
    collection.find.return_value = cursor
    manager = MemoryManager(db)
    manager.ready = True
    result = await MemoryRetriever(db, manager).search('"NameError" -username', 100)
    assert collection.find.call_args.args[0]["$text"] == {"$search": "NameError username"}
    cursor.limit.assert_called_once_with(50)
    assert len(result) == 1


async def test_delete_cleans_derived_records():
    db = database()
    db.screen_observations.delete_one.return_value = SimpleNamespace(deleted_count=1)
    memory_id = str(ObjectId())
    assert await MemoryManager(db).delete(memory_id) == 1
    db.assistant_conversations.delete_many.assert_awaited_once_with({"source_observation_ids": memory_id})


async def test_clear_keeps_settings():
    db = database()
    for name in ("screen_observations", "assistant_conversations", "memory_summaries"):
        db[name].delete_many.return_value = SimpleNamespace(deleted_count=2)
    assert await MemoryManager(db).clear() == 6
    db.user_settings.delete_many.assert_not_called()


async def test_connection_health_failure():
    connection = MongoConnection("mongodb://127.0.0.1:27017", "test")
    original = connection.client
    connection.client = SimpleNamespace(admin=SimpleNamespace(command=AsyncMock(side_effect=ServerSelectionTimeoutError("offline"))))
    try:
        assert not (await connection.health()).available
    finally:
        await original.close()
