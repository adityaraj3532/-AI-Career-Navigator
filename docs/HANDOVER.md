# AI Career Navigator – Project Handover & State Ledger

This document tracks the ongoing operational state of the codebase across engineering sessions. Every session logs its latest status on top with the model name and date.

---

## Session: 2026-10-23 (Gemini 3.8 Flash (Medium)) – Phase 1 Foundation

### Done
- Rebased initial scaffolding onto `origin/main` (incorporating remote `README.md`) and switched to branch `backend`.
- Configured project dependencies in `requirements.txt` with exact version pinning, logged in `docs/DEPENDENCIES.md`.
- Implemented environment-driven configuration via `pydantic-settings` (`app/core/config.py`).
- Implemented structured logging with request-ID tracking (`app/core/logging.py`, `app/core/middleware.py`).
- Implemented global error handling with single standard JSON error envelope (`app/core/exceptions.py`).
- Implemented async PostgreSQL engine and session factory using `asyncpg` exclusively (`app/core/database.py`).
- Implemented async Redis connection pool and healthcheck (`app/core/redis.py`).
- Implemented `/health` (liveness) and `/ready` (readiness checking PostgreSQL and Redis) under `/v1` router (`app/api/v1/health.py`, `app/main.py`).
- Implemented ARQ background worker bootstrap with Redis settings and sample task (`app/workers/worker.py`).
- Configured Alembic with native async runner (`run_async_migrations`) and `asyncpg` (`alembic.ini`, `alembic/env.py`).
- Authored production `Dockerfile` and updated `docker-compose.yml` (Postgres, Redis, API, ARQ worker).
- Added GitHub Actions workflow (`.github/workflows/ci.yml`) running Ruff linter and Pytest with real Postgres & Redis service containers.
- Implemented automated tests for health, ready, and standard error handling (`tests/test_health.py`, `tests/test_errors.py`). Real pytest execution: 7 passed, 0 failures.
- Documented single-driver decision in `docs/DECISIONS.md` (ADR-006).

### In progress
- Phase 1 completed. Waiting for user review before proceeding to Phase 2.

### Broken or risky
- Local Windows Docker daemon was not running during the session (client pipe `//./pipe/dockerDesktopLinuxEngine` inactive), preventing local `docker compose up` from starting containers locally. Local pytest and uvicorn runtime tests verified against local Python 3.12 environment. CI pipeline is configured with real Postgres and Redis service containers.

### Next (Phase 2 upon approval)
- Implement `User` SQLAlchemy model with `role` (`student`/`admin`) and `education_level` (`class_11_12`/`college`).
- Generate initial Alembic migration for `users` and refresh token store.
- Implement `user_repository.py` and `auth_service.py` with:
  - Refresh token rotation (storing hashed tokens, revoking on logout & password reset).
  - Single-use 30-minute password reset tokens with timing-attack resistant uniform responses.
  - Redis-based login rate limiting.
  - Ownership guard (`get_current_user` dependency ensuring students only access their own records).
- Add tests for signup, login, refresh rotation, rate limiting, and ownership protection.

### Do not touch
- `docs/CONSTRAINTS.md`: Core product and security rules are locked.
- Single standard error response envelope contract (`{"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}`).
