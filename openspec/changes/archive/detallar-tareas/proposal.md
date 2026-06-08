# Proposal: detallar-tareas

## Intent

Tasks currently expose `title`, `description`, `status`, `priority` but no deadline, and
there is no UI to create or browse tasks (the React app only has auth + profile). Users
cannot tell when a task is due or which tasks are overdue. This change adds an optional
`due_date` to the task model and ships a greenfield tasks UI that surfaces `description`
and `due_date` and highlights overdue tasks. `description` already exists and is fully
wired — no work there.

## Scope

### In Scope
- Backend: add `due_date` (optional `date`) to `TaskCreate`, `TaskUpdate`, `TaskRead`.
- Backend: validate "not in the past" ONLY on create via Pydantic `@field_validator` → `422`. Today is allowed.
- Frontend: greenfield tasks UI — create form (title + description + due_date), task list showing due date, overdue highlight.
- Frontend: new `'tasks'` view in `App.tsx` + nav; `Task`/`TaskCreateRequest` interfaces + `listTasks`/`createTask` API helpers.
- Tests: pytest (create with/without new fields, past-date `422`, legacy payloads still parse) + Playwright E2E (E2E-07/08/09).

### Out of Scope
- `description` field — already exists and fully wired. No change.
- Adding auth to task endpoints — tasks stay unauthenticated (current contract).
- `due_date` validation on UPDATE — update is unrestricted per scope.
- Task edit/delete UI — only create + list this round.

## Capabilities

### New Capabilities
- `tasks-ui`: greenfield React tasks view — create form, list, overdue highlight, API client helpers, nav wiring.

### Modified Capabilities
- `tasks`: adds optional `due_date` field across create/update/read; create rejects past dates with `422`; endpoints stay backward-compatible (optional field defaults to `null`).

## Approach

Backend (PR1): add `from datetime import date`; add `due_date: date | None = None` to the
three schemas; add a `@field_validator('due_date')` on `TaskCreate` that raises
`ValueError` (→ `422`) when the date is before `date.today()`. Service and in-memory
repository need no changes — `model_copy(update=...)` and `model_dump(exclude_unset=True)`
absorb the new optional field transparently. `TaskUpdate.due_date` defaults to `None` and
is only applied when sent (preserves omitted values; explicit `null` clears).

Frontend (PR2): `TasksView` container fetches `GET /api/tasks` on mount + after create;
renders presentational `TaskCreateForm` + `TaskList`. Overdue = `due_date < todayISO AND
status !== 'done'`, compared as ISO date strings (no `Date` math). New `'tasks'` view in
`App.tsx` reachable from a topbar nav button. E2E-09 injects a past-date task via
`page.request.post()` (bypassing form validation) to assert the overdue badge.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/schemas/task.py` | Modified | `due_date` on 3 schemas + `field_validator` + `date` import |
| `backend/tests/test_schemas.py`, `test_tasks_api.py`, `test_service.py` | Modified | past-date `422`, create with/without `due_date`, legacy payloads |
| `frontend/src/api/client.ts` | Modified | `Task`/`TaskCreateRequest` + `listTasks`/`createTask` |
| `frontend/src/components/TasksView.tsx`, `TaskCreateForm.tsx`, `TaskList.tsx` | New | container + form + list |
| `frontend/src/App.tsx` | Modified | `'tasks'` view + nav |
| `frontend/src/index.css` | Modified | `.task-list`, `.task-item`, `.badge-overdue` |
| `e2e/tasks.spec.ts` | New | E2E-07/08/09 |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `date.today()` not mockable in validator | Low | `patch('app.schemas.task.date')` in TDD tests |
| TS `new Date("YYYY-MM-DD")` TZ ambiguity | Low | Overdue uses lexicographic ISO string compare, not `Date` math |
| `App.tsx` under Quorum lock | Med | Apply agent sequences PR2 to avoid editing while locked |
| E2E-09 needs past-date task the form rejects | Med | Inject via direct `page.request.post()` (tasks unauthenticated) |

## Rollback Plan

PR1: revert the `schemas/task.py` change — `due_date` is purely additive and optional, so
removing it leaves the API contract unchanged. PR2 is greenfield (new view + components);
revert by removing the `'tasks'` view wiring and the new files. Neither PR mutates existing
behavior, so rollback is a clean `git revert` of the respective PR branch.

## Dependencies

- PR2 (frontend + E2E) depends on PR1 (backend `due_date`) being merged/reachable so the UI and E2E can round-trip the field.

## Delivery

Auto-chain / feature-branch-chain → two chained PRs:
- **PR1 — backend**: `due_date` field + validator + pytest. Self-contained, mergeable alone.
- **PR2 — frontend + E2E**: tasks UI + Playwright suite. Targets PR1's branch in the chain.

## Success Criteria

- [ ] Create with valid/future/today `due_date` succeeds; past `due_date` returns `422`.
- [ ] Legacy `{"title": "..."}` payloads still create tasks (`due_date` → `null`).
- [ ] Tasks UI creates tasks and lists them with description + due date; overdue tasks are visibly highlighted.
- [ ] `pytest` green (backend) and `npx playwright test` green (E2E-07/08/09).
