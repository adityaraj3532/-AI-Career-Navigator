# Architectural Decision Records (ADR)

This document tracks all foundational technology and architecture choices, evaluating options, rationales, trade-offs, and conditions under which the decisions should be revisited.

---

## ADR-001: Web Framework – FastAPI

- **Options Considered**:
  - FastAPI
  - Django / Django REST Framework
  - Flask / Quart
- **Choice**: **FastAPI**
- **Reason**:
  - Native asynchronous (`async`/`await`) architecture perfectly aligned with modern async database drivers (`asyncpg`) and Redis.
  - Built-in data validation and serialization via Pydantic V2, ensuring strict schema enforcement at HTTP boundaries.
  - Automatic OpenAPI / Swagger documentation generation and first-class typing support.
- **Trade-off**:
  - Requires explicit architectural scaffolding (e.g., repository layer, worker queue integration) compared to batteries-included frameworks like Django.
- **Revisit if**:
  - Project requirements shift toward monolithic server-rendered admin interfaces with heavy pre-built ORM admin panels that Django provides out-of-the-box.

---

## ADR-002: Primary Datastore – PostgreSQL with SQLAlchemy & Alembic

- **Options Considered**:
  - PostgreSQL (via SQLAlchemy + asyncpg + Alembic)
  - MongoDB
  - MySQL
- **Choice**: **PostgreSQL**
- **Reason**:
  - Strong ACID guarantees, relational integrity, foreign key constraints, and mature index structures crucial for catalog verification (colleges, exams, resources).
  - Robust JSONB support allowing structured semi-dynamic documents (e.g., assessment answer payloads, structured roadmaps) alongside rigid relational schemas.
  - SQLAlchemy 2.0 provides type-safe async query compilation and repository decoupling, while Alembic guarantees deterministic schema migrations.
- **Trade-off**:
  - Requires maintaining disciplined schema migration files for data evolution.
- **Revisit if**:
  - The domain evolves into purely unstructured, high-velocity un-indexed time-series logs requiring distributed non-relational storage engines.

---

## ADR-003: Background Worker Queue – ARQ vs Celery

- **Options Considered**:
  - ARQ (Async Redis Queue)
  - Celery
- **Choice**: **ARQ**
- **Reason**:
  - ARQ is natively asynchronous, non-blocking, and built directly on Python `asyncio` and `redis-py` (hiredis), matching FastAPI’s async runtime seamlessly.
  - Celery is notoriously complex to configure, suffers from fragile Windows OS support (requiring custom thread pool workarounds that are unstable in local dev), and relies heavily on synchronous execution threads unless wrapped in gevent/eventlet.
  - ARQ has minimal operational footprint and native serialization for async task payloads.
- **Trade-off**:
  - Celery has a broader ecosystem of legacy plugins and canvas workflows (e.g., chords, groups), but ARQ provides all necessary primitives for background LLM processing and async email/task handling.
- **Revisit if**:
  - Multi-broker topologies (RabbitMQ/SQS) or highly complex distributed task graph orchestration (chords/chains) exceed ARQ’s async task chaining capabilities.

---

## ADR-004: LLM Gateway – Google Gemini Encapsulated in Custom Module

- **Options Considered**:
  - Direct calls to Google Gemini API scattered across API endpoints/services
  - Third-party orchestrators (LangChain, LlamaIndex)
  - Custom Internal LLM Gateway Module using official `google-genai` SDK
- **Choice**: **Custom Internal LLM Gateway Module (`app/llm/`)**
- **Reason**:
  - Provides full control over strict Pydantic JSON validation, automated retry policies, prompt versioning, and deterministic fallback responses without 3rd party black-box overhead.
  - Shields business domain logic from upstream SDK breaking changes and vendor lock-in.
  - Google Gemini offers competitive latency, long-context understanding, and native JSON structured output support.
- **Trade-off**:
  - We maintain our own fallback mechanisms, token counters, and retry backoff handlers.
- **Revisit if**:
  - Multiple model providers (Anthropic, OpenAI, local open-source models) need active multi-provider routing, load balancing, or dynamic cost-arbitrage routing.

---

## ADR-005: Scoring Logic – Deterministic Code vs LLM Evaluation

- **Options Considered**:
  - LLM computes assessment scores, skill readiness, match percentages, and career levels.
  - Deterministic Python scoring engines in code (`app/services/`), with LLM used strictly for phrasing and personalization.
- **Choice**: **Deterministic Code Computation**
- **Reason**:
  - LLM calculation of scores and percentiles is inherently non-deterministic, prone to calculation hallucinations, and impossible to audit for fairness.
  - Real products require mathematically reproducible, auditable, and unit-tested business logic for user assessment scoring, career match algorithms, and milestone progressions.
  - LLMs are reserved for what they excel at: natural language synthesis, customized coaching commentary, and personalized phrasing of deterministic results.
- **Trade-off**:
  - Engineering team must explicitly model and code scoring rules and algorithms in Python services.
- **Revisit if**:
  - Never. Scoring integrity and auditability are foundational non-negotiables for educational and career advisory products.

---

## ADR-006: Database Driver – Single Driver Architecture (`asyncpg` Only)

- **Options Considered**:
  - Dual drivers: `asyncpg` for FastAPI runtime + `psycopg2-binary` for Alembic migrations.
  - Single driver: `asyncpg` exclusively for both runtime API and Alembic migrations via Alembic's async template.
- **Choice**: **Single Driver (`asyncpg` Only)**
- **Reason**:
  - Alembic natively supports async runners (`run_async_migrations` using `async_engine_from_config` and `connection.run_sync()`), eliminating the need for a secondary synchronous driver.
  - Eliminates extra build-time C-dependencies (`psycopg2-binary`) and prevents dual-driver connection string drift in configuration files.
- **Trade-off**:
  - Requires `alembic/env.py` to use `asyncio.run(run_async_migrations())` for online migrations.
- **Revisit if**:
  - Explicit Alembic plugins or offline schema generation tools require synchronous DBAPI connections that cannot execute within `run_sync`.

---

## ADR-007: LLM Gateway Resilience – Deterministic Fallback instead of Fail-Open

- **Options Considered**:
  - Fail-Open: Return unvalidated raw LLM strings or partially formed payloads on provider error or timeout.
  - Hard Error: Raise HTTP 500 / unhandled exceptions on AI failures.
  - Deterministic Fallback: Every gateway call requires a `fallback_factory` supplying a strongly typed, code-computed fallback instance conforming to the target Pydantic schema.
- **Choice**: **Deterministic Fallback**
- **Reason**:
  - User journeys in career counseling cannot break due to transient AI latency, upstream outages, or malformed JSON.
  - Failing open violates our core security constraints by allowing hallucinated IDs, unvalidated outputs, or prompt leakage into consumer applications.
  - Deterministic fallbacks guarantee that the frontend and downstream consumers always receive fully validated, compliant data structures even under complete upstream LLM disruption.
- **Trade-off**:
  - Callers must author domain-appropriate fallback factories.
- **Revisit if**:
  - Never. Deterministic fallback guarantees high availability and zero user-facing crash states.

---

## ADR-008: Auth Architecture – UUIDs, PyJWT, Opaque Tokens & Family Reuse Detection

- **Options Considered**:
  - User identifiers: Serial autoincrement integers vs PostgreSQL UUIDs (`uuid.UUID`).
  - JWT Engine: `python-jose` vs `PyJWT`.
  - Refresh Tokens: Stateless self-contained JWTs vs Opaque DB-tracked tokens with family rotation.
- **Choice**: **PostgreSQL UUIDs + PyJWT + Opaque SHA-256 Hashed Tokens with Token Family Reuse Detection**
- **Reason**:
  - **UUIDs**: Prevent ID enumeration and resource scraping across multi-tenant endpoints; client cannot guess another student's user ID.
  - **PyJWT**: Actively maintained, strictly RFC 7519 compliant, and enforces unambiguous algorithm pinning (`HS256`), eliminating `alg: none` header bypass attacks.
  - **Opaque Refresh Tokens with SHA-256 Hashing**: Prevents token theft via database inspection. Allows instantaneous server-side revocation upon logout or password change.
  - **Token Family Reuse Detection**: Each token generation chain shares a `family_id`. If an already-used or revoked refresh token is presented (indicating a replay or stolen token), the gateway immediately revokes all tokens across the entire family, protecting the user account.
- **Trade-off**:
  - Requires database roundtrips during token rotation (mitigated by indexed SHA-256 hash lookup).
- **Revisit if**:
  - Highly distributed edge deployments strictly require zero-datastore token verification without revocation requirements.

---

## ADR-009: Assessment Architecture – Versioned Question Banks & Deterministic Career Ranking

- **Options Considered**:
  - Mutable questions without versioning vs Immutable versioned question sets (`assessment_versions`).
  - LLM selects and ranks recommended careers vs Code computes similarity rankings from verified database vectors.
- **Choice**: **Versioned Question Banks (`assessment_versions`) + Deterministic Code-Ranked Careers**
- **Reason**:
  - **Versioned Questions**: Question inventories evolve over time as psychometric phrasing is refined. Versioning guarantees that historical attempts and answer records remain permanently tethered to the exact questions the student saw, enabling scientifically valid retake comparisons over years.
  - **Deterministic Code Ranking**: Careers are ranked mathematically via vector distance (e.g. Euclidean / Manhattan distance between student's normalized RIASEC scores and verified career profiles in our database). The AI is strictly barred from choosing or ranking careers; it is invoked solely to explain and personalize the code-selected careers. This completely eradicates hallucinated career IDs and guarantees 100% reproducible, auditable recommendations.
- **Trade-off**:
  - Requires maintaining explicit Holland affinity weights per career in database seed tables.
- **Revisit if**:
  - Never. Career matchmaking integrity requires auditability and strict relational foreign key verification.

---

## ADR-010: Assessment Stage 2 – Pure Vector Scoring, Strict AI Boundary & Immutable Versioned Results

- **Options Considered**:
  - Allow AI to select, rank, and explain careers simultaneously in a single prompt.
  - Compute scores and career similarity mathematically in code, passing only numbers and catalog summaries to AI, and saving immutable versioned results.
- **Choice**: **Deterministic Pure-Function Vector Scoring & Career Ranking with AI Isolation**
- **Reason**:
  - **Mathematical Reproducibility**: 30-item Likert 1-5 inventory with reverse-scoring is scored deterministically in pure functions with 0-100 normalization and a canonical tie-break (`R -> I -> A -> S -> E -> C`), generating reproducible Holland codes (e.g. `IAS`).
  - **Vector Similarity**: Careers are ranked via Euclidean vector similarity between the student's normalized 6D vector and the career's `dimension_weights` in $[0, 100]^6$. Tie-breaks sort by similarity descending, then career title ascending.
  - **Academic Stream Sequencing**: For high school students (`education_level == "class_11_12"`), recommended curriculum streams (Science PCM/PCB, Commerce with Math, Humanities) are mapped and returned before careers.
  - **Strict AI Privacy & Delimitation**: AI receives **only numbers and career summaries**—never user name, email, or unvetted free text. Post-validation asserts every referenced career ID belongs to the code-selected list; any discrepancy triggers the deterministic fallback.
  - **Idempotency & Concurrency Safety**: Submissions are idempotent. Re-submitting the same attempt returns the existing immutable result record. Concurrent submissions are handled safely with database unique constraints (`assessment_results.attempt_id` and `uq_user_assessment_result_version`).
  - **Quality Assurance & Verification**: Careers are seeded as `draft`. Only `verified` careers are exposed in production results; draft careers are allowed only in `development` when `ALLOW_DRAFT_CAREERS=true`. A dedicated CLI (`scripts/verify_career.py`) records the reviewer and timestamp.
- **Trade-off**:
  - Requires maintaining curated multidimensional weights for all verified careers in the database.
- **Revisit if**:
  - Never. Vocational counseling integrity and student privacy require deterministic matching and zero AI hallucination of career pathways.
