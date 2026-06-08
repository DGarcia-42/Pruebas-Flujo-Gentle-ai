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
                                ┌────────────────┘
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

## All 18 tasks completed (✓)

**PR1 Backend:** T-01 through T-09 COMPLETED
- T-01: repo accessors (get_by_token, get_by_id) ✓
- T-02: InvalidCurrentPassword exception ✓
- T-03: ChangePasswordRequest schema ✓
- T-04: get_current_user dependency ✓
- T-05: get_me service method ✓
- T-06: change_password service method ✓
- T-07: GET /api/auth/me endpoint ✓
- T-08: PUT /api/auth/me/password endpoint ✓
- T-09: Final pytest verification ✓

**PR2 Frontend scaffold + auth:** T-10 through T-14 COMPLETED
- T-10: Vite+React+TS scaffold ✓
- T-11: api/client.ts fetch wrapper ✓
- T-12: auth/storage.ts in-memory storage ✓
- T-13: RegisterForm, LoginForm, App.tsx conditional ✓
- T-14: Vite proxy config ✓

**PR3 Profile + E2E:** T-15 through T-18 COMPLETED
- T-15: Profile component ✓
- T-16: ChangePasswordForm component ✓
- T-17: Playwright config with dual webServer ✓
- T-18: E2E suite (E2E-01..06) ✓

---

## Spec/design conflict resolution (noted in tasks)

**PASS-05 status code conflict:** Original spec said 401, design decision #4 locked it to 400. Implementation correctly returns 400 + "La contraseña actual es incorrecta". This was flagged in sdd-verify and RESOLVED (both spec and implementation now agree on 400).

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
**Decision needed before apply: Yes** — confirm stacked-to-main vs feature-branch-chain before PR1 is opened.
