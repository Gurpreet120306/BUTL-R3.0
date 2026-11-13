"""Opt in: $env:BUTLR_LIVE_TESTS='1'; python -m pytest -m live -v.

Uses a unique temporary database; only its own database is dropped.
No desktop capture. The vision input is an explicitly generated test image.
"""
import os
from io import BytesIO
from uuid import uuid4

from PIL import Image, ImageDraw
import pytest

from backend.assistant_engine import Assistant, OllamaClient, VisionAnalyzer
from backend.memory_engine import MemoryManager, MemoryRetriever, MongoConnection
from backend.screen_engine.schemas import CapturedScreen
from backend.shared.config import Config
from backend.shared.contracts import AnalyzedObservation, ScreenObservation, UserSettings

pytestmark = [pytest.mark.live, pytest.mark.skipif(os.getenv("BUTLR_LIVE_TESTS") != "1", reason="Opt-in local service checks")]


async def test_live_mongo_persistence_search_settings_and_deletion():
    config = Config()
    database_name = f"butlr_test_{uuid4().hex}"
    connection = MongoConnection(config.mongodb_uri, database_name)
    second = None
    try:
        manager = MemoryManager(connection.db)
        item = AnalyzedObservation(capture_id=str(uuid4()), capture_status="success", application="Test editor",
                                   extracted_text="NameError username not defined", ai_summary="Undefined variable")
        memory_id = await manager.save_observation(item)
        await manager.save_summary("Test error", item.ai_summary, [memory_id])
        await manager.save_answer("What error?", "NameError", [memory_id])
        await manager.save_settings(UserSettings())
        await connection.close()
        # A new connection simulates process restart; there is no in-memory fallback.
        second = MongoConnection(config.mongodb_uri, database_name)
        other_manager = MemoryManager(second.db)
        retriever = MemoryRetriever(second.db, other_manager)
        assert (await retriever.get(memory_id)).extracted_text == item.extracted_text
        assert (await retriever.search("NameError"))[0].observation_id == memory_id
        assert (await other_manager.load_settings()).memory_enabled
        await other_manager.apply_retention(1)
        assert await other_manager.delete(memory_id) == 1
        assert await retriever.get(memory_id) is None
        assert await second.db.assistant_conversations.count_documents({}) == 0
    finally:
        cleanup = second or connection
        await cleanup.client.drop_database(database_name)
        await cleanup.close()


async def test_live_ollama_vision_and_memory_grounded_answer():
    config = Config()
    model = os.getenv("BUTLR_TEST_MODEL", config.vision_model)
    ai = OllamaClient(config.ollama_url, config.ollama_timeout)
    db_name = f"butlr_test_{uuid4().hex}"
    connection = MongoConnection(config.mongodb_uri, db_name)
    try:
        assert (await ai.health(model)).available
        image = Image.new("RGB", (640, 240), "white")
        ImageDraw.Draw(image).text((30, 80), "TEST FIXTURE: NameError: username is not defined", fill="black", font_size=22)
        output = BytesIO()
        image.save(output, format="PNG")
        observed = ScreenObservation(capture_id=str(uuid4()), capture_status="success", application="Test fixture",
                                    extracted_text="NameError: username is not defined")
        result = await VisionAnalyzer(ai).analyze(CapturedScreen(observed, output.getvalue()), model)
        assert result.analysis_status == "complete", result.analysis_error
        manager = MemoryManager(connection.db)
        memory_id = await manager.save_observation(result)
        assistant = Assistant(ai, MemoryRetriever(connection.db, manager), manager, model)
        answer = await assistant.ask("What NameError was observed?", UserSettings())
        assert memory_id in answer.source_observation_ids
        assert answer.answer
    finally:
        await connection.client.drop_database(db_name)
        await connection.close()
        await ai.close()
