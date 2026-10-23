# AI Career Navigator – Project Handover & State Ledger

This document tracks the ongoing operational state of the codebase across engineering sessions. Every session logs its latest status on top with the model name and date.

---

## Session: 2026-10-24 (Antigravity) – Personalized Portfolio: Custom Portfolios, Public Vanity Pages, and Anti-Hallucination AI Text Assistant (Step 1a, Step 1b, Step 2)

### Done
- **Single Alembic Head & Migration 011**:
  - Confirmed single head at `010_create_password_reset_tokens`.
  - Created migration `011_create_user_portfolios.py` adding `user_portfolios` table: `id`, `user_id` (UNIQUE FK), `slug` (UNIQUE, indexed), `is_public` (bool default false), `headline`, `about`, `visibility` (JSONB allowlist default false), `featured_item_ids` (JSONB), `custom_projects` (JSONB), `custom_certificates` (JSONB), `competitions` (JSONB), `achievements` (JSONB), `created_at`, `updated_at`.
  - Verified `alembic heads` has single head at `011_create_user_portfolios`.
- **Pydantic Schemas (`app/schemas/portfolio.py`)**:
  - `PortfolioVisibility`: allowlist booleans per section (`about`, `skills`, `projects`, `certificates`, `competitions`, `achievements`), default `False`.
  - JSONB section items: `ProjectItem`, `CertificateItem`, `CompetitionItem`, `AchievementItem` with `extra="forbid"`, length caps, max 20 items per list, HTTP/HTTPS link validators, date string validation.
  - `UpdatePortfolioRequest`: validates optional custom slug (regex `^[a-z0-9]+(-[a-z0-9]+)*$`, 3-40 chars, reserved words list check).
  - `OwnerPortfolioResponse`: owner view returning persisted state, slug, provenance-partitioned skills (`test_assessed` vs `self_reported`), completed roadmap projects/certificates (labelled `self_reported`), custom items, and `is_persisted` flag.
  - `PublicPortfolioViewResponse`: separate unauthenticated allowlist projection schema; strips all user IDs, emails, and internal profile fields; sections omitted when `visibility[section] == False`.
  - `GeneratePortfolioTextRequest` / `GeneratePortfolioTextResponse`: section enum (`about`, `project_description`), max 10 facts $\times$ 200 chars.
- **Repository & Non-Writing GET Invariant**:
  - `PortfolioRepository` (`app/repositories/portfolio_repository.py`):
    - `get_user_skills`: partitioned by provenance (`test_assessed` if valid test evidence exists; else `self_reported`).
    - `get_user_portfolio`, `get_portfolio_by_slug`, `save_user_portfolio`.
  - `PortfolioService` (`app/services/portfolio_service.py`):
    - `GET /v1/portfolio`: **MUST NOT write to DB**. If no row exists, returns computed suggestions from student skills and completed roadmap items with `is_persisted=False`. Row is only created on explicit first PUT.
    - `PUT /v1/portfolio`: Owner only. Validates custom slug uniqueness (catches 409 Conflict), audit logs slug/visibility changes, persists/updates record.
    - `GET /v1/portfolio/p/{slug}`: Public unauthenticated view. Returns identical 404 for missing, private (`is_public=False`), or disabled. Sets `X-Robots-Tag: noindex, nofollow`, `Cache-Control: no-cache, no-store, must-revalidate`, and enforces IP rate limiting.
    - `POST /v1/portfolio/generate-text`: Enforces daily per-user rate limit; sanitizes prompt inputs via `portfolio_text_v1.txt`; executes through `LLMGateway`; anti-hallucination post-validator rejects any number, year, or percentage not present in user facts; returns deterministic template fallback when validation fails or gateway offline. User facts are never logged.
- **Testing & Verification**:
  - Comprehensive tests in `tests/test_portfolio.py`:
    - `test_get_portfolio_creates_no_rows`: verifies GET produces zero DB writes and returns `is_persisted=False`.
    - `test_put_portfolio_persists_row`: verifies first PUT persists row, assigns slug, and sets `is_persisted=True`.
    - `test_put_portfolio_slug_rules_and_conflict`: validates slug regex, reserved words, and 409 conflict handling.
    - `test_put_portfolio_validation_limits`: enforces max 20 items, invalid URLs, and `extra="forbid"`.
    - `test_skills_provenance_labels`: confirms `test_assessed` vs `self_reported` labels.
    - `test_public_portfolio_privacy_and_headers`: verifies unauthenticated access, 404 for private/missing, header enforcement (`X-Robots-Tag`, `Cache-Control`), and omission of private PII.
    - `test_public_portfolio_visibility_toggles`: verifies sections disabled in visibility settings are omitted from public payload.
    - `test_generate_text_grounded_in_facts`: verifies AI output is strictly grounded in input facts and non-persisted.
    - `test_generate_text_anti_hallucination_rejects_invented_metrics`: validates that invented numbers/percentages trigger the deterministic template fallback.
  - Full test suite: **140 passed, 1 skipped** (100% pass rate).
  - Code hygiene: `ruff check app tests` passes cleanly with **0 errors**.

### Active Invariants
- Zero LLM calls synchronously inside any GET endpoint.
- `GET /v1/portfolio` strictly non-writing: never commits to DB.
- Public portfolio `GET /v1/portfolio/p/{slug}` uses strict allowlist schema; identical 404 for missing, private, or disabled.
- AI generated portfolio text is strictly post-validated for metric hallucinations against user facts.
- No hand-rolled PDF generation; PDF export deferred until client-side print stylesheet / maintained library decision.
- Foreign user resources always return HTTP 404 (never 403 or leaky 200).
- All request schemas enforce `extra="forbid"`.

---

## Session: 2026-10-24 (Antigravity) – Complete Resolution of All Deferred Steps Across Entire Codebase

### Done
- **Roadmap Step 1b (Endpoints & Cloning Engine)**:
  - `POST /v1/roadmaps`: Clones verified template into independent copies; applies 15% buffer weekly allocation; prevents template mutations from altering active user roadmaps.
  - `GET /v1/roadmaps/{id}`: Returns complete roadmap tree with phases, items, and completion percentages.
  - `PATCH /v1/roadmaps/items/{id}`: Validates state machine (`todo` -> `in_progress` -> `done`/`skipped`); automatically creates low-weight skill evidence when marked `done`.
  - `POST /v1/roadmaps/{id}/replan`: Recalculates unfinished items with a strict 7-day replan cooldown rate limit.
  - Multi-tenant ownership invariant: Foreign roadmaps return HTTP 404.
- **Career Catalog Step 1b (Search & Ranking)**:
  - `GET /v1/careers/search`: Case-insensitive title and alias search with max 60-char query limit; multi-tier ranking (`title` > `alias` > `trigram`); inline compatibility score when student profile is present.
- **Assessment Results Contextual Q&A & Selection**:
  - `POST /v1/assessment/results/{id}/ask`: Contextual career counseling with delimiter stripping, 6-message conversational window, and Pydantic validation.
  - `POST /v1/assessment/results/{id}/choose`: Preferred career selection updating user profile with validation.
- **Adaptive Diagnostic Tests Stage 2**:
  - `GET /v1/tests/history`: Paginated attempt history returning user test results, demonstrated levels, confidence scores, and completion timestamps.
  - `POST /v1/tests/language-advisor`: Deterministic recommendation questionnaire mapping goals (`dsa_interviews`, `machine_learning`, `backend_development`, `systems`, `mobile_development`) to languages, with AI-enhanced coaching explanations via `LLMGateway` and deterministic fallback.
- **Auth Step 2 (Password Reset & Progressive Rate Limiting)**:
  - Model & Migration `010_create_password_reset_tokens.py`: `password_reset_tokens` table (`id`, `user_id`, `token_hash`, `expires_at`, `used_at`, `created_at`).
  - `POST /v1/auth/forgot-password`: Constant-time execution, timing attack safe, 32-byte cryptographically secure tokens with SHA-256 hash and 30-min expiry, enqueues ARQ email dispatch.
  - `POST /v1/auth/reset-password`: Single-use validation, password update, token invalidation, and complete revocation of all active user refresh sessions.
  - Progressive rate limiting utility in `app/core/rate_limit.py` returning HTTP 429 when burst limits are exceeded.
- **ARQ Background Jobs & Workers**:
  - `generate_career_compatibility_explanation`, `generate_skill_report_narrative`, `cleanup_expired_test_attempts`, `cleanup_expired_auth_tokens`.
  - Hourly cleanup of abandoned test attempts and daily purge of expired tokens.
  - AI prompt templates: `career_compatibility_v1.txt`, `career_compare_v1.txt`, `career_skill_report_v1.txt`, `recommendation_enrichment_v1.txt`, `portfolio_pitch_v1.txt`, `language_advisor_v1.txt`.
- **Gateway Step 2 (Telemetry & Cost Accounting)**:
  - Token tracking in `TelemetryEvent` (`input_tokens`, `output_tokens`, `estimated_cost_usd`).
  - Asynchronous daily token counters in Redis (`llm:tokens:prompt`, `llm:tokens:completion`).
- **Portfolio Extensions**:
  - `GET /v1/portfolio/public/{user_id}`: Unauthenticated shareable public portfolio omitting private user credentials.
  - `POST /v1/portfolio/summary`: AI elevator pitch and recruiter highlights.
  - `GET /v1/portfolio/export/resume`: Formats structured Markdown resume from verified portfolio records.
- **Verification & Code Quality**:
  - Entire test suite: **137 passed, 1 skipped** (live Gemini smoke test).
  - Linting: `ruff check app tests` passes cleanly with **0 errors**.
  - All constraints maintained: deterministic scores, strict Bearer JWT auth, multi-tenant 404 isolation, `extra="forbid"`, zero LLM calls synchronously inside GET endpoints.

### Active Invariants
- Zero LLM calls synchronously inside any GET endpoint.
- All scores, levels, match calculations, and progression rules are deterministic Python code.
- Foreign user resources always return HTTP 404 (never 403 or leaky 200).
- All request schemas enforce `extra="forbid"`.

---

## Session: 2026-10-23 (Antigravity) – Portfolio Read-Only Aggregation (Step 1b)

### Done
- **Portfolio Aggregation Schema (`app/schemas/portfolio.py`)**:
  - `PortfolioProfile`: `user_id`, `name`, `email`, `education_level`, `target_career`, `subjects_of_interest`.
  - `PortfolioSkillItem`: `skill_id`, `slug`, `name`, `current_level`, `confidence`, `evidence_count`, `updated_at`.
  - `PortfolioCompletedRecommendation`: `item_id`, `item_type`, `title`, `provider`, `source_url`, `completed_at`.
  - `PortfolioCompletedMilestone`: `item_id`, `roadmap_id`, `type`, `title`, `topic`, `difficulty`, `source_url`, `completed_at`.
  - `PortfolioDiagnosticTest`: `attempt_id`, `type`, `topic`, `demonstrated_level`, `confidence`, `score_percentage`, `completed_at`.
  - `PortfolioSummary`: `total_skills_tracked`, `total_recommendations_completed`, `total_milestones_completed`, `total_tests_completed`.
  - `PortfolioResponse`: aggregates all sections with strict `extra="forbid"`.
- **Repository & Service Layer**:
  - `PortfolioRepository` (`app/repositories/portfolio_repository.py`):
    - Multi-domain on-demand read-only aggregation across `student_profiles`, `user_skills` (with evidence count aggregation), `recommendation_actions` (with grouped batch queries across `courses`, `certificates`, `internships`, `template_items`), `roadmap_items` (joined with `roadmaps`), and `test_attempts`.
    - Guarantees flat query count with zero N+1 queries.
  - `PortfolioService` (`app/services/portfolio_service.py`):
    - Coordinates portfolio aggregation and deterministically calculates summary counters.
- **API Endpoint (`app/api/v1/portfolio.py`)**:
  - `GET /v1/portfolio`:
    - Strict Bearer JWT authentication (`get_current_user`).
    - Returns `200 OK` with `PortfolioResponse`.
    - Handles fresh/empty users gracefully (all counts 0, empty lists).
    - Registered in `app/api/v1/router.py`.
- **Testing & Quality Assurance**:
  - 5 comprehensive tests in `tests/test_portfolio.py`:
    - Unauthenticated access returns 401.
    - Non-GET methods disallowed (405).
    - Fresh/new user empty aggregation.
    - Full multi-domain aggregation (profile, skills with evidence count, completed recommendations, completed roadmap items, diagnostic tests, summary counters).
    - Strict cross-user ownership isolation (User B never sees User A's completed items).
  - Full project test suite execution: **123 passed, 1 skipped** (live Gemini smoke test).
  - Code hygiene: `ruff check app tests scripts` passes cleanly with 0 errors.
- **Documentation**:
  - Added ADR-017 in `docs/DECISIONS.md`.

### Pending Hooks & Features
- **Later steps for Portfolio**:
  - Public shareable vanity portfolio page.
  - PDF resume exporter.
  - AI-written portfolio summary / elevator pitch.
- **Stage 2 for Recommendations**:
  - AI enrichment of `why_it_fits` commentary in background ARQ worker (never in GET).
- **Kept Pending from Previous Steps**:
  - Roadmap Step 1b endpoints (`POST /v1/roadmaps`, `GET /v1/roadmaps/{id}`, `PATCH /v1/roadmaps/items/{id}`, `POST /v1/roadmaps/{id}/replan`).
  - Adaptive test Stage 2 (`GET /v1/tests/history`, language advisor).
  - Skill tracker Step 2 (background ARQ worker for AI skill report narrative).

### Do not touch
- Portfolio is strictly read-only; mutations only occur through primary source domain actions.
- Never call AI inside `GET /v1/portfolio`.
- Ownership is strictly enforced via token authentication.

---

## Session: 2026-10-23 (Antigravity) – Recommendations Engine & Actions (Step 1a)

### Done
- **Data Models & Migration**:
  - Schema extension on existing `courses`, `certificates`, `internships` (`app/models/career.py`):
    - Reused existing tables without duplicate entities.
    - Added missing columns: `cost_inr` (int nullable), `duration` (string nullable), `mode` ("online" | "offline" | "hybrid"), `location` (JSONB nullable), `eligibility` (JSONB nullable), `application_deadline` (DateTime nullable), `expires_at` (DateTime nullable).
  - New Model `RecommendationAction` (`app/models/recommendation.py`):
    - `id` (UUID PK), `user_id` (FK to users ondelete CASCADE, indexed), `item_type` (internship/course/certificate/resource), `item_id` (UUID), `state` (saved/dismissed/done), `created_at`, `updated_at`.
    - `UniqueConstraint("user_id", "item_type", "item_id", name="uq_recommendation_actions_user_item")`.
    - Exported in `app/models/__init__.py`.
  - Alembic Migration `009_create_recommendations_and_actions.py`:
    - Full upgrade and downgrade static SQL validation.
- **Pure Recommendation Engine (`app/services/recommendation_engine.py`)**:
  - `is_item_active_and_verified`: Enforces 90-day verification freshness window (`(now - last_verified).days <= 90`) and hides expired opportunities (`expires_at` / `application_deadline`), with dev bypass (`ALLOW_DRAFT_CAREERS=true`).
  - `filter_recommendation_candidates`: Filters candidates against budget tiers (`low` <= 50k INR, `medium` <= 250k INR, `high` unconstrained), location (online matches all; offline/hybrid matches user city/state/locations), hours available, and user action states (dismissed hidden unless explicitly requested; done excluded).
  - `score_and_rank_item` & `rank_recommendations`:
    - Multi-factor scoring: career match (30–40 pts), tested skill gap fit (15 pts bonus for tested skill < 2.5), location/mode fit (5–10 pts), cost fit (5–10 pts).
    - Deterministic tie-break: `(-match_score, title.lower(), str(id))`.
    - Deterministic `why_it_fits`: Pure code string generator directly mapping matched criteria; never calls AI.
    - Non-personalized fallback: If user lacks profile or skills, returns default recommendations with `personalised = False`.
- **Repository, Service & API Router**:
  - `RecommendationRepository` (`app/repositories/recommendation_repository.py`):
    - Bulk-loads candidates across courses, certificates, internships, and template items.
    - Bulk-loads user interaction records in a single query to eliminate N+1 queries.
  - `RecommendationService` (`app/services/recommendation_service.py`):
    - Enforces sliding-window rate limit (30 actions/min per user).
    - `state="done"` completion hook: automatically registers low-weight skill evidence (`source_type="roadmap"` or `"project"`, level_signal `"intermediate"`) and updates `UserSkill`.
  - Router (`app/api/v1/recommendations.py`):
    - `GET /v1/recommendations` with query filters (`career_id`, `item_type`, `budget_level`, `max_budget_inr`, `location`, `max_hours`, `include_dismissed`, `saved_only`, pagination).
    - `POST /v1/recommendations/{item_type}/{item_id}/action` with `extra="forbid"` validation, token authentication, and 404 for unknown/unverified items.
- **Testing & Quality Assurance**:
  - 7 comprehensive unit and integration tests in `tests/test_recommendations.py`:
    - Staleness (> 90 days) and expiration filtering.
    - Constraint filtering (budget, location, actions).
    - Deterministic ranking & tie-break.
    - Personalisation flag (`False` for fresh users, `True` after profile update).
    - Action lifecycle (save, dismiss, restore via `none`, mark `done`).
    - Automated skill evidence creation and idempotency.
    - Rate limit enforcement (30 requests/min, 429 on 31st).
    - Strict validation (`extra="forbid"`, 422 on invalid types, 404 on unverified items).
  - Full project test suite execution: **118 passed, 1 skipped** (live Gemini smoke test).
  - Code hygiene: `ruff check app tests scripts` passes cleanly with 0 errors.
- **Documentation**:
  - Added ADR-016 in `docs/DECISIONS.md`.

### Pending Hooks & Features
- **Step 1b (later)**:
  - `GET /v1/portfolio`: read-only aggregation of user profile, completed courses/certificates/internships/resources, verified projects, and skill tracker mastery.
- **Later steps**:
  - Public portfolio page, PDF resume exporter, AI-written portfolio summary.
  - Stage 2: Background ARQ worker for AI enrichment of `why_it_fits` (never in GET).
- **Kept Pending from Previous Steps**:
  - Roadmap Step 1b endpoints (`POST /v1/roadmaps`, `GET /v1/roadmaps/{id}`, `PATCH /v1/roadmaps/items/{id}`, `POST /v1/roadmaps/{id}/replan`).
  - Adaptive test Stage 2 (`GET /v1/tests/history`, language advisor).
  - Skill tracker Step 2 (background ARQ worker for AI skill report narrative).

### Do not touch
- Never mark anything "free" unless verified (`is_free: bool` requires `cost_inr == 0` AND verified).
- Never call AI inside GET requests; `why_it_fits` is generated by pure code.
- Items unverified for > 90 days or past expiration dates are strictly excluded from recommendation feeds.
- Action endpoints require strict token auth; cross-user or unauthorized access returns 401/404.

---

## Session: 2026-10-23 (Antigravity) – Versioned Roadmaps & Scheduling Engine (Step 1a)

### Done
- **Data Models & Migration**:
  - `ExamCycle` (`app/models/exam_cycle.py`):
    - `id` (UUID PK), `exam_id` (FK to exams), `year`, `registration_start`, `registration_end`, `exam_date`, `source_url`, `status` ("draft" | "verified"), `reviewer`, `last_verified_at`, `created_at`.
    - `UniqueConstraint("exam_id", "year", name="uq_exam_cycle_year")`.
  - Authoring Templates (`app/models/roadmap.py`):
    - `RoadmapTemplate`: `id`, `career_id` (FK to careers), `version`, `title`, `description`, `status` ("draft" | "verified"), `reviewer`, `last_verified_at`, `created_at`. `UniqueConstraint("career_id", "version")`.
    - `TemplatePhase`: `id`, `template_id` (FK), `name`, `phase_order`, `description`, `created_at`. `UniqueConstraint("template_id", "phase_order")`.
    - `TemplateItem`: `id`, `template_id` (FK), `phase_id` (FK), `item_code`, `type` ("video" | "problem" | "project" | "certificate" | "exam" | "internship_task" | "outreach"), `title`, `source_url`, `estimated_minutes`, `difficulty` (1–3), `topic`, `skill_id` (FK to skills), `prerequisites` (JSONB list of codes), `optional` (bool), `status`, `reviewer`, `last_verified_at`, `sequence_order`, `extra_data` (JSONB), `created_at`.
  - Independent Cloned User Roadmaps (`app/models/roadmap.py`):
    - `Roadmap`: `id`, `user_id` (FK), `career_id` (FK), `template_id` (FK), `template_version`, `title`, `status` ("active" | "completed" | "archived"), `timezone`, `hours_per_week`, `start_date`, `target_completion_date`, `created_at`, `updated_at`.
    - `RoadmapPhase`: `id`, `roadmap_id` (FK), `name`, `phase_order`, `description`, `created_at`.
    - `RoadmapItem`: `id`, `roadmap_id` (FK), `phase_id` (FK), `item_code`, `type`, `title`, `source_url`, `estimated_minutes`, `difficulty`, `topic`, `skill_id` (FK), `prerequisites`, `optional`, `status` ("todo" | "in_progress" | "done" | "skipped"), `scheduled_week`, `scheduled_date`, `completed_at`, `order_index`, `extra_data`, `created_at`, `updated_at`.
    - `ReplanHistory`: `id`, `roadmap_id` (FK), `reason`, `summary` (JSONB), `created_at`.
  - Authored migration `alembic/versions/008_create_roadmap_and_exam_cycle_tables.py` (tested upgrade and downgrade static SQL generation).
- **Seed Content & Prerequisite Validation**:
  - `app/data/seed/exam_cycles.json`: seeded draft cycles for JEE Main, GATE CS, CAT, UPSC CSE with original URLs and null dates where unknown.
  - `app/data/seed/roadmap_templates.json`: seeded SDE (`SWE`) accelerated template with 4 phases and 14 items:
    - Curated DSA problem list across Arrays, Binary Search, Strings, Sliding Window, Trees, Graphs, DP, Two Pointers with original LeetCode problem links (no copied problem text).
    - Videos with `source_url: null` pending verification.
    - Personalised projects scoped by level and marked `optional: true`.
    - Outreach items containing role titles and search keywords only, never people's names.
  - Idempotent seeders: `scripts/seed_exam_cycles.py` and `scripts/seed_roadmaps.py`.
  - `validate_prerequisite_graph` runs automatically on load, strictly verifying absence of missing references and circular dependencies.
- **Verification CLI**:
  - `scripts/verify_roadmap_item.py`: marks items verified by `--item-id`, `--item-code`, `--career`, or `--all`, recording reviewer name and verification date, and verifying parent template.
- **Pure Scheduling Engine (`app/services/roadmap_engine.py`)**:
  - Graph validation with `CycleError` and `MissingReferenceError`.
  - Priority ordering: Prerequisites strictly before dependents $\rightarrow$ Skill gap descending $\rightarrow$ Difficulty ascending $\rightarrow$ Optional items last.
  - Tested skill downweighting: beginner items downweighted only when tested level $\ge 2.0$; declared skills do not count.
  - Weekly capacity allocation: respects $W_{\text{usable}} = \text{round}(W_{\text{avail}} \times (1 - 0.15))$. Overflow items placed in `backlog_items`. Zero hours edge-case puts all items to backlog.
  - Timezone-aware date boundaries (ZoneInfo).
  - Replan algorithm: preserves completed and skipped items with historical timestamps; reschedules remaining active items from replan date.
  - Status transition state machine: enforces `todo -> in_progress -> done`, `todo -> skipped`, and `done` is final unless explicitly undone.
- **Testing & Quality Assurance**:
  - 14 pure unit tests in `tests/test_roadmap_engine.py`.
  - Full project test suite execution: **111 passed, 1 skipped** (live Gemini smoke test).
  - Code hygiene: `ruff check app tests scripts` passes cleanly with 0 errors.
- **Documentation**:
  - Added ADR-015 in `docs/DECISIONS.md`.

### Pending Hooks & Features
- **Roadmap Item Completion Evidence Hook**:
  - When Step 1b implements `PATCH /v1/roadmaps/items/{id}`, marking an item `status="done"` will automatically record a low-weight roadmap evidence row (`source_type="roadmap"`, `source_id=item.id`, capped at `"intermediate"`) through the existing Skill Tracker `SkillService.repo.add_evidence` path.
- **Kept Pending from Previous Steps**:
  - `GET /v1/tests/history` (Adaptive Test Stage 2).
  - Language advisor questionnaire with AI gateway integration.
  - Asynchronous background ARQ worker for `career_skill_report_v1` AI skill report generation and caching.

### Next (Step 1b upon approval)
- Endpoints:
  - `POST /v1/roadmaps` (generate personalized roadmap cloned from verified template).
  - `GET /v1/roadmaps/{id}` (fetch roadmap with parts 1, 2, 3 and completion progress).
  - `PATCH /v1/roadmaps/items/{id}` (update status, record completion, trigger low-weight skill evidence).
  - `POST /v1/roadmaps/{id}/replan` (reschedule remaining items from today, record replan history, rate limit).
- Ownership tests (strict HTTP 404 on cross-user access).

### Do not touch
- Editing a template must NEVER modify existing user roadmaps (cloned rows invariant).
- Never schedule more than available minutes in any week; preserve 15% buffer.
- Declared skills must never be used to skip or downweight roadmap items; tested evidence only.
- Done status is final unless explicitly undone.

---

## Session: 2026-10-23 (Antigravity) – Skill Tracker Engine (Step 1)

### Done
- **Data Models & Migration**:
  - `Skill` (`app/models/skill.py`):
    - `id` (UUID PK), `slug` (unique String 64, indexed), `name` (String 128), `description` (Text), `aliases` (JSONB, default `[]`), `category` (String 64, default "General"), `created_at`.
  - `SkillEvidence` (`app/models/skill.py`):
    - `id` (UUID PK), `user_id` (FK to users ondelete CASCADE, indexed), `skill_id` (FK to skills ondelete CASCADE, indexed).
    - `source_type` ("test" | "project" | "roadmap" | "declared"), `source_id` (UUID nullable).
    - `score` (Integer 0–100 nullable), `level_signal` ("beginner" | "intermediate" | "advanced" nullable).
    - `subtopic_scores` (JSONB, default `{}`), `summary` (Text nullable), `created_at`.
    - `UniqueConstraint("source_type", "source_id", name="uq_skill_evidence_source")`.
    - Composite index `ix_skill_evidence_user_skill` on `(user_id, skill_id)`.
  - `UserSkill` (`app/models/skill.py`):
    - `id` (UUID PK), `user_id` (FK to users ondelete CASCADE, indexed), `skill_id` (FK to skills ondelete CASCADE, indexed).
    - `current_level` (String 32, default "beginner"), `confidence` (String 32, default "low"), `updated_at`.
    - `UniqueConstraint("user_id", "skill_id", name="uq_user_skill")`.
  - Authored migration `alembic/versions/007_create_skill_tracker_tables.py` (tested upgrade and downgrade static SQL).
- **Skills Catalog Seed & Seeder**:
  - Authored `app/data/seed/skills_catalog.json` with 10 core skills (DSA, Python, C++, Java, Quantitative Aptitude, Logical Reasoning, ML, SQL & Databases, UI/UX Design, System Design).
  - Authored idempotent seeder `scripts/seed_skills_catalog.py`.
- **Pure Skill Tracker Engine (`app/services/skill_tracker_engine.py`)**:
  - Versioned config object: `SKILL_TRACKER_WEIGHTS_V1`.
  - Source weights: `test: 1.0` > `project: 0.6` > `roadmap: 0.35` > `declared: 0.15`.
  - Exponential recency decay: half-life $T_{1/2} = 30$ days ($w = w_0 \times 0.5^{\Delta t / 30}$).
  - Strict source level caps:
    - `declared`: hard-capped at `"beginner"` (1.0).
    - `roadmap`: hard-capped at `"intermediate"` (2.0).
    - Non-test evidence cap: if user has no test evidence, their aggregate level cannot exceed the maximum cap of their non-test sources.
  - Discrete level thresholds: $\ge 2.5 \rightarrow$ `"advanced"`, $\ge 1.6 \rightarrow$ `"intermediate"`, $< 1.6 \rightarrow$ `"beginner"`.
  - Confidence formula: requires total weight $\ge 1.8$ AND at least 1 test for `"high"`; $\ge 0.8$ for `"medium"`; otherwise `"low"`.
  - Subtopic analysis: identifies strengths ($\ge 70\%$) and weak subtopics ($< 60\%$).
  - Trend progression: strictly returns `None` if fewer than 2 evidence items; returns direction (`improving` / `stable` / `declining`), start/current levels, and chronological history when $\ge 2$.
  - Fallback deterministic report text generator with `report_status="fallback"`.
- **Repository, Services & API Layer**:
  - `SkillRepository` (`app/repositories/skill_repository.py`): case-insensitive search across slugs, names, and aliases.
  - `SkillService` (`app/services/skill_service.py`): listing user skills, handling self-declarations, generating reports with code-driven next recommendations, and ingesting test results.
  - Test finish atomic sync: `AdaptiveTestService.finish_test` computes subtopic performance, resolves matching catalog skill, inserts `SkillEvidence`, and updates `UserSkill` in the exact same database transaction.
  - Double finish idempotency: retrying test finish checks `get_evidence_by_source("test", attempt_id)` and prevents duplicate evidence insertion.
  - API router (`app/api/v1/skills.py`):
    - `GET /v1/skills`: current user's tracked skills.
    - `GET /v1/skills/{skill_id}/report`: detailed deterministic report; ownership violation strictly returns HTTP 404.
    - `POST /v1/skills/declare`: self-declared skills endpoint (lowest weight, capped at beginner).
    - Strict `extra="forbid"` on all request schemas.
    - Zero endpoints to create test or project evidence directly.
    - Never calls AI inside GET requests.
- **Testing & Verification**:
  - Created 17 unit and integration tests in `tests/test_skill_tracker.py`.
  - Full project test suite execution: **97 passed, 1 skipped** (live Gemini smoke test).
  - Code hygiene: `ruff check app tests scripts` passes cleanly with 0 errors.
- **Documentation**:
  - Added ADR-014 in `docs/DECISIONS.md`.

### In progress
- Step 1 complete. Awaiting user review before Step 2 (`career_skill_report_v1` prompt through gateway, run in ARQ background worker on test finish or profile update, storing `ai_report`, `ai_strengths`, `ai_weaknesses`, `generated_at`, with GET returning cached AI report or fallback).

### Broken or risky
- None. All 97 tests pass cleanly.

### Next (Step 2 upon approval)
- Background ARQ worker for asynchronous report generation using `career_skill_report_v1` prompt.
- Table columns / schema update to cache AI narrative reports (`ai_report`, `ai_strengths`, `ai_weaknesses`, `generated_at`).
- Updating `GET /v1/skills/{id}/report` to return cached AI report with `report_status="completed"` (or fallback if pending/failed).

### Do not touch
- Never call AI inside a GET request.
- Keep source caps strict: declared capped at beginner, roadmap capped at intermediate.
- Trend must remain strictly None if fewer than 2 evidence items.
- Production auth: Bearer JWT only.

---

## Session: 2026-10-23 (Antigravity) – Adaptive Skill & Aptitude Testing Engine (Stage 1)

### Done
- **Data Models & Migration**:
  - `TestQuestionBank` (`app/models/adaptive_test.py`):
    - `id` (UUID PK), `type` ("skill" | "aptitude"), `topic` (indexed), `subtopic`, `language` (e.g. "python", "cpp", "java", or null), `difficulty` (1, 2, 3), `question_text`, `options` (JSONB list of `{"id", "text"}`), `correct_option_id` (secret, never leaked before answer), `explanation`, `source_note`, `status` ("draft" | "verified", default "draft"), `reviewer`, `verified_at`, `career_cluster`.
  - `TestAttempt` (`app/models/adaptive_test.py`):
    - `id` (UUID PK), `user_id` (FK to users), `career_id` (FK to careers), `type`, `topic`, `language`, `status` ("in_progress" | "finished" | "expired"), `current_difficulty` (default 2), `target_questions` (default 6), `time_limit_seconds` (default 1200), `demonstrated_level`, `confidence`, `score_percentage`, `total_correct`, `total_answered`, `disclaimer_note`, `started_at`, `expires_at`, `finished_at`.
    - Composite index `ix_test_attempts_user_topic_status` on `(user_id, topic, status)`.
  - `TestAttemptAnswer` (`app/models/adaptive_test.py`):
    - `id` (UUID PK), `attempt_id` (FK to test_attempts), `question_id` (FK to test_question_banks), `question_order`, `difficulty_at_question`, `selected_option_id`, `is_correct`, `time_taken_seconds`, `created_at`.
    - `UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question_answer")`.
  - Authored migration `alembic/versions/006_create_adaptive_test_tables.py` (tested for both upgrade and downgrade static SQL compilation).
- **Question Bank Seed & Verification CLI**:
  - Authored 60 original, curriculum-grounded questions across DSA, Python, C++, Java, Quantitative Aptitude, and Logical Reasoning (`app/data/seed/test_questions.json`), all seeded as `status="draft"` with `source_note`.
  - Created idempotent seeder `scripts/seed_test_questions.py`.
  - Created verification CLI `scripts/verify_question.py` supporting `--id`, `--topic`, or `--all`, recording reviewer name and verification timestamp.
  - Added configuration settings: `ALLOW_DRAFT_QUESTIONS`, `TEST_TIME_LIMIT_MINUTES` (20), `TEST_RETAKE_COOLDOWN_MINUTES` (30), `TEST_MAX_STARTS_PER_HOUR` (10).
- **Adaptive Step Ladder Engine (`app/services/adaptive_test_engine.py`)**:
  - `calculate_next_difficulty(current_difficulty, is_correct)`: pure function stepping up (+1 to 3) on correct, down (-1 to 1) on incorrect.
  - `evaluate_final_level(answers)`: pure function enforcing minimum answers per level:
    - `"advanced"` requires $\ge 2$ answers at level 3, $\ge 60\%$ level 3 accuracy, and $\ge 60\%$ overall accuracy.
    - `"intermediate"` requires $\ge 2$ answers at level $\ge 2$, $\ge 50\%$ level 2+ accuracy, and $\ge 40\%$ overall accuracy.
    - `"beginner"` otherwise.
    - Confidence rating ("low" for $< 3$ answers, "medium" for 3–5, "high" for $\ge 6$ stable).
    - Disclaimer note: "This level is a preliminary estimate from a short adaptive diagnostic test."
- **API Endpoints (`app/api/v1/adaptive_tests.py`) & Service Layer**:
  - `POST /v1/tests/start`: Server picks the starting question (difficulty 2). Verifies career is verified, checks active attempt conflict, retake cooldown, rate limits, and guarantees zero answer leakage.
  - `POST /v1/tests/{id}/answer`: Strictly checks ownership, evaluates answer against secret `correct_option_id`, returns explanation, advances adaptive difficulty, and returns next public question. Enforces single answer per question with idempotent resubmission. Rejects expired attempts.
  - `POST /v1/tests/{id}/finish`: Evaluates demonstrated proficiency, records completion, returns recommendations, and allows idempotent retrieval.
  - Strict `extra="forbid"` on all request bodies.
- **Testing & Verification**:
  - Created 15 tests in `tests/test_adaptive_tests.py`:
    - Progression rule cases (step up, step down, floor 1, ceiling 3).
    - Final level formula (all correct -> advanced, all wrong -> beginner, alternating -> intermediate, minimum answers requirement, low sample confidence).
    - Zero answer leakage in start and question payloads.
    - Double answer idempotency and conflict rejection.
    - Answering after expiry rejection.
    - One active attempt per user/topic.
    - Retake cooldown enforcement.
    - Strict user ownership isolation (HTTP 404).
    - Draft questions hidden by default.
    - Insufficient verified questions returns clear HTTP 400.
    - Request validation (`extra="forbid"`).
  - Full project test suite execution: **80 passed, 1 skipped** (live Gemini smoke test).
  - Code hygiene: `ruff check app tests` passes cleanly with 0 errors/warnings.
- **Documentation**:
  - Added ADR-013 in `docs/DECISIONS.md`.

### In progress
- Stage 1 complete. Awaiting user review before Stage 2 (skill_assessments sync, language advisor questionnaire, test history).

### Broken or risky
- None. All 80 tests pass cleanly.

### Next (Stage 2 upon approval)
- Append-only `skill_assessments` table (`user_id`, `skill`, `level`, `confidence`, `source`, `attempt_id`, `created_at`), keeping declared and assessed skills strictly separate.
- Deterministic language advisor questionnaire mapped by seed table, with AI explanations through gateway.
- Test history endpoint `GET /v1/tests/history`.

### Do not touch
- Deterministic progression & level rule: Server drives difficulty; client never sends or chooses difficulty.
- Zero answer leakage: never send correct answer or explanation before question is answered.
- Declared and assessed skills stay separate.
- Production auth: Bearer JWT only.

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
