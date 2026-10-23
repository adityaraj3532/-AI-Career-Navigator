# Product & Engineering Constraints

This document defines the strict, non-negotiable operational and engineering boundaries of the AI Career Navigator codebase. Every contributor, engineer, and automated agent must adhere to these rules without exception.

---

## 1. Security & Configuration
- **Never** hardcode secrets, tokens, private keys, or credentials in source code or version control.
- **Only** read secrets, credentials, and environment-specific settings from validated environment variables via `app/core/config.py`.
- **Always** check ownership: a user can only read or write their own data (enforce multi-tenant resource isolation via authenticated user ID in repositories/services).
- **Never** expose internal database IDs or stack traces to unauthenticated clients.

## 2. Artificial Intelligence & LLM Boundaries
- **Never** trust AI output: always validate AI output with strict Pydantic schemas.
- **Always** retry an invalid or malformed AI response exactly once; if validation fails a second time, immediately fall back to a deterministic, pre-computed response.
- **Never** let AI compute scores, levels, match percentages, or rankings. All scores, levels, percentiles, and ranks are computed strictly in deterministic Python code.
- **Only** allow AI to explain, personalize, contextualize, and phrase user-facing feedback based on code-calculated values.
- **Only** let AI reference resource, college, and exam IDs that actually exist in our database; reject and strip any hallucinated or unverified IDs before persisting or presenting results.
- **Never** inject raw user free-text into an LLM prompt without sanitizing and wrapping it inside explicit XML/tag delimiters (e.g., `<user_input>...</user_input>`) to prevent prompt injection attacks.
- **Always** use versioned prompt templates stored under `app/llm/prompts/`.

## 3. Database & Architecture Boundaries
- **Only** access the database through `app/repositories/`. No direct SQL or session queries inside API routers, services, or workers.
- **Always** execute schema migrations through versioned Alembic migration scripts.
- **Always** run database writes within atomic transactions.
- **Never** bypass relational foreign key integrity checks between user entities, recommendations, roadmaps, and verified catalog items.

## 4. Dependencies & Engineering Process
- **Never** add a new third-party dependency without asking for user approval first.
- **Always** log every approved dependency in `docs/DEPENDENCIES.md` with its name, pinned version, and architectural rationale.
- **Always** write automated tests for every feature or modification and inspect real test execution outputs before completing work.
- **Always** stop and ask before breaking or circumventing any rule defined herein.
