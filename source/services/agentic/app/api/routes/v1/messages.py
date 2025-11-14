from datetime import datetime
import os

from dotenv import load_dotenv
from app.models.base_models import MessageModel
from app.services.messages_service import MessagesService
from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/message", description="Send a message.", response_model=MessageModel)
async def create_message(message: str, password: str | None = None):
    load_dotenv()
    if password == os.getenv("PASSWORD", None):
        answer = await MessagesService.send_message(message)

        return MessageModel(
            message=answer,
            created_at=datetime.now()
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong password !")
