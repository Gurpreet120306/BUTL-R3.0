import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"true", "1", "yes"}


def local_url(value: str, schemes: set[str]) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in schemes or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("BUTL-R services must use a loopback address")
    if parsed.username or parsed.password:
        raise ValueError("Credential-bearing service URLs are not supported")
    if parsed.query or parsed.fragment or "," in parsed.netloc:
        raise ValueError("Use a single loopback server without URL query options")
    return value.rstrip("/")


@dataclass(frozen=True)
class Config:
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "butlr_memory")
    ollama_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    vision_model: str = os.getenv("OLLAMA_VISION_MODEL", "qwen2.5vl:3b")
    chat_model: str = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5vl:3b")
    memory_enabled: bool = flag("MEMORY_ENABLED", True)
    capture_enabled: bool = flag("SCREEN_CAPTURE_ENABLED", True)
    retention_days: int = int(os.getenv("MEMORY_RETENTION_DAYS", "30"))
    ollama_timeout: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))
    ollama_max_tokens: int = int(os.getenv("OLLAMA_MAX_OUTPUT_TOKENS", "768"))
    vision_max_dimension: int = int(os.getenv("OLLAMA_VISION_MAX_DIMENSION", "1280"))
    tesseract_cmd: str | None = os.getenv("TESSERACT_CMD")

    def __post_init__(self):
        local_url(self.frontend_origin, {"http"})
        local_url(self.ollama_url, {"http"})
        local_url(self.mongodb_uri, {"mongodb"})
        if flag("AUTO_CAPTURE_ENABLED", False) or flag("STORE_RAW_SCREENSHOTS", False):
            raise ValueError("Automatic capture and raw screenshot storage are disabled in this MVP")
        if not 0 <= self.retention_days <= 3650:
            raise ValueError("MEMORY_RETENTION_DAYS must be between 0 and 3650")
        if not 1 <= self.ollama_timeout <= 3600:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be between 1 and 3600")
        if not 128 <= self.ollama_max_tokens <= 4096:
            raise ValueError("OLLAMA_MAX_OUTPUT_TOKENS must be between 128 and 4096")
        if not 512 <= self.vision_max_dimension <= 4096:
            raise ValueError("OLLAMA_VISION_MAX_DIMENSION must be between 512 and 4096")
