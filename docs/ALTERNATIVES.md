# Architectural Alternatives & Trade-Off Analysis (`ALTERNATIVES.md`)

This document analyzes the technical alternatives considered during the architecture, design, and implementation of the AI Career Navigator platform, documenting why specific options were chosen, why others were rejected, and the trade-offs accepted.

---

## 1. Web Framework: FastAPI vs. Django vs. Flask

| Criterion | Chosen: FastAPI | Rejected: Django / DRF | Rejected: Flask / Quart |
| :--- | :--- | :--- | :--- |
| **Concurrency Runtime** | Native async/await event loop matching `asyncpg` and Redis | Monolithic WSGI heritage with async bolt-on | Synchronous WSGI (Flask); Quart has smaller ecosystem |
| **Schema Validation** | Native Pydantic V2 parsing at HTTP boundary | DRF serializers require duplicate typing declarations | Marshmallow / manual validation |
| **Type Safety & OpenAPI** | Automated OpenAPI 3.1 generation from Python type hints | Third-party extensions (`drf-spectacular`) | Manual Swagger configuration |
| **Latency Profile** | Sub-millisecond routing overhead | Higher framework middleware overhead | Low overhead, but lacks built-in async validation |

- **Why FastAPI Won**: The system relies heavily on asynchronous I/O across PostgreSQL connection pools, Redis cache queries, and concurrent LLM HTTP streaming calls. FastAPI's native ASGI foundation and deep Pydantic V2 integration guarantee strict schema validation at the perimeter with minimal latency.
- **Accepted Trade-off**: Requires explicit architectural scaffolding (repository layer, worker wiring, auth middleware) compared to Django’s pre-built admin panel.

---

## 2. Primary Datastore: PostgreSQL (Hybrid Relational + JSONB) vs. MongoDB vs. MySQL

| Criterion | Chosen: PostgreSQL 16+ | Rejected: MongoDB | Rejected: MySQL 8+ |
| :--- | :--- | :--- | :--- |
| **Data Model Flexibility** | Hybrid: Rigid relational catalog + JSONB semi-structured documents | Pure document store | Relational with basic JSON functions |
| **Integrity Guarantees** | Foreign keys, compound unique constraints, partial indexes | Application-level validation only | Relational integrity, but inferior JSONB indexing |
| **Index Capabilities** | Partial indexes (`WHERE status <> 'cancelled'`), GIN indexes | Secondary indexes, but lacks partial expression indexes | Limited functional indexing |
| **Async Ecosystem** | `asyncpg` provides superior binary protocol throughput | `motor` async driver | `aiomysql` is less performant and mature |

- **Why PostgreSQL Won**: Vocational roadmaps, career catalogs, colleges, exams, and activity ledgers demand strict ACID relational integrity and cascading foreign keys. Concurrently, semi-structured data (psychometric dimension scores, adaptive test payloads, and user portfolio customizations) benefit from PostgreSQL's JSONB and GIN indexing without sacrificing relational joins.
- **Accepted Trade-off**: Schema migrations require disciplined Alembic management and head verification compared to schemaless document stores.

---

## 3. Worker Queue: ARQ (Async Redis Queue) vs. Celery

| Criterion | Chosen: ARQ | Rejected: Celery |
| :--- | :--- | :--- |
| **Runtime Architecture** | Native `asyncio` execution loop directly sharing FastAPI models | Heavy multi-process/prefork architecture |
| **Connection Sharing** | Direct integration with `redis-py` async connection pool | Requires AMQP/RabbitMQ or complex Redis broker configurations |
| **Resource Footprint** | Extremely low memory overhead per worker process | High memory overhead; duplicate ORM initialization |
| **Serialization** | Native Python pickle or JSON | Pickle / Kombu serialization |

- **Why ARQ Won**: Because all database repositories and LLM services are authored with `async/await`, ARQ allows background jobs (such as weekly summary generation and career compatibility snapshots) to run asynchronously within the native Python event loop without spawning heavy OS processes.
- **Accepted Trade-off**: Does not support complex multi-hop workflow orchestration (canvas/chords) out-of-the-box, which Celery provides. For current workloads, sequential and single-task jobs are sufficient.

---

## 4. LLM Gateway & Provider Abstraction: Custom Gateway vs. LangChain / LlamaIndex

| Criterion | Chosen: Custom `LLMGateway` | Rejected: LangChain / LlamaIndex | Rejected: Direct Provider SDK Calls |
| :--- | :--- | :--- | :--- |
| **Dependency Footprint** | Zero external framework dependencies; pure `asyncio` + Pydantic | Hundreds of transient dependencies; frequent breaking API changes | Low footprint, but high vendor lock-in and zero isolation |
| **Security & Sanitization** | Centralized XML wrapping, delimiter neutralization, token filtering | Fragmented prompt injection hooks | Manual per-call sanitization prone to developer oversight |
| **Resilience & Fallbacks** | Universal 15s timeout, 20s budget, strict 1-retry, deterministic fallback | Complex callback chains and fallback abstractions | Unhandled timeouts crash user requests |
| **Auditability** | Clean AST isolation tests (`test_gateway_wiring.py`) | Impossible to audit vendor-specific abstraction leakage | Scattered vendor imports across application codebase |

- **Why Custom `LLMGateway` Won**: Heavy orchestration frameworks like LangChain introduce massive dependency graphs, erratic breaking changes, and uncontrolled prompt bloat. A lean, centralized `LLMGateway` (250 LOC) guarantees strict AST isolation, dependency injection, hard timeout budgets, XML boundary defense, and guaranteed deterministic fallback degradation.
- **Accepted Trade-off**: Custom prompt template loading and output schema parsing must be maintained in-house.

---

## 5. Scoring Architecture: Pure Code Math vs. End-to-End LLM Grading

| Criterion | Chosen: Code-Calculated Rubrics | Rejected: End-to-End LLM Scoring |
| :--- | :--- | :--- |
| **Score Consistency** | 100% deterministic mathematical formulas | Susceptible to temperature drift, seed variance, and model updates |
| **Adversarial Resistance** | Resistant to prompt injection, flattery, and sycophancy | Vulnerable to prompt injection jailbreaks awarding 100% |
| **Auditability & Fairness** | Versioned weights and transparent signals inspectable by students | "Black box" model scores with unexplainable fluctuations |
| **Language Fairness** | Multi-lingual boolean detection with zero language penalty | Implicit bias against regional English dialects or mixed language |

- **Why Pure Code Math Won**: Large Language Models are notoriously unreliable at scoring numeric rubrics objectively. Under the chosen architecture, the LLM is restricted strictly to returning boolean detection flags (`covered_points: Dict[str, bool]`). Pure Python code evaluates depth, structure, coverage, and assigns numerical grades based on versioned rubric weights.
- **Accepted Trade-off**: Requires authors to define structured rubric criteria and key-points in question seed files rather than letting the LLM grade freely.

---

## 6. Authentication: JWT + Opaque Refresh Token Families vs. Stateful Session Cookies

| Criterion | Chosen: JWT + Token Family Rotation | Rejected: Stateful Session Cookies |
| :--- | :--- | :--- |
| **Scalability** | Stateless access verification across horizontally scaled nodes | Requires centralized session lookups on every single HTTP request |
| **Mobile & Cross-Platform** | Native Bearer token support across web, mobile, and CLI clients | Cookie handling issues across cross-site API domains and native apps |
| **Theft Detection** | Immediate whole-family revocation upon reuse detection | Session hijacking requires manual invalidation |
| **Access Invalidation** | Bounded 15-minute access lifetime + immediate refresh revocation | Instant session revocation, but higher database lookup penalty |

- **Why Token Family Rotation Won**: Combines the high performance of stateless short-lived JWT access tokens (15m) with the security of stateful refresh token families in PostgreSQL. If an attacker intercepts and attempts to replay a rotated refresh token, the system detects reuse and revokes all active tokens in that family immediately.
- **Accepted Trade-off**: Requires maintaining `refresh_tokens` table cleanup tasks for expired token records.

---

## 7. Adaptive Testing: Deterministic Step-Ladder vs. Continuous Item Response Theory (IRT)

| Criterion | Chosen: Deterministic Step-Ladder Progression | Rejected: Continuous IRT (3-PL Model) |
| :--- | :--- | :--- |
| **Transparency** | Clear rules: 2 correct advance level; 2 incorrect lower level | Statistical probability distribution difficult to explain to students |
| **Cold-Start Requirements** | Operates immediately with zero calibration datasets | Requires thousands of student responses to calibrate discrimination parameters |
| **Auditability** | Bounded progression: levels 1 to 5 with strict ladder constraints | Complex convergence algorithms with non-deterministic ability bounds |
| **Implementation Complexity**| 120 lines of pure, testable Python code | Heavy scientific Python dependencies (`scipy`, `numpy`) in request path |

- **Why Step-Ladder Won**: Classical IRT requires extensive historical testing populations to calibrate discrimination and guessing parameters. The deterministic step-ladder algorithm provides instant, transparent, and reproducible adaptive difficulty transitions suitable for vocational skill profiling.
- **Accepted Trade-off**: Lacks continuous psychometric discrimination modeling, but provides predictable and debuggable skill evaluation.

---

## 8. Portfolio Sharing: Allowlisted Public Slug vs. Sequential/UUID User Paths

| Criterion | Chosen: `/v1/portfolio/p/{slug}` | Rejected: `/v1/portfolio/public/{user_id}` |
| :--- | :--- | :--- |
| **IDOR Vulnerability** | Impossible: user ID is decoupled from the URL | High risk: exposing internal user IDs allows enumeration and scraping |
| **User Control** | Student chooses their URL identity; can change slug or toggle private | Fixed to internal identifier; impossible to re-brand |
| **Data Projection** | Dedicated `PublicPortfolioViewResponse` excluding all private keys | Risk of leaking user profile fields or internal database IDs |
| **SEO & Sharing** | Clean, human-readable URLs (`/p/alex-chen`) | Opaque UUID URLs (`/public/550e8400-e29b-41d4-a716-446655440000`) |

- **Why Public Slug Won**: Permanently eliminating the user ID route eradicates Insecure Direct Object References (IDOR). Public portfolios project only explicitly allowlisted fields, while security tests confirm internal user IDs, emails, and assessment answers are never included in the payload.
- **Accepted Trade-off**: Requires maintaining a reserved keyword list (`RESERVED_SLUGS`) and handling slug collision deduplication.

---

## 9. Prompt Injection Defense: XML Isolation + Token Neutralization vs. System Prompt Only

| Criterion | Chosen: Multi-Layer Structural Defense | Rejected: System Directives Alone |
| :--- | :--- | :--- |
| **Adversarial Resilience** | High: structural boundaries, delimiter stripping, token filtering | Low: easily bypassed by "ignore previous instructions" jailbreaks |
| **Boundary Enforcement** | Explicit XML parsing boundary (`<user_input name="...">`) | Blended unstructured text where student input mixes with prompts |
| **Deterministic Guarantee**| Code strips control tokens (`<|im_start|>`) before model sees text | Model relies entirely on internal attention filtering |
| **Automated Testing** | Comprehensive injection test battery across all 14 templates | Subjective manual testing |

- **Why Multi-Layer Structural Defense Won**: "Prompting the model to be good" fails against determined attackers. Encapsulating untrusted text in strict `<user_input>` XML tags, neutralizing control tokens, stripping delimiter breakout tags, and placing a universal `CRITICAL SECURITY DIRECTIVE` across all templates provides robust defense-in-depth.
- **Accepted Trade-off**: Legitimate inputs containing delimiter-looking tags (`<system>`) have tags replaced with `[FILTERED_DELIMITER]`.
