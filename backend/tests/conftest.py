import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_user_repository
from app.repositories.user_repository import UserRepository


@pytest.fixture
def client():
    """TestClient con un repositorio aislado por test."""
    repo = UserRepository()
    app.dependency_overrides[get_user_repository] = lambda: repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_repo():
    """TestClient que también expone el repositorio para inspección directa."""
    repo = UserRepository()
    app.dependency_overrides[get_user_repository] = lambda: repo
    with TestClient(app) as c:
        yield c, repo
    app.dependency_overrides.clear()
