from app.schemas.task import TaskRead


class TaskRepository:
    """Repositorio in-memory para tareas. Cada instancia tiene su propio estado."""

    def __init__(self) -> None:
        self._items: dict[str, TaskRead] = {}

    def get_all(self) -> list[TaskRead]:
        return list(self._items.values())

    def get(self, task_id: str) -> TaskRead | None:
        return self._items.get(task_id)

    def add(self, task: TaskRead) -> TaskRead:
        self._items[str(task.id)] = task
        return task

    def update(self, task_id: str, data: dict) -> TaskRead | None:
        existing = self._items.get(task_id)
        if existing is None:
            return None
        updated = existing.model_copy(update=data)
        self._items[task_id] = updated
        return updated

    def delete(self, task_id: str) -> bool:
        if task_id not in self._items:
            return False
        del self._items[task_id]
        return True


# Singleton de módulo (ADR-2)
_repository = TaskRepository()


def get_task_repository() -> TaskRepository:
    return _repository
