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

---

## Archivos afectados

Todos son archivos nuevos (este cambio crea el esqueleto backend desde cero):

| Archivo | Rol |
|---|---|
| `backend/app/main.py` | Aplicación FastAPI; registra el router de auth bajo `/api` |
| `backend/app/routers/auth.py` | Endpoints `POST /api/auth/register` y `POST /api/auth/login` |
| `backend/app/services/auth_service.py` | Lógica de negocio, hashing PBKDF2, emisión de token |
| `backend/app/repositories/user_repository.py` | Almacén en memoria: usuarios y tokens |
| `backend/app/schemas/auth.py` | Schemas Pydantic: `RegisterRequest`, `LoginRequest`, `TokenResponse` |
| `backend/tests/test_auth.py` | Casos pytest con TestClient (un test por escenario de aceptación) |
