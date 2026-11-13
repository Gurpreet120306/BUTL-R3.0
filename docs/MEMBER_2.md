# Member 2 — Memory engine

## Ownership and responsibilities

Own `backend/memory_engine/`: `__init__.py`, `mongo_client.py`, `collections.py`, `memory_manager.py`, `memory_retriever.py`, `schemas.py`, `routes.py`, and `tests/test_memory.py`. Own local connection health, collection/index definitions, asynchronous storage/search, safe serialization, deletion, retention, and settings persistence. No screen capture or Ollama calls.

## Public functions and schemas

- `MongoConnection(uri, database)`: public `.db`, `health() -> ServiceStatus`, `close()`.
- `MemoryManager(db)`: `ensure_indexes()`, `save_observation(AnalyzedObservation, retention_days=30) -> str`, `save_summary(title, summary, source_ids, retention_days=30) -> str`, `save_answer(question, answer, source_ids, retention_days=30) -> str`.
- Manager also exposes `delete(id) -> int`, `clear() -> int`, `load_settings() -> UserSettings | None`, `save_settings(settings)`, and `apply_retention(days)`.
- `MemoryRetriever(db, manager)`: `get(id) -> AnalyzedObservation | None`, `recent(limit=20) -> list[AnalyzedObservation]`, `search(query, limit=10) -> list[AnalyzedObservation]`.
- `MemoryUnavailable`: sanitized database service/operation failure, handled by API integration as 503 or partial-success warning.

Input: validated shared observations/settings, bounded text queries, string IDs. Output: typed models and safe string IDs, never raw `_id`. Observation insertion updates the supplied observation with persisted/observation_id. No screenshots or API credentials enter the schema. Refer to API_CONTRACTS.md and ARCHITECTURE.md for collection/index definitions and error semantics.

## Dependencies and tests

`pymongo>=4.13` with `AsyncMongoClient`, Pydantic, local MongoDB Community. Index creation uses the native async collection API. No Motor, SQL, Atlas Search, embeddings, or in-memory database fallback.

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_indexes
.\.venv\Scripts\python.exe -m pytest backend/memory_engine/tests -q
```

Mocked tests cover inserts/redaction, ObjectId serialization, text search syntax/bounds, index creation, connection failure, derived-record deletion and clear preservation of settings. Opt-in live tests cover connection-reopen persistence, actual text indexes, CRUD, retention pipeline, and settings.

## Completion and integration checklist

- [x] Async CRUD, four collections, native text/timestamp/TTL indexes, health, deletion and settings.
- [x] Public storage/retrieval interface and mocked tests.
- [x] Optional live integration test provided.
- [ ] Team production-machine restart/persistence smoke test and backup policy review.

Member 3 creates one connection during lifespan and passes its database to manager/retriever. Recover from offline startup through lazy index initialization. Close client on shutdown. Use `feature/memory-engine`, PR into main, and coordinate shared schema/index migrations. Do not drop or recreate user databases to resolve integration problems.
