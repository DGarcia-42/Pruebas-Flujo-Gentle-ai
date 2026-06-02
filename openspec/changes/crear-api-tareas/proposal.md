# Propuesta: API CRUD de tareas (`crear-api-tareas`)

Esta propuesta define la primera API funcional del proyecto: un CRUD de tareas en
FastAPI con persistencia en memoria. Habilita a Carlos para construir la feature de
tareas (backend `/api/tasks` y, más adelante, la UI) y sirve como banco de pruebas
real del ciclo SDD. El alcance es deliberadamente pequeño: cinco endpoints, sin base
de datos y sin dependencias nuevas, todo bajo TDD estricto.

## Por qué ahora

- El repositorio está vacío (greenfield): no existe `backend/`, ni tests, ni
  paquetes instalados. Necesitamos un primer cimiento sobre el que ejercitar el flujo
  `explore → propose → spec → design → tasks → apply → verify → archive`.
- Las tareas son el núcleo del gestor. La autenticación (cambio de Diego,
  `agregar-autenticacion`) es paralela e independiente: no acoplamos nada a auth en v1.
- El valor del ejercicio es validar el ciclo SDD con TDD estricto sobre código real,
  no construir un motor de consultas completo. Por eso v1 es mínimo y honesto con YAGNI.

## Qué significa éxito

- Existe un proyecto `backend/` ejecutable con `pytest` en verde.
- Los cinco endpoints (`/api/tasks`) responden con los códigos y contratos esperados.
- La arquitectura respeta las capas `routers → services → repositories`.
- Cero dependencias nuevas más allá de FastAPI/Pydantic/Uvicorn + pytest/httpx.
- Cada tarea de implementación nació de un test que falla primero (RED → GREEN).

## Alcance

### Dentro (v1)

- `GET /api/tasks` — listar todas las tareas (lista plana, sin filtros/paginación/orden).
- `POST /api/tasks` — crear una tarea.
- `GET /api/tasks/{id}` — obtener una tarea por id.
- `PUT /api/tasks/{id}` — actualizar una tarea (actualización **parcial**).
- `DELETE /api/tasks/{id}` — eliminar una tarea.
- Repositorio in-memory (dict en memoria), inyectable por dependencia de FastAPI.
- Modelo de dominio: `id`, `title`, `description`, `status`, `priority`,
  `created_at`, `updated_at`.
- Bootstrap del proyecto `backend/` (pyproject.toml, árbol de directorios, `main.py`).
- TDD estricto con `pytest` + `TestClient`.

### Fuera (no en v1)

- Autenticación, usuarios, `owner_id` o cualquier acoplamiento a auth (cambio de Diego).
- Persistencia real: SQLite, SQLModel, ORM o cualquier base de datos.
- Filtrado, paginación u ordenación en `GET /api/tasks`.
- Endpoint `PATCH` (la actualización parcial se hace vía `PUT`).
- Campos extra del dominio: `due_date`, `tags`, etc.
- Seguridad concurrente (thread-safety): Uvicorn corre single-worker en dev; se
  documenta la limitación, no se resuelve.
- UI de React (se aborda en un cambio posterior).

## Enfoque

### Arquitectura por capas

Se sigue la regla de `AGENTS.md` y `openspec/config.yaml`: los routers no tocan el
repositorio directamente.

```
routers/tasks.py     (HTTP: parseo, status codes, mapeo de errores a HTTP)
    ↓ depende de
services/task_service.py   (lógica de negocio: crear, obtener, listar, actualizar, borrar)
    ↓ depende de
repositories/task_repository.py   (dict en memoria, CRUD puro sobre el store)
```

- **Schemas Pydantic** (patrón canónico FastAPI, tres clases):
  - `TaskCreate` — lo que acepta la creación (`title` obligatorio, `description`
    opcional, `status` por defecto `pending`, `priority` por defecto `medium`).
  - `TaskUpdate` — **todos los campos opcionales** (patrón de actualización parcial).
  - `TaskRead` — representación completa devuelta al cliente (incluye `id`,
    `created_at`, `updated_at`).
- **Enums como `str, Enum`** (validados por Pydantic, serializados como string en JSON):
  - `TaskStatus`: `pending` / `in_progress` / `done`.
  - `TaskPriority`: `low` / `medium` / `high`.
- **IDs UUID4** generados en creación. Sin contador global mutable (evita estado
  compartido difícil de resetear en tests y race conditions).
- **Repositorio inyectable**: dict keyed por `UUID`. En producción es un singleton a
  nivel de módulo expuesto vía `Depends(get_task_repository)`. En tests se inyecta un
  `{}` fresco por test mediante `app.dependency_overrides` → aislamiento total.
- **Errores**: el servicio lanza una excepción de dominio `TaskNotFoundError`; el
  router la mapea a HTTP 404. La capa de servicio queda testeable sin contexto HTTP y
  no se acopla a HTTP (cumple la regla de capas de `AGENTS.md`).

### Decisiones ya tomadas (no se reabren)

1. **`priority` incluido** como `str, Enum` (`low`/`medium`/`high`), por defecto
   `medium` en creación. (El propio ejemplo de commit de `AGENTS.md` —"validación de
   prioridad vacía"— anticipa este campo.)
2. **`PUT /api/tasks/{id}` es actualización parcial**: todos los campos de
   `TaskUpdate` son opcionales, solo se actualizan los provistos. No hay `PATCH`.
3. **`description` opcional** (`str | None = None`, por defecto null).
4. **Bootstrap primero**: una tarea inicial dedicada (pyproject.toml, árbol de
   directorios, `backend/app/main.py`) precede a las tareas TDD de la feature.
   Sin ella, el primer `apply` no tendría proyecto contra el que ejecutar `pytest`.

### Bootstrap-first (nota para `sdd-tasks` y `sdd-apply`)

Como el repo es greenfield, la PRIMERA tarea NO es de feature: crea el esqueleto
mínimo del proyecto (`pyproject.toml` con FastAPI/Uvicorn/Pydantic + pytest/httpx,
árbol `backend/app/{routers,services,repositories,schemas}`, `exceptions.py`,
`backend/tests/conftest.py` y `backend/app/main.py` con la app FastAPI y el prefijo
`/api`). Solo después arrancan las tareas de feature, cada una con su test RED previo.

### Layout propuesto

```
backend/
├── app/
│   ├── main.py                 # crea FastAPI(), incluye router con prefijo /api
│   ├── routers/tasks.py        # handlers HTTP de /api/tasks
│   ├── services/task_service.py
│   ├── repositories/task_repository.py
│   ├── schemas/task.py         # TaskCreate, TaskUpdate, TaskRead, TaskStatus, TaskPriority
│   └── exceptions.py           # TaskNotFoundError
└── tests/
    ├── conftest.py             # fixture TestClient + repo fresco por test
    └── test_tasks.py
```

## Decisiones clave

| Decisión | Elección | Motivo |
|----------|----------|--------|
| Campos del modelo | id, title, description, status, priority, created_at, updated_at | Task-tracker realista y mínimo |
| `priority` | Incluido (`low`/`medium`/`high`, def. `medium`) | Decisión humana; anticipado en AGENTS.md |
| `description` | Opcional (`str \| None = None`) | Decisión humana |
| `status` por defecto | `pending` en creación | Comodidad del cliente; explícito |
| Tipo de id | UUID4 | Sin colisiones ni contador global; reset limpio en tests |
| Repositorio | dict inyectable vía `Depends`, singleton en prod | TDD limpio con `dependency_overrides` |
| Enums | `str, Enum` (status y priority) | Validación Pydantic + OpenAPI correcto |
| Schemas | TaskCreate / TaskUpdate (todo opcional) / TaskRead | Patrón canónico FastAPI, OpenAPI honesto |
| Semántica `PUT` | Actualización **parcial**, sin `PATCH` | Decisión humana |
| Manejo de errores | `TaskNotFoundError` en servicio → 404 en router | Respeta capas; servicio testeable sin HTTP |
| `GET /api/tasks` | Lista plana, sin filtros/paginación/orden | YAGNI; el valor es el ciclo SDD |
| Bootstrap | Tarea inicial separada antes de la feature | Sin proyecto no hay `pytest` que correr |
| Persistencia | Solo in-memory, cero dependencias nuevas | Restricción dura de AGENTS.md/config.yaml |

## Plan de reversión

El cambio es aditivo y aislado: todo vive bajo `backend/` (carpeta nueva) y
`openspec/changes/crear-api-tareas/`, en la rama hija de Carlos. No toca código
existente ni `desarrollo-testing` (la integración hacia arriba la hace la persona).

- **Reversión total**: eliminar la carpeta `backend/` y la rama hija; el repositorio
  vuelve al estado greenfield sin efectos colaterales (no hay migraciones, schema de
  BD ni dependencias compartidas que deshacer).
- **Reversión parcial por capas**: como cada endpoint es una unidad TDD independiente,
  se puede revertir un endpoint concreto quitando su router/servicio/test sin afectar
  al resto. El repositorio in-memory no deja estado persistente: reiniciar el proceso
  borra todos los datos.
- **Riesgo de dependencias**: nulo más allá de FastAPI/Uvicorn/Pydantic + pytest/httpx;
  revertir el `pyproject.toml` al estado previo elimina cualquier rastro.

## Siguiente paso

Continuar con `sdd-spec` (escenarios Given/When/Then por endpoint con RFC 2119) y
`sdd-design` (decisiones de arquitectura con rationale). Ambas pueden ejecutarse en
paralelo: la spec formaliza los contratos, el design detalla las capas y la inyección.
