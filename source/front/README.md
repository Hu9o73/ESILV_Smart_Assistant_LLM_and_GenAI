# Chat'akon Frontend (Reflex)

Reflex (Python) port of the Chat'akon UI. It keeps the password gate, chatbox, markdown rendering, and job polling to the FastAPI agentic backend.

## Local dev

```bash
cd source/front
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
reflex run
```

The app runs on `http://localhost:3000` and the Reflex backend runs on `http://localhost:8000`.

Environment variables:

- `BACKEND_URL` — URL used by Reflex to reach the agentic API (default `http://localhost:8001`).
- `REFLEX_API_URL` — Public URL the browser uses to reach the Reflex backend (default `http://localhost:8000`).

## Docker

Handled by the root `source/docker-compose.yml`.

```bash
cd source
docker compose up --build
```

The frontend is served on `http://localhost:8080` and the Reflex backend is exposed on `http://localhost:8000`.
