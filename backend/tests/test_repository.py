"""
Tests unitarios del repositorio in-memory.
Cubre ADR-2 (singleton, self._items), ADR-4 (devuelve None, no lanza).
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskPriority, TaskRead, TaskStatus


def _make_task(title: str = "Test") -> TaskRead:
    now = datetime.now(timezone.utc)
    return TaskRead(
        id=uuid.uuid4(),
        title=title,
        description=None,
        status=TaskStatus.pending,
        priority=TaskPriority.medium,
        created_at=now,
        updated_at=now,
    )


class TestTaskRepository:
    def test_get_all_empty(self) -> None:
        """Repositorio vacío → get_all devuelve []."""
        repo = TaskRepository()
        assert repo.get_all() == []

    def test_add_and_get_all(self) -> None:
        """add(task) → la tarea aparece en get_all."""
        repo = TaskRepository()
        task = _make_task()
        returned = repo.add(task)
        assert returned == task
        assert task in repo.get_all()

    def test_get_existing(self) -> None:
        """get(id_existente) → devuelve TaskRead."""
        repo = TaskRepository()
        task = _make_task()
        repo.add(task)
        result = repo.get(str(task.id))
        assert result == task

    def test_get_nonexistent_returns_none(self) -> None:
        """get(id_inexistente) → None."""
        repo = TaskRepository()
        result = repo.get(str(uuid.uuid4()))
        assert result is None

    def test_update_existing(self) -> None:
        """update(id, data) → devuelve TaskRead actualizado."""
        repo = TaskRepository()
        task = _make_task()
        repo.add(task)
        updated = repo.update(str(task.id), {"title": "Nuevo"})
        assert updated is not None
        assert updated.title == "Nuevo"

    def test_update_nonexistent_returns_none(self) -> None:
        """update(id_inexistente, ...) → None."""
        repo = TaskRepository()
        result = repo.update(str(uuid.uuid4()), {"title": "X"})
        assert result is None

    def test_delete_existing(self) -> None:
        """delete(id) → True; get(id) → None."""
        repo = TaskRepository()
        task = _make_task()
        repo.add(task)
        result = repo.delete(str(task.id))
        assert result is True
        assert repo.get(str(task.id)) is None

    def test_delete_nonexistent_returns_false(self) -> None:
        """delete(id_inexistente) → False."""
        repo = TaskRepository()
        result = repo.delete(str(uuid.uuid4()))
        assert result is False
