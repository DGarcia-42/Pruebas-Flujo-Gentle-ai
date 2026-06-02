# Tasks: agregar-autenticacion

**Cambio:** agregar-autenticacion
**Fecha:** 2026-06-02
**Modo TDD:** estricto (test-first, pytest + FastAPI TestClient)
**Estado:** completado — 15/15 tests en verde

---

## Convención de este fichero

- Cada tarea de implementación (`IMPL-*`) va siempre precedida por su tarea de
  test (`TEST-*`) en el orden de ejecución.
- Las tareas de un mismo bloque `[paralelo]` pueden hacerse en paralelo porque no
  tienen dependencias entre sí.
- Las tareas de un bloque `[secuencial]` deben completarse en el orden indicado.

---

## Bloque 0 — Andamiaje del proyecto (secuencial)

> Sin infraestructura ningún otro bloque puede ejecutarse. Va primero y es
> condición necesaria para todos los demás.

- [x] **T-00** `SCAFFOLD` — Crear la estructura de directorios `backend/` con
  todos sus `__init__.py` vacíos y el `pyproject.toml` con las dependencias
  mínimas (`fastapi`, `uvicorn`, `pydantic>=2`; dev: `pytest`, `httpx`).
  Archivos afectados: `backend/pyproject.toml`,
  `backend/app/__init__.py`,
  `backend/app/routers/__init__.py`,
  `backend/app/services/__init__.py`,
  `backend/app/repositories/__init__.py`,
  `backend/app/schemas/__init__.py`,
  `backend/app/security/__init__.py`,
  `backend/tests/__init__.py`.
  *Satisface: RNF-01, RNF-03.*

---

## Bloque 1 — Schemas Pydantic (secuencial, tras T-00)

> Los schemas no tienen lógica; se crean antes que cualquier otra capa para que
> las siguientes tareas puedan importarlos.

- [x] **T-01** `IMPL` — Implementar `backend/app/schemas/auth.py` con las
  cinco clases:
  - `RegisterRequest` (email: str `min_length=3 max_length=254`,
    password: str `min_length=8 max_length=128`, username: str `min_length=1`)
  - `LoginRequest` (email: str, password: str)
  - `TokenResponse` (access_token: str, token_type: str = "bearer")
  - `UserPublic` (id: str, email: str) — sin password
  - `UserRecord` (id: str, email: str, hashed_password: str) — modelo interno
  *Satisface: RNF-02, RF-01.1, RF-01.3, RF-01.4, RF-01.6.*

---

## Bloque 2 — Utilidades de seguridad (paralelo entre sí, tras T-01)

> `passwords.py` y `tokens.py` son módulos puros y sin estado; pueden
> desarrollarse en paralelo. Los tests van antes que la implementación.

### 2a — Módulo de contraseñas

- [x] **T-02a-TEST** `TEST` — Escribir en `backend/tests/test_auth.py` (sección
  unitaria, marcada con un comentario separador) los tests de `passwords.py`:
  - El hash resultante de `hash_password` es diferente a la contraseña original.
  - `verify_password(password, hash_password(password))` devuelve `True`.
  - `verify_password("otra", hash_password(password))` devuelve `False`.
  - Dos llamadas a `hash_password` con la misma contraseña producen hashes
    distintos (salts aleatorios).
  *Estos tests fallan en este momento (no existe `passwords.py`).*
  *Satisface: RS-01.1, RS-01.2, RS-01.3.*

- [x] **T-02a-IMPL** `IMPL` — Implementar `backend/app/security/passwords.py`:
  - Constante `PBKDF2_ITERATIONS = 600_000`.
  - `hash_password(password: str) -> str`: genera salt con
    `secrets.token_bytes(16)`, aplica `hashlib.pbkdf2_hmac("sha256", ...)`,
    devuelve cadena `pbkdf2_sha256$<iter>$<salt_b64>$<hash_b64>`.
  - `verify_password(password: str, stored: str) -> bool`: parsea la cadena,
    recalcula el hash y compara con `hmac.compare_digest`. Devuelve bool, no lanza.
  *Los tests de T-02a-TEST deben pasar al completar esta tarea.*
  *Satisface: RS-01.1, RS-01.2, RS-01.3.*

### 2b — Módulo de tokens

- [x] **T-02b-TEST** `TEST` — Escribir en `backend/tests/test_auth.py` (sección
  unitaria) los tests de `tokens.py`:
  - `generate_token()` devuelve una cadena no vacía.
  - Dos llamadas producen valores distintos (unicidad probabilística).
  *Estos tests fallan en este momento (no existe `tokens.py`).*
  *Satisface: RS-02.1, RF-02.3.*

- [x] **T-02b-IMPL** `IMPL` — Implementar `backend/app/security/tokens.py`:
  - `generate_token() -> str`: devuelve `secrets.token_urlsafe(32)`.
  *Los tests de T-02b-TEST deben pasar al completar esta tarea.*
  *Satisface: RS-02.1, RF-02.3.*

---

## Bloque 3 — Excepciones de dominio (secuencial, tras T-00)

> Las excepciones no dependen de los schemas ni de security; pueden crearse en
> paralelo con el Bloque 2, pero deben existir antes del Bloque 4.

- [x] **T-03** `IMPL` — Implementar `backend/app/services/exceptions.py`:
  - `class AuthError(Exception): ...`
  - `class EmailAlreadyExists(AuthError): ...`
  - `class InvalidCredentials(AuthError): ...`
  *No requiere test dedicado; se cubre por los tests de integración del servicio.*
  *Satisface: RNF-01, RNF-04.*

---

## Bloque 4 — Repositorio en memoria (secuencial, tras T-01 y T-03)

> El repositorio necesita `UserRecord` (schema) y no depende de la seguridad.

- [x] **T-04** `IMPL` — Implementar `backend/app/repositories/user_repository.py`:
  - Clase `UserRepository` con atributos en `__init__`:
    `users_by_email: dict[str, UserRecord]`,
    `users_by_id: dict[str, UserRecord]`,
    `tokens: dict[str, str]` (token → user_id).
  - Métodos: `get_by_email(email: str) -> UserRecord | None`,
    `add(user: UserRecord) -> None`,
    `save_token(token: str, user_id: str) -> None`.
  *No requiere test unitario dedicado; se cubre por los tests de integración vía
  `dependency_overrides`.*
  *Satisface: RNF-01, RF-01.7, RF-02.4.*

---

## Bloque 5 — Servicio de autenticación (secuencial, tras bloques 2a, 2b, 3, 4)

> El service es el núcleo de negocio; depende de todas las piezas anteriores.
> Los tests de integración van antes que la implementación.

- [x] **T-05-TEST** `TEST` — Escribir en `backend/tests/conftest.py` el fixture
  `client` con `dependency_overrides`:
  ```python
  # conftest.py (esquemático)
  import pytest
  from fastapi.testclient import TestClient
  from app.main import app
  from app.dependencies import get_user_repository
  from app.repositories.user_repository import UserRepository

  @pytest.fixture
  def client():
      repo = UserRepository()
      app.dependency_overrides[get_user_repository] = lambda: repo
      with TestClient(app) as c:
          yield c
      app.dependency_overrides.clear()
  ```
  *Este fixture falla (la app no existe aún); es la infraestructura de test.*
  *Satisface: RNF-01 (testing idiomático FastAPI).*

- [x] **T-05a-TEST** `TEST` — Escribir el test de integración `test_register_creates_user`
  en `backend/tests/test_auth.py`:
  - `POST /api/auth/register` con datos válidos → respuesta 201.
  - El cuerpo de respuesta NO contiene los campos `password` ni `hashed_password`.
  - El cuerpo contiene `id` y `email` (UserPublic).
  *Falla hasta que existan router, service y el resto del stack.*
  *Satisface: REG-01, RF-01.6, RS-01.4.*

- [x] **T-05b-TEST** `TEST` — Escribir el test de integración `test_register_duplicate_email_fails`:
  - Registrar el mismo email dos veces → segunda llamada devuelve 409.
  *Satisface: REG-02, RF-01.5.*

- [x] **T-05c-TEST** `TEST` — Escribir los tests de validación Pydantic:
  - `test_register_invalid_email` → campo `email` con valor `"no-es-un-email"`
    (sin "@") → 422.
  - `test_register_short_password` → `password: "corta"` (5 chars) → 422.
  - `test_register_missing_field` → body sin el campo `username` → 422.
  *Satisface: REG-03, REG-04, REG-05, RF-01.1, RF-01.2, RF-01.3, RF-01.4.*

- [x] **T-05d-TEST** `TEST` — Escribir los tests de integración de login:
  - `test_login_returns_token` → registrar usuario, luego `POST /api/auth/login` →
    200, cuerpo contiene `access_token` (str no vacío) y `token_type == "bearer"`.
  - `test_login_wrong_password_fails` → 401 con `{"detail": "Credenciales inválidas"}`.
  - `test_login_unknown_email_fails` → 401 con el MISMO `detail` que el anterior.
  *Satisface: LOG-01, LOG-02, LOG-03, LOG-04, RF-02.2, RF-02.5, RF-02.6.*

- [x] **T-05e-TEST** `TEST` — Escribir el test de seguridad `test_password_not_stored_in_plaintext`:
  - Registrar un usuario con contraseña `"segura1234"`, luego inspeccionar el repo
    directamente (fixture alternativo que devuelva también el repo) para verificar
    que ningún campo del `UserRecord` almacenado contiene la cadena `"segura1234"`.
  *Satisface: SEC-01, RF-01.7, RS-01.4.*

---

## Bloque 6 — Implementación del servicio y capas (secuencial, tras todos los TEST del Bloque 5)

> Solo se implementa cuando todos los tests del Bloque 5 estén escritos y en rojo.

- [x] **T-06a** `IMPL` — Implementar `backend/app/services/auth_service.py`:
  - Clase `AuthService` que recibe `UserRepository` por constructor (`__init__`).
  - Método `register(email: str, password: str, username: str) -> UserPublic`:
    llama `get_by_email` → si existe lanza `EmailAlreadyExists`; llama
    `hash_password`; construye `UserRecord` con `uuid4().hex`; llama `repo.add`;
    devuelve `UserPublic`.
  - Método `login(email: str, password: str) -> str` (devuelve token):
    llama `get_by_email` → si None lanza `InvalidCredentials`; llama
    `verify_password` → si False lanza `InvalidCredentials`; llama
    `generate_token`; llama `repo.save_token`; devuelve token.
  *Satisface: RNF-01, RF-01.5, RF-01.7, RF-02.2, RF-02.4, RF-02.5, RF-02.6,
  RS-01.4.*

- [x] **T-06b** `IMPL` — Implementar `backend/app/dependencies.py`:
  - `get_user_repository` decorado con `@lru_cache` → devuelve singleton
    `UserRepository()`.
  - `get_auth_service(repo: UserRepository = Depends(get_user_repository))
    -> AuthService` → devuelve `AuthService(repo)`.
  *Satisface: RNF-01.*

- [x] **T-06c** `IMPL` — Implementar `backend/app/routers/auth.py`:
  - `APIRouter(prefix="/auth", tags=["auth"])`.
  - `POST /register` → recibe `RegisterRequest`, llama `service.register`,
    responde 201 con `UserPublic`; `except EmailAlreadyExists` → `HTTPException(409)`.
  - `POST /login` → recibe `LoginRequest`, llama `service.login`,
    responde 200 con `TokenResponse`; `except InvalidCredentials` →
    `HTTPException(401, detail="Credenciales inválidas")`.
  *Satisface: RF-01.1–RF-01.6, RF-02.1–RF-02.6, RNF-04.*

- [x] **T-06d** `IMPL` — Implementar `backend/app/main.py`:
  - Crea la instancia `app = FastAPI()`.
  - Incluye el router de auth con `app.include_router(auth_router, prefix="/api")`.
  *Satisface: RNF-01.*

---

## Bloque 7 — Verificación final (secuencial, tras Bloque 6)

- [x] **T-07** `VERIFY` — Ejecutar `pytest backend/tests/ -v` y confirmar que los
  11 escenarios pasan en verde:
  - Tests unitarios: T-02a (×4 aserciones), T-02b (×2 aserciones).
  - Tests de integración: REG-01 a REG-05, LOG-01 a LOG-04, SEC-01.
  *Ningún test puede quedar en rojo para dar el cambio por completado.*
  **RESULTADO: 15 passed in 1.82s**

---

## Orden de ejecución sugerido (resumen)

```
T-00
  └─► T-01
        ├─► T-02a-TEST → T-02a-IMPL   [paralelo con 2b]
        ├─► T-02b-TEST → T-02b-IMPL   [paralelo con 2a]
        └─► T-03
              └─► T-04
                    └─► T-05-TEST
                          ├─► T-05a-TEST
                          ├─► T-05b-TEST
                          ├─► T-05c-TEST
                          ├─► T-05d-TEST
                          └─► T-05e-TEST
                                └─► T-06a → T-06b → T-06c → T-06d
                                                              └─► T-07
```

---

## Review Workload Forecast

| Métrica | Valor |
|---|---|
| Archivos nuevos | 14 (pyproject.toml + 9 módulos Python + conftest.py + test_auth.py + 2 __init__ extras) |
| Líneas estimadas de producción | ~200 (passwords ~50, tokens ~10, repo ~40, service ~60, router ~40, main ~15, deps ~20) |
| Líneas estimadas de tests | ~130 (conftest ~20, unit passwords/tokens ~30, integración ~80) |
| **Total líneas estimadas** | **~330** |
| **400-line budget risk** | **Low** |
| **Chained PRs recommended** | **No** |
| **Decision needed before apply** | **No** |

> Todos los archivos son nuevos (greenfield), sin modificaciones a código
> existente. El riesgo de conflictos es mínimo. Un único PR es suficiente.
