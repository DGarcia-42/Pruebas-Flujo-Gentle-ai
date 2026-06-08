# Delta para la capacidad `tasks`

Todos los términos normativos siguen **RFC 2119**. Los escenarios usan la sintaxis **Given / When / Then**.

---

## MODIFIED Requirements

### Requirement: Modelo de dominio `Task` — campos y tipos

El modelo `Task` MUST incluir el campo `due_date` (fecha de vencimiento) junto a los campos ya existentes.

| Campo        | Tipo JSON               | Requerido en creación | Valor por defecto |
|--------------|-------------------------|-----------------------|-------------------|
| `id`         | `string` (UUID4)        | No - generado         | UUID4 nuevo       |
| `title`      | `string`                | **Sí** (min 1 char)   | -                 |
| `description`| `string` o `null`       | No                    | `null`            |
| `status`     | `string` (enum)         | No                    | `"pending"`       |
| `priority`   | `string` (enum)         | No                    | `"medium"`        |
| `due_date`   | `string` (ISO 8601 date `"YYYY-MM-DD"`) o `null` | No | `null` |
| `created_at` | `string` (ISO 8601 UTC) | No - generado         | instante de creación |
| `updated_at` | `string` (ISO 8601 UTC) | No - generado         | instante de creación |

(Previously: el modelo no tenía campo `due_date`.)

#### Scenario: Tarea creada sin due_date — campo presente como null en respuesta

- GIVEN un body `{"title": "T"}` sin campo `due_date`
- WHEN se hace `POST /api/tasks`
- THEN la respuesta es `201 Created`
- AND el campo `due_date` en el body de respuesta es `null`

---

### Requirement: Schema `TaskCreate` — validación de due_date en creación

El endpoint `POST /api/tasks` MUST rechazar con `422` cualquier `due_date` que sea anterior a la fecha actual del servidor. Una fecha igual a hoy MUST ser aceptada.

(Previously: `TaskCreate` no tenía campo `due_date`.)

#### Scenario: Crear con due_date hoy — válido

- GIVEN un body `{"title": "T", "due_date": "<hoy>"}` (fecha de hoy en ISO 8601)
- WHEN se hace `POST /api/tasks`
- THEN la respuesta es `201 Created`
- AND el campo `due_date` en la respuesta coincide con la fecha enviada

#### Scenario: Crear con due_date futuro — válido

- GIVEN un body `{"title": "T", "due_date": "<mañana o posterior>"}` 
- WHEN se hace `POST /api/tasks`
- THEN la respuesta es `201 Created`
- AND el campo `due_date` en la respuesta coincide con la fecha enviada

#### Scenario: Crear con due_date en el pasado — 422

- GIVEN un body `{"title": "T", "due_date": "<ayer o anterior>"}` 
- WHEN se hace `POST /api/tasks`
- THEN la respuesta es `422 Unprocessable Entity`

#### Scenario: Crear con due_date null explícito — válido

- GIVEN un body `{"title": "T", "due_date": null}`
- WHEN se hace `POST /api/tasks`
- THEN la respuesta es `201 Created`
- AND el campo `due_date` en la respuesta es `null`

---

### Requirement: Schema `TaskUpdate` — due_date en actualización

El endpoint `PUT /api/tasks/{id}` MUST aceptar el campo `due_date` en el body. Cuando está presente, MUST aplicarse al estado de la tarea. No existe restricción de fecha pasada en actualización.

(Previously: `TaskUpdate` no tenía campo `due_date`.)

#### Scenario: Actualizar due_date con fecha pasada — válido en UPDATE

- GIVEN una tarea existente
- WHEN se hace `PUT /api/tasks/{id}` con body `{"due_date": "<ayer>"}` 
- THEN la respuesta es `200 OK`
- AND el campo `due_date` en la respuesta coincide con la fecha enviada

#### Scenario: Actualizar due_date a null — limpia la fecha

- GIVEN una tarea existente con `due_date` no nulo
- WHEN se hace `PUT /api/tasks/{id}` con body `{"due_date": null}`
- THEN la respuesta es `200 OK`
- AND el campo `due_date` en la respuesta es `null`

#### Scenario: PUT sin due_date — fecha previa conservada

- GIVEN una tarea existente con `due_date` no nulo
- WHEN se hace `PUT /api/tasks/{id}` con body que omite `due_date`
- THEN la respuesta es `200 OK`
- AND el campo `due_date` conserva el valor previo

---

### Requirement: Schema `TaskRead` — due_date incluido en todas las respuestas

Todos los endpoints que devuelven una tarea MUST incluir el campo `due_date` en el objeto `TaskRead`.

(Previously: `TaskRead` no tenía campo `due_date`.)

#### Scenario: Listar tareas — cada elemento incluye due_date

- GIVEN que existen tareas creadas con y sin `due_date`
- WHEN se hace `GET /api/tasks`
- THEN cada elemento del array incluye el campo `due_date` (valor ISO date string o `null`)

#### Scenario: Compatibilidad con payloads legacy

- GIVEN un body `{"title": "T"}` (sin mención a `due_date`)
- WHEN se hace `POST /api/tasks`
- THEN la respuesta es `201 Created`
- AND el campo `due_date` es `null`
- AND todos los demás campos siguen con sus valores por defecto habituales

---

## ADDED Requirements

No se añaden requirements completamente nuevos; los cambios anteriores son modificaciones al modelo y schemas existentes.
