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

---

## ADR-011: Career Catalog Stage 1a – Relational Normalization, Integer Salary Bounds & Verification Gates

- **Options Considered**:
  - Embedded JSONB documents on `careers` for exams, colleges, courses, certificates, internships.
  - Fully normalized relational schema with dedicated tables and composite primary key association tables (`career_exams`, `career_colleges`, `career_courses`, `career_certificates`, `career_internships`, `career_related`, `college_exams`).
- **Choice**: **Fully Normalized Relational Architecture with Selectinload & Verification Gates**
- **Reason**:
  - **Relational Integrity & Deduplication**: Real-world entities (e.g. `JEE_MAIN`, `Indian Institute of Technology Bombay`) link to dozens of different engineering and science careers. Normalizing them prevents data duplication, update anomalies, and out-of-sync accreditation metadata.
  - **Bounded Eager Loading ($O(1)$ Queries)**: Using SQLAlchemy `lazy="selectin"` on secondary relationships ensures eager loading executes exactly 1 query per relation type using `WHERE id IN (...)`, completely avoiding $N+1$ query explosion regardless of linked entity counts.
  - **Self-Relation Guard**: The `career_related` association table enforces `CHECK (career_id != related_career_id)` at the database engine level, preventing circular self-reference bugs.
  - **Salary as Integer INR per Year**:
    - Floating-point representations introduce precision drift in financial calculations and search filters.
    - Ambiguous monthly vs annual figures confuse students across differing regional compensation models.
    - Specifying exact `{min, max}` integer bounds in INR per year across standardized bands (`entry`, `mid`, `senior`), explicitly labelled approximate with `as_of_year` and `source_url`, enables deterministic SQL range indexing and transparent student guidance.
  - **Drafts Policy & Verification Integrity**:
    - All initial seed records are created with `status="draft"` alongside authoritative `source_url`.
    - Sensitive college fields (`fees`, `cutoffs`, `nirf_rank`) remain `null` until manually verified and must include a reporting year to avoid misleading students with outdated fee or percentile expectations.
    - Only `verified` records are visible in production APIs unless `ENVIRONMENT=development` and `ALLOW_DRAFT_CAREERS=true`.
- **Trade-off**:
  - Requires maintaining explicit junction tables and structured seed catalogs.
- **Revisit if**:
  - Catalog requirements pivot to purely unvetted third-party web scraper feeds without data verification guarantees.

---

## ADR-012: Career Compatibility Service, Shortlisting & Comparison (Stage 1)

- **Options Considered**:
  - Mutable single compatibility score column on user-career junction vs Append-only snapshots (`user_career_compatibility_snapshots`).
  - Score missing data as 0 vs Exclude missing factors and re-normalise remaining weights to 1.0.
  - LLM computes compatibility score vs Deterministic pure scoring function with decoupled AI explanation.
- **Choice**: **Deterministic Pure Function Scoring with Missing Factor Re-normalisation, Append-Only Snapshots with `inputs_hash` Deduplication, and Hard Shortlist Invariants**
- **Reason**:
  - **Transparent Re-normalisation Math**: Scoring students on unprovided parameters (e.g. penalized with 0 because they haven't filled budget or hours yet) severely distorts guidance. When a factor has no user input, it is excluded and remaining weights are re-normalised ($W_P = \sum_{f \in P} w_f$, $w'_f = w_f / W_P$, $\sum w'_f = 1.0$). The API explicitly reports `data_completeness` (0–100) and `excluded_factors`.
  - **Deterministic Pure Function**: Scoring calculation is 100% deterministic, pure, and fast ($< 5$ms). The AI never touches, calculates, or overrides the numbers.
  - **Append-Only Snapshots & Deduplication**: Compatibility changes as a student's skills, assessment results, or availability evolve. Snapshots are append-only to preserve vocational progression history. To prevent database bloat, an SHA-256 `inputs_hash` covers `(career_id, weights_version, assessment_result_id, budget_level, hours_available_per_week, subjects_of_interest, skills)`. If the hash is unchanged, the existing snapshot is returned without inserting a duplicate record.
  - **Decoupled Scoring & AI Generation**: Scoring is synchronous in-request. AI qualitative commentary is decoupled into background workers (Stage 2); until then, snapshots default to `explanation_status="pending"` with a structured deterministic template.
  - **Shortlist Limit & Idempotency**: Bounded at max 20 careers per user. `POST /v1/shortlist/{id}` and `DELETE /v1/shortlist/{id}` are strictly idempotent. Unverified careers return 404.
  - **Comparison Invariant**: Accepts 2–4 distinct verified career IDs, deduplicates input IDs, and handles null college fees cleanly.
- **Trade-off**:
  - Requires maintaining versioned weight configurations (`weights_version`) and explicit hash generation across profile schemas.
- **Revisit if**:
  - Never. Mathematical transparency and auditability are non-negotiable requirements for educational counseling.

---

## ADR-013: Adaptive Testing Engine Stage 1 – Step Ladder Progression, Server-Driven Selection & Separate Assessed Skills

- **Options Considered**:
  - Continuous Item Response Theory (IRT / 2PL models) with continuous $\theta$ estimation vs Discrete 3-tier Step Ladder.
  - Client-selected question difficulty vs Server-driven adaptive item selection.
  - Overwriting self-reported skills (`StudentProfile.skills`) directly on test finish vs Maintaining separate assessed skills records (`skill_assessments`).
- **Choice**: **Discrete 3-Tier Step Ladder Progression, Pure Server-Driven Selection, and Separation of Declared vs Assessed Skills**
- **Reason**:
  - **Step Ladder over Continuous IRT**:
    - Short diagnostic assessments (5–8 items) do not possess the sample volume needed for Maximum Likelihood Estimation (MLE) or Expected A Posteriori (EAP) $\theta$ estimation to mathematically converge.
    - IRT models require pre-calibrated item difficulty ($b$) and discrimination ($a$) parameters derived from tens of thousands of historical attempts; uncalibrated IRT introduces extreme rating variance and non-intuitive score jumps.
    - A 3-step ladder (`1` Beginner $\leftrightarrow$ `2` Intermediate $\leftrightarrow$ `3` Advanced) delivers completely transparent, auditable, and reproducible transitions with documented minimum answer requirements per level (e.g. minimum 2 attempts at level 3 with $\ge 60\%$ accuracy to reach "advanced").
  - **Server-Driven Next Question Selection**:
    - The client is strictly prohibited from selecting, guessing, or submitting difficulty levels.
    - Eliminates client-side payload manipulation, prevents cheating or gaming of difficulty levels, and ensures zero answer leakage (correct options and explanations are never sent in question payloads).
  - **Separation of Declared vs Assessed Skills**:
    - Declared skills on `StudentProfile.skills` reflect user-reported interests, aspirations, and informal familiarity.
    - Empirical skill assessments reflect verified, time-stamped, and confidence-scored diagnostic performance. Conflating them destroys provenance and obscures whether a skill level was self-claimed or tested.
- **Trade-off**:
  - Requires maintaining curated question banks with explicit integer difficulty tiers (1–3) per topic and language.
- **Revisit if**:
  - The platform grows to thousands of concurrent test takers where empirical response logs enable formal item calibration for standardized psychometric IRT.

---

## ADR-014: Skill Tracker Engine (Step 1) – Multi-Source Weighted Evidence, Strict Source Caps, Append-Only Provenance, and Deterministic Reporting

- **Options Considered**:
  - Direct mutable single skill rating column on profile vs Append-only evidence log (`skill_evidence`) with aggregated state projection (`user_skills`).
  - Equal weighting across all sources vs Hierarchy of evidence weights (Test 1.0 > Project 0.6 > Roadmap 0.35 > Declared 0.15).
  - Allowing self-declarations to claim "advanced" vs Strict source level caps (declared capped at "beginner", roadmap capped at "intermediate", only tests/projects reach "advanced").
  - Invoking LLM inside `GET /v1/skills/{id}/report` vs Strictly deterministic computation with `report_status="fallback"` (decoupling AI narrative to Step 2 background job).
- **Choice**: **Multi-Source Weighted Recency Engine with Strict Non-Test Level Caps, Append-Only Provenance Log, Pure Deterministic GET Reporting, and Atomic Transaction Ingestion**
- **Reason**:
  - **Auditability & Provenance**:
    - Aggregating skill levels as a simple mutable field erases history and conflates self-reported aspiration with verified empirical mastery.
    - Append-only `skill_evidence` preserves every diagnostic test result, completed roadmap milestone, and declaration with source IDs and subtopic granularity.
  - **Source Hierarchy & Non-Test Level Caps**:
    - Self-declaration has the lowest weight (`0.15`) and is strictly hard-capped at `"beginner"` ($1.0$). Users cannot claim intermediate or advanced standing without demonstrable evidence.
    - Roadmap completion evidence is capped at `"intermediate"` ($2.0$).
    - If a user has no diagnostic test evidence, their aggregate skill level is strictly bounded by the maximum cap of their non-test sources.
  - **Recency Decay**:
    - Real-world technical proficiency degrades without practice. An exponential half-life decay model ($T_{1/2} = 30$ days, $w = 0.5^{\Delta t / 30}$) ensures recent performance weighs higher than historical milestones.
  - **No AI in GET Requests**:
    - Calling an LLM synchronously during a GET request introduces unacceptable latency (1–4s), flakiness, token cost, and potential prompt injection vulnerabilities.
    - `GET /v1/skills/{id}/report` is 100% deterministic, instant ($< 5$ms), pure, and returns structured quantitative insights (level, confidence, strengths, weak subtopics, trend) with `report_status="fallback"`. LLM narrative synthesis is deferred to Step 2 background workers.
  - **Atomic Transaction Ingestion**:
    - `POST /v1/tests/{id}/finish` commits attempt completion, subtopic performance breakdown, `skill_evidence` insertion, and `user_skills` upsert in a single database transaction, guarded by unique constraints on `(source_type, source_id)` for idempotency on retries.
  - **Security & Authorization**:
    - No public or authenticated endpoints allow creating arbitrary test or project evidence directly. Only `POST /v1/skills/declare` exists. Ownership access violations strictly return HTTP 404 to prevent resource enumeration.
- **Trade-off**:
  - Requires maintaining versioned weighting configs (`SKILL_TRACKER_WEIGHTS_V1`) and running deterministic level recalculation upon new evidence ingestion.
- **Revisit if**:
  - Step 2 is approved to incorporate asynchronous LLM narrative reporting via ARQ workers.

---

## ADR-015: Roadmap Engine Architecture (Step 1a) – Independent Cloned Roadmaps, Pure Algorithmic Scheduling, and 15% Capacity Buffer

- **Options Considered**:
  - Live pointers/foreign keys to shared template items vs Independent cloned copies (`roadmaps`, `roadmap_phases`, `roadmap_items`).
  - LLM generates calendar timelines & schedules vs Pure deterministic topological scheduling code.
  - 100% capacity packing vs 15% capacity buffer with overflow backlog.
- **Choice**: **Independent Cloned User Roadmaps, Pure Algorithmic Scheduling Engine with 15% Buffer, and Strict Tested Evidence Filtering**
- **Reason**:
  - **Why Copied Roadmaps**:
    - A student's action plan is a mutable, individualized, long-running state machine (`todo` $\rightarrow$ `in_progress` $\rightarrow$ `done` / `skipped`) spanning months.
    - If user roadmaps shared rows directly with `template_items`, editing a template (e.g. updating a curriculum, modifying an estimated duration, or revising a problem) would retroactively mutate, invalidate, or shift active student schedules.
    - Cloning template items into independent `roadmap_items` rows ensures template authors can safely publish updates (version bumps) with zero risk of breaking or altering existing active student roadmaps.
  - **Why Scheduling is Pure Code**:
    - LLMs frequently hallucinate calendar timelines, fail basic arithmetic bin-packing, violate strict prerequisite constraints, and introduce non-deterministic shifts upon repeated requests.
    - A pure, unit-tested code engine guarantees:
      1. Zero over-allocation: every scheduled week strictly obeys the user's available time.
      2. Strict graph topological ordering: prerequisite items are guaranteed to be scheduled prior to dependents.
      3. Sub-millisecond execution ($< 2$ms) with zero token costs and complete testability.
      4. Replan safety: completed and skipped milestones are preserved in place, while incomplete tasks are cleanly reorganized starting from the replan date.
  - **Why a 15% Capacity Buffer**:
    - Real-world student schedules are subject to variance, difficult concepts, and academic interruptions.
    - Scheduling at 100% capacity guarantees that a single difficult task creates an immediate cascade of overdue items.
    - A 15% buffer ($W_{\text{usable}} = \text{round}(W_{\text{avail}} \times 0.85)$) provides resilient breathing room for problem-solving retries, revision, and catch-up. Overflow items are placed into a structured backlog.
  - **Tested Evidence Only for Downweighting**:
    - Students frequently self-declare proficiency that does not hold under empirical testing.
    - Only verified diagnostic test performance (from `test_attempts` via the Skill Tracker) is authorized to downweight or skip beginner items; declared skills do not count.
- **Trade-off**:
  - Requires maintaining cloned rows in the database, slightly increasing storage footprint in exchange for isolation and historical stability.
- **Revisit if**:
  - Dynamic template updates are explicitly requested to offer opt-in roadmap migration tooling for users.

---

## ADR-016: Recommendation Engine & Action State Machine (Step 1a) – Reusable Catalog Schema, Deterministic Code-Grounded Ranking, 90-Day Freshness Window, and Skill Progress Hook

- **Options Considered**:
  - Separate dedicated tables for recommendation items vs Reusing existing `courses`, `certificates`, `internships`, and `template_items` catalog entities.
  - LLM generates fit scores and explanation dynamically inside `GET /v1/recommendations` vs Pure deterministic code ranking and rule-grounded `why_it_fits` (no AI on GET).
  - Indefinite catalog visibility vs Strict 90-day verification freshness window and expiration enforcement.
  - Free labels derived from missing costs vs Strict invariant: Never mark "free" unless verified.
  - Discarding completed recommendation items vs Hooking completed (`done`) items directly into the Skill Tracker.
- **Choice**: **Reusable Catalog Entities with Nullable Schema Enhancements, Pure Deterministic Scoring & Explanation Engine, Strict 90-Day Staleness & Expiry Filters, Reversible State Machine with Rate Limiting, and Automated Low-Weight Skill Evidence Ingestion**
- **Reason**:
  - **Schema Reusability**:
    - The database already possessed normalized catalog entities (`courses`, `certificates`, `internships`) with foreign keys to careers and domains.
    - Creating separate recommendation candidate tables would introduce data duplication, divergent sync logic, and schema bloat.
    - Adding nullable columns (`cost_inr`, `duration`, `mode`, `location`, `eligibility`, `application_deadline`, `expires_at`, `status`, `last_verified_at`) enhances existing entities without breaking existing catalog relationships.
  - **No AI Inside GET Requests**:
    - Invoking an LLM during `GET /v1/recommendations` introduces severe latency (1–4s), flakiness, token costs, and prompt hallucination risks.
    - `why_it_fits` is generated by pure, deterministic Python code matching user target career, tested skill gaps, location, budget constraints, and weekly availability.
    - Execution runs in $< 5$ms. LLM enrichment is deferred to Step 2 background ARQ workers.
  - **90-Day Staleness & Expiration Invariant**:
    - Internships, course tuitions, and application deadlines shift rapidly in the Indian higher education and edtech sectors.
    - Stale or expired opportunities degrade user trust. Any item unverified within 90 days (`(now - last_verified_at).days > 90`), past its `expires_at`, or past `application_deadline` is automatically hidden from recommendation feeds unless running in development with `ALLOW_DRAFT_CAREERS=true`.
  - **Strict "Free" Invariant**:
    - Unverified items with missing cost could mislead students into enrolling in expensive courses. An item is marked `is_free=True` strictly when `cost_inr == 0` AND the item is verified (or explicitly bypassed in dev).
  - **Action State Machine & Skill Tracker Hook**:
    - User interactions are tracked in `recommendation_actions` with unique composite constraint `(user_id, item_type, item_id)` supporting idempotent transitions (`saved`, `dismissed`, `done`, `none`).
    - Marking an item `done` automatically creates low-weight skill evidence (`source_type="roadmap"` or `"project"`, level signal `"intermediate"`) in the Skill Tracker, closing the feedback loop between discovery and skill progression.
- **Trade-off**:
  - Catalog verification requires periodic human or automated audit jobs to keep items within the 90-day freshness window.
- **Revisit if**:
  - Stage 2 AI enrichment in background ARQ workers is activated.

---

## ADR-017: Portfolio Aggregation Architecture (Step 1b) – Read-Only Multi-Domain Composition, Zero Redundant Storage, and Strict Authenticated Ownership

- **Options Considered**:
  - Materialized portfolio table (`user_portfolio_items`) with write-time dual-write synchronization vs On-demand read-only aggregation across normalized primary source domains (`student_profiles`, `user_skills`, `recommendation_actions`, `roadmap_items`, `test_attempts`).
  - LLM generates narrative resume/portfolio summary inside `GET /v1/portfolio` vs Deterministic structured Pydantic aggregation.
- **Choice**: **On-Demand Read-Only Aggregation across Primary Source Domains with Flat Batch Queries, Deterministic Summary Metrics, and Strict Authenticated Token Ownership**
- **Reason**:
  - **Zero Redundant Storage & Synchronization Safety**:
    - Materializing a separate portfolio table duplicate of completed recommendations, roadmap items, and skills introduces synchronization drift, distributed transaction failures, and stale cached states when actions are undone or updated.
    - Since completed items are already tracked in authoritative tables (`recommendation_actions` with `state="done"`, `roadmap_items` with `status="done"`, `test_attempts` with `status="finished"`, and `user_skills`), aggregating on-demand guarantees 100% data consistency without maintenance overhead.
  - **Flat Batch Query Performance**:
    - By grouping completed IDs by domain type (`courses`, `certificates`, `internships`, `resources`) and querying each entity type in a single `IN (...)` batch, the entire portfolio aggregates in 5 flat queries, eliminating N+1 access patterns and responding in $< 8$ms.
  - **No AI in GET Requests**:
    - Consistent with ADR-005, ADR-014, and ADR-016, no generative AI is invoked in `GET /v1/portfolio`. Summary metrics (`total_skills_tracked`, `total_recommendations_completed`, `total_milestones_completed`, `total_tests_completed`) are computed deterministically. AI resume phrasing is deferred to future dedicated background/export steps.
  - **Strict Authenticated Ownership**:
    - Portfolio data contains sensitive learning milestones, diagnostic test scores, and educational history. Access is strictly scoped to the authenticated `current_user` extracted from the verified JWT token.
- **Trade-off**:
  - Heavy concurrent reads on high-volume user bases will aggregate repeatedly from Postgres; however, query counts are small and read-optimized via primary keys and indexes.
- **Revisit if**:
  - Public vanity URLs (shareable portfolio links) or heavy PDF generation require Redis caching or background pre-rendering.

---

## ADR-018: Completion Architecture for All Deferred Lifecycle Steps – Background ARQ Workers, Password Reset Tokens, Public Portfolio, and Roadmap Endpoints

- **Options Considered**:
  - Synchronous execution of AI narratives & explanations inside HTTP endpoints vs Asynchronous background generation in ARQ workers with Redis caching.
  - Stateful session tracking for password resets vs Single-use 30-minute cryptographically secure SHA-256 tokens with automatic session invalidation.
- **Choice**: **ARQ Async Workers with Redis Cache Invalidation, Cryptographic Single-Use Reset Tokens, Deterministic Code Fallbacks, and Multi-Tenant Isolation Invariant**
- **Reason**:
  - **Zero LLM Latency on Read Paths**:
    - AI narratives for skill reports (`career_skill_report_v1`), compatibility explanations (`career_compatibility_v1`), and comparative verdicts (`career_compare_v1`) run asynchronously via ARQ workers and cache in Redis by deterministic evidence hash. GET endpoints return immediate fallback / pending statuses without blocking user traffic.
  - **Password Security & Enumeration Prevention**:
    - Password reset requests (`POST /v1/auth/forgot-password`) return identical responses regardless of whether the email exists, neutralizing timing/enumeration attacks with dummy bcrypt operations. Tokens are 48-byte URL-safe strings hashed with SHA-256 in the database with a 30-minute lifespan. Resetting passwords invalidates all existing refresh tokens.
  - **Public Portfolio Privacy**:
    - The public portfolio endpoint (`GET /v1/portfolio/public/{user_id}`) deliberately strips user emails and private credentials, presenting only verified skills, milestones, and credentials for recruiter sharing.
  - **Roadmap Independent Cloning**:
    - Roadmaps cloned from templates generate fresh IDs and copied milestone entities, ensuring template revisions never mutate active user plans. Re-planning is rate-limited to once per 7 days with a 15% allocation buffer.
- **Trade-off**:
  - Requires maintaining worker process (`WorkerSettings`) and Redis instances alongside the web server.
- **Revisit if**:
  - High-volume enterprise usage necessitates multi-region distributed worker clusters.

---

## ADR-019: Personalized Portfolio Architecture (Step 1a, 1b, Step 2) – Private-by-Default, Non-Writing GET Invariant, Allowlist Public Slug Projection, Grounded AI Suggestions, and Deferred PDF

- **Options Considered**:
  - Persisting a draft row into `user_portfolios` during initial `GET /v1/portfolio` vs Strictly non-writing GET returning in-memory suggestions with persistence deferred to explicit `PUT /v1/portfolio`.
  - Exposing `StudentProfile` and database entity IDs in the public portfolio view vs Strict separate allowlist projection schema stripped of emails, user IDs, and unshared metadata.
  - Hand-rolling a custom PDF generator or adding a third-party PDF compilation library vs Deferring PDF resume export until a clean frontend print stylesheet or maintained library is decided.
  - Unconstrained LLM generation for portfolio text vs Anti-hallucination post-validator verifying all numbers, years, and percentages against user-provided facts.
- **Choice**: **Non-Writing GET Invariant, Allowlist Public Slug View (`GET /v1/portfolio/p/{slug}`), Grounded Anti-Hallucination AI Suggestions (`POST /v1/portfolio/generate-text`), and Deferred PDF Export**
- **Reason**:
  - **Strict HTTP GET Idempotence and Non-Writing Safety**:
    - Under HTTP specifications, GET requests must be safe and idempotent, producing zero database side-effects. Initial GET queries synthesize computed suggestions from verified skills and roadmap items in-memory (`is_persisted=False`), persisting rows only when the student explicitly submits a `PUT /v1/portfolio`.
  - **Private-by-Default & Provenance Integrity**:
    - All sections default to `visibility = false` and `is_public = false`. Nothing from `StudentProfile` or internal user models is exposed publicly without explicit opt-in.
    - Skills are partitioned by provenance: labelled `test_assessed` only if verified assessment evidence exists; otherwise `self_reported`. Roadmap items of type project or certificate are labelled `self_reported` and never marked as verified without verification proof.
  - **Public Page Security & Anti-Leakage**:
    - `GET /v1/portfolio/p/{slug}` serves a dedicated allowlist schema (`PublicPortfolioViewResponse`). Missing, private (`is_public=False`), and non-existent portfolios return identical 404 responses to prevent slug enumeration.
    - Public responses inject `X-Robots-Tag: noindex, nofollow` and `Cache-Control: no-cache, no-store, must-revalidate` alongside IP rate-limiting.
  - **Anti-Hallucination AI Guardrails**:
    - Generative text suggestions (`generate-text`) accept at most 10 facts (max 200 chars each) and execute through `LLMGateway` with prompt-injection defense.
    - The output is verified by a strict regex post-validator: any metric, number, percentage, or year not present in the user-submitted facts is rejected, triggering a deterministic template fallback. AI suggestions are never auto-saved.
  - **Zero Dependency PDF Policy**:
    - PDF export is intentionally omitted from the backend to prevent brittle binary dependencies (e.g. wkhtmltopdf/weasyprint) and hand-rolled formatters, allowing the frontend to implement standard browser print stylesheets.
- **Trade-off**:
  - First-time users see `is_persisted=False` suggestions and must issue a PUT to establish their custom slug and persistence.
- **Revisit if**:
  - High-traffic public portfolios require edge CDN caching or static site generation (SSG) pipelines.








