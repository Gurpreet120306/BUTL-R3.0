# BUTL-R validation

## Inference timeout follow-up — 14 November 2026

Qwen is now installed and selected. Local `/api/ps` reported `qwen2.5vl:3b` with zero GPU-offloaded bytes and an 8192-token context. The earlier 120-second, 1800-output-token defaults could leave insufficient time for CPU inference; the exact timing of the user's failed request was not available.

The backend now defaults to 300 seconds, 768 output tokens, and a 1280-pixel maximum side for vision inputs. Original screenshots are retained for OCR and temporary previews. Vision text/control inputs are also bounded more tightly. Competing local inference requests return a busy message instead of adding concurrent work; timeout errors describe the timeout and configuration remedy and never trigger an automatic retry. These settings are configurable in `.env`; the user's chosen model was preserved.

- Regression suite: **43 passed, 2 optional live tests skipped**, 7.04 seconds.
- Live installed Qwen check: **1 passed in 115.11 seconds**, covering generated-fixture screenshot analysis, MongoDB retrieval and a memory-grounded text answer. Used a unique temporary test database and cleaned it up.
- Backend restarted with the changes; authenticated `/api/health` returned HTTP 200 and `status=ok`.
- Added regressions for image resizing/original preservation, busy-request rejection, generation budget, timeout defaults and invalid performance configuration.
- Actual desktop performance still depends on image complexity, record size, model state and CPU load; this generated-fixture check does not guarantee every manual analysis finishes within 300 seconds.

## Original MVP validation — 13 November 2026

Checks performed on 13 November 2026 on Windows with Python 3.12.7 and Node 24.22.1.

| Check | Result |
|---|---|
| Isolated backend and API suite | **40 passed, 2 optional live tests skipped**, 2.29 seconds on final run |
| Opt-in local service suite | **2 passed**, 82.31 seconds, using installed `gemma3:4b` |
| MongoDB persistence | Saved a test observation, closed the client, reopened a separate connection and retrieved the same data |
| Real native MongoDB operations | Index creation, `$text` search, settings, retention update and deletion passed in a unique temporary test database |
| Real Ollama vision | Validated structured image analysis of a generated, labeled test fixture with `gemma3:4b` |
| Real grounded Q&A | Saved that analysis, retrieved it, obtained a local answer and checked returned source IDs |
| Frozen frontend dependencies | `pnpm install --frozen-lockfile` passed; esbuild postinstall completed |
| Frontend production build | Passed: 1,588 modules transformed; JS approximately 251 kB / 77.5 kB gzip |
| FastAPI startup | Passed on `127.0.0.1:8000` with actual local MongoDB/Ollama connections |
| Vite startup | Passed on `http://localhost:5173` |
| Browser smoke check | Installed Edge, headless: real health API returned 200; dashboard, Memory/search and Settings loaded; no browser page errors |
| Responsive check | 1,440px desktop and 390px mobile screenshots inspected; mobile had no horizontal overflow |
| Environment checker | Python dependencies, Node, MongoDB, Ollama server, frontend dependencies and installed Tesseract detected |
| Default Qwen installation | **Not installed** on this machine; checker correctly exits 1 with `ollama pull qwen2.5vl:3b` instructions |

The default Qwen model remains configured in `.env.example` and backend defaults. Live model validation used the explicitly supported installed alternative, without changing the user's persisted settings. The installed models detected were `gemma3:1b`, `gemma3:4b`, and `llama3.2-vision:latest`. The default model's actual inference remains to be checked after downloading it.

The live tests use unique `butlr_test_<uuid>` databases and remove only those databases. They never capture the desktop. The browser checks do not create observations or alter settings. Dashboard screenshots show real backend data, not fixture memories. Test-only mocked and generated content stays in the tests.

## Remaining manual desktop validation

1. Install Qwen with the documented command, or select/configure `gemma3:4b` for both vision and chat.
2. Manually capture an intended foreground application. Verify process/title, screenshot pixels, OCR accuracy, accessibility metadata, summary and persisted observation. Clicking the browser makes it foreground; see README's foreground-window note.
3. Validate two-monitor negative-origin/mixed-DPI arrangements, protected/UAC windows, and application-specific UIA behavior on team hardware. Capture mechanics are mocked in the isolated tests; this delivery does not claim those hardware cases have been exercised.
4. Restart the whole application and MongoDB Windows service and verify a deliberately saved manual observation remains. Automated tests verify connection-reopen persistence; they do not restart the user's system services.
5. Verify a manual deletion in the UI with disposable team-created observations. Automated API tests enforce explicit bulk confirmation and live tests cover actual database deletion.

## Environment notes

Windows async tests stalled within the execution sandbox even with mocked HTTP; the same suite passed outside it. Dependency installation and local-service checks also required sandbox elevation. Standalone npm was not on PATH, so validation used the bundled pnpm and direct Vite CLI. `scripts/run_frontend.ps1` can start the installed project without npm.

The installed FastAPI/Starlette combination emits one upstream deprecation warning about httpx-based TestClient support; all tests pass. `requirements-lock.txt` records the validated Python 3.12 Windows dependency resolution, while portable direct dependencies (including Windows-only platform markers) remain in `requirements.txt`. Use the latter on non-Windows systems. Screenshots in `validation-artifacts/` are ignored by Git.
