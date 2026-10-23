# AI Career Navigator – Project Handover & State Ledger

This document tracks the ongoing operational state of the codebase across engineering sessions. Every session logs its latest status on top with the model name and date.

---

## Session: 2026-10-23 (Antigravity) – Assessment Engine Stage 2 (Scoring, Career Ranking & Immutable Results)

### Done
- **Data Models & Migration**:
  - Created `Career` model (`app/models/career.py`) with `code`, `title`, `cluster`, `overview`, `status` (`draft`/`verified`), `source_url`, `dimension_weights` (JSONB, 0-100 RIASEC scale), `reviewer`, `verified_at`.
  - Created `AssessmentResult` model (`app/models/assessment.py`) with `user_id`, `attempt_id`, `assessment_version_id`, `version`, `dimension_scores` (JSONB), `holland_code` (e.g. "IAS"), `holland_code_label`, `traits` (JSONB), `skills` (JSONB), `recommended_streams` (JSONB, optional), `career_suggestions` (JSONB), `ai_explanation`, `disclaimer_note`, and `UniqueConstraint("user_id", "version", name="uq_user_assessment_result_version")`.
  - Authored Alembic migration `alembic/versions/003_create_careers_and_assessment_results.py`.
- **Seeding & Career Verification CLI**:
  - Seeded 8 diverse draft careers in `app/data/seed/careers.json` with documented 0-100 RIASEC dimension profiles.
  - Built idempotent career seeder `scripts/seed_careers.py`.
  - Built verification CLI `scripts/verify_career.py` (`--code`, `--id`, or `--all`, with mandatory `--reviewer` and automatic timestamp recording).
  - Added `ALLOW_DRAFT_CAREERS: bool = False` to `app/core/config.py` (prohibiting drafts in production).
- **Pure-Function Deterministic Scoring & Similarity Engine (`app/services/scoring_service.py`)**:
  - `compute_riasec_scores`: Reverse scoring inversion (`6 - raw`), raw-to-percentile normalization `((raw_sum - 5) / 20) * 100`, handling dimension name normalization.
  - `derive_holland_code`: Top-3 Holland code derivation with canonical RIASEC tie-breaking (`R -> I -> A -> S -> E -> C`).
  - `derive_traits_and_skills`: Deterministic mapping of vocational strengths and competencies.
  - `calculate_career_similarity`: Euclidean vector distance in 6D $[0, 100]^6$ normalized to $0.0-1.0$.
  - `rank_careers`: Mathematical ranking with deterministic tie-break: similarity score descending, title ascending.
  - `map_streams_for_grade_11_12`: Academic stream mapping (Science PCM/PCB, Commerce with Math, Humanities) returned before careers for `class_11_12` students.
- **LLM Gateway Integration & Strict AI Boundary**:
  - Authored prompt template `app/llm/prompts/assessment_explanation_v1.txt`.
  - AI receives **only numbers and career catalog summaries** (zero user name, email, or free text).
  - `post_validator` checks that every career ID referenced in AI output exists in the code-chosen top-3 list.
  - Fallback factory provides strongly typed deterministic narrative and reasons if AI fails or references unauthorized IDs.
- **Service & Endpoints**:
  - `POST /v1/assessment/submit`: Idempotent submission, validates all 30 questions answered (returning 400 with missing questions list otherwise), handles concurrency safely, saves immutable result version.
  - `GET /v1/assessment/results/latest`: Retrieves student's latest assessment result.
  - `GET /v1/assessment/results`: Retrieves all historical assessment versions for the authenticated student.
  - `GET /v1/assessment/results/{result_id}`: Retrieves specific result enforcing strict tenant ownership (returns 404 for unauthorized users).
- **Testing & Verification**:
  - Authored 14 unit and integration tests in `tests/test_assessment_stage2.py` covering:
    - 6 fixed scoring math cases (all 1s, all 5s, neutral 3s, distinct high dimensions, reverse scoring precision, canonical tie-breaking).
    - Career vector similarity exact matching and deterministic tie-breaking.
    - Grade 11/12 stream mapping.
    - Missing answers 400 response with missing question IDs list.
    - Full end-to-end submission, idempotent double submit, retake version 2 creation, all results list.
    - Draft careers exclusion when `ALLOW_DRAFT_CAREERS=false`.
    - AI unknown career ID rejection activating deterministic fallback.
    - Strict multi-tenant ownership isolation (404 on cross-user attempt/result access).
  - Full test suite execution: **46 passed, 1 skipped** (live Gemini smoke test). Zero ruff lint errors.
- **Documentation**:
  - Added ADR-010 in `docs/DECISIONS.md`.

### In progress
- Assessment Engine Stage 2 complete and verified. Awaiting user review before proceeding to Q&A (`/v1/assessment/results/{id}/ask`) and career choice endpoints.

### Broken or risky
- None. All test suites pass cleanly.

### Next (Q&A & Career Choice Step upon approval)
- Add `POST /v1/assessment/results/{id}/ask` with Pydantic schema `{answer, referenced_career_ids, in_scope: bool}`, question max 500 chars, delimiter tag stripping, last 6 messages sliding window, max 50 messages per result thread, per-user daily rate limiting.
- Add "choose this career" endpoint setting the student's preferred career.

### Do not touch
- `docs/CONSTRAINTS.md`: Core product constraints are locked.
- Deterministic scoring rule: AI never calculates scores or ranks careers.
- Strict AI boundary: AI never receives user name, email, or unvetted free text.
- Production auth: Bearer JWT only; zero test-user fallback headers in `app/`.

---

## Session: 2026-10-23 (Gemini 3.8 Flash (Medium)) – Assessment Engine Stage 1 (Questions, Drafts & Resuming)

### Done
- Implemented Stage 1 models in `app/models/assessment.py`:
  - `AssessmentVersion` (`id` [UUID], `version_number` [int, unique], `title`, `description`, `is_active`).
  - `AssessmentQuestion` (`id` [UUID], `assessment_version_id` [FK cascade], `question_order`, `text`, `dimension`, `reverse_scored`, `is_active`).
  - `AssessmentAttempt` (`id` [UUID], `user_id` [FK cascade], `assessment_version_id` [FK restrict], `status` ['draft'/'submitted'], `started_at`, `submitted_at`).
  - `AssessmentAnswer` (`id` [UUID], `attempt_id` [FK cascade], `question_id` [FK cascade], `value` [1-5], `uq_attempt_question_answer` UniqueConstraint).
- Authored 30 original RIASEC-dimension questions (5 per dimension across Realistic, Investigative, Artistic, Social, Enterprising, Conventional, including reverse-scored items) in `app/data/seed/assessment_questions.json` under CC0 Public Domain dedication without copying proprietary question banks.
- Built idempotent database seeding script in `scripts/seed_assessment.py` to seed or update versioned assessment questions.
- Generated Alembic database migration `alembic/versions/002_create_assessment_tables.py` with upgrade and downgrade schema transitions.
- Implemented `AssessmentRepository` (`app/repositories/assessment_repository.py`) and `AssessmentService` (`app/services/assessment_service.py`).
- Implemented authenticated endpoints in `app/api/v1/assessment.py`:
  - `GET /v1/assessment/questions`: Returns ordered active 30 questions with Likert scale descriptions.
  - `GET /v1/assessment/attempt`: Resumes or initializes active draft attempt.
  - `POST /v1/assessment/answers` & `PUT /v1/assessment/answers`: Upserts draft answers and saves progress (validating 1-5 range, version integrity, and `extra="forbid"`).
  - `GET /v1/assessment/attempts/{attempt_id}`: Strict multi-tenant attempt lookup returning 404 for unauthorized users.
- Authored comprehensive test suite in `tests/test_assessment.py` (ordered questions, draft save/resume, value bounds 1-5, invalid question rejection, ownership isolation). Real pytest run: 32 passed, 1 skipped (live Gemini smoke test).
- Added ADR-009 in `docs/DECISIONS.md` documenting why questions are versioned and why code ranks careers instead of AI.
