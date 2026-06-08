from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_auth_service, get_current_user
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
    UserRecord,
)
from app.services.auth_service import AuthService
from app.services.exceptions import EmailAlreadyExists, InvalidCredentials, InvalidCurrentPassword

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS_DETAIL = "Credenciales inválidas"


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> None:
    """Changes the authenticated user's password. Returns 204 No Content on success."""
    try:
        service.change_password(
            current_user,
            body.current_password,
            body.new_password,
        )
    except InvalidCurrentPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta",
        )


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserPublic:
    """Registra un nuevo usuario. Devuelve 201 con los datos públicos del usuario."""
    try:
        return service.register(
            email=body.email,
            password=body.password,
            username=body.username,
        )
    except EmailAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado",
        )


@router.get("/me", response_model=UserPublic, status_code=status.HTTP_200_OK)
def get_me(
    current_user: UserRecord = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserPublic:
    """Returns the public profile of the authenticated user."""
    return service.get_me(current_user)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Autentica un usuario y devuelve un token opaco."""
    try:
        token = service.login(email=body.email, password=body.password)
        return TokenResponse(access_token=token)
    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_CREDENTIALS_DETAIL,
        )
