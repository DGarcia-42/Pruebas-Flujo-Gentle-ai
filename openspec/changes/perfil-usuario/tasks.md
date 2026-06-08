# Tasks: perfil-usuario

**Change:** perfil-usuario
**Date:** 2026-06-08
**TDD Mode:** Strict (test-first for every backend behavior; Playwright-first for E2E)
**Delivery strategy:** ask-on-risk → three slices (PR1 backend / PR2 frontend scaffold + auth / PR3 profile + change-password + Playwright)

---

## Slice summary

| Slice | PR | Scope | Est. lines |
|---|---|---|---|
| PR1 | Backend | repo accessors, schema, exception, dependency, service methods, endpoints + pytest | ~320 |
| PR2 | Frontend scaffold + auth screens | Vite init, project structure, api/client.ts, auth/storage.ts, RegisterForm, LoginForm, App.tsx conditional rendering, Vite proxy | ~280 |
| PR3 | Profile + change-password + Playwright E2E | Profile component, ChangePasswordForm, playwright.config.ts, e2e/ test suite (E2E-01..06) | ~350 |
| **Total** | | | **~950** |

---

## Dependency graph

```
T-01 (repo accessors) ──► T-02 (exception)
                               │
                               ▼
T-03 (schema: ChangePasswordRequest) ──► T-04 (dependency: get_current_user)
                                                │
                       ┌────────────────────────┘
                       ▼                        ▼
               T-05 (service: get_me)    T-06 (service: change_password)
                       │                        │
                       ▼                        ▼
               T-07 (endpoint: GET /me)  T-08 (endpoint: PUT /me/password)
                       │                        │
                       └─────────┬──────────────┘
                                 ▼
                          T-09 (pytest suite)   ← PR1 complete

PR2 (independent from PR1 after merge):
T-10 (Vite init) ──► T-11 (api/client.ts) ──► T-12 (auth/storage.ts)
                                ▼
                        T-13 (RegisterForm + LoginForm + App.tsx conditional)
                        T-14 (Vite proxy config)

PR3 (depends on PR1 merged + PR2 merged):
T-15 (Profile component) ──► T-16 (ChangePasswordForm)
                                      │
                                      ▼
T-17 (playwright.config.ts webServer array) ──► T-18 (E2E suite E2E-01..06)
```

---

## Slice PR1 — Backend

> Branch: `feat/perfil-usuario-backend`
> Target: `main` (or `desa/Diego` if team convention)
> Prerequisite: none (extends existing auth backend)

### T-01 — Add `get_by_token` and `get_by_id` repo accessors [PR1]

**Spec refs:** RS-03.2 (two-hop token resolution), design decision #2
**Execution:** sequential (foundation for T-04)
**TDD:** Test-first in `backend/tests/test_auth.py` (unit tests using UserRepository directly)

Work unit:
1. RED: write two unit tests in `test_auth.py`:
   - `test_get_by_token_returns_user_record` — saves a token + user, calls `repo.get_by_token(token)`, asserts the UserRecord is returned.
   - `test_get_by_token_returns_none_for_unknown_token` — calls `repo.get_by_token("unknown")`, asserts `None`.
   - `test_get_by_id_returns_user_record` — adds a user, calls `repo.get_by_id(user.id)`, asserts the UserRecord.
   - `test_get_by_id_returns_none_for_unknown_id` — asserts `None` for unknown id.
2. GREEN: add `get_by_token(token: str) -> UserRecord | None` and `get_by_id(user_id: str) -> UserRecord | None` to `UserRepository`.
3. REFACTOR: remove any inline `tokens[t]` / `users_by_id[id]` usages if they exist.

Files changed: `backend/app/repositories/user_repository.py`, `backend/tests/test_auth.py`
Commit: `feat(auth): add get_by_token and get_by_id repo accessors`

---

### T-02 — Add `InvalidCurrentPassword` exception [PR1]

**Spec refs:** design decision #4 (`InvalidCurrentPassword(AuthError)` → HTTP 400, message "La contraseña actual es incorrecta")
**Execution:** sequential after T-01 (used by T-06)
**TDD:** exception is pure Python — test by importing and raising it; 2 lines. No separate test file needed; cover inline in `test_auth.py` exception block.

Work unit:
1. RED: add one test `test_invalid_current_password_is_auth_error` asserting `isinstance(InvalidCurrentPassword(), AuthError)`.
2. GREEN: add `class InvalidCurrentPassword(AuthError)` with docstring to `services/exceptions.py`.
3. No refactor needed.

Files changed: `backend/app/services/exceptions.py`, `backend/tests/test_auth.py`
Commit: `feat(auth): add InvalidCurrentPassword domain exception`

---

### T-03 — Add `ChangePasswordRequest` schema [PR1]

**Spec refs:** RF-04.2 (both fields required → 422), RF-04.3 (`new_password` min 8 chars → 422), design decision #5
**Execution:** parallel with T-02 (no dependency between them)
**TDD:** unit test schema validation directly (no HTTP needed).

Work unit:
1. RED: add tests in `test_auth.py` (or `test_schemas.py` if the team uses it):
   - `test_change_password_request_valid` — instantiates with `current_password="segura1234"`, `new_password="nuevaClave99"`, asserts no error.
   - `test_change_password_request_short_new_password` — `new_password="short"` (7 chars) → raises `ValidationError`.
   - `test_change_password_request_empty_current_password` — `current_password=""` → raises `ValidationError`.
   - `test_change_password_request_missing_new_password` — omit `new_password` → raises `ValidationError`.
2. GREEN: add `ChangePasswordRequest` to `backend/app/schemas/auth.py`:
   - `current_password: str = Field(..., min_length=1)`
   - `new_password: str = Field(..., min_length=8, max_length=128)`
3. Export from `schemas/__init__.py` if needed.

Files changed: `backend/app/schemas/auth.py`, `backend/tests/test_auth.py`
Commit: `feat(auth): add ChangePasswordRequest schema with validation`

---

### T-04 — Add `get_current_user` FastAPI dependency [PR1]

**Spec refs:** RS-03.1, RS-03.2, RS-03.3, RS-03.4, design decision #1
**Execution:** sequential after T-01 (needs `get_by_token`/`get_by_id`)
**TDD:** test via HTTP integration (not unit) — real register+login path, then call a protected test-only endpoint; plus 401 paths using real missing/malformed/unknown token. Do NOT override `get_current_user` in these tests (design decision #1 specifies testing 401 paths as real).

Work unit:
1. RED: Add integration tests in `test_auth.py` that test the dependency's 401 behavior through a real endpoint. Because `GET /api/auth/me` doesn't exist yet, add a temporary note; tests will be written together with T-07 (dependency tests are inherently coupled to endpoint existence). Mark these tests as part of T-07 batch to avoid a chicken-and-egg problem. (See T-07 for the combined RED step.)
2. GREEN: Add `get_current_user` to `backend/app/dependencies.py`:
   - Accepts `authorization: str | None = Header(default=None)`.
   - If `None` or not starting with `"Bearer "` or token part empty → raise `HTTPException(401, detail="Credenciales inválidas", headers={"WWW-Authenticate": "Bearer"})`.
   - Call `repo.get_by_token(token)` → if `None` → same 401.
   - Call `repo.get_by_id(user_id)` → if `None` → same 401.
   - Return `UserRecord`.
   - Inject `repo: UserRepository = Depends(get_user_repository)`.
3. Verify existing tests still pass (no regression).

Files changed: `backend/app/dependencies.py`
Commit: `feat(auth): add get_current_user dependency with Bearer token validation`

**Note on test ordering:** The 401 RED tests for the dependency (ME-02, ME-03, ME-04, DEP-01) are written in T-07 RED step since they require the endpoint to exist for HTTP-level assertions.

---

### T-05 — Add `get_me` service method [PR1]

**Spec refs:** RF-03.4 (returns `UserPublic`; no password fields), design decision #3
**Execution:** parallel with T-06 (both depend on T-04 completing)
**TDD:** unit test at service layer.

Work unit:
1. RED: add unit test `test_get_me_returns_user_public` — create a `UserRecord`, call `AuthService.get_me(user)`, assert returned object is `UserPublic` with correct `id`, `email`, `username` and no `hashed_password` field.
2. GREEN: add `get_me(self, user: UserRecord) -> UserPublic` to `AuthService`. One line: `return UserPublic(id=user.id, email=user.email, username=user.username)`.
3. No refactor needed.

Files changed: `backend/app/services/auth_service.py`, `backend/tests/test_auth.py`
Commit: `feat(auth): add get_me service method`

---

### T-06 — Add `change_password` service method [PR1]

**Spec refs:** RF-04.4 (204 → in-place hash mutation), RF-04.5 (stored hash changes), RF-04.6 (`InvalidCurrentPassword` on wrong current pw), RF-04.7 (new pw works at login), design decision #3
**Execution:** parallel with T-05
**TDD:** unit test at service layer.

Work unit:
1. RED: add unit tests:
   - `test_change_password_success_mutates_hash` — register a user via service, record `old_hash = user.hashed_password`, call `service.change_password(user, "segura1234", "nuevaClave99")`, assert `user.hashed_password != old_hash`.
   - `test_change_password_wrong_current_raises` — call `service.change_password(user, "wrongpassword", "nuevaClave99")`, assert raises `InvalidCurrentPassword`.
   - `test_change_password_new_password_verifiable` — after successful change, assert `verify_password("nuevaClave99", user.hashed_password)` is True.
   - `test_change_password_old_password_no_longer_valid` — after change, assert `verify_password("segura1234", user.hashed_password)` is False.
2. GREEN: add `change_password(self, user: UserRecord, current_password: str, new_password: str) -> None` to `AuthService`:
   - `if not verify_password(current_password, user.hashed_password): raise InvalidCurrentPassword()`
   - `user.hashed_password = hash_password(new_password)`
3. No refactor needed.

Files changed: `backend/app/services/auth_service.py`, `backend/tests/test_auth.py`
Commit: `feat(auth): add change_password service method`

---

### T-07 — Add `GET /api/auth/me` endpoint [PR1]

**Spec refs:** RF-03.1–RF-03.5, RS-03.1, ME-01..05, DEP-01
**Execution:** sequential after T-04 + T-05
**TDD:** integration tests RED first, then endpoint GREEN.

Work unit:
1. RED: add integration tests in `test_auth.py`:
   - `test_get_me_valid_token_returns_user_public` (ME-01) — register + login → GET /api/auth/me with Bearer token → 200, body has `id`, `email`, `username`, no `password`/`hashed_password`.
   - `test_get_me_missing_header_returns_401` (ME-02) — GET /api/auth/me no Authorization header → 401, `{"detail": "Credenciales inválidas"}`.
   - `test_get_me_malformed_header_returns_401` (ME-03) — `Authorization: Token abc123` → 401.
   - `test_get_me_unknown_token_returns_401` (ME-04) — `Authorization: Bearer not-a-real-token` → 401.
   - `test_get_me_all_401_paths_same_body` (ME-05) — assert ME-02/ME-03/ME-04 all return exact same body (verified structurally by the three tests above).
2. GREEN: add to `routers/auth.py`:
   ```python
   @router.get("/me", response_model=UserPublic, status_code=200)
   def get_me(
       current_user: UserRecord = Depends(get_current_user),
       service: AuthService = Depends(get_auth_service),
   ) -> UserPublic:
       return service.get_me(current_user)
   ```
   Import `get_current_user` from `app.dependencies`.
3. Run pytest — all existing + new tests must pass.

Files changed: `backend/app/routers/auth.py`, `backend/tests/test_auth.py`
Commit: `feat(auth): add GET /api/auth/me endpoint (ME-01..05)`

---

### T-08 — Add `PUT /api/auth/me/password` endpoint [PR1]

**Spec refs:** RF-04.1–RF-04.7, RS-03.1, PASS-01..09
**Execution:** sequential after T-04 + T-06
**TDD:** integration tests RED first, then endpoint GREEN.

Work unit:
1. RED: add integration tests in `test_auth.py`:
   - `test_change_password_valid_returns_204` (PASS-01) — register + login, PUT with correct current pw → 204, empty body.
   - `test_change_password_hash_mutated_after_success` (PASS-02) — use `client_with_repo`; after PUT 204, assert `user.hashed_password` changed.
   - `test_change_password_new_password_login_succeeds` (PASS-03) — after PUT 204, POST /api/auth/login with new pw → 200.
   - `test_change_password_old_password_login_fails` (PASS-04) — after PUT 204, POST /api/auth/login with old pw → 401.
   - `test_change_password_wrong_current_returns_400` (PASS-05) — wrong `current_password` → **400** `{"detail": "La contraseña actual es incorrecta"}`.

   > NOTE: The spec says 401 for PASS-05 but the design decision #4 locked it to **400** with a precise message. Design takes precedence for implementation; the test MUST assert 400. The spec/design conflict is documented here so sdd-verify can flag it.

   - `test_change_password_missing_token_returns_401` (PASS-06) — no Authorization header → 401.
   - `test_change_password_missing_current_password_returns_422` (PASS-07) — body `{"new_password": "nuevaClave99"}` → 422.
   - `test_change_password_missing_new_password_returns_422` (PASS-08) — body `{"current_password": "segura1234"}` → 422.
   - `test_change_password_short_new_password_returns_422` (PASS-09) — `new_password: "short"` → 422.
2. GREEN: add to `routers/auth.py`:
   ```python
   @router.put("/me/password", status_code=204)
   def change_password(
       body: ChangePasswordRequest,
       current_user: UserRecord = Depends(get_current_user),
       service: AuthService = Depends(get_auth_service),
   ) -> None:
       try:
           service.change_password(current_user, body.current_password, body.new_password)
       except InvalidCurrentPassword:
           raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST,
               detail="La contraseña actual es incorrecta",
           )
   ```
   Import `ChangePasswordRequest` and `InvalidCurrentPassword`.
3. Run pytest — full suite must pass (expected ~30+ tests).

Files changed: `backend/app/routers/auth.py`, `backend/tests/test_auth.py`
Commit: `feat(auth): add PUT /api/auth/me/password endpoint (PASS-01..09)`

---

### T-09 — Final PR1 regression run and commit hygiene [PR1]

**Spec refs:** all backend scenarios
**Execution:** sequential after T-07 + T-08
**Action:** run full `pytest` suite from `backend/`, verify 0 failures, 0 warnings. Squash-check commit messages follow conventional commits. No production code added in this task.

Commit: none (verification only — no new commit)

---

## Slice PR2 — Frontend scaffold + auth screens

> Branch: `feat/perfil-usuario-frontend-auth`
> Target: `main` (after PR1 merged, or stacked on PR1 if using stacked-to-main)
> Prerequisite: PR1 merged (backend endpoints available at `:8000`)

### T-10 — Initialize Vite+React+TypeScript project under `frontend/` [PR2]

**Spec refs:** design decision #9 (React 18 + Vite + TS, no Redux/router)
**Execution:** sequential (foundation for all PR2/PR3 frontend tasks)
**TDD:** not applicable to scaffolding; verified by `npm run dev` starting without errors.

Work unit:
1. Run `npm create vite@latest frontend -- --template react-ts` from repo root.
2. Remove unused boilerplate: `src/App.css`, `src/assets/`, example counters.
3. Update `index.html` title to "Gentle AI".
4. Verify `npm run dev` starts on port 5173 without errors.
5. Add `frontend/node_modules` to root `.gitignore` if not already present.

Files changed: `frontend/` (new), `.gitignore`
Commit: `chore(frontend): initialize Vite+React+TS project`

---

### T-11 — Add `api/client.ts` (fetch wrapper) [PR2]

**Spec refs:** RF-05.2 (token sent to API), design decision #9 (`api/client.ts` attaches Bearer, handles 204→null, parses `{detail}`)
**Execution:** sequential after T-10
**TDD:** these are pure TS functions; unit-testable with Vitest (if available). If no Vitest configured, cover via Playwright assertions in PR3 E2E. Note in task log if unit tests deferred.

Work unit:
1. Create `frontend/src/api/client.ts`:
   - Export `getToken(): string | null` (reads from `auth/storage.ts`).
   - `apiFetch(path, options?)`: wraps `fetch`, adds `Authorization: Bearer <token>` when token present, returns `null` for 204, parses JSON otherwise, throws `{detail: string}` on non-2xx.
2. Verify TypeScript compiles with `npm run build` (no type errors).

Files changed: `frontend/src/api/client.ts`
Commit: `feat(frontend): add api/client.ts fetch wrapper with Bearer auth`

---

### T-12 — Add `auth/storage.ts` (in-memory token store) [PR2]

**Spec refs:** design decision #7 (module-level `let _token`, token lost on reload, XSS resistance)
**Execution:** parallel with T-11 (no dependency)
**TDD:** same as T-11 — unit tests deferred to Playwright E2E if no Vitest; note in log.

Work unit:
1. Create `frontend/src/auth/storage.ts`:
   - Module-level `let _token: string | null = null`.
   - Export `setToken(t: string): void`, `getToken(): string | null`, `clearToken(): void`.
2. `api/client.ts` must import `getToken` from here (ensure import consistency with T-11).
3. Verify TypeScript compiles.

Files changed: `frontend/src/auth/storage.ts`
Commit: `feat(frontend): add in-memory token storage module`

---

### T-13 — Add RegisterForm, LoginForm, and App.tsx conditional rendering [PR2]

**Spec refs:** RF-05.1 (register form → POST /api/auth/register → navigate to login), RF-05.2 (login form → POST /api/auth/login → store token → show profile), RF-05.3 (token available for subsequent requests), RF-05.4 (login screen publicly accessible), RF-06.2 (profile not accessible without token)
**Execution:** sequential after T-11 + T-12
**TDD:** E2E coverage is in PR3. This task produces working, compilable components with correct wiring.

Work unit:
1. Create `frontend/src/components/RegisterForm.tsx`:
   - Fields: `email` (type=email), `username` (type=text), `password` (type=password).
   - On submit: POST `/api/auth/register`. On 201: transition `view` to `"login"` (passed via prop/callback).
   - On error: show `{detail}` message.
2. Create `frontend/src/components/LoginForm.tsx`:
   - Fields: `email` (type=email), `password` (type=password).
   - On submit: POST `/api/auth/login`. On 200: call `setToken(access_token)` from `auth/storage.ts`, call `onLogin()` callback.
   - On error: show `{detail}` message.
3. Update `frontend/src/App.tsx`:
   - State: `view: "register" | "login" | "profile"` (initial: `"login"`).
   - Token-based guard: if `getToken()` is null and view is `"profile"`, render `<LoginForm>` instead.
   - Conditional render: `view === "register"` → `<RegisterForm>`, `view === "login"` → `<LoginForm>`, `view === "profile"` → placeholder `<div>Profile coming in PR3</div>`.
   - Register → login navigation via callback; login success → set view to `"profile"`.
4. Verify `npm run build` compiles without errors.

Files changed: `frontend/src/components/RegisterForm.tsx`, `frontend/src/components/LoginForm.tsx`, `frontend/src/App.tsx`
Commit: `feat(frontend): add RegisterForm, LoginForm, and conditional rendering in App`

---

### T-14 — Configure Vite dev proxy for `/api` [PR2]

**Spec refs:** design decision #8 (Vite proxy `/api` → `http://127.0.0.1:8000`, same-origin, no CORS, no backend change)
**Execution:** parallel with T-13 (config-only, no component dependency)
**TDD:** verified manually or by E2E test in PR3 that actual API calls succeed.

Work unit:
1. Add to `frontend/vite.config.ts`:
   ```typescript
   server: {
     proxy: {
       '/api': {
         target: 'http://127.0.0.1:8000',
         changeOrigin: false,
       },
     },
   },
   ```
2. Document in a comment that this is dev-only; prod serving must be same-origin or explicit CORS.
3. Verify `npm run build` still succeeds.

Files changed: `frontend/vite.config.ts`
Commit: `chore(frontend): configure Vite dev proxy for /api`

---

## Slice PR3 — Profile + change-password + Playwright E2E

> Branch: `feat/perfil-usuario-e2e`
> Target: `main` (after PR2 merged)
> Prerequisite: PR1 + PR2 merged

### T-15 — Add `Profile` component [PR3]

**Spec refs:** RF-06.1 (display email + username from GET /api/auth/me), RF-06.3 (no hardcoded values), RF-06.2 (unauthenticated → login screen — already handled by App.tsx, verified by E2E-02)
**Execution:** sequential (first PR3 task; T-16 depends on it)
**TDD:** E2E-01/E2E-03 will be the red tests for this component.

Work unit:
1. Create `frontend/src/components/Profile.tsx`:
   - On mount: `GET /api/auth/me` via `apiFetch`. Store `{email, username}` in state.
   - Render `<p data-testid="profile-email">{email}</p>` and `<p data-testid="profile-username">{username}</p>`.
   - Show loading state while fetching; show error if API fails.
   - Render a "Change password" section that conditionally shows/hides `<ChangePasswordForm>` (placeholder for T-16).
2. Wire `<Profile>` into `App.tsx` replacing the placeholder div from T-13.
3. Verify `npm run build` compiles.

Files changed: `frontend/src/components/Profile.tsx`, `frontend/src/App.tsx`
Commit: `feat(frontend): add Profile component (GET /api/auth/me on mount)`

---

### T-16 — Add `ChangePasswordForm` component [PR3]

**Spec refs:** RF-07.1 (form with `current_password` + `new_password`), RF-07.2 (204 → visible success message), RF-07.3 (401 wrong current pw → visible error message), RF-07.4 (E2E regression with new password covered by E2E-06)
**Execution:** sequential after T-15
**TDD:** E2E-04/E2E-05/E2E-06 are the red tests.

Work unit:
1. Create `frontend/src/components/ChangePasswordForm.tsx`:
   - Fields: `current_password` (type=password), `new_password` (type=password).
   - On submit: PUT `/api/auth/me/password` via `apiFetch`.
   - On 204 (null response): show `<p data-testid="pw-success">Password updated successfully</p>`.
   - On error (400/401): show `<p data-testid="pw-error">{detail}</p>`. Never show a blank screen.
   - Reset form fields after success.
2. Integrate into `Profile.tsx` (replace placeholder from T-15).
3. Verify `npm run build` compiles.

Files changed: `frontend/src/components/ChangePasswordForm.tsx`, `frontend/src/components/Profile.tsx`
Commit: `feat(frontend): add ChangePasswordForm with 204 success and 401 error handling`

---

### T-17 — Configure Playwright: `playwright.config.ts` + `webServer` array [PR3]

**Spec refs:** design decision #10 (webServer array: uvicorn port 8000 + vite port 5173, baseURL 5173, reuseExistingServer, healthcheck on /docs)
**Execution:** parallel with T-15/T-16 (config-only)
**TDD:** configuration verified by T-18 tests running without setup errors.

Work unit:
1. From repo root: `npm init -y` (if no root `package.json`), then `npm install -D @playwright/test`.
2. Create `playwright.config.ts` at repo root:
   ```typescript
   import { defineConfig } from '@playwright/test';
   export default defineConfig({
     testDir: './e2e',
     use: { baseURL: 'http://127.0.0.1:5173' },
     webServer: [
       {
         command: 'python -m uvicorn app.main:app --port 8000',
         cwd: './backend',
         url: 'http://127.0.0.1:8000/docs',
         reuseExistingServer: !process.env.CI,
         timeout: 30_000,
       },
       {
         command: 'npm run dev',
         cwd: './frontend',
         url: 'http://127.0.0.1:5173',
         reuseExistingServer: !process.env.CI,
         timeout: 30_000,
       },
     ],
   });
   ```
3. Create `e2e/` directory with a `.gitkeep` (tests added in T-18).
4. Add `node_modules` and `.playwright` to `.gitignore` at root level.

Files changed: `playwright.config.ts` (new), `e2e/.gitkeep` (new), `package.json` (new/modified), `.gitignore`
Commit: `chore(e2e): add Playwright config with dual webServer (uvicorn + vite)`

---

### T-18 — Write Playwright E2E suite (E2E-01..06) [PR3]

**Spec refs:** RF-05.1, RF-05.2, RF-06.1, RF-06.2, RF-06.3, RF-07.2, RF-07.3, RF-07.4, E2E-01..06
**Execution:** sequential after T-17 + T-15 + T-16
**TDD:** write tests RED first (tests fail because components don't have expected `data-testid` selectors yet), then GREEN once components are confirmed to have the selectors. In practice T-15/T-16 are built alongside so RED is confirmed by running `npx playwright test` against a partially-built frontend.

Work unit:
1. Create `e2e/auth.spec.ts`:

   **E2E-01 — Register then login navigates to profile**
   - Generate unique email: `` `user-${Date.now()}@example.com` ``
   - Navigate to app, fill RegisterForm, submit → expect URL/view shows login
   - Fill LoginForm with same credentials, submit → expect Profile renders `[data-testid="profile-email"]`

   **E2E-02 — Profile screen is not accessible without login**
   - Fresh page (no token), navigate to app → expect NO `[data-testid="profile-email"]` in DOM
   - Expect LoginForm fields visible

   **E2E-03 — Profile screen shows correct user data**
   - Reuse E2E-01 setup (register + login)
   - Assert `[data-testid="profile-email"]` text equals the email used at registration
   - Assert `[data-testid="profile-username"]` text matches

   **E2E-04 — Change password: success path**
   - Register + login (unique email)
   - Fill ChangePasswordForm with correct current pw and new pw
   - Submit → expect `[data-testid="pw-success"]` visible

   **E2E-05 — Change password: wrong current password shows error**
   - Register + login (unique email)
   - Fill ChangePasswordForm with WRONG current pw
   - Submit → expect `[data-testid="pw-error"]` visible
   - Assert no redirect/blank page

   **E2E-06 — Login with new password after change (reload-based session clear)**
   - Register + login + change password (reuse E2E-04 path)
   - Call `page.reload()` → expect login screen shown (in-memory token gone)
   - Fill LoginForm with NEW password → submit → expect Profile renders

2. Run `npx playwright test` — all 6 scenarios must pass.
3. Add `playwright-report/` and `test-results/` to `.gitignore`.

Files changed: `e2e/auth.spec.ts` (new), `.gitignore`
Commit: `test(e2e): add Playwright E2E suite (E2E-01..06) for perfil-usuario`

---

## Cross-cutting notes

### Spec/design conflict to surface at sdd-verify

**PASS-05 status code:** spec says 401, design decision #4 says 400. Tasks implement 400 (design wins) but sdd-verify MUST report this as a WARNING for human review.

### data-testid convention

All interactive/output elements in frontend components that are covered by E2E assertions MUST carry `data-testid` attributes matching the selectors in T-18. Specifically:
- `data-testid="profile-email"` and `data-testid="profile-username"` on Profile
- `data-testid="pw-success"` and `data-testid="pw-error"` on ChangePasswordForm

### Python command in playwright.config.ts

The `python -m uvicorn` command in T-17 must match the exact Python executable that has FastAPI installed on the target machine. If the project uses a venv, the command may need to be `python -m uvicorn` with the venv activated, or a full path. The apply agent should verify this.

### Token lost on page reload (E2E-06 design invariant)

E2E-06 relies on `page.reload()` causing the in-memory token to disappear and the app to render the Login screen. This is the correct behavior per design decision #7. The test MUST NOT use `localStorage.clear()` — the token is never in localStorage.

---

## Review Workload Forecast

| Slice | Estimated additions | Estimated deletions | Net changed lines |
|---|---|---|---|
| PR1 — Backend | ~260 additions (repo, exception, schema, dep, service, endpoints, tests) | ~10 minor (imports) | ~270 |
| PR2 — Frontend scaffold + auth | ~280 additions (Vite init, client, storage, forms, config) | 0 | ~280 |
| PR3 — Profile + change-password + E2E | ~340 additions (Profile, ChangePasswordForm, pw config, e2e suite) | ~5 (App.tsx placeholder replaced) | ~345 |
| **Total** | **~880** | **~15** | **~895** |

**Chained PRs recommended: Yes**
**400-line budget risk: High** (total ~895 lines across 3 PRs; each individual PR is under 400 but total change is large; each slice independently deployable)
**Decision needed before apply: Yes** — confirm stacked-to-main vs feature-branch-chain before PR1 is opened. PR1 is fully independent and can land first. PR2 depends on PR1 backend being available locally (proxy target must be running). PR3 depends on both PR1 and PR2.
