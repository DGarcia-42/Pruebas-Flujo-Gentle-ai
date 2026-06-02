from fastapi import APIRouter, Depends

from app.schemas.task import TaskCreate, TaskRead
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(service: TaskService = Depends(get_task_service)) -> list[TaskRead]:
    """L-1, L-2, L-3: Lista todas las tareas existentes."""
    return service.get_all()


@router.post("", status_code=201, response_model=TaskRead)
def create_task(
    data: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """C-1..C-8: Crea una nueva tarea y devuelve 201 con TaskRead."""
    return service.create(data)
