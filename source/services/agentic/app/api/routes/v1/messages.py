import os

from dotenv import load_dotenv
from app.models.base_models import (
    MessageJobCreateResponse,
    MessageJobStatusResponse,
    MessageModel,
)
from app.services.messages_service import MessagesService
from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post(
    "/message",
    description="Queue a message for processing.",
    response_model=MessageJobCreateResponse,
)
async def create_message(message: str, password: str | None = None):
    load_dotenv()
    if password == os.getenv("PASSWORD", None):
        job_id = await MessagesService.enqueue_message(message)
        return MessageJobCreateResponse(job_id=job_id, status="queued")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong password !")


@router.get(
    "/message/{job_id}",
    description="Get the status of a queued message.",
    response_model=MessageJobStatusResponse,
)
async def get_message(job_id: str, password: str | None = None):
    load_dotenv()
    if password != os.getenv("PASSWORD", None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong password !")

    job = await MessagesService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message job not found")

    message_payload = job.get("message")
    message_model = MessageModel(**message_payload) if message_payload else None

    return MessageJobStatusResponse(
        job_id=job_id,
        status=job["status"],
        created_at=job["created_at"],
        finished_at=job.get("finished_at"),
        message=message_model,
        error=job.get("error"),
    )
