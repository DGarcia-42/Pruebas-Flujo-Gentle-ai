# Archive Report: detallar-tareas

**Change**: detallar-tareas
**Archived**: 2026-06-08
**Branch**: sdd/detallar-tareas-frontend (integrated tip: PR1 backend + PR2 frontend)
**Artifact store**: hybrid (Engram + OpenSpec)
**Verdict**: PASS WITH WARNINGS — 0 CRITICAL, 1 WARNING (W-01, closed), 2 SUGGESTIONS

---

## Scope Delivered

Added optional `due_date` field to the task domain model and shipped a greenfield tasks UI.

### Backend (PR1 — `sdd/detallar-tareas-backend`)
- `due_date: date | None = None` added to `TaskCreate`, `TaskUpdate`, `TaskRead` schemas.
- Pydantic `@field_validator('due_date')` on `TaskCreate` only: rejects past dates with 422; today is allowed. No restriction on `TaskUpdate`.
- `TaskService.create()` wires `due_date=data.due_date` through.
- `model_dump(exclude_unset=True)` + `model_copy` absorb the field in update path transparently.
- Legacy `{"title": "T"}` payloads continue to work (due_date defaults to null).

### Frontend (PR2 — `sdd/detallar-tareas-frontend`)
- New `Task` + `TaskCreateRequest` interfaces and `listTasks()`/`createTask()` helpers on existing `apiFetch` wrapper.
- New components: `TasksView` (container), `TaskCreateForm` (controlled form), `TaskList` (presentational with overdue badge).
- `isOverdue` logic: lexicographic ISO date string compare (`due_date < todayISO && status !== 'done'`); no `Date` subtraction (avoids UTC-midnight ambiguity).
- `nav-tasks` button wired on BOTH login screen (`App.tsx`) and Profile topbar (`Profile.tsx`).
- New CSS tokens: `.task-list`, `.task-item`, `.task-item__meta`, `.badge-overdue`.
- Playwright E2E: `e2e/tasks.spec.ts` — E2E-07, E2E-08, E2E-09.

---

## Test Results

| Suite | Result | Count |
|-------|--------|-------|
| pytest (backend) | PASS | 123 passed, 0 failed |
| Playwright E2E | PASS | 9/9 (6 auth + 3 tasks) |
| TypeScript build | PASS | 0 errors, 25 modules |
| **Total** | **PASS** | **123 pytest + 9 E2E** |

---

## Spec Compliance

- **19/19 scenarios** from both domains (`tasks` MODIFIED + `tasks-ui` NEW) verified as COMPLIANT.
- Full compliance matrix in verify-report (Engram observation #88).

---

## W-01 Resolution

**Warning**: R-UI-01 spec gap — `nav-tasks` accessible from unauthenticated login screen (spec wording said "authenticated area" only).

**Resolution (closed)**: The baseline spec `openspec/specs/tasks-ui/spec.md` has been updated with the correct R-UI-01 wording: navigation is available from BOTH the login screen AND the authenticated area, because task endpoints are unauthenticated by design. This is not a regression; it is an intentional, better UX decision that the verification phase flagged and archive now closes.

---

## Delivery Chain (feature-branch-chain)

```
main
 └─ feature/detallar-tareas          ← tracker branch
     └─ sdd/detallar-tareas-backend  ← PR1 (backend due_date)
         └─ sdd/detallar-tareas-frontend ← PR2 (tasks UI + E2E) ← FINAL BRANCH
```

---

## Specs Promoted to Baseline

| Domain | Action | File |
|--------|--------|------|
| `tasks` | UPDATED — due_date requirements merged in | `openspec/specs/tasks/spec.md` |
| `tasks-ui` | CREATED — new baseline from delta | `openspec/specs/tasks-ui/spec.md` |

The `tasks` spec now contains all original requirements PLUS the `due_date` additions:
- `R-MOD-08` (new): due_date invariant
- `R-LIST-05` (new): each list element includes due_date
- `R-CREATE-09` through `R-CREATE-11` (new): due_date creation rules
- `R-UPDATE-10` through `R-UPDATE-12` (new): due_date update rules
- Scenarios C-9 through C-13 (new create scenarios)
- Scenarios U-9 through U-11 (new update scenarios)

Total requirements: 33 (old) → 40 (merged)
Total scenarios: 27 (old) → 36 (merged)

---

## Suggestions (Carry Forward)

These were SUGGESTIONS from the verify report — non-blocking, no action required for archive:

- **S-01**: No `pytest-cov` configured. Consider adding coverage tooling for future changes.
- **S-02**: The "done task with past due_date = no badge" scenario (R-UI-04 second scenario) has only static code coverage, no E2E test. Consider a future E2E or component test.

---

## Engram Observation IDs (Traceability)

| Artifact | Observation ID |
|----------|----------------|
| proposal | #83 |
| spec | #85 |
| design | #84 |
| tasks | #86 |
| verify-report | #88 |
| archive-report | (this document — saved to Engram as sdd/detallar-tareas/archive-report) |

---

## SDD Cycle Complete

The `detallar-tareas` change has been fully planned, implemented, verified, and archived.
All 14 tasks (T-01..T-14) completed. 0 CRITICAL issues. W-01 closed by spec update. Ready for the next change.
