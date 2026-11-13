from unittest.mock import patch

import pytest
from PIL import Image

from backend.screen_engine.capture import CaptureError, WindowInfo, capture_window
from backend.screen_engine.ocr_engine import extract_text, preprocess
from backend.screen_engine.screen_processor import ScreenProcessor, normalize_text


def processor(**kwargs):
    info = WindowInfo(12, "Code.exe", "editor", (0, 0, 200, 100))
    args = dict(window_fn=lambda: info, capture_fn=lambda _: Image.new("RGB", (200, 100), "white"),
                ui_fn=lambda _: ([{"name": "hello", "control_type": "Text"}], []),
                ocr_fn=lambda *_: ("hello\nworld\npassword=secret", []))
    args.update(kwargs)
    return ScreenProcessor(**args)


def test_normalization_deduplication_and_redaction():
    assert normalize_text("  Hello \nhello\napi_key=abc", [{"name": "hello"}]) == "Hello\napi_key=[REDACTED]"


def test_processor_real_contract_and_png():
    result = processor().process()
    assert result.image_bytes.startswith(b"\x89PNG")
    assert result.observation.application == "Code.exe"
    assert result.observation.capture_status == "success"
    assert "secret" not in result.observation.extracted_text
    assert result.observation.timestamp.tzinfo is not None


def test_capture_disabled_never_calls_window():
    with pytest.raises(CaptureError, match="disabled"):
        processor(window_fn=lambda: pytest.fail("must not access desktop")).process(False)


def test_capture_identifiers_are_fresh():
    p = processor()
    assert p.process().observation.capture_id != p.process().observation.capture_id


def test_focus_change_rejected():
    windows = iter([WindowInfo(1, "A", "A", (0,0,2,2)), WindowInfo(2, "B", "B", (0,0,2,2))])
    with pytest.raises(CaptureError, match="changed"):
        processor(window_fn=lambda: next(windows)).process()


def test_missing_ocr_yields_partial_capture():
    result = processor(ocr_fn=lambda *_: ("", ["Tesseract missing"])).process()
    assert result.observation.capture_status == "partial"
    assert result.observation.extracted_text == "hello"


def test_preprocessing_grayscale_and_scale():
    image = preprocess(Image.new("RGB", (100, 50), "red"))
    assert image.mode == "L"
    assert image.size == (200, 100)


def test_missing_tesseract():
    import pytesseract
    with patch.object(pytesseract, "image_to_string", side_effect=pytesseract.TesseractNotFoundError()):
        text, warnings = extract_text(Image.new("RGB", (10, 10)))
    assert not text
    assert "Tesseract is missing" in warnings[0]


def test_capture_clips_to_virtual_monitor():
    class Shot:
        size = (2, 1)
        rgb = bytes([0, 20, 30, 255, 220, 110])
    class Screen:
        monitors = [{"left": -2, "top": 0, "width": 2, "height": 1}]
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def grab(self, region):
            assert region == {"left": -2, "top": 0, "width": 2, "height": 1}
            return Shot()
    with patch("mss.mss", return_value=Screen()):
        image = capture_window(WindowInfo(1, "A", "A", (-5, -5, 10, 10)))
    assert image.size == (2, 1)
