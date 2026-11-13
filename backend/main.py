import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from backend.integration import coordinate_capture
from backend.assistant_engine import Assistant, OllamaClient, OllamaUnavailable, VisionAnalyzer
from backend.assistant_engine.routes import router as assistant_router
from backend.memory_engine import MemoryManager, MemoryRetriever, MemoryUnavailable, MongoConnection
from backend.memory_engine.routes import router as memory_router
from backend.screen_engine import ScreenProcessor
from backend.screen_engine.routes import router as screen_router
from backend.shared.config import Config
from backend.shared.contracts import HealthResponse, ModelList, ServiceStatus, SettingsResponse, SettingsUpdate, UserSettings
from backend.shared.security import check_origin, new_session_token, require_session


def create_app(config: Config | None = None, overrides: dict | None = None) -> FastAPI:
    config = config or Config()

    @asynccontextmanager
    async def lifespan(app):
        state = app.state
        state.config = config
        state.session_token = new_session_token()
        state.coordinate_capture = coordinate_capture
        state.latest = None
        state.capture_lock = asyncio.Lock()
        state.settings_lock = asyncio.Lock()
        state.settings = UserSettings(memory_enabled=config.memory_enabled, capture_enabled=config.capture_enabled,
                                      selected_ollama_model=config.vision_model, memory_retention_days=config.retention_days)
        state.mongo = (overrides or {}).get("mongo") or MongoConnection(config.mongodb_uri, config.mongodb_db)
        state.memory = (overrides or {}).get("memory") or MemoryManager(state.mongo.db)
        state.retriever = (overrides or {}).get("retriever") or MemoryRetriever(state.mongo.db, state.memory)
        state.ollama = (overrides or {}).get("ollama") or OllamaClient(
            config.ollama_url, config.ollama_timeout, max_tokens=config.ollama_max_tokens)
        state.screen = ScreenProcessor(config.tesseract_cmd)
        state.analyzer = VisionAnalyzer(state.ollama, config.vision_max_dimension)
        state.assistant = Assistant(state.ollama, state.retriever, state.memory, config.chat_model)
        for key, value in (overrides or {}).items():
            setattr(state, key, value)
        try:
            saved = await state.memory.load_settings()
            if saved:
                state.settings = saved
            await state.memory.ensure_indexes()
        except MemoryUnavailable:
            pass  # Offline startup is supported; each operation still reports its own error.
        yield
        await state.ollama.close()
        await state.mongo.close()

    app = FastAPI(title="BUTL-R", version="0.1.0", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])
    app.add_middleware(CORSMiddleware, allow_origins=[config.frontend_origin],
                       allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Content-Type", "X-BUTLR-Token"], max_age=600)

    @app.middleware("http")
    async def no_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(MemoryUnavailable)
    async def mongo_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(OllamaUnavailable)
    async def ollama_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.get("/api/session", dependencies=[Depends(check_origin)])
    async def session(request: Request):
        # An unrelated website cannot read this token: exact Origin + JSON/custom-header flow.
        return {"token": request.app.state.session_token}

    api = APIRouter(dependencies=[Depends(require_session)])
    api.include_router(screen_router)
    api.include_router(memory_router)
    api.include_router(assistant_router)

    @api.get("/api/health", response_model=HealthResponse)
    async def health(request: Request):
        state = request.app.state
        ollama, mongodb = await asyncio.gather(state.ollama.health(state.settings.selected_ollama_model), state.mongo.health())
        return HealthResponse(status="ok" if ollama.available and mongodb.available else "degraded", ollama=ollama, mongodb=mongodb)

    @api.get("/api/ollama/status", response_model=ServiceStatus)
    async def ollama_status(request: Request):
        return await request.app.state.ollama.health(request.app.state.settings.selected_ollama_model)

    @api.get("/api/ollama/models", response_model=ModelList)
    async def models(request: Request):
        return ModelList(models=await request.app.state.ollama.models())

    @api.get("/api/mongodb/status", response_model=ServiceStatus)
    async def mongo_status(request: Request):
        return await request.app.state.mongo.health()

    @api.get("/api/settings", response_model=SettingsResponse)
    async def settings(request: Request):
        state = request.app.state
        try:
            saved = await state.memory.load_settings()
            # Never overwrite changes made in this running session after an offline save.
            return SettingsResponse(settings=state.settings, persisted=saved == state.settings)
        except MemoryUnavailable as exc:
            return SettingsResponse(settings=state.settings, persisted=False, warning=str(exc))

    @api.put("/api/settings", response_model=SettingsResponse)
    async def update_settings(request: Request, body: SettingsUpdate):
        state = request.app.state
        async with state.settings_lock:
            settings = state.settings.model_copy(update=body.model_dump(exclude_none=True))
            previous = state.settings
            state.settings = settings
            try:
                await state.memory.ensure_indexes()
                if previous.memory_retention_days != settings.memory_retention_days:
                    await state.memory.apply_retention(settings.memory_retention_days)
                await state.memory.save_settings(settings)
                return SettingsResponse(settings=settings, persisted=True)
            except MemoryUnavailable as exc:
                return SettingsResponse(settings=settings, persisted=False,
                                        warning=f"Applied for this session only. {exc}")

    app.include_router(api)
    return app


app = create_app()
