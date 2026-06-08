# Delta Spec: perfil-usuario

**Change:** perfil-usuario
**Date:** 2026-06-08
**Status:** approved
**Extends:** `openspec/specs/user-auth/spec.md` (RF-01, RF-02, RS-01, RS-02 remain in force unchanged)

---

## Context

This delta adds account visibility and password change to the existing auth capability, and delivers the first user-facing surface (React+Vite SPA validated end-to-end with Playwright).

All existing requirements in `user-auth/spec.md` remain in force. This document only states what MUST additionally be true after this change is applied. Where the baseline spec sets conventions (error format, anti-enumeration message, 3-layer architecture, stdlib-only) they are inherited and NOT repeated — they are equally binding here.

---

## New Functional Requirements

### RF-03 — View own profile (`GET /api/auth/me`)

**RF-03.1** The request MUST include an `Authorization: Bearer <token>` header. Missing header → 401 with `{"detail": "Credenciales inválidas"}`.

**RF-03.2** If the header is present but not of the form `Bearer <token>` (malformed, empty token, wrong scheme) → 401 with `{"detail": "Credenciales inválidas"}`.

**RF-03.3** If the token is not found in the repository (unknown or never issued) → 401 with `{"detail": "Credenciales inválidas"}`.

**RF-03.4** If the token resolves to a user, the response is 200 with the body:

```json
{
  "id": "<user-id>",
  "email": "<user-email>",
  "username": "<username>"
}
```

This is the existing `UserPublic` schema. The response MUST NOT contain `password`, `hashed_password`, or any derivative of the password.

**RF-03.5** All three 401 paths (missing header, malformed header, unknown token) return the same `{"detail": "Credenciales inválidas"}` body. The response does NOT reveal which condition was triggered (anti-enumeration extension to token space).

---

### RF-04 — Change own password (`PUT /api/auth/me/password`)

**RF-04.1** The request MUST include a valid Bearer token (same rules as RF-03.1–RF-03.3 above). Missing/malformed/unknown token → 401 with `{"detail": "Credenciales inválidas"}`.

**RF-04.2** The request body MUST contain both fields `current_password` and `new_password`. Missing either field → 422.

**RF-04.3** `new_password` MUST be at least 8 characters (aligning with RF-01.3). A shorter value → 422.

**RF-04.4** If the token is valid and `current_password` matches the stored hash for that user, the operation returns **204 No Content** with an empty body. The success confirmation shown to the user is rendered by the frontend upon receiving 204; no response body is read.

**RF-04.5** After a successful change, the stored `hashed_password` for the user MUST reflect the new password (the old hash MUST NOT be present for the new one; it MUST be different from the value before the call).

**RF-04.6** If `current_password` does not match the stored hash, the operation returns 400 with `{"detail": "La contraseña actual es incorrecta"}`.

**RF-04.7** After a successful password change, the user CAN authenticate via `POST /api/auth/login` using the NEW password. The user CANNOT authenticate via `POST /api/auth/login` using the OLD password (regression invariant).

---

## New Security Requirements

### RS-03 — Bearer token validation

**RS-03.1** Token validation is performed via a single reusable FastAPI dependency (`get_current_user`). Any protected endpoint MUST use this dependency; ad-hoc token parsing in routers is not permitted.

**RS-03.2** The dependency resolves a token by looking it up in `repo.tokens`. If the token is found, the associated `user_id` is used to retrieve the full `UserRecord` from `repo.users_by_id`. If either lookup fails → raise 401 immediately.

**RS-03.3** The same 401 message `"Credenciales inválidas"` is returned for all failure modes of the dependency (missing header, malformed header, token not in repo, user_id not in repo). No failure mode leaks information about which step failed.

**RS-03.4** The `get_current_user` dependency MUST be overridable in tests via the same `dependency_overrides` mechanism already used for `get_user_repository`.

---

## New Frontend Functional Requirements

These requirements describe observable behavior that MUST be verifiable by Playwright E2E tests.

### RF-05 — Auth screens (Register + Login)

**RF-05.1** There exists a Register screen with fields for email, username, and password. Submitting valid data calls `POST /api/auth/register`. On success (201), the user is navigated to the Login screen (or directly to the authenticated area).

**RF-05.2** There exists a Login screen with fields for email and password. Submitting valid credentials calls `POST /api/auth/login`. On success (200), the returned `access_token` is stored client-side and the user is navigated to the Profile screen.

**RF-05.3** After a successful login, the token MUST be available for all subsequent requests (e.g. to `GET /api/auth/me`) without requiring the user to re-enter credentials.

**RF-05.4** The Login screen is publicly accessible (no auth required to view it).

---

### RF-06 — Profile screen

**RF-06.1** There exists a Profile screen that displays the logged-in user's `email` and `username`, fetched from `GET /api/auth/me` using the stored Bearer token.

**RF-06.2** The Profile screen MUST NOT be reachable without a valid stored token. An unauthenticated user attempting to access it MUST be redirected to (or shown) the Login screen.

**RF-06.3** The profile data shown to the user MUST match what the API returns. The screen does not show placeholder or hardcoded values.

---

### RF-07 — Change-password form

**RF-07.1** There exists a Change-password form (accessible from the Profile screen) with fields for `current_password` and `new_password`.

**RF-07.2** On success (API returns 204), the form shows a visible confirmation message to the user (e.g. "Password updated successfully" or equivalent). The message is rendered by the frontend logic; no body is read from the response.

**RF-07.3** If the API returns 400 due to a wrong current password, the form shows a visible error message to the user (not a blank screen or a silent failure).

**RF-07.4** After a successful password change, the user can log in again via the Login screen using the new password (E2E regression scenario).

---

## Out of Scope (explicit)

The following are explicitly excluded from this change and MUST NOT be addressed by implementation:

| Item | Rationale |
|---|---|
| Logout / token revocation | Future change |
| Token TTL / expiration | Inherited from RS-02.2; future change |
| Protecting `/api/tasks` with `get_current_user` | Deferred (branch Carlos) |
| Password reset / forgot-password / email flows | Out of scope |
| Username or email editing | Only password change is in scope |
| Any new backend runtime dependency | Inherited RNF-03; non-negotiable |
| Redux or client-side state libraries | Frontend is stdlib-only (`fetch`, `useState`) |

---

## Acceptance Scenarios

### Backend — `GET /api/auth/me`

#### ME-01 — Valid token returns UserPublic

**Given** a user registered with email `perfil@ejemplo.com`, username `PerfUser`, and password `segura1234`
**And** that user has logged in and obtained an `access_token`
**When** `GET /api/auth/me` is called with `Authorization: Bearer <access_token>`
**Then** the response status is 200
**And** the response body contains `id`, `email: "perfil@ejemplo.com"`, `username: "PerfUser"`
**And** the response body does NOT contain any field named `password` or `hashed_password`

---

#### ME-02 — Missing Authorization header → 401

**Given** any repository state
**When** `GET /api/auth/me` is called with no `Authorization` header
**Then** the response status is 401
**And** the response body is `{"detail": "Credenciales inválidas"}`

---

#### ME-03 — Malformed Authorization header → 401

**Given** any repository state
**When** `GET /api/auth/me` is called with `Authorization: Token abc123` (wrong scheme)
**Then** the response status is 401
**And** the response body is `{"detail": "Credenciales inválidas"}`

---

#### ME-04 — Unknown token → 401

**Given** a token value `"not-a-real-token"` that was never issued by the system
**When** `GET /api/auth/me` is called with `Authorization: Bearer not-a-real-token`
**Then** the response status is 401
**And** the response body is `{"detail": "Credenciales inválidas"}`

---

#### ME-05 — Anti-enumeration: same 401 body for all failure modes

**Given** scenarios ME-02, ME-03, and ME-04
**Then** all three return the identical response body `{"detail": "Credenciales inválidas"}`

> Validated by structural comparison across ME-02, ME-03, ME-04. No separate runtime test needed if the three scenarios above are already asserted.

---

### Backend — `PUT /api/auth/me/password`

#### PASS-01 — Valid token + correct current password → 204

**Given** a registered user with password `segura1234` who has logged in and obtained `access_token`
**When** `PUT /api/auth/me/password` is called with `Authorization: Bearer <access_token>` and body `{"current_password": "segura1234", "new_password": "nuevaClave99"}`
**Then** the response status is 204
**And** the response body is empty

---

#### PASS-02 — Stored hash changes after successful change

**Given** the same context as PASS-01 (after the PUT call succeeds)
**When** the user record in the repository is inspected
**Then** the stored `hashed_password` is different from the value it had before the call

---

#### PASS-03 — Login with new password succeeds after change

**Given** the same context as PASS-01 (after the PUT call succeeds)
**When** `POST /api/auth/login` is called with `{"email": "...", "password": "nuevaClave99"}`
**Then** the response status is 200

---

#### PASS-04 — Login with old password fails after change

**Given** the same context as PASS-01 (after the PUT call succeeds)
**When** `POST /api/auth/login` is called with `{"email": "...", "password": "segura1234"}`
**Then** the response status is 401
**And** the response body is `{"detail": "Credenciales inválidas"}`

---

#### PASS-05 — Wrong current password → 400

**Given** a registered user with password `segura1234` who has logged in and obtained `access_token`
**When** `PUT /api/auth/me/password` is called with `{"current_password": "wrongpassword", "new_password": "nuevaClave99"}`
**Then** the response status is 400
**And** the response body is `{"detail": "La contraseña actual es incorrecta"}`

---

#### PASS-06 — Missing token → 401

**Given** any repository state
**When** `PUT /api/auth/me/password` is called with no `Authorization` header and a valid body
**Then** the response status is 401
**And** the response body is `{"detail": "Credenciales inválidas"}`

---

#### PASS-07 — Missing `current_password` field → 422

**Given** a valid `access_token`
**When** `PUT /api/auth/me/password` is called with body `{"new_password": "nuevaClave99"}` (no `current_password`)
**Then** the response status is 422

---

#### PASS-08 — Missing `new_password` field → 422

**Given** a valid `access_token`
**When** `PUT /api/auth/me/password` is called with body `{"current_password": "segura1234"}` (no `new_password`)
**Then** the response status is 422

---

#### PASS-09 — `new_password` too short → 422

**Given** a valid `access_token`
**When** `PUT /api/auth/me/password` is called with `{"current_password": "segura1234", "new_password": "short"}` (fewer than 8 characters)
**Then** the response status is 422

---

### Backend — `get_current_user` dependency unit scenarios

#### DEP-01 — Dependency is injectable/overridable in tests

**Given** a FastAPI app with `get_current_user` wired via `Depends`
**When** tests set `app.dependency_overrides[get_current_user]` to a stub returning a fixed `UserRecord`
**Then** the protected endpoint receives the stubbed user without real token resolution

> This is verified by the ME and PASS test structure: if those tests pass without a real token in the repo fixture, DEP-01 is satisfied.

---

### Frontend E2E — Playwright scenarios

#### E2E-01 — Register then login navigates to profile

**Given** the app is running (FastAPI + Vite dev server)
**When** a user visits the Register screen
**And** fills in a valid email, username, and password and submits
**And** is then on the Login screen and submits valid credentials
**Then** the Profile screen is shown
**And** the profile screen displays the user's email and username

---

#### E2E-02 — Profile screen is not accessible without login

**Given** the app is running
**When** a user navigates directly to the Profile screen URL without having logged in
**Then** the user is redirected to (or shown) the Login screen
**And** the Profile screen content is NOT shown

---

#### E2E-03 — Profile screen shows correct user data

**Given** a logged-in user (via E2E-01 path or equivalent setup)
**When** the Profile screen is displayed
**Then** it shows the `email` and `username` that were used during registration

---

#### E2E-04 — Change password: success path

**Given** a logged-in user on the Change-password form
**When** the user enters the correct current password and a valid new password and submits
**Then** a success confirmation message is visible on screen

---

#### E2E-05 — Change password: wrong current password shows error

**Given** a logged-in user on the Change-password form
**When** the user enters an INCORRECT current password and submits
**Then** an error message is visible on screen (not a blank page, not a redirect)

---

#### E2E-06 — Login with new password after change

**Given** the user successfully changed their password (E2E-04)
**When** Playwright reloads the page (causing the in-memory token to be lost)
**Then** the app shows the Login screen (token gone, unauthenticated state)
**When** the user submits credentials with the NEW password
**Then** login succeeds and the Profile screen is shown

> Note: E2E-06 resets client state by reloading the page. Because the token is stored in-memory (not persisted to localStorage), a full page reload is sufficient and correct — no localStorage clearing or logout action is needed.

---

## Files Expected to Exist or Change

| File | Change type |
|---|---|
| `backend/app/dependencies.py` | Modify — add `get_current_user` |
| `backend/app/routers/auth.py` | Modify — add `GET /me`, `PUT /me/password` |
| `backend/app/services/auth_service.py` | Modify — add `get_me`, `change_password` |
| `backend/app/repositories/user_repository.py` | Modify — add token/id lookup helpers |
| `backend/app/schemas/auth.py` | Modify — add `ChangePasswordRequest` |
| `backend/app/services/exceptions.py` | Modify — add or reuse exception for wrong current password |
| `backend/tests/test_auth.py` | Modify — add ME-01..05, PASS-01..09, DEP-01 |
| `frontend/` | New — React+Vite SPA |
| `frontend/src/` | New — app code (screens, API client) |
| Playwright config + `e2e/` tests | New — E2E scenarios E2E-01..06 |

---

## Open Questions Deferred to Design

The following were explicitly flagged in the proposal as design decisions and MUST NOT be resolved by this spec:

1. Token storage location (localStorage vs in-memory vs httpOnly cookie) — security-relevant.
2. CORS middleware vs Vite dev proxy for frontend↔backend integration.
3. Exception naming: reuse `InvalidCredentials` or new `InvalidCurrentPassword`.
4. Playwright orchestration — how to spin up both servers in CI.
5. Repo accessor method shape (`get_user_by_token` helper vs inline lookup).
