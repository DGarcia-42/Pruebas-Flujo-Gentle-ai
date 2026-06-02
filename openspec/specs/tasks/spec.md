# Spec de capacidad: `tasks` (API CRUD de tareas)

Esta spec define el contrato de comportamiento observable de los cinco endpoints de
tareas bajo `/api/tasks`. Rige lo que DEBE ser cierto para la capacidad `tasks`, sin dictar
como implementarlo (la arquitectura y las capas se documentan en el documento de diseño).

Todos los términos normativos siguen **RFC 2119** (`MUST`, `SHALL`, `SHOULD`, `MAY`).
Los escenarios usan la sintaxis **Given / When / Then**.

---

## 1. Modelo de dominio `Task`

### 1.1 Campos y tipos

| Campo        | Tipo JSON               | Requerido en creacion | Valor por defecto      |
|--------------|-------------------------|-----------------------|------------------------|
| `id`         | `string` (UUID4)        | No - generado         | UUID4 nuevo            |
| `title`      | `string`                | **Si** (min 1 char)   | -                      |
| `description`| `string` o `null`       | No                    | `null`                 |
| `status`     | `string` (enum)         | No                    | `"pending"`            |
| `priority`   | `string` (enum)         | No                    | `"medium"`             |
| `created_at` | `string` (ISO 8601 UTC) | No - generado         | instante de creacion   |
| `updated_at` | `string` (ISO 8601 UTC) | No - generado         | instante de creacion; se actualiza en cada modificacion |

### 1.2 Valores de enum `status`

`"pending"` - `"in_progress"` - `"done"`

### 1.3 Valores de enum `priority`

`"low"` - `"medium"` - `"high"`

### 1.4 Invariantes del modelo

- **R-MOD-01** - El `id` MUST ser un UUID4 en formato string estándar
  (`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`). MUST ser inmutable tras la creación.
- **R-MOD-02** - `title` MUST ser un string no vacío (longitud mínima 1 carácter).
  La API MUST rechazar un `title` vacío, `null` o ausente con `422`.
- **R-MOD-03** - `status` MUST pertenecer al enum `TaskStatus`. Cualquier otro valor
  MUST ser rechazado con `422`.
- **R-MOD-04** - `priority` MUST pertenecer al enum `TaskPriority`. Cualquier otro
  valor MUST ser rechazado con `422`.
- **R-MOD-05** - `created_at` MUST establecerse en el instante de creación (UTC) y
  MUST ser inmutable a partir de ese momento.
- **R-MOD-06** - `updated_at` MUST establecerse en el instante de creación y MUST
  actualizarse al instante de cada modificación exitosa. Si ningún campo cambia en
  un `PUT`, `updated_at` MUST actualizarse igualmente.
- **R-MOD-07** - El sistema MUST aceptar y devolver fechas en formato ISO 8601 UTC.

---

## 2. Schemas de entrada y salida

### 2.1 `TaskCreate` (cuerpo de `POST`)

- `title` - string, **requerido**, no vacío.
- `description` - string o null, opcional, por defecto `null`.
- `status` - enum `TaskStatus`, opcional, por defecto `"pending"`.
- `priority` - enum `TaskPriority`, opcional, por defecto `"medium"`.

### 2.2 `TaskUpdate` (cuerpo de `PUT`)

- Todos los campos (`title`, `description`, `status`, `priority`) son **opcionales**.
- Un `PUT` con cuerpo vacío `{}` es válido; MUST producir `200` y actualizar
  únicamente `updated_at`.
- Si `title` está presente MUST ser no vacío; si es `""` MUST producir `422`.

### 2.3 `TaskRead` (respuesta de todos los endpoints que devuelven una tarea)

Todos los campos del modelo: `id`, `title`, `description`, `status`, `priority`,
`created_at`, `updated_at`.

---

## 3. Endpoints

### 3.1 `GET /api/tasks` - Listar tareas

**Requisitos**

- **R-LIST-01** - El endpoint MUST responder `200 OK` siempre, incluso si no existen tareas.
- **R-LIST-02** - El cuerpo de la respuesta MUST ser un array JSON (`[]` si no hay
  tareas, `[TaskRead, ...]` si las hay).
- **R-LIST-03** - El endpoint MUST devolver TODAS las tareas existentes sin filtrado,
  paginación ni ordenación en v1.
- **R-LIST-04** - Cada elemento del array MUST cumplir el schema `TaskRead` completo.

**Escenarios**

```
Escenario L-1: Sin tareas en el sistema
  Dado que no existe ninguna tarea
  Cuando se hace GET /api/tasks
  Entonces la respuesta es 200 OK
  Y el cuerpo es []

Escenario L-2: Con tareas existentes
  Dado que existen N tareas (N >= 1)
  Cuando se hace GET /api/tasks
  Entonces la respuesta es 200 OK
  Y el cuerpo es un array con N elementos
  Y cada elemento tiene todos los campos de TaskRead

Escenario L-3: La tarea recién creada aparece en el listado
  Dado que se crea una tarea con POST /api/tasks
  Cuando se hace GET /api/tasks
  Entonces la respuesta contiene la tarea creada (mismo id, title, status, priority)
```

---

### 3.2 `POST /api/tasks` - Crear tarea

**Requisitos**

- **R-CREATE-01** - El endpoint MUST responder `201 Created` al crear una tarea válida.
- **R-CREATE-02** - El cuerpo de la respuesta MUST ser un objeto `TaskRead` con todos
  los campos, incluidos `id`, `created_at` y `updated_at` generados por el servidor.
- **R-CREATE-03** - Si `title` está ausente, es `null` o es string vacío, el endpoint
  MUST responder `422 Unprocessable Entity`.
- **R-CREATE-04** - Si `status` tiene un valor fuera del enum, el endpoint MUST
  responder `422`.
- **R-CREATE-05** - Si `priority` tiene un valor fuera del enum, el endpoint MUST
  responder `422`.
- **R-CREATE-06** - Los campos omitidos MUST tomar sus valores por defecto:
  `description -> null`, `status -> "pending"`, `priority -> "medium"`.
- **R-CREATE-07** - Cada tarea creada MUST recibir un `id` único (UUID4); dos llamadas
  sucesivas MUST generar IDs distintos.
- **R-CREATE-08** - `created_at` y `updated_at` MUST ser iguales (mismo instante) en
  la respuesta de creación.

**Escenarios**

```
Escenario C-1: Crear tarea con solo título (happy path mínimo)
  Dado un body {"title": "Mi primera tarea"}
  Cuando se hace POST /api/tasks
  Entonces la respuesta es 201 Created
  Y el body contiene id (UUID4), title="Mi primera tarea",
    description=null, status="pending", priority="medium",
    created_at y updated_at (iguales entre sí)

Escenario C-2: Crear tarea con todos los campos
  Dado un body {"title": "T", "description": "Desc", "status": "in_progress", "priority": "high"}
  Cuando se hace POST /api/tasks
  Entonces la respuesta es 201 Created
  Y el body refleja exactamente los valores enviados (más id, created_at, updated_at)

Escenario C-3: title ausente -> 422
  Dado un body {} (sin title)
  Cuando se hace POST /api/tasks
  Entonces la respuesta es 422 Unprocessable Entity

Escenario C-4: title vacío -> 422
  Dado un body {"title": ""}
  Cuando se hace POST /api/tasks
  Entonces la respuesta es 422 Unprocessable Entity

Escenario C-5: title null -> 422
  Dado un body {"title": null}
  Cuando se hace POST /api/tasks
  Entonces la respuesta es 422 Unprocessable Entity

Escenario C-6: status con valor inválido -> 422
  Dado un body {"title": "T", "status": "borrador"}
  Cuando se hace POST /api/tasks
  Entonces la respuesta es 422 Unprocessable Entity

Escenario C-7: priority con valor inválido -> 422
  Dado un body {"title": "T", "priority": "urgente"}
  Cuando se hace POST /api/tasks
  Entonces la respuesta es 422 Unprocessable Entity

Escenario C-8: Dos creaciones generan IDs distintos
  Dado dos llamadas POST /api/tasks con body {"title": "T"}
  Cuando se procesan ambas peticiones
  Entonces los dos id devueltos son distintos entre sí
```

---

### 3.3 `GET /api/tasks/{id}` - Obtener tarea por id

**Requisitos**

- **R-GET-01** - El endpoint MUST responder `200 OK` con el objeto `TaskRead` si la
  tarea existe.
- **R-GET-02** - El endpoint MUST responder `404 Not Found` si no existe una tarea con
  el `id` proporcionado.
- **R-GET-03** - El `id` recibido por la ruta MUST coincidir con el campo `id` del
  objeto devuelto.

**Escenarios**

```
Escenario G-1: id existente -> 200 con la tarea (happy path)
  Dado que existe una tarea con id=X creada previamente
  Cuando se hace GET /api/tasks/X
  Entonces la respuesta es 200 OK
  Y el body es un objeto TaskRead con id=X y los campos correctos

Escenario G-2: id inexistente -> 404
  Dado un UUID válido que no corresponde a ninguna tarea
  Cuando se hace GET /api/tasks/{uuid_inexistente}
  Entonces la respuesta es 404 Not Found

Escenario G-3: Datos íntegros - lo que se creó es lo que se obtiene
  Dado que se crea una tarea con title="Z", priority="low"
  Cuando se hace GET /api/tasks/{id_de_la_tarea_creada}
  Entonces el body contiene title="Z" y priority="low"
```

---

### 3.4 `PUT /api/tasks/{id}` - Actualizar tarea (parcial)

**Requisitos**

- **R-UPDATE-01** - El endpoint MUST responder `200 OK` con el objeto `TaskRead`
  actualizado si la tarea existe y el body es válido.
- **R-UPDATE-02** - El endpoint MUST responder `404 Not Found` si no existe una tarea
  con el `id` proporcionado.
- **R-UPDATE-03** - El endpoint MUST responder `422` si `title` está presente y es
  string vacío.
- **R-UPDATE-04** - El endpoint MUST responder `422` si `status` está presente y tiene
  un valor fuera del enum.
- **R-UPDATE-05** - El endpoint MUST responder `422` si `priority` está presente y
  tiene un valor fuera del enum.
- **R-UPDATE-06** - Solo los campos presentes en el body MUST actualizarse; los campos
  ausentes MUST conservar su valor anterior.
- **R-UPDATE-07** - `updated_at` MUST actualizarse al instante de la petición exitosa,
  independientemente de cuántos campos hayan cambiado.
- **R-UPDATE-08** - `created_at` MUST permanecer inmutable tras el `PUT`.
- **R-UPDATE-09** - `id` MUST permanecer inmutable; si el body incluye un campo `id`,
  MUST ser ignorado o rechazado con 422.

**Escenarios**

```
Escenario U-1: Actualizar un campo (happy path parcial)
  Dado una tarea existente con title="Original" y status="pending"
  Cuando se hace PUT /api/tasks/{id} con body {"title": "Actualizado"}
  Entonces la respuesta es 200 OK
  Y el body contiene title="Actualizado"
  Y status="pending" (sin cambio)
  Y updated_at >= created_at

Escenario U-2: Actualizar varios campos
  Dado una tarea existente
  Cuando se hace PUT /api/tasks/{id} con body {"status": "done", "priority": "high"}
  Entonces la respuesta es 200 OK
  Y el body refleja status="done" y priority="high"
  Y los campos no incluidos en el body conservan su valor anterior

Escenario U-3: Body vacío {} - solo updated_at cambia
  Dado una tarea existente
  Cuando se hace PUT /api/tasks/{id} con body {}
  Entonces la respuesta es 200 OK
  Y todos los campos (title, description, status, priority) conservan su valor
  Y updated_at es mayor o igual al updated_at previo

Escenario U-4: id inexistente -> 404
  Dado un UUID válido que no corresponde a ninguna tarea
  Cuando se hace PUT /api/tasks/{uuid_inexistente} con body {"title": "X"}
  Entonces la respuesta es 404 Not Found

Escenario U-5: title vacío -> 422
  Dado una tarea existente
  Cuando se hace PUT /api/tasks/{id} con body {"title": ""}
  Entonces la respuesta es 422 Unprocessable Entity

Escenario U-6: status inválido -> 422
  Dado una tarea existente
  Cuando se hace PUT /api/tasks/{id} con body {"status": "cancelado"}
  Entonces la respuesta es 422 Unprocessable Entity

Escenario U-7: priority inválido -> 422
  Dado una tarea existente
  Cuando se hace PUT /api/tasks/{id} con body {"priority": "crítica"}
  Entonces la respuesta es 422 Unprocessable Entity

Escenario U-8: created_at inmutable
  Dado una tarea existente con created_at=T0
  Cuando se hace PUT /api/tasks/{id} con cualquier body válido
  Entonces el campo created_at en la respuesta es igual a T0
```

---

### 3.5 `DELETE /api/tasks/{id}` - Eliminar tarea

**Requisitos**

- **R-DELETE-01** - El endpoint MUST responder `204 No Content` si la tarea existe y
  se elimina con éxito. El cuerpo de la respuesta MUST estar vacío.
- **R-DELETE-02** - El endpoint MUST responder `404 Not Found` si no existe una tarea
  con el `id` proporcionado.
- **R-DELETE-03** - Tras un `DELETE` exitoso, cualquier petición posterior a
  `GET /api/tasks/{id}` con el mismo id MUST devolver `404`.
- **R-DELETE-04** - Tras un `DELETE` exitoso, la tarea eliminada MUST dejar de
  aparecer en `GET /api/tasks`.
- **R-DELETE-05** - Un segundo `DELETE` sobre el mismo id (ya eliminado) MUST devolver
  `404`.

**Escenarios**

```
Escenario D-1: Eliminar tarea existente -> 204 sin cuerpo (happy path)
  Dado una tarea existente con id=X
  Cuando se hace DELETE /api/tasks/X
  Entonces la respuesta es 204 No Content
  Y el cuerpo de la respuesta está vacío

Escenario D-2: id inexistente -> 404
  Dado un UUID válido que no corresponde a ninguna tarea
  Cuando se hace DELETE /api/tasks/{uuid_inexistente}
  Entonces la respuesta es 404 Not Found

Escenario D-3: Tarea eliminada no aparece en GET /api/tasks
  Dado que se elimina con éxito la tarea con id=X
  Cuando se hace GET /api/tasks
  Entonces el array de respuesta NO contiene ningún elemento con id=X

Escenario D-4: GET por id tras DELETE -> 404
  Dado que se elimina con éxito la tarea con id=X
  Cuando se hace GET /api/tasks/X
  Entonces la respuesta es 404 Not Found

Escenario D-5: DELETE idempotente falla con 404
  Dado que la tarea con id=X fue eliminada
  Cuando se hace un segundo DELETE /api/tasks/X
  Entonces la respuesta es 404 Not Found
```

---

## 4. Comportamiento transversal

### 4.1 Content-Type

- **R-CT-01** - El servidor MUST devolver `Content-Type: application/json` en todas
  las respuestas con cuerpo (200, 201, 404, 422). Las respuestas 204 MUST omitir el
  cuerpo.

### 4.2 Respuestas de error

- **R-ERR-01** - Las respuestas `404` SHOULD incluir un objeto JSON con un campo
  `detail` que describa el recurso no encontrado (p.ej. `{"detail": "Task not found"}`).
- **R-ERR-02** - Las respuestas `422` MUST incluir el detalle de validación estándar de
  FastAPI/Pydantic (`{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`).

### 4.3 Aislamiento entre tests

- **R-TEST-01** - Cada test MUST partir de un repositorio vacío (sin tareas). La
  implementación MUST permitir inyectar un store vacío por test mediante
  `app.dependency_overrides`.

### 4.4 Fuera de alcance en v1

Los siguientes comportamientos están **fuera de spec** y no deben validarse:

- Filtrado, paginación u ordenación en `GET /api/tasks`.
- Autenticación, autorización o cualquier campo `owner_id`.
- Persistencia en base de datos; el store es in-memory.
- Seguridad ante concurrencia (thread-safety).
- Endpoint `PATCH`.

---

## 5. Resumen de requisitos y escenarios

| Endpoint                  | Requisitos | Escenarios | Códigos cubiertos |
|---------------------------|-----------|------------|-------------------|
| `GET /api/tasks`          | 4         | 3          | 200               |
| `POST /api/tasks`         | 8         | 8          | 201, 422          |
| `GET /api/tasks/{id}`     | 3         | 3          | 200, 404          |
| `PUT /api/tasks/{id}`     | 9         | 8          | 200, 404, 422     |
| `DELETE /api/tasks/{id}`  | 5         | 5          | 204, 404          |
| Transversales             | 4         | -          | -                 |
| **TOTAL**                 | **33**    | **27**     |                   |

---

## 6. Decisiones baked-in (no se reabren)

Estas decisiones vienen de la fase de propuesta y son contratos cerrados para esta spec:

| Decisión                  | Valor                                                      |
|---------------------------|------------------------------------------------------------|
| `PUT` semántica           | Actualización parcial (no reemplazo total)                 |
| No hay `PATCH`            | La parcialidad la da `TaskUpdate` con campos opcionales    |
| `description`             | Opcional, por defecto `null`                               |
| `status` por defecto      | `"pending"` en creación                                    |
| `priority` por defecto    | `"medium"` en creación                                     |
| `GET /api/tasks` v1       | Lista plana sin filtros, paginación ni orden               |
