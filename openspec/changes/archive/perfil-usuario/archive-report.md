# Archive Report: perfil-usuario

**Change:** perfil-usuario  
**Archived:** 2026-06-08  
**Status:** COMPLETE — PASS (0 CRITICAL, 1 WARNING [non-blocking], 1 SUGGESTION)

---

## Executive Summary

The **perfil-usuario** change has been fully implemented, verified, and archived. The change adds user profile visibility (`GET /api/auth/me`), password change capability (`PUT /api/auth/me/password`), and the first user-facing frontend (React + Vite SPA with Playwright E2E validation) to the existing authentication backend. All 18 tasks across 3 delivery slices have been completed successfully:

- **PR1 (Backend):** 9 tasks, 107 pytest cases (all PASS)
- **PR2 (Frontend scaffold + auth screens):** 5 tasks, build verified (0 TypeScript errors)
- **PR3 (Profile + change-password + Playwright E2E):** 4 tasks, 6 E2E tests (all PASS)

---

## Delivery Summary

### PR1 — Backend (branch: `sdd/perfil-usuario-backend`)
**Task count:** T-01 through T-09 (9 tasks) | **Test result:** 107 passed (0 failures)

- `get_by_token` / `get_by_id` repo accessors (T-01)
- `InvalidCurrentPassword` domain exception for 400 responses (T-02)
- `ChangePasswordRequest` schema with validation (T-03)
- `get_current_user` FastAPI dependency with Bearer token validation (T-04)
- `get_me(user) -> UserPublic` service method (T-05)
- `change_password(user, current, new) -> None` service method (T-06)
- `GET /api/auth/me` endpoint (ME-01..05 scenarios) (T-07)
- `PUT /api/auth/me/password` endpoint (PASS-01..09 scenarios) (T-08)
- Final verification pass (T-09)

**Files modified:** 
- `backend/app/repositories/user_repository.py`
- `backend/app/services/exceptions.py`
- `backend/app/schemas/auth.py`
- `backend/app/dependencies.py`
- `backend/app/services/auth_service.py`
- `backend/app/routers/auth.py`
- `backend/tests/test_auth.py`

**Commits:** 9 commits implementing T-01..T-08 + W-01 (W-01 = RS-03.2 orphan token coverage)

---

### PR2 — Frontend Scaffold + Auth Screens (branch: `sdd/perfil-usuario-frontend-auth`)
**Task count:** T-10 through T-14 (5 tasks) | **Build result:** tsc + vite, 0 TypeScript errors

- Vite + React 19 + TypeScript 6 initialization (T-10)
- `api/client.ts` fetch wrapper with Bearer token attachment (T-11)
- `auth/storage.ts` in-memory token storage module (T-12)
- RegisterForm, LoginForm, App.tsx conditional rendering (T-13)
- Vite dev proxy `/api -> http://127.0.0.1:8000` (T-14)

**Files created:**
- `frontend/` — complete React+Vite project
  - `src/api/client.ts` — native fetch, Bearer header, error parsing, 204→null
  - `src/auth/storage.ts` — module-level `let _token` (in-memory, lost on reload)
  - `src/components/RegisterForm.tsx`, `LoginForm.tsx` — form UIs with E2E selectors
  - `src/App.tsx` — conditional view state (register/login/profile)
  - `src/index.css` — design system (borders-only, slate-900 ink, blue-600 accent)
  - `vite.config.ts` — dev proxy config

**Commits:** 5 commits implementing T-10..T-14

---

### PR3 — Profile + Change-Password + Playwright E2E (branch: `sdd/perfil-usuario-profile-e2e`)
**Task count:** T-15 through T-18 (4 tasks) | **Test result:** 6 E2E tests PASS (100%)

- Profile.tsx component with GET /api/auth/me on mount (T-15)
- ChangePasswordForm.tsx component with 204 success + 400 error handling (T-16)
- Playwright config with dual webServer (uvicorn + vite) (T-17)
- E2E suite with E2E-01..06 scenarios (T-18)

**Files created/modified:**
- `frontend/src/components/Profile.tsx` — data-testid="profile-email", "profile-username"
- `frontend/src/components/ChangePasswordForm.tsx` — data-testid="pw-success", "pw-error"
- `playwright.config.ts` — webServer array, baseURL=http://localhost:5173
- `e2e/auth.spec.ts` — 6 E2E scenarios covering all user flows
- `package.json` (root) — @playwright/test devDependency

**Commits:** 4 commits implementing T-15..T-18

---

## Verification Report (PASS)

**Backend:** 107 pytest cases all PASS (0 failures)  
**Frontend:** tsc + vite build, 0 TypeScript errors, 22 modules transformed  
**E2E:** 6 Playwright test scenarios all PASS (100%)

### Test Coverage

| Category | Scenarios | Status |
|---|---|---|
| GET /api/auth/me (ME-01..05) | 5 scenarios | PASS |
| PUT /api/auth/me/password (PASS-01..09) | 9 scenarios | PASS |
| Token dependency (DEP-01, W-01) | 2 scenarios | PASS |
| E2E flows (E2E-01..06) | 6 scenarios | PASS |

**Spec coverage:** All RF-03, RF-04, RF-05, RF-06, RF-07, RS-03 requirements verified.

---

## Spec Promotion

The delta spec has been **merged into the canonical baseline** at `openspec/specs/user-auth/spec.md`:

- **RF-03** (GET /api/auth/me) — added to baseline
- **RF-04** (PUT /api/auth/me/password) — added to baseline, with status **204** (success), **400** (wrong current pw), **401** (bad token), **422** (schema violation)
- **RS-03** (Bearer token validation via `get_current_user`) — added to baseline
- **RF-05, RF-06, RF-07** (Frontend requirements) — added to baseline
- **Out-of-scope notes** — updated to reflect password change (NOT email/username editing), in-memory token storage, and Playwright E2E policy
- **Files expected** — updated to list all backend, frontend, and E2E changes

The baseline spec now reads as a coherent, complete description of the user-auth capability including profile visibility, password management, and the first end-to-end validated user interface.

---

## Findings from Verify Report

### PASS — Verdict
All test suites passed independently:
- Backend pytest: 107 passed in 7.84s
- Frontend build: 0 TypeScript errors
- Playwright E2E: 6 passed in 6.6s

### WARNING (non-blocking)
**RegisterForm/LoginForm onSuccess prop naming inconsistency:**  
The form components use an `onSuccess` callback that is semantically odd (should be `onSubmit` or `onNavigate`). This is a minor naming issue; functionality is correct and tests pass. Recommend documenting the prop contract in a future refactor.

### SUGGESTION
**pyproject.toml `httpx2` naming:**  
The backend dev dependencies list `httpx2` instead of standard `httpx`. This appears to be a project-specific alias or fork. Since tests pass, it works correctly, but worth documenting for CI reproducibility (ensure the same package is installed in CI environments).

### Conflict Resolution
**PASS-05 spec/design conflict RESOLVED:**  
Original spec said 401, design decision #4 locked to 400 + "La contraseña actual es incorrecta". Both spec and implementation now agree on 400. No conflict remains.

---

## Archived Artifacts

All change artifacts have been moved to `openspec/changes/archive/perfil-usuario/` with full traceability:

| Artifact | Location | Observation ID |
|---|---|---|
| Proposal | `archive/perfil-usuario/proposal.md` | #59 |
| Spec (delta) | `archive/perfil-usuario/spec.md` | #60 |
| Design | `archive/perfil-usuario/design.md` | #61 |
| Tasks | `archive/perfil-usuario/tasks.md` | #63 |
| Apply-progress | (Engram only) | #64 |
| Verify-report | (Engram only) | #65 |
| Archive-report | (Engram + below) | (this document) |

---

## Chained-PR Delivery Strategy

The change was delivered as **3 stacked PRs** (feature-branch-chain style):

1. **PR1 (sdd/perfil-usuario-backend)** — Backend API endpoints
   - Target: `main` or `desa/{Diego}`
   - Autonomous: deployable independently
   - Value: provides `/api/auth/me` and `/api/auth/me/password` endpoints

2. **PR2 (sdd/perfil-usuario-frontend-auth)** — Frontend scaffold + login/register
   - Depends on: PR1 merged (backend endpoints available at `:8000`)
   - Target: `main` or stacked on PR1
   - Value: provides working login/register screens, ready for profile screen

3. **PR3 (sdd/perfil-usuario-profile-e2e)** — Profile + change-password + Playwright E2E
   - Depends on: PR1 + PR2 merged
   - Target: `main` or stacked on PR2
   - Value: completes user interface, validates end-to-end with Playwright

**Rationale:** Total implementation is ~895 lines (exceeds 400-line single-PR budget). Splitting along backend / frontend-scaffold / UI+E2E seams keeps each PR reviewable and independently verifiable, with each slice shipping incremental value.

---

## Known Limitations & Carryover Items

### Intentional Design Decisions (no action needed)

1. **In-memory token storage** (user loses session on page reload)
   - Chosen for XSS resistance per user confirmation
   - localStorage explicitly rejected as less secure
   - httpOnly cookie deferred (adds backend CSRF/CORS complexity, out of scope)

2. **Token has no TTL / expiration**
   - Known limitation per RS-02.2
   - Future change (not in scope)

3. **No logout / token revocation**
   - Out of scope (future change)

4. **`/api/tasks` not protected by `get_current_user`**
   - Dependency is built reusable and overridable
   - Wiring tasks deferred to "branch Carlos"

### Minor Issues Carried Forward

- **RegisterForm prop naming:** `onSuccess` for a navigation callback could be clearer (recommendation: rename to `onNavigate` in a future refactor)
- **httpx2 in pyproject.toml:** Verify this alias is available in CI environments

---

## Cycle Complete

The **perfil-usuario** SDD cycle is complete:

✓ Proposal (intent, scope, approach)  
✓ Spec (RF-03..07, RS-03, acceptance scenarios)  
✓ Design (10 ADRs: dependency, repo, service, exception, schema, response, token storage, dev integration, frontend structure, Playwright)  
✓ Tasks (18 tasks across 3 slices, TDD strict mode)  
✓ Apply (all tasks completed, 3 PRs with 9+5+4 commits)  
✓ Verify (PASS verdict, 107 pytest + 6 E2E, 0 CRITICAL)  
✓ Archive (change folder moved, baseline spec promoted, report recorded)

**Next change:** ready to start new SDD cycle for next feature.

---

## Traceability

All SDD artifacts are recorded in Engram for cross-session recovery:

- `sdd/perfil-usuario/proposal` #59
- `sdd/perfil-usuario/spec` #60
- `sdd/perfil-usuario/design` #61
- `sdd/perfil-usuario/tasks` #63
- `sdd/perfil-usuario/apply-progress` #64
- `sdd/perfil-usuario/verify-report` #65
- `sdd/perfil-usuario/archive-report` (this document, saved now)
