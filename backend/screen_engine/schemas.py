from dataclasses import dataclass

from backend.shared.contracts import ScreenObservation


@dataclass
class CapturedScreen:
    observation: ScreenObservation
    image_bytes: bytes
