# Class To-Do Board

A tiny shared to-do list for teaching **how the internet works**. Every click
sends a message to a server. The **Under the hood** panel describes each one in
plain words, such as **Create: Do Dishes**, **Edit: Do Dishes to Do Laundry**,
**Update: Do Dishes** (ticked or unticked) or **Remove: Do Dishes**. Under each
one it shows:

1. **Sent to the server**: the JSON the browser sent
2. **Received from the server**: the JSON that came back, and how long the round trip took

The JSON is shown in bright vermillion so it stands out on a projector.

The whole class shares one board, so a to-do added on a phone shows up on the
projector within 5 seconds. That shows the data lives on the server, not in
anyone's browser.

## How it fits together

```
Browser ──HTTPS──> Docker container (gunicorn + Flask)
                     ├── /            → React app (static files)
                     └── /api/todos   → plain SQL via psycopg ──TLS──> Postgres (Neon)
```

- `frontend/`: React + Vite + TypeScript. `src/api.ts` wraps `fetch` and records every exchange for the inspector.
- `backend/`: Flask. `app.py` holds the routes, and `db.py` holds the connection and the table. It uses no ORM, so the SQL is easy to read.
- `Dockerfile`: builds React, then copies the files into a small Python image. One image, one URL, one log stream. It runs anywhere Docker runs.

### API

| Method | Path | Success | Errors |
|---|---|---|---|
| `GET` | `/api/todos` | 200 list | |
| `GET` | `/api/todos/<id>` | 200 | 404 |
| `POST` | `/api/todos` `{"title", "author"?}` | 201 | 400, 409 (board full) |
| `PATCH` | `/api/todos/<id>` `{"title"?, "done"?}` | 200 | 400, 404 |
| `DELETE` | `/api/todos/<id>` | 204 | 404 |
| `POST` | `/api/reset` (header `X-Reset-Token`) | 200 | 403, 404 if disabled |
| `GET` | `/api/health` | 200 | |

## Run it locally

### With Docker (easiest)

```bash
docker compose up --build
```

Open http://localhost:8000. Compose starts a local Postgres, so you don't need a Neon account.
To use Neon instead, copy `.env.example` to `.env` and set `DATABASE_URL`. Then start only the app:

```bash
docker compose up --build --no-deps app
```

### Without Docker (for hot reload while editing)

You need a Postgres running somewhere, either local or Neon.

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/todos python app.py
```

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards `/api` to Flask on port 8000.

### Tests

The tests run against a real Postgres. They wipe the `todos` table, so use a throwaway database.

```bash
cd backend
pip install pytest
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/todos pytest
```

## Deploy: Neon + Azure Container Apps

See **[DEPLOY.md](DEPLOY.md)** for the full step-by-step guide. It covers the Neon database, the GitHub image build, Azure Container Apps, live logs, warming the app up before class, shipping updates, costs and troubleshooting.

The short version: push to GitHub, and GitHub Actions builds the image into GHCR. Then create one Azure Container App pointing at that image, with `DATABASE_URL` set to your Neon connection string. Watch the logs with:

```bash
az containerapp logs show -n class-todo -g class-todo-rg --follow --format text
```

## Classroom script (suggestion)

1. Put the site on the projector with the live log stream beside it. Have students open the URL on their phones.
2. A student adds a to-do. Point out **Create** in the panel, the JSON their phone sent, the JSON the server sent back, and the matching line in the server log. The log shows the request came from their phone.
3. Wait 5 seconds and everyone's screen shows it. The data lives on the server, not in your browser.
4. Tick a box (**Update**), rename one (**Edit**), then delete one (**Remove**: the server sends nothing back, it just confirms).
5. Open the browser DevTools → **Network** tab. It shows the same messages: the panel is a friendlier view of what the browser already does.
