import re
import secrets

from fastapi import HTTPException, Request

# Heuristics only: images may still expose secrets. Images are never persisted.
PATTERNS = [
    (re.compile(r"(?i)\b(password|passwd|pwd|api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*[^\s,;]+"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b"), "[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "[REDACTED]"),
    (re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.S), "[REDACTED PRIVATE KEY]"),
]


def redact(text: str) -> str:
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_value(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_value(x) for x in value]
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    return value


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin != request.app.state.config.frontend_origin:
        raise HTTPException(403, "Request requires the configured local frontend Origin")
    # localhost → 127.0.0.1 is classified cross-site by browsers. The exact
    # configured Origin is authoritative; rejecting that fetch breaks the defaults.


def require_session(request: Request) -> None:
    check_origin(request)
    token = request.headers.get("x-butlr-token", "")
    if not secrets.compare_digest(token, request.app.state.session_token):
        raise HTTPException(403, "Local session token is missing or expired; reload BUTL-R")
