# Tasks: detallar-tareas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380 total (PR1 ~140, PR2 ~240) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR1 (backend due_date) → PR2 (tasks UI + E2E) |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

### Branch Shape (feature-branch-chain)

```
main
 └─ feature/detallar-tareas          ← tracker branch (draft PR → main, no-merge until all children done)
     └─ sdd/detallar-tareas-backend  ← PR1 targets tracker
         └─ sdd/detallar-tareas-ui   ← PR2 targets PR1 branch
```

Only `feature/detallar-tareas` merges to main. PR1 diff = backend-only. PR2 diff = frontend+E2E only (no PR1 changes visible).

### Suggested Work Units

| Unit | Goal | Likely PR | Base branch |
|------|------|-----------|-------------|
| 1 — Backend due_date | `due_date` field on all schemas + `@field_validator` on TaskCreate + pytest RED→GREEN | PR1 | `feature/detallar-tareas` |
| 2 — Tasks UI + Playwright E2E | api/client.ts helpers + 3 new components + App.tsx + CSS + E2E-07/08/09 | PR2 | `sdd/detallar-tareas-backend` |

---

## PR1 — Backend `due_date`

Strict TDD: every behavior gets a RED (failing test) commit before its GREEN (implementation) commit.

### T-01 — RED: `test_schemas.py` — `due_date` validation unit tests

- [ ] In `backend/tests/test_schemas.py`, add tests for `TaskCreate` validator (patch `app.schemas.task.date`):
  - `test_due_date_past_raises`: `due_date = yesterday` → `ValidationError`
  - `test_due_date_today_valid`: `due_date = today` → no error
  - `test_due_date_future_valid`: `due_date = tomorrow` → no error
  - `test_due_date_none_valid`: `due_date = None` → no error
  - `test_taskupdate_past_date_valid`: `due_date = yesterday` in `TaskUpdate` → no error (no validator on update)
- Commit: `test(tasks): RED — due_date validator unit tests on TaskCreate/TaskUpdate schemas`
- Spec: `TaskCreate` 422-past, today/future/None valid; `TaskUpdate` no past restriction

### T-02 — GREEN: `schemas/task.py` — add `due_date` to all three schemas + `@field_validator`

- [ ] In `backend/app/schemas/task.py`:
  - Add `from datetime import date` (keep existing `datetime` import)
  - Add `due_date: date | None = None` to `TaskCreate`, `TaskUpdate`, `TaskRead`
  - Add `@field_validator('due_date') @classmethod due_date_not_in_past` on `TaskCreate` only → `raise ValueError('due_date must not be in the past')` when `v is not None and v < date.today()`
- Commit: `feat(tasks): add due_date field to TaskCreate/TaskUpdate/TaskRead with past-date validator`
- Spec: model domain + all three schema requirements

### T-03 — RED: `test_service.py` — service passthrough

- [ ] In `backend/tests/test_service.py`, add:
  - `test_create_task_passes_due_date_through`: `TaskService.create(TaskCreate(title="T", due_date=tomorrow))` → returned `TaskRead.due_date == tomorrow`
  - `test_create_task_due_date_none_by_default`: `TaskService.create(TaskCreate(title="T"))` → `due_date is None`
- Commit: `test(tasks): RED — service passthrough tests for due_date`
- Spec: `TaskRead` includes `due_date` in all responses

### T-04 — GREEN: `services/task_service.py` — pass `due_date` through `create()`

- [ ] In `backend/app/services/task_service.py`, update `create()` to pass `due_date=data.due_date` into the `TaskRead(...)` constructor (if not already using `**data.model_dump()` which would absorb it automatically).
- [ ] Verify `update()` path: `model_dump(exclude_unset=True)` + `model_copy(update=...)` already absorbs `due_date` transparently — confirm with a quick read, no change needed if so.
- Commit: `feat(tasks): wire due_date through TaskService.create()`
- Spec: service passthrough

### T-05 — RED: `test_tasks_api.py` — integration tests

- [ ] In `backend/tests/test_tasks_api.py`, add:
  - `test_create_task_with_due_date_201`: POST with `due_date=tomorrow_str` → 201, response `due_date == tomorrow_str`
  - `test_create_task_past_due_date_422`: POST with `due_date=yesterday_str` → 422
  - `test_create_task_without_due_date_null`: POST `{"title":"T"}` → 201, `due_date is None`
  - `test_list_tasks_includes_due_date`: create two tasks (one with, one without due_date), GET /api/tasks → both include `due_date` key
  - `test_update_task_due_date_past_valid`: PUT with `due_date=yesterday_str` → 200, echoes value
  - `test_update_task_clears_due_date`: PUT `{"due_date": null}` → 200, `due_date is None`
  - `test_update_task_preserves_due_date_when_omitted`: PUT without `due_date` → 200, `due_date` unchanged
  - `test_legacy_payload_still_works`: POST `{"title":"T"}` → 201, all defaults present
- Commit: `test(tasks): RED — API integration tests for due_date scenarios`
- Spec: all scenarios from `specs/tasks/spec.md`

### T-06 — GREEN: verify all `backend/` tests pass

- [ ] Run `pytest` from `backend/` — all tests must pass (0 failures).
- [ ] Fix any unexpected failures before committing.
- Commit: _(no separate commit — T-02 and T-04 are the GREEN commits; this is a verification gate)_
- Spec: full suite gate before PR1 is ready

**PR1 commit story** (ordered, each self-contained):
1. `test(tasks): RED — due_date validator unit tests on TaskCreate/TaskUpdate schemas` (T-01)
2. `feat(tasks): add due_date field to TaskCreate/TaskUpdate/TaskRead with past-date validator` (T-02)
3. `test(tasks): RED — service passthrough tests for due_date` (T-03)
4. `feat(tasks): wire due_date through TaskService.create()` (T-04)
5. `test(tasks): RED — API integration tests for due_date scenarios` (T-05)

All five commits land on `sdd/detallar-tareas-backend`. PR1 targets `feature/detallar-tareas`.

---

## PR2 — Tasks UI + Playwright E2E

Strict TDD: E2E tests are written first (RED — failing), then components are implemented (GREEN).

> COORDINATION LOCK WARNING: `frontend/src/App.tsx` and `frontend/src/index.css` may be under an active edit lock from another Quorum session. Before editing either file, run `git status` and verify no staged/unstaged changes exist. New files (`TasksView.tsx`, `TaskCreateForm.tsx`, `TaskList.tsx`, `e2e/tasks.spec.ts`) are unaffected and can be written immediately.

### T-07 — `api/client.ts` — Task interface + helpers

- [ ] In `frontend/src/api/client.ts`, add:
  - `interface Task { id: string; title: string; description: string|null; status: 'pending'|'in_progress'|'done'; priority: 'low'|'medium'|'high'; due_date: string|null; created_at: string; updated_at: string }`
  - `interface TaskCreateRequest { title: string; description?: string; due_date?: string }`
  - `export function listTasks(): Promise<Task[]|null>` → `apiFetch<Task[]>('GET', '/api/tasks')`
  - `export function createTask(data: TaskCreateRequest): Promise<Task|null>` → `apiFetch<Task>('POST', '/api/tasks', data)`
- Commit: `feat(tasks): add Task interface and listTasks/createTask helpers to api/client.ts`
- Spec: R-UI-02, R-UI-03 (API contract)

### T-08 — RED: `e2e/tasks.spec.ts` — E2E-07, E2E-08, E2E-09 (failing)

- [ ] Create `e2e/tasks.spec.ts` with:
  - `registerAndLogin` reuse helper from `e2e/auth.spec.ts` or inline an `authAndNavigateToTasks()` helper
  - `createTaskViaApi(request, data)` helper using `page.request.post('/api/tasks', {data})` — no auth needed
  - `E2E-07`: navigate to tasks view (`nav-tasks`), fill `task-title`/`task-description`/`task-due-date` (today or future), submit, assert task appears with all three fields
  - `E2E-08`: navigate to tasks view, fill only `task-title`, submit, assert task appears, no `due_date`/`description` shown
  - `E2E-09`: inject past-date task via `createTaskViaApi` (bypass create-time validator), navigate to tasks view, assert `data-testid="badge-overdue"` visible on that task
  - Use `Date.now()` for unique titles per run
- Commit: `test(tasks): RED — Playwright E2E-07/08/09 for tasks UI`
- Spec: R-UI-02 (E2E-07/08), R-UI-04 (E2E-09), R-UI-01 (nav-tasks)

### T-09 — `TaskCreateForm.tsx` — controlled form component

- [ ] Create `frontend/src/components/TaskCreateForm.tsx`:
  - Controlled inputs: `data-testid="task-title"` (required), `data-testid="task-description"` (textarea, optional), `data-testid="task-due-date"` (date input, optional)
  - Submit button `data-testid="task-submit"`
  - On submit: call `createTask(...)`, call `onTaskCreated()` prop on success, clear fields
  - Props: `onTaskCreated: () => void`
- Commit: `feat(tasks): add TaskCreateForm component with data-testid selectors`
- Spec: R-UI-02, R-UI-05

### T-10 — `TaskList.tsx` — presentational list with overdue badge

- [ ] Create `frontend/src/components/TaskList.tsx`:
  - Props: `tasks: Task[]`
  - Renders each task in `.task-list` / `.task-item`
  - Shows `title` always; shows `description` when not null; shows `due_date` (via `toLocaleDateString()`) when not null
  - `isOverdue(task)` = `task.due_date !== null && task.due_date < todayISO && task.status !== 'done'` where `todayISO = new Date().toISOString().split('T')[0]`
  - When `isOverdue`, render `<span data-testid="badge-overdue" className="badge-overdue">Overdue</span>`
- Commit: `feat(tasks): add TaskList presentational component with overdue badge`
- Spec: R-UI-03, R-UI-04

### T-11 — `TasksView.tsx` — container

- [ ] Create `frontend/src/components/TasksView.tsx`:
  - Fetches `listTasks()` on mount (useEffect) and stores in `tasks` state
  - Re-fetches after `TaskCreateForm` calls `onTaskCreated()`
  - Renders `<TaskCreateForm onTaskCreated={refresh} />` and `<TaskList tasks={tasks} />`
- Commit: `feat(tasks): add TasksView container with fetch on mount and post-create refresh`
- Spec: R-UI-03, R-UI-05

### T-12 — `index.css` — task CSS tokens

> Check git status before editing. If file has unsaved/staged changes from another session, coordinate first.

- [ ] In `frontend/src/index.css`, append:
  - `.task-list` — vertical list layout
  - `.task-item` — card/row with border-only depth (matches existing design system)
  - `.task-item__meta` — muted secondary text for date/description
  - `.badge-overdue` — uses `var(--color-destructive)` or equivalent red/danger token; small pill badge
- Commit: `feat(tasks): add task-list, task-item, task-item__meta, badge-overdue CSS`
- Spec: R-UI-04 (visual overdue indicator)

### T-13 — `App.tsx` — wire `'tasks'` view + nav

> Check git status before editing. If file has unsaved/staged changes from another session, coordinate first.

- [ ] In `frontend/src/App.tsx`:
  - Add `'tasks'` to the `View` union type
  - Import `TasksView`
  - In the authenticated area, add `<button data-testid="nav-tasks" onClick={() => setView('tasks')}>Tasks</button>` to the topbar
  - Render `{view === 'tasks' && <TasksView />}` in the app shell
- Commit: `feat(tasks): wire TasksView into App with nav-tasks button`
- Spec: R-UI-01

### T-14 — GREEN: verify E2E suite and build

- [ ] Run `npx playwright test e2e/tasks.spec.ts` from repo root — all 3 tests must pass.
- [ ] Run `npm run build` from `frontend/` — exit 0, zero TypeScript errors.
- [ ] Fix any failures before considering PR2 done.
- Commit: _(verification gate — no separate commit unless a bug fix is needed)_

**PR2 commit story** (ordered, each self-contained):
1. `feat(tasks): add Task interface and listTasks/createTask helpers to api/client.ts` (T-07)
2. `test(tasks): RED — Playwright E2E-07/08/09 for tasks UI` (T-08)
3. `feat(tasks): add TaskCreateForm component with data-testid selectors` (T-09)
4. `feat(tasks): add TaskList presentational component with overdue badge` (T-10)
5. `feat(tasks): add TasksView container with fetch on mount and post-create refresh` (T-11)
6. `feat(tasks): add task-list, task-item, task-item__meta, badge-overdue CSS` (T-12)
7. `feat(tasks): wire TasksView into App with nav-tasks button` (T-13)

All seven commits land on `sdd/detallar-tareas-ui`. PR2 targets `sdd/detallar-tareas-backend`.

---

## Task Summary

| PR | Tasks | Spec requirements covered |
|----|-------|--------------------------|
| PR1 — Backend | T-01..T-06 (5 commits) | domain model, TaskCreate 422, TaskUpdate no-restriction, TaskRead all responses |
| PR2 — Frontend | T-07..T-14 (7 commits) | R-UI-01..R-UI-05, E2E-07/08/09 |
| Total | 14 tasks | All spec requirements |

## Parallelism Notes

Within PR1: T-01→T-02 (sequential RED→GREEN), T-03→T-04 (sequential RED→GREEN), T-05 can be written after T-02 is done (schemas exist). T-06 is a gate, not a commit.

Within PR2: T-07 (client.ts) is independent and can be written first. T-08 (E2E RED) must come before T-09–T-13 (GREEN). T-09, T-10, T-11 are independent of each other once T-07 is done. T-12 (CSS) and T-13 (App.tsx) must check git status before editing (coordination lock risk).
