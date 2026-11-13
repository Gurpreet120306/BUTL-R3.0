from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScreenObservation(StrictModel):
    application: str | None = None
    window_title: str | None = None
    extracted_text: str = ""
    ui_elements: list[dict] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utcnow)
    capture_status: Literal["success", "partial", "failed"]
    capture_id: str
    warnings: list[str] = Field(default_factory=list)
    source_metadata: dict = Field(default_factory=dict)


class AnalyzedObservation(ScreenObservation):
    observation_id: str | None = None
    ai_summary: str = ""
    important_findings: list[str] = Field(default_factory=list)
    detected_errors: list[str] = Field(default_factory=list)
    analysis_status: Literal["not_requested", "complete", "unavailable", "failed"] = "not_requested"
    analysis_error: str | None = None
    persisted: bool = False
    memory_error: str | None = None


class CaptureRequest(StrictModel):
    include_preview: bool = True


class ScreenResponse(StrictModel):
    observation: AnalyzedObservation
    preview_base64: str | None = None


class VisionResult(StrictModel):
    application: str | None = None
    visible_task: str = ""
    important_ui_elements: list[str] = Field(default_factory=list)
    input_fields: list[str] = Field(default_factory=list)
    ai_summary: str = Field(min_length=1, max_length=6000)
    important_findings: list[str] = Field(default_factory=list)
    detected_errors: list[str] = Field(default_factory=list)


class MemoryList(StrictModel):
    items: list[AnalyzedObservation]


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=4000, pattern=r"\S")


class AssistantAnswer(StrictModel):
    answer: str
    source_observation_ids: list[str] = Field(default_factory=list)
    conversation_id: str | None = None
    memory_error: str | None = None


class ServiceStatus(StrictModel):
    available: bool
    message: str
    models: list[str] = Field(default_factory=list)


class HealthResponse(StrictModel):
    app: str = "BUTL-R"
    status: Literal["ok", "degraded"]
    ollama: ServiceStatus
    mongodb: ServiceStatus


class UserSettings(StrictModel):
    memory_enabled: bool = True
    capture_enabled: bool = True
    screenshot_retention_enabled: bool = False
    selected_ollama_model: str = Field(default="qwen2.5vl:3b", min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.:/-]+$")
    memory_retention_days: int = Field(default=30, ge=0, le=3650)


class SettingsUpdate(StrictModel):
    memory_enabled: bool | None = None
    capture_enabled: bool | None = None
    screenshot_retention_enabled: Literal[False] | None = None
    selected_ollama_model: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.:/-]+$")
    memory_retention_days: int | None = Field(default=None, ge=0, le=3650)


class SettingsResponse(StrictModel):
    settings: UserSettings
    persisted: bool
    warning: str | None = None


class DeleteResult(StrictModel):
    deleted: int


class ModelList(StrictModel):
    models: list[str]
