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

## Frontend Notes

- Authentication is a lightweight gate: users enter the shared password once per session.
- Suggestions (`suggestionChips` in `HomeView.vue`) offer one-click starter topics.
- Responses render with `marked` + `DOMPurify`, enabling links, lists, and inline code safely.
- Conversations persist locally until "Nouvelle discussion" resets the state.

---
