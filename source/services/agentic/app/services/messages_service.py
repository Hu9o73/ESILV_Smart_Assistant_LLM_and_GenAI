from app.agents.basic_agent import basic_agent

from fastapi import HTTPException, status

class MessagesService:
    @staticmethod
    async def send_message(user_message: str) -> str:
        if len(user_message) > 500:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question is over 500 characters")
        return await basic_agent.send_message(user_message)
