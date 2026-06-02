import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.dependencies import get_user_repository
from app.repositories.user_repository import UserRepository
from app.repositories.task_repository import TaskRepository, get_task_repository


@pytest.fixture
def client():
    """TestClient con repositorios aislados por test (tareas y usuarios)."""
    application = create_app()
    task_repo = TaskRepository()
    user_repo = UserRepository()
    application.dependency_overrides[get_task_repository] = lambda: task_repo
    application.dependency_overrides[get_user_repository] = lambda: user_repo
    with TestClient(application) as c:
        yield c
    application.dependency_overrides.clear()


@pytest.fixture
def client_with_repo():
    """TestClient que además expone el repositorio de usuarios para inspección directa."""
    application = create_app()
    task_repo = TaskRepository()
    user_repo = UserRepository()
    application.dependency_overrides[get_task_repository] = lambda: task_repo
    application.dependency_overrides[get_user_repository] = lambda: user_repo
    with TestClient(application) as c:
        yield c, user_repo
    application.dependency_overrides.clear()
