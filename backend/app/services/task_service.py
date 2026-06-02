import uuid
from datetime import datetime, timezone

from fastapi import Depends

from app.exceptions import TaskNotFoundError
from app.repositories.task_repository import TaskRepository, get_task_repository
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate


class TaskService:
    """Servicio de lógica de negocio para tareas. Genera IDs y timestamps UTC."""

    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo

    def create(self, data: TaskCreate) -> TaskRead:
        """Crea una tarea nueva con UUID4 y timestamps UTC iguales."""
        now = datetime.now(timezone.utc)
        task = TaskRead(
            id=uuid.uuid4(),
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            created_at=now,
            updated_at=now,
        )
        return self._repo.add(task)

    def get_all(self) -> list[TaskRead]:
        return self._repo.get_all()

    def get(self, task_id: str) -> TaskRead:
        """Devuelve la tarea o lanza TaskNotFoundError."""
        result = self._repo.get(task_id)
        if result is None:
            raise TaskNotFoundError(task_id)
        return result

    def update(self, task_id: str, data: TaskUpdate) -> TaskRead:
        """Actualiza campos presentes y refresca updated_at. Lanza TaskNotFoundError si no existe."""
        existing = self._repo.get(task_id)
        if existing is None:
            raise TaskNotFoundError(task_id)

        changes = data.model_dump(exclude_unset=True)
        changes["updated_at"] = datetime.now(timezone.utc)
        # created_at es inmutable: nunca incluir en changes

        updated = self._repo.update(task_id, changes)
        assert updated is not None  # repo.update devuelve None solo si no existe
        return updated

    def delete(self, task_id: str) -> None:
        """Elimina la tarea. Lanza TaskNotFoundError si no existe."""
        deleted = self._repo.delete(task_id)
        if not deleted:
            raise TaskNotFoundError(task_id)


def get_task_service(
    repo: TaskRepository = Depends(get_task_repository),
) -> TaskService:
    return TaskService(repo=repo)
