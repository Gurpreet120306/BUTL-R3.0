import sys
from dataclasses import dataclass
from io import BytesIO

from PIL import Image


class CaptureError(RuntimeError):
    pass


@dataclass
class WindowInfo:
    handle: int
    application: str | None
    title: str
    bounds: tuple[int, int, int, int]


def active_window() -> WindowInfo:
    if sys.platform != "win32":
        raise CaptureError("Active-window capture requires an interactive Windows desktop")
    import ctypes
    import psutil
    import win32gui
    import win32process

    # Per-monitor coordinates, including negative origins on secondary displays.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (OSError, AttributeError):
        pass
    handle = win32gui.GetForegroundWindow()
    if not handle or win32gui.IsIconic(handle):
        raise CaptureError("No visible foreground window is available")
    left, top, right, bottom = win32gui.GetWindowRect(handle)
    if right <= left or bottom <= top:
        raise CaptureError("The foreground window has invalid bounds")
    _, pid = win32process.GetWindowThreadProcessId(handle)
    try:
        application = psutil.Process(pid).name()
    except (psutil.Error, OSError):
        application = None
    return WindowInfo(handle, application, win32gui.GetWindowText(handle), (left, top, right, bottom))


def capture_window(info: WindowInfo) -> Image.Image:
    import mss
    try:
        with mss.mss() as screen:
            virtual = screen.monitors[0]
            left, top, right, bottom = info.bounds
            left, top = max(left, virtual["left"]), max(top, virtual["top"])
            right = min(right, virtual["left"] + virtual["width"])
            bottom = min(bottom, virtual["top"] + virtual["height"])
            if right <= left or bottom <= top:
                raise CaptureError("Foreground window is outside the available monitors")
            shot = screen.grab({"left": left, "top": top, "width": right-left, "height": bottom-top})
            image = Image.frombytes("RGB", shot.size, shot.rgb)
            if all(high - low < 2 for low, high in image.getextrema()):
                raise CaptureError("Capture appears blank or blocked by the application")
            return image
    except CaptureError:
        raise
    except Exception as exc:
        raise CaptureError("Screen capture failed; check desktop permissions and protected content") from exc


def png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
