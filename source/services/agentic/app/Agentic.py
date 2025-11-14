from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.v1.messages import router as message_router

app = FastAPI(title="Agentic API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(message_router, tags=["Messages"])
