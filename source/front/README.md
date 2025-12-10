# Chat'akon Frontend (Next.js)

Next.js + Tailwind rewrite of the Chat'akon UI. It keeps the password gate, chatbox, markdown rendering, and `/api/message` polling to the FastAPI agentic backend.

## Local dev

```bash
cd source/front
npm install
npm run dev
```

The app runs on `http://localhost:3000`.

Environment variables (see `.env.example`):

- `NEXT_PUBLIC_BACKEND_URL` — Base URL the browser uses to hit the agentic API (default `/api` so the frontend can proxy).
- `BACKEND_URL` — Internal URL used by Next.js rewrites to proxy `/api/*` to the FastAPI container (default `http://chatakon-agentic:8001` for Docker).

## Docker

Handled by the root `source/docker-compose.yml`. Build args/env for the frontend mirror the two variables above.

```bash
cd source
docker compose up --build
```

The frontend is served on `http://localhost:8080` and proxies `/api/*` to the backend.
