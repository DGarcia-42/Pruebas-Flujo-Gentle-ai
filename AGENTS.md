# Pruebas-Flujo-Gentle-ai

Proyecto de prueba para validar el flujo de trabajo de Gentle-AI (SDD + Engram +
skills) trabajando dos personas en paralelo sobre el mismo repositorio.

La aplicación es un **gestor de tareas (task-tracker)** con API en FastAPI y una
interfaz en React. El objetivo no es el producto en sí, sino ejercitar el ciclo
`/sdd-new → explore → propose → spec → design → tasks → /sdd-apply → /sdd-verify →
/sdd-archive` sobre features reales.

## Idioma del proyecto

- **Toda la documentación en español de España** (README, guías, specs redactadas
  a mano, comentarios explicativos).
- **Los mensajes de commit en español de España**, con la descripción en español.
- Los identificadores de código siguen las convenciones de cada lenguaje
  (ver sección Convenciones de código); el idioma español aplica a documentación
  y comunicación, no a los nombres de variables/funciones.

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

## Reglas de testing (TDD)

- **Test primero, implementación después.** Cada tarea de `/sdd-apply` empieza por
  un test que falla.
- Backend: tests con `pytest` en `backend/tests/`; usar `TestClient` de FastAPI
  para los endpoints.
- Frontend: tests con Vitest + Testing Library en `frontend/src/**/*.test.tsx`.
- Una feature no se da por terminada en `/sdd-verify` si sus tests no pasan.

## Flujo de git (obligatorio)

### Ramas

- `main` → rama estable. **Nunca se mergea nada directamente a `main`.**
- `desarrollo-testing` → **rama de integración**. Es la base de la que sale todo y
  donde se integran las features. Contiene el `AGENTS.md` y el esqueleto de SDD
  (`openspec/config.yaml`).
- `desa/<Nombre>` → rama personal de cada persona (p. ej. `desa/Carlos`,
  `desa/Diego`). Se crea **desde `desarrollo-testing`**.
- `desa/<Nombre>/<descripcion>` → rama hija, **una por spec/cambio SDD**. Se crea
  **desde la rama personal padre**.

### Quién hace qué con las ramas

- **El agente crea y cambia de rama hija.** Al iniciar un `/sdd-new`, el agente crea
  la rama hija `desa/<Nombre>/<descripcion>` **desde la rama personal activa**
  (`desa/<Nombre>`), pidiendo confirmación antes de hacerlo. Si no está situado en la
  rama personal correcta, debe cambiar a ella primero, nunca crear la hija desde
  `desarrollo-testing` directamente.
- **El agente NUNCA hace merge ni push a `desarrollo-testing`.** La integración hacia
  arriba (hija → personal → `desarrollo-testing`) la realiza siempre la persona.
- La persona es responsable de que exista su rama personal `desa/<Nombre>` (creada
  desde `desarrollo-testing`) antes de pedir al agente el primer `/sdd-new`.

### Reglas

- Toda rama nueva sale de su base correcta: las personales de `desarrollo-testing`,
  las hijas de su rama personal. Así heredan `AGENTS.md` y `openspec/config.yaml`.
- **Una rama hija = un `/sdd-new` = un nombre de cambio SDD distinto.** Nunca dos
  personas usan el mismo nombre de cambio (evita conflictos en `openspec/changes/`).
- Tras `/sdd-verify` con los tests en verde, la rama hija se integra hacia arriba.
- **El merge a `desarrollo-testing` lo hacen las personas, no el agente**, de uno
  en uno y siempre con `git pull` previo de `desarrollo-testing` para resolver
  conflictos localmente.
- Sincronizar las ramas personales con `desarrollo-testing` con frecuencia (no solo
  al final) para que los merges no se acumulen.

### `/sdd-init` (importante)

- `/sdd-init` se ejecuta **una sola vez, sobre `desarrollo-testing`**, y su esqueleto
  de OpenSpec (`openspec/config.yaml`) se commitea allí.
- **No re-ejecutar `/sdd-init` en las ramas personales ni en las hijas**: heredan el
  `config.yaml` por git. Regenerarlo en cada rama provocaría conflictos en ese archivo.
- `/skill-registry` sí es local (`.atl/`, en `.gitignore`): se corre una vez por clon
  (o lo gestiona el hook de arranque), es independiente de la rama.

## Reglas de commits

- **Mensajes en español de España**, formato convencional con descripción en español.
  Ejemplos:
  - `feat: añade endpoint de creación de tareas`
  - `fix: corrige validación de prioridad vacía`
  - `test: cubre el listado de tareas`
  - `docs: actualiza la guía de instalación`
- **Prohibido incluir a Claude (o cualquier agente de IA) como co-autor.** Los commits
  no deben contener ningún trailer `Co-authored-by:` que mencione a Claude, ni firmas
  generadas por la IA. El autor del commit es siempre la persona.

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

- **Carlos** → rama personal `desa/Carlos`. Feature de tareas: backend `/api/tasks`
  + UI de lista/creación. Ramas hijas por spec (p. ej. `desa/Carlos/tareas-crud`).
- **Diego** → rama personal `desa/Diego`. Feature de autenticación: backend
  `/api/auth` + pantallas de login/registro. Ramas hijas por spec
  (p. ej. `desa/Diego/auth-login`).

Cada rama hija usa un **nombre de cambio SDD distinto** (`crear-api-tareas`,
`agregar-autenticacion`, etc.).

## Notas para el agente

- Si falta contexto técnico al iniciar, este documento es la fuente de verdad del
  stack y las convenciones.
- No introducir dependencias nuevas (bases de datos, librerías de estado, ORMs)
  sin que una spec aprobada lo requiera.
- Preferir soluciones simples y bien testeadas sobre abstracciones prematuras.
- El agente **puede crear y cambiar de rama hija** (`desa/<Nombre>/<descripcion>`)
  desde la rama personal activa, pidiendo confirmación. El agente **no realiza merges
  ni pushes a `desarrollo-testing`**: deja la integración a la persona.
