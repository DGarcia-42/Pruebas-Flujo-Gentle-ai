# Tareas de implementación: `crear-api-tareas`

Desglose ordenado con TDD estricto (RED → GREEN → REFACTOR).  
Cada tarea de feature incluye los escenarios de la spec que sus tests DEBEN cubrir.  
Numeración jerárquica por fase; dependencias entre fases son secuenciales (cada fase  
requiere que la anterior esté en verde).

---

## Fase 0 — Bootstrap (prerequisito)

> Objetivo: repo ejecutable con `pytest` antes de escribir código de feature.  
> Esta es la única fase donde se ensambla el esqueleto antes de que los tests puedan correr.  
> Al final de la fase 0, `pytest` DEBE poder descubrir y ejecutar tests (aunque fallen).

- [x] **0.1 — Crear `backend/pyproject.toml`**  
  Crear el fichero de proyecto con:  
  - `[project]` dependencies: `fastapi`, `uvicorn`, `pydantic` (Python `>=3.12`).  
  - `[project.optional-dependencies]` dev: `pytest`, `httpx`.  
  - Sección `[tool.pytest.ini_options]` con `testpaths = ["tests"]`.  
  - Verificar: `pip install -e ".[dev]"` (o `uv pip install`) sin errores.  
  Sin tests previos posibles aquí (es infraestructura pura). Prerequisito de todo lo demás.

- [x] **0.2 — Crear árbol de paquetes**  
  Crear directorios y `__init__.py` vacíos:  
  ```
  backend/app/__init__.py
  backend/app/schemas/__init__.py
  backend/app/repositories/__init__.py
  backend/app/services/__init__.py
  backend/app/routers/__init__.py
  backend/tests/__init__.py
  ```  
  Verificar: Python puede importar `app` sin errores.

- [x] **0.3 — Crear `app/exceptions.py`**  
  Definir `TaskNotFoundError(Exception)`.  
  Sin tests previos posibles aquí (es definición pura sin comportamiento).  
  Necesario en 0.4 (main.py necesita importarlo).

- [x] **0.4 — Crear `app/main.py` con `create_app()` (esqueleto)**  
  Crear la función `create_app()` que:  
  - Instancia `FastAPI()`.  
  - Registra `@app.exception_handler(TaskNotFoundError)` → `JSONResponse(404, {"detail": "Task not found"})`.  
  - Expone `app = create_app()` en el módulo.  
  El router de tareas se conectará en la fase 4 (cuando exista). Por ahora `create_app` solo  
  devuelve la app con el handler registrado.  
  Sin tests previos posibles aquí (el router aún no existe).

- [x] **0.5 — Crear `tests/conftest.py` con fixture `client`**  
  Implementar:  
  ```python
  @pytest.fixture
  def client(app):
      app.dependency_overrides[get_task_repository] = lambda: TaskRepository()
      with TestClient(app) as c:
          yield c
      app.dependency_overrides.clear()
  ```  
  Importaciones: `pytest`, `TestClient`, `create_app`, `get_task_repository`, `TaskRepository`.  
  Nota: `get_task_repository` y `TaskRepository` aún no existen; la fixture fallará al  
  importar hasta la fase 2. Esto es esperado: el import-error es el RED de la fase 1.

- [x] **0.6 — Crear smoke test RED + verificar que `pytest` arranca**  
  En `tests/test_tasks_api.py`, escribir:  
  ```python
  def test_get_tasks_returns_empty_list(client):
      response = client.get("/api/tasks")
      assert response.status_code == 200
      assert response.json() == []
  ```  
  Ejecutar `pytest` y confirmar que **falla** (ImportError o 404 porque el router no existe).  
  Este es el RED canónico que dispara toda la cadena de implementación.  
  Spec: **R-LIST-01, R-LIST-02**, escenario **L-1**.

---

## Fase 1 — Schemas y enums

> Objetivo: `TaskCreate`, `TaskUpdate`, `TaskRead`, `TaskStatus`, `TaskPriority` definidos y  
> validados. Ningún endpoint funciona aún, pero los schemas se pueden importar y probar.

- [x] **1.1 — RED: tests de validación de `TaskCreate`**  
  En `tests/test_tasks_api.py` (o un fichero `tests/test_schemas.py` separado),  
  escribir tests que importen directamente `TaskCreate`, `TaskStatus`, `TaskPriority`  
  y validen su comportamiento:  
  - `TaskCreate(title="T")` → objeto válido con defaults `status="pending"`, `priority="medium"`, `description=None`.  
  - `TaskCreate(title="")` → lanza `ValidationError`.  
  - `TaskCreate()` (sin title) → lanza `ValidationError`.  
  - `TaskCreate(title=None)` → lanza `ValidationError`.  
  - `TaskCreate(title="T", status="invalido")` → lanza `ValidationError`.  
  - `TaskCreate(title="T", priority="invalido")` → lanza `ValidationError`.  
  Ejecutar: todos deben fallar con ImportError (los schemas no existen).  
  Spec: **R-MOD-02, R-MOD-03, R-MOD-04**, **R-CREATE-03, R-CREATE-04, R-CREATE-05, R-CREATE-06**.

- [x] **1.2 — GREEN: implementar `app/schemas/task.py`**  
  Definir:  
  - `TaskStatus(str, Enum)`: `pending`, `in_progress`, `done`.  
  - `TaskPriority(str, Enum)`: `low`, `medium`, `high`.  
  - `TaskCreate`: `title: str = Field(min_length=1)`, `description: str | None = None`,  
    `status: TaskStatus = TaskStatus.pending`, `priority: TaskPriority = TaskPriority.medium`.  
  - `TaskUpdate`: todos opcionales (`title: str | None = Field(None, min_length=1)`,  
    `description: str | None = None`, `status: TaskStatus | None = None`,  
    `priority: TaskPriority | None = None`).  
  - `TaskRead`: `id: UUID`, `title: str`, `description: str | None`, `status: TaskStatus`,  
    `priority: TaskPriority`, `created_at: datetime`, `updated_at: datetime`.  
  Ejecutar pytest: los tests de 1.1 deben pasar (GREEN).  
  ADR relevante: ADR-1 (TaskRead como representación interna), ADR-6 (exclude_unset).

- [x] **1.3 — RED: tests de validación de `TaskUpdate`**  
  Añadir tests para `TaskUpdate`:  
  - `TaskUpdate()` → objeto válido (todos None/unset).  
  - `TaskUpdate(title="")` → lanza `ValidationError`.  
  - `TaskUpdate(status="invalido")` → lanza `ValidationError`.  
  Ejecutar: deben fallar (schema existe pero la lógica puede no ser correcta aún).  
  Spec: **R-UPDATE-03, R-UPDATE-04, R-UPDATE-05**, escenario **U-5, U-6, U-7**.

  > Estos tests se pasan con la implementación de 1.2 si `TaskUpdate` ya está bien  
  > definido. Si pasan inmediatamente, verificar que el schema es correcto (no un falso positivo).

---

## Fase 2 — Repositorio

> Objetivo: `TaskRepository` con CRUD in-memory funcional y testeable sin HTTP.

- [x] **2.1 — RED: tests del repositorio**  
  Crear `tests/test_repository.py` (opcional) o añadir directamente en `test_tasks_api.py`.  
  Tests unitarios del repositorio (sin TestClient):  
  - `repo.get_all()` sobre repo vacío → `[]`.  
  - `repo.add(task_read)` → devuelve la tarea; `repo.get_all()` la incluye.  
  - `repo.get(str(id))` con id existente → devuelve `TaskRead`.  
  - `repo.get(str(uuid_inexistente))` → devuelve `None`.  
  - `repo.update(str(id), partial_data)` → devuelve `TaskRead` actualizado.  
  - `repo.update(str(uuid_inexistente), ...)` → devuelve `None`.  
  - `repo.delete(str(id))` → devuelve `True`; `repo.get(str(id))` → `None`.  
  - `repo.delete(str(uuid_inexistente))` → devuelve `False`.  
  Ejecutar: ImportError (repositorio no existe).  
  ADR relevante: ADR-2 (singleton, `self._items`), ADR-4 (devuelve None, no lanza).

- [x] **2.2 — GREEN: implementar `app/repositories/task_repository.py`**  
  Definir `TaskRepository`:  
  - `self._items: dict[str, TaskRead] = {}`.  
  - `get_all() -> list[TaskRead]`.  
  - `get(task_id: str) -> TaskRead | None`.  
  - `add(task: TaskRead) -> TaskRead`.  
  - `update(task_id: str, data: dict) -> TaskRead | None` (fusiona data sobre tarea existente).  
  - `delete(task_id: str) -> bool`.  
  Exponer `_repository = TaskRepository()` y `get_task_repository() -> TaskRepository`.  
  Ejecutar pytest: tests de 2.1 deben pasar (GREEN).

---

## Fase 3 — Servicio

> Objetivo: `TaskService` con lógica de negocio (UUID, timestamps UTC, `TaskNotFoundError`),  
> testeable sin HTTP.

- [x] **3.1 — RED: tests del servicio**  
  Tests unitarios del servicio (sin TestClient, usando `TaskRepository()` fresco):  
  - `service.create(TaskCreate(title="T"))` → devuelve `TaskRead` con `id` UUID4,  
    `created_at == updated_at`, `status="pending"`, `priority="medium"`.  
  - Dos llamadas `create` → IDs distintos.  
  - `created_at` y `updated_at` son `datetime` con timezone UTC.  
  - `service.get_all()` sobre servicio vacío → `[]`.  
  - `service.get(id_existente)` → devuelve `TaskRead` correcto.  
  - `service.get(uuid_inexistente)` → lanza `TaskNotFoundError`.  
  - `service.update(id_existente, TaskUpdate(title="X"))` → devuelve `TaskRead` con `title="X"`.  
  - `service.update(id_existente, TaskUpdate())` → `updated_at` actualizado, campos sin cambio.  
  - `service.update(id_existente, ...)` → `created_at` inmutable.  
  - `service.update(uuid_inexistente, ...)` → lanza `TaskNotFoundError`.  
  - `service.delete(id_existente)` → sin excepción; `get` posterior lanza `TaskNotFoundError`.  
  - `service.delete(uuid_inexistente)` → lanza `TaskNotFoundError`.  
  Ejecutar: ImportError (servicio no existe).  
  Spec: **R-MOD-05, R-MOD-06, R-CREATE-07, R-CREATE-08**, escenarios **C-8, U-3, U-8**.  
  ADR relevante: ADR-4 (lanza TaskNotFoundError), ADR-5 (timestamps UTC), ADR-6 (exclude_unset).

- [x] **3.2 — GREEN: implementar `app/services/task_service.py`**  
  Definir `TaskService`:  
  - `__init__(self, repo: TaskRepository)`.  
  - `create(data: TaskCreate) -> TaskRead`: genera UUID4, timestamps UTC iguales.  
  - `get_all() -> list[TaskRead]`.  
  - `get(task_id: str) -> TaskRead`: lanza `TaskNotFoundError` si no existe.  
  - `update(task_id: str, data: TaskUpdate) -> TaskRead`:  
    - `repo.get` → None → lanza `TaskNotFoundError`.  
    - Aplica `data.model_dump(exclude_unset=True)` fusionado.  
    - Actualiza `updated_at = datetime.now(timezone.utc)`.  
    - `created_at` inmutable.  
  - `delete(task_id: str) -> None`: lanza `TaskNotFoundError` si no existe.  
  Exponer `get_task_service(repo: TaskRepository = Depends(get_task_repository)) -> TaskService`.  
  Ejecutar pytest: tests de 3.1 deben pasar (GREEN).

---

## Fase 4 — Router y wiring de la aplicación

> Objetivo: router conectado a la app; el smoke test L-1 pasa en verde.

- [x] **4.1 — RED: smoke test del router (L-1 ya escrito en 0.6)**  
  El test `test_get_tasks_returns_empty_list` del paso 0.6 sigue en RED.  
  Confirmar que el fallo es porque el router no está montado (404 o similar),  
  no un ImportError (las fases anteriores ya resuelven los imports).

- [x] **4.2 — GREEN: implementar `app/routers/tasks.py` (esqueleto + GET /api/tasks)**  
  Crear `APIRouter(prefix="/tasks", tags=["tasks"])`.  
  Implementar solo:  
  ```python
  @router.get("", response_model=list[TaskRead])
  def list_tasks(service: TaskService = Depends(get_task_service)) -> list[TaskRead]:
      return service.get_all()
  ```  
  Conectar en `main.py`: `app.include_router(tasks_router, prefix="/api")`.  
  Actualizar `conftest.py` si los imports estaban en espera.  
  Ejecutar pytest: `test_get_tasks_returns_empty_list` debe pasar (GREEN).  
  Spec: **R-LIST-01, R-LIST-02, R-LIST-03, R-LIST-04**, escenarios **L-1, L-2**.

---

## Fase 5 — Endpoints CRUD (uno por tarea, orden POST → GET-list → GET-id → PUT → DELETE)

> Cada tarea es una unidad TDD independiente. Los tests de escenarios anteriores  
> NO se rompen al añadir nuevos endpoints.

- [x] **5.1 — POST `/api/tasks` (crear tarea)**  

  - [x] **5.1.1 — RED: tests de POST**  
    - `POST /api/tasks {"title": "T"}` → 201, body `TaskRead` completo con defaults.  
    - `POST /api/tasks {"title": "T", "description": "D", "status": "in_progress", "priority": "high"}` → 201, body refleja campos.  
    - `created_at == updated_at` en la respuesta de creación.  
    - Dos POST → IDs distintos.  
    - `POST /api/tasks {}` (sin title) → 422.  
    - `POST /api/tasks {"title": ""}` → 422.  
    - `POST /api/tasks {"title": null}` → 422.  
    - `POST /api/tasks {"title": "T", "status": "borrador"}` → 422.  
    - `POST /api/tasks {"title": "T", "priority": "urgente"}` → 422.  
    Ejecutar: 404 (endpoint no existe) o errores de validación inesperados. Confirmar RED.  
    Spec: **R-CREATE-01..08**, escenarios **C-1, C-2, C-3, C-4, C-5, C-6, C-7, C-8**.

  - [x] **5.1.2 — GREEN: implementar handler `POST /api/tasks`**  
    ```python
    @router.post("", status_code=201, response_model=TaskRead)
    def create_task(data: TaskCreate, service: TaskService = Depends(get_task_service)) -> TaskRead:
        return service.create(data)
    ```  
    Ejecutar pytest: todos los tests de 5.1.1 deben pasar.

  - [x] **5.1.3 — RED adicional: L-2 y L-3 (tarea creada aparece en el listado)**  
    - `POST` + `GET /api/tasks` → array con la tarea creada (mismo id, title, status, priority).  
    Ejecutar: puede pasar inmediatamente si el GET ya funciona. Si pasa, confirmar que el  
    test es válido (no un falso positivo).  
    Spec: escenarios **L-2, L-3**, **R-LIST-04**.

- [ ] **5.2 — GET `/api/tasks/{id}` (obtener tarea por id)**  

  - [ ] **5.2.1 — RED: tests de GET por id**  
    - `POST` para crear tarea con id `X`; `GET /api/tasks/X` → 200, body `TaskRead` con `id=X`.  
    - `id` en la URL coincide con `id` en el body.  
    - `title` y `priority` en el body coinciden con los del POST.  
    - `GET /api/tasks/{uuid_inexistente}` → 404 con `{"detail": "Task not found"}`.  
    Ejecutar: 404 (endpoint no existe). Confirmar RED.  
    Spec: **R-GET-01, R-GET-02, R-GET-03**, **R-ERR-01**, escenarios **G-1, G-2, G-3**.

  - [ ] **5.2.2 — GREEN: implementar handler `GET /api/tasks/{task_id}`**  
    ```python
    @router.get("/{task_id}", response_model=TaskRead)
    def get_task(task_id: str, service: TaskService = Depends(get_task_service)) -> TaskRead:
        return service.get(task_id)
    ```  
    El exception handler global en `main.py` convierte `TaskNotFoundError` → 404.  
    Ejecutar pytest: tests de 5.2.1 deben pasar.

- [ ] **5.3 — PUT `/api/tasks/{id}` (actualización parcial)**  

  - [ ] **5.3.1 — RED: tests de PUT**  
    - `POST` + `PUT /api/tasks/{id} {"title": "Actualizado"}` → 200, `title="Actualizado"`, `status` sin cambio.  
    - `PUT` con `{"status": "done", "priority": "high"}` → 200, `status` y `priority` actualizados, campos no incluidos intactos.  
    - `PUT` con `{}` → 200, todos los campos de datos conservados, `updated_at >= created_at`.  
    - `PUT` con `{}` sobre `updated_at`: comprobar que `updated_at` no disminuye.  
    - `PUT /api/tasks/{uuid_inexistente} {"title": "X"}` → 404.  
    - `PUT /api/tasks/{id} {"title": ""}` → 422.  
    - `PUT /api/tasks/{id} {"status": "cancelado"}` → 422.  
    - `PUT /api/tasks/{id} {"priority": "critica"}` → 422.  
    - `POST` + `PUT` → `created_at` en respuesta PUT igual al de la respuesta POST.  
    Ejecutar: 404 o 405 (endpoint no existe). Confirmar RED.  
    Spec: **R-UPDATE-01..09**, **R-MOD-05, R-MOD-06**, escenarios **U-1, U-2, U-3, U-4, U-5, U-6, U-7, U-8**.

  - [ ] **5.3.2 — GREEN: implementar handler `PUT /api/tasks/{task_id}`**  
    ```python
    @router.put("/{task_id}", response_model=TaskRead)
    def update_task(task_id: str, data: TaskUpdate, service: TaskService = Depends(get_task_service)) -> TaskRead:
        return service.update(task_id, data)
    ```  
    El servicio aplica `data.model_dump(exclude_unset=True)` + refresca `updated_at`.  
    Ejecutar pytest: tests de 5.3.1 deben pasar.

- [ ] **5.4 — DELETE `/api/tasks/{id}` (eliminar tarea)**  

  - [ ] **5.4.1 — RED: tests de DELETE**  
    - `POST` + `DELETE /api/tasks/{id}` → 204, cuerpo vacío.  
    - `DELETE /api/tasks/{uuid_inexistente}` → 404.  
    - `POST` + `DELETE` + `GET /api/tasks/{id}` → 404 (D-4).  
    - `POST` + `DELETE` + `GET /api/tasks` → array sin la tarea eliminada (D-3).  
    - `POST` + `DELETE` + `DELETE` (segundo DELETE) → 404 (D-5).  
    Ejecutar: 404 o 405 (endpoint no existe). Confirmar RED.  
    Spec: **R-DELETE-01..05**, escenarios **D-1, D-2, D-3, D-4, D-5**.

  - [ ] **5.4.2 — GREEN: implementar handler `DELETE /api/tasks/{task_id}`**  
    ```python
    @router.delete("/{task_id}", status_code=204)
    def delete_task(task_id: str, service: TaskService = Depends(get_task_service)) -> None:
        service.delete(task_id)
    ```  
    Ejecutar pytest: tests de 5.4.1 deben pasar.

---

## Fase 6 — Verificación final y refactor

> Objetivo: suite completa en verde, cobertura de los 33 requisitos y 27 escenarios,  
> type hints completos, cero warnings de pytest.

- [ ] **6.1 — Ejecutar suite completa y confirmar 0 fallos**  
  ```bash
  cd backend && pytest -v
  ```  
  Todos los tests deben pasar. Si alguno falla, aplicar RED-GREEN antes de continuar.

- [ ] **6.2 — Verificar cobertura de escenarios**  
  Comprobar manualmente que cada escenario de la spec (L-1..L-3, C-1..C-8, G-1..G-3,  
  U-1..U-8, D-1..D-5) tiene al menos un test que lo cubre directamente.  
  Añadir tests para cualquier escenario sin cobertura.

- [ ] **6.3 — Revisar type hints y checklist de diseño**  
  Verificar el checklist de `design.md`:  
  - [ ] Router solo depende de `TaskService` vía `Depends`.  
  - [ ] Servicio no importa nada de `fastapi` salvo el provider; no usa `HTTPException`.  
  - [ ] Repositorio devuelve `None` ante ausencia.  
  - [ ] `TaskNotFoundError` en `exceptions.py`, mapeado en `main.py`.  
  - [ ] Timestamps UTC, `created_at` inmutable en update.  
  - [ ] `TaskUpdate` con `exclude_unset=True`.  
  - [ ] Cero dependencias fuera de fastapi/uvicorn/pydantic + pytest/httpx.  
  - [ ] Type hints en todas las firmas públicas.

- [ ] **6.4 — Refactor (si aplica)**  
  Con todos los tests en verde: eliminar duplicación, mejorar nombres, extraer helpers.  
  No añadir comportamiento. Volver a ejecutar pytest tras cada cambio de refactor.

---

## Resumen de dependencias entre fases

```
0 (bootstrap) → 1 (schemas) → 2 (repositorio) → 3 (servicio) → 4 (wiring) → 5.x (endpoints) → 6 (verificación)
```

Los endpoints de la fase 5 son **independientes entre sí** una vez que la fase 4 está en verde  
(cada uno es una unidad TDD autónoma). Sin embargo, por claridad y para que los tests  
de integración de fases anteriores no interfieran, se recomienda completarlos en orden:  
POST → GET list → GET id → PUT → DELETE.

## Mapa de requisitos → tareas

| Requisitos spec        | Tareas                       |
|------------------------|------------------------------|
| R-MOD-01..07           | 1.1, 1.2, 1.3, 3.1, 3.2      |
| R-LIST-01..04          | 4.2, 5.1.3                   |
| R-CREATE-01..08        | 5.1.1, 5.1.2, 5.1.3          |
| R-GET-01..03, R-ERR-01 | 5.2.1, 5.2.2                 |
| R-UPDATE-01..09        | 5.3.1, 5.3.2                 |
| R-DELETE-01..05        | 5.4.1, 5.4.2                 |
| R-CT-01, R-ERR-02      | 0.4 (handler), 1.2 (Pydantic)|
| R-TEST-01              | 0.5 (conftest)               |
