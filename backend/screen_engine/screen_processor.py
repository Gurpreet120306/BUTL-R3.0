from uuid import uuid4

from backend.shared.contracts import ScreenObservation
from backend.shared.security import redact, redact_value
from .accessibility import extract_ui
from .capture import CaptureError, active_window, capture_window, png_bytes
from .ocr_engine import extract_text
from .schemas import CapturedScreen


def normalize_text(ocr: str, controls: list[dict]) -> str:
    seen, lines = set(), []
    for line in ocr.splitlines() + [str(x.get("name", "")) for x in controls]:
        line = " ".join(line.split())
        key = line.casefold()
        if key and key not in seen:
            seen.add(key)
            lines.append(line)
    return redact("\n".join(lines))[:40000]


class ScreenProcessor:
    def __init__(self, tesseract_cmd=None, window_fn=active_window, capture_fn=capture_window,
                 ui_fn=extract_ui, ocr_fn=extract_text):
        self.tesseract_cmd = tesseract_cmd
        self.window_fn, self.capture_fn = window_fn, capture_fn
        self.ui_fn, self.ocr_fn = ui_fn, ocr_fn

    def process(self, permitted: bool = True) -> CapturedScreen:
        if not permitted:
            raise CaptureError("Screen capture is disabled in Settings")
        info = self.window_fn()
        image = self.capture_fn(info)
        # Reject focus changes rather than assigning metadata from another window.
        if self.window_fn().handle != info.handle:
            raise CaptureError("Foreground window changed during capture. Try again")
        controls, ui_warnings = self.ui_fn(info.handle)
        text, ocr_warnings = self.ocr_fn(image, self.tesseract_cmd)
        if self.window_fn().handle != info.handle:
            raise CaptureError("Foreground window changed during extraction. Try again")
        warnings = ui_warnings + ocr_warnings
        observation = ScreenObservation(
            application=redact(info.application or "") or None,
            window_title=redact(info.title), extracted_text=normalize_text(text, controls),
            ui_elements=redact_value(controls), capture_status="partial" if warnings else "success",
            capture_id=str(uuid4()), warnings=warnings,
            source_metadata={"platform": "windows", "bounds": list(info.bounds), "image_size": list(image.size),
                             "capture_method": "mss foreground window", "redaction": "best effort text only"},
        )
        return CapturedScreen(observation, png_bytes(image))
