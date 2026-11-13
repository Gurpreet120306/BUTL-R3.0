# BUTL-R API contracts

Base: `http://127.0.0.1:8000`. JSON bodies; all responses have `Cache-Control: no-store`. Stable schemas live in `backend/shared/contracts.py`. FastAPI's schema is at `/openapi.json` and interactive documentation at `/docs`.

## Local session

Browser requests must originate from exactly `FRONTEND_ORIGIN` (default `http://localhost:5173`). First `GET /api/session` with that Origin returns `{"token":"..."}`. All remaining routes require `Origin` plus `X-BUTLR-Token`. Tokens rotate on backend restart; the frontend retries once after refreshing its token. No token is stored on disk. Swagger's same-backend-origin “Try it out” cannot bypass the configured frontend Origin. For manual CLI checks supply the headers explicitly:

```powershell
$headers = @{ Origin = "http://localhost:5173" }
$session = Invoke-RestMethod http://127.0.0.1:8000/api/session -Headers $headers
$headers['X-BUTLR-Token'] = $session.token
Invoke-RestMethod http://127.0.0.1:8000/api/health -Headers $headers
```

## Routes

| Method / path | Input | Result |
|---|---|---|
| GET /api/health | session headers | app, status (`ok`/`degraded`), ollama, mongodb |
| POST /api/screen/capture | `{"include_preview":true}` | ScreenResponse with extraction only, no persistence |
| POST /api/screen/analyze | same | capture + local vision + observation persistence if enabled |
| GET /api/screen/latest | none | previous successful session observation; no screenshot; 404 if absent |
| GET /api/memory | limit 1–50, default 20 | `{"items":[AnalyzedObservation]}` newest first |
| GET /api/memory/search | q 1–500 characters; limit 1–50 | same, native text score order |
| GET /api/memory/{id} | 24-character hex ObjectId | AnalyzedObservation or 404 |
| DELETE /api/memory/{id} | same | `{"deleted":1}` or 404; removes associated derived records |
| DELETE /api/memory | `confirm=DELETE ALL MEMORIES` | deleted count across observations/conversations/summaries; settings preserved |
| POST /api/assistant/ask | `{"question":"What error did I encounter earlier?"}` | AssistantAnswer |
| GET /api/ollama/status | none | ServiceStatus, validates selected vision model |
| GET /api/ollama/models | none | `{"models":["qwen2.5vl:3b"]}` from local `/api/tags` |
| GET /api/mongodb/status | none | ServiceStatus |
| GET /api/settings | none | SettingsResponse |
| PUT /api/settings | partial settings object | SettingsResponse with effective settings and persistence state |

## Core types

`ScreenObservation`: application/window_title nullable strings, extracted_text string, ui_elements list of dictionaries, timestamp UTC datetime, capture_status (`success`, `partial`, `failed`), capture_id UUID string, warnings list, source_metadata dictionary. List/dictionary fields use factory defaults.

`AnalyzedObservation`: all ScreenObservation fields plus observation_id nullable string, ai_summary string, important_findings and detected_errors lists, analysis_status (`not_requested`, `complete`, `unavailable`, `failed`), analysis_error nullable string, persisted boolean, memory_error nullable string. Source metadata contains capture bounds/size/method; successful vision adds model/task/UI/input metadata. ObjectIds never appear as raw BSON in JSON.

`ScreenResponse`: `{"observation": AnalyzedObservation, "preview_base64": "PNG base64 or null"}`. Previews are temporary and not stored. `/capture` always performs a fresh capture. `/latest` never performs capture and includes the original timestamp/capture_id.

`AssistantAnswer`: answer string, source_observation_ids list of string IDs chosen from retrieved records, conversation_id nullable string, memory_error nullable string. Source IDs represent supplied context, not independent verification of the model's conclusions. A no-match answer has no IDs. Conversation persistence failure returns the generated answer with a warning; failed retrieval or inference returns 503.

`ServiceStatus`: available boolean, message string, models list (empty for MongoDB). Health endpoint returns HTTP 200 even if status is degraded, allowing frontend diagnostics.

`UserSettings`: memory_enabled, capture_enabled, screenshot_retention_enabled (always false in MVP), selected_ollama_model, memory_retention_days (0–3650). PUT rejects raw-image retention true and unknown fields. A null patch field is ignored. Offline writes return effective session settings with persisted=false and a warning; they do not silently claim disk persistence.

## Errors and semantics

- 400: missing/wrong explicit clear confirmation.
- 403: wrong/missing Origin or session token; cross-site request; capture disabled.
- 404: absent memory/latest.
- 409: capture already in progress.
- 422: invalid body, unknown body field, invalid memory ID, invalid query bounds.
- 503: capture, MongoDB, or Ollama unavailable. Analyze returns HTTP 200 when capture succeeded but AI/storage degraded; inspect analysis_status, analysis_error, persisted, and memory_error.

FastAPI errors use `{"detail":"message"}`; validation errors may have the standard detail array. UI displays these as actionable text without interpreting HTML. No streaming, embeddings, remote URLs, arbitrary command execution, or automatic monitoring endpoints exist.
