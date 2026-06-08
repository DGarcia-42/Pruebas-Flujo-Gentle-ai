# Proposal: perfil-usuario

## 1. Intent / Why
The auth backend can register and log in users, but a logged-in user has NO way to see their own account or change their password, and there is NO user-facing surface at all (the repo is backend-only). This change adds account **visibility** (view my profile) and **control** (change my password) on top of the existing auth, and delivers the first real UI for the product.

Success looks like:
- An authenticated user can fetch their own profile via `GET /api/auth/me`.
- An authenticated user can change their password via `PUT /api/auth/me/password`, with the current password verified.
- A minimal React UI lets a user register, log in, view their profile, and change their password, validated end-to-end with Playwright.

## 2. Scope

### In scope
**Backend**
- Reusable `get_current_user` FastAPI dependency: extracts the Bearer token from the `Authorization` header, resolves `repo.tokens[token]` → `repo.users_by_id[user_id]` → `UserRecord`, and raises `401` on any miss. (Approach A from exploration.)
- `GET /api/auth/me` → reuses the existing `UserPublic {id, email, username}` schema (no new response schema).
- `PUT /api/auth/me/password` accepting `ChangePasswordRequest {current_password, new_password}`; verifies the current password with the existing `verify_password` and rehashes with the existing `hash_password`.
- Repository accessor to resolve token → user (`get_user_by_token` / `get_by_id`).
- Service methods `get_me` and `change_password` in `auth_service.py`.

**Frontend (React + Vite, MINIMAL)**
- Greenfield React+Vite app under `frontend/` — no Redux, no heavy state libraries, native `fetch`.
- Screens: Register, Login, Profile (renders `me`), Change-password form.
- Bearer token stored client-side and sent as `Authorization: Bearer <token>` (exact storage location is a design decision, security-relevant).

**Testing**
- pytest backend tests (strict TDD) for `me`, change-password, and `get_current_user` 401 paths.
- Playwright E2E covering the UI spec scenarios — MANDATORY per project policy.

### Out of scope (explicit)
- Logout / token revocation.
- Token TTL / expiration.
- Protecting `/api/tasks` with `get_current_user` (the dependency is built to be reusable, but wiring tasks is deferred).
- Password reset / forgot-password / email flows.
- Editing username or email (only password change).
- Any new backend runtime dependency.

## 3. Approach (high-level)
- **Auth dependency**: Approach A — a single reusable `get_current_user` in `dependencies.py`. Idiomatic FastAPI, forward-looking (future `/api/tasks` protection), and overridable in tests through the existing `get_user_repository` override chain.
- **Reuse over new**: reuse `UserPublic` for the `me` response; reuse `hash_password` / `verify_password` for change-password. The only genuinely new schema is `ChangePasswordRequest`.
- **Backend stays stdlib-only**: PBKDF2 600k, opaque tokens, NO passlib/JWT, NO new backend runtime deps (inherited RNF-03, non-negotiable).
- **Frontend**: a minimal React+Vite SPA that talks to the FastAPI API with native `fetch`; after login it stores the token client-side and attaches it as a Bearer header. Storage location is flagged for the design phase (security-relevant — not decided here).
- **Spec extension**: extend the live `openspec/specs/user-auth/spec.md` with RF-03 (`/me`), RF-04 (change-password), and RS-03 (token validation), WITHOUT contradicting existing out-of-scope notes. Preserve the anti-enumeration 401 message convention already in use ("Credenciales inválidas").

## 4. Affected capabilities / files
- `backend/app/dependencies.py` — add `get_current_user`.
- `backend/app/routers/auth.py` — add `GET /me` and `PUT /me/password`.
- `backend/app/services/auth_service.py` — add `get_me` and `change_password`.
- `backend/app/repositories/user_repository.py` — add `get_by_id` / `get_user_by_token`.
- `backend/app/schemas/auth.py` — add `ChangePasswordRequest` (reuse `UserPublic`).
- `backend/app/services/exceptions.py` — exception for a wrong current password (reuse `InvalidCredentials` vs new `InvalidCurrentPassword` — deferred to design).
- `backend/tests/test_auth.py` — ME-* / PASS-* scenarios plus 401 tests.
- `openspec/specs/user-auth/spec.md` — RF-03, RF-04, RS-03 deltas.
- `frontend/` (NEW) — React+Vite app, screens, API client.
- Playwright config + E2E tests (NEW).

## 5. Risks & open questions for design
- **Token storage location** — localStorage vs in-memory vs cookie. Security-relevant; decide in design.
- **Frontend↔backend dev integration** — CORS middleware on FastAPI vs Vite dev proxy. Decide in design.
- **Exception naming** — reuse `InvalidCredentials` or introduce `InvalidCurrentPassword`.
- **Where the React app lives** — `frontend/` at repo root (proposed); confirm in design.
- **How Playwright runs against the stack** — needs both the API and the Vite dev server running; orchestration (scripts, fixtures, CI) is a design question.
- **Repo method shape** — dedicated `get_user_by_token` helper vs inline `users_by_id.get(tokens.get(token))`.

## 6. Recommended delivery (ask-on-risk; expected > 400 lines → chained PRs)
- **PR1 — Backend**: `get_current_user` dependency + `GET /me` + `PUT /me/password` + repo/service/schema additions + pytest. Self-contained, mergeable, no UI. (~Medium)
- **PR2 — Frontend scaffold + auth screens**: Vite+React app, register + login screens, API client, token storage. (~Medium-Large, greenfield)
- **PR3 — Profile + change-password + Playwright E2E**: profile screen, change-password form, full Playwright suite. (~Medium)

**Rationale**: the total work clearly exceeds the 400-line single-PR budget (greenfield frontend + Playwright). Splitting along the natural backend / frontend-scaffold / UI+E2E seams keeps each PR reviewable and independently verifiable, and PR1 ships value (the API) even if the frontend work slips.
