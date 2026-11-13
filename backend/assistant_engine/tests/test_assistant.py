import json
import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from PIL import Image

from backend.assistant_engine import Assistant, OllamaClient, OllamaUnavailable, VisionAnalyzer
from backend.assistant_engine.context_builder import build_context
from backend.assistant_engine.vision_analyzer import parse_vision
from backend.memory_engine import MemoryUnavailable
from backend.shared.contracts import AnalyzedObservation, ScreenObservation, UserSettings


def memory():
    return AnalyzedObservation(capture_id="test", capture_status="success", observation_id="a" * 24,
                               extracted_text="NameError: name 'username' is not defined", ai_summary="Undefined variable")


def captured():
    output = BytesIO()
    Image.new("RGB", (640, 240), "white").save(output, format="PNG")
    return SimpleNamespace(observation=ScreenObservation(capture_id="test", capture_status="success"), image_bytes=output.getvalue())


def test_vision_validation_and_limited_recovery():
    assert parse_vision('```json\n{"ai_summary":"A code editor"}\n```').ai_summary == "A code editor"
    assert parse_vision('Result: {"ai_summary":"A code editor"}').ai_summary
    with pytest.raises(ValueError):
        parse_vision('{"ai_summary":3}')


async def test_ollama_unavailable():
    def handler(request): raise httpx.ConnectError("offline")
    client = OllamaClient("http://127.0.0.1:11434", transport=httpx.MockTransport(handler))
    try:
        assert not (await client.health("qwen2.5vl:3b")).available
        with pytest.raises(OllamaUnavailable): await client.chat("qwen2.5vl:3b", [])
    finally: await client.close()


async def test_ollama_missing_model():
    client = OllamaClient("http://127.0.0.1:11434", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"models": []})))
    try:
        status = await client.health("qwen2.5vl:3b")
        assert not status.available and "ollama pull" in status.message
    finally: await client.close()


async def test_ollama_image_payload_and_timeout():
    def handler(request):
        if request.url.path == "/api/tags": return httpx.Response(200, json={"models":[{"name":"vision:1"}]})
        assert json.loads(request.content)["messages"][0]["images"] == ["abc"]
        raise httpx.ReadTimeout("slow")
    client = OllamaClient("http://127.0.0.1:11434", transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(OllamaUnavailable, match="timed out"):
            await client.chat("vision:1", [{"role":"user", "images":["abc"], "content":"image"}])
    finally: await client.close()


async def test_inference_budget_and_busy_request_rejection():
    calls = []
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models":[{"name":"vision:1"}]})
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"message":{"content":"answer"}})
    client = OllamaClient("http://127.0.0.1:11434", max_tokens=512, transport=httpx.MockTransport(handler))
    try:
        assert client.http.timeout.read == 300
        await client.inference_lock.acquire()
        try:
            with pytest.raises(OllamaUnavailable, match="busy"):
                await client.chat("vision:1", [])
        finally:
            client.inference_lock.release()
        assert not calls
        assert await client.chat("vision:1", []) == "answer"
        assert calls[0]["options"]["num_predict"] == 512
    finally:
        await client.close()


def test_vision_resizes_model_input_without_changing_original():
    original = BytesIO()
    Image.new("RGB", (3840, 2160), "white").save(original, format="PNG")
    image_bytes = original.getvalue()
    analyzer = VisionAnalyzer(None)
    encoded, size = analyzer.prepare_image(image_bytes)
    assert size == [1280, 720]
    assert Image.open(BytesIO(base64.b64decode(encoded))).size == (1280, 720)
    assert Image.open(BytesIO(image_bytes)).size == (3840, 2160)
    small_encoded, small_size = analyzer.prepare_image(captured().image_bytes)
    assert small_size == [640, 240]


def test_invalid_inference_configuration():
    from backend.shared.config import Config
    for options in ({"ollama_timeout":0}, {"ollama_max_tokens":1}, {"vision_max_dimension":0}):
        with pytest.raises(ValueError):
            Config(**options)


async def test_vision_failure_preserves_observation():
    ai = SimpleNamespace(chat=AsyncMock(side_effect=OllamaUnavailable("offline")))
    result = await VisionAnalyzer(ai).analyze(captured(), "vision:1")
    assert result.capture_status == "success" and result.analysis_status == "unavailable"
    assert not result.ai_summary


async def test_vision_invalid_output_retries_once():
    ai = SimpleNamespace(chat=AsyncMock(return_value="not JSON"))
    result = await VisionAnalyzer(ai).analyze(captured(), "vision:1")
    assert result.analysis_status == "failed" and ai.chat.await_count == 2


async def test_vision_success_redacts_model_output():
    ai = SimpleNamespace(chat=AsyncMock(return_value='{"ai_summary":"password=abc", "detected_errors":["NameError"]}'))
    result = await VisionAnalyzer(ai).analyze(captured(), "vision:1")
    assert result.analysis_status == "complete"
    assert "abc" not in result.ai_summary


def test_bounded_context():
    context, ids = build_context([memory()] * 20)
    assert len(ids) <= 6 and len(context) < 19000
    assert "untrusted_memory_records" in context


async def test_assistant_grounding_and_persistence():
    ai = SimpleNamespace(chat=AsyncMock(return_value="The earlier error was NameError."))
    retriever = SimpleNamespace(search=AsyncMock(return_value=[memory()]))
    manager = SimpleNamespace(save_answer=AsyncMock(return_value="conversation"))
    answer = await Assistant(ai, retriever, manager, "vision:1").ask("What error?", UserSettings())
    assert answer.source_observation_ids == ["a" * 24]
    assert answer.conversation_id == "conversation"
    messages = ai.chat.call_args.args[1]
    assert "NameError" in messages[1]["content"]
    assert "untrusted" in messages[0]["content"]


async def test_no_memory_does_not_invent_or_call_model():
    ai = SimpleNamespace(chat=AsyncMock())
    retriever = SimpleNamespace(search=AsyncMock(return_value=[]))
    result = await Assistant(ai, retriever, None, "model").ask("a nonexistent entry", UserSettings(memory_enabled=False))
    assert not result.source_observation_ids and "No matching" in result.answer
    ai.chat.assert_not_called()


async def test_answer_survives_failed_conversation_save():
    ai = SimpleNamespace(chat=AsyncMock(return_value="NameError"))
    retriever = SimpleNamespace(search=AsyncMock(return_value=[memory()]))
    manager = SimpleNamespace(save_answer=AsyncMock(side_effect=MemoryUnavailable("offline")))
    result = await Assistant(ai, retriever, manager, "model").ask("error", UserSettings())
    assert result.answer == "NameError" and result.memory_error == "offline"
