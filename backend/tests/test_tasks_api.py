"""
Tests de API para el endpoint de tareas.
Cubre escenarios L-1..L-3, C-1..C-8 de la spec crear-api-tareas.
"""
import uuid

import pytest
from fastapi.testclient import TestClient


# ─── Fase 0 / Fase 4: smoke test (L-1) ───────────────────────────────────────

def test_get_tasks_returns_empty_list(client: TestClient) -> None:
    """L-1: Sin tareas en el sistema → 200 con array vacío."""
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json() == []


# ─── Fase 5.1: POST /api/tasks (C-1..C-8) ────────────────────────────────────

def test_create_task_minimal_title_returns_201(client: TestClient) -> None:
    """C-1: POST con solo título → 201 y TaskRead con defaults."""
    response = client.post("/api/tasks", json={"title": "Mi primera tarea"})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Mi primera tarea"
    assert body["description"] is None
    assert body["status"] == "pending"
    assert body["priority"] == "medium"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    # id debe ser un UUID4 válido
    parsed = uuid.UUID(body["id"])
    assert parsed.version == 4


def test_create_task_all_fields_returns_201(client: TestClient) -> None:
    """C-2: POST con todos los campos → 201 y body refleja valores enviados."""
    payload = {
        "title": "T",
        "description": "Desc",
        "status": "in_progress",
        "priority": "high",
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "T"
    assert body["description"] == "Desc"
    assert body["status"] == "in_progress"
    assert body["priority"] == "high"


def test_create_task_created_at_equals_updated_at(client: TestClient) -> None:
    """C-1/R-CREATE-08: created_at == updated_at en la creación."""
    response = client.post("/api/tasks", json={"title": "T"})
    assert response.status_code == 201
    body = response.json()
    assert body["created_at"] == body["updated_at"]


def test_create_task_two_posts_produce_different_ids(client: TestClient) -> None:
    """C-8: Dos POSTs → IDs distintos (R-CREATE-07)."""
    r1 = client.post("/api/tasks", json={"title": "T"})
    r2 = client.post("/api/tasks", json={"title": "T"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]


def test_create_task_missing_title_returns_422(client: TestClient) -> None:
    """C-3: body {} sin title → 422."""
    response = client.post("/api/tasks", json={})
    assert response.status_code == 422


def test_create_task_empty_title_returns_422(client: TestClient) -> None:
    """C-4: title='' → 422."""
    response = client.post("/api/tasks", json={"title": ""})
    assert response.status_code == 422


def test_create_task_null_title_returns_422(client: TestClient) -> None:
    """C-5: title=null → 422."""
    response = client.post("/api/tasks", json={"title": None})
    assert response.status_code == 422


def test_create_task_invalid_status_returns_422(client: TestClient) -> None:
    """C-6: status='borrador' → 422."""
    response = client.post("/api/tasks", json={"title": "T", "status": "borrador"})
    assert response.status_code == 422


def test_create_task_invalid_priority_returns_422(client: TestClient) -> None:
    """C-7: priority='urgente' → 422."""
    response = client.post("/api/tasks", json={"title": "T", "priority": "urgente"})
    assert response.status_code == 422


# ─── Fase 5.1.3: L-2 y L-3 (tarea creada aparece en listado) ─────────────────

def test_created_task_appears_in_list(client: TestClient) -> None:
    """L-2/L-3: POST + GET /api/tasks → array contiene la tarea creada."""
    create_resp = client.post("/api/tasks", json={"title": "Tarea visible"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    list_resp = client.get("/api/tasks")
    assert list_resp.status_code == 200
    tasks = list_resp.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == task_id
    assert tasks[0]["title"] == "Tarea visible"
    assert tasks[0]["status"] == "pending"
    assert tasks[0]["priority"] == "medium"
