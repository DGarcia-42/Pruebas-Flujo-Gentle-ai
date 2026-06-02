# Design: agregar-autenticacion

Diseño técnico (el QUÉ a nivel de arquitectura, no el código ni las tareas). Toda
la narrativa está en español de España; los identificadores y rutas siguen las
convenciones del stack (`snake_case` en Python).

Contexto bloqueado (no se reabre): solo stdlib (`pbkdf2_hmac` para hashing, token
opaco vía `secrets.token_urlsafe`), sin `passlib`/JWT/dependencias nuevas.
Endpoints `POST /api/auth/register` y `POST /api/auth/login`. Respuesta de token
`{"access_token", "token_type": "bearer"}`. La protección de `/api/tasks` queda
**fuera de alcance**. Persistencia **en memoria**.

---

## 1. Estructura de ficheros (greenfield: `backend/` no existe)

```
backend/
├── pyproject.toml                      # deps mínimas (ver §1.1)
├── app/
│   ├── __init__.py
│   ├── main.py                         # crea la app FastAPI, incluye router auth bajo /api
│   ├── dependencies.py                 # singletons + providers Depends (repo, service)
│   ├── routers/
│   │   ├── __init__.py
│   │   └── auth.py                      # rutas register/login (capa HTTP)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py             # registro, login, hashing, emisión token
│   │   └── exceptions.py               # excepciones de dominio (EmailAlreadyExists, InvalidCredentials)
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── user_repository.py          # usuarios + tokens en dicts en memoria
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── auth.py                      # schemas Pydantic v2 + UserRecord interno
│   └── security/
│       ├── __init__.py
│       ├── passwords.py                # hash/verify PBKDF2
│       └── tokens.py                   # generación de token opaco
└── tests/
    ├── __init__.py
    ├── conftest.py                     # fixture de TestClient + reset del repo entre tests
    └── test_auth.py                    # tests TestClient de los flujos
```

Dos ficheros que el enunciado deja a criterio del diseñador y que **sí** se
incluyen, con su justificación:

- **`app/security/passwords.py` y `app/security/tokens.py`**: se confirma la
  ubicación `security/` (no dentro de `services/`). Motivo: son utilidades
  criptográficas **puras y sin estado** (no dependen del repositorio ni de la
  lógica de negocio). Separarlas las hace testeables de forma aislada (semillas
  de test claras), reutilizables por un futuro middleware de protección de
  `/api/tasks` y evita que `auth_service` mezcle "cómo se hashea" con "qué se
  hace al registrar". El servicio las **orquesta**; no reimplementa cripto.

- **`app/services/exceptions.py`**: las excepciones de dominio viven en la capa
  de servicio (ver §5). Se aíslan en su módulo para que router y service las
  importen sin acoplarse al resto de la lógica.

- **`app/dependencies.py`**: centraliza los providers de FastAPI (`Depends`). Es
  el único sitio donde se construye el singleton del repositorio, de modo que el
  reset entre tests tenga un punto único de override (ver §7).

### 1.1 `pyproject.toml` — dependencias

Solo lo imprescindible; cero deps nuevas de runtime respecto al stack ya aprobado:

```toml
[project]
name = "backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "uvicorn",
    "pydantic>=2",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "httpx",   # requerido por starlette.testclient.TestClient
]
```

`hashlib`, `hmac`, `secrets`, `base64` son **stdlib**: no aparecen como
dependencias. `httpx` se declara como dev porque `TestClient` lo necesita por
debajo; no es una dependencia de runtime de la API.

---

## 2. Capas y responsabilidades

Flujo estricto, en una sola dirección, tal como exige `AGENTS.md`:

```
HTTP  ─►  routers/auth.py  ─►  services/auth_service.py  ─►  repositories/user_repository.py
                │                        │                            │
          valida I/O con           orquesta dominio:            dicts en memoria:
          schemas Pydantic         hash, verify, token,         users_by_email,
          traduce excepciones      reglas de negocio            users_by_id, tokens
          de dominio → HTTP
```

- **router** (`auth.py`): única capa que habla HTTP. Recibe el request validado
  por el schema, llama al **service**, y traduce las **excepciones de dominio**
  en `HTTPException` con el `status_code` correcto. Construye la respuesta a
  partir del schema de salida. **El router NUNCA toca el repository** (regla de
  `AGENTS.md`). No conoce hashes, salts ni tokens; solo schemas y excepciones.

- **service** (`auth_service.py`): contiene la lógica de negocio. En `register`:
  comprueba unicidad de email (vía repo), genera salt+hash (vía `security/`),
  persiste el `UserRecord`. En `login`: recupera el usuario por email, verifica
  password (vía `security/`), emite y persiste el token (vía `security/` +
  repo). Lanza **excepciones de dominio**, nunca `HTTPException` (no conoce
  HTTP). No conoce schemas de request/response HTTP; trabaja con tipos internos
  y devuelve datos que el router envuelve.

- **repository** (`user_repository.py`): única capa que persiste. Mantiene los
  diccionarios en memoria, ofrece operaciones CRUD mínimas (`get_by_email`,
  `add`, `save_token`). No conoce reglas de negocio ni cripto; solo guarda y
  recupera. Es el punto que se resetea entre tests.

Las utilidades `security/passwords.py` y `security/tokens.py` son **transversales
y sin estado**: las consume el service. No son una capa de la cadena, son
herramientas (igual que la stdlib).

---

## 3. Schemas Pydantic v2

Todos en `app/schemas/auth.py`. Pydantic v2 (`model_config`, `Field`,
`EmailStr` si se acepta `email-validator`; ver nota). Distinción clave entre los
**schemas de borde HTTP** (request/response) y el **modelo interno** `UserRecord`.

```python
from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserPublic(BaseModel):
    id: str
    email: str
    # NUNCA expone password ni hashed_password

class UserRecord(BaseModel):     # modelo INTERNO de dominio (no se serializa a HTTP)
    id: str
    email: str
    hashed_password: str         # cadena PBKDF2 con formato propio (ver §4)
```

Notas de diseño sobre los schemas:

- **`email` como `str`, no `EmailStr`**: `EmailStr` exige la dependencia
  `email-validator`, que sería una **dep nueva**. Para respetar el contexto
  bloqueado (cero deps nuevas) se usa `str` con `min_length`. Si en el futuro se
  aprueba `email-validator`, basta cambiar el tipo. La unicidad de email es
  responsabilidad del **service** (no de Pydantic).
- **`UserPublic`** existe para garantizar que ninguna respuesta filtre el hash.
  En este alcance los endpoints devuelven `TokenResponse` (no el usuario), pero
  `UserPublic` queda definido para un futuro `GET /api/auth/me` y para los tests
  que comprueben el contenido del repo sin tocar el hash.
- **`UserRecord`** es interno: vive en el repo, lo manipula el service. **Nunca**
  se devuelve directamente por el router. Se modela con Pydantic por consistencia
  con la convención del proyecto ("nada de dicts sueltos en firmas públicas").
- `password` se valida con `min_length=8` (política simple acordada en la
  proposal) y `max_length=128` para acotar el coste de PBKDF2 ante entradas
  abusivas.

---

## 4. Diseño de seguridad

### 4.1 `security/passwords.py` — hashing PBKDF2

- Algoritmo: `hashlib.pbkdf2_hmac("sha256", password_bytes, salt, iterations)`.
- **Salt por usuario**: `secrets.token_bytes(16)` (128 bits) generado en cada
  registro. Nunca compartido entre usuarios.
- **Iteraciones (recomendación OWASP)**: para PBKDF2-HMAC-SHA256 OWASP recomienda
  **600 000 iteraciones**. Se fija como constante `PBKDF2_ITERATIONS = 600_000`.
  Tradeoff: encarece el login (~decenas de ms), aceptable para esta prueba; en un
  sistema real se haría configurable y se reharía el hash al subir el coste.
- **Formato de almacenamiento** (cadena autocontenida, estilo Django/PHC simplificado):

  ```
  pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
  ```

  Ejemplo conceptual: `pbkdf2_sha256$600000$Zm9vYmFy...$2b8c1f...`.
  `salt_b64` y `hash_b64` se codifican con `base64.b64encode(...).decode("ascii")`.
  Ventaja: el hash es autocontenido (algoritmo, coste y salt viajan con él), lo
  que permite verificar sin metadatos externos y migrar el coste en el futuro.

- API del módulo (firmas, sin implementación):

  ```python
  def hash_password(password: str) -> str: ...          # genera salt + devuelve cadena formateada
  def verify_password(password: str, stored: str) -> bool: ...  # parsea la cadena y compara
  ```

- **Verificación**: `verify_password` parsea `stored`, recalcula el hash con el
  mismo salt e iteraciones y compara con **`hmac.compare_digest`** (comparación
  en tiempo constante, mitiga timing attacks). Devuelve `bool`; no lanza por
  password incorrecta (eso lo decide el service).

### 4.2 `security/tokens.py` — token opaco

- Generación: `secrets.token_urlsafe(32)` → ~43 caracteres URL-safe, 256 bits de
  entropía. Token **opaco** (no contiene información del usuario; no es JWT).

  ```python
  def generate_token() -> str:
      return secrets.token_urlsafe(32)
  ```

- El **repositorio** mantiene el mapa `tokens: dict[str, str]` (`token -> user_id`).
  La emisión la orquesta el service: pide el token a `tokens.py` y lo persiste vía
  `repo.save_token(token, user_id)`.
- Sin TTL en este alcance (limitación conocida, §8).

---

## 5. Manejo de errores

Patrón elegido: **el service lanza excepciones de dominio; el router las traduce
a `HTTPException`**. Justificación: mantiene el service ignorante de HTTP (capa de
negocio pura, testeable sin cliente web) y concentra el conocimiento de códigos
de estado en la capa que sí es responsable del protocolo (el router). Es el
patrón idiomático en arquitectura por capas y el que `AGENTS.md` favorece.

Excepciones de dominio (`app/services/exceptions.py`):

```python
class AuthError(Exception): ...
class EmailAlreadyExists(AuthError): ...     # register con email duplicado
class InvalidCredentials(AuthError): ...     # login: password mala O email inexistente
```

Mapa de traducción en el router:

| Situación                               | Excepción de dominio    | Respuesta HTTP                         |
|-----------------------------------------|-------------------------|----------------------------------------|
| Registro con email ya existente         | `EmailAlreadyExists`    | `409 Conflict`                         |
| Login: password incorrecta              | `InvalidCredentials`    | `401 Unauthorized` (mensaje idéntico)  |
| Login: email inexistente                | `InvalidCredentials`    | `401 Unauthorized` (mensaje idéntico)  |
| Body inválido (email corto, sin campos) | — (la lanza Pydantic)   | `422 Unprocessable Entity` (automático)|

Puntos clave:

- **Anti-enumeración**: para password mala y email inexistente el service lanza
  **la misma** `InvalidCredentials`, y el router responde **401 con el mismo
  `detail`** (p. ej. `"Credenciales inválidas"`). Nunca se distingue "ese email
  no existe" de "esa contraseña es incorrecta".
- **422** lo gestiona FastAPI/Pydantic automáticamente al validar el body contra
  el schema; el router no escribe código para ello.
- El formato de error es el de FastAPI por defecto (`{"detail": ...}`), acordado
  en la proposal (sin RFC 7807).
- El router captura las excepciones de dominio y relanza `HTTPException`. Se hará
  con `try/except` explícito en cada handler (claro y local), evitando exception
  handlers globales para este alcance reducido.

---

## 6. Flujos paso a paso entre capas

### 6.1 Flujo `register` (`POST /api/auth/register`)

1. **router**: FastAPI valida el body contra `RegisterRequest` (si falla → 422
   automático). Llama a `service.register(email, password)`.
2. **service**: pide al **repo** `get_by_email(email)`.
   - Si existe → lanza `EmailAlreadyExists`.
3. **service**: llama a `passwords.hash_password(password)` (genera salt+hash,
   devuelve la cadena formateada).
4. **service**: construye un `UserRecord` (id nuevo vía `uuid4().hex`, email,
   `hashed_password`) y lo persiste con `repo.add(user_record)`.
5. **service**: devuelve el usuario creado (o su id/email) al router.
6. **router**: responde **201 Created**. (Cuerpo: en este alcance puede ser
   `UserPublic` del usuario creado o vacío; la spec fija el cuerpo exacto. El
   criterio de éxito de la proposal solo exige 201 + usuario en repo.)
7. Si el service lanzó `EmailAlreadyExists` → el router responde **409**.

### 6.2 Flujo `login` (`POST /api/auth/login`)

1. **router**: FastAPI valida el body contra `LoginRequest` (si falla → 422).
   Llama a `service.login(email, password)`.
2. **service**: pide al **repo** `get_by_email(email)`.
   - Si no existe → lanza `InvalidCredentials`.
3. **service**: llama a `passwords.verify_password(password, user.hashed_password)`.
   - Si es `False` → lanza `InvalidCredentials` (misma excepción que el paso 2).
4. **service**: genera token con `tokens.generate_token()` y lo persiste con
   `repo.save_token(token, user.id)`.
5. **service**: devuelve el token al router.
6. **router**: responde **200 OK** con `TokenResponse(access_token=token,
   token_type="bearer")`.
7. Si el service lanzó `InvalidCredentials` (paso 2 o 3) → el router responde
   **401** con mensaje idéntico.

---

## 7. Inyección de dependencias FastAPI y estado entre tests

El estado en memoria es un **singleton de proceso**. El reto es resetearlo entre
tests para que no se filtren usuarios de un test a otro. Diseño:

### 7.1 Providers (`app/dependencies.py`)

```python
from functools import lru_cache
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository()        # singleton: una sola instancia por proceso

def get_auth_service(
    repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(repo)       # el service recibe el repo por constructor (testeable)
```

- El **repo** es el singleton (vía `lru_cache`): mismo dict para toda la app.
- El **service** se inyecta por `Depends` y recibe el repo por constructor, lo
  que permite construirlo con un repo falso en tests unitarios si hiciera falta.
- El router declara `service: AuthService = Depends(get_auth_service)`. Así el
  router **no construye** ni el service ni el repo (cumple la regla de que el
  router no toca el repo: ni siquiera lo instancia).

### 7.2 Reset del repo entre tests

Dos opciones; se elige la **B** por ser la más limpia y alineada con FastAPI:

- **Opción A (rechazada)**: exponer `repo.clear()` y llamarlo en un fixture
  `autouse`. Funciona, pero obliga al repo a conocer su uso en tests y deja el
  singleton global compartido (riesgo de fugas si algún test crea su propia app).

- **Opción B (elegida) — `dependency_overrides` + fixture por test**: en
  `conftest.py`, un fixture crea una **instancia nueva** de `UserRepository` por
  test y la inyecta vía `app.dependency_overrides[get_user_repository]`. Cada
  test arranca con un repo vacío y aislado; al terminar, se limpia el override.

  ```python
  # conftest.py (esquemático)
  @pytest.fixture
  def client():
      repo = UserRepository()                      # repo limpio por test
      app.dependency_overrides[get_user_repository] = lambda: repo
      with TestClient(app) as c:
          yield c
      app.dependency_overrides.clear()
  ```

  Ventajas: aislamiento total entre tests sin tocar la API de producción, sin
  método `clear()` artificial, y usando el mecanismo idiomático de FastAPI. Como
  `get_user_repository` usa `lru_cache`, el override lo cortocircuita sin que la
  caché interfiera (FastAPI consulta `dependency_overrides` antes de resolver).

Esto hace evidentes los **seams de test** (TDD): se puede testear vía `TestClient`
con repo aislado por test, y opcionalmente testear `AuthService` y los módulos de
`security/` de forma unitaria pura (sin HTTP).

---

## 8. Decisiones de diseño (tradeoffs) y limitaciones conocidas

### Decisiones (estilo ADR resumido)

- **PBKDF2 stdlib en `security/passwords.py` separado del service.**
  Alternativa rechazada: `passlib`/`bcrypt` (dep nueva, prohibida) y meter el
  hashing dentro del service (mezcla cripto con negocio, peor de testear).
  Elegido: módulo puro sin estado → testeable y reutilizable.

- **Cadena de hash autocontenida `pbkdf2_sha256$iter$salt$hash`.**
  Alternativa rechazada: guardar salt/iteraciones en columnas/campos separados
  del `UserRecord` (más acoplamiento, más campos que serializar). Elegido:
  formato único que viaja con el hash y permite migrar el coste sin cambiar el
  modelo.

- **Token opaco persistido `token -> user_id` en el repo.**
  Alternativa rechazada: JWT (dep/firma + complejidad innecesaria; prohibido).
  Elegido: opaco vía `secrets.token_urlsafe`, simple y sin secretos de firma que
  gestionar.

- **Excepciones de dominio en el service, traducción a HTTP en el router.**
  Alternativa rechazada: lanzar `HTTPException` desde el service (acopla negocio
  a HTTP, rompe la testeabilidad pura del service). Elegido: separación de
  responsabilidades por capa.

- **`email: str` en vez de `EmailStr`.**
  Tradeoff: validación de formato de email más laxa, a cambio de **cero deps
  nuevas** (`email-validator`). Aceptado para esta prueba.

- **Inyección con `Depends` + `dependency_overrides` para tests.**
  Alternativa rechazada: variables globales mutables reseteadas a mano. Elegido:
  el mecanismo idiomático de FastAPI, que da aislamiento por test sin ensuciar la
  API de producción.

### Limitaciones conocidas (aceptadas para este alcance)

- **Token sin TTL/expiración**: una vez emitido es válido indefinidamente mientras
  viva el proceso. Riesgo bajo aceptado; TTL queda como evolución futura.
- **Persistencia en memoria**: usuarios y tokens se pierden al reiniciar el
  proceso. Es intencional (la proposal mantiene in-memory; SQLite es futuro).
- **Sin protección de `/api/tasks`**: emitimos token pero aún no hay dependencia
  que lo valide en rutas protegidas (fuera de alcance, depende de la rama de
  Carlos).
- **Coste PBKDF2 fijo**: 600 000 iteraciones fijadas en constante; no se
  reajustan automáticamente ni se rehace el hash al cambiar el coste.
- **Sin revocación/logout**: no hay endpoint para invalidar tokens en este
  alcance.

---

## Cobertura de tests prevista (alineada con la proposal, para `sdd-tasks`)

Los seams del diseño permiten estos tests vía `TestClient` con repo aislado:

- `test_register_creates_user` → 201 y usuario presente en el repo.
- `test_register_duplicate_email_fails` → 409.
- `test_login_returns_token` → 200 con `access_token` y `token_type == "bearer"`.
- `test_login_wrong_password_fails` → 401.
- `test_login_unknown_email_fails` → 401 con **el mismo** `detail` que el anterior.

Opcionalmente, tests unitarios puros de `security/passwords.py`
(`hash != password`, `verify` correcto/incorrecto, salts distintos por usuario) y
de `security/tokens.py` (longitud/unicidad), sin levantar la app.
