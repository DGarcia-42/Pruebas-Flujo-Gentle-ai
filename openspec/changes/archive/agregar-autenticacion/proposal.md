# Proposal: agregar-autenticacion

## Intención / Por qué

El proyecto necesita una base de autenticación para que más adelante los endpoints de
tareas puedan asociarse a usuarios reales. Hoy `backend/` no existe: este cambio crea el
esqueleto de la app FastAPI y entrega los dos primeros endpoints de identidad, `register`
y `login`, con hashing seguro de contraseñas y emisión de un token de acceso. El objetivo
inmediato es disponer de un flujo de alta y autenticación testeado en verde, sin introducir
dependencias nuevas y respetando la arquitectura en tres capas del repositorio.

## Alcance (in / out)

### In Scope
- `POST /api/auth/register` — alta de usuario; email único; 201 al crear; 409 si el email ya existe.
- `POST /api/auth/login` — login; 200 con token si las credenciales son válidas; 401 con
  el **mismo mensaje** para contraseña incorrecta y email desconocido (anti-enumeración).
- Esqueleto FastAPI: `main.py` + router/service/repository/schemas de auth y sus tests.
- Hashing de contraseñas y emisión de token, ambos con stdlib.

### Out of Scope
- Protección de los endpoints `/api/tasks` (depende de la rama de Carlos; cambio aparte).
- Política de fortaleza de contraseña más allá de una longitud mínima.
- Expiración / TTL de tokens (anotado como trabajo futuro).
- Persistencia en SQLite/SQLModel (sigue en memoria).
- JWT, passlib o cualquier dependencia nueva de runtime.

## Capabilities

### New Capabilities
- `user-auth`: registro de usuario y login con emisión de token de acceso opaco.

### Modified Capabilities
- None

## Enfoque técnico

Arquitectura en tres capas estricta desde el primer commit: `routers/` (HTTP) →
`services/` (lógica) → `repositories/` (datos en memoria). Todo request/response se modela
con Pydantic v2 (`RegisterRequest`, `LoginRequest`, `TokenResponse`, `User` interno).

Decisiones cerradas (no se reabren):
- **Hashing**: stdlib `hashlib.pbkdf2_hmac` (PBKDF2-SHA256), salt por usuario con
  `secrets.token_bytes`, iteraciones según OWASP, verificación con `hmac.compare_digest`.
- **Token**: opaco vía `secrets.token_urlsafe`, almacenado como `token -> user_id` en el
  repo en memoria. Respuesta `{"access_token": "...", "token_type": "bearer"}`.
- **Sin nuevas dependencias de runtime**: solo FastAPI/Pydantic/Uvicorn + stdlib; pytest para tests.

El repositorio en memoria guarda usuarios (por email/id) y la tabla de tokens activos.

## Decisiones menores aún por cerrar en spec

- **Formato de error**: se recomienda el `{"detail": ...}` por defecto de FastAPI (lean), sin RFC 7807.
- **Longitud mínima de contraseña**: se recomienda un mínimo simple (p. ej. 8 caracteres) en `RegisterRequest`.
- **TTL de token**: sin expiración por ahora; el token vive hasta reiniciar el servidor.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/main.py` | New | App FastAPI, registra el router de auth bajo `/api` |
| `backend/app/routers/auth.py` | New | Rutas HTTP de register/login |
| `backend/app/services/auth_service.py` | New | Lógica de alta, hashing y emisión de token |
| `backend/app/repositories/user_repository.py` | New | Almacén en memoria de usuarios y tokens |
| `backend/app/schemas/auth.py` | New | Schemas Pydantic de auth |
| `backend/tests/test_auth.py` | New | Tests de integración con `TestClient` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Enumeración de cuentas en login | Med | Mismo 401 y mensaje para email desconocido y password incorrecta |
| Token sin TTL persiste indefinidamente | Low | Aceptado para el scope de prueba; TTL anotado como futuro |
| Coste de hashing no auto-actualizable (PBKDF2) | Low | Iteraciones OWASP fijadas; revisable en cambio posterior |

## Rollback Plan

El cambio es aditivo y aislado en `backend/`. Para revertir basta eliminar los archivos
nuevos del directorio `backend/` (o revertir el commit de la rama hija); no toca el frontend
ni `openspec/config.yaml`, por lo que no hay migraciones que deshacer.

## Dependencies

- Ninguna nueva. Stack ya existente (FastAPI/Pydantic/Uvicorn) + stdlib + pytest.

## Success Criteria

- [ ] `test_register_creates_user` → 201 y usuario en el repo.
- [ ] `test_register_duplicate_email_fails` → 409.
- [ ] `test_login_returns_token` → 200 con `access_token`.
- [ ] `test_login_wrong_password_fails` → 401.
- [ ] `test_login_unknown_email_fails` → 401 con el mismo mensaje que password incorrecta.
- [ ] Cero dependencias nuevas de runtime añadidas al proyecto.
