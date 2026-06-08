# Design: perfil-usuario

> SDD design phase (architecture-level HOW). Tasks are written separately.
> Grounded against the real backend at `backend/app/*` (read 2026-06-08).

## 0. Architecture overview

The backend already follows a clean layered split that this change extends without
reshaping:

```
HTTP (FastAPI router)         backend/app/routers/auth.py
  -> Dependencies (DI wiring) backend/app/dependencies.py   <-- new: get_current_user
  -> Service (domain logic)   backend/app/services/auth_service.py  <-- new: get_me, change_password
  -> Repository (in-memory)   backend/app/repositories/user_repository.py  <-- new: get_by_id / get_by_token
  -> Security primitives       backend/app/security/passwords.py  (REUSED as-is)
  -> Schemas (Pydantic DTOs)   backend/app/schemas/auth.py  <-- new: ChangePasswordRequest
```

Frontend is greenfield and lives outside the Python tree:

```
frontend/            React + Vite SPA (native fetch, no state libs)
e2e/                 Playwright config + specs (drives Vite + FastAPI together)
```

Layering rule preserved: **routers translate exceptions -> HTTP; services raise domain
exceptions; repository never knows about HTTP.** `get_current_user` is the one new
seam that lives in the DI layer because it bridges the transport header to a domain
`UserRecord` and must be overridable in tests via the existing
`dependency_overrides[get_user_repository]` chain.

---

## 1. `get_current_user` dependency  (DECISION: FastAPI `Header`, not HTTPBearer)

**Chosen option: read the raw `Authorization` header with `fastapi.Header` and parse the
`Bearer ` prefix manually.**

```python
# backend/app/dependencies.py
from typing import Annotated
from fastapi import Depends, Header, HTTPException, status
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRecord

_INVALID_TOKEN_DETAIL = "Credenciales inválidas"  # same string as login (anti-enumeration)

def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    repo: UserRepository = Depends(get_user_repository),
) -> UserRecord:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_TOKEN_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len("Bearer "):].strip()
    user = repo.get_by_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_TOKEN_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

It returns the full `UserRecord` (not `UserPublic`) so that `change_password` can verify
against `hashed_password` without a second repo round-trip; the router narrows to
`UserPublic` for the `/me` response.

**Why `Header` over `HTTPBearer`/`Security`:**
- `HTTPBearer` adds an OpenAPI security scheme and its own 403/401 behaviour, and it
  ties the failure detail/format to Starlette's security internals — harder to keep the
  exact `"Credenciales inválidas"` anti-enumeration string the project already uses.
- `Header` is plain, stdlib-adjacent, fully under our control, and trivially unit-testable
  by sending/omitting the header. No new dependency, no OpenAPI side effects.
- Tradeoff accepted: we lose the auto-generated "Authorize" button in Swagger UI. For a
  test project with opaque tokens that is irrelevant; correctness and message control win.

**How tests override it:** they do NOT override `get_current_user` itself. They override
`get_user_repository` (already done in `conftest.py`), register+login a real user through
the API to obtain a real token, then send `Authorization: Bearer <token>`. This exercises
the genuine token->user path. A direct `dependency_overrides[get_current_user]` is
available as an escape hatch but is intentionally avoided so the 401 paths are real.

**401 paths to cover in tests:** missing header, malformed header (no `Bearer ` prefix),
unknown/garbage token, empty token.

---

## 2. Repository accessor  (DECISION: add `get_by_token`, keep `get_by_id` private-ish)

**Chosen option: add a single `get_by_token` that encapsulates the two-hop lookup, plus a
thin `get_by_id` for symmetry/testability.**

```python
# backend/app/repositories/user_repository.py  (additions)
def get_by_id(self, user_id: str) -> UserRecord | None:
    return self.users_by_id.get(user_id)

def get_by_token(self, token: str) -> UserRecord | None:
    user_id = self.tokens.get(token)
    if user_id is None:
        return None
    return self.users_by_id.get(user_id)
```

**Why:** the token->user_id->user chain is repository knowledge (it owns both `tokens` and
`users_by_id` dicts). Exposing it as `get_by_token` keeps `get_current_user` ignorant of
the dict layout — the dependency asks one clean question. `get_by_id` is added because it
is trivial, useful for tests, and makes `get_by_token` read naturally.

**Password mutation (in-memory, in place):** `UserRecord` is a Pydantic model and mutable
by default, and `users_by_email` / `users_by_id` hold references to the *same* object, so
reassigning the field mutates both views with no re-indexing:

```python
# inside change_password (service layer); see section 3
user.hashed_password = hash_password(new_password)
```

No repo `update` method is required because we hold the live object reference. (If the team
later switches to immutable records or a real DB, a `repo.update(user)` seam would be added
then — out of scope now.)

---

## 3. Service methods  (DECISION: `get_me(user)` + `change_password(user, current, new)`)

```python
# backend/app/services/auth_service.py  (additions)
def get_me(self, user: UserRecord) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, username=user.username)

def change_password(self, user: UserRecord, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise InvalidCurrentPassword()
    user.hashed_password = hash_password(new_password)
```

**Design note on the seam:** the dependency already resolves the user, so the service
takes the resolved `UserRecord` (not the token), allowing the router to do the identity
work and the service to focus on domain logic.

Router wiring:

```python
# backend/app/routers/auth.py  (additions)
@router.get("/me", response_model=UserPublic)
def me(
    current_user: UserRecord = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserPublic:
    return service.get_me(current_user)

@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        service.change_password(current_user, body.current_password, body.new_password)
    except InvalidCurrentPassword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="La contraseña actual es incorrecta")
```

---

## 4. Exception naming  (DECISION: add `InvalidCurrentPassword`, do NOT reuse `InvalidCredentials`)

**Chosen option: new `InvalidCurrentPassword(AuthError)`.**

```python
# backend/app/services/exceptions.py  (addition)
class InvalidCurrentPassword(AuthError):
    """Se lanza cuando la contraseña actual aportada en el cambio no coincide."""
```

`change_password` raises `InvalidCurrentPassword` when `verify_password` fails.

**Why not reuse `InvalidCredentials`:** the two cases need *different* HTTP semantics and
the anti-enumeration argument does not apply here.
- `InvalidCredentials` exists for login, where leaking "email exists vs wrong password"
  enables account enumeration, so it deliberately maps to **401** with a vague message.
- In change-password the user is already authenticated (token valid). Telling them "your
  current password is wrong" leaks nothing — they already proved they own the session.
  The correct status is **400 Bad Request** with a precise, helpful message.
- Mapping a single exception to two different statuses depending on call site is exactly
  the ambiguity to avoid. Distinct exception => distinct status, no router guesswork.

Mapping summary:
- Missing/invalid token (no identity) -> `get_current_user` -> **401**.
- Valid token but wrong `current_password` -> `InvalidCurrentPassword` -> **400**.

---

## 5. `ChangePasswordRequest` schema  (DECISION: mirror register's password rules)

```python
# backend/app/schemas/auth.py  (addition)
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
```

**Why:**
- `new_password` mirrors `RegisterRequest.password` exactly (`min_length=8, max_length=128`)
  so the strength contract is consistent across register and change. A weak new password is
  a **422** (Pydantic validation) before the service runs.
- `current_password` only needs `min_length=1` (non-empty). It is verified against the hash,
  not re-validated for strength — an old password might predate any rule. Empty current
  password -> 422.
- No `field_validator` needed; both are plain strings with length bounds.

---

## 6. Change-password response  (DECISION: 204 No Content)

**Chosen: `PUT /api/auth/me/password` -> 204 No Content, empty body on success.**

**Why over `200 + body`:** the operation is a pure side effect; there is no resource
representation worth returning (we are NOT returning the new password or token). 204 is the
REST-idiomatic answer for a successful mutation with nothing to send back. The frontend
treats any 2xx as success and refreshes nothing (profile fields unchanged). Tradeoff: clients
must not try to parse a JSON body — acceptable and standard. The existing `/login` returns a
body because it has a token to deliver; `/me/password` does not, so the asymmetry is correct.

---

## 7. Token storage on the client  (DECISION: IN-MEMORY — confirmed by user)

**Chosen: in-memory module-level variable in `frontend/src/auth/storage.ts`.** The token
is intentionally lost on page reload; the user must re-login after a refresh. User confirmed
this tradeoff for XSS resistance.

Options weighed (opaque token, no TTL, in-memory backend, test project):

| Option | Survives reload | XSS exposure | Fit here |
|---|---|---|---|
| localStorage | yes | readable by any injected JS | rejected — XSS can steal token |
| sessionStorage | per-tab only | same XSS exposure | loses token on tab close, same risk as localStorage |
| **in-memory (JS var)** | **no** | **not persisted, not JS-accessible across scopes** | **chosen — safest vs XSS; re-login on reload accepted** |
| httpOnly cookie | yes | not readable by JS (best vs XSS) | needs backend Set-Cookie + CSRF handling + CORS credentials — violates "minimal", adds backend work this change excludes |

**Decision rationale:**
- **Plainly: a token in `localStorage` is readable by any JavaScript that runs on the page,
  so a successful XSS injection can steal the session token.** The user chose to prioritise
  XSS resistance over surviving page reloads.
- In-memory storage means the token lives only as long as the page session. A full reload
  clears it → the user lands on the Login screen → must re-authenticate. This is the
  intentional and documented behaviour.
- The truly secure production answer is an **httpOnly, Secure, SameSite cookie** set by the
  backend, which is explicitly out of scope (it would add Set-Cookie, CORS `credentials`,
  and CSRF handling — expands all three PRs).

**Implementation:** `auth/storage.ts` exposes three functions backed by a module-level `let`:

```ts
// frontend/src/auth/storage.ts
let _token: string | null = null;

export function getToken(): string | null { return _token; }
export function setToken(token: string): void { _token = token; }
export function clearToken(): void { _token = null; }
```

`storage.ts` is the **single storage seam** — if the decision is ever revisited, only this
file changes. All other code calls `getToken`/`setToken`/`clearToken` and is storage-agnostic.

**E2E consequence (D3):** Playwright simulates session clearing by reloading the page
(`page.reload()`). Because the in-memory token is gone after reload, the app correctly
shows the Login screen. No `localStorage.clear()` call is needed or correct.

---

## 8. Frontend ↔ backend integration  (DECISION: Vite dev-server proxy for dev)

**Chosen for dev: Vite dev-server proxy.** The frontend calls same-origin `/api/...`; Vite
proxies to `http://127.0.0.1:8000`.

```ts
// frontend/vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
```

**Why proxy over CORS for dev:**
- Same-origin requests in dev => **no CORS at all**, no preflight, no `Set-Cookie`/credentials
  subtleties. The frontend code uses relative `/api` URLs and is environment-agnostic.
- No backend change required — keeps PR1 (backend) free of frontend concerns.

**Tradeoff / prod implication:** in production the SPA is typically served by the same origin
as the API (reverse proxy / static mount), so relative `/api` still works and CORS stays
unneeded. **If** prod ever serves the SPA from a different origin, add
`from fastapi.middleware.cors import CORSMiddleware` (ships with FastAPI/Starlette — **no new
package**) in `create_app()`. Confirmed: `fastapi.middleware.cors` is part of the installed
FastAPI/Starlette, so this fallback also respects the no-new-deps constraint. We do not add it
now (YAGNI for dev-proxy setup).

---

## 9. Frontend structure  (DECISION: `frontend/`, minimal, conditional rendering — NO react-router)

```
frontend/
  index.html
  package.json
  vite.config.ts
  src/
    main.tsx              # mounts <App/>
    App.tsx               # top-level guard: token? -> authed view : auth view (conditional render)
    api/client.ts         # fetch wrapper: base /api, attaches Bearer header, parses errors
    auth/storage.ts       # getToken/setToken/clearToken over a module-level let (in-memory, single seam)
    components/
      RegisterForm.tsx
      LoginForm.tsx
      Profile.tsx         # GET /api/auth/me on mount, shows id/email/username
      ChangePasswordForm.tsx
```

**Routing: conditional rendering, NOT react-router.** The whole app is a single guard:
"do we have a token?" If no -> show Login/Register; if yes -> show Profile +
ChangePassword. That is one boolean. Adding react-router for two states is ceremony that
violates the MINIMAL constraint. `App.tsx` holds a `token` state (seeded from
`storage.getToken()`); login sets it, a "logout"-less design just means the token persists.

**API client shape** (the one place the Bearer header is attached):

```ts
// frontend/src/api/client.ts
import { getToken } from "../auth/storage";

const BASE = "/api";

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Request failed");
  }
  return res.status === 204 ? null : res.json();   // 204 from change-password
}

export const api = {
  register: (b) => request("/auth/register", { method: "POST", body: JSON.stringify(b) }),
  login:    (b) => request("/auth/login",    { method: "POST", body: JSON.stringify(b) }),
  me:       () => request("/auth/me"),
  changePassword: (b) => request("/auth/me/password", { method: "PUT", body: JSON.stringify(b) }),
};
```

`storage.ts` is the single storage seam (decision #7) — token lives in a module-level `let`,
intentionally lost on reload. All other code is storage-agnostic.

**Stack:** React 18 + Vite + TypeScript (TS is the Vite React default and aids the minimal
typed client; no extra runtime deps). No Redux, no react-query, native `fetch` only.

---

## 10. Playwright orchestration  (DECISION: `e2e/` at root, Playwright `webServer` starts both)

```
e2e/
  playwright.config.ts
  tests/
    auth-flow.spec.ts      # register -> login -> see profile
    change-password.spec.ts# login -> change password -> re-login with new password
```

**Both servers via Playwright `webServer` (array of two):**

```ts
// e2e/playwright.config.ts
export default defineConfig({
  testDir: "./tests",
  use: { baseURL: "http://127.0.0.1:5173" },   # Vite dev server
  webServer: [
    {
      command: "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: "../backend",
      url: "http://127.0.0.1:8000/docs",
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      cwd: "../frontend",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
```

- **baseURL** = Vite (`5173`); the SPA's `/api` proxy forwards to uvicorn on `8000`, so E2E
  traffic flows through the exact dev path users use.
- **Test users** are created **through the real register API** at the start of each spec
  (unique email per run, e.g. `user-${Date.now()}@example.com`) — no DB seeding, no fixtures
  poking internals. The backend is in-memory and fresh per uvicorn process, which is fine
  because each test registers its own user; tests must not assume a clean slate beyond their
  own unique emails.
- **Server start order** is independent; Playwright waits on each `url` healthcheck before
  running. Backend health uses `/docs` (always 200 when FastAPI is up) since there is no
  dedicated health endpoint and adding one is out of scope.

**Why `webServer` over manual scripts:** Playwright owns lifecycle (start, wait-for-ready,
teardown) and `reuseExistingServer` lets a developer keep both servers running locally while
iterating. No bespoke shell orchestration, cross-platform (Windows dev box) safe.

---

## 11. ADR summary (decisions + rejected alternatives)

| # | Decision | Chosen | Rejected (why) |
|---|---|---|---|
| 1 | Auth dependency | `get_current_user` via `Header`, returns `UserRecord`, 401 vague msg | `HTTPBearer`/`Security` (OpenAPI/format coupling, harder msg control) |
| 2 | Repo accessor | `get_by_token` (+ `get_by_id`) | inline dict access in dependency (leaks layout) |
| 3 | Service methods | take resolved `UserRecord`; `get_me`, `change_password` | re-resolve by token in service (double lookup, split auth) |
| 4 | Exception | new `InvalidCurrentPassword` -> 400 | reuse `InvalidCredentials` (wrong 401 semantics post-auth) |
| 5 | Schema | `ChangePasswordRequest` mirrors register pw rules | looser/no validation (inconsistent strength) |
| 6 | Change-pw response | 204 No Content | 200+body (nothing to return) |
| 7 | Token storage | **in-memory** (`let` in `storage.ts`) — XSS-safe, lost on reload | localStorage (XSS-readable), cookie (not minimal, backend work) |
| 8 | Dev integration | Vite proxy `/api` | CORS middleware now (unneeded for same-origin dev) |
| 9 | Frontend | `frontend/`, conditional render, native fetch | react-router/Redux (overkill for 1 boolean of state) |
| 10 | E2E | `e2e/` + Playwright `webServer` (both servers) | manual shell scripts (no lifecycle/teardown) |

## 12. Architectural risks / assumptions

- **R1 (token storage — reload UX)** — in-memory token is lost on page reload; user must
  re-login. This is the intentional tradeoff for XSS resistance (decision #7, confirmed by
  user). localStorage was explicitly rejected. No open sign-off required.
- **R2 (in-memory state)** — restarting uvicorn wipes all users/tokens. Acceptable for a test
  project; E2E must register its own users each run (assumed, encoded in decision #10).
- **R3 (Pydantic mutability)** — in-place `user.hashed_password = ...` relies on `UserRecord`
  being a mutable Pydantic model shared by reference across both repo dicts. Verified true in
  current code; a future switch to frozen models would require a `repo.update` seam.
- **R4 (no health endpoint)** — Playwright backend healthcheck uses `/docs`. If FastAPI docs
  are ever disabled, swap to a dedicated `/health` (out of scope now).
- **Assumption** — `fastapi.middleware.cors` ships with installed FastAPI/Starlette (no new
  dep) if CORS is ever needed; not added now.
