# AI Career Navigator – Project Handover & State Ledger

This document tracks the ongoing operational state of the codebase across engineering sessions. Every session logs its latest status on top with the model name and date.

---

## Session: 2026-10-23 (Antigravity) – Transparent Compatibility Service, Shortlist & Career Comparison (Stage 1)

### Done
- **Data Models & Migration**:
  - `Career` model (`app/models/career.py`):
    - Added `time_to_job_ready_months` (`Integer`, nullable).
    - Added `entrance_difficulty` (`String(32)`, nullable).
  - `StudentProfile` model (`app/models/profile.py`):
    - `id` (UUID PK), `user_id` (UUID FK to `users.id` with `unique=True`, `ondelete="CASCADE"`).
    - `name` (String 128), `budget_level` (String 32: low/medium/high), `hours_available_per_week` (Integer).
    - `subjects_of_interest` (`JSONB`, default `[]`), `skills` (`JSONB`, default `[]`).
    - `created_at`, `updated_at`.
  - `UserShortlist` model (`app/models/career.py`):
    - `user_id` (UUID FK, composite PK), `career_id` (UUID FK, composite PK), `created_at`.
    - `ON DELETE CASCADE`, indexed on both foreign keys.
  - `UserCareerCompatibilitySnapshot` model (`app/models/career.py`):
    - `id` (UUID PK), `user_id` (UUID FK), `career_id` (UUID FK), `overall_score` (Integer 0–100).
    - `factor_breakdown` (`JSONB`), `strengths` (`JSONB`), `gaps` (`JSONB`), `weights_version` (Integer, default 1).
    - `inputs_hash` (`String(64)`, indexed), `explanation_status` (`String(32)`, default "pending").
    - `ai_explanation` (`Text`, nullable), `created_at`.
    - Composite index `ix_user_career_comp_latest` on `(user_id, career_id, created_at DESC)`.
  - Alembic migration `005_create_compatibility_shortlist_and_profile_tables.py` (tested for both upgrade and downgrade static SQL generation).
- **Seed Catalog & Seeder Updates**:
  - Populated `time_to_job_ready_months` and `entrance_difficulty` across all 8 careers in `app/data/seed/career_catalog.json`.
  - Updated `scripts/seed_career_catalog.py` to persist these attributes idempotently.
- **Pure Scoring Function & Re-normalisation Logic (`app/services/compatibility_service.py`)**:
  - Versioned weights config: `COMPATIBILITY_WEIGHTS_V1` (interest_fit: 30, skills: 25, subjects: 20, hours: 15, budget: 10).
  - Pure calculation function `compute_career_compatibility`:
    - Dynamic missing-factor detection: factors with no data are excluded and remaining present weights re-normalise such that $\sum w'_f = 1.0$. Missing data is **never scored as 0**.
    - Returns `(overall_score, data_completeness, excluded_factors, factor_breakdown, strengths, gaps)`.
    - Boundary safety verified: clamped within $[0, 100]$.
  - SHA-256 `inputs_hash` covering `(career_id, weights_version, assessment_result_id, budget_level, hours_available_per_week, subjects_of_interest, skills)`. Deduplicates snapshot rows when inputs are unchanged.
- **Repositories & Service Layer**:
  - `ProfileRepository` (`app/repositories/profile_repository.py`) & `ProfileService` (`app/services/profile_service.py`).
  - `ShortlistRepository` (`app/repositories/shortlist_repository.py`).
  - `CompatibilityRepository` (`app/repositories/compatibility_repository.py`).
  - `CompatibilityService` (`app/services/compatibility_service.py`).
- **API Endpoints**:
  - `GET /v1/profile` & `PUT /v1/profile`
  - `POST /v1/shortlist/{career_id}` & `DELETE /v1/shortlist/{career_id}` (idempotent, max 20 limit, verified career check)
  - `GET /v1/shortlist` (returns shortlisted items with compatibility scores)
  - `GET /v1/careers/{career_id}/compatibility` (evaluates score, deduplicates snapshots via `inputs_hash`)
  - `GET /v1/careers/{career_id}/compatibility/history` (ordered by `created_at DESC`)
  - `POST /v1/compare` (accepts 2–4 distinct verified career IDs, deduplicates, handles null college fees cleanly, returns multi-dimensional comparison matrix)
- **Testing & Verification**:
  - Created 11 comprehensive tests in `tests/test_compatibility_stage1.py`:
    - 5 pure scoring cases: all factors present, 1 missing, 2 missing, all missing, boundary 0% and 100%.
    - Weight re-normalisation math verification ($\sum w'_f = 1.0$).
    - `inputs_hash` determinism, sensitivity, and list order invariance.
    - Profile get & put integration.
    - Snapshot creation and `inputs_hash` deduplication.
    - History ordering (`created_at DESC`).
    - Shortlist idempotency, 20-item cap enforcement, and strict user ownership isolation.
    - Compare endpoint 2–4 bounds, deduplication, and non-verified 404 rejection.
    - Unverified career rejection gate (HTTP 404).
  - Full project test suite execution: **65 passed, 1 skipped** (live Gemini smoke test).
  - Code hygiene: `ruff check app tests` passes with 0 warnings/errors.
- **Documentation**:
  - Added ADR-012 in `docs/DECISIONS.md`.

### In progress
- Stage 1 complete. Awaiting user review before Stage 2 (ARQ asynchronous AI explanation job for snapshots and qualitative comparison verdicts).

### Broken or risky
- None. All 65 tests pass cleanly.

### Next (Stage 2 upon approval)
- Background ARQ job worker generating personalized AI explanations for `UserCareerCompatibilitySnapshot` with status transitions (`pending` -> `completed` / `failed`).
- LLM qualitative comparison verdict generation for `POST /v1/compare` (strictly decoupled from deterministic scores).

### Do not touch
- Deterministic scoring rule: AI never calculates, overrides, or alters compatibility numbers or comparison metrics.
- Missing factors are never scored as 0.
- Strict verification gate: Only verified careers can be shortlisted, evaluated, or compared.
- Production auth: Bearer JWT only.

---

## Session: 2026-10-23 (Antigravity) – Career Catalog Step 1a (Normalized Tables, Seeding & Exploration Endpoints)

### Done
- **Data Models & Migration**:
  - Altered `careers` table (`app/models/career.py`):
    - Added `aliases` (`ARRAY(String(128))`), `description` (`Text`), `day_in_life` (`Text`).
    - Added `salary_ranges` (`JSONB`, integers in INR per year `{min, max}` for `entry`/`mid`/`senior`, labelled approximate with `as_of_year` and `source_url`).
    - Added `demand` (`String(32)`, indexed), `required_skills` (`JSONB`), `education_paths` (`JSONB`), `last_verified_at` (`DateTime(timezone=True)`).
  - Created normalized entity models:
    - `Exam`: `code`, `name`, `description`, `conducting_body`, `exam_level`, `registration_url`, `source_url`, `status`, `reviewer`, `last_verified_at`.
    - `College`: `name`, `location` (`JSONB`), `official_url`, `fees` (`JSONB`, null by default), `cutoffs` (`JSONB`, null by default), `nirf_rank` (`JSONB`, null by default), `source_url`, `status`, `reviewer`, `last_verified_at`.
    - `Course`: `code`, `title`, `degree_level`, `duration`, `description`, `source_url`, `status`, `reviewer`, `last_verified_at`.
    - `Certificate`: `code`, `name`, `issuing_organization`, `description`, `url`, `source_url`, `status`, `reviewer`, `last_verified_at`.
    - `Internship`: `code`, `title`, `domain`, `stipend_range` (`JSONB`), `duration_months`, `locations` (`JSONB`), `description`, `source_url`, `status`, `reviewer`, `last_verified_at`.
  - Created association tables with composite PKs, `ON DELETE CASCADE`, and indexes on both sides:
    - `career_exams`, `career_colleges`, `career_courses`, `career_certificates`, `career_internships`, `college_exams`.
    - `career_related`: Self-referencing association guarded by `CheckConstraint("career_id != related_career_id", name="ck_career_not_self_related")`.
  - Configured `lazy="selectin"` on all secondary relationships, guaranteeing bounded $O(1)$ query execution and eliminating $N+1$ query explosion on detail queries.
  - Authored migration `alembic/versions/004_create_career_catalog_tables.py` (tested both upgrade and downgrade SQL compilation).
- **Authoritative Catalog Seed (`app/data/seed/career_catalog.json`) & Idempotent Seeder (`scripts/seed_career_catalog.py`)**:
  - Seeded 8 flagship careers fully: Software Development Engineer (SDE), Data Analyst, AI/ML Engineer, UI/UX Designer, Doctor (MBBS/Specialist), Chartered Accountant (CA), Civil Services (IAS/IPS/IFS), Mechanical Engineer.
  - Linked to real Indian exams (JEE Main/Adv, NEET-UG, CA Foundation, UPSC CSE, GATE, UCEED), top colleges (IIT Bombay, IIT Madras, AIIMS New Delhi, ICAI, NID Ahmedabad, St. Stephen's), courses, certificates, and internships.
  - All seeded records set to `status="draft"` with authoritative `source_url`. College fees, cutoffs, and NIRF rank stay null until verified with a reporting year.
- **Verification CLI (`scripts/verify_catalog.py` & `scripts/verify_career.py`)**:
  - Extended CLI to verify `career`, `exam`, `college`, `course`, `certificate`, `internship`, or `all` records (sets `status="verified"`, `reviewer`, `last_verified_at`).
  - Enforced verification gate: only verified records appear in API responses unless `ENVIRONMENT=development` and `ALLOW_DRAFT_CAREERS=true`.
- **API Endpoints (`app/api/v1/careers.py`) & Service Layer (`app/services/career_service.py`)**:
  - `GET /v1/careers`: Supports filters (`cluster`, `demand`, `min_salary`, `max_salary`), pagination (`page_size` max 50, `page`, `total_count`, `total_pages`), stable ordering (`title asc, id asc`), and optional student compatibility scoring.
  - `GET /v1/careers/{id}`: Returns full career detail with eager-loaded exams, colleges, courses, certificates, internships, and related careers.
  - Optional Auth: If caller is authenticated and has an assessment result, real-time compatibility score (integer 0–100) is computed and attached; otherwise returns `null`.
- **Testing & Verification**:
  - Authored 8 tests in `tests/test_career_catalog.py` covering draft filtering, pagination bounds, cluster/demand/salary filtering, eager-loading structure, optional auth compatibility scoring, idempotent seeder, and migration 004 upgrade/downgrade.
  - Full test suite execution: **54 passed, 1 skipped** (live Gemini smoke test). Zero ruff lint errors.
- **Documentation**:
  - Added ADR-011 in `docs/DECISIONS.md`.

### In progress
- Step 1a complete. Awaiting user review before Step 1b (pg_trgm extension, GIN indexes, `GET /v1/careers/search` with typo-tolerance and ranked aliases).

### Broken or risky
- None. All test suites pass cleanly.

### Next (Step 1b upon approval)
- Add PostgreSQL `pg_trgm` extension and GIN trigram indexes on `title`, `overview`, and `aliases`.
- Build `GET /v1/careers/search?q=` (query max 60 chars, ranking name > alias > trigram similarity, single-pass compatibility scoring).

### Do not touch
- `docs/CONSTRAINTS.md`: Core product constraints are locked.
- Deterministic scoring rule: AI never calculates scores or ranks careers.
- Strict AI boundary: AI never receives user name, email, or unvetted free text.
- Production auth: Bearer JWT only; zero test-user fallback headers in `app/`.

---

## Session: 2026-10-23 (Antigravity) – Assessment Engine Stage 2 (Scoring, Career Ranking & Immutable Results)

### Done
- **Data Models & Migration**:
  - Created `Career` model (`app/models/career.py`) with `code`, `title`, `cluster`, `overview`, `status` (`draft`/`verified`), `source_url`, `dimension_weights` (JSONB, 0-100 RIASEC scale), `reviewer`, `verified_at`.
  - Created `AssessmentResult` model (`app/models/assessment.py`) with `user_id`, `attempt_id`, `assessment_version_id`, `version`, `dimension_scores` (JSONB), `holland_code` (e.g. "IAS"), `holland_code_label`, `traits` (JSONB), `skills` (JSONB), `recommended_streams` (JSONB, optional), `career_suggestions` (JSONB), `ai_explanation`, `disclaimer_note`, and `UniqueConstraint("user_id", "version", name="uq_user_assessment_result_version")`.
  - Authored Alembic migration `alembic/versions/003_create_careers_and_assessment_results.py`.
