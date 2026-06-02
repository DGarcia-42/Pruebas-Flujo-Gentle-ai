import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.task_repository import TaskRepository, get_task_repository


@pytest.fixture
def client():
    application = create_app()
    repo = TaskRepository()
    application.dependency_overrides[get_task_repository] = lambda: repo
    with TestClient(application) as c:
        yield c
    application.dependency_overrides.clear()
