# Diseño técnico: API CRUD de tareas (`crear-api-tareas`)

Este documento define el **CÓMO** arquitectónico de la API de tareas: las capas, el
flujo de datos, la representación interna del dominio frente a los schemas de API, la
inyección de dependencias y el manejo de errores. No repite los contratos de endpoint
(eso lo formaliza `spec.md`) ni enumera tareas de implementación (eso lo produce
`tasks.md`). La meta es que cualquier persona pueda implementar la feature sin reinventar
decisiones y revisarla sin reconstruir el razonamiento.

## Decisión rápida (resumen ejecutivo)

API FastAPI en tres capas estrictas (`routers → services → repositories`) con un
repositorio in-memory (un `dict`) inyectado por `Depends`. El servicio posee las reglas
de negocio y lanza un error de dominio (`TaskNotFoundError`) que el router traduce a HTTP
404. El dominio se almacena como un schema Pydantic `TaskRead` directamente en el `dict`,
sin modelo de dominio separado (decisión consciente, justificada abajo). Pydantic cubre
la validación (422). Los timestamps son UTC y los fija el servicio. Cero dependencias
nuevas.

## Camino feliz (flujo de una petición)

Recorrido de un `POST /api/tasks` exitoso, para anclar las responsabilidades de cada capa:

1. **Router** (`routers/tasks.py`): FastAPI valida el body contra `TaskCreate` (422 si
   falla). El handler recibe el `TaskService` por `Depends` y llama a `service.create(data)`.
2. **Service** (`services/task_service.py`): genera el `id` (UUID4) y los timestamps
   (`created_at`/`updated_at` en UTC), aplica los defaults de negocio, construye el
   objeto y lo entrega al repositorio.
3. **Repository** (`repositories/task_repository.py`): guarda el objeto en el `dict`
   keyed por `str(id)` y lo devuelve.
4. **Router**: devuelve `TaskRead` con `status_code=201`. FastAPI serializa a JSON.

El error path (`GET/PUT/DELETE` sobre id inexistente) invierte el mismo flujo: el
repositorio devuelve `None`, el servicio lanza `TaskNotFoundError`, y un exception
handler global lo mapea a 404. **El router nunca toca el repositorio; el servicio nunca
conoce HTTP.**

## Mapa de capas y flujo de datos

```
Cliente HTTP
   │  JSON
   ▼
┌─────────────────────────────────────────────────────────────┐
│ routers/tasks.py        (CAPA HTTP)                           │
│  · valida entrada vía schemas Pydantic (422 automático)       │
│  · status codes (200/201/204/404)                             │
│  · recibe TaskService por Depends                             │
│  · NO conoce el dict ni la lógica de negocio                  │
└───────────────┬───────────────────────────────────────────────┘
                │  TaskCreate / TaskUpdate (objetos Pydantic)
                ▼
┌─────────────────────────────────────────────────────────────┐
│ services/task_service.py   (CAPA DE LÓGICA / DOMINIO)         │
│  · genera id UUID4 y timestamps UTC                           │
│  · aplica reglas de negocio y defaults                        │
│  · lanza TaskNotFoundError cuando el id no existe             │
│  · recibe TaskRepository por Depends                          │
│  · NO conoce HTTP (testeable sin TestClient)                  │
└───────────────┬───────────────────────────────────────────────┘
                │  TaskRead (objeto de dominio = schema completo)
                ▼
┌─────────────────────────────────────────────────────────────┐
│ repositories/task_repository.py  (CAPA DE DATOS)             │
│  · dict[str, TaskRead] keyed por str(UUID)                    │
│  · CRUD puro: get/get_all/add/update/delete                  │
│  · devuelve None en ausencia (NO lanza excepciones)           │
│  · sin lógica de negocio ni HTTP                              │
└─────────────────────────────────────────────────────────────┘

exceptions.py      → TaskNotFoundError (excepción de dominio)
main.py            → app factory + exception_handler 404 + router con prefijo /api
```

## Layout de ficheros y módulos (definitivo)

```
backend/
├── pyproject.toml                      # deps: fastapi, uvicorn, pydantic; dev: pytest, httpx
├── app/
│   ├── __init__.py
│   ├── main.py                         # create_app(): FastAPI(), exception_handler, include_router(prefix="/api")
│   ├── exceptions.py                   # TaskNotFoundError(Exception)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── task.py                     # TaskStatus, TaskPriority, TaskCreate, TaskUpdate, TaskRead
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── task_repository.py          # TaskRepository (dict) + get_task_repository (provider singleton)
│   ├── services/
│   │   ├── __init__.py
│   │   └── task_service.py             # TaskService + get_task_service (provider)
│   └── routers/
│       ├── __init__.py
│       └── tasks.py                    # APIRouter(prefix="/tasks", tags=["tasks"])
└── tests/
    ├── __init__.py
    ├── conftest.py                     # fixtures: repo fresco {} + TestClient con dependency_overrides
    └── test_tasks_api.py               # tests de endpoint (RED primero, TDD estricto)
```

> Nota sobre el nombre del fichero de tests: el layout encargado fija
> `tests/test_tasks_api.py`. La propuesta mencionaba `tests/test_tasks.py` como ejemplo;
> se adopta `test_tasks_api.py` por ser más explícito (son tests de la API vía
> `TestClient`). Es un renombrado cosmético sin impacto arquitectónico.

## Decisiones de arquitectura (estilo ADR)

Cada decisión incluye su rationale y las alternativas descartadas, según la regla
`design` de `openspec/config.yaml` ("Document architecture decisions with rationale").

### ADR-1 · Sin modelo de dominio separado: `TaskRead` es la representación interna

**Decisión.** El repositorio almacena instancias de `TaskRead` directamente en el `dict`.
No existe una clase `Task` de dominio adicional (dataclass/entidad) distinta del schema
de salida.

**Rationale.** El dominio aquí es trivial (un registro plano de 7 campos sin invariantes
complejas ni comportamiento). Introducir una entidad `Task` + mappers entidad↔schema sería
una abstracción prematura que viola "prefer simple over premature abstraction"
(`config.yaml`, regla `apply`) y la filosofía YAGNI de la propuesta. `TaskRead` ya es un
modelo Pydantic validado y tipado, suficiente como contrato interno.

**Frontera de la decisión.** La separación de capas se mantiene por **responsabilidad**
(quién hace qué), no por tipos distintos: el repositorio guarda/recupera, el servicio
decide. La regla de capas de `AGENTS.md` se cumple porque el router sigue sin tocar el
`dict`.

**Alternativas descartadas.**
- *Entidad de dominio + mappers*: más ceremonia, cero valor en v1; se reabriría si
  llegara SQLite/SQLModel (cambio futuro fuera de alcance).
- *Guardar `dict` crudo en el repositorio*: violaría "nada de dicts sueltos en firmas
  públicas" (`AGENTS.md`) y perdería el tipado.

### ADR-2 · Repositorio in-memory inyectable como singleton de módulo

**Decisión.** `TaskRepository` envuelve un `dict[str, TaskRead]`. Una única instancia a
nivel de módulo (singleton) actúa de store de producción, expuesta por el provider
`get_task_repository()`. En tests, cada test inyecta un `TaskRepository` fresco vía
`app.dependency_overrides[get_task_repository]`.

**Rationale.** El singleton da persistencia durante la vida del proceso (lo que se espera
de un store in-memory de dev). La inyección por `Depends` permite **aislamiento total
entre tests**: un store vacío por test sin estado compartido ni necesidad de resetear
globales. Encaja con TDD estricto y con `TestClient`.

**Clave técnica.** El store mutable vive **dentro** de la instancia `TaskRepository`
(atributo `self._items`), no como variable global suelta. El singleton es la *instancia*,
no el `dict`. Así el override sustituye la instancia entera y no quedan referencias
colgantes al `dict` viejo.

**Alternativas descartadas.**
- *`dict` global a nivel de módulo + función de reset en tests*: frágil, propenso a fugas
  de estado entre tests y a olvidos de reset.
- *Contador global de ids*: descartado en la propuesta (UUID4 evita estado compartido y
  race conditions).

### ADR-3 · Inyección de dependencias en cadena vía `Depends`

**Decisión.** El wiring es una cadena de providers de FastAPI:

```python
# repositories/task_repository.py
_repository = TaskRepository()                 # singleton de módulo (prod)
def get_task_repository() -> TaskRepository:
    return _repository

# services/task_service.py
def get_task_service(
    repo: TaskRepository = Depends(get_task_repository),
) -> TaskService:
    return TaskService(repo)

# routers/tasks.py
@router.post("", status_code=201, response_model=TaskRead)
def create_task(
    data: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    return service.create(data)
```

**Rationale.** Cada capa declara su dependencia hacia abajo (`router → service →
repository`) sin instanciar manualmente. Para aislar tests basta con sobreescribir el
provider del nivel más bajo:

```python
app.dependency_overrides[get_task_repository] = lambda: TaskRepository()
```

`get_task_service` reconstruye automáticamente el servicio sobre el repo fresco. No hace
falta sobreescribir el servicio: la cadena se reensambla sola.

**Alternativas descartadas.**
- *Instanciar el servicio en el módulo del router*: rompe la inyección y dificulta el
  override en tests.
- *Sobreescribir `get_task_service` en tests*: funciona pero obliga a recrear el servicio
  a mano; sobreescribir solo el repo es más limpio y respeta la dirección de dependencia.

### ADR-4 · Errores de dominio en el servicio, mapeo a HTTP en el borde

**Decisión.** El repositorio devuelve `None` cuando un id no existe (no lanza). El
servicio interpreta ese `None` y lanza `TaskNotFoundError` (definido en `exceptions.py`).
Un `@app.exception_handler(TaskNotFoundError)` en `main.py` lo traduce a
`JSONResponse(status_code=404)`.

**Rationale.** Mantiene la capa de servicio **testeable sin contexto HTTP** (un test
unitario verifica que lanza `TaskNotFoundError`, sin `TestClient`). Cumple la regla de
capas de `AGENTS.md`: el servicio no conoce códigos HTTP. El handler global evita repetir
`try/except → HTTPException` en cada handler del router (DRY) y centraliza el formato del
cuerpo de error 404.

**Reparto de validación.**
- **422** (cuerpo malformado, tipos inválidos, `title` vacío en create) → lo gestiona
  Pydantic/FastAPI automáticamente. No se escribe código a mano.
- **404** (recurso inexistente en `GET/PUT/DELETE /{id}`) → `TaskNotFoundError` → handler.

**Alternativas descartadas.**
- *Lanzar `HTTPException` desde el servicio*: acopla la lógica a HTTP, viola las capas y
  ensucia los tests unitarios.
- *`try/except` en cada handler del router*: funciona pero duplica el mapeo; el handler
  global es más mantenible. (Si una spec futura necesitara cuerpos de error distintos por
  endpoint, se reabriría.)

### ADR-5 · Política de timestamps: UTC, fijados por el servicio

**Decisión.** `created_at` y `updated_at` son `datetime` en **UTC**
(`datetime.now(timezone.utc)`). Los fija siempre el **servicio**, nunca el cliente ni el
router:

- **Create**: `created_at = updated_at = ahora_utc`.
- **Update (PUT parcial)**: `created_at` inmutable; `updated_at = ahora_utc` en cada
  actualización, aunque el body no traiga cambios efectivos.

**Rationale.** Centralizar la generación de tiempo en el servicio garantiza consistencia
e impide que el cliente falsee timestamps. UTC evita ambigüedades de zona horaria y es el
estándar de serialización ISO-8601 de FastAPI/Pydantic. Ubicarlo en el servicio (no en el
schema ni el repositorio) respeta que el tiempo es una **regla de negocio**.

**Alternativas descartadas.**
- *`default_factory` en el schema Pydantic*: mezclaría generación de estado con el
  contrato de datos y dificultaría tests deterministas.
- *Timestamps naive (sin tz)*: descartado por ambigüedad y por buenas prácticas Pydantic v2.

### ADR-6 · Actualización parcial (`PUT`) y aplicación de cambios

**Decisión.** `PUT /api/tasks/{id}` es **parcial**: `TaskUpdate` tiene todos los campos
opcionales. El servicio aplica solo los campos presentes en el request usando
`data.model_dump(exclude_unset=True)` y los fusiona sobre la tarea existente.

**Rationale.** `exclude_unset=True` distingue "campo ausente" (no tocar) de "campo enviado
como `None`" (rara vez aplicable aquí, pero correcto semánticamente). Es el patrón canónico
de actualización parcial en Pydantic v2 sin un `PATCH` separado (decisión humana baked-in:
sin `PATCH`).

**Alternativas descartadas.**
- *`exclude_none=True`*: impediría borrar `description` poniéndola a `None`; semántica
  incorrecta para parcial.
- *Endpoint `PATCH` aparte*: explícitamente fuera de alcance en la propuesta.

## Schemas y enums (forma, no contrato de endpoint)

Los enums son `str, Enum` para que Pydantic los valide y FastAPI genere un OpenAPI honesto
(se serializan como string en JSON):

| Elemento | Definición | Notas |
|----------|------------|-------|
| `TaskStatus` | `pending` / `in_progress` / `done` | `str, Enum`; default `pending` en create |
| `TaskPriority` | `low` / `medium` / `high` | `str, Enum`; default `medium` en create |
| `TaskCreate` | `title` (str, no vacío) · `description` (str\|None=None) · `status` (=pending) · `priority` (=medium) | entrada de creación |
| `TaskUpdate` | todos opcionales (`title`, `description`, `status`, `priority`) | parcial; sin id/timestamps |
| `TaskRead` | `id` (UUID) · `title` · `description` · `status` · `priority` · `created_at` · `updated_at` | salida completa = representación interna (ADR-1) |

> `title` no vacío: se modela con `Field(min_length=1)` en `TaskCreate` para que Pydantic
> devuelva 422 ante string vacío (alineado con el commit de ejemplo de `AGENTS.md`,
> "validación de prioridad vacía"). La spec define el comportamiento exacto del contrato.

## Bootstrap (cómo arranca el proyecto)

El repo es greenfield: la **primera unidad de trabajo crea el esqueleto** antes de toda
tarea de feature (decisión baked-in "bootstrap-first").

| Pieza | Contenido |
|-------|-----------|
| `pyproject.toml` | `[project]` con deps `fastapi`, `uvicorn`, `pydantic`; dev-deps `pytest`, `httpx`. Python `>=3.12`. |
| Árbol de paquetes | `app/` y subpaquetes (`routers`, `services`, `repositories`, `schemas`) con `__init__.py`; `tests/`. |
| `main.py` | `create_app()` → `FastAPI()`, registra el `exception_handler` de `TaskNotFoundError`, hace `include_router(tasks.router, prefix="/api")`. Expone `app = create_app()` para Uvicorn. |
| `conftest.py` | fixture `client` que crea la app, inyecta `TaskRepository()` fresco vía `dependency_overrides` y entrega un `TestClient`. |

> `httpx` es dependencia de dev porque el `TestClient` de FastAPI/Starlette lo usa por
> debajo. No es una dependencia nueva de runtime; entra en el conjunto permitido
> (pytest/httpx) por la propuesta.

## Checklist de diseño (verificable por el revisor)

- [ ] El router solo depende de `TaskService` (vía `Depends`), nunca del `dict` ni del repo.
- [ ] El servicio no importa nada de `fastapi` salvo, como mucho, el provider; no usa `HTTPException`.
- [ ] El repositorio devuelve `None` ante ausencia y no lanza excepciones de dominio.
- [ ] `TaskNotFoundError` vive en `exceptions.py` y se mapea a 404 en `main.py`.
- [ ] Timestamps en UTC fijados por el servicio; `created_at` inmutable en update.
- [ ] `TaskUpdate` aplica solo campos presentes (`exclude_unset=True`).
- [ ] Cero dependencias fuera de fastapi/uvicorn/pydantic + pytest/httpx.
- [ ] Type hints en todas las firmas públicas.
- [ ] Tests inyectan un repositorio fresco por test (aislamiento total).

## Limitaciones conocidas

- **Thread-safety fuera de alcance.** El `dict` no está protegido por locks. En dev,
  Uvicorn corre single-worker, así que no hay condición de carrera práctica. Si una spec
  futura exige concurrencia o multi-worker, esta decisión se reabre (probablemente junto
  con la migración a una persistencia real).
- **Sin persistencia entre reinicios.** Reiniciar el proceso vacía el store. Es el
  comportamiento esperado de v1.

## Riesgos para reconciliar con la spec

- **Cuerpo del error 404.** El diseño centraliza el 404 en un handler global; la spec
  debe definir el **shape del cuerpo** (p. ej. `{"detail": "..."}`). Si la spec exige un
  formato concreto, se ajusta el handler (no la arquitectura).
- **`title` vacío → 422 vs 400.** El diseño lo trata como validación Pydantic (422). Si la
  spec lo formula como 400, habría que interceptar y remapear; conviene que ambas converjan
  en **422** (default honesto de FastAPI).
- **Semántica de `PUT` sobre id inexistente.** El diseño devuelve 404 (no crea/upsert). La
  spec debe confirmar que `PUT` NO hace upsert.
- **`updated_at` en update sin cambios.** El diseño lo refresca siempre. Si la spec
  prefiere refrescar solo ante cambios efectivos, se ajusta el servicio.

## Siguiente paso

Con `spec.md` y este `design.md` listos, continuar con `sdd-tasks`: desglose por fases con
numeración jerárquica, cada tarea arrancando por un test RED (TDD estricto), empezando por
la tarea de bootstrap.
