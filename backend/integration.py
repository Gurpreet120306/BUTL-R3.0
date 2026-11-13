"""Member 3 orchestration: stable public screen, memory and AI interfaces."""
import asyncio
import base64
from fastapi import HTTPException, Request
from backend.shared.contracts import AnalyzedObservation, CaptureRequest, ScreenResponse
from backend.screen_engine import CaptureError
from backend.memory_engine import MemoryUnavailable


async def coordinate_capture(request: Request, body: CaptureRequest, analyze: bool) -> ScreenResponse:
    state = request.app.state
    if state.capture_lock.locked():
        raise HTTPException(409, "A capture is already in progress")
    async with state.capture_lock:
        state.latest = None
        settings = state.settings
        if not settings.capture_enabled:
            raise HTTPException(403, "Screen capture is disabled in Settings")
        try:
            captured = await asyncio.to_thread(state.screen.process, settings.capture_enabled)
        except CaptureError as exc:
            raise HTTPException(503, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, "Screen extraction failed. Check the interactive desktop and capture permissions") from exc
        observation = AnalyzedObservation(**captured.observation.model_dump())
        if analyze:
            observation = await state.analyzer.analyze(captured, settings.selected_ollama_model)
            if state.settings.memory_enabled:
                try:
                    await state.memory.save_observation(observation, state.settings.memory_retention_days)
                except MemoryUnavailable as exc:
                    observation.memory_error = str(exc)
        # Raw bytes live only in this request. Latest holds text metadata, never an image.
        state.latest = observation
        return ScreenResponse(observation=observation, preview_base64=(
            base64.b64encode(captured.image_bytes).decode() if body.include_preview else None))


