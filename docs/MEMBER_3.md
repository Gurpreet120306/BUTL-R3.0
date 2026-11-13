# Member 3 — Assistant, frontend and integration

## Ownership and responsibilities

Own `backend/assistant_engine/` (`__init__.py`, `ollama_client.py`, `vision_analyzer.py`, `context_builder.py`, `assistant.py`, `schemas.py`, `routes.py`, tests), all `frontend/`, `backend/main.py`, and `backend/integration.py`. Own local model health/detection, structured screenshot interpretation, grounded Q&A, dashboard/error states, dependency wiring, API integration and end-to-end checks.

## Public functions and schemas

- `OllamaClient(base_url, timeout=300, transport=None, max_tokens=768)`: `models() -> list[str]`, `health(model) -> ServiceStatus`, `chat(model, messages, schema=None) -> str`, `close()`; raises `OllamaUnavailable`. One in-flight inference is allowed per client; competing requests report busy.
- `VisionAnalyzer(ollama, max_dimension=1280).analyze(CapturedScreen, model) -> AnalyzedObservation`: maintains real screen evidence even when vision is unavailable; resizes only the model input, and permits one structured-output retry (never an automatic timeout retry).
- `build_context(memories, budget=18000) -> (str, list[str])`: up to six bounded, clearly untrusted records.
- `Assistant(ollama, retriever, memory, chat_model).ask(question, UserSettings) -> AssistantAnswer`: retrieval first, no-match handling, local text inference, optional conversation persistence.
- `create_app(config=None, overrides=None) -> FastAPI`: one application with injectable public service instances.
- `coordinate_capture(request, CaptureRequest, analyze) -> ScreenResponse`: member-owned modules connected by their public interfaces.

Frontend components: Sidebar, ScreenPanel, ChatPanel, MemoryPanel, StatusIndicator. Pages: Dashboard, Memories, Settings. `services/api.js` centralizes Fetch API, token bootstrap, one expired-token retry, no-store requests, and error conversion. React renders plain text; screen/model content is never inserted as HTML.

## Dependencies and tests

Python: FastAPI, Uvicorn, Pydantic, httpx, python-dotenv; public screen/memory interfaces. Frontend: React, Vite, JavaScript, Tailwind, Lucide. Models run on local Ollama only.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/assistant_engine/tests tests -q
cd frontend
npm run build
```

Tests cover health/model missing/timeouts, invalid/recovered vision JSON, context budget and grounding, no-match behavior, failed conversation persistence, HTTP codes, Origin/token checks, capture settings, and latest invalidation. Opt-in live checks cover local vision and retrieved-answer flow.

## Completion and integration checklist

- [x] Local Ollama API, JSON validation/retry, explicit unavailable states.
- [x] Bounded memory context, source IDs, no fake records or responses.
- [x] Responsive dashboard, settings, previews, search/deletion and service monitoring.
- [x] One FastAPI application; screen and memory internals stay independently owned.
- [x] Mocked API integration tests and frontend production build.
- [ ] Manual complete desktop workflow on the team's hardware, including default Qwen model.

Use `feature/assistant-frontend`, integrate completed public interfaces, and open PRs into main. Resolve interface mismatches by updating the agreed contract with owners. Do not rewrite another module's internals to bypass coordination. Run all module tests and frontend build before merge; document unavailable local services honestly.
