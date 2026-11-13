"""Public API: ScreenProcessor, CaptureError. No database or AI dependencies."""
from .screen_processor import ScreenProcessor
from .capture import CaptureError

__all__ = ["ScreenProcessor", "CaptureError"]
