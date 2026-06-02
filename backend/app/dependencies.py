from functools import lru_cache

from fastapi import Depends

from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


@lru_cache
def get_user_repository() -> UserRepository:
    """Singleton del repositorio de usuarios (un dict en memoria por proceso)."""
    return UserRepository()


def get_auth_service(
    repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    """Proveedor del servicio de autenticación."""
    return AuthService(repo)
