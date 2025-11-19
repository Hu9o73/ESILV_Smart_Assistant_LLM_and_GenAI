import asyncio
from datetime import datetime, timezone
from typing import ClassVar
from uuid import uuid4

from app.agents.answer_verifier_agent import answer_verifier_agent
from app.agents.orchestrator_agent import orchestrator_agent
from app.agents.query_reformulator_agent import query_reformulator_agent

from fastapi import HTTPException, status
from langfuse.decorators import langfuse_context, observe


class MessagesService:
    MAX_VERIFICATION_ATTEMPTS = 3
    FALLBACK_MESSAGE = (
        "Je n'ai pas pu vérifier une réponse fiable pour le moment. "
        "Merci de contacter la scolarité à scolarite@esilv.com."
    )

    JOB_STATUS_QUEUED = "queued"
    JOB_STATUS_PROCESSING = "processing"
    JOB_STATUS_COMPLETED = "completed"
    JOB_STATUS_ERROR = "error"

    _jobs: ClassVar[dict[str, dict]] = {}
    _job_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _queue: ClassVar[asyncio.Queue[str] | None] = None
    _worker_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _worker_task: ClassVar[asyncio.Task | None] = None

    @classmethod
    async def enqueue_message(cls, user_message: str) -> str:
        cls._validate_message(user_message)
        job_id = str(uuid4())
        timestamp = datetime.now(timezone.utc)
        sanitized_message = user_message.strip()

        job_record = {
            "job_id": job_id,
            "user_message": sanitized_message,
            "status": cls.JOB_STATUS_QUEUED,
            "created_at": timestamp,
            "started_at": None,
            "finished_at": None,
            "message": None,
            "error": None,
        }

        async with cls._job_lock:
            cls._jobs[job_id] = job_record

        await cls._ensure_worker()
        assert cls._queue is not None
        await cls._queue.put(job_id)
        return job_id

    @classmethod
    async def get_job(cls, job_id: str) -> dict | None:
        async with cls._job_lock:
            job = cls._jobs.get(job_id)
            if not job:
                return None
            return cls._public_job_snapshot(job)

    @classmethod
    async def _ensure_worker(cls):
        if cls._queue is None:
            cls._queue = asyncio.Queue()

        if cls._worker_task and not cls._worker_task.done():
            return

        async with cls._worker_lock:
            if cls._worker_task and not cls._worker_task.done():
                return
            cls._worker_task = asyncio.create_task(cls._worker_loop())

    @classmethod
    async def _worker_loop(cls):
        assert cls._queue is not None
        while True:
            job_id = await cls._queue.get()
            try:
                user_message = await cls._mark_job_processing(job_id)
                if user_message is None:
                    continue

                payload = await cls._run_multi_agent(user_message)
                completed_at = datetime.now(timezone.utc)
                payload["created_at"] = completed_at
                await cls._finalize_job(
                    job_id,
                    status=cls.JOB_STATUS_COMPLETED,
                    finished_at=completed_at,
                    message=payload,
                    error=None,
                )
            except asyncio.CancelledError:
                await cls._finalize_job(
                    job_id,
                    status=cls.JOB_STATUS_ERROR,
                    finished_at=datetime.now(timezone.utc),
                    message=None,
                    error="Le traitement a été interrompu.",
                )
                raise
            except Exception as exc:
                await cls._finalize_job(
                    job_id,
                    status=cls.JOB_STATUS_ERROR,
                    finished_at=datetime.now(timezone.utc),
                    message=None,
                    error=str(exc),
                )
            finally:
                cls._queue.task_done()

    @classmethod
    async def _mark_job_processing(cls, job_id: str) -> str | None:
        async with cls._job_lock:
            job = cls._jobs.get(job_id)
            if not job:
                return None
            job["status"] = cls.JOB_STATUS_PROCESSING
            job["started_at"] = datetime.now(timezone.utc)
            return job["user_message"]

    @classmethod
    async def _finalize_job(
        cls,
        job_id: str,
        *,
        status: str,
        finished_at: datetime,
        message: dict | None,
        error: str | None,
    ) -> None:
        async with cls._job_lock:
            job = cls._jobs.get(job_id)
            if job is None:
                return
            job.update(
                {
                    "status": status,
                    "finished_at": finished_at,
                    "message": message,
                    "error": error,
                }
            )

    @staticmethod
    def _public_job_snapshot(job: dict) -> dict:
        snapshot = job.copy()
        snapshot.pop("user_message", None)
        snapshot.pop("started_at", None)
        return snapshot

    @classmethod
    @observe(as_type="generation")
    async def _run_multi_agent(cls, original_question: str) -> dict:
        langfuse_context.update_current_observation(name="Method: Multi-Agent Message")
        langfuse_context.update_current_trace(
            name="Chat",
            input=original_question,
            user_id="Random User",
            session_id="Random Thread",
        )

        last_feedback: str | None = None
        last_reformulation: str | None = None

        for attempt in range(1, cls.MAX_VERIFICATION_ATTEMPTS + 1):
            reformulated_query = await query_reformulator_agent.send_message(original_question)
            last_reformulation = reformulated_query

            orchestrator_response = await orchestrator_agent.send_message(
                original_question=original_question,
                reformulated_query=reformulated_query,
            )

            verdict = await answer_verifier_agent.send_message(
                original_query=original_question,
                reformulated_query=reformulated_query,
                proposed_answer=orchestrator_response,
            )

            verdict_status = verdict.get("status")
            last_feedback = verdict.get("feedback")

            if verdict_status == "approved":
                final_answer = verdict.get("final_answer") or orchestrator_response
                langfuse_context.update_current_trace(output=final_answer)
                return {
                    "message": final_answer,
                    "status": "approved",
                    "attempts": attempt,
                    "reformulated_query": reformulated_query,
                    "verifier_feedback": last_feedback,
                }

        langfuse_context.update_current_trace(output=cls.FALLBACK_MESSAGE)
        return {
            "message": cls.FALLBACK_MESSAGE,
            "status": "fallback",
            "attempts": cls.MAX_VERIFICATION_ATTEMPTS,
            "reformulated_query": last_reformulation,
            "verifier_feedback": last_feedback,
        }

    @staticmethod
    def _validate_message(user_message: str):
        if len(user_message) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question is over 500 characters",
            )
        if not user_message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty",
            )
