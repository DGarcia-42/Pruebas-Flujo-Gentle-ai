from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status

from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRecord
from app.services.auth_service import AuthService

_INVALID_CREDENTIALS_DETAIL = "Credenciales inválidas"


@lru_cache
def get_user_repository() -> UserRepository:
    """Singleton del repositorio de usuarios (un dict en memoria por proceso)."""
    return UserRepository()


def get_auth_service(
    repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    """Proveedor del servicio de autenticación."""
    return AuthService(repo)


def get_current_user(
    authorization: str | None = Header(default=None),
    repo: UserRepository = Depends(get_user_repository),
) -> UserRecord:
    """Dependency that resolves a Bearer token to a UserRecord.

    Raises 401 for missing header, malformed header, unknown token,
    or unknown user_id — all with the same message (anti-enumeration).
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_INVALID_CREDENTIALS_DETAIL,
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization:
        raise credentials_error

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise credentials_error

    token = parts[1].strip()
    user = repo.get_by_token(token)
    if user is None:
        raise credentials_error

    return user
