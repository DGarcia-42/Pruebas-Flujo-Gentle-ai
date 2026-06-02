from fastapi import APIRouter, Depends

from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
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


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: str, service: TaskService = Depends(get_task_service)) -> TaskRead:
    """G-1..G-3: Devuelve la tarea por id o 404 si no existe."""
    return service.get(task_id)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str,
    data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """U-1..U-8: Actualiza parcialmente la tarea o 404 si no existe."""
    return service.update(task_id, data)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, service: TaskService = Depends(get_task_service)) -> None:
    """D-1..D-5: Elimina la tarea (204) o 404 si no existe."""
    service.delete(task_id)
