# AI Career Navigator – Project Handover & State Ledger

This document tracks the ongoing operational state of the codebase across engineering sessions. Every session logs its latest status on top with the model name and date.

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

### In progress
- Assessment Stage 1 complete. Awaiting user review before Stage 2.

### Broken or risky
- None.

### Next (Assessment Stage 2 upon approval)
- Implement pure-function deterministic scoring:
  - Reverse scoring handling for reverse-scored items.
  - Per-dimension scores normalized 0–100%.
  - Top-3 Holland code synthesis with documented tie-breaking rules.
  - Require all 30 questions answered on submission (returning missing question IDs otherwise).
- Implement minimal `careers` table (`id`, `name`, `status` [draft/verified], `source_url`, numeric dimension profile) and seed 8 draft careers.
- Implement code-based career similarity ranking matching student vector to career vectors.
- Implement Grade 11/12 stream mapping table returning recommended subjects/streams before careers.
- Wire LLM Gateway for natural language explanation and personalized reasons per code-chosen career, with `post_validator` rejecting unverified career IDs.
- Implement immutable `AssessmentResult` table with version 1, 2, 3... per user (`uq_user_assessment_version`), safe concurrency, and guidance disclaimer note.
- Add comprehensive scoring math tests (6 cases: all 1s, all 5s, mixed, reverse-scored, tie), double submit idempotency, and retake version increments.

### Do not touch
- `docs/CONSTRAINTS.md`: Core product constraints are locked.
- Deterministic scoring rule: AI never calculates scores or ranks careers.
- Question versioning integrity: answers must tether to their attempt's version.
