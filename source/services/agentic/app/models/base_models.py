from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]


class MessageModel(BaseModel):
    message: str
    created_at: datetime
    status: Literal["approved", "fallback"]
    attempts: int
    reformulated_query: str | None = None
    verifier_feedback: str | None = None


class MessageJobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued"]


class MessageJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "error"]
    created_at: datetime
    finished_at: datetime | None = None
    message: MessageModel | None = None
    error: str | None = None
