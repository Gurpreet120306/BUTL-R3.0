# BUTL-R architecture

## Boundaries

BUTL-R is one modular monolith. `backend.main:create_app` creates shared dependencies in FastAPI's lifespan, loads settings, attempts index initialization, and registers routers. MongoDB/Ollama outages do not prevent frontend or API startup. There is no background capture task.

```text
Manual React action → authenticated local FastAPI route
  → screen_engine.ScreenProcessor.process → CapturedScreen
  → assistant_engine.VisionAnalyzer.analyze → AnalyzedObservation
  → memory_engine.MemoryManager.save_observation → MongoDB

Question → MemoryRetriever.search / recent → bounded context
  → OllamaClient.chat → answer + retrieved IDs → optional conversation storage
```

`backend/integration.py` owns orchestration. Screen routes delegate to this coordinator; screen internals do not import memory or AI. Memory internals do not import screen or AI. Assistant imports only the public memory error/interface behavior and shared contracts; it does not access MongoDB collections. Cross-module shared types live in `shared/contracts.py`. Member-specific `schemas.py` files expose their relevant shared schemas.

## Screen lifecycle

The foreground HWND, application process, title, and bounds come from Windows APIs. `mss` clips capture coordinates against the virtual desktop, preserving negative monitor coordinates. Focus changes before/after extraction reject the capture. UIA skips password controls and bounds traversal to 300 controls and a best-effort four-second traversal budget. OCR runs grayscale/autocontrast/upscale/sharpen preprocessing and Tesseract with a timeout. Extraction text is normalized, deduplicated, truncated and redacted.

`CapturedScreen` is an internal dataclass containing a `ScreenObservation` and PNG bytes; bytes never enter MongoDB. Every request generates a new capture UUID and timezone-aware timestamp. A single async lock prevents concurrent captures. A new attempt invalidates latest state before work. Failed capture returns 503 and latest becomes 404. Capture-disabled returns 403. `/latest` is explicitly session-local, dated metadata from an earlier successful request, never a fresh capture.

Vision receives an aspect-preserving image capped at a 1280-pixel side, plus bounded metadata and redacted text. This resize affects only local model input; OCR and previews retain the original. JSON schema-constrained inference is validated with Pydantic. Parsing tolerates a code fence or surrounding text and permits one corrective inference retry. Failed AI results have no fabricated summary. The observation can still persist with its error status. No raw image is cached by the backend's latest observation. Inference defaults to a 300-second read timeout and 768 generated tokens, configurable through environment variables. A client-level lock rejects competing inference requests instead of queuing more work; timeout failures are never automatically retried.

## MongoDB persistence

Uses `AsyncMongoClient`, not Motor. Each request awaits native asynchronous CRUD. Four collections:

| Collection | Contents and indexes |
|---|---|
| screen_observations | shared observation fields, AI summary/findings/errors, created_at, expires_at; timestamp, text and TTL indexes |
| assistant_conversations | question, answer, source_observation_ids, created_at, expires_at; created_at, text and TTL indexes |
| memory_summaries | reusable title/summary/source IDs via `save_summary`; created_at, text and TTL indexes |
| user_settings | one `_id: local` settings document; MongoDB built-in unique ID index |

Screen summaries are stored directly with their observations. The separate `save_summary` interface supports future combined summaries without requiring changes to screen storage; it is not a second automatic model call. `observation_from_document` filters internal fields and converts ObjectId to a string. Expired observations are filtered even before the TTL worker physically deletes them. Search uses `$text` and score sorting, at most 50 API results and six assistant records with an 18,000-character context budget. No fallback database exists; unavailable persistence is explicit.

## Security and failures

All privileged endpoints require the exact configured frontend Origin and the backend-process token in `X-BUTLR-Token`. `/api/session` issues the random token only after exact Origin validation; CORS additionally restricts browser reads and custom headers. Host validation reduces DNS rebinding risk. The configured Origin remains authoritative when browsers classify localhost → 127.0.0.1 as cross-site. Local URLs reject remote addresses, credentials, extra hosts, and query options. HTTP proxy environment settings and redirects are disabled for Ollama. Responses are `no-store`.

Settings updates apply immediately in memory, then persist. Database failures explicitly mark them session-only. A capture rechecks the memory toggle immediately before saving. Deletion has no hidden model invocation. All source records and screen text are labeled untrusted in model system prompts; they never flow into shell execution or UI-control APIs.

## Extension points

Replace `MemoryRetriever.search` behind the same typed result interface to add semantic retrieval later. Inject `ScreenProcessor`, `OllamaClient`, `MemoryManager`, retriever, or the high-level assistant through `create_app(overrides=...)` for tests. Future desktop control requires a separate approval/action/verification design; it is deliberately absent here.
