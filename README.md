# BUTL-R

A local-first screen understanding and persistent memory assistant built for **TheCruisers**. One FastAPI application, three independently owned modules, a React dashboard, local MongoDB, and local Ollama inference. No cloud AI, API keys, telemetry, authentication provider, Docker, or autonomous desktop control.

## What works

- Manually capture the foreground Windows window with `mss`; inspect UI Automation using `pywinauto`; extract OCR with Tesseract. Screen processing returns a shared Pydantic contract and has no database or AI dependencies.
- Send a temporary screenshot and redacted extracted text to an installed Ollama vision model. Validate JSON output, recover bounded formatting errors, and retry once. OCR/capture still return when inference fails.
- Persist normalized observations and AI summaries with `pymongo.AsyncMongoClient`. Native MongoDB text search, timestamp indexes, TTL retention, recent observations, ID lookup, deletion, conversations, settings, and reusable summary storage are included.
- Retrieve bounded historical context for local Q&A, return the retrieved memory IDs, and save conversations when enabled. No matching records produces an explicit message without invented memory.
- Dark React dashboard with manual capture, temporary screenshot preview, extracted text, UI controls, AI analysis, chat, searchable memories, settings, and service health.
- Exact frontend Origin, per-backend-session token, Host checks, no-store responses, loopback-only service configuration, text redaction, and explicit bulk-delete confirmation.

## Project structure and ownership

```text
backend/
  shared/             contracts.py, config.py, security.py (joint agreement)
  screen_engine/      capture, accessibility, OCR, processor, routes, tests (Member 1)
  memory_engine/      AsyncMongoClient, indexes, manager, retriever, routes, tests (Member 2)
  assistant_engine/   Ollama, vision, bounded context, assistant, routes, tests (Member 3)
  integration.py      capture → analysis → memory orchestration (Member 3)
  main.py             one FastAPI application, dependency wiring, health/settings (Member 3)
frontend/             React + Vite + Tailwind + Lucide (Member 3)
docs/                 architecture, API contracts, ownership and validation
scripts/              environment checks, indexes, backend launcher
tests/                API integration and optional live service tests
```

See [architecture](docs/ARCHITECTURE.md), [API contracts](docs/API_CONTRACTS.md), [Member 1](docs/MEMBER_1.md), [Member 2](docs/MEMBER_2.md), and [Member 3](docs/MEMBER_3.md).

## Windows installation

Install these once, then reopen PowerShell so PATH updates take effect:

1. [Python 3.11+](https://www.python.org/downloads/windows/), with the Python launcher and PATH option.
2. [Node.js LTS](https://nodejs.org/en/download), including npm. Node 20.19+ or 22.12+ is recommended for the frontend toolchain.
3. [MongoDB Community Server](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-windows/), using its local Windows service. The separate MongoDB Shell (`mongosh`) is useful for checks.
4. [Ollama for Windows](https://ollama.com/download/windows).
5. [Tesseract Windows installer information](https://tesseract-ocr.github.io/tessdoc/Installation.html). Install English language data. BUTL-R checks PATH and `C:\Program Files\Tesseract-OCR\tesseract.exe`; override with `TESSERACT_CMD` when needed.

In the project root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

No PowerShell activation or execution policy change is needed. Edit `.env` as appropriate. `.env` is ignored by Git. Automatic capture and raw screenshot storage are intentionally unavailable; setting either environment flag to true produces a startup configuration error.

### MongoDB

If installed as a Windows service, check/start it (starting the service may need Administrator PowerShell):

```powershell
Get-Service MongoDB
Start-Service MongoDB
mongosh "mongodb://127.0.0.1:27017" --eval "db.adminCommand({ ping: 1 })"
```

For a manual process instead of the service:

```powershell
New-Item -ItemType Directory -Force .\local-data\mongodb
& "C:\Program Files\MongoDB\Server\9.0\bin\mongod.exe" --dbpath "$PWD\local-data\mongodb" --bind_ip 127.0.0.1 --port 27017
```

Replace `9.0` with the installed version. Run only one server on port 27017. Keep MongoDB bound to loopback. MongoDB writes its persistent data to the service's configured data directory or the explicit `--dbpath`; restarting BUTL-R does not delete it.

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_indexes
```

Indexes are also initialized at backend startup and lazily before inserts/search, so a database that starts later can recover. Database name defaults to `butlr_memory`. Keep `local-data/` out of Git; it is already ignored.

### Ollama

Ollama usually starts automatically after installation on Windows. In a terminal:

```powershell
ollama pull qwen2.5vl:3b
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Use `ollama serve` **only if the server is not already running**. The default model supports both [text and image input](https://ollama.com/library/qwen2.5vl). To use the optional alternative:

```powershell
ollama pull gemma3:4b
```

Set `OLLAMA_VISION_MODEL=gemma3:4b` and `OLLAMA_CHAT_MODEL=gemma3:4b` in `.env` before startup. Saved Settings override the vision model default; select the installed model in Settings as needed. Chat uses `OLLAMA_CHAT_MODEL`. The backend calls the local `/api/chat` endpoint with base64 image data and a JSON schema, following [Ollama structured output documentation](https://ollama.com/blog/structured-outputs).

### Start the backend

From the project root:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_backend
```

Equivalent default command:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The launcher honors `BACKEND_HOST` and `BACKEND_PORT` and rejects non-loopback bindings. The equivalent Uvicorn command uses the explicit address given. Do not bind this application to `0.0.0.0`.

### Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Use that exact origin: `127.0.0.1:5173` is a different origin and will be rejected by default. Set `FRONTEND_ORIGIN` in backend `.env` if intentionally changing it. `frontend/.env.local` may set `VITE_BACKEND_URL=http://127.0.0.1:8000` when the backend address changes. Build/preview with `npm run build` and `npm run preview`; preview also uses port 5173 so the same strict origin works (stop the development server first).

This workspace was built with the bundled pnpm because standalone npm was absent. `frontend/pnpm-lock.yaml` records the exact frontend dependency resolution. With pnpm available, use `pnpm install --frozen-lockfile`, `pnpm dev`, and `pnpm build`. `pnpm-workspace.yaml` permits esbuild's installation script. npm is also supported, but does not read the pnpm lockfile. With dependencies already installed, run `.\scripts\run_frontend.ps1` from the project root to launch without npm, or run `node .\node_modules\vite\bin\vite.js` from `frontend/`.

## Verify the environment

```powershell
.\.venv\Scripts\python.exe -m scripts.check_environment
node --version
npm --version
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

The Python checker verifies dependencies, Tesseract location, local MongoDB, local Ollama, installed vision/chat model names, Node, and frontend dependencies. It captures no screen and performs no AI inference. Missing requirements produce exit code 1 and actionable messages.

## Tests and build

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

Unit/API tests use injected screen providers, MongoDB mocks, and Ollama mocks. They do not require a desktop or live services. Optional live checks use unique `butlr_test_<uuid>` databases and delete only those databases afterwards. They verify connection-reopen persistence, text search, settings, deletion, local image analysis on an explicitly generated fixture, and memory-grounded answers:

```powershell
$env:BUTLR_LIVE_TESTS="1"
# Optional override if the default Qwen model is not installed:
$env:BUTLR_TEST_MODEL="gemma3:4b"
.\.venv\Scripts\python.exe -m pytest -m live -v
Remove-Item Env:BUTLR_LIVE_TESTS
Remove-Item Env:BUTLR_TEST_MODEL
```

See [validation notes](docs/VALIDATION.md) for checks performed in this workspace and remaining manual checks.

## Using BUTL-R

1. Verify local service status. Enable capture and memory in Settings.
2. Click **Analyze Screen** to capture whichever desktop window is foreground when the request reaches the backend. Clicking the browser normally makes the browser itself foreground; switch to the intended window immediately or trigger the authenticated API from a local client while that target is foreground. This MVP has no window picker or background watcher.
3. Check application, title, preview, extracted text, UI controls, warnings, and summary. A failed inference still returns the real capture, and can store it for later retrieval.
4. In Memory, search for a distinctive term such as `NameError` and inspect the record. Ask “What error did I encounter earlier?” in the assistant.
5. Restart the backend and confirm the observation remains in Memory. Delete individual memories, or type the explicit phrase in Settings to clear all observations, summaries, and conversations.

## Slow local inference

CPU-only inference and the first model load can take several minutes. BUTL-R now waits up to 300 seconds per local inference request, limits generation to 768 tokens, and resizes the model's screenshot input to a maximum 1280-pixel side. OCR and the preview retain the original screenshot. Only one inference request runs at a time; a competing request reports that AI is busy instead of adding work to Ollama's queue. Invalid structured JSON can still trigger one corrective request, but timeouts are never automatically retried.

To tune this on your machine, set these in the root `.env`, then restart the backend:

```env
OLLAMA_TIMEOUT_SECONDS=300
OLLAMA_MAX_OUTPUT_TOKENS=768
OLLAMA_VISION_MAX_DIMENSION=1280
```

For very slow CPU systems, try a 600-second timeout and a 1024-pixel input. Smaller inputs can lose fine visual details; extracted OCR text still accompanies them. Keep a vision-capable model such as Qwen or `gemma3:4b` for screenshots; an installed text-only model can be configured separately through `OLLAMA_CHAT_MODEL`. No model is silently changed. Ollama documents [model loading, context memory and concurrency](https://docs.ollama.com/faq); use `ollama ps` to inspect the running model.

## Privacy and practical limitations

- Captures only on a manual API/button request. No startup capture, polling capture, hidden recording, telemetry, command execution, or screenshot upload to remote hosts.
- Screenshots are temporarily returned as base64 previews, sent only to local Ollama, and discarded by the backend after the request. `/screen/latest` stores only session text/metadata. The frontend retains the current preview until it is replaced or the panel is unmounted. Browser/OS/GPU memory and Ollama runtime buffers are outside secure-erasure guarantees.
- Password UI controls are skipped. OCR, metadata, stored observations, and model output use heuristic password/key/token redaction. This cannot reliably identify every credential, especially in images, unlabeled text, or novel token formats. Close sensitive windows before capture. No credential vault or deliberate credential-storage feature exists.
- `mss` captures visible pixels in the foreground window rectangle; occluding windows, protected applications, UAC/secure desktops, minimized windows, remote sessions, mixed DPI, and some Electron/custom controls can limit results. UIA calls can block inside Windows despite traversal limits. OCR quality depends on scale, language data, and contrast. There is no claim of perfect capture or redaction.
- Only Windows supports active-window capture in this MVP. Isolated tests can run without a Windows desktop. Ollama model hardware/RAM requirements and inference latency vary. Missing vision capabilities or invalid JSON produce explicit errors.
- Full-text retrieval is English MongoDB native word/stem search (OR terms), with a bounded recent fallback only for explicit temporal questions. It has no embeddings, chat-history reconstruction, or semantic ranking. Returned IDs identify retrieved context; inspect records to verify model claims. Prompt-injection resistance is best effort, not a guarantee of model truthfulness.
- Memory toggle controls new writes; existing memories remain readable until deleted. When MongoDB is offline, settings apply in process and report that they are not persisted; saving them after recovery persists them. Existing settings are loaded only at startup.
- Default retention is 30 days; 0 means manual deletion only. Expired observations are excluded from queries immediately, while MongoDB TTL physical deletion is asynchronous. Changes recompute expiry on all three memory collections. Individual deletion also deletes derived conversations/summaries; clear-all preserves settings. Deletion across collections is sequential, so a database failure can require retry. Database backups remain the user's responsibility.
- Local token security prevents unrelated websites from reading privileged APIs. Other programs already running as the local user remain inside the trust boundary. No multi-user authentication or hostile-local-user isolation is provided.

## Team workflow

Recommended long-lived branch: `main`. Feature branches: `feature/screen-engine`, `feature/memory-engine`, `feature/assistant-frontend`. Shared contracts were defined first in `backend/shared/contracts.py`; changes require agreement and API documentation updates. Each member owns their folder and tests. Integration belongs to Member 3; do not rewrite other modules to wire them together. Submit pull requests with module tests, then run API tests and the frontend build before merging. This delivery does not create remote repositories or branches automatically.
