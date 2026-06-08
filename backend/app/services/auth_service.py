from uuid import uuid4

from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserPublic, UserRecord
from app.security.passwords import hash_password, verify_password
from app.security.tokens import generate_token
from app.services.exceptions import EmailAlreadyExists, InvalidCredentials


class AuthService:
    """Servicio de autenticación: registro y login."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    def register(self, email: str, password: str, username: str) -> UserPublic:
        """Registra un nuevo usuario.

        Lanza EmailAlreadyExists si el email ya existe.
        """
        if self.repo.get_by_email(email) is not None:
            raise EmailAlreadyExists(f"El email ya está registrado: {email}")

        hashed = hash_password(password)
        user = UserRecord(
            id=uuid4().hex,
            email=email,
            username=username,
            hashed_password=hashed,
        )
        self.repo.add(user)
        return UserPublic(id=user.id, email=user.email, username=user.username)

    def get_me(self, user: UserRecord) -> UserPublic:
        """Returns the public profile for an already-resolved user."""
        return UserPublic(id=user.id, email=user.email, username=user.username)

    def login(self, email: str, password: str) -> str:
        """Autentica un usuario y devuelve un token opaco.

        Lanza InvalidCredentials tanto si el email no existe como si
        la contraseña es incorrecta (anti-enumeración).
        """
        user = self.repo.get_by_email(email)
        if user is None:
            raise InvalidCredentials()

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentials()

        token = generate_token()
        self.repo.save_token(token, user.id)
        return token
