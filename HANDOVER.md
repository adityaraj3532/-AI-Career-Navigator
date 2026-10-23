# AI Career Navigator – Project Handover & State Ledger

This document tracks the ongoing operational state of the codebase across engineering sessions. Every session logs its latest status on top with the model name and date.

---

## Session: 2026-10-23 (Gemini 3.8 Flash (Medium)) – Auth Step 1 (Users & Token Rotation)

### Done
- Replaced `python-jose` with `PyJWT==2.15.1`, `passlib` with standalone `bcrypt==5.0.0`, and updated `python-multipart==0.0.32` (all pinned and verified >14 days stable). Updated `docs/DEPENDENCIES.md`.
- Implemented `User` model with PostgreSQL `UUID` primary key, normalized lowercase unique email, bcrypt password hash, strict `student` default role, and `education_level` (`app/models/user.py`).
- Implemented `RefreshToken` model with UUID primary keys, SHA-256 hashed storage, `family_id` tracking, and timestamps (`app/models/auth.py`).
- Created initial database migration `alembic/versions/001_create_users_and_refresh_tokens.py` with upgrade and downgrade logic for PostgreSQL.
- Implemented security primitives in `app/core/security.py`:
  - Standalone `bcrypt` hashing with 72-byte max length enforcement.
  - Dummy bcrypt hash verification on non-existent emails to neutralize timing attacks on login.
  - Strict 15-minute `PyJWT` access token issuance with algorithm pinned to `HS256` (rejecting `none` and all other algs).
  - Opaque cryptographically random refresh tokens and SHA-256 hashing.
- Implemented `UserRepository` and `TokenRepository` (`app/repositories/`).
- Implemented `AuthService` (`app/services/auth_service.py`):
  - Signup (strictly `student` role, `extra="forbid"` on schemas).
  - Login (identical error response for unknown email and wrong password with dummy hash timing defense).
  - Refresh token rotation on every use with **Token Family Reuse Detection** (revokes entire family if an already-used or revoked token is re-submitted).
  - Logout and Logout-All (revoking active user refresh sessions).
  - Change-Password (verifies current password, updates hash, revokes all user sessions).
- Created CLI admin provisioning script (`scripts/create_admin.py`).
- Configured ARQ scheduled token purge task (`delete_expired_tokens_task` running daily at 03:00 UTC).
- Implemented strict `get_current_user` dependency in `app/api/deps.py` (Bearer JWT only, zero test-user fallback headers).
- Created comprehensive test suite in `tests/test_auth.py` (16 test cases). Real test run: 28 passed, 1 skipped (Gemini live key).
- Documented architectural decisions in `docs/DECISIONS.md` (ADR-008: UUIDs, PyJWT, Opaque Tokens, and Family Reuse Detection).

### In progress
- Auth Step 1 complete. Awaiting review before proceeding to Auth Step 2 (Password reset with ARQ email queue, Redis login rate limiting with in-process fallback).

### Broken or risky
- Local PostgreSQL service was offline on developer machine during session; unit & integration tests ran with test isolation repository double in `tests/conftest.py`. Real PostgreSQL is executed via `.github/workflows/ci.yml` service container.

### Next (Auth Step 2 upon approval)
- Implement single-use 30-minute password reset tokens with SHA-256 hash storage, invalidating older outstanding tokens.
- Implement ARQ email queuing for password reset delivery with identical timing/response for existent vs nonexistent emails.
- Implement progressive Redis rate limiting on login (per IP and per email), signup, and reset requests, with strict in-process fallback if Redis is down.
- Once Auth is fully completed, deliver the Student Profile domain and deterministic completeness scoring.

### Do not touch
- `docs/CONSTRAINTS.md`: Core product constraints are locked.
- Production auth policy: Bearer JWT only; no test-user headers anywhere in `app/`.
- Strict schema policy: `extra="forbid"`, no `role` field in client requests.
