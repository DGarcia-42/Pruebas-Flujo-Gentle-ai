"""
Tests de API para el endpoint de tareas.
Cubre escenarios L-1..L-3, C-1..C-8, G-1..G-3, U-1..U-8, D-1..D-5 de la spec crear-api-tareas.
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


# ─── Fase 5.2: GET /api/tasks/{id} (G-1..G-3) ────────────────────────────────

def test_get_task_by_id_returns_200(client: TestClient) -> None:
    """G-1: POST para crear; GET /api/tasks/{id} → 200 con TaskRead completo."""
    create_resp = client.post("/api/tasks", json={"title": "Tarea para obtener"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == task_id


def test_get_task_by_id_body_matches_created(client: TestClient) -> None:
    """G-2: El id en URL coincide con id en body; title y priority coinciden."""
    payload = {"title": "Tarea G-2", "priority": "high"}
    create_resp = client.post("/api/tasks", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    task_id = created["id"]

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == task_id
    assert body["title"] == "Tarea G-2"
    assert body["priority"] == "high"


def test_get_task_nonexistent_returns_404(client: TestClient) -> None:
    """G-3: GET /api/tasks/{uuid_inexistente} → 404 con detail."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/tasks/{random_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


# ─── Fase 5.3: PUT /api/tasks/{id} (U-1..U-8) ────────────────────────────────

def test_put_task_updates_title(client: TestClient) -> None:
    """U-1: POST + PUT {"title": "Actualizado"} → 200, title cambiado, status intacto."""
    create_resp = client.post("/api/tasks", json={"title": "Original", "status": "pending"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    response = client.put(f"/api/tasks/{task_id}", json={"title": "Actualizado"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Actualizado"
    assert body["status"] == "pending"


def test_put_task_updates_status_and_priority(client: TestClient) -> None:
    """U-2: PUT {"status": "done", "priority": "high"} → 200, ambos campos actualizados."""
    create_resp = client.post("/api/tasks", json={"title": "T"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    response = client.put(f"/api/tasks/{task_id}", json={"status": "done", "priority": "high"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["priority"] == "high"
    assert body["title"] == "T"


def test_put_task_empty_body_returns_200(client: TestClient) -> None:
    """U-3: PUT {} → 200, datos conservados."""
    create_resp = client.post("/api/tasks", json={"title": "Original"})
    assert create_resp.status_code == 201
    created = create_resp.json()
    task_id = created["id"]

    response = client.put(f"/api/tasks/{task_id}", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Original"
    assert body["status"] == "pending"
    assert body["priority"] == "medium"


def test_put_task_nonexistent_returns_404(client: TestClient) -> None:
    """U-4: PUT /api/tasks/{uuid_inexistente} → 404."""
    random_id = str(uuid.uuid4())
    response = client.put(f"/api/tasks/{random_id}", json={"title": "X"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_put_task_empty_title_returns_422(client: TestClient) -> None:
    """U-5: PUT {"title": ""} → 422."""
    create_resp = client.post("/api/tasks", json={"title": "T"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    response = client.put(f"/api/tasks/{task_id}", json={"title": ""})
    assert response.status_code == 422


def test_put_task_invalid_status_returns_422(client: TestClient) -> None:
    """U-6: PUT {"status": "cancelado"} → 422."""
    create_resp = client.post("/api/tasks", json={"title": "T"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    response = client.put(f"/api/tasks/{task_id}", json={"status": "cancelado"})
    assert response.status_code == 422


def test_put_task_invalid_priority_returns_422(client: TestClient) -> None:
    """U-7: PUT {"priority": "critica"} → 422."""
    create_resp = client.post("/api/tasks", json={"title": "T"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    response = client.put(f"/api/tasks/{task_id}", json={"priority": "critica"})
    assert response.status_code == 422


def test_put_task_created_at_immutable(client: TestClient) -> None:
    """U-8: created_at en respuesta PUT igual al de POST (inmutable)."""
    create_resp = client.post("/api/tasks", json={"title": "T"})
    assert create_resp.status_code == 201
    created = create_resp.json()
    task_id = created["id"]
    original_created_at = created["created_at"]

    response = client.put(f"/api/tasks/{task_id}", json={"title": "Nuevo"})
    assert response.status_code == 200
    assert response.json()["created_at"] == original_created_at


def test_put_task_id_in_body_is_ignored(client: TestClient) -> None:
    """R-UPDATE-09: un id en el cuerpo del PUT se ignora; el id de la ruta manda."""
    create_resp = client.post("/api/tasks", json={"title": "Original"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    otro_id = str(uuid.uuid4())

    response = client.put(f"/api/tasks/{task_id}", json={"title": "Nuevo", "id": otro_id})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == task_id  # el id del body se descarta: la tarea conserva el suyo
    assert body["id"] != otro_id
    assert body["title"] == "Nuevo"


# ─── Fase 5.4: DELETE /api/tasks/{id} (D-1..D-5) ─────────────────────────────

def test_delete_task_returns_204(client: TestClient) -> None:
    """D-1: POST + DELETE → 204, cuerpo vacío."""
    create_resp = client.post("/api/tasks", json={"title": "A eliminar"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 204
    assert response.content == b""


def test_delete_nonexistent_returns_404(client: TestClient) -> None:
    """D-2: DELETE /api/tasks/{uuid_inexistente} → 404."""
    random_id = str(uuid.uuid4())
    response = client.delete(f"/api/tasks/{random_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_delete_task_removed_from_list(client: TestClient) -> None:
    """D-3: POST + DELETE + GET /api/tasks → array sin la tarea eliminada."""
    create_resp = client.post("/api/tasks", json={"title": "Eliminar de lista"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    client.delete(f"/api/tasks/{task_id}")

    list_resp = client.get("/api/tasks")
    assert list_resp.status_code == 200
    tasks = list_resp.json()
    assert all(t["id"] != task_id for t in tasks)


def test_delete_task_get_by_id_returns_404(client: TestClient) -> None:
    """D-4: POST + DELETE + GET /api/tasks/{id} → 404."""
    create_resp = client.post("/api/tasks", json={"title": "Eliminar por id"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    client.delete(f"/api/tasks/{task_id}")

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 404


def test_delete_task_second_delete_returns_404(client: TestClient) -> None:
    """D-5: POST + DELETE + DELETE (segundo) → 404."""
    create_resp = client.post("/api/tasks", json={"title": "Doble eliminar"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    client.delete(f"/api/tasks/{task_id}")

    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 404
