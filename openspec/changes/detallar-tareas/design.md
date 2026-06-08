# Design: detallar-tareas

## Technical Approach

Two chained slices map to the proposal. **PR1 (backend)**: add an optional `due_date: date | None = None` to all three task schemas and enforce "not in the past" ONLY on create via a Pydantic `@field_validator` (→ 422). Service and in-memory repo are untouched — `model_copy`/`model_dump(exclude_unset=True)` absorb the new optional field transparently. **PR2 (frontend + E2E)**: a greenfield `'tasks'` view following the existing container/presentational pattern (`TasksView` container + `TaskCreateForm` + `TaskList`), new `Task`/`createTask`/`listTasks` helpers on the existing `apiFetch` wrapper, overdue highlight via lexicographic ISO date compare, and Playwright E2E-07/08/09 on the already-configured dual webServer.

## Architecture Decisions

### Decision: due_date validation placement
**Choice**: Pydantic `@field_validator('due_date')` on `TaskCreate` only → raises `ValueError` → FastAPI 422. `date.today()` called inside the validator (request-parse time). Today allowed (`v < date.today()` rejects). No validator on `TaskUpdate`.
**Alternatives**: Service-level check raising a 400/custom exception; hybrid schema-type + service-rule.
**Rationale**: Consistent with the existing `title=Field(min_length=1)` 422 signal; fails before the service runs; zero service/HTTP coupling; auto-documented in OpenAPI. `date.today()` is mockable in strict-TDD tests via `patch('app.schemas.task.date')`. A date-only field has no timezone, so server-local `date.today()` is correct and pragmatic.

### Decision: Frontend tasks architecture
**Choice**: New `'tasks'` value in the `App.tsx` `View` union, reached by topbar nav buttons. `TasksView` (container: fetch `GET /api/tasks` on mount + after create, owns `tasks` state), `TaskCreateForm` (controlled title/description/due_date, calls `createTask`), `TaskList` (presentational, renders overdue badge). `data-testid` on every interactive element + feedback.
**Alternatives**: Inline tasks section inside `Profile` (rejected — God component, poor testability).
**Rationale**: Matches the established `Profile`/`ChangePasswordForm` container-presentational split; single-responsibility; testable nav with simple `data-testid` clicks; reuses existing `app-shell`/`app-topbar`/`topbar-action` CSS.

### Decision: Overdue logic
**Choice**: `isOverdue = due_date !== null && due_date < todayISO && status !== 'done'` where `todayISO = new Date().toISOString().split('T')[0]`. Lexicographic ISO string compare — NO `Date` subtraction. Display via `new Date(due_date).toLocaleDateString()`. New CSS `.badge-overdue` (uses `var(--color-destructive)`), `.task-list`, `.task-item`, `.task-item__meta` reusing existing tokens.
**Alternatives**: `new Date(a) < new Date(b)` subtraction (rejected — `new Date('YYYY-MM-DD')` parses as UTC midnight, ambiguous vs local).
**Rationale**: ISO `YYYY-MM-DD` strings sort lexicographically identical to chronological order; zero timezone risk.

### Decision: API client + auth posture
**Choice**: Add `Task` + `TaskCreateRequest` interfaces and `listTasks()`/`createTask(data)` on the existing `apiFetch` wrapper. Tasks stay unauthenticated; `apiFetch` attaches a Bearer token only if one exists, which is harmless.
**Rationale**: Reuses the proven wrapper (204→null, `ApiError` throw); no new auth wiring per scope.

### Decision: E2E-09 overdue injection
**Choice**: Inject a past-date task via `page.request.post('/api/tasks', { data: { title, due_date: yesterday } })`, bypassing the create-time 422 validator, then assert the overdue badge in the UI. Unique data per run (`Date.now()`).
**Rationale**: Spec requires "overdue highlight visible", not "user inputs past dates". Tasks have no auth, so direct injection is trivial and legitimate.

## Data Flow

    TaskCreateForm ──createTask()──→ apiFetch ──POST /api/tasks──→ TaskService.create
         │                                                              │ (422 if past due_date)
         └──onTaskCreated()──→ TasksView ──listTasks()──→ GET /api/tasks ──→ repo.get_all()
                                    │
                                    └──tasks[]──→ TaskList ──isOverdue?──→ .badge-overdue

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/schemas/task.py` | Modify | `from datetime import date`; `due_date: date \| None = None` on `TaskCreate`/`TaskUpdate`/`TaskRead`; `@field_validator('due_date')` on `TaskCreate` |
| `backend/app/services/task_service.py` | Modify | `create()` passes `due_date=data.due_date` into `TaskRead` |
| `backend/tests/test_schemas.py` | Modify | RED: past→ValidationError, today/future/None→valid (patch `app.schemas.task.date`) |
| `backend/tests/test_tasks_api.py` | Modify | RED: create with due_date 201, past due_date 422, list includes due_date, legacy `{title}` still 201 |
| `backend/tests/test_service.py` | Modify | RED: service create passes due_date through |
| `frontend/src/api/client.ts` | Modify | `Task`/`TaskCreateRequest` interfaces + `listTasks`/`createTask` |
| `frontend/src/components/TasksView.tsx` | Create | Container: fetch on mount + after create |
| `frontend/src/components/TaskCreateForm.tsx` | Create | Controlled form, `data-testid` on all fields |
| `frontend/src/components/TaskList.tsx` | Create | Presentational, overdue badge |
| `frontend/src/App.tsx` | Modify | `'tasks'` in `View` union + nav buttons (LOCKED — see Risks) |
| `frontend/src/index.css` | Modify | `.task-list`/`.task-item`/`.task-item__meta`/`.badge-overdue` (LOCKED — see Risks) |
| `e2e/tasks.spec.ts` | Create | E2E-07/08/09 + `createTaskViaApi` helper |

## Interfaces / Contracts

```python
# backend/app/schemas/task.py
from datetime import date

class TaskCreate(BaseModel):
    # ...existing fields...
    due_date: date | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("due_date must not be in the past")
        return v
# TaskUpdate.due_date and TaskRead.due_date: `date | None = None` (no validator)
```

```typescript
// frontend/src/api/client.ts
export interface Task {
  id: string; title: string; description: string | null;
  status: 'pending' | 'in_progress' | 'done';
  priority: 'low' | 'medium' | 'high';
  due_date: string | null; created_at: string; updated_at: string;
}
export interface TaskCreateRequest {
  title: string; description?: string | null; due_date?: string | null;
}
export function listTasks(): Promise<Task[] | null>;     // GET  /api/tasks
export function createTask(d: TaskCreateRequest): Promise<Task | null>; // POST /api/tasks
```

## Testing Strategy (strict TDD: RED → GREEN per behavior)

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (schemas) | past→ValidationError; today/future/None→valid | `pytest.raises(ValidationError)`; patch `app.schemas.task.date` for deterministic "today" |
| Unit (service) | `create` passes `due_date` through to `TaskRead` | direct `TaskService(repo).create(TaskCreate(...))` |
| Integration (API) | 201 with due_date; 422 past; list echoes due_date; legacy `{title}` 201 | FastAPI `TestClient` + isolated `TaskRepository()` fixture |
| E2E | E2E-07 all fields; E2E-08 optional fields absent; E2E-09 overdue badge via API injection | Playwright dual webServer; `data-testid` selectors; `Date.now()` uniqueness |

Order per behavior: write failing test (RED) before the schema/component change (GREEN). Backend RED suite precedes the validator; each frontend component's E2E/assertion precedes wiring.

## Migration / Rollout

No migration required. In-memory repo is wiped on restart; `due_date` is additive/optional so legacy `{title}` payloads parse unchanged. PR1 rollback: revert `schemas/task.py` (additive only). PR2 rollback: remove `'tasks'` wiring + new files. Neither mutates existing behavior — clean per-branch revert.

## Open Questions

- [ ] **App.tsx / index.css Quorum lock**: both files are under an active coordination lock from another session. PR2 apply MUST sequence its edits to these two files AFTER the lock clears, or coordinate to avoid "modified since last read" conflicts. The new component files and `client.ts`/`e2e` are unaffected and can proceed independently.
