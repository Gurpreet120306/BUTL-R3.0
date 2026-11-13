from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.main import create_app
from backend.memory_engine import MemoryUnavailable
from backend.screen_engine.capture import CaptureError, WindowInfo
from backend.screen_engine.screen_processor import ScreenProcessor
from backend.shared.config import Config
from backend.shared.contracts import ServiceStatus


@pytest.fixture
def client():
    good = ServiceStatus(available=True, message="test fixture")
    manager = SimpleNamespace(load_settings=AsyncMock(return_value=None), ensure_indexes=AsyncMock(),
                              save_settings=AsyncMock(), clear=AsyncMock(return_value=3),
                              save_observation=AsyncMock(), apply_retention=AsyncMock())
    screen = ScreenProcessor(window_fn=lambda: WindowInfo(1, "Code.exe", "Editor", (0,0,100,100)),
                             capture_fn=lambda _: Image.new("RGB", (100,100), "white"),
                             ui_fn=lambda _: ([], []), ocr_fn=lambda *_: ("NameError", []))
    overrides = {"memory": manager, "screen": screen,
                 "mongo": SimpleNamespace(health=AsyncMock(return_value=good), close=AsyncMock()),
                 "ollama": SimpleNamespace(health=AsyncMock(return_value=good), close=AsyncMock(), models=AsyncMock(return_value=[])),
                 "retriever": SimpleNamespace(recent=AsyncMock(return_value=[]), search=AsyncMock(return_value=[]), get=AsyncMock(return_value=None))}
    app = create_app(Config(), overrides)
    with TestClient(app) as c:
        c.headers["Origin"] = "http://localhost:5173"
        c.headers["X-BUTLR-Token"] = c.get("/api/session").json()["token"]
        yield c


def test_health_and_api_models(client):
    response = client.get("/api/health")
    assert response.status_code == 200 and response.json()["app"] == "BUTL-R"
    assert client.get("/api/ollama/models").json() == {"models": []}


def test_unrelated_website_and_missing_token_blocked(client):
    assert client.get("/api/health", headers={"Origin":"https://evil.example"}).status_code == 403
    assert client.post("/api/screen/capture", json={}, headers={"X-BUTLR-Token":"wrong"}).status_code == 403
    assert client.get("/api/session", headers={"Origin":"null"}).status_code == 403
    assert client.get("/api/session", headers={"Origin":"http://evil.example", "Sec-Fetch-Site":"cross-site"}).status_code == 403
    assert client.get("/api/session", headers={"Sec-Fetch-Site":"cross-site"}).status_code == 200


def test_capture_does_not_require_ollama_or_mongodb(client):
    response = client.post("/api/screen/capture", json={})
    assert response.status_code == 200
    result = response.json()
    assert result["observation"]["extracted_text"] == "NameError"
    assert result["preview_base64"]
    assert client.get("/api/screen/latest").json()["preview_base64"] is None


def test_failed_capture_invalidates_previous_screen(client):
    assert client.post("/api/screen/capture", json={}).status_code == 200
    client.app.state.screen.process = lambda *_: (_ for _ in ()).throw(CaptureError("blocked"))
    assert client.post("/api/screen/capture", json={}).status_code == 503
    assert client.get("/api/screen/latest").status_code == 404


def test_capture_toggle_enforced(client):
    assert client.put("/api/settings", json={"capture_enabled":False}).status_code == 200
    assert client.post("/api/screen/capture", json={}).status_code == 403


def test_invalid_request_and_ids(client):
    assert client.post("/api/assistant/ask", json={"question":" "}).status_code == 422
    assert client.post("/api/assistant/ask", json={"question":"x", "unexpected":True}).status_code == 422
    assert client.get("/api/memory/search?q=").status_code == 422
    assert client.get("/api/memory?limit=1000").status_code == 422
    assert client.put("/api/settings", json={"screenshot_retention_enabled":True}).status_code == 422


def test_clear_requires_confirmation(client):
    assert client.delete("/api/memory").status_code == 400
    assert client.delete("/api/memory?confirm=DELETE%20ALL%20MEMORIES").json() == {"deleted":3}


def test_memory_disconnect_is_503(client):
    client.app.state.retriever.recent.side_effect = MemoryUnavailable("offline")
    assert client.get("/api/memory").status_code == 503


def test_offline_settings_apply_session_only(client):
    client.app.state.memory.save_settings.side_effect = MemoryUnavailable("offline")
    result = client.put("/api/settings", json={"memory_enabled":False}).json()
    assert not result["persisted"] and not result["settings"]["memory_enabled"]


def test_remote_configuration_rejected():
    with pytest.raises(ValueError): Config(ollama_url="https://remote.example")
    with pytest.raises(ValueError): Config(mongodb_uri="mongodb://remote.example:27017")


def test_analyze_failure_preserves_real_capture(client):
    from backend.assistant_engine import VisionAnalyzer, OllamaUnavailable
    client.app.state.analyzer = VisionAnalyzer(SimpleNamespace(chat=AsyncMock(side_effect=OllamaUnavailable("offline"))))
    result = client.post("/api/screen/analyze", json={}).json()
    assert result["observation"]["analysis_status"] == "unavailable"
    assert result["observation"]["extracted_text"] == "NameError"
    client.app.state.memory.save_observation.assert_awaited_once()
