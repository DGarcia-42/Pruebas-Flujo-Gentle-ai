# Spec: user-auth
**Capability:** user-auth — registro y login con token opaco
**Fecha:** 2026-06-02
**Estado:** aprobado

---

## Contexto

Esta spec describe el contrato observable (qué debe ser cierto) de la capacidad de autenticación del usuario en el backend. No describe implementación interna; eso pertenece al artefacto de diseño.

Todos los endpoints viven bajo el prefijo `/api`. Las contraseñas nunca viajan hacia afuera del sistema ni se almacenan en claro.

---

## Requisitos funcionales

### RF-01 — Registro de usuario (`POST /api/auth/register`)

**RF-01.1** La petición DEBE contener los campos `email`, `password` y `username`.
Los tres son obligatorios; la ausencia de cualquiera devuelve 422.

**RF-01.2** El campo `email` DEBE ser una dirección de correo electrónico bien
formada (validación Pydantic `EmailStr`). Un email mal formado devuelve 422.

**RF-01.3** El campo `password` DEBE tener al menos 8 caracteres. Una contraseña
más corta devuelve 422.

**RF-01.4** El campo `username` DEBE ser una cadena no vacía. Un username vacío o
ausente devuelve 422.

**RF-01.5** Si el `email` ya existe en el repositorio, la operación devuelve 409.
El cuerpo sigue el formato `{"detail": "..."}`.

**RF-01.6** En caso de éxito, la operación devuelve 201. La respuesta NO contiene
la contraseña ni el hash de la contraseña bajo ningún nombre de campo.

**RF-01.7** El usuario queda almacenado en el repositorio en memoria con su
contraseña hashed (nunca en claro).

---

### RF-02 — Login (`POST /api/auth/login`)

**RF-02.1** La petición DEBE contener los campos `email` y `password`. La
ausencia de cualquiera devuelve 422.

**RF-02.2** Si el email existe y la contraseña es correcta, la operación devuelve
200 con el siguiente cuerpo:

```json
{
  "access_token": "<cadena opaca>",
  "token_type": "bearer"
}
```

**RF-02.3** El valor de `access_token` es un token opaco generado con
`secrets.token_urlsafe`. No es un JWT ni contiene información legible.

**RF-02.4** El token emitido queda registrado en el repositorio en memoria,
asociado al identificador del usuario.

**RF-02.5** Si la contraseña es incorrecta, la operación devuelve 401 con el
cuerpo `{"detail": "Credenciales inválidas"}`.

**RF-02.6** Si el email no existe en el repositorio, la operación devuelve 401
con el MISMO cuerpo que RF-02.5: `{"detail": "Credenciales inválidas"}`.
El sistema NO revela si una dirección de email está o no registrada
(requisito anti-enumeración).

---

### RF-03 — View own profile (`GET /api/auth/me`)

**RF-03.1** The request MUST include an `Authorization: Bearer <token>` header. Missing header → 401 with `{"detail": "Credenciales inválidas"}`.

**RF-03.2** If the header is present but not of the form `Bearer <token>` (malformed, empty token, wrong scheme) → 401 with `{"detail": "Credenciales inválidas"}`.

**RF-03.3** If the token is not found in the repository (unknown or never issued) → 401 with `{"detail": "Credenciales inválidas"}`.

**RF-03.4** If the token resolves to a user, the response is 200 with the body:

```json
{
  "id": "<user-id>",
  "email": "<user-email>",
  "username": "<username>"
}
```

This is the existing `UserPublic` schema. The response MUST NOT contain `password`, `hashed_password`, or any derivative of the password.

**RF-03.5** All three 401 paths (missing header, malformed header, unknown token) return the same `{"detail": "Credenciales inválidas"}` body. The response does NOT reveal which condition was triggered (anti-enumeration extension to token space).

---

### RF-04 — Change own password (`PUT /api/auth/me/password`)

**RF-04.1** The request MUST include a valid Bearer token (same rules as RF-03.1–RF-03.3 above). Missing/malformed/unknown token → 401 with `{"detail": "Credenciales inválidas"}`.

**RF-04.2** The request body MUST contain both fields `current_password` and `new_password`. Missing either field → 422.

**RF-04.3** `new_password` MUST be at least 8 characters (aligning with RF-01.3). A shorter value → 422.

**RF-04.4** If the token is valid and `current_password` matches the stored hash for that user, the operation returns **204 No Content** with an empty body. The success confirmation shown to the user is rendered by the frontend upon receiving 204; no response body is read.

**RF-04.5** After a successful change, the stored `hashed_password` for the user MUST reflect the new password (the old hash MUST NOT be present for the new one; it MUST be different from the value before the call).

**RF-04.6** If `current_password` does not match the stored hash, the operation returns 400 with `{"detail": "La contraseña actual es incorrecta"}`.

**RF-04.7** After a successful password change, the user CAN authenticate via `POST /api/auth/login` using the NEW password. The user CANNOT authenticate via `POST /api/auth/login` using the OLD password (regression invariant).

---

## Requisitos de seguridad

### RS-01 — Almacenamiento de contraseñas

**RS-01.1** Las contraseñas DEBEN almacenarse EXCLUSIVAMENTE como hash PBKDF2-SHA256
con salt aleatorio por usuario, usando `hashlib.pbkdf2_hmac` de la stdlib.

**RS-01.2** El salt DEBE generarse con `secrets.token_bytes` y almacenarse junto
al hash, de forma que la verificación sea posible sin la contraseña original.

**RS-01.3** La verificación de contraseña DEBE realizarse con `hmac.compare_digest`
para evitar ataques de temporización (timing attacks).

**RS-01.4** Ningún endpoint, log ni respuesta expone la contraseña en claro ni el
hash bajo ninguna circunstancia.

---

### RS-02 — Tokens

**RS-02.1** Los tokens son opacos; su valor no contiene información del usuario ni
puede descodificarse para obtener datos.

**RS-02.2** En este cambio los tokens NO tienen TTL ni fecha de expiración.
Esta limitación es conocida y aceptada; la caducidad de tokens se abordará en un
cambio posterior.

---

### RS-03 — Bearer token validation

**RS-03.1** Token validation is performed via a single reusable FastAPI dependency (`get_current_user`). Any protected endpoint MUST use this dependency; ad-hoc token parsing in routers is not permitted.

**RS-03.2** The dependency resolves a token by looking it up in `repo.tokens`. If the token is found, the associated `user_id` is used to retrieve the full `UserRecord` from `repo.users_by_id`. If either lookup fails → raise 401 immediately.

**RS-03.3** The same 401 message `"Credenciales inválidas"` is returned for all failure modes of the dependency (missing header, malformed header, token not in repo, user_id not in repo). No failure mode leaks information about which step failed.

**RS-03.4** The `get_current_user` dependency MUST be overridable in tests via the same `dependency_overrides` mechanism already used for `get_user_repository`.

---

## New Frontend Functional Requirements

These requirements describe observable behavior that MUST be verifiable by end-to-end testing (Playwright).

### RF-05 — Auth screens (Register + Login)

**RF-05.1** There exists a Register screen with fields for email, username, and password. Submitting valid data calls `POST /api/auth/register`. On success (201), the user is navigated to the Login screen (or directly to the authenticated area).

**RF-05.2** There exists a Login screen with fields for email and password. Submitting valid credentials calls `POST /api/auth/login`. On success (200), the returned `access_token` is stored client-side and the user is navigated to the Profile screen.

**RF-05.3** After a successful login, the token MUST be available for all subsequent requests (e.g. to `GET /api/auth/me`) without requiring the user to re-enter credentials.

**RF-05.4** The Login screen is publicly accessible (no auth required to view it).

---

### RF-06 — Profile screen

**RF-06.1** There exists a Profile screen that displays the logged-in user's `email` and `username`, fetched from `GET /api/auth/me` using the stored Bearer token.

**RF-06.2** The Profile screen MUST NOT be reachable without a valid stored token. An unauthenticated user attempting to access it MUST be redirected to (or shown) the Login screen.

**RF-06.3** The profile data shown to the user MUST match what the API returns. The screen does not show placeholder or hardcoded values.

---

### RF-07 — Change-password form

**RF-07.1** There exists a Change-password form (accessible from the Profile screen) with fields for `current_password` and `new_password`.

**RF-07.2** On success (API returns 204), the form shows a visible confirmation message to the user (e.g. "Password updated successfully" or equivalent). The message is rendered by the frontend logic; no body is read from the response.

**RF-07.3** If the API returns 400 due to a wrong current password, the form shows a visible error message to the user (not a blank screen or a silent failure).

**RF-07.4** After a successful password change, the user can log in again via the Login screen using the new password (E2E regression scenario).

---

## Requisitos no funcionales

### RNF-01 — Arquitectura en capas

La implementación DEBE seguir la arquitectura en tres capas del proyecto:

```
routers/ (HTTP)  →  services/ (lógica)  →  repositories/ (datos)
```

Los routers no acceden directamente al repositorio. Los servicios no importan
objetos de FastAPI (`Request`, `Response`, etc.).

### RNF-02 — Schemas Pydantic

Todos los request y response bodies DEBEN modelarse con clases Pydantic v2.
No se admiten `dict` sin tipo en las firmas públicas de routers ni servicios.

### RNF-03 — Sin dependencias nuevas de runtime

Este cambio NO introduce dependencias nuevas. Solo se usa:
- `hashlib`, `hmac`, `secrets` (stdlib Python)
- FastAPI, Pydantic v2, Uvicorn (ya presentes en el stack)
- `pytest` y `httpx`/`TestClient` (ya presentes para tests)

### RNF-04 — Formato de error

Todos los errores siguen el formato por defecto de FastAPI:
`{"detail": "<mensaje>"}`. No se usa RFC 7807 ni ningún otro envelope de error.

---

## Escenarios de aceptación

Los escenarios usan la notación Given/When/Then. Cada escenario se corresponde
directamente con un caso de prueba `pytest` usando `TestClient`.

---

### Escenario REG-01 — Registro exitoso

**Dado** que no existe ningún usuario con el email `nuevo@ejemplo.com`
**Cuando** se envía `POST /api/auth/register` con:
```json
{
  "email": "nuevo@ejemplo.com",
  "password": "segura1234",
  "username": "Diego"
}
```
**Entonces** la respuesta tiene código 201
**Y** el cuerpo de respuesta no contiene los campos `password` ni `hashed_password`
ni ningún campo cuyo valor sea la contraseña o el hash

---

### Escenario REG-02 — Email duplicado

**Dado** que ya existe un usuario registrado con el email `existente@ejemplo.com`
**Cuando** se envía `POST /api/auth/register` con ese mismo email
**Entonces** la respuesta tiene código 409
**Y** el cuerpo contiene `{"detail": ...}` con un mensaje que indica conflicto

---

### Escenario REG-03 — Email mal formado

**Dado** cualquier estado del repositorio
**Cuando** se envía `POST /api/auth/register` con `email: "no-es-un-email"`
**Entonces** la respuesta tiene código 422

---

### Escenario REG-04 — Contraseña demasiado corta

**Dado** cualquier estado del repositorio
**Cuando** se envía `POST /api/auth/register` con `password: "corta"` (menos de 8 caracteres)
**Entonces** la respuesta tiene código 422

---

### Escenario REG-05 — Campo obligatorio ausente

**Dado** cualquier estado del repositorio
**Cuando** se envía `POST /api/auth/register` sin el campo `username`
**Entonces** la respuesta tiene código 422

---

### Escenario LOG-01 — Login exitoso

**Dado** que existe un usuario registrado con email `usuario@ejemplo.com` y
contraseña `segura1234`
**Cuando** se envía `POST /api/auth/login` con:
```json
{
  "email": "usuario@ejemplo.com",
  "password": "segura1234"
}
```
**Entonces** la respuesta tiene código 200
**Y** el cuerpo contiene los campos `access_token` (cadena no vacía) y
`token_type` con valor `"bearer"`

---

### Escenario LOG-02 — Token queda registrado en el repositorio

**Dado** el mismo contexto que LOG-01
**Cuando** el login devuelve 200 con un `access_token`
**Entonces** ese token existe en el repositorio en memoria asociado al usuario

---

### Escenario LOG-03 — Contraseña incorrecta

**Dado** que existe un usuario registrado con email `usuario@ejemplo.com`
**Cuando** se envía `POST /api/auth/login` con la contraseña incorrecta
`password: "malaclave"`
**Entonces** la respuesta tiene código 401
**Y** el cuerpo es `{"detail": "Credenciales inválidas"}`

---

### Escenario LOG-04 — Email inexistente (anti-enumeración)

**Dado** que el email `fantasma@ejemplo.com` NO existe en el repositorio
**Cuando** se envía `POST /api/auth/login` con ese email y cualquier contraseña
**Entonces** la respuesta tiene código 401
**Y** el cuerpo es `{"detail": "Credenciales inválidas"}`
**Y** el mensaje es idéntico al de LOG-03 (no revela si la cuenta existe)

---

### Escenario SEC-01 — Contraseña no almacenada en claro

**Dado** que se ha registrado un usuario con contraseña `segura1234`
**Cuando** se inspecciona el estado interno del repositorio en memoria
**Entonces** ninguna entrada del repositorio contiene la cadena `"segura1234"`
como valor de ningún campo

---

### Escenario SEC-02 — Verificación en tiempo constante

**Dado** que se ha registrado un usuario
**Cuando** el servicio verifica una contraseña
**Entonces** la verificación usa `hmac.compare_digest` y no comparación directa
de strings (`==` o `!=`)

> Nota: este escenario se valida mediante revisión de código en `sdd-verify`,
> no con un test de integración de tiempo.

---

## Limitaciones conocidas y fuera de alcance

| Limitación | Decisión |
|---|---|
| Los tokens no tienen TTL ni expiración | Aceptado; cambio futuro |
| No hay endpoint de logout ni revocación de tokens | Fuera de alcance |
| `/api/tasks` no está protegido por autenticación | Fuera de alcance (rama Carlos) |
| No hay política de fortaleza de contraseña más allá del mínimo de 8 caracteres | Fuera de alcance |
| Persistencia en memoria (los datos se pierden al reiniciar) | Diseño actual; SQLite es evolución futura |
| Cambio de email o username | Solo cambio de contraseña está en alcance |
| Recuperación de contraseña olvidada / flujos de email | Fuera de alcance |
| Persistencia del token en cliente (localStorage/httpOnly) | Token almacenado en memoria por resistencia a XSS; se pierden en recarga de página |

---

## Archivos afectados

### Backend (agregar-autenticacion + perfil-usuario)

| Archivo | Rol | Cambio |
|---|---|---|
| `backend/app/main.py` | Aplicación FastAPI; registra el router de auth bajo `/api` | Nuevo |
| `backend/app/routers/auth.py` | Endpoints `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `PUT /api/auth/me/password` | Nuevo + Modificado |
| `backend/app/services/auth_service.py` | Lógica de negocio, hashing PBKDF2, emisión de token, get_me, change_password | Nuevo + Modificado |
| `backend/app/repositories/user_repository.py` | Almacén en memoria: usuarios y tokens; accesores get_by_token, get_by_id | Nuevo + Modificado |
| `backend/app/schemas/auth.py` | Schemas Pydantic: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `ChangePasswordRequest`, `UserPublic` | Nuevo + Modificado |
| `backend/app/dependencies.py` | FastAPI dependency `get_current_user` para validación Bearer token | Nuevo |
| `backend/app/services/exceptions.py` | Exception `InvalidCurrentPassword` para 400 en cambio de contraseña | Nuevo + Modificado |
| `backend/tests/test_auth.py` | Casos pytest con TestClient para todas aceptación scenarios (ME, PASS, E2E) | Nuevo + Modificado |

### Frontend (perfil-usuario)

| Archivo | Rol | Cambio |
|---|---|---|
| `frontend/` | Aplicación React 19 + Vite 8 + TypeScript 6 | Nuevo |
| `frontend/src/api/client.ts` | Wrapper fetch; adjunta Bearer token; maneja 204→null; lanza {detail} en errores | Nuevo |
| `frontend/src/auth/storage.ts` | Módulo in-memory para token (`let _token`); exporta setToken/getToken/clearToken | Nuevo |
| `frontend/src/components/RegisterForm.tsx` | Pantalla de registro; POST /api/auth/register | Nuevo |
| `frontend/src/components/LoginForm.tsx` | Pantalla de login; POST /api/auth/login | Nuevo |
| `frontend/src/components/Profile.tsx` | Pantalla de perfil; GET /api/auth/me | Nuevo |
| `frontend/src/components/ChangePasswordForm.tsx` | Formulario cambio contraseña; PUT /api/auth/me/password | Nuevo |
| `frontend/src/App.tsx` | Renderizado condicional (register/login/profile); manejo de token | Nuevo |
| `frontend/src/index.css` | Design system: borders-only, slate-900 ink, blue-600 accent | Nuevo |
| `frontend/vite.config.ts` | Configuración Vite; proxy `/api → http://127.0.0.1:8000` | Nuevo |
| `playwright.config.ts` | Config Playwright; webServer dual (uvicorn + vite) | Nuevo |
| `e2e/auth.spec.ts` | Suite E2E (E2E-01..06) con Playwright Chromium | Nuevo |
