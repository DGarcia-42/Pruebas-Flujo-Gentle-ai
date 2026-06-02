"""
Tests unitarios del servicio de tareas.
Cubre: R-MOD-05, R-MOD-06, R-CREATE-07, R-CREATE-08, ADR-4, ADR-5, ADR-6.
"""
import uuid
from datetime import timezone

import pytest

from app.exceptions import TaskNotFoundError
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate
from app.services.task_service import TaskService


@pytest.fixture
def service() -> TaskService:
    return TaskService(repo=TaskRepository())


class TestTaskServiceCreate:
    def test_create_returns_task_read(self, service: TaskService) -> None:
        """create devuelve TaskRead con id UUID4 y defaults correctos."""
        data = TaskCreate(title="T")
        result = service.create(data)
        assert result.title == "T"
        assert result.description is None
        assert result.status == TaskStatus.pending
        assert result.priority == TaskPriority.medium
        # Verificar que id es un UUID válido
        parsed = uuid.UUID(str(result.id))
        assert parsed.version == 4

    def test_create_sets_equal_timestamps(self, service: TaskService) -> None:
        """created_at == updated_at en el instante de creación (R-CREATE-08)."""
        result = service.create(TaskCreate(title="T"))
        assert result.created_at == result.updated_at

    def test_create_timestamps_are_utc(self, service: TaskService) -> None:
        """Los timestamps tienen timezone UTC (ADR-5)."""
        result = service.create(TaskCreate(title="T"))
        assert result.created_at.tzinfo is not None
        assert result.created_at.tzinfo.utcoffset(result.created_at).total_seconds() == 0

    def test_two_creates_produce_different_ids(self, service: TaskService) -> None:
        """Dos creates → IDs distintos (R-CREATE-07)."""
        a = service.create(TaskCreate(title="T"))
        b = service.create(TaskCreate(title="T"))
        assert a.id != b.id

    def test_get_all_empty(self, service: TaskService) -> None:
        """get_all sobre servicio vacío → []."""
        assert service.get_all() == []


class TestTaskServiceGet:
    def test_get_existing(self, service: TaskService) -> None:
        """get(id_existente) → TaskRead correcto."""
        created = service.create(TaskCreate(title="T"))
        result = service.get(str(created.id))
        assert result == created

    def test_get_nonexistent_raises(self, service: TaskService) -> None:
        """get(uuid_inexistente) → TaskNotFoundError (ADR-4)."""
        with pytest.raises(TaskNotFoundError):
            service.get(str(uuid.uuid4()))


class TestTaskServiceUpdate:
    def test_update_title(self, service: TaskService) -> None:
        """update con título nuevo → title actualizado."""
        created = service.create(TaskCreate(title="Original"))
        updated = service.update(str(created.id), TaskUpdate(title="Nuevo"))
        assert updated.title == "Nuevo"

    def test_update_refreshes_updated_at(self, service: TaskService) -> None:
        """update → updated_at >= created_at (R-MOD-06)."""
        created = service.create(TaskCreate(title="T"))
        updated = service.update(str(created.id), TaskUpdate(title="X"))
        assert updated.updated_at >= created.created_at

    def test_update_keeps_created_at_immutable(self, service: TaskService) -> None:
        """created_at no cambia tras update (R-MOD-05)."""
        created = service.create(TaskCreate(title="T"))
        updated = service.update(str(created.id), TaskUpdate(title="X"))
        assert updated.created_at == created.created_at

    def test_update_empty_body_refreshes_updated_at(self, service: TaskService) -> None:
        """update con TaskUpdate() → updated_at se actualiza aunque no cambien datos."""
        created = service.create(TaskCreate(title="T"))
        updated = service.update(str(created.id), TaskUpdate())
        assert updated.updated_at >= created.updated_at
        # Campos de datos conservados
        assert updated.title == created.title
        assert updated.status == created.status
        assert updated.priority == created.priority

    def test_update_nonexistent_raises(self, service: TaskService) -> None:
        """update(uuid_inexistente) → TaskNotFoundError."""
        with pytest.raises(TaskNotFoundError):
            service.update(str(uuid.uuid4()), TaskUpdate(title="X"))


class TestTaskServiceDelete:
    def test_delete_existing(self, service: TaskService) -> None:
        """delete(id_existente) → sin excepción; get posterior lanza."""
        created = service.create(TaskCreate(title="T"))
        service.delete(str(created.id))
        with pytest.raises(TaskNotFoundError):
            service.get(str(created.id))

    def test_delete_nonexistent_raises(self, service: TaskService) -> None:
        """delete(uuid_inexistente) → TaskNotFoundError."""
        with pytest.raises(TaskNotFoundError):
            service.delete(str(uuid.uuid4()))
