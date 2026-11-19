"""CRUD tests. They need a real Postgres: set TEST_DATABASE_URL.

    TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres pytest
"""

import os
import sys
from pathlib import Path

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")
if not TEST_DB:
    pytest.skip("TEST_DATABASE_URL not set", allow_module_level=True)

os.environ["DATABASE_URL"] = TEST_DB
os.environ["MAX_TODOS"] = "3"
os.environ["RESET_TOKEN"] = "secret"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db  # noqa: E402
from app import create_app  # noqa: E402


@pytest.fixture()
def client():
    app = create_app()
    db.ensure_schema()
    with db.connect() as conn:
        conn.execute("TRUNCATE todos RESTART IDENTITY")
    return app.test_client()


def test_create_and_list(client):
    res = client.post("/api/todos", json={"title": "  Buy milk ", "author": "Sam"})
    assert res.status_code == 201
    todo = res.get_json()
    assert todo["title"] == "Buy milk"
    assert todo["author"] == "Sam"
    assert todo["done"] is False

    res = client.get("/api/todos")
    assert res.status_code == 200
    assert [t["title"] for t in res.get_json()] == ["Buy milk"]


def test_get_one_and_404(client):
    todo_id = client.post("/api/todos", json={"title": "A"}).get_json()["id"]
    assert client.get(f"/api/todos/{todo_id}").get_json()["title"] == "A"
    res = client.get("/api/todos/9999")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_create_validation(client):
    assert client.post("/api/todos", json={"title": ""}).status_code == 400
    assert client.post("/api/todos", json={}).status_code == 400
    assert client.post("/api/todos", json={"title": "x" * 201}).status_code == 400
    assert client.post("/api/todos", data="not json").status_code == 400


def test_update(client):
    todo_id = client.post("/api/todos", json={"title": "A"}).get_json()["id"]
    res = client.patch(f"/api/todos/{todo_id}", json={"done": True, "title": "B"})
    assert res.status_code == 200
    assert res.get_json()["done"] is True
    assert res.get_json()["title"] == "B"

    assert client.patch(f"/api/todos/{todo_id}", json={"done": "yes"}).status_code == 400
    assert client.patch(f"/api/todos/{todo_id}", json={}).status_code == 400
    assert client.patch("/api/todos/9999", json={"done": True}).status_code == 404


def test_delete(client):
    todo_id = client.post("/api/todos", json={"title": "A"}).get_json()["id"]
    assert client.delete(f"/api/todos/{todo_id}").status_code == 204
    assert client.delete(f"/api/todos/{todo_id}").status_code == 404
    assert client.get("/api/todos").get_json() == []


def test_board_full(client):
    for i in range(3):
        assert client.post("/api/todos", json={"title": str(i)}).status_code == 201
    assert client.post("/api/todos", json={"title": "too many"}).status_code == 409


def test_reset(client):
    client.post("/api/todos", json={"title": "A"})
    assert client.post("/api/reset").status_code == 403
    res = client.post("/api/reset", headers={"X-Reset-Token": "secret"})
    assert res.status_code == 200
    assert client.get("/api/todos").get_json() == []


def test_unknown_api_route_and_method(client):
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/nope").is_json
    assert client.put("/api/todos").status_code == 405
