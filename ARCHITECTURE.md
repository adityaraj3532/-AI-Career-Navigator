# AI Career Navigator – System Architecture

One-page overview of modules, request data flows, trust boundaries, and core database schema models.

---

## 1. Module Ownership Matrix

| Module Directory | Primary Responsibility & Ownership | Boundary Rules |
| :--- | :--- | :--- |
| `app/core/` | Configuration, security tokens (JWT), DB session factory, Redis client. | Lowest-level singleton utilities; depends on nothing in `app/`. |
| `app/models/` | SQLAlchemy declarative database models and relationships. | Pure ORM entity definitions; no queries or business logic. |
| `app/schemas/` | Pydantic data contracts (DTOs, request/response models, AI schemas). | Pure validation schemas with type hints; no database access. |
| `app/repositories/` | Database access only (CRUD operations, filtering, eager loading). | Only layer authorized to interact with SQLAlchemy sessions. |
| `app/services/` | Business domain workflows, deterministic scoring, ownership verification. | Coordinates repositories, workers, and LLM gateway. |
| `app/api/` | FastAPI routers, HTTP request/response serialization, route guards. | Thin controllers; delegate immediately to services. |
| `app/llm/` | Google Gemini gateway, schema validation, retry & deterministic fallback. | Enforces prompt sanitization; validates outputs against Pydantic. |
| `app/llm/prompts/` | Versioned prompt templates stored as discrete text/jinja files. | Isolated prompt definitions with explicit tag delimiters. |
| `app/workers/` | ARQ background job worker functions, scheduled tasks, queues. | Non-blocking async worker jobs for heavy compute or async AI tasks. |
| `app/data/seed/` | Verified static seed datasets (exams, colleges, courses, resources). | Source-of-truth JSON files for pre-populating catalog tables. |

---

## 2. Request Data Flows

### A. Standard Operational Request Flow
```text
[Client / Browser]
       │
       ▼ (1. HTTPS Request + Bearer JWT)
[app/api/ (FastAPI Router)]
       │ (2. Authenticate token, validate payload via Pydantic Schema)
       ▼
[app/services/ (Service Layer)]
       │ (3. Verify ownership & calculate scores/rules deterministically)
       ▼
[app/repositories/ (Repository Layer)]
       │ (4. Construct async SQLAlchemy statement)
       ▼
[PostgreSQL Database]
```

### B. AI Enrichment & Gateway Flow
```text
[app/services/]
       │ (1. Deterministic score calculated; fetch valid catalog DB IDs)
       ▼
[app/llm/gateway.py]
       │ (2. Load template from app/llm/prompts/ & sanitize delimited user text)
       ▼
[Google Gemini API (google-genai)]
       │ (3. Return structured JSON payload)
       ▼
[app/llm/validator.py]
      ├── Validation Success: Check referenced IDs exist in DB ──► [Return to Service]
      └── Validation Failed: Retry once. If still invalid ───────► [Deterministic Fallback]
```

---

## 3. Trust Boundaries & Input Ingress

1. **Boundary 1: External Client HTTP Requests (Untrusted)**
   - **Ingress**: Public Internet to FastAPI router endpoints.
   - **Protection**: JWT authentication guards, rate limiting, and Pydantic schema validation. Malformed inputs are rejected with 422 Unprocessable Entity before reaching services.
2. **Boundary 2: User Free-Text Input (Untrusted)**
   - **Ingress**: Open text fields (chat queries, portfolio text, profile bio, notes).
   - **Protection**: Never passed raw to shell, SQL, or LLMs. Always sanitized and delimited inside XML tags (e.g., `<user_input>...</user_input>`) before prompt interpolation to prevent prompt injection.
3. **Boundary 3: AI Model Output (Semi-Trusted / Suspect)**
   - **Ingress**: Responses received from Google Gemini API.
   - **Protection**: Never trusted blindly. Validated against strict Pydantic schemas, checked against active database entity IDs (exams, colleges, resources), retried once upon failure, and replaced with deterministic code fallback if invalid.

---

## 4. Relational Database Schema Outline

All entities enforce relational foreign key constraints and multi-tenant user ownership:

1. **Identity & User Profiles**:
   - `users`: Core authentication identity (`id`, `email`, `hashed_password`, `role`, `is_active`, `created_at`).
   - `profiles`: Demographic and academic background (`user_id`, `full_name`, `grade_level`, `target_stream`, `target_year`, `bio`).
2. **Academic & Extracurricular Evidence**:
   - `projects`: Student projects (`id`, `user_id`, `title`, `description`, `skills_used`, `artifact_url`).
   - `competitions`: Competitions & hackathons (`id`, `user_id`, `title`, `rank_or_award`, `year`).
   - `records`: Academic transcripts and certifications (`id`, `user_id`, `category`, `score_or_grade`, `issuer`).
3. **Assessments & Testing**:
   - `assessment_questions`: Question bank (`id`, `category`, `sub_domain`, `prompt_text`, `options`, `correct_answer_id`).
   - `assessment_answers`: User responses (`id`, `user_id`, `question_id`, `selected_option_id`, `time_spent_seconds`).
   - `assessment_results`: Deterministically scored results (`id`, `user_id`, `score`, `percentile`, `domain_breakdown`, `created_at`).
   - `tests` & `test_attempts`: Standardized aptitude tests and user attempt histories.
4. **Verified Career, Exam & Institution Catalogs (Seed Verified)**:
   - `careers`: Career paths (`id`, `title`, `cluster`, `overview`, `salary_bracket`, `market_demand`).
   - `exams`: Entrance exams (`id`, `name`, `code`, `conducting_body`, `eligibility`, `syllabus_url`).
   - `colleges`: Accredited universities/colleges (`id`, `name`, `nirf_rank`, `location`, `type`).
   - `courses`: Degrees and programs offered (`id`, `college_id`, `degree_name`, `stream`, `duration_years`).
   - `resources`: Verified learning materials and guides (`id`, `title`, `url`, `type`, `domain_tag`).
5. **Shortlists & Comparisons**:
   - `shortlists`: User-saved items (`id`, `user_id`, `entity_type` [career/college/exam], `entity_id`).
   - `comparisons`: Side-by-side user comparisons (`id`, `user_id`, `entity_type`, `compared_entity_ids`).
6. **Skills & Progression**:
   - `skills`: Master skill taxonomy (`id`, `name`, `category`).
   - `skill_history`: Progression ledger (`id`, `user_id`, `skill_id`, `level`, `verified_source`, `recorded_at`).
   - `progress_streaks`: Daily activity streaks (`user_id`, `current_streak`, `longest_streak`, `last_active_date`).
   - `milestones`: Unlocked achievements (`id`, `user_id`, `milestone_code`, `achieved_at`).
7. **Roadmaps, Tasks & Recommendations**:
   - `roadmaps`, `phases`, `roadmap_items`: Multi-phase career execution plans with ordered action items.
   - `recommendations`: Deterministically ranked career/college/exam guidance with AI phrasing.
   - `planner_tasks`: Scheduled tasks, reminders, and deadlines (`id`, `user_id`, `title`, `due_date`, `is_done`).
8. **Coaching & Interactive Sessions**:
   - `portfolio`: Aggregated user showcase (`id`, `user_id`, `slug`, `summary_statement`, `is_public`).
   - `interview_sessions`: Mock interview transcripts and deterministic scoring metrics.
   - `chat_history`: Threaded conversational guidance logs with role and sanitized message tokens.

---

## 5. Architectural Deep Dives & Related Docs
- [CONSTRAINTS.md](file:///c:/Users/Lenovo/Desktop/Appa/docs/CONSTRAINTS.md) – Operational rules and non-negotiables.
- [DECISIONS.md](file:///c:/Users/Lenovo/Desktop/Appa/docs/DECISIONS.md) – Architectural Decision Records (ADRs).
- [DEPENDENCIES.md](file:///c:/Users/Lenovo/Desktop/Appa/docs/DEPENDENCIES.md) – Approved third-party libraries.
- [HANDOVER.md](file:///c:/Users/Lenovo/Desktop/Appa/docs/HANDOVER.md) – State of the codebase, progress, and roadmap.
