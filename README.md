<p align="center">
  <img src="source/front/src/assets/logos/logo.png" alt="Chat'akon logo" width="500" />
</p>

# Chat'akon

[https://chatakon.fr](https://chatakon.fr)

Chat'akon is an AI concierge dedicated to students of the Pôle Léonard de Vinci. It combines a polished Vue 3 interface with an agentic FastAPI backend powered by LangChain, vector search, Supabase Postgres and curated web retrieval. The goal: answer questions about schedules, services, and student life with verifiable facts.

---

## Why Chat'akon?

- **Trusted answers** - Embeddings + SQL queries on curated knowledge, backed by Supabase Postgres.
- **Agentic reasoning** - LangChain tools let the bot cross‑reference stored FAQs, fetch details, and fall back to vetted web results.
- **Human-friendly UX** - Suggestion chips, markdown rendering, and mobile-ready layout crafted with Tailwind.
- **Observability ready** - Langfuse traces every LLM call and tool execution.
- **Deploy anywhere** - Run with Docker Compose or as separate FastAPI/Vite services.

---

## Architecture at a Glance

```
[Vue 3 + Vite Frontend]
        |
        | REST (POST /message)
        v
[FastAPI Agentic service]
   |        |         |
   |        |         +--> Tavily Search (web fallbacks)
   |        +------------> pgvector (Q/A pairs)
   +---------------------> Supabase Postgres (SQL access)
```

---

## Repository Layout

| Path | Description |
| --- | --- |
| `source/front` | Vue 3 + Vite app (Pinia, Tailwind, Font Awesome). |
| `source/services/agentic` | FastAPI service, LangChain agents, tool implementations. |
| `source/docker-compose.yml` | Orchestrates the frontend (nginx) and backend containers. |
| `certification/` | GenAI certificates earned during the hackathon. |
| `demo_video.mp4` & `pitchdeck.pdf` | Demo assets for juries and partners. |

---

## Prerequisites

- Node.js 20+ and npm (for the frontend dev server).
- Python 3.11+ (or Docker) for the FastAPI service.
- Access keys for OpenAI, Langfuse, Supabase and Tavily (see `.env` section).

---

## Quick Start (Docker Compose)

```bash
cd source
cp .env.example .env   # Fill the placeholders
docker compose up --build
```

- Frontend: http://localhost:8080
- API: http://localhost:8001
The nginx container proxies `/api` calls to the FastAPI service. When deploying, set `VITE_BACKEND_URL` to the public API base (e.g., `/api` behind the same domain).

---

## Environment Variables (`source/.env`)

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | LLM used by the LangChain agent (`gpt-4o-mini-2024-07-18` by default). |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | Observability/tracing. |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Access to embeddings (pgvector). |
| `TAVILY_API_KEY` | Web search. |
| `PASSWORD` | Shared secret required both by the frontend modal and the `/message` endpoint. |
| `PYTHONUNBUFFERED` | Keeps FastAPI logs unbuffered inside containers. |

---

## API Reference

`POST /message`
Body parameters:
- `message` *(string, ≤500 chars)* – the user prompt.
- `password` *(string)* - must match the `PASSWORD` env var.

Response:
```jsonc
{
  "message": "Markdown answer rendered in the UI",
  "created_at": "2024-09-26T20:14:55.834Z"
}
```

Example call:

```bash
curl -X POST "http://localhost:8001/message" \
  -H "Content-Type: application/json" \
  -d '{"message":"Quels sont les horaires du Learning Center ?", "password":"<secret>"}'
```

Validation guards prevent prompts longer than 500 characters and reject wrong passwords with HTTP 400.

---

## Frontend Notes

- Authentication is a lightweight gate: users enter the shared password once per session.
- Suggestions (`suggestionChips` in `HomeView.vue`) offer one-click starter topics.
- Responses render with `marked` + `DOMPurify`, enabling links, lists, and inline code safely.
- Conversations persist locally until "Nouvelle discussion" resets the state.

---

## Resources

- Demo video: `demo_video.mp4`
- Pitch deck: `pitchdeck.pdf`
- Certifications: `certification/`

---
