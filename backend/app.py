
import json
import logging
import os
import sys
import time
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

import db

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("showcase")

STATIC_DIR = Path(__file__).parent / "static"
MAX_TITLE = 200
MAX_AUTHOR = 40
COLUMNS = "id, title, done, author, created_at, updated_at"


def serialize(row: dict) -> dict:
    return {
        **row,
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def error(status: int, message: str):
    return jsonify({"error": message}), status


def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or request.remote_addr or "?"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    max_todos = int(os.environ.get("MAX_TODOS", "200"))
    reset_token = os.environ.get("RESET_TOKEN", "")

    # ------------------------------------------------------------------ hooks
    @app.before_request
    def start_timer():
        g.start = time.perf_counter()
        if request.path.startswith("/api/") and request.path != "/api/health":
            db.ensure_schema()

    @app.after_request
    def log_request(response):
        if request.path.startswith("/api/"):
            ms = (time.perf_counter() - g.get("start", time.perf_counter())) * 1000
            line = f"{request.method} {request.path} {response.status_code} {ms:.0f}ms ip={client_ip()}"
            body = request.get_json(silent=True)
            if isinstance(body, dict) and body:
                line += " body=" + json.dumps(body, ensure_ascii=False)[:200]
            log.info(line)
        return response

    app.teardown_appcontext(db.close_conn)

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        if request.path.startswith("/api/"):
            return error(exc.code or 500, exc.description or exc.name)
        return exc

    @app.errorhandler(Exception)
    def unexpected_error(exc: Exception):
        log.exception("Unhandled error")
        return error(500, "Something went wrong on the server")

    # ------------------------------------------------------------------- API
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/todos")
    def list_todos():
        rows = db.run(f"SELECT {COLUMNS} FROM todos ORDER BY created_at, id")
        return jsonify([serialize(r) for r in rows])

    @app.get("/api/todos/<int:todo_id>")
    def get_todo(todo_id: int):
        rows = db.run(f"SELECT {COLUMNS} FROM todos WHERE id = %s", (todo_id,))
        if not rows:
            return error(404, f"There is no to-do with id {todo_id}")
        return jsonify(serialize(rows[0]))

    @app.post("/api/todos")
    def create_todo():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error(400, "Send a JSON object, e.g. {\"title\": \"Buy milk\"}")

        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            return error(400, "A to-do needs a non-empty \"title\"")
        title = title.strip()
        if len(title) > MAX_TITLE:
            return error(400, f"Title must be at most {MAX_TITLE} characters")

        author = data.get("author")
        if author is not None and not isinstance(author, str):
            return error(400, "\"author\" must be text")
        author = (author or "").strip()[:MAX_AUTHOR] or None

        count = db.run("SELECT count(*) AS n FROM todos")[0]["n"]
        if count >= max_todos:
            return error(409, f"The board is full ({max_todos} to-dos). Delete some first.")

        rows = db.run(
            f"INSERT INTO todos (title, author) VALUES (%s, %s) RETURNING {COLUMNS}",
            (title, author),
        )
        return jsonify(serialize(rows[0])), 201

    @app.patch("/api/todos/<int:todo_id>")
    def update_todo(todo_id: int):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error(400, "Send a JSON object, e.g. {\"done\": true}")

        sets, params = [], []
        if "title" in data:
            title = data["title"]
            if not isinstance(title, str) or not title.strip():
                return error(400, "\"title\" cannot be empty")
            if len(title.strip()) > MAX_TITLE:
                return error(400, f"Title must be at most {MAX_TITLE} characters")
            sets.append("title = %s")
            params.append(title.strip())
        if "done" in data:
            if not isinstance(data["done"], bool):
                return error(400, "\"done\" must be true or false")
            sets.append("done = %s")
            params.append(data["done"])
        if not sets:
            return error(400, "Nothing to update: send \"title\" and/or \"done\"")

        sets.append("updated_at = now()")
        rows = db.run(
            f"UPDATE todos SET {', '.join(sets)} WHERE id = %s RETURNING {COLUMNS}",
            (*params, todo_id),
        )
        if not rows:
            return error(404, f"There is no to-do with id {todo_id}")
        return jsonify(serialize(rows[0]))

    @app.delete("/api/todos/<int:todo_id>")
    def delete_todo(todo_id: int):
        rows = db.run("DELETE FROM todos WHERE id = %s RETURNING id", (todo_id,))
        if not rows:
            return error(404, f"There is no to-do with id {todo_id}")
        return "", 204

    @app.post("/api/reset")
    def reset_board():
        """Teacher-only: wipe the board between classes."""
        if not reset_token:
            return error(404, "Reset is not enabled on this server")
        if request.headers.get("X-Reset-Token") != reset_token:
            return error(403, "Wrong reset token")
        db.run("TRUNCATE todos RESTART IDENTITY")
        return jsonify({"status": "board cleared"})

    @app.get("/")
    @app.get("/<path:path>")
    def frontend(path: str = ""):
        if path.startswith("api/"):
            return error(404, "Unknown API route")
        if not (STATIC_DIR / "index.html").exists():
            return "Frontend not built. Run the Vite dev server or build the Docker image.", 404
        if path and (STATIC_DIR / path).is_file():
            return send_from_directory(STATIC_DIR, path)
        return send_from_directory(STATIC_DIR, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=True)
