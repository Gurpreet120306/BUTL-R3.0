# Member 1 — Screen engine

## Ownership and responsibilities

Own `backend/screen_engine/`: `__init__.py`, `capture.py`, `accessibility.py`, `ocr_engine.py`, `screen_processor.py`, `schemas.py`, `routes.py`, and `tests/test_screen.py`. Capture foreground windows, identify process/title, inspect UI controls, preprocess OCR, normalize/redact observations, handle failure, and maintain screen tests. Do not call MongoDB or Ollama from this module. Coordinate shared contract changes with all members.

## Public functions and schemas

- `ScreenProcessor(...).process(permitted=True) -> CapturedScreen`: injectable window/capture/UI/OCR providers; raises `CaptureError` on disabled/failed/changed focus.
- `active_window() -> WindowInfo`: HWND, application, title, pixel bounds.
- `capture_window(info) -> PIL.Image`: fresh `mss` capture clipped to virtual desktop.
- `extract_ui(handle, limit=300) -> (list[dict], list[str])`: controls and warnings; skips password text.
- `extract_text(image, command=None) -> (str, list[str])`: OCR text and warnings.
- `normalize_text(ocr, controls) -> str`: bounded, deduplicated, redacted text.
- `CapturedScreen`: shared `ScreenObservation` and internal PNG bytes. Only the shared observation crosses into persistence. Bytes go to the integration layer for temporary vision input/preview.

Input: permission plus actual Windows foreground desktop. Output: timestamped ScreenObservation with capture UUID, application, window title, extracted text, UI elements, status, warnings, source metadata. API response uses the shared ScreenResponse wrapper. Routes delegate orchestration to the injected integration function and do not implement AI/storage.

## Dependencies and tests

Python 3.11+, `mss`, Pillow, pytesseract, pywinauto, pywin32, psutil; Windows interactive session and Tesseract for real desktop/OCR. Imports of Windows-only libraries are lazy so mocked tests work without a desktop.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/screen_engine/tests -q
```

Tests cover clipping including negative monitor origins, preprocessing, missing Tesseract, permission gating, observation normalization/redaction, partial extraction, focus changes, and fresh identifiers.

## Completion and integration checklist

- [x] Capture implementation, metadata, UIA, OCR, shared contract, failure handling, isolated tests.
- [x] No database/model imports or screenshot persistence.
- [ ] Manually validate multiple-monitor mixed-DPI machines, UAC/protected content, custom UI controls, and target applications.

Member 3 injects ScreenProcessor into app.state and calls it in a worker thread from `backend/integration.py`. Change the processor interface only via agreement in API_CONTRACTS.md. Use `feature/screen-engine`, submit a PR to main, and include tests plus manual capture notes. Do not edit another owner's internals to integrate.
