from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]


class MessageModel(BaseModel):
    message: str
    created_at: datetime
