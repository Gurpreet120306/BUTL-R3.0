import time


def extract_ui(handle: int, limit: int = 300) -> tuple[list[dict], list[str]]:
    # Each asyncio worker thread needs its own COM initialization.
    com = None
    try:
        import pythoncom
        com = pythoncom
        com.CoInitialize()
        return _extract_ui(handle, limit)
    except Exception:
        return [], ["Accessibility unavailable for this window; OCR and vision remain available"]
    finally:
        if com is not None:
            com.CoUninitialize()


def _extract_ui(handle: int, limit: int = 300) -> tuple[list[dict], list[str]]:
    """Best effort UIA extraction; never read password edit controls."""
    try:
        from pywinauto import Desktop
        root = Desktop(backend="uia").window(handle=handle)
        queue = [root.wrapper_object()]
        controls, warnings = [], []
        deadline = time.monotonic() + 4
        while queue and len(controls) < limit and time.monotonic() < deadline:
            control = queue.pop(0)
            try:
                info = control.element_info
                if not info.visible:
                    continue
                protected = bool(info.element.CurrentIsPassword)
                # Names/values of password controls are excluded entirely.
                if protected:
                    controls.append({"control_type": "Edit", "name": "[PASSWORD FIELD]", "protected": True})
                    continue
                name = info.name or ""
                if name:
                    controls.append({"control_type": info.control_type, "name": name[:1000]})
                queue.extend(control.children()[:limit])
            except Exception:
                continue
        if queue:
            warnings.append("Accessibility traversal was bounded; some controls were omitted")
        return controls, warnings
    except Exception:
        return [], ["Accessibility unavailable for this window; OCR and vision remain available"]
