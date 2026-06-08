from app.schemas.auth import UserRecord


class UserRepository:
    """Repositorio en memoria para usuarios y tokens."""

    def __init__(self) -> None:
        self.users_by_email: dict[str, UserRecord] = {}
        self.users_by_id: dict[str, UserRecord] = {}
        self.tokens: dict[str, str] = {}

    def get_by_email(self, email: str) -> UserRecord | None:
        return self.users_by_email.get(email)

    def add(self, user: UserRecord) -> None:
        self.users_by_email[user.email] = user
        self.users_by_id[user.id] = user

    def save_token(self, token: str, user_id: str) -> None:
        self.tokens[token] = user_id

    def get_by_token(self, token: str) -> UserRecord | None:
        user_id = self.tokens.get(token)
        if user_id is None:
            return None
        return self.users_by_id.get(user_id)

    def get_by_id(self, user_id: str) -> UserRecord | None:
        return self.users_by_id.get(user_id)
