from typing import Any
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    profile: dict[str, Any]


class SessionCreate(BaseModel):
    dataset_id: str


class SessionResponse(BaseModel):
    session_id: str
    dataset_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)


class ChatRequest(BaseModel):
    dataset_id: str
    message: str = Field(min_length=1, max_length=10000)
    session_id: str | None = None


class FinalAnswer(BaseModel):
    summary: str = ""
    findings: list[str] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    charts: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    run_id: str
    answer: FinalAnswer
    trace: list[dict[str, Any]] = Field(default_factory=list)


class ReportRequest(BaseModel):
    session_id: str
