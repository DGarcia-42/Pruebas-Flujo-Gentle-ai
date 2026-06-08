# Spec de capacidad: `tasks-ui` (Vista de tareas — greenfield)

Esta spec define el comportamiento observable de la interfaz de usuario de tareas. No dicta implementación; rige lo que el usuario DEBE poder hacer y lo que el sistema DEBE mostrar.

Todos los términos normativos siguen **RFC 2119**. Los escenarios usan la sintaxis **Given / When / Then** y son directamente mapeables a tests Playwright E2E.

Los endpoints de tareas son **sin autenticación** — ningún escenario requiere token Bearer.

---

## Requirements

### Requirement: R-UI-01 — Acceso a la vista de tareas

La aplicación MUST ofrecer un mecanismo de navegación explícito para acceder a la vista de tareas desde el área autenticada. La vista de tareas MUST ser una vista diferenciada (no mezclada con el perfil de usuario).

#### Scenario: Navegar a la vista de tareas

- GIVEN que el usuario ha iniciado sesión y está en el área autenticada
- WHEN hace clic en el elemento de navegación hacia tareas (identificable por `data-testid="nav-tasks"`)
- THEN la vista de tareas se muestra
- AND el formulario de creación de tareas y la lista de tareas son visibles

---

### Requirement: R-UI-02 — Formulario de creación de tareas

La vista de tareas MUST incluir un formulario que permita crear tareas. El formulario MUST exponer los campos `title` (requerido), `description` (opcional) y `due_date` (opcional). Todos los campos interactivos y el botón de envío MUST tener atributos `data-testid`.

#### Scenario: E2E-07 — Crear tarea con todos los campos (happy path completo)

- GIVEN que el usuario está en la vista de tareas
- WHEN rellena `data-testid="task-title"` con un título
- AND rellena `data-testid="task-description"` con una descripción
- AND rellena `data-testid="task-due-date"` con una fecha futura o de hoy en formato `YYYY-MM-DD`
- AND hace clic en `data-testid="task-submit"`
- THEN la tarea aparece en la lista de tareas
- AND la lista muestra el título, la descripción y la fecha de vencimiento introducidos

#### Scenario: E2E-08 — Crear tarea sin campos opcionales

- GIVEN que el usuario está en la vista de tareas
- WHEN rellena únicamente `data-testid="task-title"` con un título
- AND deja `description` y `due_date` vacíos
- AND hace clic en `data-testid="task-submit"`
- THEN la tarea aparece en la lista de tareas
- AND la lista muestra el título
- AND no se muestra ninguna fecha de vencimiento ni descripción para esa tarea

---

### Requirement: R-UI-03 — Lista de tareas

La vista de tareas MUST mostrar todas las tareas existentes. Cada tarea MUST mostrar al menos su `title`. Si `description` no es `null`, MUST mostrarse. Si `due_date` no es `null`, MUST mostrarse.

#### Scenario: Lista vacía al inicio

- GIVEN que no existe ninguna tarea en el sistema
- WHEN el usuario accede a la vista de tareas
- THEN la lista de tareas está vacía (sin elementos de tarea visibles)

#### Scenario: Lista muestra tareas existentes

- GIVEN que existen tareas creadas previamente
- WHEN el usuario accede o regresa a la vista de tareas
- THEN la lista muestra cada tarea con su título
- AND cada tarea con `due_date` no nulo muestra la fecha de vencimiento

---

### Requirement: R-UI-04 — Indicador visual de tarea vencida (overdue)

Una tarea MUST mostrarse como "vencida" (overdue) cuando cumple todas estas condiciones: `due_date` es no nulo, `due_date` es anterior a la fecha actual, y `status` no es `"done"`. La indicación visual MUST ser perceptible (p.ej. una etiqueta o badge diferenciado). Tareas con `status = "done"` MUST NOT marcarse como vencidas aunque `due_date` sea pasado.

#### Scenario: E2E-09 — Tarea con due_date pasado muestra indicador overdue

- GIVEN que existe en el sistema una tarea con `due_date` en el pasado y `status = "pending"` (inyectada directamente via API, ya que el formulario rechaza fechas pasadas)
- WHEN el usuario accede a la vista de tareas
- THEN la tarea muestra un indicador visual de overdue identificable por `data-testid="badge-overdue"` (o clase CSS `.badge-overdue` verificable)

#### Scenario: Tarea completada con due_date pasado NO muestra overdue

- GIVEN que existe una tarea con `due_date` en el pasado y `status = "done"`
- WHEN el usuario accede a la vista de tareas
- THEN esa tarea NO muestra el indicador de overdue

---

### Requirement: R-UI-05 — Actualización de la lista tras creación

Tras una creación exitosa de tarea, la lista MUST actualizarse sin requerir recarga manual de página y MUST mostrar la tarea recién creada.

#### Scenario: Lista se actualiza automáticamente tras crear

- GIVEN que el usuario está en la vista de tareas
- WHEN crea una tarea y el envío es exitoso
- THEN la tarea recién creada aparece en la lista sin que el usuario recargue la página

---

## Fuera de alcance en esta versión

- Edición o eliminación de tareas desde la UI.
- Filtrado, paginación u ordenación de la lista.
- Visualización del `status` o `priority` de la tarea en la lista.
- Autenticación en los endpoints de tareas (permanecen sin auth).
