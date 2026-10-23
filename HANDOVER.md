# AI Career Navigator – Project Handover & State Ledger

This document tracks the ongoing operational state of the codebase across engineering sessions. Every session logs its latest status on top with the model name and date.

---

## Session: 2026-10-23 (Gemini 3.8 Flash (Medium))

### Done
- Established foundational directory structure:
  - `app/core/`, `app/models/`, `app/schemas/`, `app/repositories/`, `app/api/`, `app/services/`
  - `app/llm/prompts/`, `app/workers/`, `app/data/seed/`
  - `alembic/versions/`, `tests/`, `docs/`
- Created security configuration `.gitignore` (ignoring `.env`, caches, virtual environments).
- Created environment template `.env.example` with zero hardcoded secrets.
- Created `docker-compose.yml` defining PostgreSQL 16 and Redis 7 healthchecked containers.
- Created foundational engineering documentation under `docs/` (and root mirrors):
  - `ARCHITECTURE.md`: Module boundaries, standard & AI request flows, 3 trust boundaries, complete 20-entity schema outline.
  - `CONSTRAINTS.md`: Plain never/always/only rules (secrets, Pydantic validation, deterministic scoring, verified DB ID referencing, prompt sanitization, ownership checks).
  - `DECISIONS.md`: Initial ADRs for FastAPI, PostgreSQL, ARQ vs Celery, Gemini internal gateway, deterministic code scoring.
  - `DEPENDENCIES.md`: Pinned dependencies for Python 3.11+, FastAPI, SQLAlchemy, ARQ, google-genai, etc.
- Initialized Git repository and recorded initial commit.

### In progress
- None (Foundation and scaffolding step complete).

### Broken or risky
- No application code written yet (as explicitly instructed for this step). Ensure virtual environment and dependencies are installed before running application code in subsequent steps.

### Next
- Step 1: Initialize Python project dependencies (`requirements.txt` or `pyproject.toml`) matching `docs/DEPENDENCIES.md`.
- Step 2: Implement `app/core/config.py` with `pydantic-settings` to load and validate all `.env` variables.
- Step 3: Implement database engine, session factory (`app/core/database.py`), and Alembic configuration.
- Write tests for settings loading and database connection.

### Do not touch
- `docs/CONSTRAINTS.md`: Core rules are locked and require explicit approval to modify.
- Architectural boundaries defined in `docs/DECISIONS.md`.
