from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode
from rxconfig import config

import httpx
import reflex as rx


JOB_STATUS = {
    "QUEUED": "queued",
    "PROCESSING": "processing",
    "COMPLETED": "completed",
    "ERROR": "error",
}

JOB_POLL_INTERVAL_S = 1.5
MAX_POLL_DURATION_S = 120
BACKEND_URL = config.agentic_api_url


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_timestamp(iso_string: str) -> str:
    if not iso_string:
        return ""
    try:
        parsed = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return parsed.strftime("%H:%M")


class AssistantMeta(rx.Base):
    status: str = "approved"
    attempts: int = 1
    reformulated_query: Optional[str] = None
    verifier_feedback: Optional[str] = None
    fallback_label: Optional[str] = None
    attempts_label: Optional[str] = None
    reformulated_label: Optional[str] = None


class ChatMessage(rx.Base):
    id: str
    role: str
    content: str
    created_at: str
    time_label: str
    meta: Optional[AssistantMeta] = None


def create_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def initial_assistant_message() -> ChatMessage:
    created_at = now_iso()
    return ChatMessage(
        id=create_id("assistant"),
        role="assistant",
        content=(
            "Salut ! Je suis l'assistant du Pôle Léonard de Vinci. "
            "Pose tes questions sur la scolarité, les services du campus ou la vie associative."
        ),
        created_at=created_at,
        time_label=format_timestamp(created_at),
    )


class State(rx.State):
    password_input: str = ""
    password: str = ""
    password_error: str = ""
    is_authenticated: bool = False
    new_message: str = ""
    error_message: str = ""
    is_loading: bool = False
    active_job_status: Optional[str] = None
    conversation: list[ChatMessage] = [initial_assistant_message()]
    suggestion_chips: list[str] = [
        "Quels sont les prochains événements associatifs ?",
        "Comment réserver une salle de travail au campus ?",
        "Qui contacter pour une question de scolarité ?",
    ]

    @rx.var
    def job_status_label(self) -> str:
        if self.active_job_status == JOB_STATUS["QUEUED"]:
            return "Message en file d'attente..."
        return "Réflexion en cours..."

    def validate_password(self) -> None:
        if not self.password_input.strip():
            self.password_error = "Le mot de passe est requis."
            return
        self.password = self.password_input.strip()
        self.password_input = ""
        self.password_error = ""
        self.is_authenticated = True

    def reset_conversation(self) -> None:
        self.new_message = ""
        self.error_message = ""
        self.conversation = [initial_assistant_message()]

    def apply_suggestion(self, prompt: str) -> None:
        self.new_message = prompt

    async def request_json(
        self,
        url: str,
        method: str = "GET",
        default_error_message: str = "Une erreur est survenue.",
    ) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.request(
                    method,
                    url,
                    headers={"Content-Type": "application/json"},
                )
        except httpx.RequestError as exc:
            raise RuntimeError(default_error_message) from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code >= 400:
            detail = None
            if isinstance(payload, dict):
                detail = payload.get("detail") or payload.get("error")
            raise RuntimeError(detail or default_error_message)

        return payload if isinstance(payload, dict) else {}

    def backend_base(self) -> str:
        return BACKEND_URL

    def build_job_creation_url(self, message_content: str) -> str:
        query = urlencode({"message": message_content, "password": self.password})
        return f"{self.backend_base()}/message?{query}"

    def build_job_status_url(self, job_id: str) -> str:
        query = urlencode({"password": self.password})
        return f"{self.backend_base()}/message/{job_id}?{query}"

    def build_assistant_meta(self, payload: Optional[Dict[str, Any]]) -> AssistantMeta:
        payload = payload or {}
        status = payload.get("status") or "approved"
        attempts = payload.get("attempts")
        if not isinstance(attempts, int):
            attempts = 1
        reformulated_query = payload.get("reformulated_query")
        verifier_feedback = payload.get("verifier_feedback")
        fallback_label = None
        if status == "fallback":
            fallback_label = "Cette réponse n'a pas pu être validée automatiquement."
            if verifier_feedback:
                fallback_label = f"{fallback_label} Motif : {verifier_feedback}"
        attempts_label = None
        if status == "approved" and attempts > 1:
            attempts_label = f"Validée après {attempts} tentatives."
        reformulated_label = (
            f"Reformulation : {reformulated_query}" if reformulated_query else None
        )
        return AssistantMeta(
            status=status,
            attempts=attempts,
            reformulated_query=reformulated_query or None,
            verifier_feedback=verifier_feedback or None,
            fallback_label=fallback_label,
            attempts_label=attempts_label,
            reformulated_label=reformulated_label,
        )

    def append_message(self, message: ChatMessage) -> None:
        self.conversation = self.conversation + [message]

    async def send_message(self):
        trimmed_message = self.new_message.strip()
        if not trimmed_message or self.is_loading:
            return
        if not self.is_authenticated:
            self.error_message = "Veuillez entrer le mot de passe avant de discuter."
            yield
            return

        created_at = now_iso()
        self.append_message(
            ChatMessage(
                id=create_id("user"),
                role="user",
                content=trimmed_message,
                created_at=created_at,
                time_label=format_timestamp(created_at),
            )
        )
        self.new_message = ""
        self.error_message = ""
        self.is_loading = True
        self.active_job_status = JOB_STATUS["QUEUED"]
        yield

        try:
            job_payload = await self.request_json(
                self.build_job_creation_url(trimmed_message),
                method="POST",
                default_error_message=(
                    "Impossible de mettre en file d'attente votre requête, merci de réessayer."
                ),
            )
            job_id = job_payload.get("job_id")
            if not job_id:
                raise RuntimeError("Réponse invalide du serveur : identifiant de job manquant.")

            deadline = time.monotonic() + MAX_POLL_DURATION_S
            last_status = None
            job_result: Dict[str, Any] = {}

            while time.monotonic() < deadline:
                job_result = await self.request_json(
                    self.build_job_status_url(job_id),
                    default_error_message="Impossible de récupérer l'état du traitement.",
                )
                current_status = job_result.get("status")
                if current_status and current_status != last_status:
                    self.active_job_status = current_status
                    last_status = current_status
                    yield

                if current_status == JOB_STATUS["COMPLETED"]:
                    break
                if current_status == JOB_STATUS["ERROR"]:
                    raise RuntimeError(job_result.get("error") or "La génération a échoué.")
                if current_status in (JOB_STATUS["QUEUED"], JOB_STATUS["PROCESSING"]):
                    await asyncio.sleep(JOB_POLL_INTERVAL_S)
                    continue

                raise RuntimeError("Réponse inattendue du serveur, merci de réessayer.")

            if last_status != JOB_STATUS["COMPLETED"]:
                timeout_message = (
                    "La file d'attente est temporairement saturée, merci de réessayer dans un instant."
                    if last_status == JOB_STATUS["QUEUED"]
                    else "Le délai d'attente a été dépassé, merci de réessayer."
                )
                raise RuntimeError(timeout_message)

            assistant_payload = job_result.get("message")
            if isinstance(assistant_payload, str):
                assistant_payload = {
                    "message": assistant_payload,
                    "created_at": now_iso(),
                    "status": "approved",
                    "attempts": 1,
                }

            if not assistant_payload or not assistant_payload.get("message"):
                raise RuntimeError("Le serveur a terminé sans réponse valide.")

            created_at = assistant_payload.get("created_at") or now_iso()
            self.append_message(
                ChatMessage(
                    id=create_id("assistant"),
                    role="assistant",
                    content=assistant_payload.get("message"),
                    created_at=created_at,
                    time_label=format_timestamp(created_at),
                    meta=self.build_assistant_meta(assistant_payload),
                )
            )
        except Exception as exc:
            message = str(exc) or "Une erreur est survenue pendant la génération."
            self.error_message = message
            created_at = now_iso()
            self.append_message(
                ChatMessage(
                    id=create_id("assistant"),
                    role="assistant",
                    content=f"⚠️ {message}",
                    created_at=created_at,
                    time_label=format_timestamp(created_at),
                    meta=AssistantMeta(
                        status="error",
                        attempts=0,
                        reformulated_query=None,
                        verifier_feedback=message,
                    ),
                )
            )
        finally:
            self.is_loading = False
            self.active_job_status = None
            yield
