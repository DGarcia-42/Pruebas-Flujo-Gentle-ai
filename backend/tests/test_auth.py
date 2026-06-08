"""
Tests de autenticación: unitarios (passwords, tokens) e integración (endpoints).
"""

# =============================================================================
# Tests unitarios — passwords.py
# =============================================================================

from app.security.passwords import hash_password, verify_password


def test_hash_is_different_from_password():
    hashed = hash_password("segura1234")
    assert hashed != "segura1234"


def test_verify_correct_password_returns_true():
    password = "segura1234"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_wrong_password_returns_false():
    hashed = hash_password("segura1234")
    assert verify_password("otra_clave", hashed) is False


def test_two_hashes_of_same_password_are_different():
    password = "segura1234"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    assert hash1 != hash2


# =============================================================================
# Tests unitarios — tokens.py
# =============================================================================

from app.security.tokens import generate_token


def test_generate_token_returns_nonempty_string():
    token = generate_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_two_tokens_are_different():
    assert generate_token() != generate_token()


# =============================================================================
# Tests de integración — endpoints
# =============================================================================

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"

VALID_USER = {
    "email": "nuevo@ejemplo.com",
    "password": "segura1234",
    "username": "Diego",
}


def test_register_creates_user(client):
    response = client.post(REGISTER_URL, json=VALID_USER)
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert "email" in body
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_fails(client):
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(REGISTER_URL, json=VALID_USER)
    assert response.status_code == 409


def test_register_invalid_email(client):
    payload = {**VALID_USER, "email": "no-es-un-email"}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 422


def test_register_short_password(client):
    payload = {**VALID_USER, "password": "corta"}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 422


def test_register_missing_field(client):
    payload = {"email": "nuevo@ejemplo.com", "password": "segura1234"}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 422


def test_login_returns_token(client):
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(
        LOGIN_URL,
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0
    assert body["token_type"] == "bearer"


def test_login_wrong_password_fails(client):
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(
        LOGIN_URL,
        json={"email": VALID_USER["email"], "password": "malaclave"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_login_unknown_email_fails(client):
    response = client.post(
        LOGIN_URL,
        json={"email": "fantasma@ejemplo.com", "password": "cualquiera"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_password_not_stored_in_plaintext(client_with_repo):
    client, repo = client_with_repo
    client.post(REGISTER_URL, json=VALID_USER)
    for user in repo.users_by_email.values():
        for field_value in user.model_dump().values():
            assert "segura1234" not in str(field_value)


# W-01 — LOG-02 / RF-02.4: el token devuelto por login se persiste en el repositorio
def test_login_token_is_stored_in_repo(client_with_repo):
    client, repo = client_with_repo
    reg_response = client.post(REGISTER_URL, json=VALID_USER)
    user_id = reg_response.json()["id"]

    login_response = client.post(
        LOGIN_URL,
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    assert access_token in repo.tokens
    assert repo.tokens[access_token] == user_id


# W-02 — RF-02.1: login con campo faltante devuelve 422
def test_login_missing_field(client):
    response = client.post(LOGIN_URL, json={"email": VALID_USER["email"]})
    assert response.status_code == 422


# =============================================================================
# T-01 — Repository accessors: get_by_token + get_by_id
# =============================================================================

from app.repositories.user_repository import UserRepository as _UserRepository
from app.schemas.auth import UserRecord as _UserRecord


def _make_user(suffix: str = "") -> _UserRecord:
    return _UserRecord(
        id=f"uid{suffix}",
        email=f"user{suffix}@example.com",
        username=f"User{suffix}",
        hashed_password="hashed",
    )


def test_get_by_token_returns_user_when_token_exists():
    repo = _UserRepository()
    user = _make_user("1")
    repo.add(user)
    repo.save_token("tok1", user.id)
    result = repo.get_by_token("tok1")
    assert result is not None
    assert result.id == user.id


def test_get_by_token_returns_none_for_unknown_token():
    repo = _UserRepository()
    result = repo.get_by_token("nope")
    assert result is None


def test_get_by_id_returns_user_when_id_exists():
    repo = _UserRepository()
    user = _make_user("2")
    repo.add(user)
    result = repo.get_by_id(user.id)
    assert result is not None
    assert result.email == user.email


def test_get_by_id_returns_none_for_unknown_id():
    repo = _UserRepository()
    result = repo.get_by_id("does-not-exist")
    assert result is None


# =============================================================================
# T-02 — InvalidCurrentPassword domain exception
# =============================================================================

from app.services.exceptions import InvalidCurrentPassword


def test_invalid_current_password_is_auth_error():
    from app.services.exceptions import AuthError
    exc = InvalidCurrentPassword("wrong")
    assert isinstance(exc, AuthError)


def test_invalid_current_password_can_be_raised_and_caught():
    raised = False
    try:
        raise InvalidCurrentPassword("wrong password")
    except InvalidCurrentPassword:
        raised = True
    assert raised


# =============================================================================
# T-03 — ChangePasswordRequest schema validation
# =============================================================================

from app.schemas.auth import ChangePasswordRequest
import pytest


def test_change_password_request_valid():
    req = ChangePasswordRequest(current_password="oldpass1", new_password="newpass12")
    assert req.current_password == "oldpass1"
    assert req.new_password == "newpass12"


def test_change_password_request_empty_current_password_fails():
    with pytest.raises(Exception):
        ChangePasswordRequest(current_password="", new_password="newpass12")


def test_change_password_request_new_password_too_short_fails():
    with pytest.raises(Exception):
        ChangePasswordRequest(current_password="oldpass1", new_password="short")


def test_change_password_request_new_password_too_long_fails():
    with pytest.raises(Exception):
        ChangePasswordRequest(current_password="oldpass1", new_password="x" * 129)


# =============================================================================
# T-05 — AuthService.get_me
# =============================================================================

from app.services.auth_service import AuthService as _AuthService


def test_get_me_returns_user_public():
    from app.schemas.auth import UserPublic
    repo = _UserRepository()
    user = _make_user("me")
    repo.add(user)
    service = _AuthService(repo)
    result = service.get_me(user)
    assert isinstance(result, UserPublic)
    assert result.id == user.id
    assert result.email == user.email
    assert result.username == user.username


def test_get_me_does_not_expose_password():
    repo = _UserRepository()
    user = _make_user("me2")
    repo.add(user)
    service = _AuthService(repo)
    result = service.get_me(user)
    result_dict = result.model_dump()
    assert "hashed_password" not in result_dict
    assert "password" not in result_dict
