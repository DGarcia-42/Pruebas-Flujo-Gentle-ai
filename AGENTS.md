# Pruebas-Flujo-Gentle-ai

Proyecto de prueba para validar el flujo de trabajo de Gentle-AI (SDD + Engram +
skills) trabajando dos personas en paralelo sobre el mismo repositorio.

La aplicación es un **gestor de tareas (task-tracker)** con API en FastAPI y una
interfaz en React. El objetivo no es el producto en sí, sino ejercitar el ciclo
`/sdd-new → explore → propose → spec → design → tasks → /sdd-apply → /sdd-verify →
/sdd-archive` sobre features reales.

## Stack

### Backend
- Python 3.12+
- FastAPI (framework web)
- Pydantic v2 (validación y schemas)
- Uvicorn (servidor ASGI)
- Persistencia en memoria por ahora (un repositorio in-memory); SQLite/SQLModel
  queda como evolución futura, no implementar hasta que una spec lo pida.
- Gestión de dependencias con `uv` (o `pip` + `venv` si no está disponible).
- Tests con `pytest`.

### Frontend
- React 18 + TypeScript
- Vite como bundler y dev server
- Fetch nativo para llamar a la API (sin librería de data-fetching salvo que una
  spec lo justifique).
- Tests con Vitest + React Testing Library.

## Estructura del repositorio

```
.
├── backend/        # API FastAPI (app, routers, services, repositories, tests)
├── frontend/       # App React + Vite (src/, components/, tests)
├── openspec/       # Artefactos SDD (generados por el flujo, versionados)
├── AGENTS.md       # Este documento
└── README.md
```

- El backend expone la API bajo el prefijo `/api`.
- El frontend consume `http://localhost:8000/api` en desarrollo.

## Convenciones de código

- **Backend**: capas separadas — `routers/` (HTTP) → `services/` (lógica) →
  `repositories/` (datos). Los routers no acceden directamente al repositorio.
- **Schemas**: todo request/response se modela con Pydantic. Nada de dicts sueltos
  en las firmas públicas.
- **Tipado**: type hints obligatorios en Python; `strict` activado en TypeScript.
- **Frontend**: componentes funcionales con hooks. Estado local salvo necesidad
  real de estado global.
- **Nombres**: `snake_case` en Python, `camelCase`/`PascalCase` en TS.
- **Commits**: formato convencional (`feat:`, `fix:`, `chore:`, `test:`...).

## Reglas de testing (TDD)

- **Test primero, implementación después.** Cada tarea de `/sdd-apply` empieza por
  un test que falla.
- Backend: tests con `pytest` en `backend/tests/`; usar `TestClient` de FastAPI
  para los endpoints.
- Frontend: tests con Vitest + Testing Library en `frontend/src/**/*.test.tsx`.
- Una feature no se da por terminada en `/sdd-verify` si sus tests no pasan.

## Endpoints previstos (alcance de la prueba)

Estos son el punto de partida; la especificación exacta de cada uno la produce la
fase `spec` de SDD, no este documento.

- `GET /api/tasks` — listar tareas
- `POST /api/tasks` — crear tarea
- `GET /api/tasks/{id}` — obtener una tarea
- `PUT /api/tasks/{id}` — actualizar tarea
- `DELETE /api/tasks/{id}` — eliminar tarea
- `POST /api/auth/register` — registro de usuario
- `POST /api/auth/login` — login (devuelve token)

## Reparto de trabajo (para la prueba en paralelo)

- **Persona A** → feature de tareas. Rama `feat/api-tareas`, cambio SDD
  `crear-api-tareas`. Cubre backend `/api/tasks` + UI de lista/creación.
- **Persona B** → feature de autenticación. Rama `feat/autenticacion`, cambio SDD
  `agregar-autenticacion`. Cubre backend `/api/auth` + pantallas de login/registro.

Usar **nombres de cambio SDD distintos** para evitar conflictos en `openspec/changes/`.

## Notas para el agente

- Si falta contexto técnico al iniciar, este documento es la fuente de verdad del
  stack y las convenciones.
- No introducir dependencias nuevas (bases de datos, librerías de estado, ORMs)
  sin que una spec aprobada lo requiera.
- Preferir soluciones simples y bien testeadas sobre abstracciones prematuras.
